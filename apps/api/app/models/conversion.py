"""Document conversion models."""

from datetime import datetime

from pydantic import BaseModel


class ConversionRequest(BaseModel):
    """Options for a Markdown conversion."""

    include_images: bool = False


class ConversionResponse(BaseModel):
    """Status of a document conversion."""

    id: str
    document_id: str
    status: str
    include_images: bool
    error: str | None = None
    created_at: datetime
    updated_at: datetime
