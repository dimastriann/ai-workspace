"""Tests for document type detection."""

import pytest

from app.services.document_types import detect_document_type


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("report.pdf", "pdf"),
        ("notes.md", "markdown"),
        ("NOTES.MARKDOWN", "markdown"),
        ("data.csv", "csv"),
        ("readme.txt", "text"),
        ("config.yaml", "text"),
        ("main.py", "code"),
        ("app.tsx", "code"),
        ("lib.rs", "code"),
        ("archive.zip", "text"),
    ],
)
def test_detect_document_type(filename: str, expected: str) -> None:
    assert detect_document_type(filename) == expected
