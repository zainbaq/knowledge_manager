"""MCP resource schemas for Knowledge Manager.

Resources are read-only content that AI agents can access for context.
In the Knowledge Manager, corpuses are exposed as MCP resources.
"""

from typing import Dict, List


def corpus_to_resource(corpus: dict) -> Dict:
    """Convert a corpus to an MCP resource definition.

    Args:
        corpus: Corpus metadata dictionary from the API

    Returns:
        MCP resource definition
    """
    return {
        "uri": f"corpus://{corpus['id']}",
        "name": f"Corpus: {corpus.get('display_name', corpus.get('name', 'Unknown'))}",
        "description": corpus.get("description", "No description available"),
        "mimeType": "application/json",
    }


def get_resource_template(uri: str) -> Dict:
    """Get MCP resource content template.

    Args:
        uri: Resource URI (e.g., "corpus://123")

    Returns:
        MCP resource content structure
    """
    return {"uri": uri, "mimeType": "application/json", "text": ""}


def format_corpus_content(corpus: dict) -> str:
    """Format corpus metadata as readable content for MCP resources.

    Args:
        corpus: Corpus metadata dictionary

    Returns:
        Formatted text content
    """
    lines = [
        f"# {corpus.get('display_name', corpus.get('name'))}",
        "",
        "## Corpus Information",
        f"- **ID**: {corpus.get('id')}",
        f"- **Name**: {corpus.get('name')}",
        f"- **Category**: {corpus.get('category', 'Uncategorized')}",
        f"- **Version**: {corpus.get('version', 1)}",
        f"- **Owner**: {corpus.get('owner_username', 'Unknown')}",
        f"- **Status**: {'✅ Approved' if corpus.get('is_approved') else '⏳ Pending Approval'}",
        f"- **Visibility**: {'🌐 Public' if corpus.get('is_public') else '🔒 Private'}",
        "",
        "## Description",
        corpus.get("description", "No description provided."),
        "",
        "## Statistics",
        f"- **Chunks**: {corpus.get('chunk_count', 0)}",
        f"- **Files**: {corpus.get('file_count', 0)}",
        "",
    ]

    # Add permissions if available
    if "user_permission" in corpus and corpus["user_permission"]:
        lines.extend(
            [
                "## Your Access",
                f"- **Permission Level**: {corpus['user_permission'].upper()}",
                "",
            ]
        )

    return "\n".join(lines)


# MCP resource list response structure
def create_resource_list_response(resources: List[Dict]) -> Dict:
    """Create MCP resources/list response.

    Args:
        resources: List of resource definitions

    Returns:
        MCP response structure
    """
    return {"resources": resources}


# MCP resource read response structure
def create_resource_read_response(uri: str, content: str) -> Dict:
    """Create MCP resources/read response.

    Args:
        uri: Resource URI
        content: Resource content (formatted text or JSON)

    Returns:
        MCP response structure
    """
    return {
        "contents": [
            {"uri": uri, "mimeType": "text/markdown", "text": content}  # Use markdown for better readability
        ]
    }
