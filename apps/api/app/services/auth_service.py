"""
AI Workspace API — Authentication Service

User lifecycle, password verification, and opaque session management.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.database import Session, User
from app.models.enums import Role


def utcnow() -> datetime:
    """Return a naive UTC timestamp, matching the database column type."""
    return datetime.now(UTC).replace(tzinfo=None)


class AuthService:
    """Business logic for users and sessions."""

    async def create_user(
        self,
        *,
        email: str,
        password: str,
        role: Role,
        db: AsyncSession,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=hash_password(password),
            role=Role(role).value,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def get_user_by_email(self, email: str, db: AsyncSession) -> User | None:
        result = await db.execute(
            select(User).where(User.email == email.strip().lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID, db: AsyncSession) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_users(self, db: AsyncSession) -> list[User]:
        result = await db.execute(select(User).order_by(User.created_at))
        return list(result.scalars().all())

    async def authenticate(
        self, email: str, password: str, db: AsyncSession
    ) -> User | None:
        user = await self.get_user_by_email(email, db)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def create_session(
        self,
        user: User,
        db: AsyncSession,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, Session]:
        token = generate_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
            ip=ip,
            user_agent=user_agent[:255] if user_agent else None,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return token, session

    async def get_user_for_token(self, token: str, db: AsyncSession) -> User | None:
        result = await db.execute(
            select(User)
            .join(Session, Session.user_id == User.id)
            .where(
                Session.token_hash == hash_token(token),
                Session.expires_at > utcnow(),
                User.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def revoke_session(self, token: str, db: AsyncSession) -> None:
        result = await db.execute(
            select(Session).where(Session.token_hash == hash_token(token))
        )
        session = result.scalar_one_or_none()
        if session is not None:
            await db.delete(session)
            await db.commit()

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        db: AsyncSession,
    ) -> bool:
        if not verify_password(current_password, user.password_hash):
            return False

        user.password_hash = hash_password(new_password)
        sessions = await db.execute(select(Session).where(Session.user_id == user.id))
        for session in sessions.scalars().all():
            await db.delete(session)
        await db.commit()
        return True

    async def update_user(
        self,
        user: User,
        *,
        role: Role | None,
        is_active: bool | None,
        db: AsyncSession,
    ) -> User:
        if role is not None:
            user.role = Role(role).value
        if is_active is not None:
            user.is_active = is_active
        await db.commit()
        await db.refresh(user)
        return user


auth_service = AuthService()
