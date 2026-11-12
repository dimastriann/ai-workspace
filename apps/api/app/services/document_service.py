"""
AI Workspace API — Document Service

Handles business logic for document management, including file uploads,
metadata persistence, and triggering ingestion tasks.
"""

import os
import shutil
import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document
from app.services.job_service import job_service


class DocumentService:
    @staticmethod
    async def upload_document(
        workspace_id: uuid.UUID, file: UploadFile, db: AsyncSession
    ) -> Document:
        """
        Uploads a document, saves it locally, creates a DB record,
        and triggers the background ingestion task.
        """
        # 1. Create DB record
        document_id = uuid.uuid4()
        filename = os.path.basename(file.filename or "unnamed")

        # Determine document type from extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "text"

        db_doc = Document(
            id=document_id,
            workspace_id=workspace_id,
            filename=filename,
            document_type=ext,
            size_bytes=0,  # Will update after saving
            status="processing",
        )

        db.add(db_doc)
        await db.commit()
        await db.refresh(db_doc)

        # 2. Save file locally
        upload_dir = os.path.join("uploads", str(workspace_id))
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, f"{document_id}_{filename}")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Update size
        db_doc.size_bytes = os.path.getsize(file_path)
        await db.commit()

        # 3. Trigger background task
        await job_service.enqueue(
            db,
            kind="document.ingest",
            payload={
                "document_id": str(document_id),
                "workspace_id": str(workspace_id),
                "file_path": file_path,
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


# Singleton instance
document_service = DocumentService()
