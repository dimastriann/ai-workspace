"""Document conversion models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ConversionFormat = Literal["markdown", "json", "both"]


class ConversionRequest(BaseModel):
    """Options for a document conversion."""

    format: ConversionFormat = "markdown"
    include_images: bool = False


class ConversionResponse(BaseModel):
    """Status of a document conversion."""

    id: str
    document_id: str
    status: str
    format: str
    include_images: bool
    error: str | None = None
    created_at: datetime
    updated_at: datetime
