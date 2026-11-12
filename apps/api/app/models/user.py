"""
AI Workspace API — Auth Models

Pydantic schemas for users, login, and role management.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Role


class UserCreate(BaseModel):
    """Request body for creating a user."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: Role = Role.MEMBER


class UserResponse(BaseModel):
    """Public user representation."""

    id: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    """Login credentials."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserUpdate(BaseModel):
    """Admin updates to a user account."""

    role: Role | None = None
    is_active: bool | None = None


class PasswordChangeRequest(BaseModel):
    """Self-service password change."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
