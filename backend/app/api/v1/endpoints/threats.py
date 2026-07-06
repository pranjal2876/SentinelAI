"""Threat log query, acknowledgement, and explanation endpoints."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models.event import ThreatLog
from app.db.models.user import User
from app.schemas.threat import ThreatExplanation, ThreatOut
from app.services.analytics import fetch_threats
from app.vision.explain import explain_threat
from app.vision.types import (
    ThreatCategory,
    ThreatEvent,
    ThreatSeverity,
)

router = APIRouter(prefix="/threats", tags=["threats"])


@router.get("", response_model=List[ThreatOut])
async def list_threats(
    camera_id: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    start: Optional[float] = None,
    end: Optional[float] = None,
    acknowledged: Optional[bool] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Query threat logs with flexible filters (newest first)."""
    return await fetch_threats(
        db, camera_id, category, severity, start, end,
        acknowledged, limit, offset,
    )


@router.get("/{threat_id}", response_model=ThreatOut)
async def get_threat(threat_id: int, db: AsyncSession = Depends(get_db),
                     _: User = Depends(get_current_user)):
    row = await db.get(ThreatLog, threat_id)
    if not row:
        raise HTTPException(404, "Threat not found")
    return row


@router.post("/{threat_id}/acknowledge", response_model=ThreatOut)
async def acknowledge(threat_id: int, db: AsyncSession = Depends(get_db),
                      _: User = Depends(get_current_user)):
    """Mark a threat as reviewed/acknowledged by an operator."""
    row = await db.get(ThreatLog, threat_id)
    if not row:
        raise HTTPException(404, "Threat not found")
    row.acknowledged = True
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/{threat_id}/explain", response_model=ThreatExplanation)
async def explain(threat_id: int, db: AsyncSession = Depends(get_db),
                  _: User = Depends(get_current_user)):
    """Return a structured, human-readable explanation of why a threat fired."""
    row = await db.get(ThreatLog, threat_id)
    if not row:
        raise HTTPException(404, "Threat not found")
    event = ThreatEvent(
        category=ThreatCategory(row.category),
        score=row.score,
        camera_id=row.camera_id,
        timestamp=row.timestamp,
        message=row.message,
        track_ids=row.track_ids or [],
        metadata=row.event_metadata or {},
    )
    # Severity is derived from score inside ThreatEvent, matching stored value.
    _ = ThreatSeverity.from_score(row.score)
    return explain_threat(event)
