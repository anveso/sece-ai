"""Simple, dependency-free text chunking with overlap.

Good enough for an MVP; swap for a token-aware splitter (e.g. one driven by
tiktoken) if chunk boundaries start cutting sentences too aggressively.
"""
from typing import List


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
    text = text.strip()
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = end - overlap

    return chunks
