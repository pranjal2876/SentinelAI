"""
Geometric zones used by the threat engine.

A `Zone` is a named polygon with a semantic type (restricted area, tripwire
line, direction-controlled corridor, etc.). Zones are defined in normalized
coordinates [0..1] so they are resolution-independent and can be drawn once in
the dashboard and reused across camera resolutions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np


class ZoneType(str, Enum):
    RESTRICTED = "restricted"      # any presence is an intrusion
    TRIPWIRE = "tripwire"          # a line; crossing triggers an event
    DIRECTIONAL = "directional"    # movement against `allowed_direction`
    VEHICLE_EXCLUDE = "vehicle_exclude"  # vehicles not allowed
    COUNTING = "counting"          # entry/exit counting line


@dataclass
class Zone:
    """A polygon (or line) region of interest in normalized coordinates."""

    id: str
    name: str
    type: ZoneType
    # Polygon points as (x, y) in [0,1]. For TRIPWIRE/COUNTING, exactly 2 points.
    points: List[Tuple[float, float]]
    # For DIRECTIONAL zones: allowed unit direction vector (dx, dy).
    allowed_direction: Optional[Tuple[float, float]] = None
    enabled: bool = True
    metadata: dict = field(default_factory=dict)

    def polygon_px(self, width: int, height: int) -> np.ndarray:
        """Return polygon points scaled to pixel coordinates."""
        return np.array(
            [(x * width, y * height) for x, y in self.points], dtype=np.float32
        )

    def contains(self, point: Tuple[float, float], width: int, height: int) -> bool:
        """Point-in-polygon test (ray casting) for a pixel-space point."""
        poly = self.polygon_px(width, height)
        if len(poly) < 3:
            return False
        px, py = point
        inside = False
        n = len(poly)
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if ((yi > py) != (yj > py)) and (
                px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi
            ):
                inside = not inside
            j = i
        return inside

    def line_px(self, width: int, height: int
                ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Return the two endpoints (pixels) for a tripwire/counting line."""
        (x1, y1), (x2, y2) = self.points[0], self.points[1]
        return (x1 * width, y1 * height), (x2 * width, y2 * height)


def segments_intersect(p1, p2, p3, p4) -> bool:
    """Return True if segment p1p2 intersects segment p3p4."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (
        ccw(p1, p2, p3) != ccw(p1, p2, p4)
    )


def side_of_line(point, a, b) -> float:
    """Signed side of `point` relative to directed line a->b (>0 left, <0 right)."""
    return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])
