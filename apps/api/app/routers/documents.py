"""
AI Workspace API — Document Management Router

Endpoints for uploading, listing, and managing documents.
Integrates with DocumentService for business logic and Taskiq for ingestion.
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.document_service import document_service
from app.models.document import DocumentUploadResponse, DocumentMetadata


router = APIRouter()


@router.post("/upload/{workspace_id}", response_model=DocumentUploadResponse)
async def upload_document(
    workspace_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Upload a document to a specific workspace.
    Triggers asynchronous parsing and indexing.
    """
    try:
        db_doc = await document_service.upload_document(workspace_id, file, db)
        return DocumentUploadResponse(
            document_id=str(db_doc.id),
            filename=db_doc.filename,
            document_type=db_doc.document_type,
            chunk_count=0, # Initially zero, updated by worker
            message="Document upload successful. Ingestion started."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{workspace_id}", response_model=List[DocumentMetadata])
async def list_documents(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """List all documents in a workspace."""
    docs = await document_service.get_workspace_documents(workspace_id, db)
    return [
        DocumentMetadata(
            id=str(d.id),
            filename=d.filename,
            document_type=d.document_type,
            size_bytes=d.size_bytes,
            chunk_count=d.chunk_count,
            workspace_id=str(d.workspace_id),
            created_at=d.created_at,
            updated_at=d.updated_at
        )
        for d in docs
    ]
