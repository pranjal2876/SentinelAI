"""Threat/event log model — one row per raised threat."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, Integer, String, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ThreatLog(Base):
    __tablename__ = "threat_logs"
    __table_args__ = (
        Index("ix_threat_camera_time", "camera_id", "timestamp"),
        Index("ix_threat_category_time", "category", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(String(512), default="")
    # Epoch seconds of the event (float for sub-second precision).
    timestamp: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    track_ids: Mapped[list] = mapped_column(JSON, default=list)
    bbox: Mapped[list | None] = mapped_column(JSON, nullable=True)
    snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    clip_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
