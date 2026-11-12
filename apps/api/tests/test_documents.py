"""
Tests for the Documents router endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_documents_rejects_invalid_workspace_id(client: AsyncClient):
    """The workspace id path parameter must be a UUID."""
    response = await client.get("/api/documents/not-a-uuid")

    assert response.status_code == 422
