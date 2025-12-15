#!/usr/bin/env python3
"""Synchronous Python client for Knowledge Manager API.

This example demonstrates how to use the Knowledge Manager API
from a Python application using the requests library.
"""

import requests
from typing import List, Optional


class KnowledgeManagerClient:
    """Simple synchronous client for Knowledge Manager API."""

    def __init__(self, base_url: str, api_key: str):
        """Initialize the client.

        Args:
            base_url: Base URL of the API (e.g., "http://localhost:8000")
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})

    def upload_documents(self, collection: str, file_paths: List[str]) -> dict:
        """Upload documents to a collection.

        Args:
            collection: Name of the collection
            file_paths: List of file paths to upload

        Returns:
            Response dict with 'message' and 'indexed_chunks'

        Raises:
            requests.HTTPError: If the request fails
        """
        files = []
        for file_path in file_paths:
            with open(file_path, "rb") as f:
                files.append(("files", (file_path, f.read(), "application/octet-stream")))

        response = self.session.post(
            f"{self.base_url}/api/v1/create-index/",
            data={"collection": collection},
            files=files,
        )
        response.raise_for_status()
        return response.json()

    def update_collection(self, collection: str, file_paths: List[str]) -> dict:
        """Add documents to an existing collection.

        Args:
            collection: Name of the collection
            file_paths: List of file paths to add

        Returns:
            Response dict with 'message' and 'indexed_chunks'

        Raises:
            requests.HTTPError: If the request fails
        """
        files = []
        for file_path in file_paths:
            with open(file_path, "rb") as f:
                files.append(("files", (file_path, f.read(), "application/octet-stream")))

        response = self.session.post(
            f"{self.base_url}/api/v1/update-index/",
            data={"collection": collection},
            files=files,
        )
        response.raise_for_status()
        return response.json()

    def query(
        self,
        query: str,
        collection: Optional[str] = None,
        collections: Optional[List[str]] = None,
    ) -> str:
        """Query one or more collections.

        Args:
            query: Search query text
            collection: Single collection to query (optional)
            collections: Multiple collections to query (optional)

        Returns:
            Compiled context string from query results

        Raises:
            requests.HTTPError: If the request fails
        """
        payload = {"query": query}
        if collection:
            payload["collection"] = collection
        elif collections:
            payload["collections"] = collections

        response = self.session.post(f"{self.base_url}/api/v1/query/", json=payload)
        response.raise_for_status()
        return response.json()["context"]

    def list_collections(self) -> List[dict]:
        """List all collections.

        Returns:
            List of collection metadata dicts

        Raises:
            requests.HTTPError: If the request fails
        """
        response = self.session.get(f"{self.base_url}/api/v1/list-indexes/")
        response.raise_for_status()
        return response.json()["collections"]

    def delete_collection(self, collection: str) -> dict:
        """Delete a collection.

        Args:
            collection: Name of the collection to delete

        Returns:
            Response dict with 'message'

        Raises:
            requests.HTTPError: If the request fails
        """
        response = self.session.delete(
            f"{self.base_url}/api/v1/delete-index/{collection}"
        )
        response.raise_for_status()
        return response.json()


def main():
    """Example usage of the Knowledge Manager client."""
    # Initialize client (replace with your API key)
    client = KnowledgeManagerClient(
        base_url="http://localhost:8000", api_key="your-api-key-here"
    )

    # Example 1: Upload documents
    print("Uploading documents...")
    result = client.upload_documents(
        collection="my_docs", file_paths=["document1.txt", "document2.pdf"]
    )
    print(f"✓ {result['message']}")
    print(f"  Indexed {result['indexed_chunks']} chunks")

    # Example 2: Query a collection
    print("\nQuerying collection...")
    context = client.query(query="What is the main topic?", collection="my_docs")
    print(f"✓ Query result:")
    print(f"  {context[:200]}...")  # Print first 200 chars

    # Example 3: List all collections
    print("\nListing collections...")
    collections = client.list_collections()
    for col in collections:
        print(f"✓ Collection: {col['name']}")
        print(f"  Files: {', '.join(col['files'])}")
        print(f"  Chunks: {col['num_chunks']}")

    # Example 4: Update existing collection
    print("\nUpdating collection...")
    result = client.update_collection(collection="my_docs", file_paths=["document3.txt"])
    print(f"✓ {result['message']}")

    # Example 5: Query multiple collections
    print("\nQuerying multiple collections...")
    context = client.query(query="API documentation", collections=["my_docs", "references"])
    print(f"✓ Multi-collection query result:")
    print(f"  {context[:200]}...")

    # Example 6: Delete collection
    # Uncomment to delete
    # print("\nDeleting collection...")
    # result = client.delete_collection("my_docs")
    # print(f"✓ {result['message']}")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"✗ API Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json().get("detail", "Unknown error")
                print(f"  Detail: {error_detail}")
            except:
                print(f"  Response: {e.response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")
