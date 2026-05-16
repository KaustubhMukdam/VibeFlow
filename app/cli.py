"""
app/cli.py
VibeFlow command-line interface (Typer + Rich).

Commands:
  scan      – Ingest local music library into the database
  extract   – Extract audio features using librosa
  cluster   – Run KMeans genre clustering
  label     – Interactive genre labeling
  recommend – Print today's recommendations to the terminal
  serve     – Start the FastAPI development server

Usage:
  python -m app.cli <command> [options]
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
import uvicorn
from rich import print as rprint
from rich.console import Console
from rich.table import Table

app_cli = typer.Typer(
    name="vibeflow",
    help="VibeFlow — Local AI Music Recommendation System",
    add_completion=False,
)
console = Console()


# ─── Async runner helper ──────────────────────────────────────────────────────

def _run(coro):
    """Run an async coroutine from a sync CLI command."""
    return asyncio.run(coro)


# ─── DB session helper ────────────────────────────────────────────────────────

async def _get_session():
    """Bootstrap logging + DB, return an async session."""
    from app.core.logging_config import configure_logging
    from app.db.init_db import init_db
    from app.db.session import _get_session_factory

    configure_logging()
    await init_db()
    factory = _get_session_factory()
    return factory


# ─── Commands ─────────────────────────────────────────────────────────────────

@app_cli.command()
def scan(
    music_dir: Optional[Path] = typer.Option(None, help="Override MUSIC_DIR from .env"),
):
    """Scan the local music library and ingest songs into the database."""

    async def _scan():
        if music_dir:
            import os
            os.environ["MUSIC_DIR"] = str(music_dir)

        factory = await _get_session()
        async with factory() as db:
            from app.ingestion.pipeline import run_ingestion
            with console.status("[bold green]Scanning library..."):
                summary = await run_ingestion(db, show_progress=True)
            await db.commit()

        table = Table(title="Ingestion Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_row("Scanned", str(summary["scanned"]))
        table.add_row("Inserted", str(summary["inserted"]))
        table.add_row("Updated", str(summary["updated"]))
        table.add_row("Errors", str(summary["errors"]))
        console.print(table)

    _run(_scan())


@app_cli.command()
def extract(
    workers: int = typer.Option(4, help="Number of parallel extraction workers"),
):
    """Extract audio features (MFCCs, chroma, tempo, etc.) from all unprocessed songs."""

    async def _extract():
        factory = await _get_session()
        async with factory() as db:
            from app.features.pipeline import run_feature_extraction
            summary = await run_feature_extraction(db, show_progress=True)
            await db.commit()

        table = Table(title="Feature Extraction Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_row("Pending", str(summary["total"]))
        table.add_row("Extracted", str(summary["extracted"]))
        table.add_row("Already Done", str(summary["skipped"]))
        table.add_row("Failed", str(summary["failed"]))
        console.print(table)

    _run(_extract())


@app_cli.command()
def cluster(
    n_clusters: int = typer.Option(12, help="Number of genre clusters"),
    force: bool = typer.Option(False, "--force", help="Retrain even if artifact exists"),
):
    """Run KMeans clustering to auto-discover genre groups."""

    async def _cluster():
        factory = await _get_session()
        async with factory() as db:
            from app.features.feature_matrix import build_feature_matrix
            from app.models.genre.clustering import get_cluster_distribution, run_kmeans_clustering
            from app.models.recommender.similarity import build_similarity_matrix

            with console.status("[bold blue]Building feature matrix..."):
                X, song_ids = await build_feature_matrix(db, fit_scaler=True)

            with console.status("[bold blue]Clustering..."):
                labels = await run_kmeans_clustering(
                    db, X, song_ids, n_clusters=n_clusters, force_retrain=force
                )
                await db.commit()

            dist = get_cluster_distribution(labels)

            with console.status("[bold blue]Building similarity matrix..."):
                build_similarity_matrix(X, song_ids)

        console.print(f"\n[bold green]Clustered {len(song_ids)} songs into {len(dist)} groups.[/]")
        table = Table(title="Cluster Distribution")
        table.add_column("Cluster", style="cyan")
        table.add_column("Songs", style="green")
        for cid, count in sorted(dist.items()):
            table.add_row(f"cluster_{cid}", str(count))
        console.print(table)
        console.print("\n[yellow]Next step:[/] Run [bold]python -m app.cli label[/] to name each cluster.")

    _run(_cluster())


@app_cli.command()
def label(
    action: str = typer.Argument(
        "export",
        help="'export' — write cluster_samples.json  |  'apply' — write genres to DB",
    ),
    n_per_cluster: int = typer.Option(5, help="Songs to show per cluster"),
):
    """
    Label KMeans clusters with human-readable genre names.

    \b
    Step 1:  python -m app.cli label          -> exports cluster_samples.json
    Step 2:  Edit data/interim/cluster_samples.json (set confirmed_genre for each cluster)
    Step 3:  python -m app.cli label apply    -> writes genres to DB
    """

    async def _label():
        factory = await _get_session()
        async with factory() as db:
            from app.models.genre.labeler import (
                SAMPLES_FILE,
                apply_genre_labels,
                export_cluster_samples,
            )

            if action.lower() == "apply":
                # ── Apply confirmed names from the JSON file to the DB ──────────
                results = await apply_genre_labels(db)
                await db.commit()
                console.print(f"\n[green]Applied genre labels to {len(results)} clusters.[/]")
                table = Table(title="Genre Labels Applied")
                table.add_column("Cluster", style="cyan")
                table.add_column("Genre", style="green")
                table.add_column("Songs", style="yellow")
                for cid, (genre, count) in sorted(results.items()):
                    table.add_row(str(cid), genre, str(count))
                console.print(table)

            else:
                # ── Default: export samples for review ───────────────────────────
                samples = await export_cluster_samples(db, n_per_cluster=n_per_cluster)
                console.print(f"\n[green]Exported {len(samples)} clusters to:[/] {SAMPLES_FILE}")
                console.print("\n[yellow]Edit the file and set 'confirmed_genre' for each cluster.[/]")
                console.print("[yellow]Then run:[/] [bold]python -m app.cli label apply[/]")

    _run(_label())



@app_cli.command()
def recommend(
    n: int = typer.Option(10, help="Number of recommendations"),
    refresh: bool = typer.Option(False, "--refresh", help="Force regenerate today's picks"),
):
    """Print today's personalised song recommendations."""

    async def _recommend():
        factory = await _get_session()

        # Try to load similarity matrix
        try:
            async with factory() as db:
                from app.features.feature_matrix import build_feature_matrix
                from app.models.recommender.similarity import build_similarity_matrix
                X, song_ids = await build_feature_matrix(db, fit_scaler=False)
                build_similarity_matrix(X, song_ids)
        except Exception:
            pass  # proceed without similarity if features not ready

        async with factory() as db:
            from app.models.recommender.engine import recommend_daily
            recs = await recommend_daily(db, n=n, force_refresh=refresh)
            await db.commit()

            if not recs:
                console.print("[red]No recommendations yet. Run scan + extract + cluster first.[/]")
                return

            table = Table(title=f"Today's Top {n} Picks")
            table.add_column("#", style="dim")
            table.add_column("Title", style="bold")
            table.add_column("Artist", style="cyan")
            table.add_column("Genre", style="green")
            table.add_column("Why", style="yellow")

            from app.db.repository import SongRepo
            for r in recs:
                song = await SongRepo.get_by_id(db, r["song_id"])
                if song:
                    table.add_row(
                        str(r["rank"]),
                        song.title[:45],
                        song.artist[:30],
                        song.predicted_genre or "–",
                        r["reason_code"].replace("_", " "),
                    )

            console.print(table)

    _run(_recommend())


