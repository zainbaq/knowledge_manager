#!/usr/bin/env python3
"""Async Python client for Knowledge Manager API.

This example demonstrates how to use the Knowledge Manager API
asynchronously for high-performance integrations.
"""

import asyncio
from typing import List, Optional

import aiohttp


class AsyncKnowledgeManagerClient:
    """Async client for Knowledge Manager API."""

    def __init__(self, base_url: str, api_key: str):
        """Initialize the client.

        Args:
            base_url: Base URL of the API (e.g., "http://localhost:8000")
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def query(
        self,
        query: str,
        collection: Optional[str] = None,
        collections: Optional[List[str]] = None,
    ) -> str:
        """Query one or more collections asynchronously.

        Args:
            query: Search query text
            collection: Single collection to query (optional)
            collections: Multiple collections to query (optional)

        Returns:
            Compiled context string from query results
        """
        payload = {"query": query}
        if collection:
            payload["collection"] = collection
        elif collections:
            payload["collections"] = collections

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/query/",
                json=payload,
                headers={"X-API-Key": self.api_key},
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data["context"]

    async def list_collections(self) -> List[dict]:
        """List all collections asynchronously.

        Returns:
            List of collection metadata dicts
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/v1/list-indexes/",
                headers={"X-API-Key": self.api_key},
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data["collections"]


async def main():
    """Example async usage of the Knowledge Manager client."""
    # Initialize client (replace with your API key)
    client = AsyncKnowledgeManagerClient(
        base_url="http://localhost:8000", api_key="your-api-key-here"
    )

    # Example 1: Single async query
    print("Querying collection...")
    context = await client.query(query="What are the main features?", collection="documentation")
    print(f"✓ Query result:")
    print(f"  {context[:200]}...")

    # Example 2: Multiple concurrent queries
    print("\nRunning concurrent queries...")
    queries = [
        client.query("feature A", collection="docs"),
        client.query("feature B", collection="docs"),
        client.query("feature C", collection="docs"),
    ]
    results = await asyncio.gather(*queries)
    for i, result in enumerate(results, 1):
        print(f"✓ Query {i}: {result[:100]}...")

    # Example 3: List collections
    print("\nListing collections...")
    collections = await client.list_collections()
    for col in collections:
        print(f"✓ Collection: {col['name']} ({col['num_chunks']} chunks)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except aiohttp.ClientError as e:
        print(f"✗ API Error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
