"""
Event bus — the bridge between camera worker threads and the async app.

Camera pipelines run in dedicated threads; when they raise a `ThreatEvent`, they
call `event_bus.publish_threat(...)`, which is thread-safe. The bus schedules the
async handling (persist to DB, save snapshot, broadcast to WS clients, dispatch
alerts) onto the main event loop via `run_coroutine_threadsafe`.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import numpy as np

from app.core.logging import logger
from app.vision.types import ThreatEvent


class EventBus:
    """Thread-safe hand-off from worker threads to the asyncio event loop."""

    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once at startup from the main event loop."""
        self._loop = loop

    def publish_threat(self, event: ThreatEvent,
                       frame: Optional[np.ndarray] = None) -> None:
        """Thread-safe entry point invoked from camera worker threads."""
        if self._loop is None:
            logger.warning("EventBus has no bound loop; dropping threat event.")
            return
        # Import here to avoid a circular import at module load.
        from app.services.threat_handler import handle_threat_event

        asyncio.run_coroutine_threadsafe(
            handle_threat_event(event, frame), self._loop
        )


event_bus = EventBus()
