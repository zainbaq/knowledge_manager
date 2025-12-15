"""MCP tool and resource handlers.

This module routes MCP tool calls and resource requests to the existing
Knowledge Manager API endpoints, avoiding code duplication.
"""

import json
from typing import Dict

from fastapi import HTTPException, Request

from api.models.corpus_requests import CorpusQueryRequest
from api.models.requests import QueryRequest
from api.v1.corpus import get_corpus, list_corpuses as list_corpuses_endpoint, query_corpus
from api.v1.endpoints import list_indexes, query
from logging_config import get_logger
from mcp.schemas import corpus_to_resource, create_resource_list_response, create_resource_read_response, format_corpus_content
from mcp.tools import get_tool_definitions, validate_tool_arguments

logger = get_logger(__name__)


async def handle_tools_list() -> Dict:
    """Handle MCP tools/list request.

    Returns:
        Dict: MCP tools list response
    """
    tools = get_tool_definitions()
    logger.debug(f"Returning {len(tools)} MCP tools")
    return {"tools": tools}


async def handle_tools_call(tool_name: str, arguments: dict, current_user: dict, request: Request) -> Dict:
    """Handle MCP tools/call request.

    Routes the tool call to the appropriate API endpoint.

    Args:
        tool_name: Name of the tool to call
        arguments: Tool arguments
        current_user: Authenticated user
        request: FastAPI request object

    Returns:
        Dict: Tool execution result

    Raises:
        HTTPException: If tool not found or execution fails
    """
    # Validate arguments against schema
    try:
        validate_tool_arguments(tool_name, arguments)
    except (KeyError, ValueError) as e:
        logger.warning(f"Invalid tool call: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    logger.info(f"Executing MCP tool '{tool_name}' for user {current_user['username']}")

    # Route to appropriate handler
    if tool_name == "query_knowledge":
        return await _handle_query_knowledge(arguments, current_user, request)

    elif tool_name == "query_corpus":
        return await _handle_query_corpus(arguments, current_user, request)

    elif tool_name == "list_collections":
        return await _handle_list_collections(current_user, request)

    elif tool_name == "list_corpuses":
        return await _handle_list_corpuses(arguments, current_user, request)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")


async def handle_resources_list(current_user: dict, request: Request) -> Dict:
    """Handle MCP resources/list request.

    Lists all accessible corpuses as MCP resources.

    Args:
        current_user: Authenticated user
        request: FastAPI request object

    Returns:
        Dict: MCP resources list response
    """
    logger.info(f"Listing MCP resources for user {current_user['username']}")

    # Get all accessible corpuses
    response = await list_corpuses_endpoint(
        request=request,
        current_user=current_user,
    )

    corpuses = response.corpuses

    # Convert corpuses to MCP resources
    resources = [corpus_to_resource(corpus.dict()) for corpus in corpuses]

    logger.debug(f"Returning {len(resources)} MCP resources")

    return create_resource_list_response(resources)


async def handle_resources_read(uri: str, current_user: dict, request: Request) -> Dict:
    """Handle MCP resources/read request.

    Reads a specific resource (corpus metadata).

    Args:
        uri: Resource URI (e.g., "corpus://123")
        current_user: Authenticated user
        request: FastAPI request object

    Returns:
        Dict: MCP resource content response

    Raises:
        HTTPException: If resource not found or invalid URI
    """
    logger.info(f"Reading MCP resource '{uri}' for user {current_user['username']}")

    if not uri.startswith("corpus://"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource URI: {uri}. Only 'corpus://' URIs are supported.",
        )

    # Extract corpus ID
    try:
        corpus_id_str = uri.replace("corpus://", "")
        corpus_id = int(corpus_id_str)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid corpus ID in URI: {uri}. Must be an integer."
        )

    # Get corpus details
    corpus = await get_corpus(
        request=request,
        corpus_id=corpus_id,
        current_user=current_user,
    )

    # Format as readable content
    content = format_corpus_content(corpus.dict())

    logger.debug(f"Returning content for corpus {corpus_id}")

    return create_resource_read_response(uri, content)


# Private helper functions for tool handlers


async def _handle_query_knowledge(arguments: dict, current_user: dict, request: Request) -> Dict:
    """Handle query_knowledge tool call."""
    # Build QueryRequest
    query_request = QueryRequest(
        query=arguments["query"],
        collection=None,  # Will search all if not specified
        collections=arguments.get("collections"),
    )

    # Call existing query endpoint
    response = await query(
        request=request,
        payload=query_request,
        current_user=current_user,
    )

    # Return MCP-formatted result
    return {
        "context": response.context,
        "num_results": len(response.raw_results.get("ids", [[]])[0]),
        "collections_searched": (
            arguments.get("collections")
            if arguments.get("collections")
            else "all accessible collections"
        ),
    }


async def _handle_query_corpus(arguments: dict, current_user: dict, request: Request) -> Dict:
    """Handle query_corpus tool call."""
    corpus_id = arguments["corpus_id"]

    # Build CorpusQueryRequest
    query_request = CorpusQueryRequest(
        query=arguments["query"], n_results=arguments.get("n_results", 5)
    )

    # Call existing corpus query endpoint
    response = await query_corpus(
        request=request,
        corpus_id=corpus_id,
        query_request=query_request,
        current_user=current_user,
    )

    # Return MCP-formatted result
    return {
        "context": response.context,
        "num_results": len(response.raw_results.get("ids", [[]])[0]),
        "corpus_id": corpus_id,
    }


async def _handle_list_collections(current_user: dict, request: Request) -> Dict:
    """Handle list_collections tool call."""
    # Call existing list endpoint
    response = await list_indexes(
        request=request,
        current_user=current_user,
    )

    collections = response.get("collections", [])

    # Return MCP-formatted result
    return {
        "collections": collections,
        "count": len(collections),
    }


async def _handle_list_corpuses(arguments: dict, current_user: dict, request: Request) -> Dict:
    """Handle list_corpuses tool call."""
    # Call existing list corpuses endpoint
    response = await list_corpuses_endpoint(
        request=request,
        current_user=current_user,
    )

    corpuses = response.corpuses

    # Apply filters
    category = arguments.get("category")
    approved_only = arguments.get("approved_only", True)

    filtered_corpuses = []
    for corpus in corpuses:
        corpus_dict = corpus.dict()

        # Category filter
        if category and corpus_dict.get("category") != category:
            continue

        # Approval filter
        if approved_only and not corpus_dict.get("is_approved"):
            continue

        filtered_corpuses.append(corpus_dict)

    # Return MCP-formatted result
    return {
        "corpuses": filtered_corpuses,
        "count": len(filtered_corpuses),
        "filters": {"category": category, "approved_only": approved_only},
    }
