"""Middleware to add MCP error codes to HTTP exception responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.models.mcp_errors import to_mcp_error_code
from logging_config import get_logger

logger = get_logger(__name__)


class MCPErrorMiddleware(BaseHTTPMiddleware):
    """Middleware that adds MCP error codes to error responses.

    This middleware intercepts error responses and adds X-MCP-Error-Code
    headers to enable AI agents to make intelligent retry decisions.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and add MCP error code headers to error responses."""
        try:
            response = await call_next(request)

            # If response is an error (4xx or 5xx), add MCP error code header
            if response.status_code >= 400:
                # Try to extract error detail from response body
                detail = ""
                try:
                    # For JSONResponse, we can peek at the body
                    if hasattr(response, "body"):
                        import json
                        body = response.body.decode() if isinstance(response.body, bytes) else response.body
                        body_json = json.loads(body) if isinstance(body, str) else {}
                        detail = body_json.get("detail", "")
                except Exception:
                    # If we can't extract detail, use generic error code
                    pass

                # Map to MCP error code
                error_code = to_mcp_error_code(response.status_code, detail)

                # Add header
                response.headers["X-MCP-Error-Code"] = error_code.value

                logger.debug(
                    f"Added MCP error code {error_code.value} to {response.status_code} response"
                )

            return response

        except Exception as e:
            # If middleware itself fails, return 500 with MCP error code
            logger.exception(f"MCPErrorMiddleware failed: {e}")

            error_code = to_mcp_error_code(500, "Internal server error")

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error", "error_code": error_code.value},
                headers={"X-MCP-Error-Code": error_code.value},
            )
