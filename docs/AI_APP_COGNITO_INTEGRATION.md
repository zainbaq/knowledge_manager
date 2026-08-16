# Promethean AI ↔ Knowledge Manager: Cognito-Native Integration Guide

**Audience:** a Claude Code session working in `the-jarvis-project-agent-server`
(the "ai app" / "Promethean AI" repo), implementing this change on that side.
**Written from:** `knowledge_manager`, after auditing both repos directly.
**Status:** Knowledge Manager's side is fully ready (see §2). Nothing here has
been implemented in the `ai` app repo — this is the plan to hand to that session.

---

## 0. The one-sentence version

Stop having Promethean AI's backend log into Knowledge Manager with a
username and password on the user's behalf. Instead, forward the same
Cognito access token the user already used to sign into Promethean AI —
Knowledge Manager verifies it directly and auto-provisions that person their
own KM identity, with no separate credential, no separate login screen, and
no shared/global connection object to leak across users.

---

## 1. Why this, and why now

### 1.1 The estate context

Promethean Labs runs a suite of apps (`ai`, `knowledge_manager`, `data-agent`,
`document-intelligence`, `data-probe`) that are consolidating onto one host
behind Traefik, with **one shared AWS Cognito user pool** and one App Client
per app. This is already true today, verified directly:

| App | Pool | App Client |
|---|---|---|
| Promethean AI | `us-east-2_CyRy6JBhm` | `76dr18kllrvs9rc0bujjc5o7hh` |
| Data Agent | `us-east-2_CyRy6JBhm` | `5k00q5jqknq59lqh29h0bdtvu8` |
| Knowledge Manager | `us-east-2_CyRy6JBhm` | `5noehk1hqq52ilj2lq0nr2u3d7` |

