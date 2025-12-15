# Knowledge Manager Architecture

This document provides a comprehensive overview of the Knowledge Manager's architecture, components, and design decisions.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Layers](#architecture-layers)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Security Architecture](#security-architecture)
- [Scalability Considerations](#scalability-considerations)

## System Overview

Knowledge Manager is a local knowledge management solution that enables semantic search over document collections using OpenAI embeddings and ChromaDB vector storage.

### Key Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
├─────────────────┬───────────────────────┬──────────────────────┤
│  Streamlit UI   │   MCP Clients (AI)    │   REST API Clients   │
└─────────────────┴───────────────────────┴──────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ REST API v1  │  │  MCP Server  │  │  Authentication    │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │Rate Limiting │  │  Validation  │  │  Error Handling    │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Business Logic Layer                       │
├─────────────────┬────────────────────┬─────────────────────────┤
│  Ingestion      │   Vector Operations │   Corpus Management    │
│  - File Loader  │   - Query           │   - CRUD Operations    │
│  - Chunker      │   - Index           │   - Permissions        │
│  - Embedder     │   - Streaming       │   - Approval Workflow  │
└─────────────────┴────────────────────┴─────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Data Layer                               │
├──────────────────────┬──────────────────────────────────────────┤
│    ChromaDB          │           SQLite                         │
│  Vector Storage      │   User Data & Metadata                   │
│  - Per-user DBs      │   - Users & API Keys                     │
│  - Collections       │   - Corpus Metadata                      │
│  - Embeddings        │   - Permissions                          │
└──────────────────────┴──────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      External Services                           │
│                     OpenAI Embeddings API                        │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture Layers

### 1. Presentation Layer

**Streamlit UI** (`ui/`)
- Multi-page application for user interaction
- File upload, query, and management interfaces
- Session-based authentication
- Real-time feedback

**MCP Server** (`mcp/`, `api/v1/mcp.py`)
- JSON-RPC 2.0 protocol implementation
- Tool definitions for AI agents
- Resource exposure (corpus metadata)
- Server-Sent Events for streaming

### 2. API Layer

**FastAPI Application** (`api/app.py`)
- RESTful API endpoints
- Request validation using Pydantic
- Rate limiting middleware
- CORS configuration
- Error handling middleware

**API Versions**
- `/api/v1/*` - Current versioned API (primary)
- `/api/*` - Legacy endpoints (deprecated, backward compatible)

### 3. Business Logic Layer

**Document Ingestion** (`ingestion/`)
- `file_loader.py`: Extract text from PDF, DOCX, TXT, MD
- `chunker.py`: Split text into semantic chunks (token-based)

**Vector Operations** (`vector_store/`)
- `embedder.py`: Generate OpenAI embeddings
- `vector_index.py`: ChromaDB operations (CRUD, query, streaming)

**User Management** (`api/users.py`)
- User registration and authentication
- API key generation and validation
- Per-user database isolation

**Corpus Management** (`api/v1/corpus.py`)
- CRUD operations for curated corpuses
- Permission management (owner, viewer, public)
- Approval workflow for public corpuses

### 4. Data Layer

**ChromaDB** (Vector Storage)
- Persistent local storage
- Per-user isolated databases: `{VECTOR_DB_PATH}/{username}/`
- Collections as logical indexes
- Automatic embedding storage

**SQLite** (Relational Metadata)
- `users.db`: User accounts and API keys
- Future: Corpus metadata, permissions, usage tracking

## Component Details

### Authentication Flow

```
1. User Registration
   POST /api/v1/user/register
   ├─ Validate username/password
   ├─ Hash password (bcrypt)
   ├─ Create user record
   └─ Create user vector DB directory

2. API Key Generation
   POST /api/v1/user/login
   ├─ Verify credentials
   ├─ Generate API key (secrets.token_hex)
   ├─ Hash and store key (SHA256)
   └─ Return plain key to user (one time)

3. API Authentication
   X-API-Key header
   ├─ Hash provided key
   ├─ Look up in database
   ├─ Check expiration (API_KEY_TTL_DAYS)
   └─ Inject current_user into request context
```

### Document Processing Pipeline

```
File Upload → Validation → Text Extraction → Chunking → Embedding → Storage

1. Validation (api/validation.py)
   ├─ File size check (MAX_FILE_SIZE_MB)
   ├─ Extension check (.pdf, .docx, .txt, .md)
   ├─ MIME type validation (python-magic)
   └─ Filename sanitization

2. Text Extraction (ingestion/file_loader.py)
   ├─ PDF: PyMuPDF (fitz)
   ├─ DOCX: python-docx
   ├─ TXT/MD: Direct read
   └─ Return plain text

3. Chunking (ingestion/chunker.py)
   ├─ Token-based chunking (500 tokens default)
   ├─ Whitespace splitting
   └─ Metadata: source, chunk_index

4. Embedding (vector_store/embedder.py)
   ├─ OpenAI text-embedding-3-small
   ├─ Batch processing
   ├─ Rate limiting & retries
   └─ 1536-dimensional vectors

5. Storage (vector_store/vector_index.py)
   ├─ Generate UUIDs
   ├─ Bulk insert to ChromaDB
   └─ Collection = user-defined index
```

### Query Processing

```
Query Request → Embedding → Vector Search → Context Compilation → Response

Single Collection Query:
  query_index(collection, query_text)
  └─ Embed query → ChromaDB query → Top-k results

Multi-Collection Query:
  query_multiple_indexes(collections, query_text)
  ├─ Embed query (once)
  ├─ Query collections in parallel (asyncio.gather)
  ├─ Aggregate results
  ├─ Sort by distance
  └─ Return unified results

Streaming Query:
  stream_query_results(collections, query_text)
  ├─ Embed query (once)
  ├─ For each collection:
  │   ├─ Query collection
  │   ├─ Yield results progressively
  │   └─ Yield collection_complete event
  └─ Yield done event
```

### MCP Integration Architecture

```
AI Agent (Claude) → MCP Client → Knowledge Manager MCP Server

MCP Protocol Flow:
1. tools/list
   └─ Returns 4 tool definitions

2. tools/call
   ├─ Validate arguments against schema
   ├─ Route to handler:
   │   ├─ query_knowledge → api/v1/endpoints.py:query
   │   ├─ query_corpus → api/v1/corpus.py:query_corpus
   │   ├─ list_collections → api/v1/endpoints.py:list_indexes
   │   └─ list_corpuses → api/v1/corpus.py:list_corpuses
   └─ Return formatted result

3. resources/list
   └─ List all accessible corpuses as resources

4. resources/read
   └─ Return corpus metadata as markdown

Streaming Endpoint:
  POST /api/v1/mcp/query/stream
  ├─ Server-Sent Events (SSE)
  ├─ Progressive result streaming
  └─ Event types: metadata, result, collection_complete, done, error
```

## Data Flow

### Document Ingestion Data Flow

```
User Upload (UI/API)
    │
    ▼
Validation Layer
    │
    ├─ File Size Check
    ├─ MIME Type Verification
    └─ Filename Sanitization
    │
    ▼
Temporary Storage
    │
    ▼
Text Extraction
    │
    ├─ PDF → fitz.open()
    ├─ DOCX → Document()
    └─ TXT/MD → read()
    │
    ▼
Chunking
    │
    └─ token_text_chunker(text, chunk_size=500)
    │
    ▼
Embedding Generation (Parallel)
    │
    ├─ Chunk 1 → OpenAI API → [e1, e2, ..., e1536]
    ├─ Chunk 2 → OpenAI API → [e1, e2, ..., e1536]
    └─ Chunk N → OpenAI API → [e1, e2, ..., e1536]
    │
    ▼
Metadata Creation
    │
    └─ {source: filename, chunk_index: i}
    │
    ▼
ChromaDB Insertion
    │
    └─ collection.add(documents, embeddings, metadatas, ids)
    │
    ▼
Success Response
```

### Query Processing Data Flow

```
User Query (UI/API/MCP)
    │
    ▼
Authentication Check
    │
    ▼
Query Embedding
    │
    └─ OpenAI API → [q1, q2, ..., q1536]
    │
    ▼
Collection Selection
    │
    ├─ Specific collection(s) → Use provided
    └─ No collection → List all user collections
    │
    ▼
Vector Search (Parallel)
    │
    ├─ Collection 1 → ChromaDB.query() → Top-k results
    ├─ Collection 2 → ChromaDB.query() → Top-k results
    └─ Collection N → ChromaDB.query() → Top-k results
    │
    ▼
Result Aggregation
    │
    ├─ Combine all results
    ├─ Sort by distance (lower = more similar)
    └─ Deduplicate
    │
    ▼
Context Compilation
    │
    └─ Join document chunks with newlines
    │
    ▼
Response Formation
    │
    ├─ Standard: {"context": ..., "raw_results": ...}
    └─ Streaming: SSE events with progressive results
```

## Security Architecture

### Defense in Depth

**1. Input Validation**
- Filename sanitization (path traversal prevention)
- Collection name validation (alphanumeric + underscore/hyphen)
- File size limits
- MIME type verification
- SQL injection prevention (parameterized queries)

**2. Authentication & Authorization**
- API key-based authentication
- Bcrypt password hashing (cost factor 12)
- API key expiration (90 days default)
- Per-user database isolation
- Corpus permission model (owner, viewer, public)

**3. Rate Limiting**
- Per-endpoint rate limits
- IP-based tracking
- Configurable limits via environment
- 429 responses with retry-after headers

**4. Data Isolation**
- Per-user vector databases: `{VECTOR_DB_PATH}/{username}/`
- Path traversal protection in get_user_db_path()
- Absolute path validation
- Corpus-level permissions

**5. Error Handling**
- Structured error codes (MCP integration)
- Minimal error information disclosure
- Logging without sensitive data
- Global exception handler

### Threat Model

**Threats Mitigated:**
- ✅ Path traversal attacks (sanitization + validation)
- ✅ SQL injection (SQLAlchemy ORM + parameterized queries)
- ✅ Brute force attacks (rate limiting)
- ✅ MIME type spoofing (python-magic verification)
- ✅ Unauthorized access (API key authentication)
- ✅ Data leakage (per-user isolation)
- ✅ XSS (input sanitization, API-first architecture)

**Threats Requiring Additional Mitigation:**
- ⚠️ DDoS (consider additional infrastructure-level protection)
- ⚠️ API key leakage (consider key rotation policies)
- ⚠️ Large file DoS (current: 25MB limit, consider additional checks)

## Scalability Considerations

### Current Architecture Limitations

**Single-Server Design:**
- All components run on one server
- ChromaDB is file-based (not distributed)
- SQLite is single-file (not distributed)
- Limited by single server resources

**Concurrency Handling:**
- AsyncIO for I/O-bound operations
- Semaphore for OpenAI API rate limiting
- Parallel collection querying
- Connection pooling for database

### Scaling Strategies

**Horizontal Scaling (Future):**
1. **API Layer:**
   - Deploy multiple FastAPI instances
   - Load balancer (nginx, HAProxy)
   - Sticky sessions for rate limiting

2. **Vector Storage:**
   - Migrate to distributed vector DB (Pinecone, Weaviate, Qdrant)
   - Shard by user or collection
   - Separate read/write paths

3. **Metadata Storage:**
   - Migrate to PostgreSQL
   - Read replicas for query scaling
   - Connection pooling

**Vertical Scaling (Current):**
- Increase EMBEDDING_CONCURRENCY for parallel embeddings
- Add more RAM for ChromaDB caching
- Use SSD storage for faster I/O
- Increase CPU cores for async task processing

**Caching Strategies:**
- Query result caching (Redis)
- Embedding caching for repeated queries
- Collection metadata caching
- API response caching (Varnish, CDN)

### Performance Optimization

**Current Optimizations:**
- Parallel file processing (asyncio.create_task)
- Batch embedding generation
- Parallel collection querying
- ChromaDB client caching
- Streaming responses for large result sets

**Future Optimizations:**
- Query result pagination
- Incremental indexing (append-only mode)
- Embedding model quantization
- GPU acceleration for local embeddings
- Background job queue (Celery) for long-running tasks

## Technology Stack

### Backend
- **Web Framework:** FastAPI 0.109.2
- **ASGI Server:** Uvicorn 0.27.1
- **Vector Database:** ChromaDB 0.4.24
- **Embeddings:** OpenAI API (text-embedding-3-small)
- **User Database:** SQLite 3
- **Authentication:** bcrypt (via passlib)
- **Rate Limiting:** slowapi 0.1.9

### Frontend
- **UI Framework:** Streamlit 1.31.1
- **HTTP Client:** requests 2.31.0

### Document Processing
- **PDF:** PyMuPDF 1.23.26
- **DOCX:** python-docx 1.1.0
- **MIME Detection:** python-magic 0.4.27

### MCP Integration
- **Streaming:** sse-starlette 2.0.0
- **Protocol:** JSON-RPC 2.0

### Infrastructure
- **Process Manager:** honcho 1.1.0
- **Configuration:** python-dotenv 1.0.1
- **Logging:** Python logging module

## Design Decisions

### Why ChromaDB?
- Local-first architecture
- Built-in embedding storage
- Simple API
- Good performance for small-to-medium datasets
- Python-native

### Why OpenAI Embeddings?
- State-of-art quality
- Proven performance
- Simple API
- Fast inference
- Cost-effective for moderate usage

**Alternative:** Local embedding models (sentence-transformers) for offline mode

### Why FastAPI?
- High performance (async support)
- Automatic API documentation (OpenAPI)
- Type validation (Pydantic)
- Modern Python (3.9+)
- Active community

### Why Per-User Databases?
- Strong data isolation
- Simpler permission model
- Better security (defense in depth)
- Independent scaling per user
- Easier backup/restore

**Trade-off:** Less efficient than shared database, but security > efficiency

### Why Token-Based Chunking?
- Predictable chunk sizes
- Better for embedding models (optimized for token counts)
- Simpler implementation
- Avoids sentence boundary detection complexity

## Future Architecture Enhancements

1. **Distributed Vector Storage:**
   - Migrate to Qdrant or Weaviate for clustering
   - Enable horizontal scaling
   - Improve query performance

2. **Background Job Processing:**
   - Celery or RQ for async tasks
   - Long-running indexing jobs
   - Scheduled maintenance tasks

3. **Monitoring & Observability:**
   - Prometheus metrics
   - Grafana dashboards
   - Structured logging (JSON)
   - Distributed tracing (Jaeger)

4. **Caching Layer:**
   - Redis for query caching
   - Session storage
   - Rate limit counters

5. **API Gateway:**
   - Kong or Tyk
   - Centralized authentication
   - API analytics
   - Request transformation

6. **Multi-Tenancy:**
   - Organization support
   - Team collaboration
   - Shared corpuses within teams
   - Usage quotas per organization

---

**Last Updated:** Phase 6 - MCP Integration Complete