@app_cli.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
):
    """Start the VibeFlow FastAPI server."""
    console.print(f"[bold green]Starting VibeFlow on http://{host}:{port}[/]")
    console.print(f"[dim]API docs available at http://localhost:{port}/docs[/]")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@app_cli.command()
def status():
    """Show current system status (library, features, models)."""

    async def _status():
        factory = await _get_session()
        async with factory() as db:
            from app.db.repository import EventRepo, FeatureRepo, SongRepo
            from app.models.genre.classifier import RF_PIPELINE_PATH
            from app.models.genre.clustering import KMEANS_PATH
            from app.features.feature_matrix import SCALER_PATH

            total = await SongRepo.count(db)
            features = await FeatureRepo.count_extracted(db)
            events = await EventRepo.count(db)
            genres = await SongRepo.get_distinct_genres(db)

        table = Table(title="VibeFlow System Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_row("Songs in library", str(total))
        table.add_row("With features", str(features))
        table.add_row("Listening events", str(events))
        table.add_row("Genres discovered", str(len(genres)))
        table.add_row("Scaler artifact", "✓" if SCALER_PATH.exists() else "✗ (run extract)")
        table.add_row("KMeans artifact", "✓" if KMEANS_PATH.exists() else "✗ (run cluster)")
        table.add_row("RF Classifier", "✓" if RF_PIPELINE_PATH.exists() else "✗ (run label + cluster)")
        console.print(table)

    _run(_status())


if __name__ == "__main__":
    app_cli()
