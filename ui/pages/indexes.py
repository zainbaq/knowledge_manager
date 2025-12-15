import streamlit as st

from utils.api_client import api_request
from utils.auth import get_api_key, get_headers
from utils.error_handling import handle_api_error

st.markdown("### 💽 Existing Indexes with Metadata")

api_key = get_api_key()
if api_key:
    try:
        res = api_request("get", "/api/v1/list-indexes/", headers=get_headers())
        if res.status_code == 200:
            response_data = res.json()
            collections = response_data.get("collections", [])

            if collections:
                for col in collections:
                    index_name = col["name"]

                    with st.expander(f"📂 {index_name} ({col['num_chunks']} chunks, {len(col['files'])} files)"):
                        st.markdown("**Files Indexed:**")
                        for f in col["files"]:
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
                                    "/api/v1/update-index/",
                                    files=files,
                                    data={"collection": index_name},
                                    headers=get_headers(),
                                )
                                if update_res.status_code == 200:
                                    result = update_res.json()
                                    st.success(result["message"])
                                    if "indexed_chunks" in result:
                                        st.info(f"Indexed {result['indexed_chunks']} new chunks")
                                    st.rerun()
                                else:
                                    handle_api_error(update_res, "Update")

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
                                        f"/api/v1/delete-index/{index_name}",
                                        headers=get_headers(),
                                    )
                                    if del_res.status_code == 200:
                                        st.success(del_res.json()["message"])
                                        del st.session_state["pending_delete"]
                                        st.rerun()
                                    else:
                                        handle_api_error(del_res, "Delete")

                            with col2:
                                if st.button("❌ Cancel", key=cancel_key):
                                    del st.session_state["pending_delete"]
            else:
                st.info("No indexes found.")
        else:
            handle_api_error(res, "List Collections")
    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("Enter API key to view indexes.")
