"""
AI Workspace API — Document Ingestion Handler

Parses an uploaded document locally, chunks it, and stores the chunks
in Postgres. No embeddings or vector database are required.
"""

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk
from app.services.chunking import chunk_text
from app.services.parsing import extract_text


async def process_document(db: AsyncSession, payload: dict[str, Any]) -> None:
    """Handle a document ingestion job."""
    document_id = UUID(str(payload["document_id"]))
    workspace_id = UUID(str(payload["workspace_id"]))
    file_path = str(payload["file_path"])

    document = await db.get(Document, document_id)
    if document is None:
        raise ValueError(f"Document not found: {document_id}")

    try:
        data = await asyncio.to_thread(Path(file_path).read_bytes)
        text = await asyncio.to_thread(extract_text, document.filename, data)
        chunks = chunk_text(text)

        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        db.add_all(
            [
                DocumentChunk(
                    document_id=document_id,
                    workspace_id=workspace_id,
                    ordinal=index,
                    content=chunk,
                )
                for index, chunk in enumerate(chunks)
            ]
        )

        document.status = "completed"
        document.chunk_count = len(chunks)
        await db.commit()
    except Exception:
        await db.rollback()
        failed = await db.get(Document, document_id)
        if failed is not None:
            failed.status = "error"
            await db.commit()
        raise
