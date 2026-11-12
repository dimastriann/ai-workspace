"""
Tests for the Documents router endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, Workspace


@pytest.mark.asyncio
async def test_list_documents_rejects_invalid_workspace_id(client: AsyncClient):
    """The workspace id path parameter must be a UUID."""
    response = await client.get("/api/documents/not-a-uuid")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_documents_normalizes_legacy_type(
    auth_client: AsyncClient, db_session: AsyncSession
):
    """Legacy rows with a raw extension still serialize as a valid type."""
    workspace_id = uuid.uuid4()
    db_session.add(Workspace(id=workspace_id, name="Test Workspace"))
    await db_session.commit()

    db_session.add(
        Document(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            filename="notes.md",
            document_type="md",
            size_bytes=12,
            chunk_count=0,
            status="processing",
        )
    )
    await db_session.commit()

    response = await auth_client.get(f"/api/documents/{workspace_id}")

    assert response.status_code == 200
    assert response.json()[0]["document_type"] == "markdown"
