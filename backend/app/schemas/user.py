"""User schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr

from app.db.models.user import UserRole


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str = ""
    role: UserRole = UserRole.OPERATOR
    is_active: bool = True


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
