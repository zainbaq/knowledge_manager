"""MCP-specific endpoints for API v1.

This module provides:
- JSON-RPC 2.0 endpoint for MCP protocol (tools and resources)
- Server-Sent Events (SSE) endpoint for streaming query results
"""

import json
from typing import Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from api.auth import get_current_user
from api.models.mcp_errors import to_mcp_error_code
from api.models.requests import QueryRequest
from api.rate_limiting import limiter
from config import QUERY_RATE_LIMIT
from logging_config import get_logger
from mcp.handlers import (
    handle_resources_list,
    handle_resources_read,
    handle_tools_call,
    handle_tools_list,
)
from vector_store.vector_index import list_collection_names, stream_query_results

logger = get_logger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


# MCP Protocol Models (JSON-RPC 2.0)


class MCPRequest(BaseModel):
    """MCP protocol request following JSON-RPC 2.0 specification."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str = Field(..., description="MCP method to call (e.g., tools/list, tools/call)")
    params: dict = Field(default_factory=dict, description="Method parameters")
    id: Optional[Union[str, int]] = Field(None, description="Request ID for matching responses")


class MCPError(BaseModel):
    """MCP error response structure."""

    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[dict] = Field(None, description="Additional error data")


class MCPResponse(BaseModel):
    """MCP protocol response following JSON-RPC 2.0 specification."""

    jsonrpc: Literal["2.0"] = "2.0"
    result: Optional[dict] = Field(None, description="Successful result")
    error: Optional[MCPError] = Field(None, description="Error details if failed")
    id: Optional[Union[str, int]] = Field(None, description="Request ID from original request")


# MCP JSON-RPC Endpoint


@router.post("/")
@limiter.limit(QUERY_RATE_LIMIT)
async def mcp_endpoint(
    mcp_request: MCPRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Main MCP server endpoint implementing JSON-RPC 2.0 protocol.

    This endpoint handles all MCP protocol methods including:
    - tools/list: List available MCP tools
    - tools/call: Execute an MCP tool
    - resources/list: List available MCP resources
    - resources/read: Read an MCP resource

    Args:
        mcp_request: MCP request following JSON-RPC 2.0 format
        request: FastAPI request object (for rate limiting and auth)
        current_user: Authenticated user from API key

    Returns:
        MCPResponse: JSON-RPC 2.0 response with result or error

    Example Request (tools/list):
        {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1
        }

    Example Response (tools/list):
        {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "query_knowledge",
                        "description": "Search indexed documents...",
                        "inputSchema": {...}
                    }
                ]
            },
            "id": 1
        }

    Example Request (tools/call):
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "query_knowledge",
                "arguments": {
                    "query": "What is Python?",
                    "n_results": 5
                }
            },
            "id": 2
        }

    Example Response (tools/call):
        {
            "jsonrpc": "2.0",
            "result": {
                "context": "Python is a high-level programming language...",
                "num_results": 5,
                "collections_searched": "all accessible collections"
            },
            "id": 2
        }
    """
    method = mcp_request.method
    params = mcp_request.params

    logger.info(
        f"MCP request from user {current_user['username']}: "
        f"method={method}, request_id={mcp_request.id}"
    )

    try:
        # Route to appropriate handler based on method
        if method == "tools/list":
            result = await handle_tools_list()

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                raise HTTPException(
                    status_code=400,
                    detail="Missing required parameter 'name' for tools/call",
                )

            result = await handle_tools_call(tool_name, arguments, current_user, request)

        elif method == "resources/list":
            result = await handle_resources_list(current_user, request)

        elif method == "resources/read":
            uri = params.get("uri")

            if not uri:
                raise HTTPException(
                    status_code=400,
                    detail="Missing required parameter 'uri' for resources/read",
                )

            result = await handle_resources_read(uri, current_user, request)

        else:
            # Unknown MCP method
            logger.warning(f"Unknown MCP method requested: {method}")
            return MCPResponse(
                error=MCPError(
                    code=-32601,  # Method not found (JSON-RPC standard)
                    message=f"Unknown MCP method: {method}",
                    data={
                        "available_methods": [
                            "tools/list",
                            "tools/call",
                            "resources/list",
                            "resources/read",
                        ]
                    },
                ),
                id=mcp_request.id,
            )

        # Success response
        logger.info(
            f"MCP request completed successfully for user {current_user['username']}: "
            f"method={method}, request_id={mcp_request.id}"
        )

        return MCPResponse(
            result=result,
            id=mcp_request.id,
        )

    except HTTPException as e:
        # HTTP exceptions from handlers
        logger.error(
            f"MCP request failed for user {current_user['username']}: "
            f"method={method}, status={e.status_code}, detail={e.detail}"
        )

        return MCPResponse(
            error=MCPError(
                code=e.status_code,
                message=e.detail,
                data={"http_status": e.status_code},
            ),
            id=mcp_request.id,
        )

    except Exception as e:
        # Unexpected errors
        logger.exception(
            f"Unexpected error in MCP request for user {current_user['username']}: "
            f"method={method}, error={e}"
        )

        return MCPResponse(
            error=MCPError(
                code=-32603,  # Internal error (JSON-RPC standard)
                message=f"Internal server error: {str(e)}",
                data={"error_type": type(e).__name__},
            ),
            id=mcp_request.id,
        )