Because every app shares one pool, **the same person has the same Cognito
`sub` in every app** — signing into one app's Hosted UI silently signs them
into the others too (Cognito's own session, not a custom SSO layer). The
integration in this doc is what makes Knowledge Manager actually *recognize*
that shared identity when Promethean AI calls it, instead of asking the user
to prove who they are a second time with a separate password.

### 1.2 What's wrong with the current KM integration, concretely

Read directly from `the-jarvis-project-agent-server` this session:

- **`next/components/km/KMDrawer.tsx`** is a form asking for a **KM username
  and password**, entirely separate from the Cognito credentials the user
  already typed into the Hosted UI to get into the `ai` app at all.
- **`backend/tools/km_connector.py`**'s `KMServerClient.login()` calls
  `POST {KM_SERVER_URL}/api/v1/user/login` with that username/password, gets
  back a KM API key, which is then used as `X-API-Key` on every subsequent
  call.
- **`backend/services/km_connection_storage.py`** persists that encrypted API
  key to `backend/data/km_connections.json`. This store has **no user field
  at all** — `self._connections: Dict[str, KMConnection]`, keyed only by a
  random connection UUID.
- **`backend/routers/km_connections.py`**'s `list_km_connections` returns
  every connection in that file to **any authenticated `ai`-app user**, and
  `PUT /connections/{id}/selections` has no ownership check either.

  Concretely: if you connect your own KM account through this drawer, every
  other person who signs into the `ai` app can see your connection listed and
  select it for their own chats. This is a real, currently-live multi-tenant
  bug, not a hypothetical one — confirmed by reading the code, not assumed.
- **`backend/routers/session_km.py`** is a second, parallel implementation of
  the same idea, scoped to an in-memory browser session instead of the JSON
  file. It has the same fundamental issue (a credential decoupled from the
  signed-in Cognito identity), just with a different persistence lifetime.
- **`KM_SERVER_URL` is hardcoded** in `deploy/jarvis-backend.service`
  (`https://knowledge-manager.promethean-labs.co`) and defaults to
  `http://localhost:11000` in `backend/config.py` — neither points at the KM
  instance that actually exists today (published locally at `:8511`
  frontend / `:8010` backend; see §2.4).

The redesign in this document doesn't patch these — it removes the entire
credential-and-connection-storage subsystem, because once identity comes from
the same Cognito token everywhere, there is nothing left for it to store.

---

## 2. What's ready on the Knowledge Manager side (verified this session)

Everything below is already true in `knowledge_manager` as of this commit.
Nothing here is aspirational.

### 2.1 Cognito verification already accepts a *set* of trusted app clients

`api/cognito.py`'s `verify_cognito_token()` validates the JWT signature,
issuer, and expiry against the shared pool's JWKS, then separately checks
that the token was issued for a **trusted** app client:

```python
# config.py
COGNITO_TRUSTED_CLIENT_IDS = {COGNITO_CLIENT_ID} | set(
    _as_list(os.getenv("COGNITO_TRUSTED_CLIENT_IDS", ""))
)
```

KM's own client is always trusted. **Nothing else is, until you add it.**

### 2.2 The one env var change this integration needs on KM's side

Set on the Knowledge Manager backend (`.env` / `docker-compose.yml`):

```bash
COGNITO_TRUSTED_CLIENT_IDS=76dr18kllrvs9rc0bujjc5o7hh
```

That's Promethean AI's real App Client ID (table in §1.1). Multiple values
are comma-separated if more apps need this later. This is the **only**
KM-side configuration change required. Everything else in this section is
already deployed behavior, not something to build.

Restart is enough for this one (it's backend-only env, not a frontend build
arg) — but if you're touching the compose file anyway, `docker compose up -d
--build` is always safe.

### 2.3 Why an access token works, and what it does and doesn't carry

Both apps' frontends already forward the Cognito **access token** (not the ID
token) to their own backends today — confirmed by reading both:

- `knowledge_manager/next/src/lib/api/client.ts`: `session.tokens?.accessToken`
- `the-jarvis-project-agent-server/next/lib/auth/auth-store.ts`: same,
  `session.tokens?.accessToken`

This matters because access tokens and ID tokens carry the client-id claim
differently, and KM's verifier (and, it turns out, `ai`'s own verifier —
see §3.1) already branch on this correctly:

| Token type | Client-id claim | Typically carries email? |
|---|---|---|
| Access token | `client_id` | No, not by default |
| ID token | `aud` | Yes |

**Recommendation: forward the access token**, matching what both apps
already use internally. Consequence: KM auto-provisions the user with their
`sub` and `username`, but a blank `email`. This is already handled gracefully
— `get_or_create_cognito_user()` in `api/users.py` defaults `email` to `""`
and the account works normally; email is cosmetic here, not load-bearing.
(If you'd rather have email populated, forward the ID token instead — KM's
verifier accepts either. Just be consistent, and know that ID tokens are
larger and slightly more expensive to pass around on every request.)

### 2.4 The real, currently-working REST surface

Base URLs (KM's compose maps container-internal port 8000 → published
`:8010`, and container-internal 8501 → published `:8511`; see §2.6 for which
one to actually call):

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/api/v1/query/` | POST | Bearer or X-API-Key | Body: `{"query": str, "collection"?: str, "collections"?: [str]}`. Searches the caller's own private collections. |
| `/api/v1/list-indexes/` | GET | Bearer or X-API-Key | Caller's own collections + chunk/file counts. |
| `/api/v1/corpus/` | GET | Bearer or X-API-Key | Every corpus the caller can access: owned, public, or explicitly granted. |
| `/api/v1/corpus/{id}/query` | POST | Bearer or X-API-Key | Body: `{"query": str, "n_results"?: int}`. |
| `/api/v1/corpus/{id}/usage` | GET | Bearer or X-API-Key | Requires admin-tier permission on *that* corpus (owner by default). |
| `/api/v1/user/usage` | GET | Bearer or X-API-Key | Always the caller's own stats. |
| `/api/v1/mcp/` | POST | Bearer or X-API-Key | JSON-RPC 2.0 (`tools/list`, `tools/call`, `resources/list`, `resources/read`). |
| `/health` | GET | none | Plain liveness probe. |

Every path above also works without its trailing slash — KM registers both
forms explicitly (`api/v1/__init__.py`) specifically so a proxy or client
that normalizes trailing slashes never hits a redirect.

Send the token as a normal bearer header:
```
Authorization: Bearer <cognito-access-token>
```
`X-API-Key` still works unchanged for anything that still wants a static key
(scripts, non-Cognito integrations) — this change doesn't remove that path,
it adds the token path as a second, equally-valid way in.

### 2.5 What this means for isolation (the part that used to be broken)

Every route above scopes to `current_user["id"]` — the *internal* KM user
row, resolved from the Cognito `sub` via `get_or_create_cognito_user()`, which
auto-creates a KM account on first sight of a `sub` it hasn't seen before.
Per-user vector stores are keyed on that internal id
(`vector_store/vector_index.py`), not on username — deliberately, because an
earlier username-keyed scheme let two differently-formatted usernames
collide onto one shared directory (see `docs/phase0-audit.md` §1.1 if you
want the history). None of that is relevant to this integration except as
reassurance: **an `ai`-app user who starts querying KM through this
integration gets a private, correctly-isolated KM identity automatically**,
with the same guarantees a native KM user has.

Also gone since this session: KM no longer has a global admin role. Every
`ai`-app user who talks to KM through this integration is just a normal KM
user — nothing to configure, no allowlist of who's "allowed" to use KM
beyond having a valid, trusted-client Cognito token.

### 2.6 Which URL to actually call

`:8511` is the **Next.js frontend** (browser-facing, does its own `/api/*`
rewrite). `:8010` is the **FastAPI backend** directly. This integration is a
server-to-server call from the `ai` backend, not a browser — **call the
backend directly, not through the frontend's proxy port**:

| Environment | `KM_SERVER_URL` should be |
|---|---|
| Local dev (both apps run via `docker compose`, separately) | `http://localhost:8010` |
| Both apps in the *same* `docker compose` project on one shared network | `http://<km-backend-service-name>:8000` (container-internal port, no published-port translation) |
| Production, apps not yet colocated on the shared host | `https://knowledge.promethean-labs.co` (or whatever hostname is live — see the open naming question in `docs/consolidation-readiness-plan.md`) |
| Production, once both apps share a Docker network behind Traefik | Internal service DNS name, same shape as the second row — avoids a public round trip and a Cloudflare Tunnel dependency for a call that never needs to leave the host |

Because this is server-to-server, **CORS does not apply** — CORS is a
browser-enforced mechanism, and nothing here is a browser fetch. No CORS
changes are needed on KM's side for this integration specifically.

### 2.7 A known limitation to carry into the `ai`-side design: rate limiting

KM's rate limiter (`slowapi`, `api/rate_limiting.py`) keys on
`get_remote_address` — the caller's IP. Today that's each real user's own
browser IP. Once `ai`'s backend proxies every one of its users' KM calls,
**KM will see the `ai` backend's server IP for all of them**, meaning KM's
per-IP limits (60/min query, 10/min upload, etc.) become a *shared pool*
across every concurrent `ai`-app user, not a per-person allowance.

This is not a blocker — it's the same failure mode any reverse-proxied
service has, and KM's limits are generous relative to a chat app's actual
query volume — but it's worth knowing rather than discovering under load. If
it becomes a real problem, the fix belongs on KM's side (key the limiter on
the authenticated user id when a Cognito claim is present, falling back to IP
otherwise) and is a small, self-contained follow-up, not something this
integration needs to solve up front.

