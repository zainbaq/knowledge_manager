import streamlit as st
import requests

st.set_page_config(page_title="Knowledge Indexer", layout="centered")
st.title("📚 Knowledge Indexer")

# Navigation
page = st.sidebar.selectbox("Go to", ["Upload Files", "Query Index", "View Indexes"])

# Upload Page
if page == "Upload Files":
    st.markdown("### Upload Files to Create or Update an Index")
    collection = st.text_input("Index name", placeholder="e.g. project_alpha")
    uploaded_files = st.file_uploader("Drag and drop files here", accept_multiple_files=True)

    if st.button("Submit Files") and collection and uploaded_files:
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
    collection = st.text_input("Index name")
    query = st.text_input("Ask a question")

    if st.button("Submit Query") and query and collection:
        with st.spinner("Thinking..."):
            res = requests.post("http://127.0.0.1:8000/query/", json={"query": query, "collection": collection})

            if res.status_code == 200:
                context = res.json()["context"]
                st.markdown("#### Retrieved Context")
                st.text(context)
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
                    with st.expander(f"🗂️ {idx['collection_name']} ({idx['num_chunks']} chunks)"):
                        st.markdown("**Files Indexed:**")
                        for f in idx["files"]:
                            st.markdown(f"- `{f}`")

                        st.markdown("**Add more files:**")
                        update_files = st.file_uploader(
                            f"Upload files to update '{idx['collection_name']}'",
                            accept_multiple_files=True,
                            key=f"update_{idx['collection_name']}"
                        )
                        if st.button(f"Update '{idx['collection_name']}'", key=f"btn_{idx['collection_name']}") and update_files:
                            with st.spinner("Updating..."):
                                files = [("files", (f.name, f.getvalue())) for f in update_files]
                                update_res = requests.post("http://127.0.0.1:8000/update-index/", files=files, data={"collection": idx["collection_name"]})
                                if update_res.status_code == 200:
                                    st.success(update_res.json()["message"])
                                else:
                                    st.error(f"Update failed: {update_res.json().get('error')}")

                        # Set a unique key for tracking deletion confirmation
                        delete_key = f"delete_{idx['collection_name']}"

                        # Show delete button
                        if st.button(f"❌ Delete '{idx['collection_name']}'", key=delete_key):
                            st.session_state["pending_delete"] = idx["collection_name"]

                        # Show confirm only if the user clicked delete
                        if st.session_state.get("pending_delete") == idx["collection_name"]:
                            st.warning(f"Are you sure you want to delete '{idx['collection_name']}'?", icon="⚠️")
                            confirm_key = f"confirm_delete_{idx['collection_name']}"
                            cancel_key = f"cancel_delete_{idx['collection_name']}"

                            col1, col2 = st.columns([1, 1])
                            with col1:
                                if st.button("✅ Yes, Delete", key=confirm_key):
                                    del_res = requests.delete(f"http://127.0.0.1:8000/delete-index/{idx['collection_name']}")
                                    if del_res.status_code == 200:
                                        st.success(del_res.json()["message"])
                                        del st.session_state["pending_delete"]
                                        st.experimental_rerun()
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

