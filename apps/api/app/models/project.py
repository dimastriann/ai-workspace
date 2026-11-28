"""Chat project schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Create a project inside a workspace."""

    workspace_id: str
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    instructions: str = Field(default="", max_length=4000)
    memory_mode: Literal["workspace", "project"] = "workspace"


class ProjectUpdate(BaseModel):
    """Update a project; omitted fields are unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    instructions: str | None = Field(default=None, max_length=4000)
    memory_mode: Literal["workspace", "project"] | None = None


class ProjectResponse(BaseModel):
    """Project metadata."""

    id: str
    workspace_id: str
    name: str
    description: str = ""
    instructions: str = ""
    memory_mode: str = "workspace"
    session_count: int = 0
    document_count: int = 0
    created_at: datetime
    updated_at: datetime
