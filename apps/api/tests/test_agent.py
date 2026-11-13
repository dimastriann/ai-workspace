"""Tests for agent run endpoints."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Workspace


async def test_agent_runs_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/agents/runs")).status_code == 401


async def test_list_runs_empty(member_client: AsyncClient) -> None:
    response = await member_client.get("/api/agents/runs")

    assert response.status_code == 200
    assert response.json() == []


async def test_start_run_rejects_unknown_workspace(
    member_client: AsyncClient,
) -> None:
    response = await member_client.post(
        "/api/agents/runs",
        json={"instruction": "hello", "workspace_id": str(uuid.uuid4())},
    )

    assert response.status_code == 404


async def test_start_run_rejects_unknown_skill(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()

    response = await member_client.post(
        "/api/agents/runs",
        json={
            "instruction": "hello",
            "workspace_id": str(workspace.id),
            "skill": "missing",
        },
    )

    assert response.status_code == 400
