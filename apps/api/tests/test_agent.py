"""
Tests for the Agent router endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_agent_tasks_returns_stub(client: AsyncClient):
    """GET /api/agent/tasks returns an empty task list for now."""
    response = await client.get("/api/agent/tasks")

    assert response.status_code == 200
    assert response.json() == {"tasks": []}


@pytest.mark.asyncio
async def test_submit_agent_task_returns_stub(client: AsyncClient):
    """POST /api/agent/tasks returns the placeholder status."""
    response = await client.post("/api/agent/tasks")

    assert response.status_code == 200
    assert response.json()["status"] == "stub"
