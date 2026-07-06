"""Camera configuration model."""
from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CameraStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    CONNECTING = "connecting"


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="")
    # Source: "0" (webcam index), rtsp url, or file path.
    source: Mapped[str] = mapped_column(String(512), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[CameraStatus] = mapped_column(
        Enum(CameraStatus), default=CameraStatus.OFFLINE, nullable=False
    )
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    # Per-camera detector overrides (optional).
    conf_threshold: Mapped[float] = mapped_column(Float, default=0.35)
