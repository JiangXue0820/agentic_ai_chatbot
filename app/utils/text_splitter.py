from __future__ import annotations

from typing import List


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks.
    """
    cleaned = (text or "").replace("\n", " ").strip()
    if not cleaned:
        return []

    chunks: List[str] = []
    start = 0
    effective_chunk = max(chunk_size, overlap + 1)

    while start < len(cleaned):
        end = min(start + effective_chunk, len(cleaned))
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(end - overlap, start + 1)

    return chunks

