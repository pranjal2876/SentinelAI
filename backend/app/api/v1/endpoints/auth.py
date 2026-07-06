"""Authentication endpoints: register, login, refresh, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.base import get_db
from app.db.models.user import User
from app.schemas.auth import RegisterRequest, Token, TokenRefresh
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user account."""
    exists = (await db.execute(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.email)
        )
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(400, "Username or email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(),
                db: AsyncSession = Depends(get_db)):
    """OAuth2 password-flow login returning access + refresh tokens."""
    user = (await db.execute(
        select(User).where(User.username == form.username)
    )).scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    return Token(
        access_token=create_access_token(user.username, user.role.value),
        refresh_token=create_refresh_token(user.username),
    )


@router.post("/refresh", response_model=Token)
async def refresh(payload: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a fresh token pair."""
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    username = data.get("sub")
    user = (await db.execute(
        select(User).where(User.username == username)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User not found")
    return Token(
        access_token=create_access_token(user.username, user.role.value),
        refresh_token=create_refresh_token(user.username),
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return user
