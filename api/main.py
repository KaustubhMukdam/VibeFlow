"""
VibeFlow API — FastAPI entry point.

Handles:
  - DB connection with retry + backoff (critical for Docker startup ordering)
  - Automatic table creation on first run
  - ALS model training on startup if .pkl files are missing
  - APScheduler lifecycle
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import check_db_connection, ensure_tables
from api.scheduler import start_scheduler, stop_scheduler
from api.routers import recommend, session, library

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Startup constants ────────────────────────────────────────────────────────
MAX_DB_RETRIES = 10
RETRY_DELAY_BASE = 2  # seconds — delay grows linearly: 2s, 4s, 6s, ...


def _startup_train_als():
    """
    Train ALS model on startup if .pkl files don't exist.
    This is the fix for the Docker volume sync issue — the container
    that owns the DB connection must be the one to generate the models.
    """
    als_model_path = Path("models/saved/als_model.pkl")
    als_mappings_path = Path("models/saved/als_mappings.pkl")

    if als_model_path.exists() and als_mappings_path.exists():
        logger.info("ALS model files found — skipping startup training")
        return

    logger.info("ALS model files missing — training on startup...")
    try:
        from models.collaborative import train_als

        result = train_als()
        if result:
            logger.info("✅ ALS model trained successfully on startup")
        else:
            logger.info(
                "ALS training skipped — not enough interaction data yet. "
                "Run ingestion or generate mock history first."
            )
    except Exception as e:
        logger.error(f"Startup ALS training failed: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🎵 VibeFlow API starting...")

    # ── Retry DB connection with linear backoff ──────────────────────────
    # Docker Compose `depends_on: condition: service_healthy` isn't always
    # enough — the DB socket may accept connections before it's ready to
    # serve queries. Retrying here guarantees the app waits properly.
    connected = False
    for attempt in range(1, MAX_DB_RETRIES + 1):
        if check_db_connection():
            logger.info("✅ Database connected")
            connected = True
            break
        delay = RETRY_DELAY_BASE * attempt
        logger.warning(
            f"DB connection attempt {attempt}/{MAX_DB_RETRIES} failed — "
            f"retrying in {delay}s..."
        )
        await asyncio.sleep(delay)

    if not connected:
        logger.error(
            f"❌ Database connection failed after {MAX_DB_RETRIES} attempts. "
            "Recommendations will not work until the database is available."
        )
    else:
        # Ensure all ORM tables exist (safe to call repeatedly)
        ensure_tables()

        # Train ALS if pkl files are missing
        _startup_train_als()

    # Start the scheduler regardless — jobs will fail gracefully if DB is down
    start_scheduler()

    yield

    stop_scheduler()
    logger.info("VibeFlow API shutdown")


# ── App instance ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="VibeFlow API",
    description="Intelligent music recommendation engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(recommend.router, prefix="/recommend", tags=["Recommendations"])
app.include_router(session.router,   prefix="/session",   tags=["Session"])
app.include_router(library.router,   prefix="/library",   tags=["Library"])


@app.get("/health")
def health():
    return {"status": "ok", "db": check_db_connection()}
