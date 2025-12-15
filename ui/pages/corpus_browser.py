"""Browse and subscribe to public corpuses."""

import streamlit as st

from utils.api_client import api_request
from utils.auth import get_api_key, get_headers
from utils.error_handling import handle_api_error

st.markdown("### 📚 Browse Public Corpuses")
st.markdown("Discover and subscribe to curated knowledge corpuses")

api_key = get_api_key()
if api_key:
    try:
        # Fetch accessible corpuses
        res = api_request("get", "/api/v1/corpus/", headers=get_headers())

        if res.status_code == 200:
            response_data = res.json()
            corpuses = response_data.get("corpuses", [])

            if not corpuses:
                st.info("No corpuses available yet. Check back later!")
            else:
                # Filter options
                col1, col2 = st.columns([2, 2])
                with col1:
                    show_approved_only = st.checkbox("Show approved only", value=True)
                with col2:
                    categories = list(set([c.get("category", "Uncategorized") for c in corpuses if c.get("category")]))
                    selected_category = st.selectbox(
                        "Filter by category",
                        ["All"] + categories,
                        index=0
                    )

                # Filter corpuses
                filtered_corpuses = corpuses
                if show_approved_only:
                    filtered_corpuses = [c for c in filtered_corpuses if c.get("is_approved")]
                if selected_category != "All":
                    filtered_corpuses = [c for c in filtered_corpuses if c.get("category") == selected_category]

                st.markdown(f"**Found {len(filtered_corpuses)} corpus(es)**")

                # Display corpuses
                for corpus in filtered_corpuses:
                    corpus_id = corpus["id"]
                    name = corpus["name"]
                    display_name = corpus["display_name"]
                    description = corpus.get("description", "No description provided")
                    category = corpus.get("category", "Uncategorized")
                    version = corpus.get("version", 1)
                    is_approved = corpus.get("is_approved", False)
                    owner = corpus.get("owner_username", "Unknown")
                    chunk_count = corpus.get("chunk_count", 0)
                    file_count = corpus.get("file_count", 0)

                    # Determine access status
                    permission = corpus.get("user_permission")
                    if permission == "owner":
                        access_badge = "🔑 Owner"
                    elif permission:
                        access_badge = f"✅ {permission.capitalize()}"
                    elif is_approved and corpus.get("is_public"):
                        access_badge = "🌐 Public"
                    else:
                        access_badge = "🔒 Private"

                    approval_badge = "✅ Approved" if is_approved else "⏳ Pending Approval"

                    with st.expander(
                        f"**{display_name}** ({category}) - v{version} - {access_badge}"
                    ):
                        st.markdown(f"**ID:** `{corpus_id}` | **Name:** `{name}`")
                        st.markdown(f"**Owner:** {owner} | **Status:** {approval_badge}")
                        st.markdown(f"**Description:** {description}")
                        st.markdown(f"**Stats:** {chunk_count} chunks, {file_count} files")

                        # Subscription actions
                        col1, col2 = st.columns([2, 2])

                        with col1:
                            # Subscribe button
                            if permission not in ["owner", "admin", "write", "read"]:
                                if is_approved and corpus.get("is_public"):
                                    tier = st.selectbox(
                                        "Select tier",
                                        ["free", "basic", "premium"],
                                        key=f"tier_{corpus_id}"
                                    )

                                    if st.button(f"📥 Subscribe", key=f"subscribe_{corpus_id}"):
                                        with st.spinner("Subscribing..."):
                                            sub_res = api_request(
                                                "post",
                                                f"/api/v1/corpus/{corpus_id}/subscribe",
                                                json={"tier": tier},
                                                headers=get_headers(),
                                            )

                                            if sub_res.status_code == 200:
                                                st.success(f"Subscribed to '{display_name}'!")
                                                st.rerun()
                                            else:
                                                handle_api_error(sub_res, "Subscribe")
                                else:
                                    st.info("Not yet approved for public access")
                            else:
                                st.success(f"You have {permission} access")

                        with col2:
                            # Unsubscribe button
                            if permission == "read":
                                if st.button(f"🗑️ Unsubscribe", key=f"unsubscribe_{corpus_id}"):
                                    with st.spinner("Unsubscribing..."):
                                        unsub_res = api_request(
                                            "delete",
                                            f"/api/v1/corpus/{corpus_id}/subscribe",
                                            headers=get_headers(),
                                        )

                                        if unsub_res.status_code == 200:
                                            st.success(f"Unsubscribed from '{display_name}'")
                                            st.rerun()
                                        else:
                                            handle_api_error(unsub_res, "Unsubscribe")

                        # Query corpus button
                        if permission in ["owner", "admin", "write", "read"]:
                            st.markdown("---")
                            st.markdown("**Query this corpus:**")

                            query_text = st.text_input(
                                "Enter your query",
                                key=f"query_{corpus_id}",
                                placeholder="What would you like to know?"
                            )

                            if st.button(f"🔍 Query", key=f"query_btn_{corpus_id}"):
                                if query_text:
                                    with st.spinner("Querying..."):
                                        query_res = api_request(
                                            "post",
                                            f"/api/v1/corpus/{corpus_id}/query",
                                            json={"query": query_text, "n_results": 5},
                                            headers=get_headers(),
                                        )

                                        if query_res.status_code == 200:
                                            result = query_res.json()
                                            context = result.get("context", "")

                                            st.markdown("**Results:**")
                                            st.text_area(
                                                "Context",
                                                value=context,
                                                height=200,
                                                key=f"result_{corpus_id}"
                                            )
                                        else:
                                            handle_api_error(query_res, "Query")
                                else:
                                    st.warning("Please enter a query")

        else:
            handle_api_error(res, "List Corpuses")

    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("Please enter your API key in the Account page to browse corpuses")
