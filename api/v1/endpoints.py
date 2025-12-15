"""Document management endpoints for API v1."""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from typing import Iterable, List, Optional

import magic
import openai
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from config import (
    ALLOWED_FILE_EXTENSIONS,
    ALLOWED_MIME_TYPES,
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
    compile_context,
    delete_collection,
    list_collection_names,
    list_collections_with_metadata,
    query_index,
    query_multiple_indexes,
)

from ..auth import get_current_user
from ..rate_limiting import limiter
from ..validation import validate_collection_name, validate_filename
from ..models.requests import QueryRequest
from ..models.responses import (
    DeleteResponse,
    ErrorResponse,
    ListCollectionsResponse,
    QueryResponse,
    StatusResponse,
    UploadResponse,
)

logger = get_logger(__name__)

router = APIRouter()

# Semaphore to limit concurrent OpenAI embedding API calls
_embedding_semaphore = asyncio.Semaphore(EMBEDDING_CONCURRENCY)


async def _generate_embedding_with_retry(chunk: str, max_retries: int = MAX_EMBEDDING_RETRIES) -> List[float]:
    """Generate embedding for a chunk with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            async with _embedding_semaphore:
                return await asyncio.to_thread(get_openai_embedding, chunk)
        except openai.RateLimitError as e:
            if attempt == max_retries - 1:
                logger.error(f"Rate limit exceeded after {max_retries} attempts: {e}")
                raise
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise


def validate_upload_files(files: Iterable[UploadFile]) -> Optional[tuple[str, int]]:
    """Return (error_message, status_code) tuple if any file is invalid."""
    for file in files:
        try:
            safe_filename = validate_filename(file.filename)
        except HTTPException as exc:
            return (exc.detail, HTTP_422_UNPROCESSABLE_ENTITY)

        ext = Path(safe_filename).suffix.lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            return (
                f"Unsupported file type: {safe_filename}",
                HTTP_415_UNSUPPORTED_MEDIA_TYPE
            )

        file.file.seek(0, os.SEEK_END)
        size_mb = file.file.tell() / (1024 * 1024)
        file.file.seek(0)
        if size_mb > MAX_FILE_SIZE_MB:
            return (
                f"File too large: {safe_filename} ({size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB)",
                HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        try:
            header = file.file.read(MIME_VALIDATION_BYTES)
            file.file.seek(0)
            detected_mime = magic.from_buffer(header, mime=True) if header else ""
        except Exception as exc:  # pragma: no cover - defensive
            return (
                f"Unable to determine file type for {safe_filename}: {exc}",
                HTTP_422_UNPROCESSABLE_ENTITY
            )

        allowed_mimes = ALLOWED_MIME_TYPES.get(ext)
        if allowed_mimes and detected_mime not in allowed_mimes:
            return (
                f"Invalid MIME type for {safe_filename}: expected "
                f"{', '.join(sorted(allowed_mimes))}, detected {detected_mime or 'unknown'}",
                HTTP_415_UNSUPPORTED_MEDIA_TYPE
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


@router.get("/status/", response_model=StatusResponse)
@limiter.limit(QUERY_RATE_LIMIT)
async def status(request: Request) -> StatusResponse:
    """Check API status."""
    return StatusResponse(status="ok")


@router.post("/create-index/", response_model=UploadResponse)
@limiter.limit(UPLOAD_RATE_LIMIT)
async def create_index(
    request: Request,
    collection: str = Form(...),
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
) -> UploadResponse:
    """Create a new collection and ingest the given files."""
    collection = validate_collection_name(collection)

    validation_result = validate_upload_files(files)
    if validation_result:
        error_msg, status_code = validation_result
        raise HTTPException(status_code=status_code, detail=error_msg)

    count = await process_files(files, collection, current_user["db_path"])
    if count == 0:
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="No valid files")

    return UploadResponse(
        message=f"Created index and ingested {count} chunks into '{collection}'",
        indexed_chunks=count
    )


@router.post("/update-index/", response_model=UploadResponse)
@limiter.limit(UPLOAD_RATE_LIMIT)
async def update_index(
    request: Request,
    collection: str = Form(...),
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
) -> UploadResponse:
    """Append new files to an existing collection."""
    collection = validate_collection_name(collection)

    validation_result = validate_upload_files(files)
    if validation_result:
        error_msg, status_code = validation_result
        raise HTTPException(status_code=status_code, detail=error_msg)

    count = await process_files(files, collection, current_user["db_path"])
    if count == 0:
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="No valid files")

    return UploadResponse(
        message=f"Updated '{collection}' with {count} new chunks",
        indexed_chunks=count
    )


@router.post(
    "/query/",
    response_model=QueryResponse,
    responses={
        200: {
            "description": "Successful query with context and results",
            "model": QueryResponse,
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse,
        },
        422: {
            "description": "Invalid request parameters",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
    summary="Query collections",
    description="Search one or more collections using semantic similarity. Returns compiled context from the most relevant document chunks.",
)
@limiter.limit(QUERY_RATE_LIMIT)
async def query(
    request: Request,
    payload: QueryRequest,
    current_user: dict = Depends(get_current_user),
) -> QueryResponse:
    """Return context for a query across one or many collections."""
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
    return QueryResponse(context=context, raw_results=results)


@router.get("/list-indexes/", response_model=ListCollectionsResponse)
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def list_indexes(request: Request, current_user: dict = Depends(get_current_user)) -> ListCollectionsResponse:
    """List all available collections with basic metadata."""
    collections = list_collections_with_metadata(current_user["db_path"])
    return ListCollectionsResponse(collections=collections)


@router.delete("/delete-index/{collection_name}", response_model=DeleteResponse)
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def delete_index(
    request: Request, collection_name: str, current_user: dict = Depends(get_current_user)
) -> DeleteResponse:
    """Delete an entire collection from the vector store."""
    collection_name = validate_collection_name(collection_name)

    result = delete_collection(collection_name, current_user["db_path"])
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return DeleteResponse(message=result["message"])
