"""Wrapper functions around ChromaDB for simple vector operations."""

import chromadb
from chromadb.config import Settings
from config import VECTOR_DB_PATH

import chromadb

client = chromadb.PersistentClient(path=VECTOR_DB_PATH)

def get_or_create_collection(name="default"):
    """Return an existing Chroma collection or create it if missing."""
    return client.get_or_create_collection(name=name)

def add_documents_to_index(collection_name, documents, embeddings, metadatas, ids):
    """Add new documents and embeddings to the specified collection."""
    collection = get_or_create_collection(collection_name)
    collection.add(documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids)

def query_index(collection_name, query_text, n_results=5):
    """Query ``collection_name`` using the embedding of ``query_text``."""
    from vector_store.embedder import get_openai_embedding

    collection = get_or_create_collection(collection_name)
    embedding = get_openai_embedding(query_text)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
        # include=["documents"metadatas", "distances"]
    )
    return results

def compile_context(query_results):
    """Flatten query results into a list of unique context documents."""
    documents = [r for r in query_results['documents'][0] if r is not None]
    return list(set(documents))

def list_collections_with_metadata():
    """Return available collections along with basic metadata."""
    collections = client.list_collections()
    results = []

    for col in collections:
        name = col.name
        collection = client.get_collection(name=name)
        try:
            docs = collection.get(include=["metadatas"])
            sources = [meta.get("source", "Unknown") for meta in docs["metadatas"]]
            unique_sources = sorted(set(sources))
            results.append({
                "collection_name": name,
                "files": unique_sources,
                "num_chunks": len(docs["ids"]),
            })
        except Exception as e:
            results.append({
                "collection_name": name,
                "error": str(e)
            })

    return results

def delete_collection(collection_name: str):
    """Remove ``collection_name`` from the database."""
    try:
        client.delete_collection(name=collection_name)
        return {"message": f"Collection '{collection_name}' deleted successfully"}
    except Exception as e:
        return {"error": str(e)}