# MCP Streaming Endpoint


@router.post("/query/stream")
@limiter.limit(QUERY_RATE_LIMIT)
async def stream_query(
    request: Request,
    payload: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """Stream query results via Server-Sent Events (SSE).

    This endpoint provides progressive query results as collections are searched,
    enabling better user experience and real-time feedback for MCP clients.

    Args:
        request: FastAPI request object (for rate limiting)
        payload: Query request with query text and optional collections
        current_user: Authenticated user from API key

    Returns:
        EventSourceResponse: SSE stream with progressive results

    SSE Event Types:
        - metadata: Initial query metadata
        - result: Individual document result
        - collection_complete: Collection finished processing
        - collection_error: Collection failed to query
        - done: Query complete
        - error: Fatal error occurred

    Example SSE Events:
        data: {"type": "metadata", "query": "What is Python?", "collections": ["docs"]}

        data: {"type": "result", "collection": "docs", "text": "Python is...", "relevance_score": 0.95}

        data: {"type": "collection_complete", "collection": "docs", "num_results": 5}

        data: {"type": "done", "total_results": 5}
    """
    logger.info(f"Starting streaming query for user {current_user['username']}: {payload.query}")

    async def generate():
        """Generate SSE events for streaming query."""
        try:
            # Determine collections to search
            if payload.collection:
                collections = [payload.collection]
            elif payload.collections:
                collections = payload.collections
            else:
                # Search all accessible collections
                collections = list_collection_names(current_user["db_path"])

            if not collections:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "type": "error",
                        "error_code": "resource.collection_not_found",
                        "detail": "No collections available to search",
                    }),
                }
                return

            # Yield initial metadata
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "metadata",
                    "query": payload.query,
                    "collections": collections,
                    "n_results": payload.n_results,
                }),
            }

            # Stream results as they come
            total_results = 0
            async for result in stream_query_results(
                collection_names=collections,
                query_text=payload.query,
                db_path=current_user["db_path"],
                n_results=payload.n_results,
            ):
                if result["type"] == "result":
                    total_results += 1

                yield {
                    "event": "message",
                    "data": json.dumps(result),
                }

            # Yield completion event
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "done",
                    "total_results": total_results,
                }),
            }

            logger.info(
                f"Streaming query completed for user {current_user['username']}: "
                f"{total_results} results from {len(collections)} collections"
            )

        except HTTPException as e:
            # Yield HTTP error as SSE event
            error_code = to_mcp_error_code(e.status_code, e.detail)
            logger.error(
                f"Streaming query error for user {current_user['username']}: "
                f"{e.status_code} - {e.detail}"
            )
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "error_code": error_code.value,
                    "detail": e.detail,
                    "http_status": e.status_code,
                }),
            }

        except Exception as e:
            # Yield unexpected error as SSE event
            error_code = to_mcp_error_code(500, str(e))
            logger.exception(
                f"Unexpected streaming query error for user {current_user['username']}: {e}"
            )
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "error_code": error_code.value,
                    "detail": f"Internal server error: {str(e)}",
                    "http_status": 500,
                }),
            }

    return EventSourceResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
