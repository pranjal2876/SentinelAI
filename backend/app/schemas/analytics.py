"""Analytics / reporting schemas."""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel


class CategoryCount(BaseModel):
    category: str
    count: int


class SeverityCount(BaseModel):
    severity: str
    count: int


class TimeBucket(BaseModel):
    bucket: str            # ISO date/hour
    count: int


class DashboardStats(BaseModel):
    total_threats: int
    threats_today: int
    active_cameras: int
    total_cameras: int
    by_category: List[CategoryCount]
    by_severity: List[SeverityCount]
    by_camera: Dict[str, int]
    timeline: List[TimeBucket]


class ReportRequest(BaseModel):
    start: float
    end: float
    camera_id: str | None = None
    fmt: str = "pdf"       # pdf | xlsx
