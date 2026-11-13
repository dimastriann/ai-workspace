"""
AI Workspace API — Agent Router

Runs the agent loop over SSE and exposes run history.
"""

import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.dependencies import require_member
from app.models.agent import (
    AgentRunDetail,
    AgentRunRequest,
    AgentRunSummary,
    AgentStepResponse,
)
from app.models.database import AgentRun, User
from app.models.enums import Role, role_at_least
from app.services.agent_provider import get_provider
from app.services.agent_service import agent_service
from app.services.skills import skill_registry
from app.services.workspace_service import workspace_service

router = APIRouter()


@router.post("/runs")
async def start_run(
    data: AgentRunRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> StreamingResponse:
    """Start an agent run and stream its events."""
    workspace = await workspace_service.get_workspace(data.workspace_id, db)
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    skill = skill_registry.get(data.skill) if data.skill else None
    if data.skill and skill is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown skill"
        )

    run = AgentRun(
        id=uuid4(),
        workspace_id=data.workspace_id,
        user_id=user.id,
        skill=skill.name if skill else None,
        instruction=data.instruction,
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    async def event_generator():
        async for event in agent_service.execute_stream(
            db=db,
            run=run,
            skill=skill,
            provider=get_provider(),
        ):
            yield "data: " + json.dumps(event) + "\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "cache-control": "no-cache, no-transform",
            "x-accel-buffering": "no",
        },
    )


@router.get("/runs", response_model=list[AgentRunSummary])
async def list_runs(
    workspace_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> list[AgentRunSummary]:
    """List the current user's recent runs."""
    statement = (
        select(AgentRun)
        .where(AgentRun.user_id == user.id)
        .order_by(AgentRun.created_at.desc())
        .limit(50)
    )
    if workspace_id is not None:
        statement = statement.where(AgentRun.workspace_id == workspace_id)

    runs = (await db.execute(statement)).scalars().all()
    return [
        AgentRunSummary(
            id=str(run.id),
            instruction=run.instruction,
            skill=run.skill,
            status=run.status,
            created_at=run.created_at,
        )
        for run in runs
    ]


@router.get("/runs/{run_id}", response_model=AgentRunDetail)
async def get_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> AgentRunDetail:
    """Return a run with its persisted steps."""
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .where(AgentRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None or (
        run.user_id != user.id and not role_at_least(user.role, Role.ADMIN)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )

    return AgentRunDetail(
        id=str(run.id),
        instruction=run.instruction,
        skill=run.skill,
        status=run.status,
        created_at=run.created_at,
        result=run.result,
        error=run.error,
        steps=[
            AgentStepResponse(
                ordinal=step.ordinal,
                kind=step.kind,
                tool_name=step.tool_name,
                input=step.input,
                output=step.output,
                status=step.status,
            )
            for step in run.steps
        ],
    )
