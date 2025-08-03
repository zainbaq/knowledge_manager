"""Streamlit frontend for interacting with the knowledge indexer."""

import streamlit as st
import requests
import os

# Base URL for the backend API. Defaults to a relative path so that the
# frontend and backend can run on the same host. Configure the API_URL
# environment variable if the backend is hosted elsewhere.
PORT = os.getenv("PORT", "8000")
API_URL = os.getenv("API_URL", "https://knowledge-manager-236c8288fac7.herokuapp.com/").rstrip("/")

# Session state defaults
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "api_keys" not in st.session_state:
    st.session_state.api_keys: list[str] = []
if "username" not in st.session_state:
    st.session_state.username = ""
if "password" not in st.session_state:
    st.session_state.password = ""

# Sidebar controls - reflect stored API key
api_key_input = st.sidebar.text_input(
    "API Key",
    type="password",
    value=st.session_state.get("api_key", ""),
)
if api_key_input != st.session_state.api_key:
    st.session_state.api_key = api_key_input

api_key = st.session_state.api_key
headers = {"X-API-Key": api_key} if api_key else {}

# Set up page
st.set_page_config(page_title="Knowledge Indexer", layout="centered")
st.title("📚 Knowledge Indexer")

# Navigation
# Simple navigation between app sections
page = st.sidebar.selectbox(
    "Go to", ["Upload Files", "Query Index", "View Indexes", "Account"]
)

if page != "Account" and not api_key:
    st.warning("Enter your API key in the sidebar or log in via Account page.")

# Upload Page
if page == "Upload Files":
    st.markdown("### Upload Files to Create or Update an Index")
    user_index_name = st.text_input("Index name", placeholder="e.g. project_alpha")
    uploaded_files = st.file_uploader("Drag and drop files here", accept_multiple_files=True)

    if uploaded_files:
        st.markdown("#### Preview Selected Files")
        for uf in uploaded_files:
            size_kb = len(uf.getvalue()) / 1024
            with st.expander(f"{uf.name} ({size_kb:.1f} KB)"):
                try:
                    import tempfile, os
                    from pathlib import Path
                    import sys
                    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
                    from ingestion.file_loader import extract_text_from_file

                    with tempfile.NamedTemporaryFile(delete=False, suffix=uf.name) as tmp:
                        tmp.write(uf.getvalue())
                        tmp_path = Path(tmp.name)
                    text = extract_text_from_file(tmp_path)
                    os.remove(tmp_path)
                    preview = text[:500]
                    if preview:
                        st.text_area("Preview", preview, height=200)
                    else:
                        st.write("No preview available.")
                except Exception as e:
                    st.write(f"Preview error: {e}")

    if st.button("Submit Files") and user_index_name and uploaded_files:
        if not api_key:
            st.error("API key required.")
        else:
            collection = user_index_name.strip()
            with st.spinner("Uploading and processing..."):
                files = [("files", (f.name, f.getvalue())) for f in uploaded_files]
                res = requests.post(
                    f"{API_URL}/create-index/",
                    files=files,
                    data={"collection": collection},
                    headers=headers,
                )

                if res.status_code == 200:
                    st.success(res.json()["message"])
                else:
                    st.error(f"Upload failed: {res.json().get('error')}")

# Query Page
elif page == "Query Index":
    st.markdown("### Query Your Index")
    index_options: list[str] = []
    if api_key:
        try:
            res = requests.get(f"{API_URL}/list-indexes/", headers=headers)
            if res.status_code == 200:
                index_options = [idx["collection_name"] for idx in res.json()]
        except Exception:
            index_options = []
    else:
        st.info("Enter API key to load indexes.")

    selected_indexes = st.multiselect(
        "Select indexes (leave empty to search all)", options=index_options
    )
    query = st.text_input("Ask a question")

    if st.button("Submit Query") and query:
        if not api_key:
            st.error("API key required.")
        else:
            payload = {"query": query}
            if selected_indexes:
                if len(selected_indexes) == 1:
                    payload["collection"] = selected_indexes[0]
                else:
                    payload["collections"] = selected_indexes
            with st.spinner("Thinking..."):
                res = requests.post(
                    f"{API_URL}/query/",
                    json=payload,
                    headers=headers,
                )

                if res.status_code == 200:
                    context = res.json()["context"]
                    st.markdown("#### Retrieved Context")
                    for item in context:
                        meta = item.get("metadata", {})
                        source = meta.get("source", "unknown")
                        dist = item.get("distance", 0.0)
                        label = f"{source} (distance {dist:.2f})"
                        with st.expander(label):
                            st.write(item.get("text", ""))
                            st.json(meta)
                else:
                    st.error(f"Query failed: {res.json().get('error')}")

