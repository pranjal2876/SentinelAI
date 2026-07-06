"""
Seed demo data — a sample webcam camera and a restricted zone — so the
dashboard has something to show immediately after a fresh install.

Run from the backend/ directory (so `app` is importable) with the backend
DB reachable:

    cd backend && python ../scripts/seed_demo.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the backend package importable regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db.base import AsyncSessionLocal, init_models  # noqa: E402
from app.db.models.camera import Camera  # noqa: E402
from app.db.models.zone import ZoneModel  # noqa: E402


async def main() -> None:
    await init_models()
    async with AsyncSessionLocal() as session:
        cam = (await session.execute(
            select(Camera).where(Camera.camera_id == "demo-cam")
        )).scalar_one_or_none()
        if not cam:
            session.add(Camera(
                camera_id="demo-cam", name="Demo Webcam",
                source="0", location="Lab", enabled=True,
            ))
            print("Added camera 'demo-cam' (source=0).")

        zone = (await session.execute(
            select(ZoneModel).where(ZoneModel.zone_id == "demo-restricted")
        )).scalar_one_or_none()
        if not zone:
            session.add(ZoneModel(
                zone_id="demo-restricted", camera_id="demo-cam",
                name="Restricted Area", type="restricted",
                points=[[0.35, 0.35], [0.65, 0.35], [0.65, 0.75], [0.35, 0.75]],
                enabled=True,
            ))
            print("Added restricted zone 'demo-restricted'.")

        await session.commit()
    print("Seed complete. Start the camera from the dashboard.")


if __name__ == "__main__":
    asyncio.run(main())
