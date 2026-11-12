"""
AI Workspace API — Agent Router

Handles autonomous agent task execution with
multi-step planning and tool usage.
"""

from fastapi import APIRouter, Depends

from app.dependencies import require_member
from app.models.database import User

router = APIRouter()


@router.post("/tasks")
async def submit_agent_task(_user: User = Depends(require_member)) -> dict:
    """
    Submit a task for the AI agent to execute.

    TODO (Phase 4): Implement planning, tool selection, and streaming updates.
    """
    return {
        "status": "stub",
        "message": "Agent task endpoint — implementation coming in Phase 5",
    }


@router.get("/tasks")
async def list_agent_tasks(_user: User = Depends(require_member)) -> dict:
    """
    List all agent tasks and their statuses.

    TODO (Phase 4): Query task history from database.
    """
    return {"tasks": []}
