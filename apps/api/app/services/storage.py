"""
AI Workspace API — Upload Storage Paths

Central helpers for document files and conversion artifacts.
"""

import shutil
from pathlib import Path
from uuid import UUID

UPLOADS_ROOT = Path("uploads")


def document_file_path(workspace_id: UUID, document_id: UUID, filename: str) -> Path:
    """Path of the original uploaded document."""
    return UPLOADS_ROOT / str(workspace_id) / f"{document_id}_{filename}"


def conversion_dir(workspace_id: UUID, document_id: UUID) -> Path:
    """Directory holding Markdown output and extracted assets."""
    return UPLOADS_ROOT / str(workspace_id) / "converted" / str(document_id)


def ensure_within_uploads(path: Path) -> Path:
    """Resolve a path and reject anything outside the uploads root."""
    root = UPLOADS_ROOT.resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path escapes uploads root: {path}")
    return resolved


def remove_file(path: Path) -> None:
    """Best-effort removal of a file inside the uploads root."""
    try:
        ensure_within_uploads(path).unlink(missing_ok=True)
    except (OSError, ValueError):
        pass


def remove_tree(path: Path) -> None:
    """Best-effort removal of a directory inside the uploads root."""
    try:
        resolved = ensure_within_uploads(path)
    except ValueError:
        return
    if resolved.is_dir():
        shutil.rmtree(resolved, ignore_errors=True)
