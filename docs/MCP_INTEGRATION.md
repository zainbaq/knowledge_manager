# MCP Integration Guide

This guide explains how to integrate with the Knowledge Manager using the Model Context Protocol (MCP).

## Table of Contents

- [What is MCP?](#what-is-mcp)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Available Tools](#available-tools)
- [Available Resources](#available-resources)
- [Streaming Queries](#streaming-queries)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## What is MCP?

**Model Context Protocol (MCP)** is Anthropic's open standard for connecting AI assistants to external data sources and tools. It enables AI agents like Claude to:

- Call tools to perform operations (e.g., search documents, list collections)
- Access resources for context (e.g., corpus metadata)
- Use structured error codes for intelligent retry logic

### MCP Architecture

```
AI Assistant (Claude)
    ↓ JSON-RPC 2.0
MCP Server (Knowledge Manager)
    ↓ Internal APIs
ChromaDB + SQLite + OpenAI
```

### Endpoints

The Knowledge Manager provides two MCP endpoints:

1. **JSON-RPC Endpoint**: `/api/v1/mcp/`
   - Standard MCP protocol for tool calls and resource access
   - Follows JSON-RPC 2.0 specification

2. **Streaming Endpoint**: `/api/v1/mcp/query/stream`
   - Server-Sent Events (SSE) for progressive query results
   - Better UX for large result sets

## Quick Start

### 1. Get an API Key

First, create an account and generate an API key:

```bash
curl -X POST http://localhost:8000/api/v1/user/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_secure_password"
  }'

curl -X POST http://localhost:8000/api/v1/user/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_secure_password"
  }'
```

Save the returned `api_key` for authentication.

### 2. List Available Tools

```bash
curl -X POST http://localhost:8000/api/v1/mcp/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
  }'
```

Response:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {
        "name": "query_knowledge",
        "description": "Search indexed documents for relevant context...",
        "inputSchema": { ... }
      },
      ...
    ]
  },
  "id": 1
}
```

### 3. Query Your Knowledge Base

```bash
curl -X POST http://localhost:8000/api/v1/mcp/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "query_knowledge",
      "arguments": {
        "query": "What is Python?",
        "n_results": 5
      }
    },
    "id": 2
  }'
```

Response:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "context": "Python is a high-level programming language...",
    "num_results": 5,
    "collections_searched": "all accessible collections"
  },
  "id": 2
}
```

## Authentication

All MCP endpoints require authentication via API key in the `X-API-Key` header:

```http
X-API-Key: your-api-key-here
```

If missing or invalid, you'll receive an error response with a structured error code:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": 401,
    "message": "Invalid or missing API key",
    "data": {
      "http_status": 401
    }
  },
  "id": 1
}
```

See [Error Handling](#error-handling) for details on error codes.

## Available Tools

### 1. query_knowledge

Search indexed documents for relevant context using semantic search.

**Parameters:**
- `query` (string, required): Natural language query
- `collections` (array of strings, optional): Specific collections to search
- `n_results` (integer, optional): Results per collection (default: 5, max: 20)

**Example:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "query_knowledge",
    "arguments": {
      "query": "How do I use async/await in Python?",
      "collections": ["python_docs", "tutorials"],
      "n_results": 3
    }
  },
  "id": 1
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "context": "Async/await in Python...",
    "num_results": 6,
    "collections_searched": ["python_docs", "tutorials"]
  },
  "id": 1
}
```

### 2. query_corpus

Query a specific curated corpus by ID.

**Parameters:**
- `corpus_id` (integer, required): Corpus ID to query
- `query` (string, required): Natural language query
- `n_results` (integer, optional): Number of results (default: 5, max: 20)

**Example:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "query_corpus",
    "arguments": {
      "corpus_id": 42,
      "query": "What are the penalties for breach of contract?",
      "n_results": 5
    }
  },
  "id": 2
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "context": "Breach of contract penalties...",
    "num_results": 5,
    "corpus_id": 42
  },
  "id": 2
}
```

### 3. list_collections

List all accessible document collections with metadata.

**Parameters:** None

**Example:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "list_collections"
  },
  "id": 3
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "collections": [
      {
        "name": "python_docs",
        "files": ["python_tutorial.pdf", "async_guide.md"],
        "num_chunks": 245
      },
      {
        "name": "legal_contracts",
        "files": ["contract_template.docx"],
        "num_chunks": 89
      }
    ],
    "count": 2
  },
  "id": 3
}
```

### 4. list_corpuses

List available curated corpuses with optional filtering.

