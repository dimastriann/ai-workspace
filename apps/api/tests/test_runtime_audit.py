"""Tests for runtime forward-auth session auditing."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog
from app.services import audit_service as audit_module

MEMBER_EMAIL = "member@example.com"


async def count_access(db: AsyncSession, action: str) -> int:
    result = await db.execute(
        select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.created_at)
    )
    return len(list(result.scalars().all()))


async def test_verify_audits_runtime_access_throttled(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    first = await member_client.get("/api/auth/verify?role=member&service=terminal")
    second = await member_client.get("/api/auth/verify?role=member&service=terminal")

    assert first.status_code == 204
    assert second.status_code == 204
    assert await count_access(db_session, "runtime.terminal.access") == 1


async def test_verify_records_again_after_window(
    member_client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    await member_client.get("/api/auth/verify?role=member&service=terminal")
    monkeypatch.setattr(audit_module, "RUNTIME_ACCESS_WINDOW_SECONDS", 0)
    await member_client.get("/api/auth/verify?role=member&service=terminal")

    assert await count_access(db_session, "runtime.terminal.access") == 2


async def test_verify_without_service_is_not_audited(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    response = await member_client.get("/api/auth/verify?role=member")

    assert response.status_code == 204
    assert await count_access(db_session, "runtime.terminal.access") == 0


async def test_verify_denied_role_is_not_audited(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    response = await member_client.get("/api/auth/verify?role=admin&service=ide")

    assert response.status_code == 403
    assert await count_access(db_session, "runtime.ide.access") == 0


async def test_verify_rejects_unknown_service(member_client: AsyncClient) -> None:
    response = await member_client.get("/api/auth/verify?role=member&service=shell")

    assert response.status_code == 422
