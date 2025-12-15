"""Manage user's owned corpuses."""

import streamlit as st

from utils.api_client import api_request
from utils.auth import get_api_key, get_headers
from utils.error_handling import handle_api_error

st.markdown("### 🏗️ Manage My Corpuses")
st.markdown("Create and manage your curated knowledge corpuses")

api_key = get_api_key()
if api_key:
    # Create new corpus section
    st.markdown("#### Create New Corpus")

    with st.form("create_corpus_form"):
        col1, col2 = st.columns([2, 2])

        with col1:
            corpus_name = st.text_input(
                "Corpus Name*",
                placeholder="my_legal_corpus",
                help="Unique identifier (letters, numbers, hyphens, underscores only)"
            )
            display_name = st.text_input(
                "Display Name*",
                placeholder="Legal Knowledge Base",
                help="Human-readable name"
            )

        with col2:
            category = st.text_input(
                "Category",
                placeholder="legal, medical, research, etc.",
                help="Optional category for organization"
            )
            is_public = st.checkbox(
                "Make Public",
                value=False,
                help="Public corpuses require admin approval before being accessible"
            )

        description = st.text_area(
            "Description",
            placeholder="Describe what this corpus contains...",
            help="Optional description (max 1000 characters)"
        )

        submitted = st.form_submit_button("Create Corpus")

        if submitted:
            if not corpus_name or not display_name:
                st.error("Corpus Name and Display Name are required")
            else:
                with st.spinner("Creating corpus..."):
                    create_res = api_request(
                        "post",
                        "/api/v1/corpus/",
                        json={
                            "name": corpus_name,
                            "display_name": display_name,
                            "description": description if description else None,
                            "category": category if category else None,
                            "is_public": is_public,
                        },
                        headers=get_headers(),
                    )

                    if create_res.status_code == 200:
                        result = create_res.json()
                        st.success(f"Corpus '{display_name}' created successfully!")
                        if is_public:
                            st.info("Your corpus is pending admin approval before it becomes public")
                        st.rerun()
                    else:
                        handle_api_error(create_res, "Create Corpus")

    st.markdown("---")

    # List owned corpuses
    st.markdown("#### My Corpuses")

    try:
        res = api_request("get", "/api/v1/corpus/", headers=get_headers())

        if res.status_code == 200:
            response_data = res.json()
            corpuses = response_data.get("corpuses", [])

            # Filter to show only owned corpuses
            owned_corpuses = [c for c in corpuses if c.get("user_permission") == "owner"]

            if not owned_corpuses:
                st.info("You haven't created any corpuses yet. Create one above to get started!")
            else:
                st.markdown(f"**{len(owned_corpuses)} corpus(es)**")

                for corpus in owned_corpuses:
                    corpus_id = corpus["id"]
                    name = corpus["name"]
                    display_name = corpus["display_name"]
                    description = corpus.get("description", "No description")
                    category = corpus.get("category", "Uncategorized")
                    version = corpus.get("version", 1)
                    is_public = corpus.get("is_public", False)
                    is_approved = corpus.get("is_approved", False)
                    chunk_count = corpus.get("chunk_count", 0)
                    file_count = corpus.get("file_count", 0)

                    status = "🌐 Public (✅ Approved)" if is_public and is_approved else \
                             "🌐 Public (⏳ Pending)" if is_public else \
                             "🔒 Private"

                    with st.expander(f"**{display_name}** ({category}) - v{version} - {status}"):
                        st.markdown(f"**ID:** `{corpus_id}` | **Name:** `{name}`")
                        st.markdown(f"**Description:** {description}")
                        st.markdown(f"**Stats:** {chunk_count} chunks, {file_count} files")

                        # Update corpus metadata
                        st.markdown("---")
                        st.markdown("**Update Metadata:**")

                        with st.form(f"update_corpus_{corpus_id}"):
                            new_display_name = st.text_input(
                                "Display Name",
                                value=display_name,
                                key=f"display_name_{corpus_id}"
                            )
                            new_description = st.text_area(
                                "Description",
                                value=description if description != "No description" else "",
                                key=f"description_{corpus_id}"
                            )
                            new_category = st.text_input(
                                "Category",
                                value=category if category != "Uncategorized" else "",
                                key=f"category_{corpus_id}"
                            )
                            new_is_public = st.checkbox(
                                "Make Public",
                                value=is_public,
                                key=f"is_public_{corpus_id}"
                            )

                            update_submitted = st.form_submit_button("Update")

                            if update_submitted:
                                with st.spinner("Updating..."):
                                    update_res = api_request(
                                        "patch",
                                        f"/api/v1/corpus/{corpus_id}",
                                        json={
                                            "display_name": new_display_name,
                                            "description": new_description if new_description else None,
                                            "category": new_category if new_category else None,
                                            "is_public": new_is_public,
                                        },
                                        headers=get_headers(),
                                    )

                                    if update_res.status_code == 200:
                                        st.success("Corpus updated successfully!")
                                        st.rerun()
                                    else:
                                        handle_api_error(update_res, "Update Corpus")

                        # Create version
                        st.markdown("---")
                        st.markdown("**Create Version Snapshot:**")

                        with st.form(f"create_version_{corpus_id}"):
                            version_desc = st.text_area(
                                "Version Description",
                                placeholder="Describe what changed in this version...",
                                key=f"version_desc_{corpus_id}"
                            )

                            version_submitted = st.form_submit_button("Create Version")

                            if version_submitted:
                                with st.spinner("Creating version..."):
                                    version_res = api_request(
                                        "post",
                                        f"/api/v1/corpus/{corpus_id}/versions",
                                        json={"description": version_desc if version_desc else None},
                                        headers=get_headers(),
                                    )

                                    if version_res.status_code == 200:
                                        result = version_res.json()
                                        st.success(f"Version {result['version']} created!")
                                        st.rerun()
                                    else:
                                        handle_api_error(version_res, "Create Version")

                        # List versions
                        st.markdown("---")
                        st.markdown("**Version History:**")

                        versions_res = api_request(
                            "get",
                            f"/api/v1/corpus/{corpus_id}/versions",
                            headers=get_headers(),
                        )

                        if versions_res.status_code == 200:
                            versions = versions_res.json()

                            if versions:
                                for v in versions:
                                    v_num = v["version"]
                                    v_desc = v.get("description", "No description")
                                    v_author = v.get("created_by_username", "Unknown")
                                    v_chunks = v.get("chunk_count", 0)
                                    v_files = v.get("file_count", 0)

                                    st.markdown(
                                        f"- **v{v_num}** by {v_author}: {v_desc} "
                                        f"({v_chunks} chunks, {v_files} files)"
                                    )
                            else:
                                st.info("No versions yet")
                        else:
                            st.warning("Could not load version history")

                        # Delete corpus
                        st.markdown("---")
                        st.markdown("**Danger Zone:**")

                        delete_key = f"delete_corpus_{corpus_id}"
                        if st.button(f"🗑️ Delete Corpus", key=delete_key, type="secondary"):
                            st.session_state["pending_delete_corpus"] = corpus_id

                        if st.session_state.get("pending_delete_corpus") == corpus_id:
                            st.warning(
                                f"⚠️ Are you sure you want to delete '{display_name}'? "
                                f"This action cannot be undone!",
                                icon="⚠️"
                            )

                            col1, col2 = st.columns([1, 1])

                            with col1:
                                if st.button("✅ Yes, Delete", key=f"confirm_delete_corpus_{corpus_id}"):
                                    with st.spinner("Deleting..."):
                                        delete_res = api_request(
                                            "delete",
                                            f"/api/v1/corpus/{corpus_id}",
                                            headers=get_headers(),
                                        )

                                        if delete_res.status_code == 200:
                                            st.success(f"Corpus '{display_name}' deleted successfully")
                                            del st.session_state["pending_delete_corpus"]
                                            st.rerun()
                                        else:
                                            handle_api_error(delete_res, "Delete Corpus")

                            with col2:
                                if st.button("❌ Cancel", key=f"cancel_delete_corpus_{corpus_id}"):
                                    del st.session_state["pending_delete_corpus"]
                                    st.rerun()

        else:
            handle_api_error(res, "List Corpuses")

    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("Please enter your API key in the Account page to manage corpuses")
