"""Tests for conversion record persistence."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentConversion, Workspace


async def test_conversion_record_roundtrip(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()

    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        filename="report.pdf",
        document_type="pdf",
        size_bytes=10,
        chunk_count=0,
        status="completed",
    )
    db_session.add(document)
    await db_session.commit()

    conversion = DocumentConversion(
        id=uuid.uuid4(),
        document_id=document.id,
        status="pending",
        include_images=True,
    )
    db_session.add(conversion)
    await db_session.commit()

    result = await db_session.execute(
        select(DocumentConversion).where(DocumentConversion.document_id == document.id)
    )
    stored = result.scalar_one()

    assert stored.status == "pending"
    assert stored.include_images is True
    assert stored.markdown_path is None
