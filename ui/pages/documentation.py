import streamlit as st

st.markdown("### Documentation")

st.markdown(
    """
Use the Knowledge Manager API to query files you have uploaded and indexed.\
 This example shows how to retrieve context for a user query and pass it to the OpenAI Responses API.
"""
)

code = '''from openai import OpenAI
import requests
import json
from dotenv import load_dotenv
import os

def query_remote_vector_db(url, query, api_key, collections=None):
    endpoint = url + '/api/query'

    data = {
        'query' : query
    }
    
    if collections:
        data['collections'] = collections

    headers = {
        'Content-Type' : 'application/json',
        'x-api-key' : api_key
    }

    return requests.post(endpoint, json=data, headers=headers).json()

load_dotenv()

client = OpenAI()

api_key = "<your-knowledge-manager-api-key>"
url = "https://knowledge-manager-236c8288fac7.herokuapp.com/"  # temp endpoint

user_query = "<your query here>"

context = query_remote_vector_db(url, user_query, api_key)

inp = f"""

Here is a user request:
{user_query}

Context Dump:
{json.dumps(context)}
"""

response = client.responses.create(
    model="gpt-4o",
    input=inp
)

print(response.output_text)
'''

st.code(code, language='python')
