"""
AI Workspace API — Workspace Models

Pydantic schemas for workspace management.
Each workspace provides an isolated knowledge base.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    """Request body for creating a new workspace."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""


class WorkspaceResponse(BaseModel):
    """Workspace metadata response."""

    id: str
    name: str
    description: str
    document_count: int = 0
    created_at: datetime
    updated_at: datetime
