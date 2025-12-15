"""Utilities for generating text embeddings using OpenAI."""

from typing import List
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL
from logging_config import get_logger

logger = get_logger(__name__)

# Initialize OpenAI client (v1.x pattern)
client = OpenAI(api_key=OPENAI_API_KEY)


def get_openai_embedding(text: str, model: str = OPENAI_EMBEDDING_MODEL) -> List[float]:
    """Return the embedding vector for ``text`` from the OpenAI API."""
    text_preview = text[:50] + "..." if len(text) > 50 else text
    logger.debug(f"Generating embedding for text: {text_preview} (model: {model})")

    try:
        response = client.embeddings.create(input=text, model=model)
        embedding = response.data[0].embedding
        logger.debug(f"Successfully generated embedding (dimension: {len(embedding)})")
        return embedding
    except Exception as e:
        # Catch all OpenAI errors (RateLimitError, APIError, etc.)
        logger.error(f"Error generating embedding: {e}", exc_info=True)
        raise
