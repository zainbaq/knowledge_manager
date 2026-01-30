"""FastAPI routes for managing document indexes and querying them."""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

from openai import RateLimitError as OpenAIRateLimitError
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config import (
    ALLOWED_FILE_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    CORS_ORIGINS,
    EMBEDDING_CONCURRENCY,
    MANAGEMENT_RATE_LIMIT,
    MAX_EMBEDDING_RETRIES,
    MAX_FILE_SIZE_MB,
    MIME_VALIDATION_BYTES,
    QUERY_RATE_LIMIT,
    UPLOAD_RATE_LIMIT,
)
from ingestion.chunker import token_text_chunker
from ingestion.file_loader import extract_text_from_file
from logging_config import get_logger
from vector_store.embedder import get_openai_embedding
from vector_store.vector_index import (
    add_documents_to_index,
    clear_client_cache,
    compile_context,
    delete_collection,
    list_collection_names,
    list_collections_with_metadata,
    query_index,
    query_multiple_indexes,
)

from .auth import get_current_user
from .middleware.mcp_error_handler import MCPErrorMiddleware
from .middleware.request_logging import RequestLoggingMiddleware
from .rate_limiting import limiter
from .users import router as users_router
from .validation import validate_collection_name, validate_filename

logger = get_logger(__name__)

# Semaphore to limit concurrent OpenAI embedding API calls
_embedding_semaphore = asyncio.Semaphore(EMBEDDING_CONCURRENCY)


