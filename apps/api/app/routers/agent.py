"""
AI Workspace API — Agent Router

Handles autonomous agent task execution with
multi-step planning and tool usage.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/tasks")
async def submit_agent_task() -> dict:
    """
    Submit a task for the AI agent to execute.

    TODO (Phase 5): Implement LangChain agent with
    tool selection, multi-step planning, and streaming updates.
    """
    return {
        "status": "stub",
        "message": "Agent task endpoint — implementation coming in Phase 5",
    }


@router.get("/tasks")
async def list_agent_tasks() -> dict:
    """
    List all agent tasks and their statuses.

    TODO (Phase 5): Query task history from database.
    """
    return {"tasks": []}
