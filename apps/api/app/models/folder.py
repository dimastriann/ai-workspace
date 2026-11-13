"""Document folder request and response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FolderCreate(BaseModel):
    """Create a folder in a workspace."""

    workspace_id: UUID
    parent_id: UUID | None = None
    name: str = Field(..., min_length=1, max_length=255)


class FolderUpdate(BaseModel):
    """Rename or move a folder; omitted fields are unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: UUID | None = None


class FolderResponse(BaseModel):
    """Folder metadata."""

    id: str
    workspace_id: str
    parent_id: str | None = None
    name: str
    created_at: datetime
    updated_at: datetime


class FolderTree(FolderResponse):
    """Folder metadata with nested children."""

    children: list["FolderTree"] = Field(default_factory=list)


class DocumentMoveRequest(BaseModel):
    """Move a document to a folder, or to the root when null."""

    folder_id: UUID | None = None


FolderTree.model_rebuild()