# View Indexes Page
elif page == "View Indexes":
    st.markdown("### 📁 Existing Indexes with Metadata")

    if api_key:
        try:
            res = requests.get(f"{API_URL}/list-indexes/", headers=headers)
            if res.status_code == 200:
                indexes = res.json()

                if indexes:
                    for idx in indexes:
                        index_name = idx["collection_name"]

                        with st.expander(f"🗂️ {index_name} ({idx['num_chunks']} chunks)"):
                            st.markdown("**Files Indexed:**")
                            for f in idx["files"]:
                                st.markdown(f"- `{f}`")

                            st.markdown("**Add more files:**")
                            update_files = st.file_uploader(
                                f"Upload files to update '{index_name}'",
                                accept_multiple_files=True,
                                key=f"update_{index_name}"
                            )
                            if st.button(f"Update '{index_name}'", key=f"btn_{index_name}") and update_files:
                                with st.spinner("Updating..."):
                                    files = [("files", (f.name, f.getvalue())) for f in update_files]
                                    update_res = requests.post(
                                        f"{API_URL}/update-index/",
                                        files=files,
                                        data={"collection": index_name},
                                        headers=headers,
                                    )
                                    if update_res.status_code == 200:
                                        st.success(update_res.json()["message"])
                                    else:
                                        st.error(f"Update failed: {update_res.json().get('error')}")

                            delete_key = f"delete_{index_name}"
                            if st.button(f"❌ Delete '{index_name}'", key=delete_key):
                                st.session_state["pending_delete"] = index_name

                            if st.session_state.get("pending_delete") == index_name:
                                st.warning(f"Are you sure you want to delete '{index_name}'?", icon="⚠️")
                                confirm_key = f"confirm_delete_{index_name}"
                                cancel_key = f"cancel_delete_{index_name}"

                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    if st.button("✅ Yes, Delete", key=confirm_key):
                                        del_res = requests.delete(
                                            f"{API_URL}/delete-index/{index_name}",
                                            headers=headers,
                                        )
                                        if del_res.status_code == 200:
                                            st.success(del_res.json()["message"])
                                            del st.session_state["pending_delete"]
                                        else:
                                            st.error(f"Delete failed: {del_res.json().get('error')}")

                                with col2:
                                    if st.button("❌ Cancel", key=cancel_key):
                                        del st.session_state["pending_delete"]
                else:
                    st.info("No indexes found.")
            else:
                st.error("Failed to retrieve index list.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    else:
        st.info("Enter API key to view indexes.")

# Account management page
elif page == "Account":
    st.markdown("### 🔐 Account Management")

    st.subheader("Register")
    with st.form("register_form"):
        reg_user = st.text_input("Username", key="register_username")
        reg_pass = st.text_input(
            "Password", type="password", key="register_password"
        )
        submitted = st.form_submit_button("Create Account")
    if submitted and reg_user and reg_pass:
        res = requests.post(
            f"{API_URL}/user/register",
            json={"username": reg_user, "password": reg_pass},
        )
        if res.status_code == 200:
            st.success(res.json().get("message", "Registered"))
        else:
            detail = res.json().get("detail", "Registration failed")
            st.error(detail)

    st.subheader("Login")
    with st.form("login_form"):
        login_user = st.text_input("Username", key="login_username")
        login_pass = st.text_input(
            "Password", type="password", key="login_password"
        )
        login_submitted = st.form_submit_button("Login")
    if login_submitted and login_user and login_pass:
        res = requests.post(
            f"{API_URL}/user/login",
            json={"username": login_user, "password": login_pass},
        )
        if res.status_code == 200:
            st.success(res.json().get("message", "Login successful"))
            st.session_state.username = login_user
            st.session_state.password = login_pass
            st.session_state.api_keys = res.json().get("api_keys", [])
        else:
            st.error(res.json().get("detail", "Login failed"))

    if st.session_state.api_keys:
        st.markdown("#### Existing API Keys")
        selected_key = st.selectbox(
            "Choose an API key",
            st.session_state.api_keys,
            key="existing_api_keys",
        )
        if st.button("Use Selected Key") and selected_key:
            st.session_state.api_key = selected_key
            st.success("API key set for session")

    if st.session_state.username and st.session_state.password:
        if st.button("Create New API Key"):
            res = requests.post(
                f"{API_URL}/user/create-api-key",
                json={
                    "username": st.session_state.username,
                    "password": st.session_state.password,
                },
            )
            if res.status_code == 200:
                new_key = res.json().get("api_key")
                st.session_state.api_keys.append(new_key)
                st.session_state.api_key = new_key
                st.success(f"New API key generated: {new_key}")
            else:
                st.error(res.json().get("detail", "Failed to generate key"))

        if st.button("Logout"):
            for key in [
                "api_key",
                "username",
                "password",
                "api_keys",
                "existing_api_keys",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("Logged out")