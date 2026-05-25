# Phase 102: Dashboard Auth UX + Score Tax - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes the single-tenant dashboard shareable across a team via a rotatable API token
and a real login form, and pays down the v5.2 score-tax tech debt so the CLI executive markdown
sources its score numbers from the same shared content model as HTML/PDF/DOCX.

Four deliverables:
- **AUTH-01** — a `quirk token` CLI (generate / rotate / show) using stdlib `secrets`.
- **AUTH-02** — the dashboard accepts `X-API-Key` (in addition to the existing `Authorization: Bearer`),
  timing-safe, with a CI route-coverage test that fails if any data-returning route ships unprotected.
- **AUTH-03** — a React login form + clear authenticated/unauthenticated state (no more silent 401).
- **TRANS-04** — CLI executive markdown reads score (total, band, subscores) from the shared
  `exec_content` rather than re-deriving locally; a cross-surface parity test asserts the number
  is identical across CLI/HTML/PDF/DOCX.

In scope: AUTH-01, AUTH-02, AUTH-03, TRANS-04.
Out of scope: multi-tenant auth / user accounts / RBAC (single-tenant shared token only),
OAuth/SSO, per-route scopes.
</domain>

<decisions>
## Implementation Decisions

### Token CLI (AUTH-01)
- Command surface: `quirk token generate` / `quirk token rotate` / `quirk token show` subcommands
- Token generation: stdlib `secrets.token_urlsafe(32)`
- Persisted to the YAML config `security.api_token` field — the same field `require_auth` already reads (quirk/dashboard/api/middleware/auth.py)
- Rotation: `rotate` overwrites the stored token in place — the old token stops working immediately (success criterion 1); no grace window

### API-Key Auth (AUTH-02)
- Extend the existing `require_auth` dependency to accept `X-API-Key: <token>` OR `Authorization: Bearer <token>` — both compared timing-safe via `hmac.compare_digest` (reuse the existing pattern at auth.py)
- CI route-coverage test enumerates all data-returning dashboard routes and asserts each is protected by `require_auth` — this is the route-coverage CI test Phase 101 referenced; failing the build if a new route ships unprotected
- Precedence: check `X-API-Key` first, fall back to bearer; either valid → pass
- Preserve the existing auth-disabled passthrough (empty configured token = auth disabled, dev convenience, D-02 from Phase 58)

### Login UX (AUTH-03)
- Unauthenticated browser sees a React login form (token input), not a silent 401
- Client-side token stored in `localStorage`, injected as the `X-API-Key` header on all API calls via the existing fetch/client layer (src/dashboard/src/lib + hooks)
- Auth-state detection: a probe request (health or first data call) — 401 → show login, 200 → show dashboard
- Failed login shows an inline "Invalid token" error; a logout control clears localStorage and returns to the login form

### Score-Tax Refactor (TRANS-04)
- The CLI executive markdown sources total/band/subscores from the shared `exec_content` (quirk/reports/executive.py + content_model.py) instead of re-deriving them locally
- Cross-surface parity test asserts the score number (total, band, subscores) is numerically identical across CLI / HTML / PDF / DOCX for the same scan
- This is a PURE sourcing refactor — the emitted numbers must not change versus the current HTML/PDF (already correct); HTML/PDF are the reference
- Closes the v5.2 backlog tech-debt item ("CLI score should source exec_content")

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/dashboard/api/middleware/auth.py::require_auth` — existing FastAPI Depends() with HTTPBearer + `hmac.compare_digest`; token from `QUIRK_API_TOKEN` env → `security.api_token` YAML. Extend this for X-API-Key (AUTH-02), do not replace.
- `quirk/config.py::load_config` + `cfg.security.api_token` — the persisted token field for AUTH-01.
- `quirk/reports/executive.py` + `quirk/reports/content_model.py` (ExecContent) — the shared content model the CLI must source from (TRANS-04); html_renderer.py / docx_renderer.py already consume it.
- `src/dashboard/src/` — React + Vite + shadcn/ui dashboard with `context/`, `hooks/`, `lib/`, `pages/` dirs — the login form + auth context live here.
- Phase 101 added an `integration_deliveries`-style route protection mindset; the route-coverage CI test concept originates with this phase's AUTH-02.

### Established Patterns
- Timing-safe token comparison via `hmac.compare_digest` (auth.py) — reuse for X-API-Key.
- Dashboard frontend requires an explicit `npm run build` in `src/dashboard/` before .tsx changes are visible (FastAPI serves pre-built statics) — plans must include the build step.
- Recharts static-children requirement and shadcn/ui conventions already in the dashboard.
- CLI subcommand registration pattern in quirk/cli/ (see existing *_cmd.py modules + run_scan.py interception).

### Integration Points
- `quirk/dashboard/api/routes/*.py` — every data-returning route must carry `require_auth`; the CI test scans these.
- The dashboard fetch/client layer (src/dashboard/src/lib) — inject `X-API-Key` from localStorage here.
- `quirk/reports/writer.py` / the CLI executive markdown path — repoint score sourcing to exec_content.

</code_context>

<specifics>
## Specific Ideas

- The route-coverage CI test is the concrete artifact Phase 101's plan referenced as "established here"; build it so adding a new unprotected data route fails CI.
- TRANS-04 is the v5.2 tech-debt item explicitly carried into v5.3 (folded here per v5.3-D-03). Verify against the v5.2 reporting content model — do not introduce a new score computation.
- AUTH-03 login form must follow the project UI brand / shadcn conventions; a UI-SPEC will be generated before planning (this IS a genuine frontend phase, unlike Phase 101).

</specifics>

<deferred>
## Deferred Ideas

- Multi-tenant auth, user accounts, RBAC, per-route scopes — single-tenant shared token only this milestone.
- OAuth / SSO integration.
- Token expiry / TTL (rotation is manual; no auto-expiry in v5.3).

</deferred>
