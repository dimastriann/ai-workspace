"""Tests for the agent executor using a fake provider."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AgentRun, AgentStep, Workspace
from app.models.enums import Role
from app.models.skill import SkillManifest
from app.services.agent_provider import ProviderEvent, ToolCall
from app.services.agent_service import agent_service
from app.services.auth_service import auth_service


class FakeProvider:
    """Provider that replays a fixed list of turns."""

    def __init__(self, turns: list[list[ProviderEvent]]) -> None:
        self._turns = turns

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncGenerator[ProviderEvent]:
        del messages, tools
        for event in self._turns.pop(0):
            yield event


async def _create_run(db: AsyncSession, workspace_id: uuid.UUID) -> AgentRun:
    user = await auth_service.create_user(
        email=f"agent-{uuid.uuid4()}@example.com",
        password="password123",
        role=Role.MEMBER,
        db=db,
    )
    run = AgentRun(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=user.id,
        instruction="What is 2 + 2?",
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def test_executor_calls_tool_and_completes(
    db_session: AsyncSession,
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()
    run = await _create_run(db_session, workspace.id)

    provider = FakeProvider(
        [
            [
                ProviderEvent(
                    type="tool_calls",
                    tool_calls=[
                        ToolCall(
                            id="call-1",
                            name="calculator",
                            arguments={"expression": "2 + 2"},
                        )
                    ],
                ),
                ProviderEvent(type="done"),
            ],
            [
                ProviderEvent(type="token", content="The answer is 4.0."),
                ProviderEvent(type="done"),
            ],
        ]
    )

    events = [
        event
        async for event in agent_service.execute_stream(
            db=db_session, run=run, skill=None, provider=provider
        )
    ]

    assert any(
        event["event"] == "tool" and event["status"] == "completed" for event in events
    )
    assert any(event.get("token") == "The answer is 4.0." for event in events)

    refreshed = await db_session.get(AgentRun, run.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.result == "The answer is 4.0."

    steps = (
        (await db_session.execute(select(AgentStep).where(AgentStep.run_id == run.id)))
        .scalars()
        .all()
    )
    assert len(steps) == 1
    assert steps[0].tool_name == "calculator"
    assert steps[0].output == "4.0"


async def test_executor_blocks_tools_outside_skill(
    db_session: AsyncSession,
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()
    run = await _create_run(db_session, workspace.id)
    skill = SkillManifest(
        name="no-tools",
        description="No tools allowed",
        permissions=[],
        instructions="Answer directly.",
    )

    provider = FakeProvider(
        [
            [
                ProviderEvent(
                    type="tool_calls",
                    tool_calls=[
                        ToolCall(
                            id="call-1",
                            name="calculator",
                            arguments={"expression": "2 + 2"},
                        )
                    ],
                ),
                ProviderEvent(type="done"),
            ],
            [
                ProviderEvent(type="token", content="I cannot use tools."),
                ProviderEvent(type="done"),
            ],
        ]
    )

    events = [
        event
        async for event in agent_service.execute_stream(
            db=db_session, run=run, skill=skill, provider=provider
        )
    ]

    tool_event = next(event for event in events if event["event"] == "tool")
    assert tool_event["status"] == "error"
    assert "not available" in tool_event["output"]


async def test_executor_fails_at_max_steps(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()
    run = await _create_run(db_session, workspace.id)

    provider = FakeProvider(
        [
            [
                ProviderEvent(
                    type="tool_calls",
                    tool_calls=[
                        ToolCall(
                            id="call-1",
                            name="calculator",
                            arguments={"expression": "1 + 1"},
                        )
                    ],
                ),
                ProviderEvent(type="done"),
            ]
        ]
    )

    events = [
        event
        async for event in agent_service.execute_stream(
            db=db_session, run=run, skill=None, provider=provider, max_steps=1
        )
    ]

    assert any(event["event"] == "error" for event in events)
    refreshed = await db_session.get(AgentRun, run.id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.error == "Maximum steps reached"
