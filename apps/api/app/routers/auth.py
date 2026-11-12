"""
AI Workspace API — Auth Router

Login, logout, and current-user endpoints backed by opaque sessions.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db_session
from app.dependencies import get_current_user
from app.models.database import User
from app.models.user import LoginRequest, UserResponse
from app.services.audit_service import audit_service
from app.services.auth_service import auth_service
from app.services.user_mapping import to_user_response

router = APIRouter()


@router.post("/login", response_model=UserResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Authenticate a user and start a session."""
    user = await auth_service.authenticate(data.email, data.password, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token, _ = await auth_service.create_session(
        user,
        db,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    await audit_service.record(
        db,
        action="auth.login",
        actor_id=user.id,
        ip=request.client.host if request.client else None,
    )
    return to_user_response(user)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Revoke the current session."""
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await auth_service.revoke_session(token, db)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user."""
    return to_user_response(user)
