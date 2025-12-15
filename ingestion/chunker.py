"""Simple text chunking utilities."""

import re
from typing import Iterable, List

def simple_text_chunker(text: str, max_tokens: int = 500) -> list[str]:
    """Split *text* into roughly ``max_tokens`` sized chunks."""
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) < max_tokens:
            current += sentence + " "
        else:
            chunks.append(current.strip())
            current = sentence + " "
    if current:
        chunks.append(current.strip())
    return chunks


def token_text_chunker(text: str, max_tokens: int = 500) -> Iterable[str]:
    """Yield chunks of roughly ``max_tokens`` words using whitespace tokens."""

    tokens = text.split()
    for i in range(0, len(tokens), max_tokens):
        yield " ".join(tokens[i : i + max_tokens])

