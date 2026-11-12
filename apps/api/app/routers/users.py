"""
AI Workspace API — Users Router

Admin user management and self-service password changes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.dependencies import (
    get_current_user,
    require_admin,
    require_same_origin,
)
from app.models.database import User
from app.models.user import (
    PasswordChangeRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.audit_service import audit_service
from app.services.auth_service import auth_service
from app.services.user_mapping import to_user_response

router = APIRouter()


@router.get("", response_model=list[UserResponse])
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> list[UserResponse]:
    """List all users."""
    users = await auth_service.list_users(db)
    return [to_user_response(user) for user in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_same_origin),
) -> UserResponse:
    """Create a user with a role."""
    if await auth_service.get_user_by_email(data.email, db) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists",
        )

    user = await auth_service.create_user(
        email=data.email,
        password=data.password,
        role=data.role,
        db=db,
    )
    await audit_service.record(
        db,
        action="users.create",
        actor_id=admin.id,
        target=str(user.id),
        details={"role": user.role},
        ip=request.client.host if request.client else None,
    )
    return to_user_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_same_origin),
) -> UserResponse:
    """Update a user's role or active status."""
    user = await auth_service.get_user_by_id(user_id, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    updated = await auth_service.update_user(
        user,
        role=data.role,
        is_active=data.is_active,
        db=db,
    )
    await audit_service.record(
        db,
        action="users.update",
        actor_id=admin.id,
        target=str(updated.id),
        details={"role": updated.role, "is_active": updated.is_active},
        ip=request.client.host if request.client else None,
    )
    return to_user_response(updated)


@router.post("/me/password")
async def change_password(
    data: PasswordChangeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_same_origin),
) -> dict[str, str]:
    """Change the current user's password and revoke their sessions."""
    changed = await auth_service.change_password(
        user, data.current_password, data.new_password, db
    )
    if not changed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    await audit_service.record(
        db,
        action="users.password_change",
        actor_id=user.id,
        target=str(user.id),
        ip=request.client.host if request.client else None,
    )
    return {"status": "ok"}
