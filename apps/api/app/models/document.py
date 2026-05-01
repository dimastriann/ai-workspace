"""
AI Workspace API — Document Models

Pydantic schemas for document uploads, metadata, and chunk references.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    """Supported document types."""

    PDF = "pdf"
    MARKDOWN = "markdown"
    CSV = "csv"
    CODE = "code"
    TEXT = "text"


class DocumentMetadata(BaseModel):
    """Metadata for an uploaded document."""

    id: str
    filename: str
    document_type: DocumentType
    size_bytes: int
    chunk_count: int = 0
    workspace_id: str
    created_at: datetime
    updated_at: datetime


class DocumentChunk(BaseModel):
    """A single chunk of a parsed document."""

    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: dict = Field(default_factory=dict)


class DocumentUploadResponse(BaseModel):
    """Response after a successful document upload."""

    document_id: str
    filename: str
    document_type: DocumentType
    chunk_count: int
    message: str = "Document uploaded and processed successfully"
