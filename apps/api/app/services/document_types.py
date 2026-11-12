"""Map file extensions to the stored document type."""

from pathlib import Path

_DOCUMENT_TYPES: dict[str, str] = {
    ".pdf": "pdf",
    ".md": "markdown",
    ".markdown": "markdown",
    ".csv": "csv",
    ".txt": "text",
    ".json": "text",
    ".yaml": "text",
    ".yml": "text",
    ".py": "code",
    ".js": "code",
    ".jsx": "code",
    ".ts": "code",
    ".tsx": "code",
    ".rs": "code",
    ".go": "code",
    ".java": "code",
}


def detect_document_type(filename: str) -> str:
    """Return the canonical document type for a filename."""
    return _DOCUMENT_TYPES.get(Path(filename).suffix.lower(), "text")
