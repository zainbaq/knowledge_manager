"""Wrapper functions around ChromaDB for simple vector operations."""

import chromadb
from config import VECTOR_DB_PATH


def get_client(db_path: str = VECTOR_DB_PATH):
    """Return a Chroma persistent client for the given path."""
    return chromadb.PersistentClient(path=db_path)


def get_or_create_collection(name: str = "default", db_path: str = VECTOR_DB_PATH):
    """Return an existing Chroma collection or create it if missing."""
    client = get_client(db_path)
    return client.get_or_create_collection(name=name)


def add_documents_to_index(
    collection_name: str,
    documents,
    embeddings,
    metadatas,
    ids,
    db_path: str = VECTOR_DB_PATH,
):
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
):
    """Query ``collection_name`` using the embedding of ``query_text``."""
    from vector_store.embedder import get_openai_embedding

    collection = get_or_create_collection(collection_name, db_path)
    embedding = get_openai_embedding(query_text)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
    )
    return results


def query_multiple_indexes(
    collection_names: list[str],
    query_text: str,
    db_path: str = VECTOR_DB_PATH,
    n_results: int = 5,
):
    """Query several indexes and return aggregated results sorted by distance."""
    from vector_store.embedder import get_openai_embedding

    embedding = get_openai_embedding(query_text)

    aggregated = []

    for name in collection_names:
        collection = get_or_create_collection(name, db_path)
        res = collection.query(query_embeddings=[embedding], n_results=n_results)
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


def compile_context(query_results):
    """Return ordered unique context entries with metadata."""

    docs = query_results.get("documents", [[]])[0]
    ids = query_results.get("ids", [[]])[0]
    metas = query_results.get("metadatas", [[]])[0]
    dists = query_results.get("distances", [[]])[0]

    combined = list(zip(dists, ids, docs, metas))
    combined.sort(key=lambda x: x[0])

    context = []
    seen = set()
    for dist, doc_id, doc, meta in combined:
        if doc is None or doc in seen:
            continue
        seen.add(doc)
        context.append(
            {
                "id": doc_id,
                "text": doc,
                "metadata": meta,
                "distance": dist,
            }
        )

    return context


def list_collections_with_metadata(db_path: str = VECTOR_DB_PATH):
    """Return available collections along with basic metadata."""
    client = get_client(db_path)
    collections = client.list_collections()
    results = []

    for col in collections:
        name = col.name
        collection = client.get_collection(name=name)
        try:
            docs = collection.get(include=["metadatas"])
            sources = [meta.get("source", "Unknown") for meta in docs["metadatas"]]
            unique_sources = sorted(set(sources))
            results.append(
                {
                    "collection_name": name,
                    "files": unique_sources,
                    "num_chunks": len(docs["ids"]),
                }
            )
        except Exception as e:
            results.append({"collection_name": name, "error": str(e)})

    return results


def delete_collection(collection_name: str, db_path: str = VECTOR_DB_PATH):
    """Remove ``collection_name`` from the database."""
    client = get_client(db_path)
    try:
        client.delete_collection(name=collection_name)
        return {"message": f"Collection '{collection_name}' deleted successfully"}
    except Exception as e:
        return {"error": str(e)}
