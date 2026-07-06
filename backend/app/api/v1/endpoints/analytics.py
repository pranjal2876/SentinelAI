"""Analytics + report export endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models.user import User
from app.schemas.analytics import DashboardStats
from app.services.analytics import fetch_threats, get_dashboard_stats
from app.services.reports import build_excel_report, build_pdf_report

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(db: AsyncSession = Depends(get_db),
                    _: User = Depends(get_current_user)):
    """Aggregate stats for the dashboard landing view."""
    return await get_dashboard_stats(db)


@router.get("/report")
async def report(
    start: float,
    end: float,
    camera_id: str | None = None,
    fmt: str = Query("pdf", pattern="^(pdf|xlsx)$"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Export a threat report over a time window as PDF or Excel."""
    threats = await fetch_threats(
        db, camera_id=camera_id, start=start, end=end, limit=5000
    )
    if fmt == "xlsx":
        data = build_excel_report(threats)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "sentinelai_report.xlsx"
    else:
        data = build_pdf_report(threats)
        media = "application/pdf"
        filename = "sentinelai_report.pdf"

    return StreamingResponse(
        iter([data]),
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
