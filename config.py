"""Centralized configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# === Project Root ===
BASE_DIR = Path(__file__).resolve().parent

# === OpenAI API ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# === Vector DB Settings ===
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", str(BASE_DIR / "data" / "vector_index"))

# === FastAPI Settings ===
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")

# === API Key Authentication ===
# Comma-separated list of API keys that can access the API
API_KEYS = {key.strip() for key in os.getenv("API_KEYS", "").split(",") if key.strip()}

# === File Upload Settings ===
ALLOWED_FILE_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "25"))

# === Debug Mode ===
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
