"""Zone schemas."""
from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class ZoneCreate(BaseModel):
    zone_id: str
    camera_id: str
    name: str
    type: str = Field(..., description="restricted|tripwire|directional|vehicle_exclude|counting")
    points: List[Tuple[float, float]]
    allowed_direction: Optional[Tuple[float, float]] = None
    enabled: bool = True


class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    points: Optional[List[Tuple[float, float]]] = None
    allowed_direction: Optional[Tuple[float, float]] = None
    enabled: Optional[bool] = None


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    zone_id: str
    camera_id: str
    name: str
    type: str
    points: List[Tuple[float, float]]
    allowed_direction: Optional[Tuple[float, float]] = None
    enabled: bool
