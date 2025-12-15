"""MCP error codes and models for deterministic error handling."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class MCPErrorCode(str, Enum):
    """Deterministic error codes for MCP retry logic.

    These codes enable AI agents to make intelligent decisions about:
    - Whether to retry a request
    - How long to wait before retrying
    - Whether to adjust parameters
    - Whether to request user intervention
    """

    # Authentication Errors (401) - Retry with valid credentials
    MISSING_API_KEY = "auth.missing_api_key"
    INVALID_API_KEY = "auth.invalid_api_key"
    EXPIRED_API_KEY = "auth.expired_api_key"

    # Authorization Errors (403) - Don't retry, need different permissions
    INSUFFICIENT_PERMISSIONS = "auth.insufficient_permissions"
    CORPUS_NOT_APPROVED = "auth.corpus_not_approved"
    ADMIN_REQUIRED = "auth.admin_required"

    # Validation Errors (422) - Fix parameters and retry
    INVALID_COLLECTION_NAME = "validation.invalid_collection_name"
    INVALID_FILENAME = "validation.invalid_filename"
    INVALID_USERNAME = "validation.invalid_username"
    EMPTY_QUERY = "validation.empty_query"
    INVALID_CORPUS_ID = "validation.invalid_corpus_id"
    NO_VALID_FILES = "validation.no_valid_files"
    INVALID_QUERY_LENGTH = "validation.invalid_query_length"
    INVALID_N_RESULTS = "validation.invalid_n_results"

    # File Errors (413, 415) - Adjust file and retry
    FILE_TOO_LARGE = "file.too_large"
    UNSUPPORTED_FILE_TYPE = "file.unsupported_type"
    INVALID_MIME_TYPE = "file.invalid_mime"

    # Rate Limiting (429) - Backoff and retry
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    EMBEDDING_RATE_LIMIT = "rate_limit.embedding_api"

    # Resource Errors (404) - Resource doesn't exist
    COLLECTION_NOT_FOUND = "resource.collection_not_found"
    CORPUS_NOT_FOUND = "resource.corpus_not_found"
    USER_NOT_FOUND = "resource.user_not_found"
    VERSION_NOT_FOUND = "resource.version_not_found"

    # Server Errors (500) - Retry with exponential backoff
    INTERNAL_ERROR = "server.internal_error"
    DATABASE_ERROR = "server.database_error"
    CHROMADB_ERROR = "server.chromadb_error"
    OPENAI_API_ERROR = "server.openai_api_error"

    # Unknown/Unclassified
    UNKNOWN_ERROR = "error.unknown"


class MCPErrorResponse(BaseModel):
    """MCP-compatible error response with retry guidance."""

    error_code: MCPErrorCode
    detail: str
    http_status: int
    retry_after: Optional[int] = None  # Seconds to wait before retry
    context: Optional[dict] = None  # Additional error context

    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "rate_limit.exceeded",
                "detail": "Rate limit exceeded. Please slow down and try again.",
                "http_status": 429,
                "retry_after": 60,
                "context": {"limit": "30/minute", "reset_at": 1640000000},
            }
        }


def to_mcp_error_code(status_code: int, detail: str) -> MCPErrorCode:
    """Map HTTP status code and detail message to MCP error code.

    Args:
        status_code: HTTP status code
        detail: Error detail message

    Returns:
        MCPErrorCode: Corresponding MCP error code

    This function uses pattern matching on the detail message to determine
    the specific error code, enabling AI agents to understand the exact
    failure reason and respond appropriately.
    """
    detail_lower = detail.lower()

    # 401 Unauthorized
    if status_code == 401:
        if "missing" in detail_lower and "api" in detail_lower:
            return MCPErrorCode.MISSING_API_KEY
        elif "expired" in detail_lower:
            return MCPErrorCode.EXPIRED_API_KEY
        else:
            return MCPErrorCode.INVALID_API_KEY

    # 403 Forbidden
    elif status_code == 403:
        if "admin" in detail_lower:
            return MCPErrorCode.ADMIN_REQUIRED
        elif "approved" in detail_lower:
            return MCPErrorCode.CORPUS_NOT_APPROVED
        else:
            return MCPErrorCode.INSUFFICIENT_PERMISSIONS

    # 404 Not Found
    elif status_code == 404:
        if "collection" in detail_lower:
            return MCPErrorCode.COLLECTION_NOT_FOUND
        elif "corpus" in detail_lower:
            return MCPErrorCode.CORPUS_NOT_FOUND
        elif "user" in detail_lower:
            return MCPErrorCode.USER_NOT_FOUND
        elif "version" in detail_lower:
            return MCPErrorCode.VERSION_NOT_FOUND
        else:
            return MCPErrorCode.COLLECTION_NOT_FOUND  # Default for 404

    # 413 Payload Too Large
    elif status_code == 413:
        return MCPErrorCode.FILE_TOO_LARGE

    # 415 Unsupported Media Type
    elif status_code == 415:
        if "mime" in detail_lower:
            return MCPErrorCode.INVALID_MIME_TYPE
        else:
            return MCPErrorCode.UNSUPPORTED_FILE_TYPE

    # 422 Unprocessable Entity
    elif status_code == 422:
        if "collection" in detail_lower and "name" in detail_lower:
            return MCPErrorCode.INVALID_COLLECTION_NAME
        elif "filename" in detail_lower:
            return MCPErrorCode.INVALID_FILENAME
        elif "username" in detail_lower:
            return MCPErrorCode.INVALID_USERNAME
        elif "query" in detail_lower and ("empty" in detail_lower or "cannot be" in detail_lower):
            return MCPErrorCode.EMPTY_QUERY
        elif "query" in detail_lower and "length" in detail_lower:
            return MCPErrorCode.INVALID_QUERY_LENGTH
        elif "corpus" in detail_lower and "id" in detail_lower:
            return MCPErrorCode.INVALID_CORPUS_ID
        elif "n_results" in detail_lower or "results" in detail_lower:
            return MCPErrorCode.INVALID_N_RESULTS
        elif "no valid files" in detail_lower:
            return MCPErrorCode.NO_VALID_FILES
        else:
            # Generic validation error if we can't determine specific type
            return MCPErrorCode.INVALID_COLLECTION_NAME

    # 429 Too Many Requests
    elif status_code == 429:
        if "embedding" in detail_lower or "openai" in detail_lower:
            return MCPErrorCode.EMBEDDING_RATE_LIMIT
        else:
            return MCPErrorCode.RATE_LIMIT_EXCEEDED

    # 500 Internal Server Error
    elif status_code == 500:
        if "database" in detail_lower or "sqlite" in detail_lower:
            return MCPErrorCode.DATABASE_ERROR
        elif "chroma" in detail_lower:
            return MCPErrorCode.CHROMADB_ERROR
        elif "openai" in detail_lower or "embedding" in detail_lower:
            return MCPErrorCode.OPENAI_API_ERROR
        else:
            return MCPErrorCode.INTERNAL_ERROR

    # Unknown/unhandled status code
    else:
        return MCPErrorCode.UNKNOWN_ERROR


def get_retry_guidance(error_code: MCPErrorCode) -> dict:
    """Get retry guidance for a given error code.

    Args:
        error_code: MCP error code

    Returns:
        dict: Retry guidance with keys:
            - should_retry: bool - Whether the request should be retried
            - retry_after: Optional[int] - Seconds to wait before retry
            - backoff_strategy: str - "none", "linear", "exponential"
            - max_retries: int - Maximum number of retry attempts
    """
    # Auth errors - retry with fixed credentials
    if error_code in {
        MCPErrorCode.MISSING_API_KEY,
        MCPErrorCode.INVALID_API_KEY,
        MCPErrorCode.EXPIRED_API_KEY,
    }:
        return {
            "should_retry": True,
            "retry_after": 0,
            "backoff_strategy": "none",
            "max_retries": 1,
            "guidance": "Retry with valid API key",
        }

    # Authorization errors - don't retry, need different permissions
    elif error_code in {
        MCPErrorCode.INSUFFICIENT_PERMISSIONS,
        MCPErrorCode.CORPUS_NOT_APPROVED,
        MCPErrorCode.ADMIN_REQUIRED,
    }:
        return {
            "should_retry": False,
            "retry_after": None,
            "backoff_strategy": "none",
            "max_retries": 0,
            "guidance": "Request different permissions or resource",
        }

    # Validation errors - fix parameters and retry once
    elif error_code.value.startswith("validation.") or error_code.value.startswith("file."):
        return {
            "should_retry": True,
            "retry_after": 0,
            "backoff_strategy": "none",
            "max_retries": 1,
            "guidance": "Fix parameters and retry",
        }

    # Rate limiting - exponential backoff
    elif error_code.value.startswith("rate_limit."):
        return {
            "should_retry": True,
            "retry_after": 60,
            "backoff_strategy": "exponential",
            "max_retries": 3,
            "guidance": "Wait and retry with exponential backoff",
        }

    # Resource not found - don't retry, resource doesn't exist
    elif error_code.value.startswith("resource."):
        return {
            "should_retry": False,
            "retry_after": None,
            "backoff_strategy": "none",
            "max_retries": 0,
            "guidance": "Resource not found, check parameters",
        }

    # Server errors - exponential backoff
    elif error_code.value.startswith("server."):
        return {
            "should_retry": True,
            "retry_after": 5,
            "backoff_strategy": "exponential",
            "max_retries": 5,
            "guidance": "Retry with exponential backoff",
        }

    # Unknown error - conservative retry
    else:
        return {
            "should_retry": True,
            "retry_after": 10,
            "backoff_strategy": "linear",
            "max_retries": 2,
            "guidance": "Retry with caution",
        }
