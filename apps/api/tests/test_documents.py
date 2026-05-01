"""
Tests for the Documents router endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient):
    """GET /api/documents/ should return empty documents list."""
    response = await client.get("/api/documents/")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert data["documents"] == []


@pytest.mark.asyncio
async def test_get_document(client: AsyncClient):
    """GET /api/documents/{id} should return a stub response."""
    response = await client.get("/api/documents/test-doc-123")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == "test-doc-123"
