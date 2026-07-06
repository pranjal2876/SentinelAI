"""
Frame annotation helpers — draw detections, tracks, trajectories, zones and a
threat banner onto BGR frames for the live view and stored snapshots.
"""
from __future__ import annotations

from typing import List, Tuple

import cv2
import numpy as np

from app.vision.threat.zones import Zone, ZoneType
from app.vision.types import ThreatEvent, Track

# Deterministic color per class for visual consistency.
_CLASS_COLORS = {
    "person": (0, 220, 0),
    "car": (255, 160, 0),
    "truck": (255, 120, 0),
    "bus": (255, 100, 0),
    "motorcycle": (0, 200, 255),
    "bicycle": (0, 255, 200),
    "backpack": (200, 0, 255),
    "handbag": (200, 0, 255),
    "suitcase": (200, 0, 255),
}
_SEVERITY_COLORS = {
    "low": (0, 200, 0),
    "medium": (0, 200, 255),
    "high": (0, 120, 255),
    "critical": (0, 0, 255),
}


def _color_for(name: str) -> Tuple[int, int, int]:
    return _CLASS_COLORS.get(name, (200, 200, 200))


def draw_zones(frame: np.ndarray, zones: List[Zone]) -> np.ndarray:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    for z in zones:
        if not z.enabled:
            continue
        if z.type in (ZoneType.TRIPWIRE, ZoneType.COUNTING) and len(z.points) >= 2:
            a, b = z.line_px(w, h)
            cv2.line(frame, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])),
                     (0, 0, 255), 2)
            cv2.putText(frame, z.name, (int(a[0]), int(a[1]) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        else:
            poly = z.polygon_px(w, h).astype(np.int32)
            if len(poly) >= 3:
                cv2.fillPoly(overlay, [poly], (0, 0, 200))
                cv2.polylines(frame, [poly], True, (0, 0, 255), 2)
                cx, cy = poly.mean(axis=0).astype(int)
                cv2.putText(frame, z.name, (cx - 20, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return cv2.addWeighted(overlay, 0.18, frame, 0.82, 0)


def draw_tracks(frame: np.ndarray, tracks: List[Track],
                show_trajectory: bool = True) -> np.ndarray:
    for t in tracks:
        x1, y1, x2, y2 = map(int, t.bbox)
        color = _color_for(t.class_name)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{t.class_name} #{t.track_id} {t.confidence:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        if show_trajectory and len(t.trajectory) > 1:
            pts = np.array(t.trajectory, dtype=np.int32)
            cv2.polylines(frame, [pts], False, color, 1)
    return frame


def draw_threat_banner(frame: np.ndarray, threats: List[ThreatEvent]) -> np.ndarray:
    if not threats:
        return frame
    top = max(threats, key=lambda e: e.score)
    color = _SEVERITY_COLORS.get(top.severity.value, (0, 0, 255))
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 34), color, -1)
    text = f"⚠ {top.severity.value.upper()}: {top.message}"
    cv2.putText(frame, text[:90], (10, 23),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return frame


def annotate_frame(frame: np.ndarray, tracks: List[Track],
                   threats: List[ThreatEvent], zones: List[Zone],
                   fps: float = 0.0) -> np.ndarray:
    out = frame.copy()
    out = draw_zones(out, zones)
    out = draw_tracks(out, tracks)
    out = draw_threat_banner(out, threats)
    cv2.putText(out, f"FPS: {fps:.1f} | Tracks: {len(tracks)}",
                (10, out.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (255, 255, 255), 1)
    return out
