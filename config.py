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

# === User DB Settings ===
USER_DB_PATH = os.getenv("USER_DB_PATH", Path(BASE_DIR) / "users.db")

# === FastAPI Settings ===
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")

# === File Upload Settings ===
ALLOWED_FILE_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "25"))

# === Debug Mode ===
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# === Heroku/Production Settings ===
PORT = int(os.getenv("PORT", 8000))  # Heroku provides PORT env var
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 8501))
API_HOST = os.getenv("API_HOST", "http://0.0.0.0")

API_URL = os.getenv("API_URL", f"http://localhost:{PORT}").rstrip("/")