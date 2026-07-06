"""ORM models — importing here registers them on `Base.metadata`."""
from app.db.models.user import User, UserRole
from app.db.models.camera import Camera, CameraStatus
from app.db.models.event import ThreatLog
from app.db.models.zone import ZoneModel
from app.db.models.config import SystemConfig

__all__ = [
    "User", "UserRole",
    "Camera", "CameraStatus",
    "ThreatLog",
    "ZoneModel",
    "SystemConfig",
]
