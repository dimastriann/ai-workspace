"""
AI Workspace API — Settings Admin Router

Admin-only settings management plus a public feature-flag endpoint.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.dependencies import require_admin, require_same_origin
from app.models.database import User
from app.services.audit_service import audit_service
from app.services.settings_service import SECRET_MASK, settings_service

router = APIRouter()


class SettingUpdate(BaseModel):
    """New value for a setting."""

    value: bool | int | str


def _mask(key: str, value: Any) -> Any:
    if settings_service.spec(key).is_secret:
        return SECRET_MASK if value else ""
    return value


@router.get("/public")
async def public_settings(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Expose feature flags without authentication."""
    return await settings_service.public_flags(db)


@router.get("")
async def get_settings(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return all settings, masking secret values."""
    values = await settings_service.get_all(db)
    return {key: _mask(key, value) for key, value in values.items()}


@router.put("/{key}")
async def update_setting(
    key: str,
    data: SettingUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_same_origin),
) -> dict[str, Any]:
    """Update a setting value and audit the change."""
    try:
        value = await settings_service.set(key, data.value, db, updated_by=admin.id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="settings.update",
        actor_id=admin.id,
        target=key,
        ip=request.client.host if request.client else None,
    )
    return {"key": key, "value": _mask(key, value)}
