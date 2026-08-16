# Knowledge Manager: methodology from the data-agent pass, and how it applies here

**Purpose of this document:** a briefing for the next activity — a thorough code review and phased update plan for `knowledge_manager`, in the same spirit as the work just completed on `promethean-data-agent`. Part 0 lays out the big-picture Promethean Labs vision this work actually serves, so it doesn't read as an isolated app update. Part 1 distills what actually worked (and why) from the data-agent session as a reusable methodology. Part 2 grounds that methodology in what's actually true about `knowledge_manager` today (verified by a light direct look at this repo, not assumed from the standing docs). Part 3 is the proposed phased plan. Nothing in this document has been executed yet — it's the planning artifact the next session should start from.

---

## Part 0 — The big picture: why this work exists

This isn't an isolated "clean up knowledge_manager" task. It's one piece of a decided, cross-app consolidation plan for the whole Promethean Labs estate. Worth carrying forward explicitly, because it changes what "done" looks like for individual app work — a change that's locally correct but works against the shared direction isn't actually done.

### The estate today, and where it's going

Right now there are five apps (`ai`, `knowledge_manager`, `data-agent`, `document-intelligence`, `data-probe`) plus a landing page and a separate `tools` box, spread across roughly five always-on EC2 instances at ~$200/month. The decided target state: **one right-sized EC2 instance** running everything as containers under **Docker Compose**, behind a **Traefik** reverse proxy, fronted by a **Cloudflare Tunnel** (no public IP, no open inbound ports, free TLS). Two shared infrastructure containers — **one Postgres, one Redis** — replace each app's individual databases (Postgres: one instance, separate database per app; Redis: one instance, partitioned by logical DB number per app/purpose). The marketing site moves to Cloudflare Pages. Target cost is ~$80–90/month, down from ~$200.

This is judged safe specifically because of two properties confirmed true across the whole estate: no app depends on AWS SDKs/IAM/RDS/S3/SES/SQS — Cognito is the *only* AWS touchpoint, used purely as an OIDC token verifier over public HTTPS, so nothing technically ties any app to EC2 or to AWS at all beyond that; and no app executes untrusted code locally — every "code interpreter"-style feature runs in a remote sandbox (OpenAI's or E2B's), not on the host. Co-locating everything on one box doesn't introduce a new class of risk.

### The unified auth model — the part every app-level update touches

**Decision:** redirect-through-Cognito SSO, not a shared-session or token-relay mechanism. Each app keeps its own Amplify + Cognito Hosted UI integration; there's no shared cookie domain. The "single sign-on" feel comes from Cognito's own Hosted UI remembering the user's session — sign in once, and a redirect to any other app's login completes silently. This was chosen deliberately over a shared-session approach: much less engineering, and it doesn't fight Amplify's own default (origin-scoped) token storage.

**Decided: every app shares one Cognito User Pool**, region `us-east-2` (fixed everywhere this has been checked), with each app registered as its own **App Client** against that one pool — not one pool per app. This is what makes "sign in once, everywhere else is instant" actually true: a shared pool means the same `cognito_sub` identity is valid everywhere, not just conceptually similar per-app identities that happen to use the same provider. The standard shape (confirmed already built, in varying completeness, across the apps that have real Cognito integration): Amplify v6 on the frontend with a `/auth/callback` page and an `AuthProvider`/`useAuth()` hook; JWKS-based JWT validation on the backend with a `get_current_user` dependency; a local `User` row auto-provisioned on first login, keyed on `cognito_sub`, no separate registration step.

`data-agent`'s own pass (the work Part 1 recaps) confirmed its piece of this concretely: it now points at pool `us-east-2_CyRy6JBhm` with its own dedicated App Client, and a real login was verified end-to-end. Whether `ai` and `knowledge_manager` point at that *same* pool is still the one open confirmation step (see "Still open" below) — each could independently have its own pool that merely follows the same config shape, which isn't provable from code alone.

### Routing and the app suite

