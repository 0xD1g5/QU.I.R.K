# Phase 58: Dashboard API Hardening - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 58 closes audit blockers 7–10 (`api-cli-core/CR-01, CR-02, CR-03, CR-09`) so
the dashboard API is safe to expose beyond the loopback interface. The phase delivers:

- **CR-03 / HARDEN-API-01:** Single-user bearer token auth on all mutating routes +
  CSRF header requirement on browser-initiated requests.
- **CR-03 / HARDEN-API-02:** CORS allowlist middleware (default: `127.0.0.1` and
  `localhost` only); non-allowlisted origin preflight → 403 with no body.
- **CR-03 / HARDEN-API-03:** In-process per-IP token-bucket rate limiting (60
  POST/PUT/DELETE/PATCH requests/min/IP); 429 + `Retry-After` on exhaustion.
- **CR-01 / HARDEN-API-04:** `quirk init --output <path>` path-traversal guard
  (resolves path, checks it descends from CWD or explicit allow-root, rejects `..`,
  absolute paths outside allowlist, and symlinks pointing outside allowlist).
- **CR-02 / HARDEN-API-05:** `routes/pdf.py` port-range clamp (1024–65535) + redirect
  interception so Playwright cannot be redirected to non-loopback hosts.
- **CR-09 / HARDEN-API-06:** `@file` target loading in `quirk/util/targets.py` gains
  a path-traversal allowlist check, 1 MB size cap, and 10,000-line cap with distinct
  error messages on each violation.

**In scope:** the six requirements above and the associated tests, fuzz corpus, and
AUDIT-TASKS.md row closures (flip CR-01, CR-02, CR-03, CR-09 to `[x] closed`).

**Out of scope:** Scanner security hardening (Phase 57), credential leakage (Phase 59),
score arithmetic (Phase 60), CBOM coverage (Phase 61), React hook cancellation (Phase 62).
No new SQLite columns, no new chaos lab profiles, no new pip dependencies.

</domain>

<decisions>
## Implementation Decisions

### Token Configuration (Area 1)

- **D-01:** Bearer token is read from `QUIRK_API_TOKEN` environment variable (priority)
  OR `security.api_token` YAML field in `config.yaml` (fallback). Extends the existing
  `security:` block introduced in Phase 57 (D-04):
  ```yaml
  security:
    allow_internal_targets: false
    allow_cleartext_broker_probe: false
    allow_insecure_jwks: false
    api_token: ""          # new — leave blank to disable auth
  ```
  Corresponding env var: `QUIRK_API_TOKEN`. Env var wins when both are set.
- **D-02:** When neither `QUIRK_API_TOKEN` nor `security.api_token` is set (empty
  string / absent), **auth is disabled** — the dashboard behaves as before. This
  preserves backward compatibility for existing single-user local installs that never
  exposed the port beyond loopback. Auth becomes opt-in by setting the token.
- **D-03:** Token comparison MUST use `hmac.compare_digest(token_a, token_b)` to
  prevent timing-oracle attacks — not `==` or `!=`. A timing attack matters here
  because a brute-force attacker on a LAN could observe response-time variance.
- **D-04:** Auth failure returns `401 Unauthorized` with body
  `{"detail": "Authentication required"}`. No `WWW-Authenticate` challenge header
  (this is not a browser-login flow). Business logic is never reached on 401.

### Auth + Rate-Limit Scope (Area 2)

- **D-05:** Auth (when enabled) covers **all** `/api/*` routes except
  `GET /api/health`. Rationale: scan results, trend data, and QRAMM sessions all
  contain potentially sensitive cryptographic inventory — read routes are not exempt
  from auth even though they are "informational" reads.
  - Exempt from **both** auth and rate limiting: `GET /api/health` only.
  - Auth required, **not** rate-limited: all GET routes (reads with no side effects).
  - Auth required **and** rate-limited (60/min/IP): POST, PUT, DELETE, PATCH routes.
  Current POST/PUT/DELETE routes in the codebase:
  - `POST /api/export/pdf`
  - `POST /api/qramm/sessions`
  - `POST /api/qramm/sessions/{id}/answers`
  - `POST /api/qramm/sessions/{id}/score`
  - `DELETE /api/qramm/sessions/{id}`
  - `POST /api/qramm/profiles`
  - `POST /api/qramm/assessment/draft`
