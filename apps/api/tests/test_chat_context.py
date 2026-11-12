"""Tests for chat context and source attribution."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk, Workspace
from app.services.chat_service import chat_service


async def test_build_context_returns_sources(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()

    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        filename="notes.md",
        document_type="markdown",
        size_bytes=10,
        chunk_count=1,
        status="completed",
    )
    db_session.add(document)
    await db_session.commit()

    db_session.add(
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=document.id,
            workspace_id=workspace.id,
            ordinal=0,
            content="alpha beta gamma",
        )
    )
    await db_session.commit()

    context, sources = await chat_service.build_context(
        "alpha", workspace.id, db_session
    )

    assert "alpha beta gamma" in context
    assert len(sources) == 1
    assert sources[0]["filename"] == "notes.md"
    assert sources[0]["ordinal"] == 0
    assert "alpha beta" in str(sources[0]["snippet"])


async def test_build_context_empty_query(db_session: AsyncSession) -> None:
    context, sources = await chat_service.build_context("   ", uuid.uuid4(), db_session)

    assert context == ""
    assert sources == []
