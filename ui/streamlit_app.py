"""Streamlit frontend for interacting with the knowledge indexer."""

import os
import streamlit as st

from utils.auth import init_session_state, get_api_key, set_api_key

PORT = os.getenv("PORT", "8000")


def main() -> None:
    st.set_page_config(page_title="Knowledge Indexer", layout="centered")
    st.title("📚 Knowledge Indexer")

    init_session_state()

    api_key_input = st.sidebar.text_input(
        "API Key", type="password", value=get_api_key()
    )
    if api_key_input != get_api_key():
        set_api_key(api_key_input)

    pages = [
        st.Page("pages/upload.py", title="Upload Files", icon="📤"),
        st.Page("pages/query.py", title="Query Index", icon="🔍"),
        st.Page("pages/indexes.py", title="View Indexes", icon="📁"),
        st.Page("pages/account.py", title="Account", icon="🔐"),
    ]
    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()

