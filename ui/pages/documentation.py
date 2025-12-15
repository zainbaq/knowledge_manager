import streamlit as st
import os

st.markdown("### Documentation")

# API Reference Section
API_URL = os.getenv("API_URL", "https://knowledge-manager-236c8288fac7.herokuapp.com/").rstrip("/")

st.markdown(f"""
#### API Reference

Interactive API documentation:
- [OpenAPI Docs (Swagger UI)]({API_URL}/docs)
- [ReDoc Alternative]({API_URL}/redoc)

These docs include complete endpoint reference, request/response schemas, and interactive testing.
""")

st.divider()

st.markdown("#### Quick Start Example")

st.markdown(
    """
Use the Knowledge Manager API to query files you have uploaded and indexed.\
 This example shows how to retrieve context for a user query and pass it to the OpenAI API.
"""
)

code = '''from openai import OpenAI
import requests
from dotenv import load_dotenv
import os

def query_remote_vector_db(url, query, api_key, collections=None):
    """Query the Knowledge Manager API v1."""
    endpoint = url + '/api/v1/query/'

    data = {'query': query}
    if collections:
        if len(collections) == 1:
            data['collection'] = collections[0]
        else:
            data['collections'] = collections

    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key
    }

    response = requests.post(endpoint, json=data, headers=headers)
    response.raise_for_status()

    # v1 API returns {"context": str, "raw_results": dict}
    return response.json()

load_dotenv()
client = OpenAI()

api_key = "<your-knowledge-manager-api-key>"
url = "https://knowledge-manager-236c8288fac7.herokuapp.com"

user_query = "<your query here>"

# Get context from knowledge base
result = query_remote_vector_db(url, user_query, api_key)
context = result["context"]  # This is the compiled context string

# Build prompt with context
prompt = f"""
Here is a user request:
{user_query}

Relevant Context:
{context}
"""

# Query OpenAI with context
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant. Use the provided context to answer questions."},
        {"role": "user", "content": prompt}
    ]
)

print(response.choices[0].message.content)
'''

st.code(code, language='python')
