# Knowledge Manager — Phase 0 Audit

**Date:** 2026-08-16
**Scope:** direct audit of `knowledge_manager` against (a) the unified-auth contract proven in `promethean-data-agent`, (b) the consolidation plan's checklist for this app, (c) general code health.
**Method:** direct read of this codebase + comparison against `promethean-data-agent` (the app that already completed this pass) and `the-jarvis-project-agent-server` (this app's live consumer). No two-repo fork diff exists for this app, so findings are derived by reading, with `file:line` citations.

---

## 0. Corrections to the standing docs

Two claims in the briefing/consolidation docs are wrong and change the plan:

| Claim | Reality |
|---|---|
| "No app has its production hostname committed anywhere yet." | **False for this app.** `next/next.config.ts:4` commits `https://knowledge-manager.promethean-labs.co` in `allowedDevOrigins`. |
| "Only a small env-var documentation gap" on Cognito. | **Understated.** `.env.example` contains **zero** `COGNITO_*` entries despite `config.py:56-62` reading three of them and the frontend needing five `NEXT_PUBLIC_COGNITO_*`. It also still ships Streamlit-era values (`FRONTEND_PORT=8501`, `CORS_ORIGINS=http://localhost:8501`) that contradict the actual Next frontend port (3000). |

One claim confirmed and worth restating loudly, because it constrains everything:

> **The `ai` app authenticates to Knowledge Manager with a username/password login that mints a legacy API key** — not with Cognito.
> `the-jarvis-project-agent-server/backend/tools/km_connector.py:123` → `POST /api/v1/user/login`, then `X-API-Key` on every subsequent call (`km_connector.py:45-48`).
> Endpoints consumed: `/api/v1/query/`, `/api/v1/list-indexes/`, `/api/v1/corpus/`, `/api/v1/corpus/{id}/query`.
>
> **Consequence:** the local username/password + API-key path is load-bearing production infrastructure. "Unify on Cognito" here must mean *add/normalize Cognito*, never *remove local auth*. Removing it silently breaks RAG in the `ai` app.

---

## 1. Security findings

### 1.1 🔴 Cross-tenant data exposure via username→directory collision

Every user's documents live in a directory named after their username:
`api/users.py:466` / `:510` → `get_user_db_path(username)` → `vector_store/vector_index.py:36` → `sanitize_path_component(username)`.

`api/validation.py:161-164` strips `..` **and then every remaining `.`**:

```
'zain.baq@gmail.com'  ->  'zainbaq@gmailcom'
'zainbaq@gmailcom'    ->  'zainbaq@gmailcom'   # same directory
'a.b@x.com'           ->  'ab@xcom'
'ab@xcom'             ->  'ab@xcom'            # same directory
```

(verified by executing the function's logic)

`users.username` is `UNIQUE`, so these are two genuinely distinct accounts — but they resolve to **one shared ChromaDB directory**. Each user reads, queries, and can delete the other's collections.

This is unreachable through local registration (`validate_username`, `api/validation.py:40`, rejects `.` and `@`). It is reachable through **Cognito**, because `get_or_create_cognito_user` (`api/users.py:430`) never validates the username it receives — and Cognito usernames are commonly email addresses. Moving to a **shared** pool widens the exposure: users provisioned by any other app in the estate land here too.

Same root cause, second symptom: a Cognito username of `....` sanitizes to `''`, and `(base/'').resolve() == base` passes the containment check at `vector_index.py:45` — that user is handed the **root** vector store.

### 1.2 🔴 Privilege escalation through the Cognito path

Admin rights are granted by username string match: `api/admin_auth.py:19` → `username in ADMIN_USERS`, and `.env.example:20` ships `ADMIN_USERS=admin,superuser`.

Local registration blocks this — `validate_username` reserves `admin`, `root`, `system`, `api`, `test`, `user` (`api/validation.py:47`). The Cognito path does not call `validate_username` at all, so a pool user named `admin` is provisioned as local user `admin` and passes `get_admin_user`. On a shared pool, whoever registers that name in any app becomes an admin here.

### 1.3 🟠 CORS permanently trusts localhost, with credentials

`api/app.py:127-134`:
```python
allow_origins=CORS_ORIGINS,
allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
allow_credentials=True,
```
The regex is unconditional — it applies in production. Any page on any localhost port can make credentialed cross-origin requests to the production API. Should be dev-only (or dropped entirely once the frontend proxies same-origin — see §3.1).

### 1.4 🟡 Config refuses to import without an OpenAI key

`config.py:19-20` raises at import time. Every `docker build`-time check, every `pytest` collection, and any healthcheck path that imports config needs a key present. Data-agent handles this with compose-level `${OPENAI_API_KEY:?...}` and no import-time raise.

---

## 2. Consolidation-plan gaps

| Item | Status |
|---|---|
| Dockerfile (backend) | **Absent.** No `Dockerfile`, `.dockerignore`, or entrypoint anywhere in the repo. |
| Dockerfile (frontend) | **Absent**, and blocked: `next/next.config.ts` has no `output: 'standalone'`, which data-agent's frontend image depends on (`next/Dockerfile:69`). |
| `docker-compose.yml` | **Absent.** |
| `libmagic1` system dep | Not installed anywhere. `api/v1/endpoints.py:10-14` degrades silently — MIME validation is skipped entirely when the import fails (`:119-120`), so uploads are extension-checked only. |
| Non-root runtime | Not applicable yet (no image); must be built in from the start. |
| `/health` endpoint | **Absent.** Only `/api/v1/status/` and `/api/status/`, both rate-limited (`endpoints.py:206`) — a poor healthcheck target. Data-agent's compose healthcheck expects `/health` (`docker-compose.yml:75`). |
| Streamlit removal | Not started. `ui/` (14 files) + `streamlit>=1.36.0` (`requirements.txt:21`) + README references. |
| Heroku artifacts | `Procfile`, `Procfile.dev` still present; `config.py:88` still comments `PORT` as "Heroku provides". `run.sh:5` hardcodes `~/knowledge_manager`. |
| PyMuPDF AGPL | Unresolved (`requirements.txt:12`). Shared concern with `document-intelligence` and `promethean-ai` — one decision, three repos. |
| Vector store + user DB atomic migration | Not addressed. Coupling confirmed real: `users.db` usernames are the directory names under `VECTOR_DB_PATH` (§1.1). Note the §1.1 fix changes this mapping, so **the fix and the migration must be designed together**. |

---

## 3. Uniformity gaps vs. `promethean-data-agent`

The frontends are already close: identical Next 16.1.6, React 19.2.3, `aws-amplify` ^6.16.0, Tailwind 4, shadcn/Radix, zustand, react-query. The divergence is in wiring, not stack.

### 3.1 Frontend→backend transport differs

- **data-agent:** same-origin. Next `rewrites()` proxies `/api/*` and `/health` to `BACKEND_URL` (`next/next.config.ts`). No `NEXT_PUBLIC_API_URL`, no browser CORS.
- **knowledge_manager:** cross-origin. Browser calls `NEXT_PUBLIC_API_URL` directly (`next/src/lib/api/client.ts:22`, and again at `next/src/app/(dashboard)/docs/page.tsx:13`).

This is why §1.3's CORS hole exists. It also means the backend URL must be baked into the bundle at build time, adding a build arg data-agent doesn't need.

### 3.2 Other config deltas

| | data-agent | knowledge_manager |
|---|---|---|
| Frontend port | 8501 | 3000 |
| `output: 'standalone'` | yes | **no** |
| Security headers (HSTS, X-Frame-Options, …) | yes | **no** |
| `compress`, `devIndicators: false` | yes | no |
| `.dockerignore` | yes | n/a |
| `.gitattributes` (CRLF guard) | yes — added after the entrypoint bug | **no** |

That last row matters: data-agent's live verification found a CRLF line-ending break in its container entrypoint. This repo has no `.gitattributes` and any entrypoint written here will be authored on Windows. Add the guard before writing the script, not after.

---

## 4. Code health

### 4.1 🟠 The entire API is implemented twice

`api/app.py:159-391` re-implements `QueryRequest`, `validate_upload_files`, `_process_single_file`, `process_files`, `_generate_embedding_with_retry`, and all six document endpoints — near-duplicates of `api/v1/endpoints.py`. ~230 duplicated lines, plus a second `_embedding_semaphore` (`app.py:70` vs `endpoints.py:68`), so the configured `EMBEDDING_CONCURRENCY` cap is effectively doubled if both routers see traffic.

The copies have **already diverged**: v1 returns 413/415/422 with typed response models; the legacy router returns flat 400/500 JSON.

The legacy `/api/*` mount is marked deprecated (`app.py:120`). Confirmed safe to delete — the only known external consumer, the `ai` app, calls `/api/v1/*` exclusively (`km_connector.py:183,216,227,241` and `:123`).

### 4.2 Committed artifacts that should not be tracked

`git ls-files` returns 5 `__pycache__/*.pyc` files and `backend.log`, despite `.gitignore:1-2` listing both patterns — they were committed before the rules existed and are still tracked.

### 4.3 Deprecated / fragile patterns

- `api/app.py:138` uses `@app.on_event("shutdown")`, removed in favor of lifespan handlers; `fastapi==0.109.2` (`requirements.txt:15`) is well behind data-agent's.
- `api/users.py:139` calls `init_db()` **at import time** — a filesystem write as an import side effect, which fights container startup ordering and test collection.
- `numpy` (`requirements.txt:4`) and `chromadb>=0.4.24` are unpinned/floor-pinned; data-agent pinned everything during its pass.
- `honcho` (`requirements.txt:27`) exists only to run the Heroku `Procfile` — dead once containerized.

### 4.4 Confirmed *not* broken (checked because data-agent's pass found these)

- **JWKS caching** — `api/cognito.py:17` caches for 1h. Data-agent's per-request-userinfo-round-trip bug does **not** exist here.
- **Corpus RBAC ownership** — every mutating corpus route calls `check_corpus_permission` at the right level (`api/v1/corpus.py:213,322,404,435,504,717`); `corpus_auth.py` checks per-resource ownership, not a global admin role. Data-agent's cross-tenant admin gap does **not** recur here.
- **Per-user collection isolation** — enforced structurally via `current_user["db_path"]` on every document route; no route accepts a caller-supplied path. (The isolation is nonetheless defeatable via §1.1, but by collision, not by a missing check.)
- **Rate limiting** — present and configurable, including MCP-specific limits.

---

## 5. Sequencing constraints

1. `output: 'standalone'` must land **before** the frontend Dockerfile.
2. `/health` must land **before** the compose healthchecks.
3. `.gitattributes` must land **before** any shell entrypoint.
4. The §1.1 identity fix and the vector-store/`users.db` migration are **one unit** — the fix redefines the directory mapping the migration has to preserve.
5. The §3.1 transport change touches `client.ts`, `docs/page.tsx`, `next.config.ts`, the backend CORS block, and the frontend Dockerfile args — sequence it as one track, not spread across several.
