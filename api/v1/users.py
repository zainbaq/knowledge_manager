"""User management endpoints for API v1."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api.users import (
    create_api_key_for_user,
    create_named_api_key_for_user,
    list_api_keys_for_user,
    login_user,
    register_user,
    revoke_api_key_for_user,
)
from api.auth import get_current_user
from config import AUTH_RATE_LIMIT
from api.rate_limiting import limiter
from ..models.requests import UserCredentials
from ..models.responses import AuthResponse

router = APIRouter()


class CreateApiKeyRequest(BaseModel):
    """Request body for creating a named API key."""
    name: Optional[str] = "API Key"


class ApiKeyInfo(BaseModel):
    """Information about an API key (without the full key)."""
    id: int
    name: str
    key_preview: str
    created_at: Optional[str]
    expires_at: Optional[str]


class ApiKeysListResponse(BaseModel):
    """Response containing list of API keys."""
    api_keys: list[ApiKeyInfo]


class CreateApiKeyResponse(BaseModel):
    """Response after creating a new API key."""
    api_key: str  # Full key - shown only once
    id: int
    name: str
    key_preview: str
    created_at: Optional[str]
    expires_at: Optional[str]


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


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
    """Create a new API key for an existing user (legacy endpoint using credentials)."""
    try:
        api_key = create_api_key_for_user(credentials.username, credentials.password)
        return AuthResponse(api_key=api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# New authenticated API key management endpoints

@router.get("/api-keys", response_model=ApiKeysListResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def list_api_keys(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ApiKeysListResponse:
    """List all API keys for the authenticated user."""
    try:
        keys = list_api_keys_for_user(current_user["id"])
        return ApiKeysListResponse(api_keys=keys)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api-keys", response_model=CreateApiKeyResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def create_api_key_authenticated(
    request: Request,
    body: CreateApiKeyRequest,
    current_user: dict = Depends(get_current_user),
) -> CreateApiKeyResponse:
    """Create a new named API key for the authenticated user."""
    try:
        result = create_named_api_key_for_user(current_user["id"], body.name or "API Key")
        return CreateApiKeyResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api-keys/{key_id}", response_model=MessageResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def revoke_api_key(
    request: Request,
    key_id: int,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    """Revoke (delete) an API key."""
    try:
        success = revoke_api_key_for_user(current_user["id"], key_id)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")
        return MessageResponse(message="API key revoked successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
