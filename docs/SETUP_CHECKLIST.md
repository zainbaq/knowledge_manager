# Knowledge Manager — Setup Checklist

Everything needed to get this into proper working condition, in order.
Verified against the running stack on 2026-08-16.

---

## Status of what you already have

| | |
|---|---|
| ✅ `OPENAI_API_KEY` | Set in `.env`, real key, **verified working** (live upload → embed → semantic query round trip) |
| ✅ `COGNITO_REGION` | `us-east-2` — correct |
| ✅ Test suite | 72 passed, 1 skipped, 0 failed, 0 errors |
| ✅ Docker stack | Both images build; backend reports healthy; proxy, auth and routing verified |
| ❌ **Cognito login** | **Not configured — this is the only thing blocking a working app.** Pool ID, client ID and domain are all unset, so `COGNITO_ENABLED` is `False` and every browser login is rejected |
| ⚠️ `DEBUG=true` | Fine locally. **Must be `false` in production** — it enables a permissive localhost CORS regex |
| ✅ Admin role | **Removed entirely.** Corpus visibility is now controlled directly by the owner's own `is_public` flag (no separate approval step), and usage stats are self-service (`GET /api/v1/user/usage`) or scoped to a corpus's own owner/collaborators (`GET /api/v1/corpus/{id}/usage`). There is nothing to configure here. |

---

## Step 1 — Create a Cognito App Client for this app (AWS Console)

Your estate already shares **one** user pool, and each app has its **own** App Client.
Confirmed from the sibling apps' configs:

| App | Pool | App Client |
|---|---|---|
| Promethean AI | `us-east-2_CyRy6JBhm` | `76dr18kllrvs9rc0bujjc5o7hh` |
| Data Agent | `us-east-2_CyRy6JBhm` | `5k00q5jqknq59lqh29h0bdtvu8` |
| **Knowledge Manager** | `us-east-2_CyRy6JBhm` | `5noehk1hqq52ilj2lq0nr2u3d7` ✅ created |

> ⚠️ **The client exists but has no callback or sign-out URLs registered yet.**
> Probed against live Cognito on 2026-08-16: every candidate callback URL returns
> `error=redirect_mismatch`. Sign-in cannot work until Step 1b is done.

In **Cognito → User pools → `us-east-2_CyRy6JBhm` → App integration → Create app client**:

- **Type:** Public client (SPA). **Do not generate a client secret** — the browser
  flow cannot hold one, and Amplify will fail if the client requires it.
- **Name:** e.g. `knowledge-manager-web`
- **Authentication flows:** Authorization code grant
- **OpenID Connect scopes:** `openid`, `email`, `profile` — must match exactly;
  these are what [`next/src/lib/auth/config.ts`](../next/src/lib/auth/config.ts) requests.
- **Allowed callback URLs** (add both):
  - `http://localhost:8511/auth/callback`
  - `https://knowledge.promethean-labs.co/auth/callback`
- **Allowed sign-out URLs** (add both):
  - `http://localhost:8511`
  - `https://knowledge.promethean-labs.co`

> The callback URLs must match byte-for-byte what the app sends, including scheme,
> port and the absence of a trailing slash. A mismatch surfaces as a Cognito error
> page, not an app error, which makes it easy to misdiagnose.

### Step 1b — Sign-out URLs specifically

Amplify's `signOut()` sends the user to the Hosted UI's `/logout` endpoint with
`logout_uri` set to **exactly** the `NEXT_PUBLIC_REDIRECT_SIGN_OUT` value, verbatim.
Cognito compares it against **Allowed sign-out URLs** — a separate list from the
callback URLs, which is easy to miss.

Register exactly these two, **origin only — no path, no trailing slash**:

```
http://localhost:8511
https://knowledge.promethean-labs.co
```

Common ways to get this wrong:

| Wrong | Why |
|---|---|
| `http://localhost:8511/` | Trailing slash — a different string to Cognito |
| `http://localhost:8511/auth/callback` | That is the *callback* URL, not the sign-out URL |
| `http://localhost:3000` | The old port, before this app moved to 8511 |
| Registering only the prod URL | Local sign-out then fails silently |

**A bad sign-out URL cannot be detected by probing** — Cognito only validates
`logout_uri` when there is an active session, so an unregistered value looks fine
until a real user actually signs out and lands on an error page instead of the app.
Get it right up front; there is no cheap check for it afterwards.

### Verifying the callback URLs (this one *can* be checked)

After registering, run this — it asks Cognito directly and needs no browser:

```bash
D=https://us-east-2cyry6jbhm.auth.us-east-2.amazoncognito.com; C=5noehk1hqq52ilj2lq0nr2u3d7; for u in "http%3A%2F%2Flocalhost%3A8511%2Fauth%2Fcallback" "https%3A%2F%2Fknowledge.promethean-labs.co%2Fauth%2Fcallback"; do r=$(curl -s -o /dev/null -w "%{redirect_url}" "$D/oauth2/authorize?client_id=$C&response_type=code&scope=openid+email+profile&redirect_uri=$u"); case "$r" in *redirect_mismatch*) echo "NOT registered: $u";; *"/login"*) echo "OK: $u";; *) echo "? $u -> $r";; esac; done
```

