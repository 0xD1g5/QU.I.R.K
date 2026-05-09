---
phase: 58-dashboard-api-hardening
plan: "01"
subsystem: auth
tags: [fastapi, bearer-token, hmac, csrf, cors, middleware, security]

requires:
  - phase: 57-scanner-security-hardening
    provides: SecurityCfg dataclass shape extended in this plan

provides:
  - quirk/dashboard/api/middleware package with auth.py and csrf.py
  - require_auth FastAPI Depends enforcing QUIRK_API_TOKEN bearer token (hmac.compare_digest)
  - require_csrf FastAPI Depends enforcing X-Quirk-Request: 1 header on mutating requests
  - SecurityCfg.api_token and SecurityCfg.cors_origins fields in config.py
  - get_cors_origins() helper with QUIRK_CORS_ORIGINS env var override
  - config_template.yaml extended with api_token and cors_origins keys

affects:
  - 58-02 (CORS + route wiring — consumes require_auth, require_csrf, get_cors_origins)
  - 65-dashboard-initiated-scan (hard dependency: auth must exist before dashboard launches scans)

tech-stack:
  added: []
  patterns:
    - "Bearer token auth via FastAPI HTTPBearer + hmac.compare_digest (D-03)"
    - "Env-var-first config: QUIRK_API_TOKEN overrides security.api_token YAML"
    - "Custom-request-header CSRF pattern (X-Quirk-Request: 1) for mutating routes"
    - "QUIRK_CORS_ORIGINS env var overrides security.cors_origins YAML allowlist"

key-files:
  created:
    - quirk/dashboard/api/middleware/__init__.py
    - quirk/dashboard/api/middleware/auth.py
    - quirk/dashboard/api/middleware/csrf.py
  modified:
    - quirk/config.py
    - quirk/config_template.yaml

key-decisions:
  - "hmac.compare_digest used for all token comparisons — prevents timing-oracle brute-force (T-58-01-S)"
  - "Auth disabled (pass-through) when QUIRK_API_TOKEN is unset and security.api_token is empty — local-first tool design (D-02)"
  - "401 body is identical for missing vs. wrong token — no token-oracle leakage (T-58-01-I)"
  - "CSRF returns 403 (not 401) to distinguish from auth failure (D-07)"

patterns-established:
  - "Middleware pattern: FastAPI Depends() functions in quirk/dashboard/api/middleware/ package"
  - "Config pattern: env var first, YAML fallback, coded default last"

requirements-completed:
  - HARDEN-API-01
  - HARDEN-API-02

duration: 8min
completed: 2026-05-09
---

# Phase 58 Plan 01: Dashboard API Hardening — Auth Middleware Summary

**Bearer-token auth (hmac.compare_digest) and CSRF header check middleware for the FastAPI dashboard API, with configurable CORS allowlist and api_token fields in SecurityCfg**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-09T22:12:00Z
- **Completed:** 2026-05-09T22:20:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `quirk/dashboard/api/middleware/` package with `__init__.py`, `auth.py`, and `csrf.py`
- `require_auth` Depends: env-var-first token resolution (QUIRK_API_TOKEN), hmac.compare_digest comparison, 401 with exact body for missing/wrong token, pass-through when auth disabled
- `require_csrf` Depends: enforces `X-Quirk-Request: 1` on POST/PUT/DELETE/PATCH, returns 403 with exact `"Missing CSRF header: X-Quirk-Request"` body
- Extended `SecurityCfg` with `api_token: str = ""` and `cors_origins: list` (defaults to loopback), updated `config_from_dict` to parse both from YAML
- Added `get_cors_origins()` helper in `config.py` with `QUIRK_CORS_ORIGINS` env var override
- Extended `config_template.yaml` with `api_token` and `cors_origins` keys under `security:`

## Task Commits

1. **Task 1: Create middleware package, auth dependency, and extend config** — `1343df0` (feat)
2. **Task 2: Create CSRF dependency** — `c2a8f4e` (feat)

## Files Created/Modified

- `quirk/dashboard/api/middleware/__init__.py` — Package init with docstring
- `quirk/dashboard/api/middleware/auth.py` — `require_auth` Depends with hmac.compare_digest, env-var-first config
- `quirk/dashboard/api/middleware/csrf.py` — `require_csrf` Depends enforcing X-Quirk-Request header
- `quirk/config.py` — Added `os` import; `api_token` + `cors_origins` fields to `SecurityCfg`; `api_token` + `cors_origins` parsing in `config_from_dict`; `get_cors_origins()` helper function
- `quirk/config_template.yaml` — Added `api_token` and `cors_origins` entries under `security:` block

## Decisions Made

- `_get_configured_token()` is called per-request (not cached globally) to avoid startup-race injection concerns noted in the threat model
- `load_config()` in `get_cors_origins()` is wrapped in a broad `except Exception` so import failures at startup do not crash the app — falls back to loopback defaults
- `cors_origins` field uses `dataclasses.field(default_factory=...)` to avoid the mutable-default-argument issue

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundary surfaces introduced beyond what is documented in the plan's threat model (T-58-01-S through T-58-01-D). Mitigations for T-58-01-S (hmac.compare_digest) and T-58-01-I (uniform 401 body) are implemented as specified.

## Next Phase Readiness

- Plan 02 (CORS + route wiring) can now import `require_auth`, `require_csrf`, and `get_cors_origins` from the middleware package and `quirk.config`
- No blockers for Wave A parallel execution of Phases 57, 59, 60, 61, 62

## Self-Check: PASSED

- `quirk/dashboard/api/middleware/__init__.py` — FOUND
- `quirk/dashboard/api/middleware/auth.py` — FOUND
- `quirk/dashboard/api/middleware/csrf.py` — FOUND
- Commit 1343df0 — FOUND
- Commit c2a8f4e — FOUND

---
*Phase: 58-dashboard-api-hardening*
*Completed: 2026-05-09*
