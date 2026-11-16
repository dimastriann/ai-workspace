"""Saved workflow CRUD and sequential run streaming."""

import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import (
    WorkflowNotFoundError,
    WorkflowValidationError,
    WorkspaceNotFoundError,
)
from app.dependencies import require_member
from app.models.database import AgentRun, User, Workflow
from app.models.workflow import (
    WorkflowCreate,
    WorkflowDetail,
    WorkflowRunRequest,
    WorkflowStepResponse,
    WorkflowSummary,
    WorkflowUpdate,
)
from app.services.agent_provider import get_provider
from app.services.audit_service import audit_service
from app.services.workflow_executor import workflow_executor
from app.services.workflow_service import workflow_service

router = APIRouter()


def _summary(workflow: Workflow) -> WorkflowSummary:
    return WorkflowSummary(
        id=str(workflow.id),
        workspace_id=str(workflow.workspace_id),
        name=workflow.name,
        description=workflow.description or "",
        step_count=len(workflow.steps),
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


def _detail(workflow: Workflow) -> WorkflowDetail:
    summary = _summary(workflow)
    return WorkflowDetail(
        **summary.model_dump(),
        steps=[
            WorkflowStepResponse(
                id=str(step.id),
                ordinal=step.ordinal,
                instruction=step.instruction,
                skill=step.skill,
            )
            for step in workflow.steps
        ],
    )


@router.get("", response_model=list[WorkflowSummary])
async def list_workflows(
    workspace_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> list[WorkflowSummary]:
    """List the current user's workflows in a workspace."""
    try:
        workflows = await workflow_service.list_workflows(workspace_id, user, db)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return [_summary(workflow) for workflow in workflows]


@router.post("", response_model=WorkflowDetail, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> WorkflowDetail:
    """Create a workflow with ordered steps."""
    try:
        workflow = await workflow_service.create_workflow(data, user, db)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except WorkflowValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="workflows.create",
        actor_id=user.id,
        target=str(workflow.id),
        details={"name": workflow.name, "steps": len(workflow.steps)},
        ip=request.client.host if request.client else None,
    )
    return _detail(workflow)


@router.get("/{workflow_id}", response_model=WorkflowDetail)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> WorkflowDetail:
    """Return a workflow with its steps."""
    try:
        workflow = await workflow_service.get_workflow(workflow_id, user, db)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _detail(workflow)


@router.put("/{workflow_id}", response_model=WorkflowDetail)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> WorkflowDetail:
    """Update workflow metadata and optionally replace its steps."""
    try:
        workflow = await workflow_service.update_workflow(workflow_id, data, user, db)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except WorkflowValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="workflows.update",
        actor_id=user.id,
        target=str(workflow.id),
        details={"name": workflow.name, "steps": len(workflow.steps)},
        ip=request.client.host if request.client else None,
    )
    return _detail(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
):
    """Delete a workflow and its steps."""
    try:
        workflow = await workflow_service.delete_workflow(workflow_id, user, db)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="workflows.delete",
        actor_id=user.id,
        target=str(workflow.id),
        details={"name": workflow.name},
        ip=request.client.host if request.client else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{workflow_id}/runs")
async def start_workflow_run(
    workflow_id: UUID,
    data: WorkflowRunRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> StreamingResponse:
    """Run all workflow steps sequentially and stream events."""
    try:
        workflow = await workflow_service.get_workflow(workflow_id, user, db)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    run = AgentRun(
        id=uuid4(),
        workspace_id=workflow.workspace_id,
        user_id=user.id,
        workflow_id=workflow.id,
        skill=None,
        instruction=(data.input or workflow.name)[:4000],
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    async def event_generator():
        async for event in workflow_executor.execute_stream(
            db=db,
            run=run,
            workflow=workflow,
            provider=get_provider(),
            user_input=data.input,
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
