"""Simple text chunking utilities."""

import re

def simple_text_chunker(text, max_tokens=500):
    """Split *text* into roughly ``max_tokens`` sized chunks."""
    sentences = re.split(r'(?<=[.!?]) +', text)
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
