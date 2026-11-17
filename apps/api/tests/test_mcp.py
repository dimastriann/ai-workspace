"""Tests for MCP server configuration, discovery, and tool exposure."""

import socket
import time
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.models.database import McpServer
from app.models.enums import Role
from app.models.mcp import McpToolInfo
from app.services.auth_service import auth_service
from app.services.mcp_service import mcp_service
from app.services.settings_service import settings_service

PASSWORD = "password123"


@pytest.fixture(autouse=True)
def public_dns(monkeypatch: pytest.MonkeyPatch):
    """Resolve MCP hosts to a public address without network access."""
    monkeypatch.setattr(
        "app.services.mcp_service.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )


async def _login_admin(client: AsyncClient, db: AsyncSession) -> None:
    await auth_service.create_user(
        email="admin@example.com",
        password=PASSWORD,
        role=Role.ADMIN,
        db=db,
    )
    response = await client.post(
        "/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200


async def _create_server(
    client: AsyncClient,
    *,
    name: str = "GitHub",
    url: str = "https://example.com/mcp",
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = await client.post(
        "/api/mcp/servers",
        json={
            "name": name,
            "transport": "http",
            "url": url,
            "headers": headers or {"Authorization": "Bearer super-secret-token"},
            "enabled": True,
            "timeout_seconds": 10,
            "disabled_tools": [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_mcp_server_crud_masks_and_encrypts_headers(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _login_admin(auth_client, db_session)
    created = await _create_server(auth_client)

    assert created["header_names"] == ["Authorization"]
    assert "super-secret-token" not in str(created)

    server = await db_session.get(McpServer, uuid.UUID(created["id"]))
    assert server is not None
    assert server.headers_encrypted is not None
    assert "super-secret-token" not in server.headers_encrypted
    assert mcp_service._config(server).headers["Authorization"] == (
        "Bearer super-secret-token"
    )

    listed = await auth_client.get("/api/mcp/servers")
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "GitHub"

    duplicate = await auth_client.post(
        "/api/mcp/servers",
        json={
            "name": "GitHub",
            "transport": "http",
            "url": "https://example.com/other",
        },
    )
    assert duplicate.status_code == 400

    updated = await auth_client.put(
        f"/api/mcp/servers/{created['id']}",
        json={"enabled": False, "disabled_tools": ["create_issue"]},
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False
    assert updated.json()["disabled_tools"] == ["create_issue"]

    deleted = await auth_client.delete(f"/api/mcp/servers/{created['id']}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_mcp_rejects_non_admin(
    member_client: AsyncClient,
) -> None:
    response = await member_client.get("/api/mcp/servers")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_mcp_url_validation(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _login_admin(auth_client, db_session)

    invalid = await auth_client.post(
        "/api/mcp/servers",
        json={"name": "Bad", "transport": "http", "url": "ftp://example.com"},
    )
    assert invalid.status_code == 400

    monkeypatch.setattr(app_settings, "app_env", "production")
    monkeypatch.setattr(
        "app.services.mcp_service.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
        ],
    )
    private = await auth_client.post(
        "/api/mcp/servers",
        json={"name": "Private", "transport": "http", "url": "https://127.0.0.1/mcp"},
    )
    assert private.status_code == 400


@pytest.mark.asyncio
async def test_mcp_test_endpoint_discovers_tools(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _login_admin(auth_client, db_session)
    created = await _create_server(auth_client)

    async def fake_discover(config: Any) -> list[McpToolInfo]:
        assert config.name == "GitHub"
        return [
            McpToolInfo(
                name="create_issue",
                description="Create a GitHub issue",
                input_schema={"type": "object", "properties": {}},
            )
        ]

    monkeypatch.setattr(mcp_service, "discover", fake_discover)

    response = await auth_client.post(f"/api/mcp/servers/{created['id']}/test")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["tools"][0]["name"] == "create_issue"

    server = await db_session.get(McpServer, uuid.UUID(created["id"]))
    assert server is not None
    assert server.last_status == "ok"


@pytest.mark.asyncio
async def test_mcp_tools_are_namespaced_and_respect_disabled(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _login_admin(auth_client, db_session)
    created = await _create_server(auth_client)
    await settings_service.set("features.mcp", True, db_session)

    async def fake_discover(config: Any) -> list[McpToolInfo]:
        del config
        return [
            McpToolInfo(name="create_issue", description="Create issue"),
            McpToolInfo(name="list_issues", description="List issues"),
        ]

    async def fake_call(config: Any, tool: str, arguments: dict[str, Any]) -> str:
        del config, arguments
        return f"called {tool}"

    monkeypatch.setattr(mcp_service, "discover", fake_discover)
    monkeypatch.setattr(mcp_service, "call_tool", fake_call)

    specs = await mcp_service.list_tool_specs(db_session)
    names = {spec.name for spec in specs}
    assert names == {
        "mcp__GitHub__create_issue",
        "mcp__GitHub__list_issues",
    }
    assert all(spec.permission == "mcp" for spec in specs)

    result = await specs[0].handler(db_session, uuid.uuid4(), {})
    assert result.startswith("called ")

    await auth_client.put(
        f"/api/mcp/servers/{created['id']}",
        json={"disabled_tools": ["create_issue"]},
    )
    mcp_service._cache.clear()
    specs = await mcp_service.list_tool_specs(db_session)
    assert {spec.name for spec in specs} == {"mcp__GitHub__list_issues"}


@pytest.mark.asyncio
async def test_mcp_tools_hidden_when_flag_off(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _login_admin(auth_client, db_session)
    await _create_server(auth_client)

    async def fake_discover(config: Any) -> list[McpToolInfo]:
        del config
        return [McpToolInfo(name="create_issue")]

    monkeypatch.setattr(mcp_service, "discover", fake_discover)

    assert await mcp_service.list_tool_specs(db_session) == []


@pytest.mark.asyncio
async def test_member_can_view_status_and_reconnect(
    member_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = McpServer(
        id=uuid.uuid4(),
        name="GitHub",
        transport="http",
        url="https://example.com/mcp",
        enabled=True,
        timeout_seconds=10,
        disabled_tools="[]",
    )
    db_session.add(server)
    await db_session.commit()
    mcp_service._cache[server.id] = (
        time.monotonic(),
        [McpToolInfo(name="list_issues", description="List issues")],
    )

    status = await member_client.get("/api/mcp/status")
    assert status.status_code == 200
    body = status.json()
    assert body["servers"][0]["name"] == "GitHub"
    assert body["servers"][0]["tools"][0]["name"] == "mcp__GitHub__list_issues"
    assert body["servers"][0]["tools"][0]["label"] == "list_issues"

    async def fake_discover(config: Any) -> list[McpToolInfo]:
        del config
        return [McpToolInfo(name="create_issue", description="Create issue")]

    monkeypatch.setattr(mcp_service, "discover", fake_discover)
    reconnect = await member_client.post(f"/api/mcp/servers/{server.id}/reconnect")
    assert reconnect.status_code == 200
    assert reconnect.json()["ok"] is True
    assert reconnect.json()["tools"][0]["name"] == "create_issue"
