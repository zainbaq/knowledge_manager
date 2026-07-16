---
app: "knowledge_manager"
type: "ai"                          # RAG / semantic-search knowledge base with API + MCP
subdomain: "knowledge-manager.promethean-labs.co"   # from next/next.config.ts + tests; see note re: Heroku
current_instance: "unknown"         # no infra-as-code in repo; evidence points to Heroku, not EC2 — VERIFY
languages:
  - "python@3.9+"                   # README "Python 3.9+"; dev traceback shows 3.9; no .python-version/runtime.txt
  - "node@unknown"                  # Next.js 16 needs Node >=18/20; no .nvmrc pin — VERIFY
frameworks:
  - "fastapi@0.109.2"
  - "uvicorn@0.27.1"
  - "streamlit@>=1.36.0 (legacy UI, still in tree)"
  - "next@16.1.6"
  - "react@19.2.3"
  - "chromadb@>=0.4.24"
processes:
  - "uvicorn api.app:app  (backend REST + MCP, port 8000)"
  - "next  (frontend SPA/SSR, port 3000)"
  - "streamlit run ui/streamlit_app.py  (ALTERNATE legacy UI, port 8501 — not launched by run_app.py)"
listens_on_ports: [8000, 3000, 8501]   # 8501 only if Streamlit UI is used
build_steps_required: true          # next build; pip install; no DB migration tool (tables auto-create on import)
containerization_difficulty: "moderate"
aws_services: ["cognito"]           # JWT verify via public JWKS (backend) + Amplify Hosted UI (frontend). No SDK creds.
other_external_apis: ["openai (embeddings: text-embedding-3-small)"]
databases: ["sqlite (users.db, local disk file)"]
vector_store: "chromadb (self-hosted, local disk under VECTOR_DB_PATH; per-user + corpora/{id} dirs)"
queues_caches: []                   # none; in-process asyncio.Semaphore + in-memory TTLCache/client cache only
persistent_state_locations:
  - "VECTOR_DB_PATH (default ./data/vector_index) — ChromaDB per-user vector stores + corpora/"
  - "USER_DB_PATH (default ./users.db) — users, api_keys, corpuses, permissions, subscriptions, usage_logs"
state_must_migrate: true
env_vars:
  - OPENAI_API_KEY
  - OPENAI_EMBEDDING_MODEL
  - VECTOR_DB_PATH
  - USER_DB_PATH
  - API_KEY_TTL_DAYS
  - PASSWORD_MIN_LENGTH
  - REQUIRE_COMPLEX_PASSWORD
  - ADMIN_USERS
  - DEFAULT_RATE_LIMIT
  - UPLOAD_RATE_LIMIT
  - QUERY_RATE_LIMIT
  - MANAGEMENT_RATE_LIMIT
  - AUTH_RATE_LIMIT
  - MCP_QUERY_RATE_LIMIT
  - MCP_LIST_RATE_LIMIT
  - MCP_RESOURCE_RATE_LIMIT
  - EMBEDDING_CONCURRENCY
  - MAX_EMBEDDING_RETRIES
  - CORS_ORIGINS
  - COGNITO_USER_POOL_ID
  - COGNITO_CLIENT_ID
  - COGNITO_REGION
  - MIME_VALIDATION_BYTES
  - MAX_FILE_SIZE_MB
  - DEBUG
  - LOG_LEVEL
  - LOG_FILE
  - PORT
  - FRONTEND_PORT
  - API_HOST
  - API_URL
  - NEXT_PUBLIC_API_URL
  - NEXT_PUBLIC_COGNITO_DOMAIN
  - NEXT_PUBLIC_COGNITO_USER_POOL_ID
  - NEXT_PUBLIC_COGNITO_CLIENT_ID
  - NEXT_PUBLIC_REDIRECT_SIGN_IN
  - NEXT_PUBLIC_REDIRECT_SIGN_OUT
  - TEST_API_URL                    # tests only
hardcoded_secrets_found: false      # no live secrets committed; .env gitignored. See flags for non-secret hardcodings.
has_own_auth: true
auth_type: "apikey + jwt"           # X-API-Key (SQLite) AND Cognito Bearer JWT; also self-hosted register/login (bcrypt)
sso_integration_difficulty: "easy"  # Cognito OIDC already wired end-to-end (frontend Amplify + backend JWKS verify)
calls_other_apps: []                # no outbound calls to other Promethean apps found; it is a callee (MCP/REST)
executes_untrusted_code: false
resource_estimate: "~0.5-1 vCPU / 0.5-1GB idle; CPU/RAM spikes during PDF parse + bulk embedding of uploads"
health_check_endpoint: "/api/v1/status/ (also /api/status/)"   # returns {\"status\":\"ok\"}; no /health alias
aws_coupling: "soft"                # only Cognito; backend needs only public JWKS URL, no AWS creds/SDK/instance role
migration_difficulty: "medium"
confidence: "high"                  # code fully reviewed; gaps are runtime/infra facts (instance, data size) not in repo
---

