import asyncio
import json
import uuid
from typing import List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, ToolOutput

from ingestion.chunker import token_text_chunker
from vector_store.vector_index import (
    add_documents_to_index,
    query_index,
    query_multiple_indexes,
    compile_context,
    list_collections_with_metadata,
    delete_collection,
    list_collection_names,
)
from vector_store.embedder import get_openai_embedding


# Initialize FastMCP server
mcp = FastMCP("knowledge_manager")


async def _ingest_texts(collection: str, texts: List[str]) -> int:
    """Helper to chunk, embed and store a list of texts."""
    chunks: List[str] = []
    embeddings: List = []
    metas: List[dict] = []
    ids: List[str] = []

    for t_index, text in enumerate(texts):
        text_chunks = list(token_text_chunker(text))
        for c_index, chunk in enumerate(text_chunks):
            embedding = await asyncio.to_thread(get_openai_embedding, chunk)
            chunks.append(chunk)
            embeddings.append(embedding)
            metas.append({"source": f"text_{t_index}", "chunk_index": c_index})
            ids.append(str(uuid.uuid4()))

    if chunks:
        await asyncio.to_thread(
            add_documents_to_index,
            collection,
            chunks,
            embeddings,
            metas,
            ids,
        )
    return len(chunks)


@mcp.tool()
async def create_index(collection: str, texts: List[str]) -> str:
    """Create a new collection and ingest provided texts"""
    count = await _ingest_texts(collection, texts)
    message = f"Created index and ingested {count} chunks into '{collection}'"
    return message


@mcp.tool()
async def update_index(collection: str, texts: List[str]) -> str:
    """Append texts to an existing collection"""
    count = await _ingest_texts(collection, texts)
    message = f"Updated '{collection}' with {count} new chunks"
    return message


@mcp.tool()
async def query(
    query: str,
    collection: Optional[str] = None,
    collections: Optional[List[str]] = None,
) -> str:
    """Query one or more collections and return context"""
    if collection:
        results = await asyncio.to_thread(query_index, collection, query)
    else:
        if collections:
            target = collections
        else:
            target = list_collection_names()
        results = await asyncio.to_thread(query_multiple_indexes, target, query)
    
    context = compile_context(results)
    payload = {"context": context, "raw_results": results}
    return json.dumps(payload)


@mcp.tool()
async def list_indexes() -> str:
    """List available collections with metadata"""
    data = await asyncio.to_thread(list_collections_with_metadata)
    return json.dumps(data)


@mcp.tool()
async def delete_index(collection_name: str) -> str:
    """Delete a collection from the vector store"""
    result = await asyncio.to_thread(delete_collection, collection_name)
    return json.dumps(result)


if __name__ == "__main__":
    # Run the server with stdio transport (default)
    mcp.run()