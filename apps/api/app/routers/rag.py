"""
AI Workspace API — RAG Router

Handles retrieval-augmented generation queries,
searching uploaded documents for relevant context
before generating answers.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/query")
async def rag_query() -> dict:
    """
    Submit a RAG query against uploaded documents.

    TODO (Phase 2): Implement embedding → retrieval → augmentation → generation.
    """
    return {
        "status": "stub",
        "message": "RAG query endpoint — implementation coming in Phase 2",
    }
