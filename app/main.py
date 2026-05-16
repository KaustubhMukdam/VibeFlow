"""
app/main.py
VibeFlow FastAPI application entry point.

Startup sequence:
  1. Configure structured logging.
  2. Create DB tables (idempotent).
  3. Load ML model artifacts into memory (if available).
  4. Build cosine similarity matrix (if features exist).
  5. Mount all API routers.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import events, genres, library, models, recommendations
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.db.init_db import init_db


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown logic."""
    configure_logging()
    log = structlog.get_logger(__name__)
    settings = get_settings()

    log.info("vibeflow.starting", version="0.1.0", music_dir=str(settings.MUSIC_DIR))

    # Initialise database
    await init_db()

    # Load ML artifacts into memory (best-effort — won't fail if not yet trained)
    try:
        from app.db.session import _get_session_factory
        from app.features.feature_matrix import build_feature_matrix
        from app.models.recommender.similarity import build_similarity_matrix

        session_factory = _get_session_factory()
        async with session_factory() as db:
            from app.db.repository import FeatureRepo
            count = await FeatureRepo.count_extracted(db)
            if count > 0:
                log.info("vibeflow.loading_similarity_matrix", feature_count=count)
                X, song_ids = await build_feature_matrix(db, fit_scaler=False)
                build_similarity_matrix(X, song_ids)
                log.info("vibeflow.similarity_matrix_ready")
            else:
                log.info("vibeflow.no_features_yet", hint="Run: python -m app.cli extract")
    except Exception as exc:
        log.warning("vibeflow.artifact_load_skipped", reason=str(exc))

    log.info("vibeflow.ready", host=settings.HOST, port=settings.PORT)
    yield

    log.info("vibeflow.shutdown")


# ─── App factory ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="VibeFlow API",
        description=(
            "Local-first AI music recommendation system. "
            "Ingests your personal library, learns your taste from play/skip history, "
            "and recommends daily picks + weekend playlists."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS (permissive in dev for LAN phone access) ────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(library.router, prefix=prefix)
    app.include_router(events.router, prefix=prefix)
    app.include_router(recommendations.router, prefix=prefix)
    app.include_router(genres.router, prefix=prefix)
    app.include_router(models.router, prefix=prefix)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "VibeFlow"})

    @app.get("/", tags=["Health"])
    async def root() -> JSONResponse:
        return JSONResponse({
            "message": "VibeFlow API is running",
            "docs": "/docs",
            "health": "/health",
        })

    return app


app = create_app()