- **D-06:** Route-introspection enforcement test: a pytest test enumerates
  `app.routes` via `app.routes` iteration, filters to routes whose `methods`
  include POST, PUT, DELETE, or PATCH (excluding `/api/health`), and asserts each
  is covered by the auth dependency. The test fails if a developer adds a new
  mutating route and omits the `Depends(require_auth)` injection. This is the
  SC-1 gate.

### CSRF Mechanism (Area 3)

- **D-07:** Use the **custom-request-header** CSRF pattern: all POST/PUT/DELETE/PATCH
  routes require the header `X-Quirk-Request: 1`. The React frontend sets this header
  on every API call via a shared `fetchApi()` utility.
  - Missing CSRF header → `403 Forbidden` with body
    `{"detail": "Missing CSRF header: X-Quirk-Request"}`. 403 (not 401) distinguishes
    auth failure from CSRF failure.
  - Rationale: The browser's same-origin policy prevents cross-origin JS from setting
    custom headers without a CORS preflight — which the CORS allowlist (HARDEN-API-02)
    already rejects for non-allowlisted origins. The combination of CORS lockdown +
    custom header covers the full CSRF threat model for a React SPA calling JSON APIs.
    Double-submit cookies would require stateful server-side token management with no
    additional security benefit in this local-first threat model.
- **D-08:** The React `fetchApi()` utility (to be created or extended in
  `src/dashboard/src/lib/api.ts` or equivalent) MUST set `X-Quirk-Request: 1` and
  `Content-Type: application/json` on every non-GET call. This is the single
  enforcement point — individual components should not set the header inline.

### Rate Limiting Implementation (Area 4)

- **D-09:** Implement an in-process token bucket in
  `quirk/dashboard/api/middleware/rate_limit.py` — **zero new pip dependencies**.
  Data structure: `collections.defaultdict(deque)` mapping
  `client_host: str → deque[float]` of per-request timestamps (epoch seconds).
  Sliding-window algorithm: on each mutating request, trim entries older than 60 s,
  count remaining → if count ≥ 60, return 429. Otherwise append `time.monotonic()`.
  - `Retry-After` value: `ceil(60 - (now - oldest_timestamp_in_window))` seconds.
  - Thread safety: add a `threading.Lock` around deque read-modify-write since uvicorn
    may run with multiple workers.
  - This is adequate for local single-user operation. If the tool evolves to
    multi-instance or multi-worker, replace with Redis-backed `limits` library then.
- **D-10:** Rate limiter is a FastAPI `Middleware` (subclassing `BaseHTTPMiddleware`)
  rather than a `Depends()`-injected dependency, so it runs before route matching and
  can be applied uniformly to POST/PUT/DELETE/PATCH without annotating each route.
  The middleware inspects `request.method` and exempts GET/HEAD/OPTIONS.

### PDF SSRF Clamp (Area 5)

- **D-11:** In `routes/pdf.py`, validate `QUIRK_SERVE_PORT` before use:
  `1024 <= port <= 65535` — return 500 with
  `{"detail": "QUIRK_SERVE_PORT is out of allowed range (1024–65535)."}` on violation.
  The `http://127.0.0.1:{port}` URL is already loopback-bound; this adds the range check.
- **D-12:** Playwright redirect guard: intercept all navigation via
  `page.route("**/*", handler)` where `handler` aborts requests whose URL resolves to
  a non-loopback host (`127.0.0.1` and `::1` are the only allowed hosts). This prevents
  a server-side redirect from pivoting Playwright to an arbitrary local service.

### `@file` Target Guards (Area 6)

- **D-13:** In `parse_target_tokens()` (`quirk/util/targets.py`), before calling
  `load_targets_file()`, validate each `@file` token:
  1. **Path allowlist:** `os.path.realpath(path)` must start with `os.path.realpath(os.getcwd())`.
     Additionally reject any path under `/etc`, `/proc`, `/sys`, `/dev` (absolute
     prefix check after `realpath()`).
  2. **Size cap:** `os.path.getsize(path) > 1_048_576` → reject with
     `"target_file_too_large"`.
  3. **Line cap:** stream-count lines via `sum(1 for _ in open(path)) > 10_000` →
     reject with `"target_file_too_many_lines"`.
  Each check raises a `TargetFileError(path, reason_code)` with one of:
  `path_traversal`, `path_not_allowed_prefix`, `target_file_too_large`,
  `target_file_too_many_lines`.
