"""
Analytics service — aggregate threat statistics for the dashboard and reports.
"""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.camera import Camera, CameraStatus
from app.db.models.event import ThreatLog
from app.schemas.analytics import (
    CategoryCount,
    DashboardStats,
    SeverityCount,
    TimeBucket,
)


async def get_dashboard_stats(session: AsyncSession) -> DashboardStats:
    """Compute the headline dashboard statistics."""
    now = time.time()
    start_of_day = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).timestamp()

    total = (await session.execute(
        select(func.count(ThreatLog.id))
    )).scalar_one()

    today = (await session.execute(
        select(func.count(ThreatLog.id)).where(ThreatLog.timestamp >= start_of_day)
    )).scalar_one()

    cat_rows = (await session.execute(
        select(ThreatLog.category, func.count(ThreatLog.id))
        .group_by(ThreatLog.category)
    )).all()
    by_category = [CategoryCount(category=c, count=n) for c, n in cat_rows]

    sev_rows = (await session.execute(
        select(ThreatLog.severity, func.count(ThreatLog.id))
        .group_by(ThreatLog.severity)
    )).all()
    by_severity = [SeverityCount(severity=s, count=n) for s, n in sev_rows]

    cam_rows = (await session.execute(
        select(ThreatLog.camera_id, func.count(ThreatLog.id))
        .group_by(ThreatLog.camera_id)
    )).all()
    by_camera = {cid: n for cid, n in cam_rows}

    total_cams = (await session.execute(
        select(func.count(Camera.id))
    )).scalar_one()
    active_cams = (await session.execute(
        select(func.count(Camera.id)).where(Camera.status == CameraStatus.ONLINE)
    )).scalar_one()

    # 24-hour hourly timeline.
    since = now - 24 * 3600
    tl_rows = (await session.execute(
        select(ThreatLog.timestamp).where(ThreatLog.timestamp >= since)
    )).scalars().all()
    buckets: Counter = Counter()
    for ts in tl_rows:
        hour = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:00")
        buckets[hour] += 1
    timeline = [TimeBucket(bucket=b, count=c) for b, c in sorted(buckets.items())]

    return DashboardStats(
        total_threats=total,
        threats_today=today,
        active_cameras=active_cams,
        total_cameras=total_cams,
        by_category=by_category,
        by_severity=by_severity,
        by_camera=by_camera,
        timeline=timeline,
    )


async def fetch_threats(
    session: AsyncSession,
    camera_id: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    start: Optional[float] = None,
    end: Optional[float] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[ThreatLog]:
    """Query threat logs with flexible filters, newest first."""
    stmt = select(ThreatLog)
    if camera_id:
        stmt = stmt.where(ThreatLog.camera_id == camera_id)
    if category:
        stmt = stmt.where(ThreatLog.category == category)
    if severity:
        stmt = stmt.where(ThreatLog.severity == severity)
    if start is not None:
        stmt = stmt.where(ThreatLog.timestamp >= start)
    if end is not None:
        stmt = stmt.where(ThreatLog.timestamp <= end)
    if acknowledged is not None:
        stmt = stmt.where(ThreatLog.acknowledged == acknowledged)
    stmt = stmt.order_by(ThreatLog.timestamp.desc()).limit(limit).offset(offset)
    return list((await session.execute(stmt)).scalars().all())
