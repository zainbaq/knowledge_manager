import os
import streamlit as st

from utils.api_client import api_request
from utils.auth import get_api_key, get_headers


st.markdown("### Upload Files to Create or Update an Index")

api_key = get_api_key()
if not api_key:
    st.warning("Enter your API key in the sidebar or log in via Account page.")

user_index_name = st.text_input("Index name", placeholder="e.g. project_alpha")
uploaded_files = st.file_uploader("Drag and drop files here", accept_multiple_files=True)

if uploaded_files:
    st.markdown("#### Preview Selected Files")
    for uf in uploaded_files:
        size_kb = len(uf.getvalue()) / 1024
        with st.expander(f"{uf.name} ({size_kb:.1f} KB)"):
            try:
                import tempfile
                from pathlib import Path
                import sys

                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
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
            res = api_request(
                "post",
                "/api/create-index/",
                files=files,
                data={"collection": collection},
                headers=get_headers(),
            )

            if res.status_code == 200:
                st.success(res.json()["message"])
            else:
                st.error(f"Upload failed: {res.json().get('error')}")