- **D-14:** `TargetFileError` is raised inside `parse_target_tokens()`, propagated up
  to the caller (`run_scan.py` or the dashboard scan route), logged at ERROR level, and
  surfaced to the user as a clear exit message. No silent swallowing. Consistent with
  Phase 57's `invalid_input` reason-code pattern (D-06/D-07/D-08 in 57-CONTEXT.md).

### ROADMAP / AUDIT-TASKS Housekeeping

- **D-15:** At phase completion, flip `AUDIT-TASKS.md` rows for
  `api-cli-core/CR-01`, `api-cli-core/CR-02`, `api-cli-core/CR-03`, and
  `api-cli-core/CR-09` to `[x] closed`. No other audit rows are touched by this phase.

### Claude's Discretion

- Exact FastAPI `Depends()` wiring for auth: whether `require_auth` is a plain function
  dependency or a `Security()` dependency with a custom `HTTPBearer` scheme.
- Whether to use FastAPI's `CORSMiddleware` (built-in, zero deps) or a custom middleware
  for CORS — `CORSMiddleware` is the obvious choice.
- Specific regex or string-comparison logic for the CORS allowlist (host + port combos).
- Internal structure of `quirk/dashboard/api/middleware/` package (new `__init__.py`,
  `auth.py`, `rate_limit.py`, `csrf.py` — or combined into fewer files).
- Fuzz test implementation details: whether the 50+ traversal patterns live as a pytest
  parametrize fixture, a data file, or inline list.
- Whether `TargetFileError` extends `ValueError` or is a custom exception class.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit drivers (locked findings)

- `.planning/audit-2026-05-08/api-cli-core/REVIEW.md` §CR-01, CR-02, CR-03, CR-09 —
  verbatim audit findings with proof-of-concept attack chains. Source of truth for what
  each requirement must mitigate. **Read this first.**
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — audit ledger; rows for CR-01, CR-02,
  CR-03, CR-09 must flip to `[x] closed` when this phase completes.

### Roadmap + requirements

- `.planning/ROADMAP.md` §Phase 58 — phase scope, success criteria, wave membership.
- `.planning/REQUIREMENTS.md` §HARDEN-API-01..HARDEN-API-06 — requirement language,
  precise acceptance criteria that tests must satisfy.

### Prior phase context

- `.planning/phases/57-scanner-security-hardening/57-CONTEXT.md` — Phase 57 decisions
  for the shared `quirk/util/` helper pattern (D-01..D-10), YAML `security:` config
  block (D-04), `invalid_input` reason-code pattern (D-06..D-08), and `CryptoEndpoint`
  rejection row shape. Phase 58 extends these patterns, does not replace them.

### Affected source files

- `quirk/dashboard/api/app.py` — FastAPI app factory; add middleware registrations here
  (CORS, rate limit, CSRF). Middleware order matters: CORS → auth → CSRF → rate limit.
- `quirk/dashboard/api/routes/pdf.py` — CR-02 fix (port range clamp + redirect guard).
- `quirk/cli/init_cmd.py` — CR-01 fix (path-traversal guard on `output_path`).
- `quirk/util/targets.py` — CR-09 fix (`@file` path allowlist + size/line caps in
  `parse_target_tokens()`).
- `quirk/config_template.yaml` — add `security.api_token: ""` field.
- `quirk/config.py` — load `security.api_token` alongside the existing `security.*`
  fields from Phase 57.

### Existing patterns to extend

- `quirk/util/targets.py::apply_targets_file_override` — YAML+CLI override pattern
  that the Phase 57 `security:` block mirrored. The `api_token` field follows the same
  shape.
- `.planning/phases/57-scanner-security-hardening/57-CONTEXT.md` D-06/D-07/D-08 —
  `invalid_input` category + reason-code + redacted-preview rejection row pattern.
  `TargetFileError` (D-13/D-14 above) must produce rows in this same shape.

### Codebase maps

