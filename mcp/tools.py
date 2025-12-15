"""MCP tool definitions for Knowledge Manager.

This module defines the tools that AI agents can call via the MCP protocol.
Each tool corresponds to a Knowledge Manager operation (query, list, etc.).
"""

from typing import Dict, List

# MCP Tool Definitions following the MCP spec
# https://modelcontextprotocol.io/docs/concepts/tools


def get_tool_definitions() -> List[Dict]:
    """Get all MCP tool definitions.

    Returns:
        List of tool definition dictionaries following MCP spec
    """
    return [
        {
            "name": "query_knowledge",
            "description": "Search indexed documents for relevant context using semantic search. "
            "Returns the most relevant text chunks from user's collections based on the query.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query to search for",
                        "minLength": 1,
                        "maxLength": 1000,
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific collections to search. Omit to search all accessible collections.",
                        "maxItems": 20,
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results to return per collection",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "query_corpus",
            "description": "Query a specific curated corpus by ID. "
            "Corpuses are pre-indexed knowledge bases (e.g., legal documents, medical literature). "
            "Requires read permission for the corpus.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "corpus_id": {
                        "type": "integer",
                        "description": "Corpus ID to query",
                        "minimum": 1,
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural language query to search for",
                        "minLength": 1,
                        "maxLength": 1000,
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["corpus_id", "query"],
            },
        },
        {
            "name": "list_collections",
            "description": "List all accessible document collections with metadata. "
            "Returns collection names, file counts, and chunk counts.",
            "inputSchema": {
                "type": "object",
                "properties": {},  # No parameters required
            },
        },
        {
            "name": "list_corpuses",
            "description": "List available curated corpuses. "
            "Returns corpuses the user can access, with optional filtering by category and approval status.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category",
                        "enum": ["legal", "medical", "research", "general", "technical"],
                    },
                    "approved_only": {
                        "type": "boolean",
                        "default": True,
                        "description": "Only show admin-approved corpuses",
                    },
                },
            },
        },
    ]


def get_tool_by_name(name: str) -> Dict:
    """Get a specific tool definition by name.

    Args:
        name: Tool name

    Returns:
        Tool definition dictionary

    Raises:
        KeyError: If tool name not found
    """
    tools = {tool["name"]: tool for tool in get_tool_definitions()}

    if name not in tools:
        raise KeyError(f"Tool '{name}' not found. Available tools: {list(tools.keys())}")

    return tools[name]


def validate_tool_arguments(tool_name: str, arguments: dict) -> None:
    """Validate tool arguments against the tool's input schema.

    Args:
        tool_name: Name of the tool
        arguments: Arguments to validate

    Raises:
        ValueError: If arguments are invalid
        KeyError: If tool not found
    """
    tool = get_tool_by_name(tool_name)
    schema = tool["inputSchema"]
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Check required fields
    for field in required:
        if field not in arguments:
            raise ValueError(f"Missing required field '{field}' for tool '{tool_name}'")

    # Validate each argument
    for arg_name, arg_value in arguments.items():
        if arg_name not in properties:
            raise ValueError(
                f"Unknown argument '{arg_name}' for tool '{tool_name}'. "
                f"Valid arguments: {list(properties.keys())}"
            )

        prop = properties[arg_name]
        prop_type = prop.get("type")

        # Type checking
        if prop_type == "string" and not isinstance(arg_value, str):
            raise ValueError(f"Argument '{arg_name}' must be a string")
        elif prop_type == "integer" and not isinstance(arg_value, int):
            raise ValueError(f"Argument '{arg_name}' must be an integer")
        elif prop_type == "boolean" and not isinstance(arg_value, bool):
            raise ValueError(f"Argument '{arg_name}' must be a boolean")
        elif prop_type == "array" and not isinstance(arg_value, list):
            raise ValueError(f"Argument '{arg_name}' must be an array")

        # Range validation
        if prop_type in ("string", "array"):
            min_len = prop.get("minLength") or prop.get("minItems")
            max_len = prop.get("maxLength") or prop.get("maxItems")

            if min_len and len(arg_value) < min_len:
                raise ValueError(
                    f"Argument '{arg_name}' must have at least {min_len} "
                    f"{'characters' if prop_type == 'string' else 'items'}"
                )
            if max_len and len(arg_value) > max_len:
                raise ValueError(
                    f"Argument '{arg_name}' must have at most {max_len} "
                    f"{'characters' if prop_type == 'string' else 'items'}"
                )

        if prop_type == "integer":
            minimum = prop.get("minimum")
            maximum = prop.get("maximum")

            if minimum is not None and arg_value < minimum:
                raise ValueError(f"Argument '{arg_name}' must be at least {minimum}")
            if maximum is not None and arg_value > maximum:
                raise ValueError(f"Argument '{arg_name}' must be at most {maximum}")

        # Enum validation
        if "enum" in prop and arg_value not in prop["enum"]:
            raise ValueError(
                f"Argument '{arg_name}' must be one of {prop['enum']}, got '{arg_value}'"
            )
