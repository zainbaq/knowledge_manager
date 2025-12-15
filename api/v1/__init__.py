"""API v1 router module."""

from fastapi import APIRouter
from . import admin, corpus, endpoints, mcp, users

v1_router = APIRouter()
v1_router.include_router(endpoints.router, tags=["documents"])
v1_router.include_router(users.router, prefix="/user", tags=["users"])
v1_router.include_router(corpus.router, prefix="/corpus", tags=["corpus"])
v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
v1_router.include_router(mcp.router, tags=["mcp"])
