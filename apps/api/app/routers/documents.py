"""
AI Workspace API — Document Management Router

Endpoints for uploading, listing, and managing documents.
Integrates with DocumentService for business logic and the job queue for ingestion.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.dependencies import require_member, require_viewer
from app.models.database import User
from app.models.document import DocumentMetadata, DocumentUploadResponse
from app.services.document_service import document_service
from app.services.document_types import detect_document_type

router = APIRouter()


@router.post("/upload/{workspace_id}", response_model=DocumentUploadResponse)
async def upload_document(
    workspace_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_member),
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
            document_type=detect_document_type(db_doc.filename),
            chunk_count=0,  # Initially zero, updated by worker
            message="Document upload successful. Ingestion started.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{workspace_id}", response_model=list[DocumentMetadata])
async def list_documents(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_viewer),
):
    """List all documents in a workspace."""
    docs = await document_service.get_workspace_documents(workspace_id, db)
    return [
        DocumentMetadata(
            id=str(d.id),
            filename=d.filename,
            document_type=detect_document_type(d.filename),
            size_bytes=d.size_bytes,
            chunk_count=d.chunk_count,
            status=d.status,
            workspace_id=str(d.workspace_id),
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in docs
    ]