---

## 3. What needs to change in `the-jarvis-project-agent-server`

Everything in this section is **not yet done** — it's the plan for the fresh
session working in that repo.

### 3.1 Expose the raw token, not just the decoded claims

`backend/auth/dependencies.py`'s `get_current_user()` already extracts the
raw bearer token (`credentials.credentials`) and validates it, but only
stores the *decoded* `CognitoUser` on `request.state.user` — the raw token
string itself is discarded once validated. It needs to also be kept, so a
downstream KM call can reuse it:

```python
# backend/auth/dependencies.py, inside get_current_user(), after validate_token succeeds:
request.state.user = user
request.state.user_token = token   # <-- add this line
```

This is a one-line change. `backend/auth/cognito.py`'s
`CognitoTokenValidator.validate_token()` already does the *exact* same
access-token-vs-id-token client-id check KM's own verifier does (compare
`claims.get("client_id")` against the configured client for access tokens,
`claims.get("aud")` for ID tokens) — so the precedent for "how do we check
this token belongs to us" already exists in this codebase; no new pattern to
invent there.

### 3.2 Rewrite the KM connector to forward the token instead of logging in

`backend/tools/km_connector.py`'s `KMServerClient`:

- **Remove** `login()` entirely — there is no more KM username/password.
- **Change** the constructor/headers from `X-API-Key: <api_key>` to
  `Authorization: Bearer <token>`.
