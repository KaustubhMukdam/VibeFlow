"""
app/core/config.py
Pydantic Settings loaded from the .env file.
Uses lru_cache so the settings object is constructed once per process.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Paths ─────────────────────────────────────────────────────────────────
    MUSIC_DIR: Path = Path("music_library")
    DATABASE_URL: str = "sqlite+aiosqlite:///./vibeflow.db"

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["*"]

    # ── Audio processing ──────────────────────────────────────────────────────
    FEATURE_EXTRACTION_WORKERS: int = 4
    SAMPLE_RATE: int = 22050
    # Duration in seconds to analyse per track. None means full track.
    ANALYSIS_DURATION: int | None = 30

    # ── Genre clustering ──────────────────────────────────────────────────────
    N_GENRE_CLUSTERS: int = 12

    # ── Recommendations ───────────────────────────────────────────────────────
    DAILY_RECOMMENDATION_COUNT: int = 10
    WEEKEND_PLAYLIST_COUNT: int = 30
    BEHAVIOR_DECAY_HALF_LIFE_DAYS: float = 7.0

    # ── Derived paths (not from env) ──────────────────────────────────────────
    @property
    def models_artifacts_dir(self) -> Path:
        return Path("models_artifacts")

    @property
    def data_interim_dir(self) -> Path:
        return Path("data/interim")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list) -> list:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("ANALYSIS_DURATION", mode="before")
    @classmethod
    def parse_duration(cls, v: str | int | None) -> int | None:
        if v is None or str(v).lower() in ("none", "null", ""):
            return None
        return int(v)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton per process)."""
    return Settings()
