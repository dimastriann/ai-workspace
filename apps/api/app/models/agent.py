"""
AI Workspace API — Agent Models

Pydantic schemas for agent task requests, execution steps, and results.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    """Agent task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTaskRequest(BaseModel):
    """Request body for submitting an agent task."""

    instruction: str = Field(..., min_length=1, description="The task instruction for the agent")
    workspace_id: str | None = Field(None, description="Workspace context")
    tools: list[str] = Field(default_factory=list, description="Optional list of tools to enable")


class AgentStep(BaseModel):
    """A single step in the agent's execution plan."""

    step_number: int
    action: str
    tool_used: str | None = None
    input_data: str = ""
    output_data: str = ""
    status: TaskStatus = TaskStatus.PENDING


class AgentTaskResponse(BaseModel):
    """Response from an agent task execution."""

    task_id: str
    instruction: str
    status: TaskStatus
    steps: list[AgentStep] = Field(default_factory=list)
    result: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
