"""Tests for local (AI-free) document ingestion."""

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk, Workspace
from app.tasks.ingestion import process_document


async def _create_document(
    db_session: AsyncSession, filename: str
) -> tuple[Workspace, Document]:
    workspace = Workspace(id=uuid.uuid4(), name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()

    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        filename=filename,
        document_type="markdown",
        size_bytes=0,
        chunk_count=0,
        status="processing",
    )
    db_session.add(document)
    await db_session.commit()
    return workspace, document


async def test_process_document_stores_chunks_without_ai(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    workspace, document = await _create_document(db_session, "notes.md")
    file_path = tmp_path / "notes.md"
    file_path.write_text("# Title\n\nHello world.\n" * 200)

    await process_document(
        db_session,
        {
            "document_id": str(document.id),
            "workspace_id": str(workspace.id),
            "file_path": str(file_path),
        },
    )

    refreshed = await db_session.get(Document, document.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.chunk_count > 0

    result = await db_session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.ordinal)
    )
    chunks = result.scalars().all()

    assert len(chunks) == refreshed.chunk_count
    assert chunks[0].ordinal == 0
    assert "Hello world" in chunks[0].content


async def test_process_document_marks_errors(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    _, document = await _create_document(db_session, "missing.md")

    try:
        await process_document(
            db_session,
            {
                "document_id": str(document.id),
                "workspace_id": str(document.workspace_id),
                "file_path": str(tmp_path / "does-not-exist.md"),
            },
        )
    except FileNotFoundError:
        pass

    refreshed = await db_session.get(Document, document.id)
    assert refreshed is not None
    assert refreshed.status == "error"
