"""Tests for lexical retrieval."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk, Workspace
from app.services.retrieval import retrieval_service


async def test_search_returns_matching_chunks(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()

    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        filename="notes.md",
        document_type="markdown",
        size_bytes=10,
        chunk_count=2,
        status="completed",
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
                content="alpha beta gamma",
            ),
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=document.id,
                workspace_id=workspace.id,
                ordinal=1,
                content="delta epsilon",
            ),
        ]
    )
    await db_session.commit()

    results = await retrieval_service.search("alpha", workspace.id, db_session)

    assert results == ["alpha beta gamma"]


async def test_search_scopes_to_workspace(db_session: AsyncSession) -> None:
    first = Workspace(id=uuid.uuid4(), name="First")
    second = Workspace(id=uuid.uuid4(), name="Second")
    db_session.add_all([first, second])
    await db_session.commit()

    for workspace in (first, second):
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
                content="shared keyword",
            )
        )
    await db_session.commit()

    results = await retrieval_service.search("keyword", second.id, db_session)

    assert len(results) == 1


async def test_search_empty_query(db_session: AsyncSession) -> None:
    assert await retrieval_service.search("   ", uuid.uuid4(), db_session) == []
