"""Aggregate all v1 REST routers under a single APIRouter."""
from fastapi import APIRouter

from app.api.v1.endpoints import analytics, auth, cameras, system, threats, zones

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cameras.router)
api_router.include_router(threats.router)
api_router.include_router(zones.router)
api_router.include_router(analytics.router)
api_router.include_router(system.router)
