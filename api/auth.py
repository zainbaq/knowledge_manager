"""Authentication utilities for the API."""

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

from config import COGNITO_ENABLED
from logging_config import get_logger
from .users import get_user_by_api_key, get_or_create_cognito_user

logger = get_logger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    api_key: str = Security(api_key_header),
    bearer_token: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    """
    Return the user associated with the provided credentials.

    Supports two authentication methods:
    1. X-API-Key header (legacy/internal)
    2. Authorization: Bearer <jwt> (Cognito JWT tokens)
    """
    # Try API key first (existing behavior)
    if api_key:
        user = get_user_by_api_key(api_key)
        if user:
            logger.debug(f"Authenticated via API key: {user['username']}")
            return user
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )

    # Try Bearer token (Cognito JWT)
    if bearer_token:
        if not COGNITO_ENABLED:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Cognito authentication is not configured",
            )

        from .cognito import verify_cognito_token, get_cognito_user_info

        claims = verify_cognito_token(bearer_token.credentials)
        if not claims:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Extract user info from token claims
        user_info = get_cognito_user_info(claims)
        cognito_sub = user_info["cognito_sub"]
        username = user_info["username"]
        email = user_info.get("email", "")

        if not cognito_sub:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Token missing user identifier",
            )

        # Get or create the user in our database
        user = get_or_create_cognito_user(cognito_sub, username, email)
        logger.debug(f"Authenticated via Cognito: {user['username']} (sub: {cognito_sub})")
        return user

    # No authentication provided
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Missing authentication credentials",
    )
