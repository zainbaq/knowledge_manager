"""FastAPI routes for managing document indexes and querying them."""

from fastapi import FastAPI, File, UploadFile, Form, Depends, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingestion.file_loader import extract_text_from_file
from ingestion.chunker import simple_text_chunker, token_text_chunker
from vector_store.embedder import get_openai_embedding
from vector_store.vector_index import (
    add_documents_to_index,
    query_index,
    query_multiple_indexes,
    compile_context,
    list_collections_with_metadata,
    delete_collection,
    list_collection_names,
)
import uuid
import os
import tempfile
import asyncio
from typing import Iterable, List
from pathlib import Path
from config import CORS_ORIGINS, ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE_MB
from .auth import get_current_user
from .users import router as users_router

app = FastAPI()

api_router = APIRouter()

# Mount user management routes
api_router.include_router(users_router, prefix="/user")

# Configure CORS. `CORS_ORIGINS` is already a list, so pass it directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # NEVER use "*" in production
    allow_methods=["*"],
    allow_headers=["*"]
)

class QueryRequest(BaseModel):
    query: str
    collection: str = None
    collections: list[str] = None


def validate_upload_files(files: Iterable[UploadFile]) -> str:
    """Return an error message if any file is invalid."""
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            return f"Unsupported file type: {file.filename}"
        file.file.seek(0, os.SEEK_END)
        size_mb = file.file.tell() / (1024 * 1024)
        file.file.seek(0)
        if size_mb > MAX_FILE_SIZE_MB:
            return f"File too large: {file.filename}"
    return None

async def _process_single_file(file: UploadFile, chunker) -> tuple[List[str], List, List[dict], List[str]]:
    """Extract text, chunk it and generate embeddings for one file."""

    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    content = await asyncio.to_thread(extract_text_from_file, Path(tmp_path))
    os.remove(tmp_path)

    if not content:
        print(f"Skipped: {file.filename}")
        return [], [], [], []

    chunks = list(chunker(content))

    embeddings = []
    for chunk in chunks:
        embedding = await asyncio.to_thread(get_openai_embedding, chunk)
        embeddings.append(embedding)

    metas = [{"source": file.filename, "chunk_index": i} for i in range(len(chunks))]
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

@api_router.post("/status/")
async def status():
    try:
        result = {
            'status' : 'ok'
        }
        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
@api_router.post("/create-index/")
async def create_index(
    collection: str = Form(...),
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Create a new collection and ingest the given files."""
    error = validate_upload_files(files)
    if error:
        return JSONResponse(content={"error": error}, status_code=400)
    try:
        count = await process_files(files, collection, current_user["db_path"])
        if count == 0:
            return JSONResponse(content={"error": "No valid files"}, status_code=400)
        return {
            "message": f"Created index and ingested {count} chunks into '{collection}'"
        }
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@api_router.post("/update-index/")
async def update_index(
    collection: str = Form(...),
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Append new files to an existing collection."""
    error = validate_upload_files(files)
    if error:
        return JSONResponse(content={"error": error}, status_code=400)
    try:
        count = await process_files(files, collection, current_user["db_path"])
        if count == 0:
            return JSONResponse(content={"error": "No valid files"}, status_code=400)
        return {"message": f"Updated '{collection}' with {count} new chunks"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@api_router.post("/query/")
async def query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    """Return context for a query across one or many collections."""
    try:
        if request.collection:
            results = query_index(
                request.collection, request.query, current_user["db_path"]
            )
        else:
            if request.collections:
                collections = request.collections
            else:
                collections = list_collection_names(current_user["db_path"])
            results = query_multiple_indexes(
                collections, request.query, current_user["db_path"]
            )
        context = compile_context(results)
        return {"context": context, "raw_results": results}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@api_router.get("/list-indexes/")
async def list_indexes(current_user: dict = Depends(get_current_user)):
    """List all available collections with basic metadata."""
    try:
        return list_collections_with_metadata(current_user["db_path"])
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@api_router.delete("/delete-index/{collection_name}")
async def delete_index(
    collection_name: str, current_user: dict = Depends(get_current_user)
):
    """Delete an entire collection from the vector store."""
    result = delete_collection(collection_name, current_user["db_path"])
    if "error" in result:
        return JSONResponse(content=result, status_code=500)
    return result

app.include_router(api_router, prefix="/api")

# # Add to api/app.py
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import HTMLResponse
# import subprocess
# import threading
# import time

# # Start Streamlit in background thread
# def start_streamlit():
#     subprocess.run([
#         "streamlit", "run", "ui/streamlit_app.py", 
#         "--server.port", "8501",
#         "--server.address", "0.0.0.0"
#     ])

# # Start Streamlit when FastAPI starts
# @app.on_event("startup")
# async def startup_event():
#     threading.Thread(target=start_streamlit, daemon=True).start()
#     time.sleep(5)  # Give Streamlit time to start

# # Proxy Streamlit through FastAPI
# @app.get("/ui")
# async def streamlit_ui():
#     return HTMLResponse("""
#     <iframe src="http://localhost:8501" width="100%" height="800px"></iframe>
#     """)