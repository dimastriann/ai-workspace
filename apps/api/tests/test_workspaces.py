"""Tests for workspace listing and document counts."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, Workspace


async def test_list_workspaces_with_documents(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()

    db_session.add(
        Document(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            filename="notes.md",
            document_type="markdown",
            size_bytes=5,
            chunk_count=0,
            status="processing",
        )
    )
    await db_session.commit()

    listed = await member_client.get("/api/workspaces/")

    assert listed.status_code == 200
    assert listed.json()[0]["document_count"] == 1

    detail = await member_client.get(f"/api/workspaces/{workspace.id}")

    assert detail.status_code == 200
    assert detail.json()["document_count"] == 1
