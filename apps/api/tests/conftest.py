"""
AI Workspace API — Test Fixtures

Shared pytest fixtures for the test suite.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db_session
from app.main import app
from app.models.database import Base
from app.models.enums import Role
from app.services.auth_service import auth_service

MEMBER_EMAIL = "member@example.com"
VIEWER_EMAIL = "viewer@example.com"
TEST_PASSWORD = "password123"


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """In-memory SQLite session with the full schema."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def auth_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """HTTP client whose database dependency uses the SQLite session."""

    async def override_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _create_and_login(
    client: AsyncClient, db_session: AsyncSession, email: str, role: Role
) -> None:
    await auth_service.create_user(
        email=email, password=TEST_PASSWORD, role=role, db=db_session
    )
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200


@pytest_asyncio.fixture
async def member_client(
    auth_client: AsyncClient, db_session: AsyncSession
) -> AsyncGenerator[AsyncClient]:
    await _create_and_login(auth_client, db_session, MEMBER_EMAIL, Role.MEMBER)
    yield auth_client


@pytest_asyncio.fixture
async def viewer_client(
    auth_client: AsyncClient, db_session: AsyncSession
) -> AsyncGenerator[AsyncClient]:
    await _create_and_login(auth_client, db_session, VIEWER_EMAIL, Role.VIEWER)
    yield auth_client
