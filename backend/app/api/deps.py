"""
Shared FastAPI dependencies: DB session, current user, and role guards.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.db.base import get_db
from app.db.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve and validate the authenticated user from a bearer token."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exc
    username = payload.get("sub")
    if not username:
        raise credentials_exc

    user = (await db.execute(
        select(User).where(User.username == username)
    )).scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc
    return user


def require_role(*roles: UserRole):
    """Dependency factory enforcing that the user holds one of `roles`."""
    async def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _guard
