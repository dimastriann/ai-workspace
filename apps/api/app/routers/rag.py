"""
AI Workspace API — RAG Router

Handles retrieval-augmented generation queries,
searching uploaded documents for relevant context
before generating answers.
"""

from fastapi import APIRouter, Depends

from app.dependencies import require_member
from app.models.database import User

router = APIRouter()


@router.post("/query")
async def rag_query(_user: User = Depends(require_member)) -> dict:
    """
    Submit a RAG query against uploaded documents.

    TODO: Replace the stub with retrieval → augmentation → generation.
    """
    return {
        "status": "stub",
        "message": "RAG query endpoint — implementation coming in Phase 2",
    }
