"""Authentication utilities for the API."""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED

from .users import get_user_by_api_key

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(api_key: str = Security(api_key_header)) -> dict:
    """Return the user associated with the provided API key."""
    if not api_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    user = get_user_by_api_key(api_key)
    if user:
        return user
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired API key",
    )
