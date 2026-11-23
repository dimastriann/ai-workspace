"""Tests for the stdio MCP transport."""

import sys
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import McpServer
from app.services.mcp_service import mcp_service
from app.services.settings_service import settings_service
from tests.test_mcp import _login_admin

FIXTURE_SERVER = Path(__file__).parent / "fixtures" / "mini_mcp_server.py"


async def _create_stdio_server(
    client: AsyncClient,
    *,
    name: str = "Mini",
    command: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> dict:
    response = await client.post(
        "/api/mcp/servers",
        json={
            "name": name,
            "transport": "stdio",
            "command": command or [sys.executable, str(FIXTURE_SERVER)],
            "env": env or {},
            "enabled": True,
            "timeout_seconds": 30,
            "disabled_tools": [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_stdio_requires_flag(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _login_admin(auth_client, db_session)

    response = await auth_client.post(
        "/api/mcp/servers",
        json={"name": "Mini", "transport": "stdio", "command": ["echo", "hi"]},
    )
    assert response.status_code == 400
    assert "features.mcp_stdio" in response.json()["detail"]


@pytest.mark.asyncio
async def test_stdio_create_masks_env_and_stores_command(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _login_admin(auth_client, db_session)
    await settings_service.set("features.mcp_stdio", True, db_session)

    created = await _create_stdio_server(
        auth_client, env={"MINI_TOKEN": "super-secret-env"}
    )

    assert created["command"] == [sys.executable, str(FIXTURE_SERVER)]
    assert created["env_names"] == ["MINI_TOKEN"]
    assert "super-secret-env" not in str(created)

    server = await db_session.get(McpServer, uuid.UUID(created["id"]))
    assert server is not None
    assert server.env_encrypted is not None
    assert "super-secret-env" not in server.env_encrypted


@pytest.mark.asyncio
async def test_stdio_rejects_invalid_command(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _login_admin(auth_client, db_session)
    await settings_service.set("features.mcp_stdio", True, db_session)

    for command in ([], ["", "x"], [f"a{chr(0)}b"]):
        response = await auth_client.post(
            "/api/mcp/servers",
            json={"name": "Bad", "transport": "stdio", "command": command},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_stdio_round_trip_discover_and_call(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _login_admin(auth_client, db_session)
    await settings_service.set("features.mcp_stdio", True, db_session)

    created = await _create_stdio_server(auth_client)

    tested = await auth_client.post(f"/api/mcp/servers/{created['id']}/test")
    assert tested.status_code == 200
    body = tested.json()
    assert body["ok"] is True, body.get("error")
    assert [tool["name"] for tool in body["tools"]] == ["echo"]

    server = await db_session.get(McpServer, uuid.UUID(created["id"]))
    assert server is not None
    config = mcp_service._config(server)
    output = await mcp_service.call_tool(config, "echo", {"text": "hello"})
    assert output == "echo: hello"


@pytest.mark.asyncio
async def test_stdio_tools_skipped_when_flag_off(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    server = McpServer(
        id=uuid.uuid4(),
        name="Mini",
        transport="stdio",
        url="",
        command='["echo"]',
        enabled=True,
        timeout_seconds=10,
        disabled_tools="[]",
    )
    db_session.add(server)
    await db_session.commit()

    specs = await mcp_service.list_tool_specs(db_session)
    assert specs == []
