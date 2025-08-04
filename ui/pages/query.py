import streamlit as st

from utils.api_client import api_request
from utils.auth import get_api_key, get_headers


st.markdown("### Query Your Index")

api_key = get_api_key()
index_options: list[str] = []
if api_key:
    try:
        res = api_request("get", "/api/list-indexes/", headers=get_headers())
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
            res = api_request(
                "post",
                "/api/query/",
                json=payload,
                headers=get_headers(),
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
