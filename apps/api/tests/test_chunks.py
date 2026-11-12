"""Tests for document chunk persistence."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk, Workspace


async def test_chunks_are_stored_per_workspace(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()

    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        filename="notes.md",
        document_type="markdown",
        size_bytes=10,
        chunk_count=0,
        status="processing",
    )
    db_session.add(document)
    await db_session.commit()

    db_session.add_all(
        [
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=document.id,
                workspace_id=workspace.id,
                ordinal=0,
                content="first chunk",
            ),
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=document.id,
                workspace_id=workspace.id,
                ordinal=1,
                content="second chunk",
            ),
        ]
    )
    await db_session.commit()

    result = await db_session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.workspace_id == workspace.id)
        .order_by(DocumentChunk.ordinal)
    )
    chunks = result.scalars().all()

    assert [chunk.content for chunk in chunks] == ["first chunk", "second chunk"]
