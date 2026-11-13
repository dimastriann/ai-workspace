"""Tests for the rate limiter and middleware."""

import pytest
from httpx import AsyncClient

from app.config import settings
from app.core.rate_limit import InMemoryRateLimiter


def test_limiter_allows_up_to_limit() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.allow("key", 2, 60)
    assert limiter.allow("key", 2, 60)
    assert not limiter.allow("key", 2, 60)


def test_limiter_is_keyed() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.allow("first", 1, 60)
    assert limiter.allow("second", 1, 60)
    assert not limiter.allow("first", 1, 60)


async def test_login_returns_429_after_limit(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_auth", 2)

    credentials = {"email": "nobody@example.com", "password": "wrong"}

    assert (
        await auth_client.post("/api/auth/login", json=credentials)
    ).status_code != 429
    assert (
        await auth_client.post("/api/auth/login", json=credentials)
    ).status_code != 429

    response = await auth_client.post("/api/auth/login", json=credentials)

    assert response.status_code == 429
    assert response.headers["retry-after"] == str(settings.rate_limit_window_seconds)


async def test_health_is_never_rate_limited(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_api", 1)

    for _ in range(3):
        assert (await client.get("/health")).status_code == 200
