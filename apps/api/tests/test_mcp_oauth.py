"""Tests for MCP OAuth flows using a fake authorization server."""

import json
import time
import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.core.security import decrypt_secret
from app.models.database import McpServer
from app.services.mcp_oauth_service import (
    McpOAuthError,
    mcp_oauth_service,
)
from app.services.mcp_service import mcp_service

ISSUER = "https://as.example.com"
REDIRECT_URI = "http://localhost:3000/api/mcp/oauth/callback"


def _install_fake_as(
    monkeypatch: pytest.MonkeyPatch, token_response: dict[str, Any]
) -> dict[str, httpx.Request]:
    """Serve discovery, registration, and token endpoints from memory."""
    seen: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/.well-known/oauth-protected-resource":
            return httpx.Response(
                200, json={"authorization_servers": [ISSUER]}, request=request
            )
        if path == "/.well-known/oauth-authorization-server":
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/authorize",
                    "token_endpoint": f"{ISSUER}/token",
                    "registration_endpoint": f"{ISSUER}/register",
                },
                request=request,
            )
        if path == "/register":
            seen["registration"] = request
            return httpx.Response(
                200,
                json={
                    "client_id": "client-123",
                    "client_secret": "client-secret-456",
                    "redirect_uris": [REDIRECT_URI],
                },
                request=request,
            )
        if path == "/token":
            seen["token"] = request
            return httpx.Response(200, json=token_response, request=request)
        return httpx.Response(404, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(mcp_oauth_service, "_client", client)
    return seen


async def _make_server(db: AsyncSession) -> McpServer:
    server = McpServer(
        id=uuid.uuid4(),
        name="GitHub OAuth",
        transport="http",
        url="https://mcp.example.com/mcp",
        enabled=True,
        timeout_seconds=10,
        disabled_tools="[]",
    )
    db.add(server)
    await db.commit()
    return server


def _authorize_url_params(url: str) -> dict[str, str]:
    return dict(part.split("=", 1) for part in url.split("?")[1].split("&"))


async def test_start_authorization_builds_url(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _install_fake_as(monkeypatch, {})
    server = await _make_server(db_session)

    url = await mcp_oauth_service.start_authorization(server, REDIRECT_URI)
    params = _authorize_url_params(url)

    assert url.startswith("https://as.example.com/authorize?")
    assert params["response_type"] == "code"
    assert params["client_id"] == "client-123"
    assert params["code_challenge_method"] == "S256"
    assert len(params["code_challenge"]) > 30
    registration = json.loads(seen["registration"].content)
    assert registration["redirect_uris"] == [REDIRECT_URI]


async def test_complete_authorization_persists_encrypted_tokens(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_as(monkeypatch, {"access_token": "at-123", "expires_in": 3600})
    server = await _make_server(db_session)

    url = await mcp_oauth_service.start_authorization(server, REDIRECT_URI)
    state = _authorize_url_params(url)["state"]
    pending = mcp_oauth_service.get_pending(state)
    assert pending is not None

    await mcp_oauth_service.complete_authorization(server, pending, "the-code")
    await db_session.commit()

    assert server.oauth_encrypted
    assert "at-123" not in server.oauth_encrypted
    decrypted = decrypt_secret(server.oauth_encrypted, app_settings.app_secret_key)
    assert "at-123" in decrypted
    bundle = mcp_oauth_service.load_bundle(server)
    assert bundle is not None
    assert bundle["client_id"] == "client-123"
    assert bundle["token_endpoint"] == f"{ISSUER}/token"
    # The state is single-use.
    assert mcp_oauth_service.get_pending(state) is None


async def test_unknown_state_is_rejected(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_as(monkeypatch, {})
    server = await _make_server(db_session)

    with pytest.raises(McpOAuthError):
        await mcp_oauth_service.complete_authorization(server, None, "code")  # type: ignore[arg-type]


async def test_refresh_grant_rotates_tokens(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _install_fake_as(
        monkeypatch, {"access_token": "new", "refresh_token": "rt-789"}
    )
    server = await _make_server(db_session)
    mcp_oauth_service.persist_tokens(
        server,
        client_id="client-123",
        client_secret=None,
        token_endpoint=f"{ISSUER}/token",
        tokens={"access_token": "old", "refresh_token": "rt-456"},
    )
    bundle = mcp_oauth_service.load_bundle(server)
    assert bundle is not None

    assert await mcp_oauth_service.refresh(server, bundle) is True

    form = seen["token"].content.decode()
    assert "grant_type=refresh_token" in form
    assert mcp_oauth_service.load_bundle(server)["access_token"] == "new"


async def test_bearer_token_merged_into_config(db_session: AsyncSession) -> None:
    server = await _make_server(db_session)
    mcp_oauth_service.persist_tokens(
        server,
        client_id="client-123",
        client_secret=None,
        token_endpoint=f"{ISSUER}/token",
        tokens={"access_token": "at-merged", "expires_in": 3600},
    )

    config = mcp_service._config(server)

    assert config.headers["Authorization"] == "Bearer at-merged"
    bundle = mcp_oauth_service.load_bundle(server)
    assert bundle is not None
    assert mcp_oauth_service.bundle_expired(bundle) is False


async def test_expired_bundle_detected(db_session: AsyncSession) -> None:
    server = await _make_server(db_session)
    mcp_oauth_service.persist_tokens(
        server,
        client_id="client-123",
        client_secret=None,
        token_endpoint=f"{ISSUER}/token",
        tokens={"access_token": "at", "expires_in": 3600},
    )
    bundle = mcp_oauth_service.load_bundle(server)
    assert bundle is not None

    bundle["expires_at"] = time.time() - 10

    assert mcp_oauth_service.bundle_expired(bundle) is True
