"""Utilities for generating text embeddings using OpenAI."""

import openai

from config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL
from logging_config import get_logger

logger = get_logger(__name__)

openai.api_key = OPENAI_API_KEY


def get_openai_embedding(text: str, model: str = OPENAI_EMBEDDING_MODEL) -> list[float]:
    """Return the embedding vector for ``text`` from the OpenAI API."""
    text_preview = text[:50] + "..." if len(text) > 50 else text
    logger.debug(f"Generating embedding for text: {text_preview} (model: {model})")

    try:
        response = openai.embeddings.create(input=text, model=model)
        embedding = response.data[0].embedding
        logger.debug(f"Successfully generated embedding (dimension: {len(embedding)})")
        return embedding
    except openai.RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded: {e}")
        raise
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating embedding: {e}", exc_info=True)
        raise
