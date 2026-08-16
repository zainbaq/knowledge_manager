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
# Deliberately not raised at import time: config is imported by migration
# scripts, tests and tooling that never call OpenAI, and an import-time raise
# makes those impossible to run. The API surface enforces it instead - see
# require_openai_api_key(), called from the app's startup lifespan - so a
# misconfigured deployment still fails fast and loudly at boot.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def require_openai_api_key() -> str:
    """Return the configured OpenAI key, or raise if the app cannot serve."""
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is required for Knowledge Manager"
        )
    return OPENAI_API_KEY


# === Vector DB Settings ===
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", str(BASE_DIR / "data" / "vector_index"))
# Per-user private stores live under {VECTOR_DB_PATH}/{USER_STORE_PREFIX}/{users.id}.
# Defined here rather than in vector_store so migration tooling can import it
# without pulling in chromadb.
USER_STORE_PREFIX = "u"

# === User DB Settings ===
USER_DB_PATH = os.getenv("USER_DB_PATH", Path(BASE_DIR) / "users.db")
API_KEY_TTL_DAYS = int(os.getenv("API_KEY_TTL_DAYS", "90"))
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "12"))
REQUIRE_COMPLEX_PASSWORD = os.getenv("REQUIRE_COMPLEX_PASSWORD", "true").lower() == "true"

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
_cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000")
CORS_ORIGINS = ["*"] if _cors_env.strip() == "*" else _as_list(_cors_env)

# === AWS Cognito Settings ===
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "")
COGNITO_REGION = os.getenv("COGNITO_REGION", "")
# Auto-detect region from user pool ID if not explicitly set
if not COGNITO_REGION and COGNITO_USER_POOL_ID:
    COGNITO_REGION = COGNITO_USER_POOL_ID.split("_")[0]
COGNITO_ENABLED = bool(COGNITO_USER_POOL_ID and COGNITO_REGION)

# Other apps' Cognito App Client IDs that are trusted to call this API on
# behalf of their own signed-in users (e.g. Promethean AI forwarding its
# user's Cognito token instead of a separate KM login). Every app in the
# estate shares one user pool, so without this a token is only ever bound to
# THIS app's own client - see api/cognito.py's client-id/aud check, which is
# what actually enforces the trust boundary; jose's own audience check is
# disabled precisely because it only supports one fixed value, not a set.
# Comma-separated, additive to COGNITO_CLIENT_ID - leave empty to keep this
# API reachable only via its own frontend, exactly as before this existed.
COGNITO_TRUSTED_CLIENT_IDS = {COGNITO_CLIENT_ID} | set(
    _as_list(os.getenv("COGNITO_TRUSTED_CLIENT_IDS", ""))
)
COGNITO_TRUSTED_CLIENT_IDS.discard("")

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

# === Server Settings ===
PORT = int(os.getenv("PORT", 8000))
API_HOST = os.getenv("API_HOST", "0.0.0.0")