`OK` means Cognito accepted the client + callback pair. `NOT registered` means the
URL is missing or does not match byte-for-byte.

## Step 2 — Fill in `.env`

Add these to the existing `.env` (keep the `OPENAI_API_KEY` line you already have):

```bash
COGNITO_USER_POOL_ID=us-east-2_CyRy6JBhm
COGNITO_REGION=us-east-2
COGNITO_CLIENT_ID=5noehk1hqq52ilj2lq0nr2u3d7
COGNITO_DOMAIN=us-east-2cyry6jbhm.auth.us-east-2.amazoncognito.com
DEBUG=true
LOG_LEVEL=INFO
```

This is **already written to `.env`**.

`COGNITO_DOMAIN` is the shared Hosted UI domain — the same value both sibling apps use.

### Do NOT put these in `.env` for Docker

`VECTOR_DB_PATH` and `USER_DB_PATH` are set by `docker-compose.yml` to the mounted
volumes. Setting them in `.env` overrides that and writes your data inside the
container, where it is destroyed on the next `docker compose down`.

### Everything else is optional

`CORS_ORIGINS` (leave empty — the frontend proxies same-origin),
`COGNITO_TRUSTED_CLIENT_IDS` (leave empty until another app is ready to
forward its users' Cognito tokens here instead of a separate KM login — see
[`AI_APP_COGNITO_INTEGRATION.md`](AI_APP_COGNITO_INTEGRATION.md)),
`MAX_FILE_SIZE_MB` (defaults to 100 in compose), the five `*_RATE_LIMIT` values,
`EMBEDDING_CONCURRENCY`, `MAX_EMBEDDING_RETRIES`, `API_KEY_TTL_DAYS`,
`PASSWORD_MIN_LENGTH`, `REQUIRE_COMPLEX_PASSWORD`, `OPENAI_EMBEDDING_MODEL`,
`MIME_VALIDATION_BYTES`, `LOG_FILE`.

## Step 3 — Rebuild, don't just restart

**This is the step that is easy to get wrong.** The `COGNITO_*` values reach the
frontend as `NEXT_PUBLIC_*` **build args**, and Next inlines them into the JS
bundle at build time. Restarting the container does nothing — the old values stay
baked in and login fails with no useful error.

```bash
docker compose up -d --build
```

The same applies to `BACKEND_URL`: `next.config.ts`'s `rewrites()` is evaluated
during `next build`, so it is a build-time value too.

## Step 4 — Verify login end to end

1. Open http://localhost:8511
2. Sign in — you should be redirected to the Cognito Hosted UI and back to
   `/auth/callback` without an error page.
3. Confirm the API accepts your session: the Indexes page should load an empty
   list rather than a 401.

Quick backend-only check at any time:

```bash
curl -s http://localhost:8511/health
```

---

## Before deploying to the consolidated host

- [ ] **Set `DEBUG=false`.** It currently enables a blanket
      `localhost` CORS regex that, combined with `allow_credentials`, lets any
      page on any localhost port make credentialed calls.
- [ ] **Set the production redirect URLs** so the bundle is built with them:
      ```bash
      NEXT_PUBLIC_REDIRECT_SIGN_IN=https://knowledge.promethean-labs.co/auth/callback
      NEXT_PUBLIC_REDIRECT_SIGN_OUT=https://knowledge.promethean-labs.co
      ```
- [ ] **Remove the published host ports** from `docker-compose.yml`. Traefik
      reaches the containers over the Docker network; publishing `8010`/`8511`
      on the consolidated host is unnecessary exposure.
- [ ] **Migrate existing production data** with
      [`scripts/migrate_user_storage.py`](../scripts/migrate_user_storage.py).
      Per-user vector stores are now keyed on `users.id` rather than the
      username. Copy `users.db` and `VECTOR_DB_PATH` as **one consistent
      snapshot**, run the script against the copy (dry run first), then cut over.
      It will refuse any directory shared by two users — those are the accounts
      that were silently sharing documents, and they need a manual decision.
- [ ] **Promethean AI integration is being redesigned, not just re-pointed.**
      See [`docs/AI_APP_COGNITO_INTEGRATION.md`](AI_APP_COGNITO_INTEGRATION.md) —
      the plan replaces the current username/password → API key flow with
      Cognito ID-token passthrough, so `ai`-app users get their own KM identity
      automatically. That guide supersedes the URL-only fix this bullet used to
      describe.
- [ ] **Decide the PyMuPDF (AGPL-3.0) question** — shared with
      `document-intelligence` and `promethean-ai`. One decision, three repos.

## Housekeeping

- [ ] `.claude/` is not in `.gitignore` and contains a stale agent worktree
      (`git worktree list` shows it). Add it to `.gitignore` and run
      `git worktree remove .claude/worktrees/<name>` when finished with it.
- [ ] Changes are staged but not committed.
