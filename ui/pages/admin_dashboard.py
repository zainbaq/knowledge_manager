"""Admin dashboard for corpus approval and usage monitoring."""

import streamlit as st

from utils.api_client import api_request
from utils.auth import get_api_key, get_headers
from utils.error_handling import handle_api_error

st.markdown("### 👑 Admin Dashboard")
st.markdown("Approve corpuses and monitor usage statistics")

api_key = get_api_key()
if api_key:
    # Check admin access first with a lightweight request
    # We'll try to access the pending corpuses endpoint
    try:
        test_res = api_request(
            "get",
            "/api/v1/admin/corpuses/pending",
            headers=get_headers(),
        )

        if test_res.status_code == 403:
            st.error("❌ Admin access required. You do not have admin permissions.")
            st.info(
                "Contact the system administrator to be added to the ADMIN_USERS list "
                "in the .env configuration."
            )
        elif test_res.status_code == 200:
            # User is admin, show dashboard
            st.success("✅ Admin access verified")

            # Tabs for different admin functions
            tab1, tab2, tab3 = st.tabs(["📋 Pending Approvals", "📊 Corpus Stats", "👤 User Stats"])

            # Tab 1: Pending Corpus Approvals
            with tab1:
                st.markdown("#### Corpuses Awaiting Approval")

                pending_corpuses = test_res.json()

                if not pending_corpuses:
                    st.info("No corpuses pending approval")
                else:
                    st.markdown(f"**{len(pending_corpuses)} corpus(es) pending**")

                    for corpus in pending_corpuses:
                        corpus_id = corpus["id"]
                        name = corpus["name"]
                        display_name = corpus["display_name"]
                        description = corpus.get("description", "No description")
                        category = corpus.get("category", "Uncategorized")
                        owner = corpus.get("owner_username", "Unknown")
                        version = corpus.get("version", 1)

                        with st.expander(f"**{display_name}** by {owner} ({category})"):
                            st.markdown(f"**ID:** `{corpus_id}` | **Name:** `{name}` | **Version:** v{version}")
                            st.markdown(f"**Description:** {description}")
                            st.markdown(f"**Owner:** {owner}")

                            col1, col2 = st.columns([1, 1])

                            with col1:
                                if st.button(f"✅ Approve", key=f"approve_{corpus_id}", type="primary"):
                                    with st.spinner("Approving..."):
                                        approve_res = api_request(
                                            "post",
                                            f"/api/v1/admin/corpuses/{corpus_id}/approve",
                                            headers=get_headers(),
                                        )

                                        if approve_res.status_code == 200:
                                            result = approve_res.json()
                                            st.success(result["message"])
                                            st.rerun()
                                        else:
                                            handle_api_error(approve_res, "Approve")

                            with col2:
                                if st.button(f"❌ Reject", key=f"reject_{corpus_id}", type="secondary"):
                                    with st.spinner("Rejecting..."):
                                        reject_res = api_request(
                                            "post",
                                            f"/api/v1/admin/corpuses/{corpus_id}/reject",
                                            headers=get_headers(),
                                        )

                                        if reject_res.status_code == 200:
                                            result = reject_res.json()
                                            st.success(result["message"])
                                            st.rerun()
                                        else:
                                            handle_api_error(reject_res, "Reject")

            # Tab 2: Corpus Usage Statistics
            with tab2:
                st.markdown("#### Corpus Usage Statistics")

                corpus_id_input = st.number_input(
                    "Enter Corpus ID",
                    min_value=1,
                    step=1,
                    key="corpus_stats_id"
                )

                if st.button("📊 Get Corpus Stats", key="get_corpus_stats"):
                    with st.spinner("Fetching stats..."):
                        stats_res = api_request(
                            "get",
                            f"/api/v1/admin/usage/corpus/{corpus_id_input}",
                            headers=get_headers(),
                        )

                        if stats_res.status_code == 200:
                            stats = stats_res.json()

                            st.markdown("---")
                            st.markdown(f"**Corpus:** {stats.get('corpus_name', 'Unknown')} (ID: {stats.get('corpus_id')})")

                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric("Unique Users", stats.get("unique_users", 0))

                            with col2:
                                st.metric("Total Actions", stats.get("total_actions", 0))

                            with col3:
                                st.metric("Total Queries", stats.get("total_queries", 0))

                            last_access = stats.get("last_access")
                            if last_access:
                                from datetime import datetime
                                last_access_dt = datetime.fromtimestamp(last_access)
                                st.markdown(f"**Last Access:** {last_access_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                            else:
                                st.markdown("**Last Access:** Never")

                        else:
                            handle_api_error(stats_res, "Get Corpus Stats")

            # Tab 3: User Usage Statistics
            with tab3:
                st.markdown("#### User Usage Statistics")

                user_id_input = st.number_input(
                    "Enter User ID",
                    min_value=1,
                    step=1,
                    key="user_stats_id"
                )

                if st.button("📊 Get User Stats", key="get_user_stats"):
                    with st.spinner("Fetching stats..."):
                        stats_res = api_request(
                            "get",
                            f"/api/v1/admin/usage/user/{user_id_input}",
                            headers=get_headers(),
                        )

                        if stats_res.status_code == 200:
                            stats = stats_res.json()

                            st.markdown("---")
                            st.markdown(f"**User:** {stats.get('username', 'Unknown')} (ID: {stats.get('user_id')})")

                            col1, col2 = st.columns(2)

                            with col1:
                                st.metric("Total Actions", stats.get("total_actions", 0))

                            with col2:
                                st.metric("Total Queries", stats.get("total_queries", 0))

                            last_access = stats.get("last_access")
                            if last_access:
                                from datetime import datetime
                                last_access_dt = datetime.fromtimestamp(last_access)
                                st.markdown(f"**Last Access:** {last_access_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                            else:
                                st.markdown("**Last Access:** Never")

                        else:
                            handle_api_error(stats_res, "Get User Stats")

        else:
            handle_api_error(test_res, "Admin Access Check")

    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("Please enter your API key in the Account page to access the admin dashboard")
