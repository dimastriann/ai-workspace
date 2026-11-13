"""
AI Workspace API — Agent Models

Pydantic schemas for agent runs, steps, and responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """Request body for starting an agent run."""

    instruction: str = Field(..., min_length=1, max_length=4000)
    workspace_id: UUID
    skill: str | None = Field(None, max_length=64)


class AgentStepResponse(BaseModel):
    """A single persisted step of an agent run."""

    ordinal: int
    kind: str
    tool_name: str | None = None
    input: str | None = None
    output: str | None = None
    status: str


class AgentRunSummary(BaseModel):
    """Summary of an agent run."""

    id: str
    instruction: str
    skill: str | None = None
    status: str
    created_at: datetime


class AgentRunDetail(AgentRunSummary):
    """Full agent run with steps and result."""

    result: str | None = None
    error: str | None = None
    steps: list[AgentStepResponse] = Field(default_factory=list)
