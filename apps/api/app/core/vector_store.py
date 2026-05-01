"""
AI Workspace API — Vector Store Client

Qdrant client wrapper for managing document embeddings
with workspace-isolated collections.
"""

from qdrant_client import QdrantClient

from app.config import settings

# ── Qdrant Client ────────────────────────────────────────────────────────
qdrant_client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key or None,
)


def get_collection_name(workspace_id: str) -> str:
    """
    Generate a Qdrant collection name for a given workspace.

    Each workspace has its own isolated vector collection
    to prevent cross-contamination of search results.
    """
    return f"workspace_{workspace_id}"