# Migration-Readiness Audit — `knowledge_manager`

> Scope note: This audit is based entirely on the repository at branch
> `claude/migration-readiness-audit-d7yiot`. Runtime/infra facts that live outside the
> repo (the actual EC2/Heroku host, live data sizes, the deployed `.env`, the production
> nginx/reverse-proxy config) are **not in the repo** and are marked
> `UNKNOWN — needs verification`.

## 1. Identity & purpose

`knowledge_manager` ("Knowledge Manager" / "Knowledge Indexer") is a **multi-tenant RAG /
semantic-search service**. Users upload documents (`.pdf`, `.docx`, `.txt`, `.md`), which are
extracted to text (`ingestion/file_loader.py`), chunked (`ingestion/chunker.py`), embedded via
OpenAI (`vector_store/embedder.py`), and stored in a persistent **ChromaDB** vector store
(`vector_store/vector_index.py`). Users then query by semantic similarity across one/many/all of
their collections. It exposes both a REST API and a **Model Context Protocol (MCP)** JSON-RPC
endpoint so AI agents (e.g. Claude Desktop) can use it as a tool/resource server
(`api/v1/mcp.py`, `mcp/handlers.py`, `mcp/tools.py`).

It is **both a user-facing UI and a backend API/tool**:
- Backend API: `api/app.py` (FastAPI) — documents, corpuses, users, admin, MCP.
- Primary UI: a **Next.js 16 / React 19** SPA under `next/` (launched by `run_app.py`).
- A **Streamlit** UI (`ui/streamlit_app.py` + `ui/pages/*`) also exists and is fully featured, but
  `run_app.py:24-30` launches Next.js, not Streamlit — Streamlit appears to be the **superseded
  legacy** frontend still carried in the tree.

**Users & multi-tenancy:** Real per-user data isolation exists in code. Each user gets a private
ChromaDB directory derived from their username with path-traversal defenses
(`vector_store/vector_index.py:16-50`, `get_user_db_path`), and all document/query endpoints scope
to `current_user["db_path"]` (`api/v1/endpoints.py:289-315`). Beyond private stores there is a
**shared "corpus" layer** with owners, RBAC permissions (read/write/admin/owner), subscriptions,
and admin approval (`api/corpus_db.py`, `api/corpus_auth.py`, `api/v1/corpus.py`). Admins are
defined by the `ADMIN_USERS` env allowlist (`api/admin_auth.py:9-18`).

## 2. Runtime & tech stack

**Backend — Python.** README states "Python 3.9+"; the committed `backend.log` traceback is from
Python 3.9 on the developer's machine. **No `.python-version`, `runtime.txt`, or `pyproject.toml`
pins the version** — `UNKNOWN` exact runtime; `mypy.ini`/`pytest.ini` exist for tooling.
- Web framework: **FastAPI 0.109.2**, served by **Uvicorn 0.27.1** (`requirements.txt:15-16`).
- Vector DB client: **ChromaDB ≥0.4.24** (embedded/persistent mode).
- Doc parsing: **PyMuPDF (fitz) ≥1.23.0**, **python-docx 1.1.0**.
- Auth/crypto: **passlib[bcrypt] 1.7.4 + bcrypt 4.0.1** (pinned — see risks), **python-jose[cryptography] 3.3.0** (Cognito JWT), **cachetools** (JWKS cache).
- Rate limiting: **slowapi 0.1.9**; SSE via **sse-starlette 2.0.0**; MIME sniffing via **python-magic 0.4.27** (needs libmagic).
- Package manager: **pip**, lockfile = `requirements.txt` (pinned) + `requirements-dev.txt`. No hash-locked file (no `poetry.lock`/`uv.lock`).

**Frontend — Node/TypeScript.** `next/package.json`: **Next.js 16.1.6**, **React 19.2.3**,
TypeScript 5, Tailwind 4, Radix UI, TanStack Query, Zustand, react-hook-form/zod, and
**`aws-amplify` ^6.16.0** for Cognito auth. Package manager **npm** (`next/package-lock.json`
present). No `.nvmrc` — Node version `UNKNOWN` (Next 16 requires Node ≥18/20).

**Frontend/backend split:** Separate builds and separate processes. The Next.js app is a
standalone SPA/SSR client that calls the FastAPI backend over HTTP at `NEXT_PUBLIC_API_URL`
(`next/src/lib/api/client.ts:22`). Auth tokens are minted client-side by Amplify/Cognito and sent
as `Authorization: Bearer` (`client.ts:36-69`).

