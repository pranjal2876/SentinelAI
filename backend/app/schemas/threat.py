"""Threat/event schemas."""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


class ThreatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    camera_id: str
    category: str
    severity: str
    score: float
    message: str
    timestamp: float
    track_ids: List[int] = []
    bbox: Optional[List[float]] = None
    snapshot_path: Optional[str] = None
    clip_path: Optional[str] = None
    event_metadata: dict = {}
    acknowledged: bool = False


class ThreatFilter(BaseModel):
    camera_id: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    start: Optional[float] = None
    end: Optional[float] = None
    acknowledged: Optional[bool] = None
    limit: int = 100
    offset: int = 0


class ThreatExplanation(BaseModel):
    category: str
    severity: str
    confidence: float
    why: str
    message: str
    contributing_factors: List[dict] = []
    tracks_involved: List[int] = []


class LiveThreatMessage(BaseModel):
    """Payload pushed over the events WebSocket."""
    type: str = "threat"
    camera_id: str
    category: str
    severity: str
    score: float
    message: str
    timestamp: float
    metadata: dict[str, Any] = {}
