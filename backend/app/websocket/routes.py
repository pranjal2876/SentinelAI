"""
WebSocket routes.

* `/ws/events`         — live threat-event stream (JSON) for the dashboard.
* `/ws/stream/{cam}`   — live annotated MJPEG-style frames (binary JPEG) pushed
                         at the camera's processing rate.

An MJPEG HTTP fallback is also exposed for `<img>`-based simple viewers.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.services.camera import camera_manager
from app.websocket.manager import ws_manager

router = APIRouter()


@router.websocket("/ws/events")
async def events_ws(ws: WebSocket):
    """Push live threat events to connected dashboard clients."""
    await ws_manager.connect("events", ws)
    try:
        while True:
            # Keep the socket alive; client may send pings/filters.
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect("events", ws)
    except Exception:
        await ws_manager.disconnect("events", ws)


@router.websocket("/ws/stream/{camera_id}")
async def stream_ws(ws: WebSocket, camera_id: str):
    """Stream annotated JPEG frames for a single camera over WebSocket."""
    await ws.accept()
    target_fps = min(settings.MAX_INFERENCE_FPS, 25)
    interval = 1.0 / target_fps
    try:
        while True:
            worker = camera_manager.get(camera_id)
            if worker is None:
                await ws.send_json({"error": "camera not running"})
                await asyncio.sleep(1.0)
                continue
            jpeg = worker.latest_jpeg()
            if jpeg:
                await ws.send_bytes(jpeg)
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        return
    except Exception:
        return


def _mjpeg_generator(camera_id: str):
    """Yield multipart MJPEG frames for the HTTP fallback stream."""
    boundary = b"--frame"
    while True:
        worker = camera_manager.get(camera_id)
        jpeg = worker.latest_jpeg() if worker else None
        if jpeg:
            yield (boundary + b"\r\nContent-Type: image/jpeg\r\n"
                   + f"Content-Length: {len(jpeg)}\r\n\r\n".encode()
                   + jpeg + b"\r\n")


@router.get("/stream/{camera_id}.mjpg")
async def mjpeg_stream(camera_id: str):
    """HTTP MJPEG stream usable directly in an <img src=...> tag."""
    return StreamingResponse(
        _mjpeg_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
