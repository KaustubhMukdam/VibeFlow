"""
VibeFlow Database — engine, session factory, and utilities.

Fixes:
  - Removed unused duplicate `Base` (models.py is the single source)
  - Added `ensure_tables()` for automatic table creation on startup
  - Added DATABASE_URL fallback from individual POSTGRES_* env vars
  - Added `pool_pre_ping=True` to recover from stale connections
  - Uses `text("SELECT 1")` for proper connection health checks
"""
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load .env variables, but do NOT override existing environment variables!
# In Docker, docker-compose sets DATABASE_URL in the container env,
# so load_dotenv won't overwrite it.
load_dotenv(override=False)

logger = logging.getLogger(__name__)

# ── Build DATABASE_URL ───────────────────────────────────────────────────────
# Priority: DATABASE_URL env var > constructed from individual POSTGRES_* vars
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback: construct from individual vars (local development)
    _user = os.getenv("POSTGRES_USER", "vibeflow")
    _password = os.getenv("POSTGRES_PASSWORD", "vibeflow_secret")
    _host = os.getenv("POSTGRES_HOST", "localhost")
    _port = os.getenv("POSTGRES_PORT", "5432")
    _db = os.getenv("POSTGRES_DB", "vibeflow_db")
    DATABASE_URL = f"postgresql://{_user}:{_password}@{_host}:{_port}/{_db}"
    logger.info(f"DATABASE_URL constructed from POSTGRES_* env vars (host={_host})")

# pool_pre_ping=True: test connections before use, auto-recover stale ones
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session, closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Check if the database is reachable. Returns True/False."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return False


def ensure_tables():
    """
    Create all ORM-defined tables if they don't exist.
    Safe to call repeatedly — uses IF NOT EXISTS under the hood.
    """
    from db.models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")