**Distinct processes / start commands:**
| Process | Start command | Manager | Port |
|---|---|---|---|
| Backend API + MCP | `uvicorn api.app:app --host 0.0.0.0 --port $PORT` (`Procfile.dev`) or `python api_main.py` | honcho (`Procfile`) / bare / Heroku dyno | 8000 |
| Next.js frontend | `npm run dev` (DEBUG) or `npm run start` → `next start -H 0.0.0.0 -p 3000` (`run_app.py:24-30`, `next/package.json:5-9`) | spawned by `run_app.py` | 3000 |
| Streamlit UI (legacy) | `streamlit run ui/streamlit_app.py` | manual | 8501 |

There is **no background worker, scheduler, cron, or websocket server**. Embedding concurrency is
handled *inside* the request via `asyncio` + a `Semaphore` (`api/v1/endpoints.py:68-86`); SSE
streaming is a normal request handler (`api/v1/mcp.py:242`).

**Build steps required before running:**
- Backend: `pip install -r requirements.txt`; provide `.env` (at minimum `OPENAI_API_KEY`, else
  `config.py:19-20` raises at import).
- Frontend: `npm install` + `npm run build` (for production `next start`).
- **No DB migrations tool** — SQLite tables are created lazily on import
  (`api/users.py:139 init_db()`, `api/corpus_db.py:147 init_corpus_tables()`), and columns are
  added ad-hoc via `ALTER TABLE` guards (`api/users.py:46-92`). No `collectstatic`.

## 3. Containerization readiness

