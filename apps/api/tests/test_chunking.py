"""Tests for deterministic chunking and local text extraction."""

from app.services.chunking import chunk_text
from app.services.parsing import extract_text


def test_chunk_text_empty() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n ") == []


def test_chunk_text_short_input_is_one_chunk() -> None:
    assert chunk_text("hello world", chunk_size=100) == ["hello world"]


def test_chunk_text_overlap_produces_expected_windows() -> None:
    text = "abcdefghij"
    chunks = chunk_text(text, chunk_size=5, overlap=2)

    assert chunks == ["abcde", "defgh", "ghij"]


def test_chunk_text_stops_at_end_without_duplicate() -> None:
    chunks = chunk_text("abcdefghij", chunk_size=5, overlap=0)

    assert chunks == ["abcde", "fghij"]


def test_chunk_text_handles_overlap_larger_than_size() -> None:
    chunks = chunk_text("abcdefghij", chunk_size=4, overlap=10)

    assert chunks
    assert chunks[0] == "abcd"
    assert len(chunks) < 10


def test_extract_text_decodes_utf8() -> None:
    assert extract_text("notes.md", "héllo".encode()) == "héllo"


def test_extract_text_handles_invalid_utf8() -> None:
    text = extract_text("notes.txt", b"caf\xe9")

    assert "caf" in text
