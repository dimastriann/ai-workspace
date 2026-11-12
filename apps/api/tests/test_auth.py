"""
Tests for authentication, sessions, and role-based access.
"""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token
from app.models.enums import Role
from app.services.auth_service import auth_service

PASSWORD = "password123"


async def test_authenticate_valid_and_invalid(db_session: AsyncSession) -> None:
    await auth_service.create_user(
        email="User@Example.com",
        password=PASSWORD,
        role=Role.MEMBER,
        db=db_session,
    )

    user = await auth_service.authenticate("user@example.com", PASSWORD, db_session)
    assert user is not None
    assert user.email == "user@example.com"
    assert user.role == "member"

    assert (
        await auth_service.authenticate("user@example.com", "wrong", db_session) is None
    )
    assert (
        await auth_service.authenticate("missing@example.com", PASSWORD, db_session)
        is None
    )


async def test_inactive_user_cannot_authenticate(db_session: AsyncSession) -> None:
    user = await auth_service.create_user(
        email="inactive@example.com",
        password=PASSWORD,
        role=Role.MEMBER,
        db=db_session,
    )
    user.is_active = False
    await db_session.commit()

    assert (
        await auth_service.authenticate("inactive@example.com", PASSWORD, db_session)
        is None
    )


async def test_session_resolution_and_expiry(db_session: AsyncSession) -> None:
    user = await auth_service.create_user(
        email="member@example.com",
        password=PASSWORD,
        role=Role.MEMBER,
        db=db_session,
    )

    token, session = await auth_service.create_session(user, db_session)
    assert session.token_hash == hash_token(token)
    assert await auth_service.get_user_for_token(token, db_session) is not None
    assert await auth_service.get_user_for_token("not-a-token", db_session) is None

    session.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
    await db_session.commit()

    assert await auth_service.get_user_for_token(token, db_session) is None


async def test_revoke_session(db_session: AsyncSession) -> None:
    user = await auth_service.create_user(
        email="member@example.com",
        password=PASSWORD,
        role=Role.MEMBER,
        db=db_session,
    )
    token, _ = await auth_service.create_session(user, db_session)

    await auth_service.revoke_session(token, db_session)

    assert await auth_service.get_user_for_token(token, db_session) is None


async def test_change_password_revokes_sessions(db_session: AsyncSession) -> None:
    user = await auth_service.create_user(
        email="member@example.com",
        password=PASSWORD,
        role=Role.MEMBER,
        db=db_session,
    )
    token, _ = await auth_service.create_session(user, db_session)

    changed = await auth_service.change_password(
        user, PASSWORD, "new-password123", db_session
    )

    assert changed is True
    assert await auth_service.get_user_for_token(token, db_session) is None
    assert (
        await auth_service.authenticate(
            "member@example.com", "new-password123", db_session
        )
        is not None
    )


async def test_change_password_rejects_wrong_current_password(
    db_session: AsyncSession,
) -> None:
    user = await auth_service.create_user(
        email="member@example.com",
        password=PASSWORD,
        role=Role.MEMBER,
        db=db_session,
    )

    assert not await auth_service.change_password(
        user, "wrong", "new-password123", db_session
    )


async def test_login_me_logout_flow(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await auth_service.create_user(
        email="admin@example.com",
        password=PASSWORD,
        role=Role.ADMIN,
        db=db_session,
    )

    login = await auth_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": PASSWORD},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "admin"

    me = await auth_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"
    assert me.json()["is_active"] is True

    logout = await auth_client.post("/api/auth/logout")
    assert logout.status_code == 200

    after = await auth_client.get("/api/auth/me")
    assert after.status_code == 401


async def test_login_rejects_invalid_credentials(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )

    assert response.status_code == 401


async def test_me_requires_a_session(client: AsyncClient) -> None:
    response = await client.get("/api/auth/me")

    assert response.status_code == 401