async def _generate_embedding_with_retry(chunk: str, max_retries: int = MAX_EMBEDDING_RETRIES) -> List[float]:
    """Generate embedding for a chunk with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            async with _embedding_semaphore:
                return await asyncio.to_thread(get_openai_embedding, chunk)
        except OpenAIRateLimitError as e:
            if attempt == max_retries - 1:
                logger.error(f"Rate limit exceeded after {max_retries} attempts: {e}")
                raise
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise


app = FastAPI(
    title="Knowledge Manager API",
    description="Document indexing and semantic search API with vector embeddings",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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

# Import v1 router
from api.v1 import v1_router

# Keep old router for backward compatibility (deprecated)
api_router = APIRouter()

# Mount user management routes (deprecated - use /api/v1/user instead)
api_router.include_router(users_router, prefix="/user")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",  # Allow any localhost port
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)


# Graceful shutdown: clear ChromaDB client cache
@app.on_event("shutdown")
async def shutdown_event():
    """Clear cached ChromaDB clients on application shutdown."""
    clear_client_cache()
    logger.info("ChromaDB client cache cleared on shutdown")


# Global exception handler
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


class QueryRequest(BaseModel):
    query: str
    collection: Optional[str] = None
    collections: Optional[list[str]] = None


def validate_upload_files(files: Iterable[UploadFile]) -> Optional[str]:
    """Return an error message if any file is invalid."""
    for file in files:
        try:
            safe_filename = validate_filename(file.filename)
        except HTTPException as exc:
            return exc.detail

        ext = Path(safe_filename).suffix.lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            return f"Unsupported file type: {safe_filename}"

        file.file.seek(0, os.SEEK_END)
        size_mb = file.file.tell() / (1024 * 1024)
        file.file.seek(0)
        if size_mb > MAX_FILE_SIZE_MB:
            return (
                f"File too large: {safe_filename} "
                f"({size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB)"
            )

        try:
            header = file.file.read(MIME_VALIDATION_BYTES)
            file.file.seek(0)
            if MAGIC_AVAILABLE:
                detected_mime = magic.from_buffer(header, mime=True) if header else ""
            else:
                # Skip MIME validation if libmagic is not available
                detected_mime = ""
        except Exception as exc:  # pragma: no cover - defensive
            return f"Unable to determine file type for {safe_filename}: {exc}"

        allowed_mimes = ALLOWED_MIME_TYPES.get(ext)
        # Only reject if we detected a MIME type AND it doesn't match allowed types
        # Skip validation if magic couldn't determine the type (empty string)
        if allowed_mimes and detected_mime and detected_mime not in allowed_mimes:
            return (
                f"Invalid MIME type for {safe_filename}: expected "
                f"{', '.join(sorted(allowed_mimes))}, detected {detected_mime}"
            )
    return None


async def _process_single_file(
    file: UploadFile, chunker
) -> tuple[List[str], List, List[dict], List[str]]:
    """Extract text, chunk it and generate embeddings for one file."""
    safe_filename = validate_filename(file.filename)

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(safe_filename).suffix) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    content = await asyncio.to_thread(extract_text_from_file, Path(tmp_path))
    os.remove(tmp_path)

    if not content:
        logger.warning(f"Skipped file with no extractable content: {safe_filename}")
        return [], [], [], []

    chunks = list(chunker(content))

    # Parallelize embedding generation with concurrency control and retry logic
    embeddings = await asyncio.gather(
        *[_generate_embedding_with_retry(chunk) for chunk in chunks]
    )

    metas = [{"source": safe_filename, "chunk_index": i} for i in range(len(chunks))]
    ids = [str(uuid.uuid4()) for _ in chunks]

    return chunks, embeddings, metas, ids


async def process_files(
    files: Iterable[UploadFile],
    collection: str,
    db_path: str,
    chunker=token_text_chunker,
) -> int:
    """Process and index multiple uploaded files asynchronously."""

    tasks = [asyncio.create_task(_process_single_file(file, chunker)) for file in files]
    results = await asyncio.gather(*tasks)

    all_chunks: List[str] = []
    all_embeddings: List = []
    all_metas: List[dict] = []
    all_ids: List[str] = []

    for chunks, embeddings, metas, ids in results:
        all_chunks.extend(chunks)
        all_embeddings.extend(embeddings)
        all_metas.extend(metas)
        all_ids.extend(ids)

    if all_chunks:
        await asyncio.to_thread(
            add_documents_to_index,
            collection,
            all_chunks,
            all_embeddings,
            all_metas,
            all_ids,
            db_path,
        )
        return len(all_chunks)
    return 0


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        content={"detail": "Rate limit exceeded. Please slow down and try again."},
        status_code=429,
    )


@api_router.get("/status/")
@limiter.limit(QUERY_RATE_LIMIT)
async def status(request: Request):
    try:
        return JSONResponse(content={"status": "ok"}, status_code=200)
    except Exception as exc:
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@api_router.post("/create-index/")
@limiter.limit(UPLOAD_RATE_LIMIT)
async def create_index(
    request: Request,
    collection: str = Form(...),
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Create a new collection and ingest the given files."""
    collection = validate_collection_name(collection)

    error = validate_upload_files(files)
    if error:
        return JSONResponse(content={"detail": error}, status_code=400)
    try:
        count = await process_files(files, collection, current_user["db_path"])
        if count == 0:
            return JSONResponse(content={"detail": "No valid files"}, status_code=400)
        return {
            "message": f"Created index and ingested {count} chunks into '{collection}'",
            "indexed_chunks": count
        }
    except Exception as exc:
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@api_router.post("/update-index/")
@limiter.limit(UPLOAD_RATE_LIMIT)
async def update_index(
    request: Request,
    collection: str = Form(...),
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Append new files to an existing collection."""
    collection = validate_collection_name(collection)

    error = validate_upload_files(files)
    if error:
        return JSONResponse(content={"detail": error}, status_code=400)
    try:
        count = await process_files(files, collection, current_user["db_path"])
        if count == 0:
            return JSONResponse(content={"detail": "No valid files"}, status_code=400)
        return {
            "message": f"Updated '{collection}' with {count} new chunks",
            "indexed_chunks": count
        }
    except Exception as exc:
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@api_router.post("/query/")
@limiter.limit(QUERY_RATE_LIMIT)
async def query(
    request: Request,
    payload: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """Return context for a query across one or many collections."""
    try:
        if payload.collection:
            collection = validate_collection_name(payload.collection)
            results = query_index(collection, payload.query, current_user["db_path"])
        else:
            if payload.collections:
                collections = [validate_collection_name(c) for c in payload.collections]
            else:
                collections = list_collection_names(current_user["db_path"])
            results = await query_multiple_indexes(
                collections, payload.query, current_user["db_path"]
            )
        context = compile_context(results)
        return {"context": context, "raw_results": results}
    except Exception as exc:
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@api_router.get("/list-indexes/")
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def list_indexes(request: Request, current_user: dict = Depends(get_current_user)):
    """List all available collections with basic metadata."""
    try:
        collections = list_collections_with_metadata(current_user["db_path"])
        return {"collections": collections}
    except Exception as exc:
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@api_router.delete("/delete-index/{collection_name}")
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def delete_index(
    request: Request, collection_name: str, current_user: dict = Depends(get_current_user)
):
    """Delete an entire collection from the vector store."""
    collection_name = validate_collection_name(collection_name)

    result = delete_collection(collection_name, current_user["db_path"])
    if "error" in result:
        return JSONResponse(content=result, status_code=500)
    return result


# Mount v1 router (primary, versioned API)
app.include_router(v1_router, prefix="/api/v1")

# Mount old router for backward compatibility (deprecated)
app.include_router(api_router, prefix="/api")
