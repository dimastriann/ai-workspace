"""Workflow request and response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

MAX_WORKFLOW_STEPS = 10


class WorkflowStepInput(BaseModel):
    """One ordered workflow step."""

    instruction: str = Field(..., min_length=1, max_length=4000)
    skill: str | None = Field(default=None, max_length=64)


class WorkflowCreate(BaseModel):
    """Create a workflow with ordered steps."""

    workspace_id: UUID
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    steps: list[WorkflowStepInput] = Field(
        ..., min_length=1, max_length=MAX_WORKFLOW_STEPS
    )


class WorkflowUpdate(BaseModel):
    """Update workflow metadata and optionally replace its steps."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    steps: list[WorkflowStepInput] | None = Field(
        default=None, min_length=1, max_length=MAX_WORKFLOW_STEPS
    )


class WorkflowStepResponse(BaseModel):
    """A persisted workflow step."""

    id: str
    ordinal: int
    instruction: str
    skill: str | None = None


class WorkflowSummary(BaseModel):
    """Workflow metadata without steps."""

    id: str
    workspace_id: str
    name: str
    description: str
    step_count: int
    created_at: datetime
    updated_at: datetime


class WorkflowDetail(WorkflowSummary):
    """Workflow with its ordered steps."""

    steps: list[WorkflowStepResponse] = Field(default_factory=list)


class WorkflowRunRequest(BaseModel):
    """Optional kickoff input for a workflow run."""

    input: str = Field(default="", max_length=4000)
