"""Centralized configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv


def _as_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]

# Load environment variables from .env file
load_dotenv()

# === Project Root ===
BASE_DIR = Path(__file__).resolve().parent

# === OpenAI API ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable is required for Knowledge Indexer")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# === Vector DB Settings ===
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", str(BASE_DIR / "data" / "vector_index"))

# === User DB Settings ===
USER_DB_PATH = os.getenv("USER_DB_PATH", Path(BASE_DIR) / "users.db")
API_KEY_TTL_DAYS = int(os.getenv("API_KEY_TTL_DAYS", "90"))
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "12"))
REQUIRE_COMPLEX_PASSWORD = os.getenv("REQUIRE_COMPLEX_PASSWORD", "true").lower() == "true"

# === Admin Settings ===
ADMIN_USERS = _as_list(os.getenv("ADMIN_USERS", ""))  # Comma-separated list of admin usernames

# === Rate Limiting ===
DEFAULT_RATE_LIMIT = os.getenv("DEFAULT_RATE_LIMIT", "60/minute")
UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "10/minute")
QUERY_RATE_LIMIT = os.getenv("QUERY_RATE_LIMIT", "60/minute")
MANAGEMENT_RATE_LIMIT = os.getenv("MANAGEMENT_RATE_LIMIT", "30/minute")
AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "10/minute")

# MCP-specific rate limits (defaults to QUERY_RATE_LIMIT if not set)
MCP_QUERY_RATE_LIMIT = os.getenv("MCP_QUERY_RATE_LIMIT", QUERY_RATE_LIMIT)
MCP_LIST_RATE_LIMIT = os.getenv("MCP_LIST_RATE_LIMIT", QUERY_RATE_LIMIT)
MCP_RESOURCE_RATE_LIMIT = os.getenv("MCP_RESOURCE_RATE_LIMIT", QUERY_RATE_LIMIT)

# === Performance Settings ===
EMBEDDING_CONCURRENCY = int(os.getenv("EMBEDDING_CONCURRENCY", "10"))
MAX_EMBEDDING_RETRIES = int(os.getenv("MAX_EMBEDDING_RETRIES", "3"))

# === FastAPI Settings ===
CORS_ORIGINS = _as_list(os.getenv("CORS_ORIGINS", "http://localhost:8501"))

# === MIME validation ===
ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain", "text/x-markdown"},
}
MIME_VALIDATION_BYTES = int(os.getenv("MIME_VALIDATION_BYTES", "4096"))

# === File Upload Settings ===
ALLOWED_FILE_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "25"))

# === Debug Mode ===
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# === Logging Settings ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", None)  # Optional: set to enable file logging

# === Heroku/Production Settings ===
PORT = int(os.getenv("PORT", 8000))  # Heroku provides PORT env var
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 8501))
API_HOST = os.getenv("API_HOST", "http://0.0.0.0")

API_URL = os.getenv("API_URL", f"http://localhost:{PORT}").rstrip("/")
