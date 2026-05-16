"""
app/db/init_db.py
Creates all database tables on application startup.
Safe to call multiple times (uses CREATE TABLE IF NOT EXISTS semantics).
"""
from __future__ import annotations

import structlog

from app.db.base import Base
from app.db.session import get_engine

# Import all models so that Base.metadata is populated before create_all
from app.db import models  # noqa: F401

log = structlog.get_logger(__name__)


async def init_db() -> None:
    """Create all tables. Called from the FastAPI lifespan event."""
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database.tables_created", tables=list(Base.metadata.tables.keys()))
