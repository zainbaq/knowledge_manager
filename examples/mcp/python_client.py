"""Simple Python MCP client for Knowledge Manager.

This example demonstrates how to interact with the Knowledge Manager MCP server
using the JSON-RPC 2.0 protocol.

Requirements:
    pip install requests

Usage:
    python python_client.py
"""

import json
from typing import Any, Dict, List, Optional

import requests


class KnowledgeManagerMCPClient:
    """Simple MCP client for Knowledge Manager."""

    def __init__(self, base_url: str, api_key: str):
        """Initialize the MCP client.

        Args:
            base_url: Base URL of the Knowledge Manager API (e.g., "http://localhost:8000")
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.mcp_url = f"{self.base_url}/api/v1/mcp/"
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        self.request_id = 0

    def _make_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """Make a JSON-RPC 2.0 request to the MCP server.

        Args:
            method: MCP method name (e.g., "tools/list", "tools/call")
            params: Method parameters

        Returns:
            Response result dict

        Raises:
            Exception: If the request fails or returns an error
        """
        self.request_id += 1

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.request_id,
        }

        response = requests.post(self.mcp_url, json=payload, headers=self.headers)
        response.raise_for_status()

        data = response.json()

        if "error" in data and data["error"]:
            error = data["error"]
            raise Exception(f"MCP Error {error['code']}: {error['message']}")

        return data.get("result", {})

    def list_tools(self) -> List[Dict]:
        """List all available MCP tools.

        Returns:
            List of tool definitions with names, descriptions, and input schemas
        """
        result = self._make_request("tools/list")
        return result.get("tools", [])

    def query_knowledge(
        self,
        query: str,
        collections: Optional[List[str]] = None,
        n_results: int = 5,
    ) -> Dict[str, Any]:
        """Search indexed documents for relevant context.

        Args:
            query: Natural language query to search for
            collections: Specific collections to search (omit to search all)
            n_results: Number of results to return per collection

        Returns:
            Dict with "context", "num_results", and "collections_searched" keys
        """
        arguments = {"query": query, "n_results": n_results}

        if collections:
            arguments["collections"] = collections

        result = self._make_request(
            "tools/call",
            {"name": "query_knowledge", "arguments": arguments},
        )

        return result

    def query_corpus(self, corpus_id: int, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Query a specific curated corpus by ID.

        Args:
            corpus_id: Corpus ID to query
            query: Natural language query to search for
            n_results: Number of results to return

        Returns:
            Dict with "context", "num_results", and "corpus_id" keys
        """
        result = self._make_request(
            "tools/call",
            {
                "name": "query_corpus",
                "arguments": {
                    "corpus_id": corpus_id,
                    "query": query,
                    "n_results": n_results,
                },
            },
        )

        return result

    def list_collections(self) -> Dict[str, Any]:
        """List all accessible document collections with metadata.

        Returns:
            Dict with "collections" and "count" keys
        """
        result = self._make_request("tools/call", {"name": "list_collections"})
        return result

    def list_corpuses(
        self,
        category: Optional[str] = None,
        approved_only: bool = True,
    ) -> Dict[str, Any]:
        """List available curated corpuses.

        Args:
            category: Filter by category (legal, medical, research, general, technical)
            approved_only: Only show admin-approved corpuses

        Returns:
            Dict with "corpuses", "count", and "filters" keys
        """
        arguments = {"approved_only": approved_only}

        if category:
            arguments["category"] = category

        result = self._make_request(
            "tools/call",
            {"name": "list_corpuses", "arguments": arguments},
        )

        return result

    def list_resources(self) -> List[Dict]:
        """List all available MCP resources (corpuses).

        Returns:
            List of resource definitions with URIs, names, and descriptions
        """
        result = self._make_request("resources/list")
        return result.get("resources", [])

    def read_resource(self, uri: str) -> str:
        """Read a specific MCP resource.

        Args:
            uri: Resource URI (e.g., "corpus://123")

        Returns:
            Resource content as markdown text
        """
        result = self._make_request("resources/read", {"uri": uri})
        contents = result.get("contents", [])

        if contents:
            return contents[0].get("text", "")

        return ""


# Example usage
def main():
    """Example usage of the MCP client."""
    # Initialize client (replace with your API key)
    client = KnowledgeManagerMCPClient(
        base_url="http://localhost:8000",
        api_key="your-api-key-here",
    )

    print("=" * 60)
    print("Knowledge Manager MCP Client Example")
    print("=" * 60)

    # List available tools
    print("\n1. Listing available tools...")
    tools = client.list_tools()
    print(f"Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description'][:60]}...")

    # List collections
    print("\n2. Listing collections...")
    collections_result = client.list_collections()
    collections = collections_result.get("collections", [])
    print(f"Found {len(collections)} collections:")
    for collection in collections:
        print(f"  - {collection['name']}: {collection['num_chunks']} chunks")

    # Query knowledge
    print("\n3. Querying knowledge...")
    query = "What is Python?"
    result = client.query_knowledge(query, n_results=3)
    print(f"Query: '{query}'")
    print(f"Results: {result['num_results']} documents found")
    print(f"Context (first 200 chars):\n{result['context'][:200]}...")

    # List resources
    print("\n4. Listing MCP resources...")
    resources = client.list_resources()
    print(f"Found {len(resources)} resources:")
    for resource in resources[:3]:  # Show first 3
        print(f"  - {resource['uri']}: {resource['name']}")

    # Read a resource (if any exist)
    if resources:
        print("\n5. Reading first resource...")
        uri = resources[0]["uri"]
        content = client.read_resource(uri)
        print(f"Resource: {uri}")
        print(f"Content (first 300 chars):\n{content[:300]}...")

    print("\n" + "=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
