
import asyncio
import json
import uuid
from typing import List, Optional

from mcp.server import Server
from mcp.server.fastapi import FastAPIAdapter
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


server = Server("knowledge_manager")


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


@server.tool(
    name="create_index",
    description="Create a new collection and ingest provided texts",
    input_schema={
        "type": "object",
        "properties": {
            "collection": {"type": "string"},
            "texts": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["collection", "texts"],
    },
)
async def create_index_tool(collection: str, texts: List[str]) -> ToolOutput:
    count = await _ingest_texts(collection, texts)
    message = f"Created index and ingested {count} chunks into '{collection}'"
    return ToolOutput(content=[TextContent(text=message)])


@server.tool(
    name="update_index",
    description="Append texts to an existing collection",
    input_schema={
        "type": "object",
        "properties": {
            "collection": {"type": "string"},
            "texts": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["collection", "texts"],
    },
)
async def update_index_tool(collection: str, texts: List[str]) -> ToolOutput:
    count = await _ingest_texts(collection, texts)
    message = f"Updated '{collection}' with {count} new chunks"
    return ToolOutput(content=[TextContent(text=message)])


@server.tool(
    name="query",
    description="Query one or more collections and return context",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "collection": {"type": "string"},
            "collections": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["query"],
    },
)
async def query_tool(
    query: str,
    collection: Optional[str] = None,
    collections: Optional[List[str]] = None,
) -> ToolOutput:
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
    return ToolOutput(content=[TextContent(text=json.dumps(payload))])


@server.tool(
    name="list_indexes",
    description="List available collections with metadata",
)
async def list_indexes_tool() -> ToolOutput:
    data = await asyncio.to_thread(list_collections_with_metadata)
    return ToolOutput(content=[TextContent(text=json.dumps(data))])


@server.tool(
    name="delete_index",
    description="Delete a collection from the vector store",
    input_schema={
        "type": "object",
        "properties": {"collection_name": {"type": "string"}},
        "required": ["collection_name"],
    },
)
async def delete_index_tool(collection_name: str) -> ToolOutput:
    result = await asyncio.to_thread(delete_collection, collection_name)
    return ToolOutput(content=[TextContent(text=json.dumps(result))])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(FastAPIAdapter(server), host="0.0.0.0", port=8765)
