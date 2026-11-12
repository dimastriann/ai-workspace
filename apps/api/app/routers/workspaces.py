"""
AI Workspace API — Workspace Router

Endpoints for workspace life-cycle management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.dependencies import require_member, require_viewer
from app.models.database import User
from app.models.workspace import WorkspaceCreate, WorkspaceResponse
from app.services.workspace_service import workspace_service

router = APIRouter()


@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    data: WorkspaceCreate,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_member),
):
    """Create a new workspace."""
    ws = await workspace_service.create_workspace(data, db)
    return WorkspaceResponse(
        id=str(ws.id),
        name=ws.name,
        description=ws.description or "",
        document_count=0,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.get("/", response_model=list[WorkspaceResponse])
async def list_workspaces(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_viewer),
):
    """List all workspaces."""
    workspaces = await workspace_service.list_workspaces(db)
    return [
        WorkspaceResponse(
            id=str(ws.id),
            name=ws.name,
            description=ws.description or "",
            document_count=len(ws.documents),
            created_at=ws.created_at,
            updated_at=ws.updated_at,
        )
        for ws in workspaces
    ]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_viewer),
):
    """Get workspace details."""
    ws = await workspace_service.get_workspace(workspace_id, db)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return WorkspaceResponse(
        id=str(ws.id),
        name=ws.name,
        description=ws.description or "",
        document_count=len(ws.documents),
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )
