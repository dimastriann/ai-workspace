"""Chat project endpoints, scoped to workspaces."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import ProjectNotFoundError, ProjectValidationError
from app.dependencies import require_member, require_same_origin, require_viewer
from app.models.database import User
from app.models.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.audit_service import audit_service
from app.services.project_service import project_service

router = APIRouter()


def _response(project, counts: tuple[int, int]) -> ProjectResponse:
    return ProjectResponse(
        id=str(project.id),
        workspace_id=str(project.workspace_id),
        name=project.name,
        description=project.description or "",
        instructions=project.instructions or "",
        memory_mode=project.memory_mode,
        session_count=counts[0],
        document_count=counts[1],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_viewer),
) -> list[ProjectResponse]:
    """List projects in a workspace."""
    projects = await project_service.list_projects(workspace_id, db)
    counts = await project_service.counts([project.id for project in projects], db)
    return [_response(project, counts[project.id]) for project in projects]


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
    _: None = Depends(require_same_origin),
) -> ProjectResponse:
    """Create a project in a workspace."""
    try:
        project = await project_service.create_project(data, user, db)
    except ProjectValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await audit_service.record(
        db,
        action="project.create",
        actor_id=user.id,
        target=str(project.id),
        details={"name": project.name, "memory_mode": project.memory_mode},
        ip=request.client.host if request.client else None,
    )
    counts = await project_service.counts([project.id], db)
    return _response(project, counts[project.id])


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
    _: None = Depends(require_same_origin),
) -> ProjectResponse:
    """Update a project."""
    try:
        project = await project_service.update_project(project_id, data, db)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ProjectValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await audit_service.record(
        db,
        action="project.update",
        actor_id=user.id,
        target=str(project.id),
        details={"name": project.name, "memory_mode": project.memory_mode},
        ip=request.client.host if request.client else None,
    )
    counts = await project_service.counts([project.id], db)
    return _response(project, counts[project.id])


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
    _: None = Depends(require_same_origin),
):
    """Delete a project; its sessions and documents stay in the workspace."""
    try:
        project = await project_service.delete_project(project_id, db)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    await audit_service.record(
        db,
        action="project.delete",
        actor_id=user.id,
        target=str(project.id),
        details={"name": project.name},
        ip=request.client.host if request.client else None,
    )
    return None
