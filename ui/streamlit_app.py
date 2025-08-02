"""Streamlit frontend for interacting with the knowledge indexer."""

import streamlit as st
import requests

# Set up page
st.set_page_config(page_title="Knowledge Indexer", layout="centered")
st.title("📚 Knowledge Indexer")

# Navigation
# Simple navigation between app sections
page = st.sidebar.selectbox("Go to", ["Upload Files", "Query Index", "View Indexes"])

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
        collection = user_index_name.strip()
        with st.spinner("Uploading and processing..."):
            files = [("files", (f.name, f.getvalue())) for f in uploaded_files]
            res = requests.post("http://127.0.0.1:8000/create-index/", files=files, data={"collection": collection})

            if res.status_code == 200:
                st.success(res.json()["message"])
            else:
                st.error(f"Upload failed: {res.json().get('error')}")

# Query Page
elif page == "Query Index":
    st.markdown("### Query Your Index")
    try:
        res = requests.get("http://127.0.0.1:8000/list-indexes/")
        index_options = [idx["collection_name"] for idx in res.json()] if res.status_code == 200 else []
    except Exception:
        index_options = []

    selected_indexes = st.multiselect("Select indexes", options=index_options)
    query = st.text_input("Ask a question")

    if st.button("Submit Query") and query and selected_indexes:
        with st.spinner("Thinking..."):
            res = requests.post(
                "http://127.0.0.1:8000/multi-query/",
                json={"query": query, "collections": selected_indexes},
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

    try:
        res = requests.get("http://127.0.0.1:8000/list-indexes/")
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
                                    "http://127.0.0.1:8000/update-index/",
                                    files=files,
                                    data={"collection": index_name}
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
                                    del_res = requests.delete(f"http://127.0.0.1:8000/delete-index/{index_name}")
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
