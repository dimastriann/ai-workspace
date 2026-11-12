"""Tests for admin settings, user management, and audit logging."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog
from app.models.enums import Role
from app.services.auth_service import auth_service

PASSWORD = "password123"


async def _create_and_login(
    client: AsyncClient,
    db: AsyncSession,
    *,
    email: str,
    role: Role,
    password: str = PASSWORD,
) -> None:
    await auth_service.create_user(email=email, password=password, role=role, db=db)
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200


async def test_settings_require_admin(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_and_login(
        auth_client, db_session, email="member@example.com", role=Role.MEMBER
    )

    response = await auth_client.get("/api/settings")

    assert response.status_code == 403


async def test_admin_can_update_and_read_settings(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_and_login(
        auth_client, db_session, email="admin@example.com", role=Role.ADMIN
    )

    update = await auth_client.put(
        "/api/settings/features.qdrant", json={"value": True}
    )
    assert update.status_code == 200
    assert update.json()["value"] is True

    settings = await auth_client.get("/api/settings")
    assert settings.status_code == 200
    assert settings.json()["features.qdrant"] is True

    public = await auth_client.get("/api/settings/public")
    assert public.status_code == 200
    assert public.json()["features.qdrant"] is True


async def test_secret_setting_is_masked(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_and_login(
        auth_client, db_session, email="admin@example.com", role=Role.ADMIN
    )

    update = await auth_client.put(
        "/api/settings/llm.openai_api_key", json={"value": "sk-secret"}
    )
    assert update.status_code == 200
    assert update.json()["value"] == "********"

    settings = await auth_client.get("/api/settings")
    assert settings.json()["llm.openai_api_key"] == "********"


async def test_settings_reject_unknown_key_and_wrong_type(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_and_login(
        auth_client, db_session, email="admin@example.com", role=Role.ADMIN
    )

    unknown = await auth_client.put("/api/settings/nope", json={"value": True})
    assert unknown.status_code == 404

    wrong_type = await auth_client.put(
        "/api/settings/features.qdrant", json={"value": "yes"}
    )
    assert wrong_type.status_code == 400


async def test_admin_can_manage_users(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_and_login(
        auth_client, db_session, email="admin@example.com", role=Role.ADMIN
    )

    created = await auth_client.post(
        "/api/users",
        json={
            "email": "viewer@example.com",
            "password": PASSWORD,
            "role": "viewer",
        },
    )
    assert created.status_code == 201
    viewer_id = created.json()["id"]
    assert created.json()["role"] == "viewer"

    listed = await auth_client.get("/api/users")
    assert listed.status_code == 200
    assert {user["email"] for user in listed.json()} == {
        "admin@example.com",
        "viewer@example.com",
    }

    updated = await auth_client.patch(
        f"/api/users/{viewer_id}", json={"role": "member"}
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "member"

    duplicate = await auth_client.post(
        "/api/users",
        json={
            "email": "viewer@example.com",
            "password": PASSWORD,
            "role": "viewer",
        },
    )
    assert duplicate.status_code == 409


async def test_member_cannot_manage_users(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_and_login(
        auth_client, db_session, email="member@example.com", role=Role.MEMBER
    )

    assert (await auth_client.get("/api/users")).status_code == 403
    assert (
        await auth_client.post(
            "/api/users",
            json={
                "email": "new@example.com",
                "password": PASSWORD,
                "role": "viewer",
            },
        )
    ).status_code == 403


async def test_password_change_revokes_sessions(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_and_login(
        auth_client, db_session, email="member@example.com", role=Role.MEMBER
    )

    changed = await auth_client.post(
        "/api/users/me/password",
        json={"current_password": PASSWORD, "new_password": "new-password123"},
    )
    assert changed.status_code == 200

    assert (await auth_client.get("/api/auth/me")).status_code == 401

    old_login = await auth_client.post(
        "/api/auth/login", json={"email": "member@example.com", "password": PASSWORD}
    )
    assert old_login.status_code == 401

    new_login = await auth_client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": "new-password123"},
    )
    assert new_login.status_code == 200


async def test_admin_actions_are_audited(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_and_login(
        auth_client, db_session, email="admin@example.com", role=Role.ADMIN
    )

    await auth_client.put("/api/settings/features.redis", json={"value": True})

    result = await db_session.execute(select(AuditLog))
    actions = {entry.action for entry in result.scalars().all()}
    assert "auth.login" in actions
    assert "settings.update" in actions
