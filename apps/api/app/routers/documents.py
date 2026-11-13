"""
AI Workspace API — Document Management Router

Endpoints for uploading, listing, and managing documents.
Integrates with DocumentService for business logic and the job queue for ingestion.
"""

import io
import logging
import re
import zipfile
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import (
    DocumentNotFoundError,
    FileTooLargeError,
    FolderNotFoundError,
    UnsupportedFileTypeError,
    WorkspaceNotFoundError,
)
from app.dependencies import require_member, require_viewer
from app.models.conversion import ConversionRequest, ConversionResponse
from app.models.database import Document, DocumentConversion, User
from app.models.document import DocumentMetadata, DocumentUploadResponse
from app.models.folder import DocumentMoveRequest
from app.services.audit_service import audit_service
from app.services.document_service import document_service
from app.services.document_types import detect_document_type
from app.services.folder_service import folder_service
from app.services.job_service import job_service
from app.services.storage import ensure_within_uploads

logger = logging.getLogger(__name__)

router = APIRouter()


def _conversion_response(conversion: DocumentConversion) -> ConversionResponse:
    return ConversionResponse(
        id=str(conversion.id),
        document_id=str(conversion.document_id),
        status=conversion.status,
        format=conversion.format,
        include_images=conversion.include_images,
        error=conversion.error,
        created_at=conversion.created_at,
        updated_at=conversion.updated_at,
    )


def _download_stem(filename: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).stem)
    return stem or "document"


def _document_metadata(document: Document) -> DocumentMetadata:
    return DocumentMetadata(
        id=str(document.id),
        filename=document.filename,
        document_type=detect_document_type(document.filename),
        size_bytes=document.size_bytes,
        chunk_count=document.chunk_count,
        status=document.status,
        workspace_id=str(document.workspace_id),
        folder_id=str(document.folder_id) if document.folder_id else None,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


async def _latest_conversion(
    document_id: UUID, db: AsyncSession
) -> DocumentConversion | None:
    result = await db.execute(
        select(DocumentConversion)
        .where(DocumentConversion.document_id == document_id)
        .order_by(DocumentConversion.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _completed_conversion(
    document_id: UUID, db: AsyncSession
) -> tuple[Document, DocumentConversion]:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    conversion = await _latest_conversion(document_id, db)
    if conversion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversion not found"
        )
    if conversion.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Conversion not ready"
        )
    return document, conversion


def _conversion_file(path: str | None) -> Path:
    if not path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversion format not available",
        )
    try:
        resolved = ensure_within_uploads(Path(path))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversion output missing"
        ) from exc
    if not resolved.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversion output missing"
        )
    return resolved


@router.post("/upload/{workspace_id}", response_model=DocumentUploadResponse)
async def upload_document(
    workspace_id: UUID,
    file: UploadFile = File(...),
    folder_id: UUID | None = Form(None),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_member),
):
    """
    Upload a document to a specific workspace.
    Triggers asynchronous parsing and indexing.
    """
    try:
        db_doc = await document_service.upload_document(
            workspace_id, file, db, folder_id
        )
        return DocumentUploadResponse(
            document_id=str(db_doc.id),
            filename=db_doc.filename,
            document_type=detect_document_type(db_doc.filename),
            chunk_count=0,  # Initially zero, updated by worker
            message="Document upload successful. Ingestion started.",
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)
        ) from exc
    except WorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except FolderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Document upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        ) from exc


@router.get("/{workspace_id}", response_model=list[DocumentMetadata])
async def list_documents(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_viewer),
):
    """List all documents in a workspace."""
    docs = await document_service.get_workspace_documents(workspace_id, db)
    return [_document_metadata(d) for d in docs]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> Response:
    """Delete a document, its chunks, and its stored files."""
    try:
        document = await document_service.delete_document(document_id, db)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="documents.delete",
        actor_id=user.id,
        target=str(document_id),
        details={"filename": document.filename},
        ip=request.client.host if request.client else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{document_id}", response_model=DocumentMetadata)
async def move_document(
    document_id: UUID,
    data: DocumentMoveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> DocumentMetadata:
    """Move a document to a folder, or to the workspace root."""
    try:
        document = await folder_service.move_document(document_id, data.folder_id, db)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except FolderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="documents.move",
        actor_id=user.id,
        target=str(document_id),
        details={"folder_id": str(data.folder_id or "")},
        ip=request.client.host if request.client else None,
    )
    return _document_metadata(document)


@router.post(
    "/{document_id}/convert",
    response_model=ConversionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def convert_document(
    document_id: UUID,
    data: ConversionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> ConversionResponse:
    """Queue a document conversion."""
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    conversion = DocumentConversion(
        document_id=document.id,
        status="pending",
        format=data.format,
        include_images=data.include_images,
    )
    db.add(conversion)
    await db.commit()
    await db.refresh(conversion)

    await job_service.enqueue(
        db,
        kind="document.convert",
        payload={"conversion_id": str(conversion.id)},
    )
    await audit_service.record(
        db,
        action="documents.convert",
        actor_id=user.id,
        target=str(document_id),
        details={
            "format": data.format,
            "include_images": data.include_images,
            "conversion_id": str(conversion.id),
        },
        ip=request.client.host if request.client else None,
    )
    return _conversion_response(conversion)


@router.get("/{document_id}/conversion", response_model=ConversionResponse)
async def get_conversion(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_viewer),
) -> ConversionResponse:
    """Return the latest conversion for a document."""
    conversion = await _latest_conversion(document_id, db)
    if conversion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversion not found"
        )
    return _conversion_response(conversion)


@router.get("/{document_id}/markdown")
async def download_markdown(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_viewer),
) -> FileResponse:
    """Download the converted Markdown file."""
    document, conversion = await _completed_conversion(document_id, db)
    markdown_path = _conversion_file(conversion.markdown_path)
    return FileResponse(
        markdown_path,
        media_type="text/markdown",
        filename=f"{_download_stem(document.filename)}.md",
    )


@router.get("/{document_id}/json")
async def download_json(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_viewer),
) -> FileResponse:
    """Download the converted JSON file."""
    document, conversion = await _completed_conversion(document_id, db)
    json_path = _conversion_file(conversion.json_path)
    return FileResponse(
        json_path,
        media_type="application/json",
        filename=f"{_download_stem(document.filename)}.json",
    )


@router.get("/{document_id}/markdown.zip")
async def download_markdown_zip(
    document_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_viewer),
) -> Response:
    """Download the Markdown file plus extracted images as a ZIP."""
    document, conversion = await _completed_conversion(document_id, db)
    markdown_path = _conversion_file(conversion.markdown_path)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(markdown_path, "document.md")
        if conversion.json_path:
            try:
                json_path = ensure_within_uploads(Path(conversion.json_path))
            except ValueError:
                json_path = None
            if json_path is not None and json_path.is_file():
                archive.write(json_path, "document.json")
        if conversion.assets_path:
            try:
                assets = ensure_within_uploads(Path(conversion.assets_path))
            except ValueError:
                assets = None
            if assets is not None and assets.is_dir():
                for file_path in assets.rglob("*"):
                    if file_path.is_file():
                        relative = file_path.relative_to(assets).as_posix()
                        archive.write(file_path, f"assets/{relative}")

    filename = f"{_download_stem(document.filename)}.zip"
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"content-disposition": f'attachment; filename="{filename}"'},
    )
