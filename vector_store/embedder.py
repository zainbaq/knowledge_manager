"""Utilities for generating text embeddings using OpenAI."""

import os
import openai
from dotenv import load_dotenv
from config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL

openai.api_key = OPENAI_API_KEY

def get_openai_embedding(text, model=OPENAI_EMBEDDING_MODEL):
    """Return the embedding vector for ``text`` from the OpenAI API."""
    response = openai.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding
