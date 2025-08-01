from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ingestion.file_loader import extract_text_from_file
from ingestion.chunker import simple_text_chunker
from vector_store.embedder import get_openai_embedding
from vector_store.vector_index import add_documents_to_index, query_index, compile_context
import uuid
import os
import tempfile
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

def process_files(files, collection):
    all_chunks, all_embeddings, all_metas, all_ids = [], [], [], []

    for file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name

        from pathlib import Path
        content = extract_text_from_file(Path(tmp_path))

        os.remove(tmp_path)

        if not content:
            print(f"Skipped: {file.filename}")
            continue

        chunks = simple_text_chunker(content)
        for i, chunk in enumerate(chunks):
            embedding = get_openai_embedding(chunk)
            all_chunks.append(chunk)
            all_embeddings.append(embedding)
            all_metas.append({"source": file.filename, "chunk_index": i})
            all_ids.append(str(uuid.uuid4()))

    if all_chunks:
        add_documents_to_index(collection, all_chunks, all_embeddings, all_metas, all_ids)
        return len(all_chunks)
    else:
        return 0

@app.post("/create-index/")
async def create_index(collection: str = Form(...), files: list[UploadFile] = File(...)):
    try:
        count = process_files(files, collection)
        if count == 0:
            return JSONResponse(content={"error": "No valid files"}, status_code=400)
        return {"message": f"Created index and ingested {count} chunks into '{collection}'"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/update-index/")
async def update_index(collection: str = Form(...), files: list[UploadFile] = File(...)):
    try:
        count = process_files(files, collection)
        if count == 0:
            return JSONResponse(content={"error": "No valid files"}, status_code=400)
        return {"message": f"Updated '{collection}' with {count} new chunks"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/query/")
async def query(request: QueryRequest):
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
    try:
        return list_collections_with_metadata()
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

from fastapi import Path
from vector_store.vector_index import delete_collection

@app.delete("/delete-index/{collection_name}")
async def delete_index(collection_name: str = Path(...)):
    result = delete_collection(collection_name)
    if "error" in result:
        return JSONResponse(content=result, status_code=500)
    return result





