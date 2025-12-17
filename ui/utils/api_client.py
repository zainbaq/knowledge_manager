import logging
from typing import Any

import requests

API_URL = "http://127.0.0.1:8000"
print(f"[DEBUG] api_client loaded with API_URL={API_URL}")

logger = logging.getLogger(__name__)


def api_request(method: str, path: str, **kwargs: Any) -> requests.Response:
    """Make an API request to the backend service.

    Parameters
    ----------
    method:
        HTTP method, e.g. "get", "post", "delete".
    path:
        Endpoint path that will be joined with ``API_URL``.
    **kwargs:
        Additional arguments passed to ``requests.request`` (e.g. headers, json).

    Returns
    -------
    requests.Response
        The response object from ``requests``.
    """
    url = f"{API_URL}/{path.lstrip('/') }"
    headers = kwargs.pop("headers", {}) or {}
    headers.setdefault("Accept", "application/json")

    try:
        response = requests.request(method, url, headers=headers, **kwargs)
        if response.status_code >= 400:
            logger.error(
                "API request failed: %s %s -> %s %s",
                method.upper(),
                url,
                response.status_code,
                response.text,
            )
        return response
    except requests.RequestException as exc:
        logger.error("API request exception: %s %s -> %s", method.upper(), url, exc)
        raise
