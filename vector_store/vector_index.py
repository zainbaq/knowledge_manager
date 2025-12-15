"""Wrapper functions around ChromaDB for simple vector operations."""

import asyncio
import threading
from pathlib import Path
from typing import AsyncGenerator, Dict

import chromadb
from config import VECTOR_DB_PATH

# Thread-safe client cache to avoid recreating clients for the same db_path
_client_cache: Dict[str, chromadb.PersistentClient] = {}
_cache_lock = threading.Lock()


def get_user_db_path(username: str) -> str:
    """Construct safe user database path with validation.

    SECURITY: This function prevents path traversal attacks by:
    1. Sanitizing the username (removing .., /, etc)
    2. Using Path.resolve() to get absolute path
    3. Verifying the result is still under VECTOR_DB_PATH

    Args:
        username: Username (should already be validated by validate_username)

    Returns:
        str: Safe absolute path to user's database directory

    Raises:
        ValueError: If path traversal is detected
    """
    from api.validation import sanitize_path_component

    # Defense in depth: sanitize even though username should be validated
    safe_username = sanitize_path_component(username)

    # Construct path using pathlib for safety
    base_path = Path(VECTOR_DB_PATH).resolve()
    user_path = (base_path / safe_username).resolve()

    # CRITICAL: Verify the resolved path is still under base_path
    # This prevents path traversal attacks like username="../../etc"
    try:
        user_path.relative_to(base_path)
    except ValueError:
        # Path is outside base_path - SECURITY VIOLATION
        raise ValueError(f"Invalid path for username: {username}")

    return str(user_path)


def get_corpus_db_path(corpus_id: int) -> str:
    """Construct safe corpus database path with validation.

    SECURITY: This function prevents path traversal attacks by:
    1. Using integer corpus ID (no path separators possible)
    2. Using Path.resolve() to get absolute path
    3. Verifying the result is still under VECTOR_DB_PATH

    Corpuses are stored in {VECTOR_DB_PATH}/corpora/{corpus_id}/

    Args:
        corpus_id: Corpus ID (positive integer)

    Returns:
        str: Safe absolute path to corpus database directory

    Raises:
        ValueError: If corpus_id is invalid or path traversal is detected
    """
    # SECURITY: Validate corpus_id is a positive integer
    if not isinstance(corpus_id, int) or corpus_id < 1:
        raise ValueError(f"Invalid corpus_id: {corpus_id}")

    # Construct path using pathlib for safety
    base_path = Path(VECTOR_DB_PATH).resolve()
    corpora_path = (base_path / "corpora").resolve()
    corpus_path = (corpora_path / str(corpus_id)).resolve()

    # CRITICAL: Verify the resolved path is still under base_path
    # This prevents any potential path traversal attacks
    try:
        corpus_path.relative_to(base_path)
    except ValueError:
        # Path is outside base_path - SECURITY VIOLATION
        raise ValueError(f"Invalid path for corpus_id: {corpus_id}")

    return str(corpus_path)


def get_client(db_path: str = VECTOR_DB_PATH) -> chromadb.PersistentClient:
    """Return a cached Chroma persistent client or create one if not cached.

    SECURITY: Validates that db_path is safe before creating client.

    Args:
        db_path: Path to ChromaDB persistent directory

    Returns:
        chromadb.PersistentClient: Cached or new client instance

    Raises:
        ValueError: If db_path is outside allowed directory
    """
    # If custom db_path provided, validate it
    if db_path != VECTOR_DB_PATH:
        # Ensure it's under VECTOR_DB_PATH or is absolute trusted path
        resolved = Path(db_path).resolve()
        base = Path(VECTOR_DB_PATH).resolve()

        # Allow either under base path or explicitly configured paths
        try:
            resolved.relative_to(base)
        except ValueError:
            # Not under base - only allow if it's the configured path
            if db_path != VECTOR_DB_PATH:
                raise ValueError(f"Database path outside allowed directory: {db_path}")

    with _cache_lock:
        if db_path not in _client_cache:
            _client_cache[db_path] = chromadb.PersistentClient(path=db_path)
        return _client_cache[db_path]


def clear_client_cache(db_path: str | None = None) -> None:
    """Clear cached ChromaDB clients. Useful for cleanup or testing.

    Args:
        db_path: If provided, clear only this specific client. Otherwise clear all.
    """
    with _cache_lock:
        if db_path:
            _client_cache.pop(db_path, None)
        else:
            _client_cache.clear()


def get_or_create_collection(name: str = "default", db_path: str = VECTOR_DB_PATH) -> chromadb.Collection:
    """Return an existing Chroma collection or create it if missing.

    SECURITY: Validates collection name to prevent path traversal.

    Args:
        name: Collection name
        db_path: Path to ChromaDB persistent directory

    Returns:
        chromadb.Collection: The requested collection

    Raises:
        HTTPException: 422 if collection name is invalid
    """
    from api.validation import validate_collection_name

    # SECURITY: Validate collection name
    name = validate_collection_name(name)

    client = get_client(db_path)
    return client.get_or_create_collection(name=name)


def add_documents_to_index(
    collection_name: str,
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
    ids: list[str],
    db_path: str = VECTOR_DB_PATH,
) -> None:
    """Add new documents and embeddings to the specified collection."""
    collection = get_or_create_collection(collection_name, db_path)
    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )


def list_collection_names(db_path: str = VECTOR_DB_PATH) -> list[str]:
    """Return a list of all collection names in the vector store."""
    client = get_client(db_path)
    return [col.name for col in client.list_collections()]


