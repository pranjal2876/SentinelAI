"""Persisted region-of-interest zones per camera."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ZoneModel(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    zone_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    camera_id: Mapped[str] = mapped_column(
        ForeignKey("cameras.camera_id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    # Normalized polygon/line points: [[x,y], ...]
    points: Mapped[list] = mapped_column(JSON, nullable=False)
    allowed_direction: Mapped[list | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    zone_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
