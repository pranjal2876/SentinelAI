"""
Core dataclasses shared across the vision pipeline.

Keeping these lightweight (plain dataclasses, not Pydantic) avoids validation
overhead on the hot per-frame path while still giving typed, self-documenting
structures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np


class ThreatCategory(str, Enum):
    """Enumeration of threat types the engine can raise."""

    INTRUSION = "intrusion"
    LOITERING = "loitering"
    ABANDONED_OBJECT = "abandoned_object"
    CROWD = "crowd"
    RUNNING = "running"
    WRONG_DIRECTION = "wrong_direction"
    VEHICLE_IN_ZONE = "vehicle_in_zone"
    MULTIPLE_INTRUDERS = "multiple_intruders"
    CAMERA_TAMPERING = "camera_tampering"
    FIRE_SMOKE = "fire_smoke"
    ANOMALY = "anomaly"
    VIOLENCE = "violence"
    FALL = "fall"


class ThreatSeverity(str, Enum):
    """Human-facing severity buckets derived from the numeric threat score."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_score(cls, score: float) -> "ThreatSeverity":
        if score >= 0.85:
            return cls.CRITICAL
        if score >= 0.65:
            return cls.HIGH
        if score >= 0.4:
            return cls.MEDIUM
        return cls.LOW


@dataclass
class Detection:
    """A single object detection in a frame (before tracking)."""

    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2 (pixels)
    confidence: float
    class_id: int
    class_name: str

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def foot_point(self) -> Tuple[float, float]:
        """Bottom-center point — a stable proxy for ground position."""
        x1, _, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, y2)

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.bbox
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)


@dataclass
class Track:
    """A tracked object with a persistent ID and short trajectory history."""

    track_id: int
    class_id: int
    class_name: str
    bbox: Tuple[float, float, float, float]
    confidence: float
    trajectory: List[Tuple[float, float]] = field(default_factory=list)
    first_seen: float = 0.0          # epoch seconds
    last_seen: float = 0.0
    age_frames: int = 0
    speed: float = 0.0               # pixels / second (foot point)

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def foot_point(self) -> Tuple[float, float]:
        x1, _, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, y2)

    @property
    def dwell_seconds(self) -> float:
        return max(0.0, self.last_seen - self.first_seen)


@dataclass
class ThreatEvent:
    """A raised threat, ready to be persisted and pushed to clients."""

    category: ThreatCategory
    score: float
    camera_id: str
    timestamp: float                 # epoch seconds
    message: str
    track_ids: List[int] = field(default_factory=list)
    bbox: Optional[Tuple[float, float, float, float]] = None
    snapshot_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def severity(self) -> ThreatSeverity:
        return ThreatSeverity.from_score(self.score)


@dataclass
class FrameResult:
    """Everything the pipeline produced for one processed frame."""

    camera_id: str
    frame_index: int
    timestamp: float
    detections: List[Detection]
    tracks: List[Track]
    threats: List[ThreatEvent]
    fps: float
    annotated_frame: Optional[np.ndarray] = None
