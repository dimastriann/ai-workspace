"""Tests for authorization on data routes."""

import uuid

from httpx import AsyncClient


async def test_data_routes_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/workspaces/")).status_code == 401
    assert (
        await client.post("/api/chat/stream", json={"message": "hi"})
    ).status_code == 401
    assert (await client.get("/api/agent/tasks")).status_code == 401


async def test_viewer_can_read_workspaces(viewer_client: AsyncClient) -> None:
    response = await viewer_client.get("/api/workspaces/")

    assert response.status_code == 200


async def test_viewer_cannot_upload(viewer_client: AsyncClient) -> None:
    response = await viewer_client.post(
        f"/api/documents/upload/{uuid.uuid4()}",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 403


async def test_member_can_create_workspace(member_client: AsyncClient) -> None:
    response = await member_client.post(
        "/api/workspaces/", json={"name": "Test Workspace", "description": ""}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Test Workspace"