**Parameters:**
- `category` (string, optional): Filter by category (legal, medical, research, general, technical)
- `approved_only` (boolean, optional): Only show approved corpuses (default: true)

**Example:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "list_corpuses",
    "arguments": {
      "category": "legal",
      "approved_only": true
    }
  },
  "id": 4
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "corpuses": [
      {
        "id": 42,
        "name": "us_contract_law",
        "display_name": "US Contract Law Reference",
        "category": "legal",
        "is_approved": true,
        "chunk_count": 1523
      }
    ],
    "count": 1,
    "filters": {
      "category": "legal",
      "approved_only": true
    }
  },
  "id": 4
}
```

## Available Resources

Resources provide read-only context that AI agents can access. The Knowledge Manager exposes corpuses as MCP resources.

### Listing Resources

```json
{
  "jsonrpc": "2.0",
  "method": "resources/list",
  "params": {},
  "id": 5
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "resources": [
      {
        "uri": "corpus://42",
        "name": "Corpus: US Contract Law Reference",
        "description": "Comprehensive reference for US contract law",
        "mimeType": "application/json"
      }
    ]
  },
  "id": 5
}
```

### Reading a Resource

```json
{
  "jsonrpc": "2.0",
  "method": "resources/read",
  "params": {
    "uri": "corpus://42"
  },
  "id": 6
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "contents": [
      {
        "uri": "corpus://42",
        "mimeType": "text/markdown",
        "text": "# US Contract Law Reference\n\n## Corpus Information\n- **ID**: 42\n..."
      }
    ]
  },
  "id": 6
}
```

## Streaming Queries

For better UX with large result sets, use the SSE streaming endpoint to receive progressive results.

### Endpoint

`POST /api/v1/mcp/query/stream`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/mcp/query/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -H "Accept: text/event-stream" \
  -d '{
    "query": "What is Python?",
    "n_results": 5
  }'
```

### SSE Event Types

The endpoint streams these event types:

1. **metadata**: Initial query information
   ```
   data: {"type": "metadata", "query": "What is Python?", "collections": ["docs"]}
   ```

2. **result**: Individual document result
   ```
   data: {"type": "result", "collection": "docs", "text": "Python is...", "relevance_score": 0.95, "rank": 1}
   ```

3. **collection_complete**: Collection finished processing
   ```
   data: {"type": "collection_complete", "collection": "docs", "num_results": 5}
   ```

4. **collection_error**: Collection failed to query
   ```
   data: {"type": "collection_error", "collection": "docs", "error": "Collection not found"}
   ```

5. **done**: Query complete
   ```
   data: {"type": "done", "total_results": 10}
   ```

6. **error**: Fatal error occurred
   ```
   data: {"type": "error", "error_code": "auth.invalid_api_key", "detail": "Invalid API key"}
   ```

See `examples/mcp/streaming_client.py` for a complete Python example.

## Error Handling

The Knowledge Manager uses structured error codes that AI agents can use for intelligent retry logic.

### Error Code Format

Error codes follow the pattern: `category.specific_error`

Example: `auth.invalid_api_key`, `validation.empty_query`

### Error Categories

1. **Authentication Errors** (`auth.*`) - Retry with valid credentials
   - `auth.missing_api_key` - No API key provided
   - `auth.invalid_api_key` - Invalid API key
   - `auth.expired_api_key` - API key expired
   - `auth.insufficient_permissions` - User lacks permission
   - `auth.corpus_not_approved` - Corpus not approved
   - `auth.admin_required` - Admin access required

2. **Validation Errors** (`validation.*`) - Fix parameters and retry
   - `validation.invalid_collection_name` - Invalid collection name
   - `validation.invalid_filename` - Invalid filename
   - `validation.empty_query` - Query cannot be empty
   - `validation.invalid_corpus_id` - Invalid corpus ID
   - `validation.no_valid_files` - No valid files provided

3. **File Errors** (`file.*`) - Adjust file and retry
   - `file.too_large` - File exceeds size limit
   - `file.unsupported_type` - Unsupported file type
   - `file.invalid_mime` - Invalid MIME type

4. **Rate Limiting** (`rate_limit.*`) - Backoff and retry
   - `rate_limit.exceeded` - Rate limit exceeded
   - `rate_limit.embedding_api` - OpenAI API rate limit

5. **Resource Errors** (`resource.*`) - Resource doesn't exist
   - `resource.collection_not_found` - Collection not found
   - `resource.corpus_not_found` - Corpus not found
   - `resource.user_not_found` - User not found

