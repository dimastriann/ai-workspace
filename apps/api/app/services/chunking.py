"""
AI Workspace API — Deterministic Chunking

Character-window chunking with overlap. No model or network calls.
"""


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks of at most ``chunk_size`` characters."""
    if not text.strip():
        return []

    size = max(1, chunk_size)
    gap = max(0, min(overlap, size - 1))
    step = size - gap

    chunks: list[str] = []
    start = 0
    total = len(text)

    while start < total:
        end = min(start + size, total)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == total:
            break
        start += step

    return chunks
