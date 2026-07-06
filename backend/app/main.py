"""
SentinelAI FastAPI application entry point.

Wires configuration, logging, CORS, the v1 REST API, WebSocket routes, DB
bootstrap, the event bus (bound to the running loop), and a graceful shutdown
that stops all camera workers.

Run:  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.services.event_bus import event_bus
from app.websocket.routes import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} ({settings.APP_ENV})")

    # Bind the event bus to the running loop so worker threads can hand off.
    event_bus.bind_loop(asyncio.get_running_loop())

    # Ensure DB schema exists (dev convenience; prefer Alembic in prod).
    try:
        from app.db.base import init_models

        await init_models()
        await _ensure_admin_user()
    except Exception as exc:  # pragma: no cover
        logger.error(f"Database init skipped/failed: {exc}")

    yield

    # Shutdown: stop all camera workers cleanly.
    from app.services.camera import camera_manager

    logger.info("Shutting down — stopping camera workers.")
    camera_manager.stop_all()


async def _ensure_admin_user() -> None:
    """Seed a default admin account on first run (change the password!)."""
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.db.base import AsyncSessionLocal
    from app.db.models.user import User, UserRole

    async with AsyncSessionLocal() as session:
        exists = (await session.execute(
            select(User).where(User.username == "admin")
        )).scalar_one_or_none()
        if exists:
            return
        session.add(User(
            username="admin",
            # Note: use a normal TLD — EmailStr rejects reserved names like .local.
            email="admin@sentinelai.io",
            full_name="Administrator",
            hashed_password=hash_password("admin123"),
            role=UserRole.ADMIN,
        ))
        await session.commit()
        logger.warning("Seeded default admin/admin123 — CHANGE THIS PASSWORD.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version="1.0.0",
        description="AI-Based Threat Detection and Intelligent Surveillance System.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    app.include_router(ws_router)

    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "health": f"{settings.API_V1_PREFIX}/system/health",
        }

    @app.exception_handler(Exception)
    async def _unhandled(_request, exc: Exception):  # pragma: no cover
        logger.exception(f"Unhandled error: {exc}")
        return JSONResponse(status_code=500, content={"detail": "Internal error"})

    return app


app = create_app()
