"""
Security utilities: password hashing and JWT access/refresh tokens.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Return a bcrypt hash for the given plaintext password."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


# --------------------------------------------------------------------------- #
# JSON Web Tokens
# --------------------------------------------------------------------------- #
def _create_token(subject: str, expires: timedelta, token_type: str,
                  extra: Optional[dict[str, Any]] = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str, role: str = "operator") -> str:
    """Create a short-lived access token."""
    return _create_token(
        subject,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
        {"role": role},
    )


def create_refresh_token(subject: str) -> str:
    """Create a long-lived refresh token."""
    return _create_token(
        subject,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
    )


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT. Returns payload dict or None if invalid."""
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        return None
