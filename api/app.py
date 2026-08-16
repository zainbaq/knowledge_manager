"""FastAPI application factory and wiring.

Route handlers live in api/v1/. This module only builds the app: middleware,
CORS, lifespan, error handlers and the health probe.

The legacy unversioned ``/api/*`` router that used to live here was removed - it
was a near-verbatim second copy of api/v1/endpoints.py that had already drifted
out of sync (v1 returns typed 413/415/422 responses where the copy returned flat
400s) and stood up a second embedding semaphore, doubling the effective
EMBEDDING_CONCURRENCY cap. Every known consumer, including the Promethean AI
backend's KM connector, calls /api/v1/* exclusively.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from config import CORS_ORIGINS, DEBUG, require_openai_api_key
from logging_config import get_logger
from vector_store.vector_index import clear_client_cache

from .middleware.mcp_error_handler import MCPErrorMiddleware
from .middleware.request_logging import RequestLoggingMiddleware
from .rate_limiting import limiter

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate configuration on boot, release resources on shutdown."""
    # Fail fast and loudly on a misconfigured deployment. config.py deliberately
    # does not raise at import time, so migration scripts and tests can import it.
    require_openai_api_key()
    logger.info("Knowledge Manager API starting")

    yield

    clear_client_cache()
    logger.info("ChromaDB client cache cleared on shutdown")


app = FastAPI(
    title="Knowledge Manager API",
    description="Document indexing and semantic search API with vector embeddings",
    version="1.0.0",
    # Served under /api so the frontend's single /api/* rewrite reaches them.
    # At the bare /docs they would collide with the frontend's own docs page,
    # which owns that path on the public origin.
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "documents",
            "description": "Document upload, indexing, and querying operations",
        },
        {
            "name": "users",
            "description": "User registration and API key management",
        },
        {
            "name": "mcp",
            "description": "Model Context Protocol (MCP) endpoints for AI agent integration",
        },
    ],
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(MCPErrorMiddleware)

# CORS. The blanket localhost regex is DEBUG-only on purpose: combined with
# allow_credentials it previously let any page on any localhost port make
# credentialed cross-origin calls against production. In production the frontend
# proxies /api/* same-origin (see next/next.config.ts rewrites), so CORS_ORIGINS
# only needs to name genuine external callers.
_cors_kwargs = {}
if DEBUG:
    _cors_kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    **_cors_kwargs,
)


@app.get("/health", include_in_schema=False)
async def health():
    """Container/orchestrator health probe.

    Unauthenticated and deliberately exempt from rate limiting - a probe that
    can 429 itself reports a healthy service as unhealthy.
    """
    return {"status": "ok"}


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        content={"detail": "Rate limit exceeded. Please slow down and try again."},
        status_code=429,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Mount the versioned API (the only API surface)
from api.v1 import v1_router  # noqa: E402

app.include_router(v1_router, prefix="/api/v1")
