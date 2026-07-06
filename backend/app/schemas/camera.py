"""Camera schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.camera import CameraStatus


class CameraCreate(BaseModel):
    camera_id: str = Field(..., min_length=1, max_length=64)
    name: str
    source: str = Field(..., description="Webcam index, RTSP URL, or file path")
    location: str = ""
    enabled: bool = True
    conf_threshold: float = 0.35


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    source: Optional[str] = None
    location: Optional[str] = None
    enabled: Optional[bool] = None
    conf_threshold: Optional[float] = None


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    camera_id: str
    name: str
    location: str
    source: str
    enabled: bool
    status: CameraStatus
    fps: float
    conf_threshold: float
