# Knowledge Manager API Reference

Complete API reference for the Knowledge Manager REST API and MCP endpoints.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [User Management](#user-management)
- [Document Management](#document-management)
- [Query Operations](#query-operations)
- [Corpus Management](#corpus-management)
- [Admin Operations](#admin-operations)
- [MCP Protocol](#mcp-protocol)
- [Error Responses](#error-responses)
- [Rate Limiting](#rate-limiting)

## Base URL

```
Production: https://your-domain.com
Development: http://localhost:8000
```

All API endpoints are prefixed with `/api/v1` for the current version.

Legacy endpoints under `/api` are deprecated but maintained for backward compatibility.

## Authentication

All protected endpoints require an API key in the request header:

```http
X-API-Key: your-api-key-here
```

### Obtaining an API Key

1. Register a user account
2. Login or create an API key
3. Store the key securely (shown only once)

## User Management

### Register User

Create a new user account.

**Endpoint:** `POST /api/v1/user/register`

**Request Body:**
```json
{
  "username": "string (3-50 chars, alphanumeric + underscore)",
  "password": "string (12+ chars with complexity requirements)"
}
```

**Response:** `201 Created`
```json
{
  "message": "User 'username' registered successfully",
  "username": "username"
}
```

**Errors:**
- `422` - Invalid username or password
- `409` - Username already exists

---

### Login / Create API Key

Generate a new API key for an existing user.

**Endpoint:** `POST /api/v1/user/login`

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "api_key": "32-character hex string",
  "expires_at": "2024-04-15T12:00:00Z",
  "message": "API key created successfully"
}
```

**Errors:**
- `401` - Invalid credentials
- `422` - Missing username or password

---

### Create Additional API Key

Generate additional API keys for the same user.

**Endpoint:** `POST /api/v1/user/create-api-key`

**Authentication:** Required

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "api_key": "32-character hex string",
  "expires_at": "2024-04-15T12:00:00Z"
}
```

---

## Document Management

### Create Index (Upload Documents)

Upload files and create a new collection or add to existing.

**Endpoint:** `POST /api/v1/create-index/`

**Authentication:** Required

**Content-Type:** `multipart/form-data`

**Form Data:**
- `collection`: String (collection name)
- `files`: File[] (one or more files)

**Supported File Types:**
- PDF (.pdf)
- Word Documents (.docx)
- Text files (.txt)
- Markdown (.md)

**File Size Limit:** 25 MB per file (configurable)

**Response:** `200 OK`
```json
{
  "message": "Created index and ingested 245 chunks into 'my_collection'",
  "indexed_chunks": 245
}
```

**Errors:**
- `400` - Invalid file type, size exceeded, or no valid files
- `422` - Invalid collection name
- `429` - Rate limit exceeded (10/minute)

---

### Update Index (Add Documents)

Add more files to an existing collection.

**Endpoint:** `POST /api/v1/update-index/`

**Authentication:** Required

**Content-Type:** `multipart/form-data`

**Form Data:**
- `collection`: String (existing collection name)
- `files`: File[] (one or more files)

**Response:** `200 OK`
```json
{
  "message": "Updated 'my_collection' with 89 new chunks",
  "indexed_chunks": 89
}
```

**Errors:**
- `400` - Invalid file type, size exceeded, or no valid files
- `422` - Invalid collection name
- `429` - Rate limit exceeded (10/minute)

---

### List Collections

List all accessible collections with metadata.

**Endpoint:** `GET /api/v1/list-indexes/`

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "collections": [
    {
      "name": "research_papers",
      "files": ["paper1.pdf", "paper2.pdf"],
      "num_chunks": 543
    },
    {
      "name": "documentation",
      "files": ["guide.md", "api.md"],
      "num_chunks": 234
    }
  ]
}
```

**Errors:**
- `429` - Rate limit exceeded (30/minute)

---

### Delete Collection

Remove a collection and all its data.

**Endpoint:** `DELETE /api/v1/delete-index/{collection_name}`

**Authentication:** Required

**Path Parameters:**
- `collection_name`: String (collection to delete)

**Response:** `200 OK`
```json
{
  "message": "Collection 'my_collection' deleted successfully"
}
```

**Errors:**
- `422` - Invalid collection name
- `429` - Rate limit exceeded (30/minute)
- `500` - Error during deletion

---

## Query Operations

### Query Collections

Search one, multiple, or all collections using semantic search.

**Endpoint:** `POST /api/v1/query/`

**Authentication:** Required

**Request Body:**
```json
{
  "query": "string (required, 1-1000 chars)",
  "collection": "string (optional, single collection)",
  "collections": ["string"] "(optional, multiple collections)",
  "n_results": 5 "(optional, default 5, max 20)"
}
```

**Behavior:**
- If `collection` provided: Search only that collection
- If `collections` provided: Search those specific collections
- If neither provided: Search all accessible collections

**Response:** `200 OK`
```json
{
  "context": "Combined relevant text from top results...\n\nMore context...",
  "raw_results": {
    "ids": [["id1", "id2", "id3"]],
    "documents": [["doc1", "doc2", "doc3"]],
    "metadatas": [[{"source": "file1.pdf", "chunk_index": 0}, ...]],
    "distances": [[0.234, 0.456, 0.567]]
  }
}
```

**Errors:**
- `400` - Empty query
- `422` - Invalid collection name or query too long
- `429` - Rate limit exceeded (60/minute)

---

### Stream Query Results (MCP)

Stream query results progressively via Server-Sent Events.

**Endpoint:** `POST /api/v1/mcp/query/stream`

**Authentication:** Required

**Request Headers:**
```http
Accept: text/event-stream
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "query": "string (required)",
  "collection": "string (optional)",
  "collections": ["string"] "(optional)",
  "n_results": 5
}
```

**Response:** `200 OK` (text/event-stream)

**SSE Events:**

1. **metadata** - Initial query information
```
data: {"type": "metadata", "query": "...", "collections": [...], "n_results": 5}
```

2. **result** - Individual document result
```
data: {"type": "result", "collection": "docs", "text": "...", "relevance_score": 0.95, "rank": 1}
```

3. **collection_complete** - Collection finished
```
data: {"type": "collection_complete", "collection": "docs", "num_results": 5}
```

4. **done** - Query complete
```
data: {"type": "done", "total_results": 10}
```

5. **error** - Error occurred
```
data: {"type": "error", "error_code": "...", "detail": "..."}
```

---

## Corpus Management

### Create Corpus

Create a new curated corpus.

**Endpoint:** `POST /api/v1/corpus/`

**Authentication:** Required

**Request Body:**
```json
{
  "name": "string (unique identifier)",
  "display_name": "string (human-readable name)",
  "description": "string (corpus description)",
  "category": "legal | medical | research | general | technical",
  "is_public": false
}
```

**Response:** `201 Created`
```json
{
  "id": 42,
  "name": "us_contract_law",
  "display_name": "US Contract Law Reference",
  "description": "Comprehensive reference...",
  "category": "legal",
  "version": 1,
  "owner_username": "alice",
  "is_public": false,
  "is_approved": false,
  "chunk_count": 0,
  "file_count": 0,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

### Upload Corpus Files

Upload files to a corpus.

**Endpoint:** `POST /api/v1/corpus/{corpus_id}/upload`

**Authentication:** Required (must be owner)

**Content-Type:** `multipart/form-data`

**Form Data:**
- `files`: File[] (one or more files)

**Response:** `200 OK`
```json
{
  "message": "Uploaded 3 files (523 chunks) to corpus 'US Contract Law Reference'",
  "files_processed": 3,
  "chunks_added": 523,
  "corpus": { ... }
}
```

---

### List Corpuses

List all accessible corpuses with optional filtering.

**Endpoint:** `GET /api/v1/corpus/`

**Authentication:** Required

**Query Parameters:**
- `category`: Filter by category (optional)
- `approved_only`: Show only approved corpuses (default: true)

**Response:** `200 OK`
```json
{
  "corpuses": [
    {
      "id": 42,
      "name": "us_contract_law",
      "display_name": "US Contract Law Reference",
      "category": "legal",
      "is_public": true,
      "is_approved": true,
      "chunk_count": 1523,
      "owner_username": "admin",
      "user_permission": "viewer"
    }
  ]
}
```

---

### Get Corpus

Get detailed information about a specific corpus.

**Endpoint:** `GET /api/v1/corpus/{corpus_id}`

**Authentication:** Required

**Path Parameters:**
- `corpus_id`: Integer (corpus ID)

**Response:** `200 OK`
```json
{
  "id": 42,
  "name": "us_contract_law",
  "display_name": "US Contract Law Reference",
  "description": "Comprehensive US contract law reference",
  "category": "legal",
  "version": 1,
  "is_public": true,
  "is_approved": true,
  "chunk_count": 1523,
  "file_count": 15,
  "owner_username": "admin",
  "user_permission": "viewer",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

### Query Corpus

Search within a specific corpus.

**Endpoint:** `POST /api/v1/corpus/{corpus_id}/query`

**Authentication:** Required (must have read permission)

**Path Parameters:**
- `corpus_id`: Integer (corpus ID)

**Request Body:**
```json
{
  "query": "string (required)",
  "n_results": 5 "(optional, max 20)"
}
```

**Response:** `200 OK`
```json
{
  "context": "Relevant text from corpus...",
  "raw_results": {
    "ids": [["id1", "id2"]],
    "documents": [["doc1", "doc2"]],
    "metadatas": [[...], [...]],
    "distances": [[0.123, 0.234]]
  }
}
```

---

### Update Corpus

Update corpus metadata.

**Endpoint:** `PUT /api/v1/corpus/{corpus_id}`

**Authentication:** Required (must be owner)

**Request Body:**
```json
{
  "display_name": "string (optional)",
  "description": "string (optional)",
  "is_public": false "(optional)"
}
```

**Response:** `200 OK`
```json
{
  "message": "Corpus updated successfully",
  "corpus": { ... }
}
```

---

### Delete Corpus

Delete a corpus and all its data.

**Endpoint:** `DELETE /api/v1/corpus/{corpus_id}`

**Authentication:** Required (must be owner)

**Response:** `200 OK`
```json
{
  "message": "Corpus 'US Contract Law Reference' deleted successfully"
}
```

---

## Admin Operations

### List All Corpuses (Admin)

List all corpuses in the system (admin only).

**Endpoint:** `GET /api/v1/admin/corpuses`

**Authentication:** Required (admin user)

**Response:** `200 OK`
```json
{
  "corpuses": [
    {
      "id": 42,
      "name": "us_contract_law",
      "owner_username": "alice",
      "is_approved": false,
      "is_public": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### Approve Corpus

Approve a corpus for public use (admin only).

**Endpoint:** `POST /api/v1/admin/corpuses/{corpus_id}/approve`

**Authentication:** Required (admin user)

**Response:** `200 OK`
```json
{
  "message": "Corpus 'US Contract Law Reference' approved",
  "corpus": { ... }
}
```

---

### Revoke Corpus Approval

Revoke corpus approval (admin only).

**Endpoint:** `POST /api/v1/admin/corpuses/{corpus_id}/revoke`

**Authentication:** Required (admin user)

**Response:** `200 OK`
```json
{
  "message": "Approval revoked for corpus 'US Contract Law Reference'",
  "corpus": { ... }
}
```

---

## MCP Protocol

### MCP Endpoint

Main Model Context Protocol endpoint using JSON-RPC 2.0.

**Endpoint:** `POST /api/v1/mcp/`

**Authentication:** Required

**Content-Type:** `application/json`

**Request Format:**
```json
{
  "jsonrpc": "2.0",
  "method": "string (tools/list, tools/call, resources/list, resources/read)",
  "params": {},
  "id": 1
}
```

---

### List Tools

Get all available MCP tools.

**MCP Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "id": 1
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {
        "name": "query_knowledge",
        "description": "Search indexed documents for relevant context",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": {"type": "string", "minLength": 1, "maxLength": 1000},
            "collections": {"type": "array", "items": {"type": "string"}},
            "n_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20}
          },
          "required": ["query"]
        }
      },
      {
        "name": "query_corpus",
        "description": "Query a specific curated corpus by ID",
        "inputSchema": { ... }
      },
      {
        "name": "list_collections",
        "description": "List all accessible collections with metadata",
        "inputSchema": { ... }
      },
      {
        "name": "list_corpuses",
        "description": "List available curated corpuses",
        "inputSchema": { ... }
      }
    ]
  },
  "id": 1
}
```

---

### Call Tool

Execute an MCP tool.

**MCP Request:**
```json
{
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
}
```

**Response:**
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

---

### List Resources

Get all available MCP resources.

**MCP Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "resources/list",
  "params": {},
  "id": 3
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
        "description": "Comprehensive US contract law reference",
        "mimeType": "application/json"
      }
    ]
  },
  "id": 3
}
```

---

### Read Resource

Read a specific MCP resource.

**MCP Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "resources/read",
  "params": {
    "uri": "corpus://42"
  },
  "id": 4
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
  "id": 4
}
```

---

## Error Responses

### Standard HTTP Error Format

```json
{
  "detail": "Error message description",
  "error_code": "category.specific_error"
}
```

### Error Response Headers

```http
X-MCP-Error-Code: validation.empty_query
```

### MCP Error Format

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

### Common Error Codes

#### Authentication Errors (401)
- `auth.missing_api_key` - No API key provided
- `auth.invalid_api_key` - Invalid API key
- `auth.expired_api_key` - API key expired

#### Authorization Errors (403)
- `auth.insufficient_permissions` - User lacks permission
- `auth.corpus_not_approved` - Corpus not approved
- `auth.admin_required` - Admin access required

#### Validation Errors (422)
- `validation.invalid_collection_name` - Invalid collection name
- `validation.empty_query` - Query cannot be empty
- `validation.invalid_corpus_id` - Invalid corpus ID

#### Resource Errors (404)
- `resource.collection_not_found` - Collection not found
- `resource.corpus_not_found` - Corpus not found
- `resource.user_not_found` - User not found

#### Rate Limit Errors (429)
- `rate_limit.exceeded` - Rate limit exceeded
- `rate_limit.embedding_api` - OpenAI API rate limit

#### Server Errors (500)
- `server.internal_error` - Internal server error
- `server.database_error` - Database error
- `server.chromadb_error` - ChromaDB error

---

## Rate Limiting

### Default Rate Limits

| Endpoint Type | Limit | Applies To |
|--------------|-------|------------|
| Authentication | 10/minute | `/register`, `/login`, `/create-api-key` |
| Upload | 10/minute | `/create-index`, `/update-index`, `/corpus/{id}/upload` |
| Query | 60/minute | `/query`, `/corpus/{id}/query`, `/mcp/` |
| Management | 30/minute | `/list-indexes`, `/delete-index`, `/corpus` |

### Rate Limit Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000
```

### Rate Limit Response

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30

{
  "detail": "Rate limit exceeded. Please slow down and try again.",
  "error_code": "rate_limit.exceeded"
}
```

### Customizing Rate Limits

Set environment variables:

```bash
AUTH_RATE_LIMIT=10/minute
UPLOAD_RATE_LIMIT=10/minute
QUERY_RATE_LIMIT=60/minute
MANAGEMENT_RATE_LIMIT=30/minute

# MCP-specific (optional)
MCP_QUERY_RATE_LIMIT=30/minute
MCP_LIST_RATE_LIMIT=60/minute
MCP_RESOURCE_RATE_LIMIT=120/minute
```

---

## OpenAPI Documentation

Interactive API documentation is available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

**Last Updated:** Phase 6 - MCP Integration Complete
