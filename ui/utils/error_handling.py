"""Centralized error handling for API responses."""

import streamlit as st
from requests import Response


def handle_api_error(response: Response, context: str = "Operation") -> None:
    """Display user-friendly error messages based on HTTP status code.

    Parameters
    ----------
    response : Response
        The failed API response
    context : str
        Description of the operation that failed (e.g., "Upload", "Query")
    """
    status = response.status_code

    try:
        detail = response.json().get("detail", "Unknown error")
    except Exception:
        detail = response.text or "Unknown error"

    if status == 401:
        st.error(f"🔒 Authentication Failed: {detail}")
        st.info("Check your API key in the sidebar or login via Account page.")

    elif status == 413:
        st.error(f"📦 File Too Large: {detail}")
        st.info("Maximum file size is 25MB. Consider splitting large files.")

    elif status == 415:
        st.error(f"📄 Unsupported File Type: {detail}")
        st.info("Supported formats: PDF, DOCX, TXT, MD")

    elif status == 422:
        st.error(f"⚠️ Validation Error: {detail}")
        st.info("Please check your input and try again.")

    elif status == 429:
        st.error(f"⏱️ Rate Limit Exceeded: {detail}")
        st.info("Please wait a moment before trying again.")

    elif status == 500:
        st.error(f"🔥 Server Error: {detail}")
        st.info("An internal server error occurred. Please try again later.")

    else:
        st.error(f"{context} failed: {detail} (HTTP {status})")
