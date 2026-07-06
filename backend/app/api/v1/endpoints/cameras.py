"""Camera CRUD + lifecycle (start/stop) endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.base import get_db
from app.db.models.camera import Camera, CameraStatus
from app.db.models.user import User, UserRole
from app.db.models.zone import ZoneModel
from app.schemas.camera import CameraCreate, CameraOut, CameraUpdate
from app.services.camera import camera_manager
from app.vision.threat import Zone, ZoneType

router = APIRouter(prefix="/cameras", tags=["cameras"])


async def _load_zones(db: AsyncSession, camera_id: str) -> List[Zone]:
    rows = (await db.execute(
        select(ZoneModel).where(ZoneModel.camera_id == camera_id,
                                ZoneModel.enabled == True)  # noqa: E712
    )).scalars().all()
    zones = []
    for r in rows:
        zones.append(Zone(
            id=r.zone_id, name=r.name, type=ZoneType(r.type),
            points=[tuple(p) for p in r.points],
            allowed_direction=tuple(r.allowed_direction) if r.allowed_direction else None,
            enabled=r.enabled,
        ))
    return zones


@router.get("", response_model=List[CameraOut])
async def list_cameras(db: AsyncSession = Depends(get_db),
                       _: User = Depends(get_current_user)):
    """List all configured cameras, reflecting live runtime status/fps."""
    cams = (await db.execute(select(Camera))).scalars().all()
    runtimes = {r.camera_id: r for r in camera_manager.runtimes()}
    for c in cams:
        rt = runtimes.get(c.camera_id)
        if rt:
            c.status = CameraStatus(rt.status) if rt.status in CameraStatus._value2member_map_ else c.status
            c.fps = rt.fps
    return cams


@router.post("", response_model=CameraOut, status_code=201)
async def create_camera(payload: CameraCreate, db: AsyncSession = Depends(get_db),
                        _: User = Depends(require_role(UserRole.OPERATOR))):
    """Register a new camera."""
    exists = (await db.execute(
        select(Camera).where(Camera.camera_id == payload.camera_id)
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(400, "camera_id already exists")
    cam = Camera(**payload.model_dump())
    db.add(cam)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.patch("/{camera_id}", response_model=CameraOut)
async def update_camera(camera_id: str, payload: CameraUpdate,
                        db: AsyncSession = Depends(get_db),
                        _: User = Depends(require_role(UserRole.OPERATOR))):
    cam = (await db.execute(
        select(Camera).where(Camera.camera_id == camera_id)
    )).scalar_one_or_none()
    if not cam:
        raise HTTPException(404, "Camera not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cam, k, v)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(camera_id: str, db: AsyncSession = Depends(get_db),
                        _: User = Depends(require_role(UserRole.OPERATOR))):
    cam = (await db.execute(
        select(Camera).where(Camera.camera_id == camera_id)
    )).scalar_one_or_none()
    if not cam:
        raise HTTPException(404, "Camera not found")
    camera_manager.stop_camera(camera_id)
    await db.delete(cam)
    await db.commit()


@router.post("/{camera_id}/start", status_code=202)
async def start_camera(camera_id: str, db: AsyncSession = Depends(get_db),
                       _: User = Depends(require_role(UserRole.OPERATOR))):
    """Spin up the capture + inference worker for a camera."""
    cam = (await db.execute(
        select(Camera).where(Camera.camera_id == camera_id)
    )).scalar_one_or_none()
    if not cam:
        raise HTTPException(404, "Camera not found")
    zones = await _load_zones(db, camera_id)
    camera_manager.start_camera(cam.camera_id, cam.name, cam.source, zones)
    cam.status = CameraStatus.CONNECTING
    await db.commit()
    return {"status": "starting", "camera_id": camera_id}


@router.post("/{camera_id}/stop", status_code=202)
async def stop_camera(camera_id: str, db: AsyncSession = Depends(get_db),
                      _: User = Depends(require_role(UserRole.OPERATOR))):
    """Stop a running camera worker."""
    camera_manager.stop_camera(camera_id)
    cam = (await db.execute(
        select(Camera).where(Camera.camera_id == camera_id)
    )).scalar_one_or_none()
    if cam:
        cam.status = CameraStatus.OFFLINE
        await db.commit()
    return {"status": "stopping", "camera_id": camera_id}