One subdomain per app (`ai.`, `data.`, `knowledge.`, `docs.` under `promethean-labs.co`), not path-based routing under a single host — that was considered and deliberately rejected, since it would force `basePath` rework in every app and each app already assumes it owns its root. The unified feel instead comes from a shared portal (`www`) that acts as an app launcher, with apps grouped by type in its navigation.

**The `data.` consolidation** — `data-agent`, `knowledge_manager`, `document-intelligence`, and `data-probe` — is the group this app belongs to. Confirmed by direct survey: these four are **functionally distinct, not redundant**, despite surface-level "these all touch data" similarity:
- `data-agent` — chat-with-your-database: connect a SQL database, ask natural-language questions, get SQL + visualizations back.
- `knowledge_manager` — semantic document search: upload files, get them chunked/embedded into per-user ChromaDB collections, query via semantic search across one or many collections. The "SharePoint with a vector DB" one. Possible display-name change to "Knowledge" (hostname decision still open).
- `document-intelligence` — schema-driven field extraction: upload a form/invoice/contract, define target fields, get structured output with confidence scores. No search, no vector store — a fundamentally different operation from `knowledge_manager` despite both touching "documents."
- `data-probe` — data-quality auditing: upload a CSV or connect a read-only DB, get a scored quality report with a remediation runbook. Job-queue-based, not a persistent chat/search surface.

**`knowledge_manager` already has a live piece of this suite working today**: the `ai` app's backend calls it directly over HTTP as an MCP server (`KM_SERVER_URL`) for RAG. That's a real, running cross-app integration already — not a future aspiration — and it's the reason Part 2 of this document flags "don't break the `ai` ↔ `knowledge_manager` integration" as a real constraint on this work, not a hypothetical one.

Eventually merging these four into one `data.` app's UI/backend is explicitly **out of scope for this pass** — it's a separate, larger product-architecture exercise (four different data models, four different interaction patterns) that hasn't been designed yet. What *is* decided: all four need to land on the same Cognito-based auth **before** any merge work starts, because merging four auth systems into one app at the same time as merging four product surfaces would compound two hard problems into one. That sequencing is exactly why this app-by-app auth/infra alignment pass (data-agent, now knowledge_manager) has to happen first and separately.

### The repeatable pattern this work is building toward

Part of the point of doing this consolidation carefully, app by app, is that it produces a repeatable template for "add a new app as a feature": a `Dockerfile` + `/health` endpoint + the same ~30-line Cognito JWKS verifier + non-root/volume-scoped state, a Compose service block with Traefik labels for routing, one DNS record, one Cognito App Client, one portal tile. Every app that goes through this pass (data-agent done, knowledge_manager next) makes that template more concrete and more proven, not just more apps updated.

### Still open — not this document's job to resolve, but relevant context

- **Confirming, via the AWS Cognito console, whether `ai` and `knowledge_manager` already share the same pool** `data-agent` now points at (`us-east-2_CyRy6JBhm`) — a fact-finding step, not a design decision; the target (one shared pool) is already decided.
- **`knowledge_manager`'s rename** to "Knowledge" — display-name change is agreed; whether the hostname (`knowledge-manager.promethean-labs.co`) changes too, or the rename is UI-only within the eventual `data.` suite, is still open.
- **CORS/production hostnames** — every backend already reads allowed origins from a `CORS_ORIGINS` env var (consistent pattern, confirmed across the estate); no app has its production hostname committed anywhere yet — that gets set at deploy time, not baked into any repo.

---

## Part 1 — What actually happened to promethean-data-agent, as a method

The data-agent work had five phases. None of them were "just start editing files." The value was disproportionately in phases 0, 3, and 4 — the parts that aren't code-writing at all.

### Phase 0 — Evaluate before committing to an approach

Before any plan existed, the actual question on the table was "how should I even approach this?" — not "port these features." Two parallel research agents diffed the reference deployment (ticketwala) against the skeleton (data-agent) file-by-file, producing concrete `file:line` citations of what was actually different, what was already equivalent despite looking like a gap, and where domain-specific naming was shallow (renameable) vs. structural (real rearchitecture). That research directly overturned some of the user's own priors — e.g., "does the skeleton have rate limiting" turned out to be yes, already equivalent, contradicting the initial framing.

