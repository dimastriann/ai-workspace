"""Tests for saved workflows and their sequential executor."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AgentRun, AgentStep, Workspace
from app.models.enums import Role
from app.services.agent_provider import ProviderEvent
from app.services.auth_service import auth_service


class FakeProvider:
    """Replay one fixed event turn per workflow step."""

    def __init__(self, turns: list[list[ProviderEvent]]) -> None:
        self._turns = turns

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncGenerator[ProviderEvent]:
        del messages, tools
        for event in self._turns.pop(0):
            yield event


async def _workspace(db_session: AsyncSession) -> Workspace:
    workspace = Workspace(id=uuid.uuid4(), name="Workflow Test")
    db_session.add(workspace)
    await db_session.commit()
    return workspace


def _payload(workspace_id: uuid.UUID, name: str = "Research") -> dict[str, Any]:
    return {
        "workspace_id": str(workspace_id),
        "name": name,
        "description": "Two-step research workflow",
        "steps": [
            {"instruction": "Summarize the workspace documents."},
            {"instruction": "Write three recommendations.", "skill": None},
        ],
    }


@pytest.mark.asyncio
async def test_workflow_crud(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    workspace = await _workspace(db_session)

    created = await member_client.post("/api/workflows", json=_payload(workspace.id))
    assert created.status_code == 201, created.text
    workflow = created.json()
    assert workflow["name"] == "Research"
    assert workflow["step_count"] == 2
    assert [step["ordinal"] for step in workflow["steps"]] == [0, 1]

    listed = await member_client.get(
        "/api/workflows", params={"workspace_id": str(workspace.id)}
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == workflow["id"]

    fetched = await member_client.get(f"/api/workflows/{workflow['id']}")
    assert fetched.status_code == 200

    updated = await member_client.put(
        f"/api/workflows/{workflow['id']}",
        json={
            "name": "Research v2",
            "steps": [{"instruction": "Only one step now."}],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Research v2"
    assert updated.json()["step_count"] == 1

    duplicate = await member_client.post(
        "/api/workflows", json=_payload(workspace.id, "Research v2")
    )
    assert duplicate.status_code == 400

    deleted = await member_client.delete(f"/api/workflows/{workflow['id']}")
    assert deleted.status_code == 204
    assert (
        await member_client.get(f"/api/workflows/{workflow['id']}")
    ).status_code == 404


@pytest.mark.asyncio
async def test_workflow_validation(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    workspace = await _workspace(db_session)

    unknown_skill = await member_client.post(
        "/api/workflows",
        json={
            "workspace_id": str(workspace.id),
            "name": "Bad skill",
            "steps": [{"instruction": "Do it", "skill": "missing"}],
        },
    )
    assert unknown_skill.status_code == 400

    empty_steps = await member_client.post(
        "/api/workflows",
        json={
            "workspace_id": str(workspace.id),
            "name": "Empty",
            "steps": [],
        },
    )
    assert empty_steps.status_code == 422

    too_many = await member_client.post(
        "/api/workflows",
        json={
            "workspace_id": str(workspace.id),
            "name": "Too many",
            "steps": [{"instruction": f"Step {i}"} for i in range(11)],
        },
    )
    assert too_many.status_code == 422


@pytest.mark.asyncio
async def test_workflow_is_private_to_owner(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    workspace = await _workspace(db_session)
    other = await auth_service.create_user(
        email="other@example.com",
        password="password123",
        role=Role.MEMBER,
        db=db_session,
    )
    created = await member_client.post("/api/workflows", json=_payload(workspace.id))
    workflow_id = created.json()["id"]

    # Simulate another user's workflow without changing the logged-in session.
    from app.models.database import Workflow

    workflow = await db_session.get(Workflow, uuid.UUID(workflow_id))
    assert workflow is not None
    workflow.user_id = other.id
    await db_session.commit()

    assert (await member_client.get(f"/api/workflows/{workflow_id}")).status_code == 404


@pytest.mark.asyncio
async def test_workflow_run_streams_and_persists_steps(
    member_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = await _workspace(db_session)
    created = await member_client.post("/api/workflows", json=_payload(workspace.id))
    workflow_id = created.json()["id"]

    provider = FakeProvider(
        [
            [
                ProviderEvent(type="token", content="Summary ready."),
                ProviderEvent(type="done"),
            ],
            [
                ProviderEvent(type="token", content="Recommendation ready."),
                ProviderEvent(type="done"),
            ],
        ]
    )
    monkeypatch.setattr("app.routers.workflows.get_provider", lambda: provider)

    response = await member_client.post(
        f"/api/workflows/{workflow_id}/runs", json={"input": "Focus on facts"}
    )
    assert response.status_code == 200
    assert "step_completed" in response.text
    assert "done" in response.text

    run = (
        await db_session.execute(
            select(AgentRun).where(AgentRun.workflow_id == uuid.UUID(workflow_id))
        )
    ).scalar_one()
    assert run.status == "completed"
    assert "Summary ready." in (run.result or "")

    steps = (
        (
            await db_session.execute(
                select(AgentStep)
                .where(AgentStep.run_id == run.id)
                .order_by(AgentStep.ordinal)
            )
        )
        .scalars()
        .all()
    )
    tasks = [step for step in steps if step.kind == "task"]
    assert len(tasks) == 2
    assert tasks[0].output == "Summary ready."
    assert tasks[1].output == "Recommendation ready."
