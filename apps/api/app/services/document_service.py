"""
AI Workspace API — Document Service

Handles business logic for document management, including validated uploads,
metadata persistence, and triggering ingestion tasks.
"""

import asyncio
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import (
    DocumentNotFoundError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    WorkspaceNotFoundError,
)
from app.models.database import Document, DocumentChunk, Workspace
from app.services.document_types import detect_document_type
from app.services.job_service import job_service
from app.services.storage import (
    conversion_dir,
    document_file_path,
    remove_file,
    remove_tree,
)


class DocumentService:
    @staticmethod
    async def upload_document(
        workspace_id: uuid.UUID, file: UploadFile, db: AsyncSession
    ) -> Document:
        """Validate, store, register, and enqueue a document."""
        if await db.get(Workspace, workspace_id) is None:
            raise WorkspaceNotFoundError("Workspace not found")

        filename = Path(file.filename or "unnamed").name
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix not in settings.allowed_upload_extension_set:
            raise UnsupportedFileTypeError(
                f"Unsupported file type: {suffix or 'unknown'}"
            )

        max_bytes = settings.max_upload_mb * 1024 * 1024
        data = await file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise FileTooLargeError(
                f"File exceeds the {settings.max_upload_mb} MB limit"
            )

        document_id = uuid.uuid4()
        file_path = document_file_path(workspace_id, document_id, filename)
        await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(file_path.write_bytes, data)

        db_doc = Document(
            id=document_id,
            workspace_id=workspace_id,
            filename=filename,
            document_type=detect_document_type(filename),
            size_bytes=len(data),
            status="processing",
        )
        db.add(db_doc)
        await db.commit()
        await db.refresh(db_doc)

        await job_service.enqueue(
            db,
            kind="document.ingest",
            payload={
                "document_id": str(document_id),
                "workspace_id": str(workspace_id),
                "file_path": str(file_path),
            },
        )

        return db_doc

    @staticmethod
    async def get_workspace_documents(
        workspace_id: uuid.UUID, db: AsyncSession
    ) -> list[Document]:
        """Fetch all documents for a workspace."""
        result = await db.execute(
            select(Document).where(Document.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_document(document_id: uuid.UUID, db: AsyncSession) -> Document:
        """Delete a document, its chunks, and its stored files."""
        document = await db.get(Document, document_id)
        if document is None:
            raise DocumentNotFoundError("Document not found")

        file_path = document_file_path(
            document.workspace_id, document.id, document.filename
        )
        artifacts = conversion_dir(document.workspace_id, document.id)

        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await db.delete(document)
        await db.commit()

        await asyncio.to_thread(remove_file, file_path)
        await asyncio.to_thread(remove_tree, artifacts)
        return document


# Singleton instance
document_service = DocumentService()
