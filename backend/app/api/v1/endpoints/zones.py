"""Zone CRUD — restricted areas, tripwires, directional corridors, counting lines."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.base import get_db
from app.db.models.user import UserRole
from app.db.models.zone import ZoneModel
from app.schemas.zone import ZoneCreate, ZoneOut, ZoneUpdate
from app.services.camera import camera_manager
from app.vision.threat import Zone, ZoneType

router = APIRouter(prefix="/zones", tags=["zones"])


async def _sync_worker_zones(db: AsyncSession, camera_id: str) -> None:
    """Push the camera's current enabled zones into its live worker."""
    rows = (await db.execute(
        select(ZoneModel).where(ZoneModel.camera_id == camera_id,
                                ZoneModel.enabled == True)  # noqa: E712
    )).scalars().all()
    zones = [
        Zone(id=r.zone_id, name=r.name, type=ZoneType(r.type),
             points=[tuple(p) for p in r.points],
             allowed_direction=tuple(r.allowed_direction) if r.allowed_direction else None,
             enabled=r.enabled)
        for r in rows
    ]
    camera_manager.update_zones(camera_id, zones)


@router.get("", response_model=List[ZoneOut])
async def list_zones(camera_id: str | None = None,
                     db: AsyncSession = Depends(get_db),
                     _=Depends(require_role(UserRole.VIEWER))):
    stmt = select(ZoneModel)
    if camera_id:
        stmt = stmt.where(ZoneModel.camera_id == camera_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=ZoneOut, status_code=201)
async def create_zone(payload: ZoneCreate, db: AsyncSession = Depends(get_db),
                      _=Depends(require_role(UserRole.OPERATOR))):
    exists = (await db.execute(
        select(ZoneModel).where(ZoneModel.zone_id == payload.zone_id)
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(400, "zone_id already exists")
    zone = ZoneModel(
        zone_id=payload.zone_id, camera_id=payload.camera_id, name=payload.name,
        type=payload.type, points=[list(p) for p in payload.points],
        allowed_direction=list(payload.allowed_direction) if payload.allowed_direction else None,
        enabled=payload.enabled,
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    await _sync_worker_zones(db, payload.camera_id)
    return zone


@router.patch("/{zone_id}", response_model=ZoneOut)
async def update_zone(zone_id: str, payload: ZoneUpdate,
                      db: AsyncSession = Depends(get_db),
                      _=Depends(require_role(UserRole.OPERATOR))):
    zone = (await db.execute(
        select(ZoneModel).where(ZoneModel.zone_id == zone_id)
    )).scalar_one_or_none()
    if not zone:
        raise HTTPException(404, "Zone not found")
    data = payload.model_dump(exclude_unset=True)
    if "points" in data and data["points"] is not None:
        data["points"] = [list(p) for p in data["points"]]
    if "allowed_direction" in data and data["allowed_direction"] is not None:
        data["allowed_direction"] = list(data["allowed_direction"])
    for k, v in data.items():
        setattr(zone, k, v)
    await db.commit()
    await db.refresh(zone)
    await _sync_worker_zones(db, zone.camera_id)
    return zone


@router.delete("/{zone_id}", status_code=204)
async def delete_zone(zone_id: str, db: AsyncSession = Depends(get_db),
                      _=Depends(require_role(UserRole.OPERATOR))):
    zone = (await db.execute(
        select(ZoneModel).where(ZoneModel.zone_id == zone_id)
    )).scalar_one_or_none()
    if not zone:
        raise HTTPException(404, "Zone not found")
    camera_id = zone.camera_id
    await db.delete(zone)
    await db.commit()
    await _sync_worker_zones(db, camera_id)
