import re
from typing import Iterable, List


def simple_text_chunker(text: str, max_tokens: int = 500) -> List[str]:
    """Split text into rough chunks based on sentences."""

    sentences = re.split(r"(?<=[.!?]) +", text)
    chunks, current = [], ""
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