- Keep `query()`, `query_corpus()`, `list_indexes()`, `list_corpuses()` as-is
  — same endpoints, same request/response shapes, just a different auth
  header. See §2.4 for the exact endpoint list this client should keep
  targeting.

Construct one `KMServerClient` per request, from `request.state.user_token`
(§3.1) — not a cached/stored client, since the token is short-lived and
scoped to the current request's own authenticated user.

### 3.3 Delete the connection-storage subsystem, not just its bugs

Remove, rather than patch:

- `backend/routers/km_connections.py` (global JSON-file-backed connections)
- `backend/services/km_connection_storage.py` (the storage class itself,
  including its Fernet-encrypted-API-key handling — nothing to encrypt
  anymore, there's no long-lived secret being stored)
- `backend/routers/session_km.py` (the session-scoped duplicate)
- `backend/data/km_connections.json` and the `.km_encryption_key` file next
  to it, once nothing reads them
- `KM_CONNECTIONS_FILE` and `KM_ENCRYPTION_KEY` from `backend/config.py`'s
  `Settings`

There is no replacement data model needed for "connections" — every
`ai`-app user simply *is* a KM user via their forwarded token. If the `ai`
app wants to remember which KM collections/corpora a user prefers to search
by default, that's a much smaller, ordinary user-preference (store a list of
collection/corpus names against the `ai` app's own user record, or even just
client-side local storage) — not a credential-bearing "connection" object.

### 3.4 Rewire the chat path

`backend/routers/agents.py`'s `chat()` and `chat_stream()` currently do:

```python
if hasattr(request.state, 'session') and hasattr(request.app.state, 'session_manager'):
    session_adapter = SessionKMConnectionAdapter(...)
    agent_manager.set_km_connector(session_adapter, request.app.state.settings.KM_SERVER_URL)
elif hasattr(request.app.state, 'km_connection_storage') and not agent_manager.km_connector_tool:
    agent_manager.set_km_connector(request.app.state.km_connection_storage, ...)
```

This whole branch — "which stored connection should we use" — goes away.
Replace it with: build a `KMServerClient(KM_SERVER_URL, request.state.user_token)`
(§3.1, §3.2) for the current request and pass that to whatever in
`agent_manager`/the KM tool actually issues the search call. There is no
longer a "which connection" decision to make — there is exactly one KM
identity per request, the caller's own.

The existing `enable_km_search: bool` and `km_connection_ids: [...]` fields on
`ChatRequest` should collapse: keep `enable_km_search` as the on/off toggle,
drop `km_connection_ids` (there are no more connection objects to select
between). If you want to let a user restrict a query to specific collections
or corpora, that's a `collection`/`collections`/`corpus_id` parameter passed
straight through to KM's own query endpoints (§2.4), not a connection
picker.

### 3.5 Fix configuration

`backend/config.py`:
```python
KM_SERVER_URL: str = "http://localhost:8010"  # was "http://localhost:11000" - never matched anything real
```
Set the real value per environment per the table in §2.6. Delete
`KM_CONNECTIONS_FILE` and `KM_ENCRYPTION_KEY` (§3.3).

`deploy/jarvis-backend.service`: delete the hardcoded
`Environment="KM_SERVER_URL=https://knowledge-manager.promethean-labs.co"`
line entirely — let it come from `backend/.env` like every other setting the
unit file already loads via `EnvironmentFile=`. A value baked into the unit
file silently overrides `.env` and is exactly the kind of thing that causes
"I changed the config and nothing happened" confusion.

