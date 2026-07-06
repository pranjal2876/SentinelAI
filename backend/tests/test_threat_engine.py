"""Unit tests for the threat engine rules."""
import time

from app.vision.threat import Zone, ZoneType
from app.vision.threat.engine import ThreatEngine
from app.vision.types import ThreatCategory, Track


def _person(track_id, bbox, first_seen, last_seen, speed=0.0, traj=None):
    return Track(
        track_id=track_id, class_id=0, class_name="person", bbox=bbox,
        confidence=0.9, trajectory=traj or [((bbox[0] + bbox[2]) / 2, bbox[3])],
        first_seen=first_seen, last_seen=last_seen, speed=speed,
    )


def test_intrusion_fires_inside_restricted_zone():
    zone = Zone(id="z", name="R", type=ZoneType.RESTRICTED,
                points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
    engine = ThreatEngine("cam1", zones=[zone])
    now = time.time()
    p = _person(1, (400, 400, 460, 560), now, now)
    events = engine.evaluate([p], (720, 1280), now=now)
    assert any(e.category == ThreatCategory.INTRUSION for e in events)


def test_loitering_requires_dwell_time():
    engine = ThreatEngine("cam1")
    now = time.time()
    # Dwell exceeds default threshold (30s), nearly stationary.
    p = _person(1, (100, 100, 160, 260), now - 45, now, speed=5)
    events = engine.evaluate([p], (720, 1280), now=now)
    assert any(e.category == ThreatCategory.LOITERING for e in events)


def test_running_detected_for_high_speed():
    engine = ThreatEngine("cam1")
    now = time.time()
    p = _person(1, (100, 100, 160, 260), now - 2, now, speed=600)
    events = engine.evaluate([p], (720, 1280), now=now)
    assert any(e.category == ThreatCategory.RUNNING for e in events)


def test_crowd_detected_above_threshold():
    engine = ThreatEngine("cam1")
    now = time.time()
    persons = [
        _person(i, (100 + i * 20, 100, 140 + i * 20, 260), now, now)
        for i in range(10)
    ]
    events = engine.evaluate(persons, (720, 1280), now=now)
    assert any(e.category == ThreatCategory.CROWD for e in events)


def test_cooldown_prevents_duplicate_alerts():
    engine = ThreatEngine("cam1", cooldown_s=100)
    now = time.time()
    p = _person(1, (100, 100, 160, 260), now - 45, now, speed=5)
    first = engine.evaluate([p], (720, 1280), now=now)
    second = engine.evaluate([p], (720, 1280), now=now + 1)
    assert len(first) >= 1
    assert not any(e.category == ThreatCategory.LOITERING for e in second)
