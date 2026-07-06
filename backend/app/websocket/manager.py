"""
WebSocket connection manager.

Maintains sets of connected clients per topic ("events" for threat pushes, and
one topic per camera for MJPEG-over-WS frame streaming). Broadcasts are
resilient: a failed send simply drops that client.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Dict, Set

from fastapi import WebSocket

from app.core.logging import logger


class ConnectionManager:
    """Tracks active WebSocket clients grouped by topic."""

    def __init__(self) -> None:
        self._topics: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, topic: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._topics[topic].add(ws)
        logger.debug(f"WS client joined '{topic}' (total={len(self._topics[topic])})")

    async def disconnect(self, topic: str, ws: WebSocket) -> None:
        async with self._lock:
            self._topics[topic].discard(ws)
        logger.debug(f"WS client left '{topic}'")

    async def broadcast_json(self, topic: str, payload: dict[str, Any]) -> None:
        await self._broadcast(topic, payload, binary=False)

    async def broadcast_bytes(self, topic: str, data: bytes) -> None:
        await self._broadcast(topic, data, binary=True)

    async def _broadcast(self, topic: str, payload: Any, binary: bool) -> None:
        dead = []
        for ws in list(self._topics.get(topic, ())):
            try:
                if binary:
                    await ws.send_bytes(payload)
                else:
                    await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._topics[topic].discard(ws)

    def client_count(self, topic: str) -> int:
        return len(self._topics.get(topic, ()))


# Global singleton used across the app.
ws_manager = ConnectionManager()
