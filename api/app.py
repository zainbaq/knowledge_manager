"""FastAPI routes for managing document indexes and querying them."""

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ingestion.file_loader import extract_text_from_file
from ingestion.chunker import simple_text_chunker, token_text_chunker
from vector_store.embedder import get_openai_embedding
from vector_store.vector_index import (
    add_documents_to_index,
    query_index,
    compile_context,
)
import uuid
import os
import tempfile
import asyncio
from typing import Iterable, List
from pathlib import Path
from config import CORS_ORIGINS

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

# Configure CORS. `CORS_ORIGINS` is already a list, so pass it directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # NEVER use "*" in production
    allow_methods=["*"],
    allow_headers=["*"]
)

class QueryRequest(BaseModel):
    query: str
    collection: str

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


async def process_files(files: Iterable[UploadFile], collection: str, chunker=token_text_chunker) -> int:
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
        )
        return len(all_chunks)
    return 0

@app.post("/create-index/")
async def create_index(collection: str = Form(...), files: list[UploadFile] = File(...)):
    """Create a new collection and ingest the given files."""
    try:
        count = await process_files(files, collection)
        if count == 0:
            return JSONResponse(content={"error": "No valid files"}, status_code=400)
        return {"message": f"Created index and ingested {count} chunks into '{collection}'"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/update-index/")
async def update_index(collection: str = Form(...), files: list[UploadFile] = File(...)):
    """Append new files to an existing collection."""
    try:
        count = await process_files(files, collection)
        if count == 0:
            return JSONResponse(content={"error": "No valid files"}, status_code=400)
        return {"message": f"Updated '{collection}' with {count} new chunks"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/query/")
async def query(request: QueryRequest):
    """Return relevant context for ``request.query`` from the index."""
    try:
        results = query_index(request.collection, request.query)
        context = compile_context(results)
        return {"context": context, "raw_results": results}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
import os

from vector_store.vector_index import list_collections_with_metadata

@app.get("/list-indexes/")
async def list_indexes():
    """List all available collections with basic metadata."""
    try:
        return list_collections_with_metadata()
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

from fastapi import Path
from vector_store.vector_index import delete_collection

@app.delete("/delete-index/{collection_name}")
async def delete_index(collection_name: str = Path(...)):
    """Delete an entire collection from the vector store."""
    result = delete_collection(collection_name)
    if "error" in result:
        return JSONResponse(content=result, status_code=500)
    return result





