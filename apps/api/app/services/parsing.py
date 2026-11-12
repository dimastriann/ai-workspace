"""
AI Workspace API — Local Text Extraction

Extracts text from supported formats without external services.
"""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


def extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from a supported document."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(data)

    return data.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)
