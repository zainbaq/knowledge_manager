# Knowledge Manager API Examples

This directory contains example integrations for the Knowledge Manager API, demonstrating how to use the API from different programming languages and frameworks.

## Prerequisites

1. **Start the Knowledge Manager API:**
   ```bash
   cd ..
   python run_app.py
   ```

2. **Get an API key:**
   ```bash
   # Register a new user
   curl -X POST http://localhost:8000/api/v1/user/register \
     -H "Content-Type: application/json" \
     -d '{"username": "your_username", "password": "YourSecurePassword123!"}'

   # The response will include your API key
   # {"api_key": "abcdef1234567890..."}
   ```

3. **Update the examples with your API key:**
   - Replace `"your-api-key-here"` or `YOUR_API_KEY` with your actual API key in each example file

## Examples

### 1. Python Client (`python_client.py`)

**Synchronous Python client for basic operations.**

**Install dependencies:**
```bash
pip install requests
```

**Run:**
```bash
python python_client.py
```

**Features:**
- Upload documents to collections
- Update existing collections
- Query single or multiple collections
- List all collections
- Delete collections

**Usage:**
```python
from python_client import KnowledgeManagerClient

client = KnowledgeManagerClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# Upload documents
result = client.upload_documents(
    collection="my_docs",
    file_paths=["doc1.pdf", "doc2.txt"]
)

# Query
context = client.query(
    query="What is the main topic?",
    collection="my_docs"
)
```

---

### 2. Async Client (`async_client.py`)

**Asynchronous Python client for high-performance integrations.**

**Install dependencies:**
```bash
pip install aiohttp
```

**Run:**
```bash
python async_client.py
```

**Features:**
- Async query operations
- Concurrent queries for better performance
- List collections asynchronously

**Usage:**
```python
import asyncio
from async_client import AsyncKnowledgeManagerClient

async def main():
    client = AsyncKnowledgeManagerClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )

    # Single query
    context = await client.query(
        query="What is this about?",
        collection="docs"
    )

    # Concurrent queries
    results = await asyncio.gather(
        client.query("topic A", collection="docs"),
        client.query("topic B", collection="docs"),
        client.query("topic C", collection="docs"),
    )

asyncio.run(main())
```

---

### 3. cURL Examples (`curl_examples.sh`)

**Shell script with cURL commands for all API endpoints.**

**Run:**
```bash
# Make executable
chmod +x curl_examples.sh

# Update YOUR_API_KEY in the file, then run
./curl_examples.sh
```

**Includes examples for:**
- User registration
- Login
- API key creation
- Document upload
- Index updates
- Single collection queries
- Multi-collection queries
- Listing collections
- Deleting collections
- Status check

**Individual command example:**
```bash
# Query a collection
curl -X POST http://localhost:8000/api/v1/query/ \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "collection": "research_papers"
  }'
```

---

### 4. LangChain Integration (`langchain_integration.py`)

**LangChain-compatible retriever for RAG (Retrieval Augmented Generation) applications.**

**Install dependencies:**
```bash
pip install langchain langchain-openai requests

# Set OpenAI API key
export OPENAI_API_KEY="sk-..."
```

**Run:**
```bash
python langchain_integration.py
```

**Features:**
- Custom LangChain retriever
- RAG with OpenAI
- Conversational retrieval with memory
- Multi-collection queries

**Usage:**
```python
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_integration import KnowledgeManagerRetriever

# Initialize retriever
retriever = KnowledgeManagerRetriever(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    collection="documentation"
)

# Create QA chain
llm = ChatOpenAI(model="gpt-3.5-turbo")
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True
)

# Ask questions
result = qa_chain({"query": "How do I upload documents?"})
print(result['result'])
```

---

## API Endpoints Reference

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/user/register` | POST | Register new user |
| `/api/v1/user/login` | POST | Login and get API key |
| `/api/v1/user/create-api-key` | POST | Generate additional API key |

### Document Endpoints (Require API Key)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/create-index/` | POST | Upload documents and create collection |
| `/api/v1/update-index/` | POST | Add documents to existing collection |
| `/api/v1/query/` | POST | Query one or more collections |
| `/api/v1/list-indexes/` | GET | List all collections with metadata |
| `/api/v1/delete-index/{name}` | DELETE | Delete a collection |
| `/api/v1/status/` | GET | Check API status |

---

## API Documentation

Interactive API documentation is available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## Error Handling

All API errors return a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP status codes:**

- `200` - Success
- `401` - Invalid or missing API key
- `413` - File too large (exceeds limit)
- `415` - Unsupported file type
- `422` - Validation error (invalid parameters)
- `429` - Rate limit exceeded
- `500` - Internal server error

**Example error handling in Python:**

```python
import requests

try:
    response = requests.post(...)
    response.raise_for_status()
    data = response.json()
except requests.HTTPError as e:
    if e.response is not None:
        error_detail = e.response.json().get('detail', 'Unknown error')
        print(f"Error: {error_detail}")
```

---

## Supported File Types

- **PDF** (`.pdf`)
- **Word** (`.docx`)
- **Text** (`.txt`)
- **Markdown** (`.md`)

**Maximum file size:** 25 MB per file (configurable)

---

## Rate Limits

Default rate limits (configurable via environment variables):

- **Upload:** 10 requests/minute
- **Query:** 60 requests/minute
- **Management:** 30 requests/minute
- **Auth:** 10 requests/minute

When rate limited, you'll receive a `429` status code with:
```json
{
  "detail": "Rate limit exceeded. Please slow down and try again."
}
```

---

## Best Practices

1. **Reuse API keys:** Store and reuse API keys instead of creating new ones for each request

2. **Batch uploads:** Upload multiple files in a single request instead of individual requests

3. **Query optimization:**
   - Query specific collections when possible (faster than querying all)
   - Use multiple collections parameter for cross-collection searches

4. **Error handling:** Always check response status codes and handle errors gracefully

5. **Async for performance:** Use async client for concurrent operations

6. **Collection naming:** Use descriptive, alphanumeric collection names (letters, numbers, underscores, hyphens)

---

## Troubleshooting

### "Missing API key" error
- Ensure you're sending the `X-API-Key` header
- Verify your API key is correct (32 hex characters)

### "Rate limit exceeded" error
- Wait a minute and try again
- Consider batching operations
- Contact admin to increase rate limits

### "Unsupported file type" error
- Verify file extension is `.pdf`, `.docx`, `.txt`, or `.md`
- Check file MIME type matches extension

### "File too large" error
- Split large files into smaller chunks
- Contact admin to increase file size limit

---

## Additional Resources

- **API Codebase:** https://github.com/yourusername/knowledge_manager
- **Issue Tracker:** https://github.com/yourusername/knowledge_manager/issues
- **Documentation:** Check `/docs` endpoint for interactive docs

---

## Contributing

Have a better example or integration? Contributions welcome!

1. Fork the repository
2. Add your example to this directory
3. Update this README
4. Submit a pull request

---

## License

Examples are provided as-is for educational and integration purposes.
