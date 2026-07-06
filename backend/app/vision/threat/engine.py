"""
Modular threat-detection engine.

The engine consumes the per-frame list of `Track` objects (plus optional zones)
and emits `ThreatEvent`s. Each rule is independent and stateful where needed
(e.g. loitering dwell timers, abandoned-object timers, line-crossing history).

A per-(category, key) cooldown prevents alert spamming: once a threat fires it
will not refire for `cooldown_s` seconds unless it clears and re-triggers.

Scoring
-------
Every rule returns a normalized threat score in [0,1]. `ThreatSeverity` buckets
this into LOW/MEDIUM/HIGH/CRITICAL. Scores combine rule confidence with a
severity weight so, e.g., an abandoned object in a restricted zone outranks a
single loiterer.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.vision.detection.detector import CARRIABLE_CLASSES, VEHICLE_CLASSES
from app.vision.threat.zones import (
    Zone,
    ZoneType,
    segments_intersect,
    side_of_line,
)
from app.vision.types import Track, ThreatCategory, ThreatEvent


@dataclass
class _AbandonedCandidate:
    track_id: int
    class_name: str
    first_static: float
    last_pos: Tuple[float, float]
    bbox: Tuple[float, float, float, float]


@dataclass
class _LineState:
    """Per-track memory of which side of a counting/tripwire line it was on."""
    last_side: float = 0.0


@dataclass
class CountingStats:
    entries: int = 0
    exits: int = 0


class ThreatEngine:
    """Rule-based + heuristic threat detection over tracked objects."""

    def __init__(
        self,
        camera_id: str,
        zones: Optional[List[Zone]] = None,
        cooldown_s: float = 8.0,
    ) -> None:
        self.camera_id = camera_id
        self.zones = zones or []
        self.cooldown_s = cooldown_s

        # State stores
        self._cooldowns: Dict[str, float] = {}
        self._abandoned: Dict[int, _AbandonedCandidate] = {}
        self._line_state: Dict[Tuple[str, int], _LineState] = {}
        self.counting: Dict[str, CountingStats] = {}
        self._crowd_active = False

    # ------------------------------------------------------------------ #
    # Cooldown helper
    # ------------------------------------------------------------------ #
    def _ready(self, key: str, now: float) -> bool:
        last = self._cooldowns.get(key, 0.0)
        if now - last >= self.cooldown_s:
            self._cooldowns[key] = now
            return True
        return False

    # ------------------------------------------------------------------ #
    # Main entry point
    # ------------------------------------------------------------------ #
    def evaluate(
        self,
        tracks: List[Track],
        frame_shape: Tuple[int, int],
        now: Optional[float] = None,
    ) -> List[ThreatEvent]:
        """Evaluate all rules for one frame. `frame_shape` is (height, width)."""
        now = now or time.time()
        height, width = frame_shape
        events: List[ThreatEvent] = []

        persons = [t for t in tracks if t.class_name == "person"]
        vehicles = [t for t in tracks if t.class_name in VEHICLE_CLASSES]
        objects = [t for t in tracks if t.class_name in CARRIABLE_CLASSES]

        events += self._rule_intrusion(persons, width, height, now)
        events += self._rule_loitering(persons, now)
        events += self._rule_running(persons, now)
        events += self._rule_crowd(persons, width, height, now)
        events += self._rule_multiple_intruders(persons, width, height, now)
        events += self._rule_vehicle_zone(vehicles, width, height, now)
        events += self._rule_directional(tracks, width, height, now)
        events += self._rule_tripwire_and_counting(tracks, width, height, now)
        events += self._rule_abandoned_object(objects, persons, now)

        return events

    # ------------------------------------------------------------------ #
    # Individual rules
    # ------------------------------------------------------------------ #
    def _restricted_zones(self) -> List[Zone]:
        return [z for z in self.zones if z.enabled and z.type == ZoneType.RESTRICTED]

    def _rule_intrusion(self, persons, width, height, now) -> List[ThreatEvent]:
        events = []
        for zone in self._restricted_zones():
            for t in persons:
                if zone.contains(t.foot_point, width, height):
                    key = f"intrusion:{zone.id}:{t.track_id}"
                    if self._ready(key, now):
                        events.append(ThreatEvent(
                            category=ThreatCategory.INTRUSION,
                            score=0.82,
                            camera_id=self.camera_id,
                            timestamp=now,
                            message=f"Person {t.track_id} entered restricted zone "
                                    f"'{zone.name}'.",
                            track_ids=[t.track_id],
                            bbox=t.bbox,
                            metadata={"zone": zone.name, "zone_id": zone.id},
                        ))
        return events

    def _rule_loitering(self, persons, now) -> List[ThreatEvent]:
        events = []
        for t in persons:
            if t.dwell_seconds >= settings.LOITERING_SECONDS and t.speed < 60:
                key = f"loitering:{t.track_id}"
                if self._ready(key, now):
                    score = min(0.95, 0.45 + t.dwell_seconds /
                                (settings.LOITERING_SECONDS * 4))
                    events.append(ThreatEvent(
                        category=ThreatCategory.LOITERING,
                        score=score,
                        camera_id=self.camera_id,
                        timestamp=now,
                        message=f"Person {t.track_id} loitering for "
                                f"{t.dwell_seconds:.0f}s.",
                        track_ids=[t.track_id],
                        bbox=t.bbox,
                        metadata={"dwell_s": round(t.dwell_seconds, 1)},
                    ))
        return events

    def _rule_running(self, persons, now) -> List[ThreatEvent]:
        events = []
        for t in persons:
            if t.speed >= settings.RUNNING_SPEED_PX_PER_S:
                key = f"running:{t.track_id}"
                if self._ready(key, now):
                    score = min(0.9, 0.5 + t.speed /
                                (settings.RUNNING_SPEED_PX_PER_S * 3))
                    events.append(ThreatEvent(
                        category=ThreatCategory.RUNNING,
                        score=score,
                        camera_id=self.camera_id,
                        timestamp=now,
                        message=f"Person {t.track_id} running "
                                f"({t.speed:.0f} px/s).",
                        track_ids=[t.track_id],
                        bbox=t.bbox,
                        metadata={"speed_px_s": round(t.speed, 1)},
                    ))
        return events

    def _rule_crowd(self, persons, width, height, now) -> List[ThreatEvent]:
        events = []
        count = len(persons)
        if count >= settings.CROWD_THRESHOLD:
            # Density = people per unit area of their convex bounding region.
            pts = np.array([p.center for p in persons])
            spread = (pts[:, 0].ptp() + 1) * (pts[:, 1].ptp() + 1)
            density = count / (spread / (width * height) + 1e-6)
            key = "crowd:global"
            if self._ready(key, now):
                score = min(0.95, 0.5 + (count - settings.CROWD_THRESHOLD) * 0.05)
                events.append(ThreatEvent(
                    category=ThreatCategory.CROWD,
                    score=score,
                    camera_id=self.camera_id,
                    timestamp=now,
                    message=f"Crowd detected: {count} people gathered.",
                    track_ids=[p.track_id for p in persons],
                    metadata={"count": count, "density": round(float(density), 2)},
                ))
        return events

    def _rule_multiple_intruders(self, persons, width, height, now) -> List[ThreatEvent]:
        events = []
        for zone in self._restricted_zones():
            inside = [t for t in persons if zone.contains(t.foot_point, width, height)]
            if len(inside) >= 2:
                key = f"multi_intruders:{zone.id}"
                if self._ready(key, now):
                    events.append(ThreatEvent(
                        category=ThreatCategory.MULTIPLE_INTRUDERS,
                        score=0.9,
                        camera_id=self.camera_id,
                        timestamp=now,
                        message=f"{len(inside)} intruders in zone '{zone.name}'.",
                        track_ids=[t.track_id for t in inside],
                        metadata={"count": len(inside), "zone": zone.name},
                    ))
        return events

    def _rule_vehicle_zone(self, vehicles, width, height, now) -> List[ThreatEvent]:
        events = []
        zones = [z for z in self.zones
                 if z.enabled and z.type in (ZoneType.VEHICLE_EXCLUDE,
                                             ZoneType.RESTRICTED)]
        for zone in zones:
            for t in vehicles:
                if zone.contains(t.foot_point, width, height):
                    key = f"vehicle_zone:{zone.id}:{t.track_id}"
                    if self._ready(key, now):
                        events.append(ThreatEvent(
                            category=ThreatCategory.VEHICLE_IN_ZONE,
                            score=0.78,
                            camera_id=self.camera_id,
                            timestamp=now,
                            message=f"{t.class_name} {t.track_id} entered "
                                    f"prohibited zone '{zone.name}'.",
                            track_ids=[t.track_id],
                            bbox=t.bbox,
                            metadata={"zone": zone.name, "class": t.class_name},
                        ))
        return events

    def _rule_directional(self, tracks, width, height, now) -> List[ThreatEvent]:
        events = []
        zones = [z for z in self.zones
                 if z.enabled and z.type == ZoneType.DIRECTIONAL
                 and z.allowed_direction]
        for zone in zones:
            allowed = np.array(zone.allowed_direction, dtype=float)
            allowed /= (np.linalg.norm(allowed) + 1e-9)
            for t in tracks:
                if len(t.trajectory) < 6:
                    continue
                if not zone.contains(t.foot_point, width, height):
                    continue
                p0 = np.array(t.trajectory[-6])
                p1 = np.array(t.trajectory[-1])
                move = p1 - p0
                if np.linalg.norm(move) < 15:
                    continue
                move /= (np.linalg.norm(move) + 1e-9)
                # Cosine similarity; strongly opposite -> wrong direction.
                if float(np.dot(move, allowed)) < -0.5:
                    key = f"wrongdir:{zone.id}:{t.track_id}"
                    if self._ready(key, now):
                        events.append(ThreatEvent(
                            category=ThreatCategory.WRONG_DIRECTION,
                            score=0.7,
                            camera_id=self.camera_id,
                            timestamp=now,
                            message=f"{t.class_name} {t.track_id} moving against "
                                    f"allowed direction in '{zone.name}'.",
                            track_ids=[t.track_id],
                            bbox=t.bbox,
                            metadata={"zone": zone.name},
                        ))
        return events

    def _rule_tripwire_and_counting(self, tracks, width, height, now) -> List[ThreatEvent]:
        events = []
        zones = [z for z in self.zones
                 if z.enabled and z.type in (ZoneType.TRIPWIRE, ZoneType.COUNTING)
                 and len(z.points) >= 2]
        for zone in zones:
            a, b = zone.line_px(width, height)
            self.counting.setdefault(zone.id, CountingStats())
            for t in tracks:
                if len(t.trajectory) < 2:
                    continue
                prev, cur = t.trajectory[-2], t.trajectory[-1]
                if segments_intersect(prev, cur, a, b):
                    side_now = side_of_line(cur, a, b)
                    if zone.type == ZoneType.COUNTING:
                        if side_now >= 0:
                            self.counting[zone.id].entries += 1
                            direction = "entry"
                        else:
                            self.counting[zone.id].exits += 1
                            direction = "exit"
                        logger.debug(f"Counting {zone.name}: {direction} by {t.track_id}")
                    else:  # TRIPWIRE
                        key = f"tripwire:{zone.id}:{t.track_id}"
                        if self._ready(key, now):
                            events.append(ThreatEvent(
                                category=ThreatCategory.INTRUSION,
                                score=0.8,
                                camera_id=self.camera_id,
                                timestamp=now,
                                message=f"{t.class_name} {t.track_id} crossed "
                                        f"tripwire '{zone.name}'.",
                                track_ids=[t.track_id],
                                bbox=t.bbox,
                                metadata={"zone": zone.name, "type": "tripwire"},
                            ))
        return events

    def _rule_abandoned_object(self, objects, persons, now) -> List[ThreatEvent]:
        events = []
        active_ids = {o.track_id for o in objects}
        # Drop candidates whose track disappeared.
        for tid in list(self._abandoned.keys()):
            if tid not in active_ids:
                self._abandoned.pop(tid, None)

        for obj in objects:
            pos = obj.center
            cand = self._abandoned.get(obj.track_id)
            moved = (cand is None or
                     np.hypot(pos[0] - cand.last_pos[0],
                              pos[1] - cand.last_pos[1]) > 25)
            if moved:
                self._abandoned[obj.track_id] = _AbandonedCandidate(
                    track_id=obj.track_id,
                    class_name=obj.class_name,
                    first_static=now,
                    last_pos=pos,
                    bbox=obj.bbox,
                )
                continue

            static_for = now - cand.first_static
            # Nearest person distance (unattended if far from everyone).
            near = False
            for p in persons:
                if np.hypot(pos[0] - p.center[0], pos[1] - p.center[1]) < 140:
                    near = True
                    break

            if static_for >= settings.ABANDONED_OBJECT_SECONDS and not near:
                key = f"abandoned:{obj.track_id}"
                if self._ready(key, now):
                    score = min(0.95, 0.6 + static_for /
                                (settings.ABANDONED_OBJECT_SECONDS * 4))
                    events.append(ThreatEvent(
                        category=ThreatCategory.ABANDONED_OBJECT,
                        score=score,
                        camera_id=self.camera_id,
                        timestamp=now,
                        message=f"Unattended {obj.class_name} (track {obj.track_id}) "
                                f"for {static_for:.0f}s.",
                        track_ids=[obj.track_id],
                        bbox=obj.bbox,
                        metadata={"static_s": round(static_for, 1),
                                  "class": obj.class_name},
                    ))
        return events
