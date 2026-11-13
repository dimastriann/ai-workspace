"""Tests for agent run and step persistence."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import AgentRun, AgentStep, Workspace
from app.models.enums import Role
from app.services.auth_service import auth_service


async def test_agent_run_with_ordered_steps(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()

    user = await auth_service.create_user(
        email="agent@example.com",
        password="password123",
        role=Role.MEMBER,
        db=db_session,
    )

    run = AgentRun(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        skill="summarize",
        instruction="Summarize the docs",
        status="running",
    )
    db_session.add(run)
    await db_session.commit()

    db_session.add_all(
        [
            AgentStep(
                id=uuid.uuid4(),
                run_id=run.id,
                ordinal=1,
                kind="tool",
                tool_name="calculator",
                status="completed",
            ),
            AgentStep(
                id=uuid.uuid4(),
                run_id=run.id,
                ordinal=0,
                kind="tool",
                tool_name="search_documents",
                status="completed",
            ),
        ]
    )
    await db_session.commit()

    result = await db_session.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .where(AgentRun.id == run.id)
    )
    refreshed = result.scalar_one()

    assert refreshed.skill == "summarize"
    assert [step.ordinal for step in refreshed.steps] == [0, 1]
    assert refreshed.steps[0].tool_name == "search_documents"
