"""User management endpoints for API v1."""

from fastapi import APIRouter, HTTPException, Request

from api.users import create_api_key_for_user, login_user, register_user
from config import AUTH_RATE_LIMIT
from api.rate_limiting import limiter
from ..models.requests import UserCredentials
from ..models.responses import AuthResponse

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(request: Request, credentials: UserCredentials) -> AuthResponse:
    """Register a new user and return an API key."""
    try:
        api_key = register_user(credentials.username, credentials.password)
        return AuthResponse(api_key=api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(request: Request, credentials: UserCredentials) -> AuthResponse:
    """Login and return an API key."""
    try:
        api_key = login_user(credentials.username, credentials.password)
        return AuthResponse(api_key=api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-api-key", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def create_api_key_endpoint(request: Request, credentials: UserCredentials) -> AuthResponse:
    """Create a new API key for an existing user."""
    try:
        api_key = create_api_key_for_user(credentials.username, credentials.password)
        return AuthResponse(api_key=api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