- `.planning/codebase/STACK.md` — FastAPI version, middleware available, uvicorn mode.
- `.planning/codebase/ARCHITECTURE.md` — dashboard API structure, route organization.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `quirk/dashboard/api/app.py::create_app()` — the factory function where all
  middleware must be registered. Currently has zero middleware. Add
  `app.add_middleware(CORSMiddleware, ...)`, `app.add_middleware(RateLimitMiddleware)`,
  and the CSRF check as a global dependency via `app.include_router(..., dependencies=[...])`.
- `quirk/util/targets.py::parse_target_tokens()` — the single function that handles
  `@file` token expansion. The CR-09 guard belongs here, before `load_targets_file()` is
  called.
- `quirk/cli/init_cmd.py::run_init()` — the 45-line function where `output_path` is
  validated. The CR-01 guard is a 10-line addition before `os.makedirs()`.
- `quirk/dashboard/api/routes/pdf.py::export_pdf()` — the 55-line function where the
  port is read from env. The CR-02 guard is an additional range check on line ~47.
- Phase 57 helpers in `quirk/util/url_allowlist.py` and `quirk/util/subprocess_input.py`
  — the `ValidationResult(ok, reason, redacted_preview)` shape that `TargetFileError`
  should mirror.

### Established Patterns

- All shared security helpers live in `quirk/util/`. New middleware modules live in
  `quirk/dashboard/api/middleware/` (new package, consistent with route package layout).
- Config loading is YAML-first with env var override (`QUIRK_SERVE_PORT`, `QUIRK_DB_PATH`
  env vars already exist). `QUIRK_API_TOKEN` follows the same convention.
- `hmac.compare_digest` is stdlib — no new import beyond standard library.
- `collections.defaultdict(deque)` + `time.monotonic()` for the rate limiter is stdlib.
- FastAPI's built-in `CORSMiddleware` (`fastapi.middleware.cors.CORSMiddleware`) requires
  no new dependency — it ships with FastAPI.

### Integration Points

- **Middleware registration order** in `create_app()`: CORS must come before auth so
  OPTIONS preflight responses return correct headers without hitting auth. Auth before
  CSRF. CSRF before rate limit. Rate limit before route dispatch.
- **React API client** (`src/dashboard/src/lib/api.ts` or similar): needs a shared
  `fetchApi()` wrapper that injects `Authorization: Bearer {token}` and
  `X-Quirk-Request: 1` on every non-GET call. Currently each component calls `fetch()`
  directly — this wrapper is new.
- **Route introspection test**: must run after all routers are registered so `app.routes`
  is fully populated. A `conftest.py` fixture that creates the app once and the test
  imports it.

</code_context>

<specifics>
## Specific Ideas

- The AUDIT-TASKS.md ledger (`.planning/audit-2026-05-08/AUDIT-TASKS.md`) is the
  authoritative checklist. The planner should include a task to flip the four CR rows
  at the end of the phase, not as an afterthought.
- The route-introspection test (D-06) is a regression gate that will catch future
  developers adding unprotected routes. It should live in `tests/test_api_auth.py`
  alongside the other auth tests — not in a separate "meta" test file.
- The fuzz corpus for the `quirk init --output` path-traversal test (SC-4, 50+ patterns)
  should be a `pytest.mark.parametrize` list in `tests/test_init_cmd.py`. The Phase 57
  equivalent in `tests/util/test_subprocess_input.py` is the closest existing model.
- For the PDF redirect guard (D-12), Playwright's `page.route()` API intercepts at the
  browser level — this is the correct mechanism because it fires before DNS resolution,
  not after. Using `page.on("response", ...)` would be too late (the request already
  went out).

</specifics>

<deferred>
## Deferred Ideas

- A shared `Depends(require_auth)` decorator that also logs the authenticated request
  (audit trail for multi-user scenarios). Deferred — single-user local tool, no audit
  log requirement in this milestone.
- Rate limiter backed by Redis for multi-instance/multi-worker scenarios. Explicitly
  out of scope; in-process bucket is adequate for local-first operation (D-09).
- A `quirk token generate` CLI command to create and store a new API token automatically.
  Useful UX improvement but out of scope for this hardening phase.
- CSRF via `SameSite=Strict` cookies if auth ever moves from bearer tokens to session
  cookies. Not applicable to the current bearer-token design.

</deferred>

---

*Phase: 58-dashboard-api-hardening*
*Context gathered: 2026-05-09*
