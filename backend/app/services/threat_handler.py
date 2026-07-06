"""
Central async handler for a raised `ThreatEvent`.

Responsibilities (all best-effort, isolated so one failure can't block others):
  1. Persist a snapshot image to disk.
  2. Insert a `ThreatLog` row.
  3. Broadcast a live message to the "events" WebSocket topic.
  4. Dispatch email/Telegram alerts for high-severity events.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.db.base import AsyncSessionLocal
from app.db.models.event import ThreatLog
from app.schemas.threat import LiveThreatMessage
from app.services.alerts import dispatch_alerts
from app.vision.types import ThreatEvent
from app.websocket.manager import ws_manager


def _save_snapshot(event: ThreatEvent, frame: Optional[np.ndarray]) -> Optional[str]:
    if frame is None:
        return None
    try:
        import cv2

        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(event.timestamp))
        fname = f"{event.camera_id}_{event.category.value}_{ts}_{int(event.timestamp*1000)%1000}.jpg"
        out_dir = Path(settings.SNAPSHOT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = str(out_dir / fname)
        cv2.imwrite(path, frame)
        return path
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Snapshot save failed: {exc}")
        return None


async def _persist(event: ThreatEvent, snapshot_path: Optional[str]) -> None:
    try:
        async with AsyncSessionLocal() as session:
            row = ThreatLog(
                camera_id=event.camera_id,
                category=event.category.value,
                severity=event.severity.value,
                score=event.score,
                message=event.message,
                timestamp=event.timestamp,
                track_ids=event.track_ids,
                bbox=list(event.bbox) if event.bbox else None,
                snapshot_path=snapshot_path,
                event_metadata=event.metadata,
            )
            session.add(row)
            await session.commit()
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Threat persist failed: {exc}")


async def _broadcast(event: ThreatEvent, snapshot_path: Optional[str]) -> None:
    msg = LiveThreatMessage(
        camera_id=event.camera_id,
        category=event.category.value,
        severity=event.severity.value,
        score=round(event.score, 3),
        message=event.message,
        timestamp=event.timestamp,
        metadata={**event.metadata,
                  "snapshot": snapshot_path,
                  "track_ids": event.track_ids},
    )
    await ws_manager.broadcast_json("events", msg.model_dump())


async def handle_threat_event(event: ThreatEvent,
                              frame: Optional[np.ndarray] = None) -> None:
    """Full pipeline for a single raised threat event."""
    snapshot_path = _save_snapshot(event, frame)
    event.snapshot_path = snapshot_path
    await _persist(event, snapshot_path)
    await _broadcast(event, snapshot_path)
    await dispatch_alerts(event, snapshot_path)
