"""
Application configuration.

All settings are loaded from environment variables (or a `.env` file) using
`pydantic-settings`, giving us typed, validated, centrally-managed config.

Usage
-----
    from app.core.config import settings
    print(settings.YOLO_MODEL)
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- Application ----
    APP_NAME: str = "SentinelAI"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # ---- Security ----
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ---- Database ----
    # Local dev uses SQLite (zero external services). Set USE_SQLITE=false to
    # use PostgreSQL (Docker/production). An explicit DATABASE_URL overrides all.
    USE_SQLITE: bool = True
    SQLITE_PATH: str = "./sentinelai.db"
    POSTGRES_USER: str = "sentinel"
    POSTGRES_PASSWORD: str = "sentinel_secret"
    POSTGRES_DB: str = "sentinelai"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    # ---- Redis ----
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # ---- Inference ----
    DEVICE: Literal["auto", "cuda", "cpu"] = "auto"
    YOLO_MODEL: str = "yolov8n.pt"
    DETECTION_CONF_THRESHOLD: float = 0.35
    DETECTION_IOU_THRESHOLD: float = 0.5
    TRACKER: Literal["bytetrack", "deepsort"] = "bytetrack"
    FRAME_STRIDE: int = 1
    MAX_INFERENCE_FPS: int = 25
    MODELS_DIR: str = "./models"

    # ---- Threat thresholds ----
    LOITERING_SECONDS: float = 30.0
    ABANDONED_OBJECT_SECONDS: float = 25.0
    CROWD_THRESHOLD: int = 8
    RUNNING_SPEED_PX_PER_S: float = 350.0

    # ---- Alerts ----
    ALERTS_ENABLED: bool = True
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_EMAIL_TO: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ---- Storage ----
    DATA_DIR: str = "./data"
    SNAPSHOT_DIR: str = "./data/snapshots"
    RECORDING_DIR: str = "./data/recordings"
    HEATMAP_DIR: str = "./data/heatmaps"

    # ------------------------------------------------------------------ #
    # Validators / computed properties
    # ------------------------------------------------------------------ #
    @field_validator("CORS_ORIGINS")
    @classmethod
    def _strip_origins(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins as a clean list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        """True when the active database is SQLite (affects engine pooling)."""
        if self.DATABASE_URL:
            return self.DATABASE_URL.startswith("sqlite")
        return self.USE_SQLITE

    @computed_field  # type: ignore[misc]
    @property
    def async_database_url(self) -> str:
        """Async SQLAlchemy connection string (SQLite or PostgreSQL)."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.USE_SQLITE:
            return f"sqlite+aiosqlite:///{self.SQLITE_PATH}"
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def sync_database_url(self) -> str:
        """Sync connection string (used by Alembic migrations)."""
        if self.USE_SQLITE and not self.DATABASE_URL:
            return f"sqlite:///{self.SQLITE_PATH}"
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def ensure_directories(self) -> None:
        """Create runtime storage directories if they do not exist."""
        for path in (
            self.MODELS_DIR,
            self.DATA_DIR,
            self.SNAPSHOT_DIR,
            self.RECORDING_DIR,
            self.HEATMAP_DIR,
        ):
            Path(path).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    s = Settings()
    s.ensure_directories()
    return s


settings = get_settings()
