# 🧠 Knowledge Manager

A knowledge management service built with **FastAPI** and a **Next.js** frontend that lets users upload files (PDF, DOCX, TXT, MD), chunk and embed them using OpenAI embeddings, store them in a persistent **vector database (ChromaDB)**, and query them semantically.

Part of the Promethean Labs suite. It runs as two containers (backend + frontend) behind a reverse proxy, shares one AWS Cognito user pool with the other apps, and is also consumed as an MCP server by Promethean AI.

---

## 🚀 Features

- ✅ Upload documents via drag-and-drop
- ✅ Automatically chunk and embed content
- ✅ Store embeddings locally using ChromaDB
- ✅ Create and update custom indexes (collections)
- ✅ Query indexed knowledge across single or multiple indexes
- ✅ View all collections and their metadata
- ✅ Delete collections safely from the UI
- ✅ Full Python backend & frontend integration
- ✅ User accounts with per-user vector stores and API keys
- ✅ **Model Context Protocol (MCP) support** for AI agent integration
- ✅ Streaming query results via Server-Sent Events (SSE)

---

## 📁 Project Structure

```
.
├── api/                     # FastAPI backend
│   └── app.py
├── ingestion/              # File collection & chunking
│   ├── file_loader.py
│   └── chunker.py
├── vector_store/           # Embedding + ChromaDB logic
│   ├── embedder.py
│   └── vector_index.py
├── next/                   # Next.js frontend (+ its own Dockerfile)
├── mcp/                    # MCP tool + resource handlers
├── scripts/                # Operational tooling (storage migration)
├── Dockerfile              # Backend image
├── docker-compose.yml      # Local stack: backend + frontend
├── requirements.txt
└── README.md
```

---

## ⚙️ Requirements

- Python 3.9+
- OpenAI API Key (for embeddings)

### 🔧 Install dependencies

```bash
pip install -r requirements.txt
```

> Copy `.env.example` to `.env` and set the values for your environment:
```
cp .env.example .env
```
At a minimum, `OPENAI_API_KEY` must be set before running the app.

---

## 🧠 Embeddings & Vector Store