Only after that research did an evaluation happen: three concrete options (full reimplementation, fork-and-generalize, targeted cherry-pick) were laid out with real tradeoffs, and a recommendation was given — not just "here are your options."

**Why this mattered:** it turned a vague "these two repos have diverged, deal with it" into a scoped, evidence-backed decision, and caught wrong assumptions before they became wasted implementation effort.

### Phase 1 — A structured, approved plan, not ad-hoc execution

Once the approach was chosen, the actual implementation went through plan mode: a Plan agent produced a concrete, file-level, dependency-aware plan; it was then revised against explicit user constraints (don't touch the reference repo, remove all client branding, cover both frontend and backend, minimize round-trips); and it was reviewed and approved before any code was touched.

Critically, the plan didn't only cover "port the features." It also folded in the *separate*, already-known requirements from the standing consolidation/migration plan for this specific app (Redis DB partitioning, SSRF hardening, upload caps, dependency pinning) as its own explicit track — because doing that work later, disconnected from this pass, would have meant touching the same files twice.

The plan was organized as a small number of large, mostly-independent **tracks**, each with an explicit dependency edge only where two tracks would otherwise fight over the same file (e.g., two different tracks both needing to touch a shared enum or a shared `requirements.txt`).

### Phase 2 — Parallel execution via subagents, actively coordinated

Big chunks of the plan were dispatched to background subagents rather than done serially. Each agent was briefed like a self-contained colleague, not given a one-line instruction: what the goal was, why, the hard rule (never write to the reference repo), the exact files and behaviors involved, and an explicit instruction to test what they built and report honestly what they couldn't verify rather than claiming success.

Three coordination patterns mattered in practice:
- **File-contention sequencing.** When two tracks both needed to touch the same file (a shared schema/enum file, a shared `requirements.txt`), one was held back until the other landed, rather than letting both edit concurrently and risk corruption.
- **Absorbing new gaps without losing scope.** Several subagents surfaced gaps the original plan hadn't anticipated — a frontend piece built against a backend route that turned out not to exist yet. Each time, that was captured as new, explicitly tracked work (not silently left undone, and not dumped onto an unrelated agent already mid-task).
- **Recovering from failure without redoing completed work.** One subagent failed partway through (hit a usage limit). Before relaunching, the actual repo state was inspected — it turned out the agent had completed nearly everything before failing, so the retry was a small, targeted "finish and verify" pass, not a full redo.

### Phase 3 — Real, live verification — this is the phase that actually found bugs

This is the highest-value phase and the one it would be easiest to skip. "The code compiles" and "the unit tests pass" were both true and both insufficient. Standing up the real Docker stack and actually clicking through it surfaced five real bugs that no amount of static review would have caught:

- CRLF line endings on a shell script silently breaking the container's entrypoint entirely (`exec: no such file or directory`)
- A pinned dependency version missing a method the code called (`redis` client `.aclose()`)
- A migration race condition — two services both ran `alembic upgrade head` on boot, unordered, and the second one crashed
- Docker Compose never actually wiring required env vars through to the containers that needed them (twice — once for the backend, and again for the frontend's build-time `NEXT_PUBLIC_*` args, which is a different failure mode than a normal runtime env var miss since Next.js inlines those at build time)
- A live performance bug: token validation was making a real network round-trip to the identity provider's userinfo endpoint on *every single request* instead of caching it

Beyond bug-hunting, verification meant actually exercising the real integrations: logging in through the real Cognito Hosted UI end-to-end (with a debugging detour when a browser-automation click didn't register — resolved by hitting the OAuth URL directly to isolate "is the app's config correct" from "is the test tooling behaving"), making real calls to the real LLM provider with real API credentials via a small script that exercised the exact same code path the API uses (not mocks), and spinning up a real instance of an external dependency (a temporary SQL Server container) to prove a driver fix actually worked end-to-end rather than just "the package installs."

When something looked broken, the instinct was to find the actual root cause, not the first plausible story — "the UI looks stale" turned out to be a stale Docker build-cache volume, not a code bug.

### Phase 4 — Surfacing real architectural questions instead of deciding them unilaterally

Partway through, the user raised a legitimate product question: a client-engagement's "one admin manages everyone's config" model doesn't fit a general multi-tenant product. Rather than just picking an answer, the actual current behavior was verified first (confirmed a real cross-tenant gap: any user with a global admin role could edit *any other user's* connection configuration, not just their own — a genuine finding, not a hypothetical), the real fork in approaches was laid out with tradeoffs (per-user self-service vs. a team/org model), and the decision was left to the user via an explicit question — because it was a product decision, not an implementation detail.

### Phase 5 — Wrap-up hygiene

Outstanding items were tracked explicitly rather than left implicit (a driver dependency gap, an unverified version pin) so they could be picked up later without re-deriving what was already known. When the user later said "proceed with X" on one of those deferred items, it was treated as its own complete cycle — test interactively first, then commit the change, then rebuild and re-verify live, not just "add a line and assume it works." The final commit reviewed the staged diff for secrets before committing, and the commit message was organized by area rather than being a flat list of files touched.

---

## Part 2 — What's actually true about knowledge_manager today (verified, not assumed)

The standing infra guide describes `knowledge_manager` as "most Cognito-ready of all five apps" and flags only a small env-var documentation gap. Before trusting that the same way some of data-agent's priors turned out to need correcting, a light direct look at this repo today confirms some of it and complicates the rest:

**Confirmed similar to data-agent's starting position:**
- There's a legacy Streamlit UI (`ui/streamlit_app.py`, `streamlit>=1.36.0` still in `requirements.txt`) sitting alongside a modern `next/` frontend — the same split data-agent had, and the same removal decision already applies per the consolidation plan.
- `Procfile` / `Procfile.dev` at the repo root confirm the consolidation plan's note that the Heroku artifacts here are leftovers (the app actually runs on EC2).
- `docs/COGNITO_AUTH.md` is a real, current, substantive document describing an actual implemented Amplify + Hosted UI + Authorization Code flow — this part of the "most Cognito-ready" claim looks credible on its face.

**Not what data-agent had — genuinely different starting position:**
- **No containerization exists at all.** No `Dockerfile`, no `docker-compose.yml` anywhere in the repo. Data-agent's problem was "the Docker setup exists but has silent gaps"; this app's problem is "the Docker setup doesn't exist yet." This is real, from-scratch infra authorship, not wiring.
- **There's no reference fork to diff against.** Data-agent had ticketwala's more mature deployment to compare line-by-line. There is no equivalent for this app. Phase 0 here can't be "diff two repos" — it has to be a direct audit of this codebase against (a) the proven unified-auth contract already working in the other Cognito-ready apps, (b) the consolidation plan's specific checklist for this app, and (c) general code-health signals, the same categories the two-repo diff would have surfaced, just derived by reading one codebase carefully instead of comparing two.
- **`docs/unified-user-base-implementation-plan.md` is stale.** It predates the now-decided shared `us-east-2` pool (it references `us-east-1` and a generic, not-yet-decided pool setup). It shouldn't be treated as current guidance without reconciling it against the actual decision — worth either updating or retiring in favor of a doc that reflects the real, decided architecture.
- **This app has a live external consumer.** The `ai` app's backend calls this one directly over HTTP as an MCP server (`KM_SERVER_URL`). Data-agent had no equivalent — nothing else in the estate calls it. Any change here to auth, request/response shapes, or API surface has a blast radius into `ai` that needs to be verified as part of this work, not just this app in isolation.
- **The consolidation plan's specific asks here are different in kind from data-agent's.** Data-agent's asks were mostly "finish wiring what's already built" (env vars, Redis partitioning). This app's asks include real code/infra work: author the Dockerfile (backend + frontend, "moderate effort" per the infra guide, not "confirm it works"), add the `libmagic1` system dependency, and — a genuinely trickier one — the vector store (`VECTOR_DB_PATH`, ChromaDB) and the user database (`USER_DB_PATH`, SQLite `users.db`) must be migrated together, atomically, because usernames in one are directory names in the other; copying them out of sync silently corrupts per-user data ownership.
- **PyMuPDF's AGPL license** is flagged for this app in the consolidation plan, and it's a cross-app concern — the same library shows up in `document-intelligence` and `promethean-ai` too. Worth resolving as one decision across all three rather than three separate ad-hoc calls.
- **Minor hygiene finding:** `backend.log` appears to be a committed file, not gitignored. Not urgent, but worth cleaning up while in the area — the same instinct that caught the CRLF entrypoint bug in data-agent (small, easy-to-miss things that are cheap to fix once seen).

**Worth specifically auditing for, based on what data-agent taught:**
- The cross-tenant ownership gap found in data-agent (a global admin-role check with no per-resource ownership check) is exactly the kind of bug that can recur across apps sharing similar heritage or patterns. This app's per-user ChromaDB collections and RBAC (per the infra guide: corpus RBAC, subscriptions, usage tracking) are worth an explicit pass checking that every route actually verifies the requesting user owns the resource being accessed — not assumed correct because the feature exists.
- The same "verify the env-var wiring actually reaches the container, not just that the code reads `os.environ` correctly" lesson from data-agent's docker-compose gaps applies directly once a Dockerfile/compose setup is authored here — build it with that specific failure mode in mind from the start rather than discovering it during Phase 3.

---

## Part 3 — Proposed phased plan for knowledge_manager

Mapping the five phases onto what's actually different here:

### Phase 0 — Direct audit (not a diff)
A dedicated research pass over this codebase's actual state against three things: the unified-auth contract already proven working elsewhere, the consolidation plan's specific checklist for this app (above), and general hygiene (test coverage, dependency pinning, dead/vestigial code, the committed log file). Produce the same kind of concrete, cited findings the two-repo diff produced for data-agent — just derived from one codebase instead of two. Explicitly re-verify the "most Cognito-ready" claim against actual env-var wiring rather than trusting the docs.

### Phase 1 — Plan mode
A structured, file-level, dependency-aware plan, reviewed and approved before execution. Fold the consolidation-plan alignment work in as its own track from the start (mirroring data-agent's Track J), not as an afterthought.

### Phase 2 — Parallel subagent execution
Likely large, mostly-independent tracks: Dockerfile authorship (backend + frontend, genuinely new work here); the Cognito env-var/docs pass (verify first, don't assume the gap is as small as documented); Streamlit removal (direct reuse of the exact playbook from data-agent — orphan-check the compose config, grep for leftover references, update docs); the `libmagic1` + PyMuPDF licensing review; a per-route ownership/tenant-isolation audit; and the atomic vector-store + user-db migration handling. Sequence anything that touches shared files the same way — hold back rather than risk concurrent-edit conflicts.

### Phase 3 — Real, live verification
Once a Docker stack exists (it doesn't yet, so this phase depends on Phase 2's Dockerfile track landing first), stand it up for real: real Cognito login end-to-end, a real document upload → chunk → embed → semantic-search round trip (this app's equivalent of data-agent's real-OpenAI-query test — exercise the actual embedding/query code path, not a mock), and specifically confirm the live `ai` → `knowledge_manager` integration still works after any auth or API changes, since that's a real consumer this app has that data-agent didn't.

### Phase 4 — Surface real decisions, don't assume them
If the audit surfaces a genuine product/architecture fork (analogous to data-agent's self-service-vs-team-model question) — for instance, anything touching how per-user collections and RBAC should work in a general multi-tenant deployment vs. however they were originally designed — verify the current behavior first, lay out the real tradeoff, and ask rather than deciding unilaterally.

### Phase 5 — Wrap-up
Track anything deliberately deferred. Commit with a reviewed diff and an organized message. Push (accounting for whatever auth mechanism is actually available in that session — data-agent's push was blocked by a passphrase-protected SSH key with no TTY to prompt it, worth checking upfront this time rather than discovering it at the end).

---

## What this document is not

This is a plan for how to plan and execute the work, grounded in a light direct look at the repo — not the Phase 0 audit itself. The actual deep code review (the equivalent of the two-repo diff that grounded data-agent's plan) hasn't happened yet. That's the next concrete step.