def query_index(
    collection_name: str,
    query_text: str,
    db_path: str = VECTOR_DB_PATH,
    n_results: int = 5,
) -> dict:
    """Query ``collection_name`` using the embedding of ``query_text``."""
    from vector_store.embedder import get_openai_embedding

    collection = get_or_create_collection(collection_name, db_path)
    embedding = get_openai_embedding(query_text)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
    )
    return results


async def query_multiple_indexes(
    collection_names: list[str],
    query_text: str,
    db_path: str = VECTOR_DB_PATH,
    n_results: int = 5,
) -> dict:
    """Query several indexes in parallel and return aggregated results sorted by distance."""
    from vector_store.embedder import get_openai_embedding

    # Generate embedding once for all collections
    embedding = await asyncio.to_thread(get_openai_embedding, query_text)

    # Query collections in parallel
    async def _query_collection(name: str):
        """Query a single collection and return results."""
        def _query():
            collection = get_or_create_collection(name, db_path)
            return collection.query(query_embeddings=[embedding], n_results=n_results)
        return await asyncio.to_thread(_query)

    # Execute all queries in parallel
    results = await asyncio.gather(
        *[_query_collection(name) for name in collection_names]
    )

    # Aggregate results from all collections
    aggregated = []
    for res in results:
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        for doc_id, doc, meta, dist in zip(ids, docs, metas, dists):
            aggregated.append((dist, doc_id, doc, meta))

    # sort by distance (lower is more relevant)
    aggregated.sort(key=lambda x: x[0])

    ids = [a[1] for a in aggregated]
    docs = [a[2] for a in aggregated]
    metas = [a[3] for a in aggregated]
    dists = [a[0] for a in aggregated]

    return {
        "ids": [ids],
        "documents": [docs],
        "metadatas": [metas],
        "distances": [dists],
    }


async def stream_query_results(
    collection_names: list[str],
    query_text: str,
    db_path: str = VECTOR_DB_PATH,
    n_results: int = 5,
) -> AsyncGenerator[dict, None]:
    """Stream query results progressively as collections are queried.

    Yields results from each collection as they complete, rather than waiting
    for all collections to finish. This enables progressive rendering and better
    user experience for MCP clients.

    Args:
        collection_names: List of collection names to query
        query_text: Natural language query
        db_path: Path to ChromaDB persistent directory
        n_results: Number of results per collection

    Yields:
        dict: Individual result events with type:
            - type="result": A single document result
            - type="collection_complete": A collection finished processing
            - type="collection_error": A collection failed to query
    """
    from vector_store.embedder import get_openai_embedding

    # Generate embedding once for all collections
    embedding = await asyncio.to_thread(get_openai_embedding, query_text)

    # Stream results from each collection as they complete
    for collection_name in collection_names:
        try:
            # Query single collection
            def _query():
                collection = get_or_create_collection(collection_name, db_path)
                return collection.query(query_embeddings=[embedding], n_results=n_results)

            result = await asyncio.to_thread(_query)

            # Yield each document from this collection
            ids = result.get("ids", [[]])[0]
            docs = result.get("documents", [[]])[0]
            metas = result.get("metadatas", [[]])[0]
            dists = result.get("distances", [[]])[0]

            for idx, (doc_id, doc, metadata, distance) in enumerate(zip(ids, docs, metas, dists)):
                yield {
                    "type": "result",
                    "collection": collection_name,
                    "id": doc_id,
                    "text": doc,
                    "metadata": metadata,
                    "distance": distance,
                    "relevance_score": 1 - distance,  # Higher = more relevant
                    "rank": idx + 1,
                }

            # Yield collection completion event
            yield {
                "type": "collection_complete",
                "collection": collection_name,
                "num_results": len(ids),
            }

        except Exception as e:
            # Yield error for this collection, continue with others
            yield {
                "type": "collection_error",
                "collection": collection_name,
                "error": str(e),
            }


def compile_context(query_results: dict) -> str:
    """Return ordered unique context entries as a string."""

    docs = query_results.get("documents", [[]])[0]
    ids = query_results.get("ids", [[]])[0]
    metas = query_results.get("metadatas", [[]])[0]
    dists = query_results.get("distances", [[]])[0]

    # Results are already sorted by distance from query_multiple_indexes() or query_index()
    # No need to re-sort here
    combined = list(zip(dists, ids, docs, metas))

    context_parts = []
    seen = set()
    for dist, doc_id, doc, meta in combined:
        if doc is None or doc in seen:
            continue
        seen.add(doc)
        context_parts.append(doc)

    return "\n\n".join(context_parts)


def list_collections_with_metadata(db_path: str = VECTOR_DB_PATH) -> list[dict]:
    """Return available collections along with basic metadata."""
    client = get_client(db_path)
    collections = client.list_collections()
    results: list[dict] = []

    for col in collections:
        name = col.name
        collection = client.get_collection(name=name)
        try:
            docs = collection.get(include=["metadatas"])
            sources = [meta.get("source", "Unknown") for meta in docs["metadatas"]]
            unique_sources = sorted(set(sources))
            results.append(
                {
                    "name": name,
                    "files": unique_sources,
                    "num_chunks": len(docs["ids"]),
                }
            )
        except Exception as e:
            results.append({"name": name, "error": str(e)})

    return results


def delete_collection(collection_name: str, db_path: str = VECTOR_DB_PATH) -> dict:
    """Remove ``collection_name`` from the database."""
    from fastapi import HTTPException

    client = get_client(db_path)
    try:
        client.delete_collection(name=collection_name)
        return {"message": f"Collection '{collection_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
