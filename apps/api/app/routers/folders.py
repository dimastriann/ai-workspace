"""Document folder endpoints."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import (
    FolderConflictError,
    FolderNotFoundError,
    WorkspaceNotFoundError,
)
from app.dependencies import require_member, require_viewer
from app.models.database import DocumentFolder, User
from app.models.folder import FolderCreate, FolderResponse, FolderTree, FolderUpdate
from app.services.audit_service import audit_service
from app.services.folder_service import folder_service

router = APIRouter()


def _folder_response(folder: DocumentFolder) -> FolderResponse:
    return FolderResponse(
        id=str(folder.id),
        workspace_id=str(folder.workspace_id),
        parent_id=str(folder.parent_id) if folder.parent_id else None,
        name=folder.name,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


@router.get("/{workspace_id}", response_model=list[FolderTree])
async def list_folders(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_viewer),
) -> list[FolderTree]:
    """Return the folder tree for a workspace."""
    try:
        return await folder_service.list_folders(workspace_id, db)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    data: FolderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> FolderResponse:
    """Create a folder in a workspace."""
    try:
        folder = await folder_service.create_folder(data, db)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except FolderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except FolderConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="folders.create",
        actor_id=user.id,
        target=str(folder.id),
        details={"name": folder.name, "parent_id": str(folder.parent_id or "")},
        ip=request.client.host if request.client else None,
    )
    return _folder_response(folder)


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: UUID,
    data: FolderUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> FolderResponse:
    """Rename or move a folder."""
    try:
        folder = await folder_service.update_folder(folder_id, data, db)
    except FolderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except FolderConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="folders.update",
        actor_id=user.id,
        target=str(folder.id),
        details={
            "name": folder.name,
            "parent_id": str(folder.parent_id or ""),
        },
        ip=request.client.host if request.client else None,
    )
    return _folder_response(folder)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: UUID,
    request: Request,
    strategy: Literal["reject", "move_parent"] = Query("reject"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> Response:
    """Delete a folder; optionally move its contents to the parent first."""
    try:
        folder = await folder_service.delete_folder(folder_id, strategy, db)
    except FolderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except FolderConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="folders.delete",
        actor_id=user.id,
        target=str(folder.id),
        details={"name": folder.name, "strategy": strategy},
        ip=request.client.host if request.client else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
