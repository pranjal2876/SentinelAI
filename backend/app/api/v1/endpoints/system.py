"""System/health endpoints."""
from __future__ import annotations

import platform
import time

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models.user import User
from app.services.camera import camera_manager
from app.vision.detection.detector import resolve_device

router = APIRouter(prefix="/system", tags=["system"])
_START = time.time()


@router.get("/health")
async def health():
    """Liveness probe (unauthenticated)."""
    return {"status": "ok", "uptime_s": round(time.time() - _START, 1)}


@router.get("/info")
async def info(_: User = Depends(get_current_user)):
    """Runtime environment + configuration summary."""
    return {
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "version": "1.0.0",
        "device": resolve_device(settings.DEVICE),
        "yolo_model": settings.YOLO_MODEL,
        "tracker": settings.TRACKER,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "active_cameras": len(camera_manager.runtimes()),
    }