6. **Server Errors** (`server.*`) - Retry with exponential backoff
   - `server.internal_error` - Internal server error
   - `server.database_error` - Database error
   - `server.chromadb_error` - ChromaDB error
   - `server.openai_api_error` - OpenAI API error

### Error Response Format

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": 422,
    "message": "Query cannot be empty",
    "data": {
      "http_status": 422
    }
  },
  "id": 1
}
```

HTTP responses also include an `X-MCP-Error-Code` header:

```
X-MCP-Error-Code: validation.empty_query
```

### Retry Strategy Example

```python
def should_retry(error_code: str) -> bool:
    """Determine if an error is retryable."""
    # Retry server errors and rate limits
    if error_code.startswith("server.") or error_code.startswith("rate_limit."):
        return True

    # Don't retry auth or validation errors
    if error_code.startswith("auth.") or error_code.startswith("validation."):
        return False

    # Don't retry resource not found errors
    if error_code.startswith("resource."):
        return False

    return False

def get_backoff_delay(error_code: str, attempt: int) -> int:
    """Get backoff delay in seconds based on error type."""
    if error_code.startswith("rate_limit."):
        return 2 ** attempt  # Exponential: 1s, 2s, 4s, 8s...
    elif error_code.startswith("server."):
        return min(30, 2 ** attempt)  # Exponential up to 30s
    return 0
```

## Rate Limiting

The Knowledge Manager enforces rate limits to prevent abuse and ensure fair usage.

### Default Limits

- **Query Operations**: 60 requests/minute
- **Upload Operations**: 10 requests/minute
- **Management Operations**: 30 requests/minute
- **Authentication**: 10 requests/minute

### MCP-Specific Limits

You can configure MCP-specific rate limits via environment variables:

```bash
# Query tools (query_knowledge, query_corpus)
MCP_QUERY_RATE_LIMIT=30/minute

# List tools (list_collections, list_corpuses)
MCP_LIST_RATE_LIMIT=60/minute

# Resource operations (resources/read)
MCP_RESOURCE_RATE_LIMIT=120/minute
```

If not set, these default to `QUERY_RATE_LIMIT`.

### Rate Limit Headers

Responses include rate limit information:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000
```

### Handling Rate Limits

When rate limited, you'll receive a `429 Too Many Requests` response:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": 429,
    "message": "Rate limit exceeded. Please slow down and try again.",
    "data": {
      "http_status": 429
    }
  },
  "id": 1
}
```

HTTP header:
```
X-MCP-Error-Code: rate_limit.exceeded
```

**Recommended Retry Strategy:**
1. Wait for `Retry-After` header (if present)
2. Use exponential backoff: 1s, 2s, 4s, 8s, ...
3. Maximum retry delay: 30 seconds

## Examples

### Python Client

See `examples/mcp/python_client.py` for a complete Python MCP client implementation.

Basic usage:
```python
from python_client import KnowledgeManagerMCPClient

client = KnowledgeManagerMCPClient(
    base_url="http://localhost:8000",
    api_key="your-api-key",
)

# Query knowledge
result = client.query_knowledge("What is Python?", n_results=5)
print(result["context"])

# List collections
collections = client.list_collections()
print(f"Found {collections['count']} collections")
```

### Streaming Client

See `examples/mcp/streaming_client.py` for a streaming query example.

Basic usage:
```python
import asyncio
from streaming_client import stream_query

async for event in stream_query(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    query="What is Python?",
):
    if event["type"] == "result":
        print(f"Result: {event['text'][:100]}...")
```

### Claude Desktop Integration

1. Add to Claude Desktop MCP config (`~/Library/Application Support/Claude/mcp_config.json`):

```json
{
  "mcpServers": {
    "knowledge-manager": {
      "url": "http://localhost:8000/api/v1/mcp/",
      "headers": {
        "X-API-Key": "${KNOWLEDGE_MANAGER_API_KEY}"
      }
    }
  }
}
```

2. Set environment variable:
```bash
export KNOWLEDGE_MANAGER_API_KEY="your-api-key"
```

3. Restart Claude Desktop. You can now use Knowledge Manager tools in conversations!

See `examples/mcp/claude_desktop_config.json` for a complete example.

## Additional Resources

- [MCP Specification](https://modelcontextprotocol.io/docs/)
- [OpenAPI Documentation](http://localhost:8000/docs)
- [Knowledge Manager README](../README.md)
- [Error Code Reference](../api/models/mcp_errors.py)

## Support

For questions or issues:
- GitHub Issues: [knowledge_manager/issues](https://github.com/your-org/knowledge_manager/issues)
- Documentation: [README.md](../README.md)
