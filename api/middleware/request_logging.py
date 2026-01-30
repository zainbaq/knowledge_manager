"""Request/response logging middleware for security auditing and debugging."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from logging_config import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request/response details including user, status, and duration."""
        start_time = time.time()

        # Extract request details
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        api_key = request.headers.get("X-API-Key", "")
        masked_key = f"***{api_key[-4:]}" if len(api_key) > 4 else "none"
        content_type = request.headers.get("Content-Type", "none")

        # Log incoming request
        logger.info(
            f"→ {method} {path} | IP: {client_ip} | API Key: {masked_key} | Content-Type: {content_type}"
        )

        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"← {method} {path} | Status: {response.status_code} | "
                f"Duration: {duration_ms:.2f}ms | IP: {client_ip}"
            )

            # Log authentication failures
            if response.status_code == 401:
                logger.warning(
                    f"Authentication failed: {method} {path} | "
                    f"IP: {client_ip} | API Key: {masked_key}"
                )

            # Log rate limiting
            elif response.status_code == 429:
                logger.warning(
                    f"Rate limit exceeded: {method} {path} | "
                    f"IP: {client_ip} | API Key: {masked_key}"
                )

            # Log server errors
            elif response.status_code >= 500:
                logger.error(
                    f"Server error: {method} {path} | "
                    f"Status: {response.status_code} | IP: {client_ip}"
                )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {method} {path} | "
                f"Error: {str(e)} | Duration: {duration_ms:.2f}ms | IP: {client_ip}",
                exc_info=True
            )
            raise
