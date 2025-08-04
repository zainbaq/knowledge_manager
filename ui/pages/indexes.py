import streamlit as st

from utils.api_client import api_request
from utils.auth import get_api_key, get_headers

st.markdown("### 💽 Existing Indexes with Metadata")

api_key = get_api_key()
if api_key:
    try:
        res = api_request("get", "/api/list-indexes/", headers=get_headers())
        if res.status_code == 200:
            indexes = res.json()

            if indexes:
                for idx in indexes:
                    index_name = idx["collection_name"]

                    with st.expander(f"📂 {index_name} ({idx['num_chunks']} chunks)"):
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
                                update_res = api_request(
                                    "post",
                                    "/api/update-index/",
                                    files=files,
                                    data={"collection": index_name},
                                    headers=get_headers(),
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
                                    del_res = api_request(
                                        "delete",
                                        f"/api/delete-index/{index_name}",
                                        headers=get_headers(),
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
