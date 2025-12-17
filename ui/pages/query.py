import streamlit as st

from utils.api_client import api_request
from utils.auth import get_api_key, get_headers
from utils.error_handling import handle_api_error


st.markdown("### Query Your Index")

api_key = get_api_key()
index_options: list[str] = []
if api_key:
    try:
        res = api_request("get", "/api/v1/list-indexes/", headers=get_headers())
        if res.status_code == 200:
            response_data = res.json()
            collections = response_data.get("collections", [])
            index_options = [col["name"] for col in collections]
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
            res = api_request(
                "post",
                "/api/v1/query/",
                json=payload,
                headers=get_headers(),
            )

            if res.status_code == 200:
                response_data = res.json()
                context = response_data["context"]
                raw_results = response_data.get("raw_results", {})

                # Display compiled context
                st.markdown("#### Compiled Context")
                st.text_area("", context, height=200, label_visibility="collapsed")

                # Parse and display source documents from raw_results
                if raw_results and raw_results.get("documents"):
                    docs = raw_results["documents"][0] if raw_results["documents"] else []
                    metas = raw_results.get("metadatas", [[]])[0]
                    dists = raw_results.get("distances", [[]])[0]

                    st.markdown("#### Source Documents")
                    st.caption(f"Found {len(docs)} relevant chunks")

                    for i, doc in enumerate(docs):
                        meta = metas[i] if i < len(metas) else {}
                        dist = dists[i] if i < len(dists) else 0.0
                        source = meta.get("source", "unknown")
                        chunk_idx = meta.get("chunk_index", "?")

                        # Convert cosine distance to similarity percentage
                        # Cosine distance: 0 (identical) to 2 (opposite)
                        similarity = (1 - dist / 2) * 100
                        label = f"{source} [chunk {chunk_idx}] - {similarity:.1f}% match"

                        with st.expander(label, expanded=(i == 0)):
                            st.markdown(doc)
                            st.json(meta)
            else:
                handle_api_error(res, "Query")
