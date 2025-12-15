"""Streaming MCP client example for Knowledge Manager.

This example demonstrates how to use the Server-Sent Events (SSE) streaming endpoint
to receive progressive query results from the Knowledge Manager.

Requirements:
    pip install httpx

Usage:
    python streaming_client.py
"""

import asyncio
import json
from typing import Optional

import httpx


async def stream_query(
    base_url: str,
    api_key: str,
    query: str,
    collections: Optional[list[str]] = None,
    n_results: int = 5,
):
    """Stream query results via Server-Sent Events.

    Args:
        base_url: Base URL of the Knowledge Manager API (e.g., "http://localhost:8000")
        api_key: API key for authentication
        query: Natural language query to search for
        collections: Specific collections to search (omit to search all)
        n_results: Number of results to return per collection

    Yields:
        Dict: SSE events as they arrive
    """
    stream_url = f"{base_url.rstrip('/')}/api/v1/mcp/query/stream"

    payload = {"query": query, "n_results": n_results}

    if collections:
        payload["collections"] = collections

    headers = {"X-API-Key": api_key, "Accept": "text/event-stream"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            stream_url,
            json=payload,
            headers=headers,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                # SSE format: "event: <event_name>" or "data: <json_data>"
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    try:
                        data = json.loads(data_str)
                        yield data
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse SSE data: {data_str}")


async def main():
    """Example usage of streaming query."""
    # Configuration (replace with your values)
    BASE_URL = "http://localhost:8000"
    API_KEY = "your-api-key-here"
    QUERY = "What is Python?"

    print("=" * 70)
    print("Knowledge Manager Streaming MCP Client Example")
    print("=" * 70)
    print(f"\nQuery: '{QUERY}'")
    print("Streaming results...\n")

    result_count = 0
    collections_seen = set()

    try:
        async for event in stream_query(
            base_url=BASE_URL,
            api_key=API_KEY,
            query=QUERY,
            n_results=5,
        ):
            event_type = event.get("type")

            if event_type == "metadata":
                # Initial metadata about the query
                collections = event.get("collections", [])
                n_results = event.get("n_results", 0)
                print(f"📋 Metadata:")
                print(f"   Collections: {', '.join(collections)}")
                print(f"   Results per collection: {n_results}\n")

            elif event_type == "result":
                # Individual document result
                result_count += 1
                collection = event.get("collection")
                collections_seen.add(collection)
                text = event.get("text", "")
                relevance = event.get("relevance_score", 0)
                rank = event.get("rank", 0)

                print(f"📄 Result #{result_count} from '{collection}' (rank {rank}):")
                print(f"   Relevance: {relevance:.3f}")
                print(f"   Text: {text[:100]}...")
                print()

            elif event_type == "collection_complete":
                # A collection finished processing
                collection = event.get("collection")
                num_results = event.get("num_results", 0)
                print(f"✅ Collection '{collection}' complete: {num_results} results\n")

            elif event_type == "collection_error":
                # A collection failed to query
                collection = event.get("collection")
                error = event.get("error", "Unknown error")
                print(f"❌ Error querying collection '{collection}': {error}\n")

            elif event_type == "done":
                # Query complete
                total_results = event.get("total_results", 0)
                print("=" * 70)
                print(f"🎉 Query complete!")
                print(f"   Total results: {total_results}")
                print(f"   Collections searched: {len(collections_seen)}")
                print("=" * 70)

            elif event_type == "error":
                # Fatal error occurred
                error_code = event.get("error_code", "unknown")
                detail = event.get("detail", "Unknown error")
                print("=" * 70)
                print(f"❌ Error occurred:")
                print(f"   Code: {error_code}")
                print(f"   Detail: {detail}")
                print("=" * 70)

    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"   Detail: {e.response.text}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


# Advanced example: Process results in real-time
async def process_streaming_results():
    """Example of processing streaming results as they arrive."""
    BASE_URL = "http://localhost:8000"
    API_KEY = "your-api-key-here"

    # Accumulate results by collection
    results_by_collection = {}

    print("\n" + "=" * 70)
    print("Advanced Example: Real-time Result Processing")
    print("=" * 70)

    async for event in stream_query(
        base_url=BASE_URL,
        api_key=API_KEY,
        query="Explain machine learning",
        n_results=3,
    ):
        if event.get("type") == "result":
            collection = event.get("collection")
            text = event.get("text")

            if collection not in results_by_collection:
                results_by_collection[collection] = []

            results_by_collection[collection].append(text)

            # Process result immediately as it arrives
            print(f"Processing result from '{collection}' in real-time...")

        elif event.get("type") == "done":
            print("\n📊 Final Results Summary:")
            for collection, texts in results_by_collection.items():
                print(f"  {collection}: {len(texts)} results")
                # Could send to downstream processing, cache, etc.


if __name__ == "__main__":
    # Run the basic example
    asyncio.run(main())

    # Uncomment to run the advanced example
    # asyncio.run(process_streaming_results())
