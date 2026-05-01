"""
Tests for the RAG router endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rag_query(client: AsyncClient):
    """POST /api/rag/query should return a stub response."""
    response = await client.post("/api/rag/query")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stub"
