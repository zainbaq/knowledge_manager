import streamlit as st


def init_session_state() -> None:
    """Ensure required keys exist in session_state."""
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "api_keys" not in st.session_state:
        st.session_state.api_keys = []
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "password" not in st.session_state:
        st.session_state.password = ""


def get_api_key() -> str:
    return st.session_state.get("api_key", "")


def set_api_key(value: str) -> None:
    st.session_state.api_key = value


def get_headers() -> dict:
    api_key = get_api_key()
    return {"X-API-Key": api_key} if api_key else {}


def logout() -> None:
    for key in ["api_key", "username", "password", "api_keys", "existing_api_keys"]:
        if key in st.session_state:
            del st.session_state[key]
