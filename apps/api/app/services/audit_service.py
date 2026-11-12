"""
AI Workspace API — Audit Service

Append-only logging for security-relevant actions.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog


class AuditService:
    """Record audit entries for admin and security events."""

    async def record(
        self,
        db: AsyncSession,
        *,
        action: str,
        actor_id: UUID | None = None,
        target: str | None = None,
        details: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> None:
        db.add(
            AuditLog(
                actor_id=actor_id,
                action=action,
                target=target,
                details=json.dumps(details) if details else None,
                ip=ip,
            )
        )
        await db.commit()


audit_service = AuditService()