### 3.6 Frontend: replace the credential form with a picker

`next/components/km/KMDrawer.tsx`'s `AddConnectionForm` (username/password
fields) goes away completely. There is nothing to "add" or "connect" — every
signed-in `ai`-app user already has implicit KM access. Replace the drawer's
content with:

- A fetch of the user's own KM collections and corpuses (`GET
  /api/v1/list-indexes/` and `GET /api/v1/corpus/` from the `ai` **backend**,
  which forwards the request server-side using the pattern in §3.2 — don't
  call KM directly from the browser, since the browser doesn't have a KM
  bearer token distinct from its `ai`-app one, and there's no reason to give
  it one).
- A simple multi-select over that list, feeding straight into the
  `collection`/`collections`/`corpus_id` query parameters (§3.4) — no
  connection object, no ID to manage, no delete/sync/test buttons (there's
  nothing to sync or test independently anymore; §2.4's endpoints are always
  live for whoever is signed in).

`next/lib/hooks/use-km-connections.ts` and `next/lib/store/km-store.ts`
shrink to match — replace "connections" state with "my collections" /
"my corpuses" state, fetched directly, no create/delete/sync mutations.

---

## 4. Testing checklist

Do these against a real, running KM instance (`docker compose up -d --build`
in `knowledge_manager`, with `COGNITO_TRUSTED_CLIENT_IDS` set per §2.2) and a
real signed-in `ai`-app session — not mocks, per the lesson from the
data-agent integration pass: static analysis and unit tests did not catch the
real bugs there; standing up the actual stack did.

1. **Sign into the `ai` app**, confirm `request.state.user_token` is
   populated on a protected route (log it during development, remove before
   shipping).
2. **First-ever KM call for a brand-new Cognito user** — confirm KM
   auto-provisions them (check `users.db` inside the KM container gains a row
   with the right `cognito_sub`, and a `u/{id}` directory appears under
   `VECTOR_DB_PATH`).
3. **Two different `ai`-app users** hitting KM in the same test run — confirm
   their KM collections/corpora are isolated from each other, i.e. the bug in
   §1.2 is actually gone, not just moved.
4. **An untrusted client is still rejected** — temporarily unset
   `COGNITO_TRUSTED_CLIENT_IDS` on KM (or use a token from a client that was
   never added) and confirm KM returns 401, not a silent pass-through. This
   is the negative test that proves the allowlist is doing something, not
   just that the happy path works.
5. **A public corpus query, a private corpus you don't own (expect 403), and
   your own private collection query** — exercises the real RBAC surface,
   not just auth.
6. **Token expiry mid-session** — confirm the `ai` backend surfaces a clean
   401/re-auth rather than a confusing 500 when a stale token gets forwarded.
7. **Restart the `ai` backend and confirm it boots without
   `KM_CONNECTIONS_FILE`/`KM_ENCRYPTION_KEY`** set at all, once §3.3 and §3.5
   are done — proves nothing still implicitly depends on the deleted files.

---

## 5. Rollback / compatibility notes

- KM's `X-API-Key` auth path is completely unchanged by any of this — nothing
  else that uses it (scripts, other integrations, KM's own frontend) is
  affected.
- `COGNITO_TRUSTED_CLIENT_IDS` is additive and defaults to "just KM's own
  client," so KM's behavior for every existing caller is identical until this
  var is explicitly set.
- If the `ai`-side rollout needs to be reverted, removing
  `76dr18kllrvs9rc0bujjc5o7hh` from KM's `COGNITO_TRUSTED_CLIENT_IDS` (or
  unsetting it) immediately closes the trust relationship again — one env var
  change, no code revert needed on KM's side.
- There is deliberately no migration step for `backend/data/km_connections.json`
  — those were username/password-derived API keys for whichever KM accounts
  people manually typed into the old form, decoupled from any `ai`-app
  identity. There's nothing meaningful to carry forward; users get a fresh,
  correctly-isolated KM identity the first time they use the new integration.