- Embedding model: `text-embedding-3-small` from OpenAI
- Vector DB: [ChromaDB](https://www.trychroma.com/)
- Chunking: Simple text splitter with paragraph or sentence breaks

---

## ▶️ Run the App

Copy `.env.example` to `.env`, fill in `OPENAI_API_KEY` and the `COGNITO_*` values, then:

```bash
docker compose up --build
```

Then open:
- App: http://localhost:8511
- API docs (Swagger): http://localhost:8511/api/docs

Container-internal ports match the other Promethean apps (backend `8000`, frontend
`8501`); the published host ports are offset to `8010`/`8511` so several apps can
run locally at once. In production nothing is published — Traefik reaches the
containers over the Docker network.

The frontend proxies `/api/*` to the backend server-side, so the browser only ever
talks to one origin and no backend URL is baked into the client bundle.

> **Note:** `BACKEND_URL` is consumed by `next.config.ts`'s `rewrites()`, which
> Next evaluates at **build** time. It must be passed as a Docker build arg —
> supplying it only as runtime container env leaves the localhost fallback baked
> in and every proxied API call fails with `ECONNREFUSED`.

---

### 🔐 User Accounts & API Keys

Each user has a private vector database and can generate their own API keys.

1. **Register a user**

  ```bash
  curl -X POST -H "Content-Type: application/json" \
    -d '{"username": "alice", "password": "Sup3rSecret!23"}' \
    http://localhost:8511/api/v1/user/register
  ```

2. **Create an API key** (after registering)

  ```bash
  curl -X POST -H "Content-Type: application/json" \
    -d '{"username": "alice", "password": "Sup3rSecret!23"}' \
    http://localhost:8511/api/v1/user/create-api-key
  ```

3. **Use the API key**

   ```bash
   curl -H "X-API-Key: <your-api-key>" http://localhost:8511/api/v1/list-indexes/
   ```

---

## 🧪 API Endpoints

| Method | Endpoint                  | Description                      |
|--------|---------------------------|----------------------------------|
| POST   | `/api/v1/create-index/`          | Upload files and create index   |
| POST   | `/api/v1/update-index/`          | Add files to existing index     |
| POST   | `/api/v1/query/`                 | Search one, many, or all indexes |
| GET    | `/api/v1/list-indexes/`          | View collections and metadata   |
| DELETE | `/api/v1/delete-index/{name}`    | Delete a collection             |

---

## 🤖 MCP Integration (AI Agent Support)

Knowledge Manager supports the **Model Context Protocol (MCP)**, enabling AI assistants like Claude to use it as a tool/resource server.

### Quick Start with MCP

1. **Get an API key** (see User Accounts section above)

2. **Query via MCP** using JSON-RPC 2.0:

```bash
curl -X POST http://localhost:8511/api/v1/mcp/ \
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
    "id": 1
  }'
```

3. **Stream results** for progressive queries:

```bash
curl -X POST http://localhost:8511/api/v1/mcp/query/stream \
  -H "X-API-Key: your-api-key" \
  -H "Accept: text/event-stream" \
  -d '{"query": "What is Python?", "n_results": 5}'
```

### Available MCP Tools

- `query_knowledge` - Search indexed documents using semantic search
- `query_corpus` - Query a specific curated corpus by ID
- `list_collections` - List all accessible collections with metadata
- `list_corpuses` - List available curated corpuses with filtering

### Resources

MCP clients can access corpus metadata as resources:
- `corpus://{id}` - Read corpus information and statistics

### Learn More

- 📘 **[Complete MCP Integration Guide](docs/MCP_INTEGRATION.md)** - Authentication, error handling, streaming, examples
- 💻 **[Python Client Example](examples/mcp/python_client.py)** - Simple MCP client implementation
- 🌊 **[Streaming Client Example](examples/mcp/streaming_client.py)** - SSE streaming query example
- 🖥️ **[Claude Desktop Config](examples/mcp/claude_desktop_config.json)** - Claude Desktop integration

---

### 📄 File Upload Limits

The `/api/v1/create-index/` and `/api/v1/update-index/` endpoints only accept files up to
`MAX_FILE_SIZE_MB` (100 MB in the shipped compose file) and with extensions in
`ALLOWED_FILE_EXTENSIONS` (`.pdf`, `.docx`, `.txt`, `.md`). Files that exceed
these limits are rejected with `413 Payload Too Large` or `415 Unsupported Media Type`.

Additional security controls:
- Uploads undergo MIME-type validation, so mismatched extensions are rejected.
- All API endpoints are rate limited (defaults can be tuned via env vars).
- API keys expire automatically (90 days by default) and passwords must be strong (12+ chars with complexity).

---

## 🔒 Security Features

Knowledge Manager implements multiple layers of security to protect your data and prevent abuse:

### Authentication & Authorization
- **API Key Authentication**: All protected endpoints require a valid API key via the `X-API-Key` header
- **API Key Expiration**: Keys automatically expire after 90 days (configurable via `API_KEY_TTL_DAYS`)
- **Password Security**:
  - Minimum 12 characters (configurable via `PASSWORD_MIN_LENGTH`)
  - Complexity requirements: uppercase, lowercase, digit, and special character (configurable via `REQUIRE_COMPLEX_PASSWORD`)
  - Passwords hashed using bcrypt before storage
- **User Isolation**: Each user has their own isolated vector database directory

### Input Validation
- **Collection Name Validation**:
  - Only alphanumeric characters, underscores, and hyphens allowed
  - Path traversal protection (blocks `..`, `/`, `\`)
  - Maximum 100 characters
- **Filename Validation**:
  - Strips path components to prevent directory traversal
  - Null byte detection
  - Maximum 255 characters
- **MIME Type Validation**:
  - Uses `python-magic` to detect actual file types from binary signatures
  - Rejects files with mismatched extensions (e.g., `.exe` renamed to `.pdf`)
- **File Size Limits**: Maximum 25MB per file (configurable via `MAX_FILE_SIZE_MB`)

### Rate Limiting
All endpoints are rate-limited to prevent abuse:
- **Authentication endpoints** (`/register`, `/login`): 10 requests/minute (configurable via `AUTH_RATE_LIMIT`)
- **Upload endpoints** (`/create-index`, `/update-index`): 10 requests/minute (configurable via `UPLOAD_RATE_LIMIT`)
- **Query endpoint** (`/query`): 60 requests/minute (configurable via `QUERY_RATE_LIMIT`)
- **Management endpoints** (`/list-indexes`, `/delete-index`): 30 requests/minute (configurable via `MANAGEMENT_RATE_LIMIT`)

### CORS Configuration
- CORS is restrictive by default; the frontend needs no entry because it proxies same-origin
- Explicit allowlist for origins, methods, and headers
- Configurable via `CORS_ORIGINS` environment variable

### Logging & Monitoring
- **Structured Logging**: All requests, errors, and security events are logged
- **Request Logging Middleware**: Tracks method, path, user, status code, and duration for every request
- **Authentication Failure Logging**: Failed login attempts and invalid API keys are logged
- **Rate Limit Logging**: Rate limit violations are logged for security monitoring

### Configuration
All security settings can be customized via environment variables in `.env`:

```bash
# Password requirements
PASSWORD_MIN_LENGTH=12
REQUIRE_COMPLEX_PASSWORD=true

# API key expiration
API_KEY_TTL_DAYS=90

# Rate limiting
AUTH_RATE_LIMIT=10/minute
UPLOAD_RATE_LIMIT=10/minute
QUERY_RATE_LIMIT=60/minute
MANAGEMENT_RATE_LIMIT=30/minute

# File upload
MAX_FILE_SIZE_MB=25

# CORS
CORS_ORIGINS=https://yourdomain.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log  # Optional: enables file logging
```

---

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

### Core Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - System architecture, components, data flow, and design decisions
  - Architecture layers and component details
  - Data flow diagrams
  - Security architecture and threat model
  - Scalability considerations
  - Technology stack and design decisions

- **[API Reference](docs/API_REFERENCE.md)** - Complete REST API and MCP protocol reference
  - User management endpoints
  - Document management (upload, query, delete)
  - Corpus management (create, query, permissions)
  - Usage statistics (self-service and per-corpus)
  - MCP protocol (JSON-RPC 2.0)
  - Error codes and rate limiting

- **[MCP Integration Guide](docs/MCP_INTEGRATION.md)** - Model Context Protocol integration for AI agents
  - Quick start guide
  - Available tools (4 semantic search tools)
  - Streaming queries via SSE
  - Error handling with retry strategies
  - Python client examples
  - Claude Desktop configuration

### Quick Links

| Topic | Resource |
|-------|----------|
| Getting Started | [README](#run-the-app) |
| API Documentation | [Swagger UI](http://localhost:8511/api/docs) |
| System Architecture | [ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| API Reference | [API_REFERENCE.md](docs/API_REFERENCE.md) |
| MCP Integration | [MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) |
| Python MCP Client | [examples/mcp/python_client.py](examples/mcp/python_client.py) |
| Streaming Client | [examples/mcp/streaming_client.py](examples/mcp/streaming_client.py) |

---

## 📌 Roadmap Ideas

- [ ] Full file preview in UI
- [x] Multi-index search
- [ ] Support for local embedding models (offline mode)
- [x] User authentication
- [ ] Export/Import indexes

---

## 🧑‍💻 Built With

- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/)
- [ChromaDB](https://www.trychroma.com/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)

---

## 📝 License

MIT License – use freely, build something awesome.
