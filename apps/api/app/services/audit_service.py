"""
AI Workspace API — Audit Service

Append-only logging for security-relevant actions.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog

RUNTIME_ACCESS_WINDOW_SECONDS = 300


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

    async def record_throttled(
        self,
        db: AsyncSession,
        *,
        action: str,
        actor_id: UUID,
        window_seconds: int | None = None,
        target: str | None = None,
        details: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> bool:
        """Record an entry unless one exists for (action, actor) within the window.

        Returns whether an entry was recorded. Used for high-frequency signals
        such as reverse-proxy forward-auth checks, where every proxied request
        would otherwise flood the audit log.
        """
        window = window_seconds or RUNTIME_ACCESS_WINDOW_SECONDS
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=window)
        recent = await db.scalar(
            select(AuditLog.id).where(
                AuditLog.action == action,
                AuditLog.actor_id == actor_id,
                AuditLog.created_at > since,
            )
        )
        if recent:
            return False

        await self.record(
            db, action=action, actor_id=actor_id, target=target, details=details, ip=ip
        )
        return True


audit_service = AuditService()
