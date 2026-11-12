"""
AI Workspace API — Dependency Injection

Shared FastAPI dependencies for settings, database sessions, and auth.
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db_session
from app.models.database import User
from app.models.enums import Role, role_at_least
from app.services.auth_service import auth_service


async def get_settings():
    """Provide application settings as a dependency."""
    return settings


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Resolve the authenticated user from the session cookie."""
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user = await auth_service.get_user_for_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    return user


def require_role(required: Role) -> Callable[..., Awaitable[User]]:
    """Build a dependency that enforces a minimum role."""

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if not role_at_least(user.role, required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency


require_viewer = require_role(Role.VIEWER)
require_member = require_role(Role.MEMBER)
require_admin = require_role(Role.ADMIN)


async def require_same_origin(request: Request) -> None:
    """Reject state-changing requests from unexpected origins."""
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.cors_origin_list:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid request origin",
        )