**Existing container assets:** **None.** There is **no `Dockerfile`, `docker-compose.yml`,
`.dockerignore`**. There **is** a `Procfile` (`web: honcho start -f Procfile.dev`) and a
`Procfile.dev` (`backend: uvicorn ...`) — a Heroku/honcho-style process declaration, **not**
container config. Note the `Procfile` only wires up the **backend**; the Next.js frontend is not in
the Procfile (it's started by `run_app.py`), implying frontend and backend may be deployed
separately in production.

**OS-level / native dependencies:**
- **libmagic** — required by `python-magic` for MIME sniffing. Handled gracefully: if the import
  fails, MIME validation is skipped (`api/app.py:10-14`, `api/v1/endpoints.py:10-14`,
  `MAGIC_AVAILABLE`). So it's a "should-install" (`apt-get install libmagic1`), not a hard blocker.
- **PyMuPDF** ships prebuilt wheels (bundled MuPDF binary) — no system package needed normally.
- **No** ffmpeg, tesseract, poppler, headless browser, or ODBC drivers.
- Frontend build pulls `sharp` (native image lib) transitively — normal for Next.js.

**Ports:** Backend `PORT` (default 8000) and `FRONTEND_PORT` (default 3000) are **configurable via
env** (`config.py:88-90`). Streamlit hardcodes 8501 behavior. Uvicorn binds `0.0.0.0`
(`api_main.py`, `Procfile.dev`), Next binds `0.0.0.0` (`package.json`) — container-friendly.

**Host assumptions baked in:**
- `run.sh` hardcodes `~/knowledge_manager/run_app.py` and `source .venv/bin/activate` — host/user
  specific; not usable in a container as-is.
- Default state paths are **inside the project dir** (`./data/vector_index`, `./users.db`) via
  `config.py:24-27` — writes inside the working tree unless `VECTOR_DB_PATH`/`USER_DB_PATH` are
  overridden. These MUST be redirected to a mounted volume in a container.
- `run_app.py` uses `subprocess.Popen` to co-launch backend + frontend in one process tree — an
  anti-pattern for containers (one process per container is cleaner).

**Assessment: MODERATE.** No code-level blockers, but non-trivial: two runtimes (Python + Node) to
containerize (likely two images), a system lib (libmagic) to add, and two persistent volumes
(Chroma dir + SQLite file) to externalize. No Dockerfile exists, so it must be authored from
scratch.

## 4. External service & platform dependencies

**AWS services:**
- **Cognito — the *only* AWS dependency, and it is loosely coupled.**
  - *Backend:* verifies Cognito JWTs by fetching the pool's **public JWKS** over plain HTTPS
    (`api/cognito.py:21-46`) and validating RS256 signature/issuer/audience with `python-jose`
    (`api/cognito.py:70-121`). **No AWS SDK (boto3), no AWS credentials, and no instance IAM role
    are used** anywhere (grep for `boto3`/`s3`/`secretsmanager`/etc. returns nothing in app code).
    This means the backend can verify Cognito tokens **from any host** — it only needs outbound
    HTTPS to `cognito-idp.<region>.amazonaws.com`.
  - *Frontend:* uses `aws-amplify` to drive the Cognito **Hosted UI** OAuth code flow
    (`next/src/lib/auth/config.ts`, `next/src/components/auth/AuthProvider.tsx`).
  - Config via env only: `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_REGION`
    (`config.py:56-62`); Cognito is optional — `COGNITO_ENABLED` is false if unset, and API-key
    auth still works.
- **No** S3, RDS/Aurora, DynamoDB, SES, SQS/SNS, Secrets Manager/SSM, ECR, Bedrock, CloudFront,
  EFS, or IAM-role usage found in code.

**Other third-party APIs / SaaS:**
- **OpenAI** — embeddings only, model `text-embedding-3-small` (`vector_store/embedder.py`,
  `config.py:21`). Client constructed at import with `OPENAI_API_KEY`
  (`vector_store/embedder.py:12`). Default base URL (api.openai.com); no Azure OpenAI. **This is a
  hard runtime dependency** — the process refuses to start without `OPENAI_API_KEY`
  (`config.py:19-20`), and every ingest/query calls OpenAI.
- No payment, analytics, or email provider integrations in code (Cognito handles email/verification).

**Databases:** **SQLite** single file (`users.db`), shared by the users module and the corpus
module (`api/users.py:27`, `api/corpus_db.py:10`). Self-hosted, on local disk, same box as the app.
Connections opened per-call via `sqlite3.connect` (`_get_conn`). No connection pool, no
PostgreSQL/MySQL. **Portability: portable to any host**, but SQLite-on-local-disk does not survive
an ephemeral container filesystem and does not support multiple app replicas writing concurrently.

**Vector store:** **ChromaDB in embedded PersistentClient mode** (`vector_store/vector_index.py:92-123`) —
self-hosted, data on local disk under `VECTOR_DB_PATH`. Not a managed/remote vector service.
Clients are cached in-process (`_client_cache`). **Portability: portable**, but same local-disk /
single-writer caveats as SQLite.

**Queues / caches / brokers:** **None.** No Redis/RabbitMQ/Celery. "Caches" are all in-process and
ephemeral: JWKS `TTLCache` (`api/cognito.py:17`), Chroma client cache (`vector_index.py:12`),
`asyncio.Semaphore` for embedding concurrency.

**Portability verdict per dependency:** OpenAI = portable (any host w/ outbound HTTPS + key);
Cognito = AWS-managed but reachable from anywhere (soft); SQLite + ChromaDB = portable but local-disk-bound.

## 5. State & persistence

Everything the app persists lives on **local disk** (no object storage, no managed DB):

| State | Location (default) | Format | Must migrate? |
|---|---|---|---|
| Per-user vector stores | `VECTOR_DB_PATH/<username>/` (default `./data/vector_index/<username>`) | ChromaDB (SQLite + HNSW binary index files) | **Yes** — user embeddings/documents |
| Curated corpus vector stores | `VECTOR_DB_PATH/corpora/<corpus_id>/` (`vector_index.py:53-89`) | ChromaDB | **Yes** — shared knowledge corpuses |
| User accounts, API keys, corpus metadata/permissions/subscriptions/usage logs | `USER_DB_PATH` (default `./users.db`) | SQLite | **Yes** — identity + RBAC + billing/usage data |
| Application logs | stdout always; file only if `LOG_FILE` set, rotating 10MB×5 (`logging_config.py:48-60`) | text | No (ephemeral/regenerable) |

- **User-uploaded documents:** *Not* stored as files. Uploads are written to a **temp file, parsed,
  then deleted** (`api/v1/endpoints.py:145-150`); only the **chunk text + embeddings + metadata**
  (`source` filename, `chunk_index`) are persisted into ChromaDB. So the original PDFs/DOCX are not
  retained — only their extracted/chunked representation.
- **Embeddings/vector indexes:** stored inside the ChromaDB directories above (cosine space,
  `hnsw:space` metadata — `vector_index.py:160-163`).
- **Schema management:** No migration framework. Tables auto-create on import; schema evolution is
  done with defensive `PRAGMA table_info` + `ALTER TABLE` (`api/users.py:46-92`,
  `_ensure_cognito_schema`, `_ensure_api_key_schema`). A straight file copy of `users.db` preserves
  everything.
- **Data size:** `UNKNOWN — needs verification`. Neither `./data` nor `users.db` exists in this
  fresh checkout (both are gitignored — `.gitignore:13-21`). To size on the live host:
  `du -sh $VECTOR_DB_PATH` and `ls -la $USER_DB_PATH`.

**Must-preserve set:** the ChromaDB tree under `VECTOR_DB_PATH` (user + corpora vector data) **and**
the `users.db` SQLite file. Both must be copied together and kept consistent (usernames in SQLite
map to directory names under `VECTOR_DB_PATH`). **Ephemeral/regenerable:** logs, temp upload files,
in-memory caches. Note re-embedding to rebuild vectors would cost OpenAI API calls, so treat vector
data as must-migrate, not "just re-index."

## 6. Configuration & secrets

**Config source:** `config.py` reads everything from env via `python-dotenv` `load_dotenv()`
(`config.py:12`). `.env.example` documents the common subset; a real `.env` is gitignored
(`.gitignore:5-8`). Frontend reads `NEXT_PUBLIC_*` at build/runtime (`next/src/lib/**`).

**Full env-var list:** see the `env_vars` block in the front-matter (grepped from
`config.py`, `next/src/lib/*`, `ui/*`, and tests). Backend vars are read only in `config.py`;
frontend `NEXT_PUBLIC_*` in `next/src/lib/auth/config.ts` and `next/src/lib/api/client.ts`.

**Config files:**
- `config.py` — central backend config (paths, OpenAI, rate limits, CORS, Cognito, file limits, ports).
- `next/next.config.ts` — sets `allowedDevOrigins: ["https://knowledge-manager.promethean-labs.co"]`.
- `mypy.ini`, `pytest.ini` — tooling only.
- `Procfile` / `Procfile.dev` — process declaration.

**Secrets handling:** Secrets come from the `.env` file / process env. **No live secrets are
committed** (`.env.example` holds only placeholders like `sk-your-openai-key`; the analysis doc
claims git history is clean). API keys are stored **hashed** (SHA-256) in SQLite, never in plaintext
(`api/users.py:177-178`); passwords are bcrypt-hashed (`api/users.py:159-162`).
- **Not secrets, but flag-worthy hardcodings:** a production **Heroku URL** is hardcoded as a
  default in `ui/pages/documentation.py:7,61` (`https://knowledge-manager-236c8288fac7.herokuapp.com`),
  and `ui/utils/api_client.py:6` hardcodes `http://127.0.0.1:8000` with a stray debug `print`. The
  prod subdomain is hardcoded in `next/next.config.ts` and `tests/test_external_connectivity.py`.

**Minimum credentials to boot:** `OPENAI_API_KEY` is the only hard requirement (`config.py:19-20`
raises `RuntimeError` without it). Cognito vars are optional (API-key auth works without them). The
frontend additionally needs the `NEXT_PUBLIC_COGNITO_*` values to enable login.

## 7. Networking, auth & integration

**Reverse proxy / nginx:** **No nginx or reverse-proxy config is present in the repo.** The
production TLS/proxy setup is `UNKNOWN — needs verification` (check the live host). The SSE endpoint
does set `X-Accel-Buffering: no` (`api/v1/mcp.py:384`), which is an nginx hint — suggesting nginx is
(or was) in front, but the config itself is not in the repo. **TLS handling is `UNKNOWN`** (Heroku
would terminate TLS at the platform router; an EC2+nginx setup would use certbot/ACM — cannot tell
from code).

**Authentication (critical for SSO planning):** The app has **its own auth** with **three coexisting
mechanisms** in `get_current_user` (`api/auth.py:17-77`):
1. **`X-API-Key` header** — opaque key, looked up (SHA-256) in SQLite `api_keys`, 90-day TTL
   (`api/users.py:329-358`). Used by MCP clients and programmatic access.
2. **`Authorization: Bearer <JWT>`** — **Cognito** access/id tokens, verified against Cognito JWKS
   (`api/auth.py:39-71` → `api/cognito.py`). On first login a local user row is auto-provisioned
   and linked by `cognito_sub` (`api/users.py:430-513 get_or_create_cognito_user`).
3. **Self-hosted username/password** — `/register`, `/login`, `/create-api-key` with bcrypt
   (`api/users.py:305-326`), which mint API keys. This is the legacy path (also what the Streamlit UI uses).

Users are stored in the local **SQLite `users` table**; a `cognito_sub` column links them to
Cognito (`api/users.py:104-111`). The Next.js frontend expects **Cognito Hosted UI** to render the
login page (redirect-based OAuth code flow) and sends a **Bearer token** to the API — it does
**not** manage its own login form.

**SSO integration difficulty: EASY.** This app is arguably *already* the reference implementation for
the unified SSO the founder wants — Amplify+Cognito on the frontend and JWKS verification on the
backend are fully wired (`docs/COGNITO_AUTH.md`, `docs/unified-user-base-implementation-plan.md`
describe exactly the "one Cognito pool, many app clients" pattern). To place it behind an external
OIDC IdP: point the existing Cognito envs at the shared pool/app-client and update redirect URIs.
If the target IdP is *not* Cognito (e.g. self-hosted OIDC), the backend verify path
(`api/cognito.py`) would need to be generalized to a generic OIDC issuer/JWKS — modest, since it's
already standard RS256/JWKS. The API-key path can remain for machine/MCP access.

**CORS:** Configured in `api/app.py:127-134`: `allow_origins=CORS_ORIGINS` (default
`http://localhost:3000`, `config.py:52-53`) **plus** a regex allowing any `localhost`/`127.0.0.1`
port, with `allow_credentials=True` and `allow_methods` incl. OPTIONS/PATCH. Production origins must
be added via `CORS_ORIGINS`. (Note: `allow_credentials=True` combined with broad origins is worth a
security look during migration, though `"*"` is only used if explicitly set.)

**Websockets / streaming / long-lived connections:** No websockets. There **is SSE streaming**
(`/api/v1/mcp/query/stream`, `api/v1/mcp.py:242-386`) — a reverse proxy in front must disable
response buffering and allow long-lived streaming responses (the code already emits the nginx hint).

**Inter-app calls (to other Promethean apps):** **None found.** This app makes **no outbound calls
to sibling apps** (no data-agent / doc-intelligence URLs in code). It is a **callee**: other apps /
AI agents call *it* via REST or the MCP endpoint. The only outbound HTTP is to OpenAI and to the
Cognito JWKS URL. So in the consolidated architecture, `knowledge_manager` is a downstream service
that others depend on — relevant for start-order and shared-network planning.

## 8. Resource footprint & workload shape

- **Drivers of CPU/RAM:** (a) **PDF/DOCX text extraction** (PyMuPDF/python-docx) is CPU-bound and
  runs in a threadpool (`asyncio.to_thread`, `endpoints.py:149`); (b) **embedding generation** is
  network-bound (OpenAI) but fans out up to `EMBEDDING_CONCURRENCY` (default **10**) concurrent
  calls per request (`config.py:48`, `endpoints.py:68`); (c) **ChromaDB** loads HNSW indexes into
  memory per active collection — RAM grows with corpus size and number of distinct user collections
  held in the client cache.
- **Rough estimate:** idle footprint is small (~0.5–1 GB RAM, low CPU). **Spikes** occur on bulk
  uploads (parse + embed many chunks) and on multi-collection queries that load several ChromaDB
  indexes at once. Precise numbers are `UNKNOWN — needs verification` (depends on live corpus size).
- **Background/scheduled work:** None. No cron/timer/worker. Expired API keys are purged
  opportunistically during `init_db()` and on lookup (`api/users.py:71-75, 348-352`), not on a schedule.
- **Concurrency model:** single Uvicorn process, async event loop; blocking work offloaded to the
  default threadpool. **Hardcoded knobs:** `EMBEDDING_CONCURRENCY=10`, `MAX_EMBEDDING_RETRIES=3`.
  No configured `--workers` (Procfile/`api_main.py` run a single worker). ChromaDB client cache is
  process-global and unbounded (grows with distinct `db_path`s).
- **Noisy-neighbor risk:** Moderate. Parsing large PDFs and holding multiple in-memory HNSW indexes
  can cause CPU/RAM bursts that would affect co-located apps. Unbounded Chroma client cache is a slow
  memory-growth risk on a shared box.

## 9. Untrusted / arbitrary code execution

- **Does it execute user code / eval / shell?** **No.** No `eval`/`exec` of user input, no dynamic
  code interpreter, no user-driven SQL (all SQL is parameterized; corpus updates build column lists
  from a fixed allowlist, `api/v1/corpus.py:327-355`). The only `subprocess` use is `run_app.py`
  launching the app's *own* backend/frontend (`run_app.py:18,27`) — not user-controlled.
- **File handling:** It parses **untrusted uploaded documents** (PDF/DOCX/TXT/MD) with PyMuPDF and
  python-docx. That's parsing, not execution, but these libraries process attacker-supplied binaries
  — a memory-safety bug in PyMuPDF/MuPDF is the realistic risk surface here. Uploads are validated by
  extension, size (≤25 MB), and libmagic MIME sniffing (`endpoints.py:89-136`) and parsed in a temp
  file that is deleted immediately.
- **Docker-in-Docker / privileged ops / container spawning:** None.
- **Runs as root / network/filesystem scope:** `UNKNOWN` at runtime — no evidence of privileged
  operations in code; it only reads/writes under its configured data dir.
- **Shared-host danger:** Low from a code-execution standpoint. The main isolation consideration is
  the untrusted-document parser (PyMuPDF) — on a shared kernel, run it as a non-root user with
  limited filesystem access. There is **no** sandbox today because none is needed for the current
  feature set.

## 10. Build, deploy & operations (current state)

- **Build/deploy tooling in repo:** No CI/CD pipeline, no `.github/workflows`, no deploy script
  beyond `run.sh` (a dev convenience that activates `.venv` and runs `run_app.py`). The `Procfile`
  (`web: honcho start -f Procfile.dev`) + `config.py`'s explicit "Heroku provides PORT env var"
  comment (`config.py:87-88`) + a hardcoded `*.herokuapp.com` URL
  (`ui/pages/documentation.py`) strongly indicate the **backend was deployed on Heroku** at some
  point. Meanwhile the live domain `knowledge-manager.promethean-labs.co` and the audit's stated
  EC2+nginx context suggest it may now (also) run behind nginx on a VM. **The actual current host is
  `UNKNOWN — needs verification`** — this discrepancy is important for the migration and should be
  confirmed with the owner.
- **How updates ship / restart:** `UNKNOWN` (no scripts). On Heroku it would be `git push` + dyno
  restart; on a VM it would be a manual pull + process restart. No systemd unit or pm2 config is in
  the repo.
- **Health/readiness endpoint:** **Yes** — `GET /api/v1/status/` (and legacy `/api/status/`) return
  `{"status":"ok"}` (`api/v1/endpoints.py:205-209`). Usable as a container/LB health check. There is
  no `/health` alias and no deep readiness check (it doesn't verify OpenAI/Chroma reachability).
- **Logging:** Structured logging to **stdout** by default; optional rotating file if `LOG_FILE` is
  set (`logging_config.py`). Request logging middleware records method/path/user/status/duration
  (`api/middleware/request_logging.py`, referenced in `api/app.py:114`). No centralized log shipping
  configured — stdout capture by the platform is assumed.
- **Cron/timers:** None.

## 11. Risks, fragility & tech debt

- **Local-disk state on an ephemeral filesystem:** SQLite + ChromaDB default to paths *inside the
  project dir* (`config.py:24-27`). On Heroku's ephemeral dyno FS or an unmounted container, **all
  user data would be lost on restart**. Migration MUST externalize `VECTOR_DB_PATH` and
  `USER_DB_PATH` to a persistent volume. This is the single biggest lift-and-shift trap.
- **Single-writer stores:** SQLite and embedded ChromaDB do not support multiple app replicas
  writing concurrently. The app **cannot be horizontally scaled** as-is without switching to
  networked stores (e.g. Postgres + a client/server Chroma or another vector DB).
- **Two frontends in one repo:** Streamlit (`ui/`) and Next.js (`next/`) both exist; only Next.js is
  wired into `run_app.py`. Ambiguity about which is "production" should be resolved before migration
  (dead code vs. supported UI).
- **`bcrypt` pinned to 4.0.1** with a comment that passlib 1.7.4 breaks on bcrypt ≥4.1
  (`requirements.txt:30-31`); git history shows repeated bcrypt/passlib breakage
  (commits "fix password issue", "pin bcrypt…"). Fragile dependency corner to preserve exactly
  during any rebuild.
- **Committed `backend.log`** contains a developer's absolute path
  (`/Users/zainbaq/...`) and a stack trace — should not be in the repo; low sensitivity but noise.
- **Schema managed by ad-hoc `ALTER TABLE`** rather than a migration tool — works, but risky to
  evolve and hard to reason about across versions.
- **Hardcoded prod/localhost URLs** in `ui/` and `next.config.ts`/tests (see §6) — will break or
  mislead if the domain changes during migration.
- **`OPENAI_API_KEY` hard-required at import** (`config.py:19-20`): the process won't even start
  without it — fine, but means health checks/CI need the key or a mock.
- **CORS `allow_credentials=True` + localhost regex**: acceptable for dev, but review before exposing
  publicly behind the unified proxy.
- **Licensing:** App is MIT (`README.md`). Bundled/self-hosted components to note for a self-hosted
  target: **ChromaDB** (Apache-2.0), **PyMuPDF** (**AGPL-3.0** / commercial — the notable one: AGPL
  can carry obligations for networked services; verify this is acceptable for the consolidated
  hosting model), FastAPI/Streamlit/Next.js (MIT/BSD). **PyMuPDF's AGPL license is the one to flag.**

---

## Migration-relevant flags

- **AWS coupling / can it run on any Docker host?** **Yes, with soft coupling.** The only AWS tie is
  **Cognito**, and the backend only needs the *public* JWKS URL over HTTPS — no boto3, no AWS creds,
  no instance IAM role. It can run on any Docker host / non-AWS VPS today, keeping Cognito as the
  external IdP (or swapping it for another OIDC provider with a modest change to `api/cognito.py`).
  The hard external dependency is **OpenAI** (network + API key), not AWS.

- **What state must migrate, and how big/risky?** Two things, together: the **ChromaDB tree**
  (`VECTOR_DB_PATH`, per-user + `corpora/` vector data) and the **`users.db` SQLite file**
  (identity, API keys, RBAC, subscriptions, usage). They're consistency-linked (usernames ↔
  directory names). Size is `UNKNOWN` — measure with `du -sh $VECTOR_DB_PATH` and `ls -la $USER_DB_PATH`
  on the live host. Risk is **medium-high** mainly because it currently sits on local/ephemeral disk;
  a clean, atomic copy onto a persistent volume is required, and vectors are expensive to regenerate.

- **Does it execute untrusted code / isolation needed?** **No arbitrary code execution.** The only
  attack surface is parsing untrusted uploaded PDFs/DOCX with PyMuPDF/python-docx. On a shared host,
  run it as a **non-root user with a constrained filesystem**; no sandbox/gVisor/DinD is otherwise
  required.

- **Unified external SSO — how much app change?** **Minimal.** Cognito OIDC is already implemented
  end-to-end (Amplify frontend + JWKS backend verification). Repointing to a shared Cognito pool is
  a config change. Moving to a non-Cognito OIDC IdP is a small, well-scoped backend change (generic
  issuer/JWKS). The X-API-Key path can stay for MCP/machine access. This app is effectively a working
  template for the SSO the founder is after.

- **Containerize cleanly?** **Moderate.** No Dockerfile exists yet; you'll likely build **two images**
  (Python backend, Node/Next frontend), add **libmagic** to the backend image, redirect the two
  **persistent stores** to mounted volumes, and drop the `run_app.py`/`run.sh` host assumptions. No
  hard blockers — ports and bind addresses are already env-configurable and `0.0.0.0`.

- **Any reason NOT to share a host with other apps?** Two soft reasons: (1) **noisy-neighbor** CPU/RAM
  spikes from PDF parsing + bulk embedding + in-memory HNSW indexes (unbounded Chroma client cache);
  (2) it holds **all its user data on local disk** with single-writer stores, so it wants a stable,
  persistent volume and cannot be casually replicated. It can co-locate, but give it resource
  limits and dedicated persistent storage.

---

## Open questions for the owner

1. **Where does it actually run today** — Heroku (Procfile/`herokuapp.com`/PORT comments) or an
   EC2 instance behind nginx (the audit's premise + `knowledge-manager.promethean-labs.co`)? Both,
   or migrated? What instance type/size?
2. **Live data sizes:** `du -sh` of the ChromaDB dir and byte size of `users.db`; approx. user count
   and total document/chunk count. (Needed to plan the copy.)
3. **Is the Streamlit UI (`ui/`) still used in production, or is Next.js the sole frontend?** Can
   Streamlit be dropped?
4. **Production `.env` values** (names only are in this report): confirm `VECTOR_DB_PATH`/`USER_DB_PATH`
   point at a persistent location today, the Cognito pool/client IDs, and the real `CORS_ORIGINS`.
5. **Production TLS + reverse proxy:** who terminates TLS and what does the current nginx (or Heroku
   router) config look like (timeouts, body-size for 25 MB uploads, SSE buffering)?
6. **OpenAI account/billing** for the embedding key — is it a shared org key, and are there rate/cost
   limits to preserve?
7. **Is Cognito the intended long-term IdP for the unified SSO**, or should this move to a self-hosted
   OIDC provider (which would require generalizing `api/cognito.py`)?
8. **PyMuPDF AGPL** — is AGPL acceptable for the consolidated hosting, or is a commercial license /
   alternative parser needed?

---

## Files reviewed

Backend / config:
- `README.md`, `config.py`, `requirements.txt`, `requirements-dev.txt`, `.env.example`, `.gitignore`
- `Procfile`, `Procfile.dev`, `run.sh`, `run_app.py`, `api_main.py`, `logging_config.py`, `backend.log`
- `api/app.py`, `api/auth.py`, `api/cognito.py`, `api/users.py`, `api/admin_auth.py`
- `api/corpus_db.py`, `api/corpus_auth.py`, `api/rate_limiting.py`
- `api/v1/__init__.py`, `api/v1/endpoints.py`, `api/v1/corpus.py`, `api/v1/mcp.py`
- `vector_store/vector_index.py`, `vector_store/embedder.py`
- `ingestion/file_loader.py`, `ingestion/chunker.py`
- `mcp/handlers.py`
- `ui/streamlit_app.py`, `ui/utils/api_client.py`, `ui/pages/documentation.py` (partial)

Frontend:
- `next/package.json`, `next/next.config.ts`, `next/src/lib/auth/config.ts`,
  `next/src/lib/api/client.ts`, `next/src/components/auth/AuthProvider.tsx`

Docs / tests (scanned):
- `docs/unified-user-base-implementation-plan.md`, `docs/KNOWLEDGE_MANAGER_ANALYSIS.md` (head),
  `docs/COGNITO_AUTH.md` (refs), `docs/MCP_INTEGRATION.md` (refs)
- `tests/test_external_connectivity.py`, `tests/test_performance.py`, and repo-wide greps for
  `os.getenv`/`process.env`, `subprocess`/`eval`/`exec`, `boto3`/AWS SDK usage, and inter-app URLs.

Not present in checkout (gitignored / not in repo): `.env`, `users.db`, `data/` (vector store),
any `Dockerfile`/`docker-compose.yml`/nginx config/CI pipeline.

**Overall confidence: HIGH** on everything determinable from source. The remaining gaps
(current host, live data sizes, production `.env`/proxy) are runtime/infra facts that do not exist in
the repository and are enumerated in "Open questions for the owner."
