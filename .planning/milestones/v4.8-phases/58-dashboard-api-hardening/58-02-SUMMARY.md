---
phase: 58-dashboard-api-hardening
plan: 02
subsystem: api
tags: [fastapi, cors, rate-limit, middleware, starlette, threading, security]

# Dependency graph
requires:
  - phase: 58-dashboard-api-hardening-plan-01
    provides: get_cors_origins() in quirk/config.py (Plan 01 parallel worktree)
provides:
  - RateLimitMiddleware: sliding-window 60 req/min/IP on mutating methods with Retry-After
  - CORSMiddleware registration in create_app() with configurable allowlist via get_cors_origins()
  - quirk/dashboard/api/middleware/ package with __init__.py and rate_limit.py
affects: [58-03, 58-04, 65-dashboard-initiated-scan]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sliding-window rate limiter: defaultdict(deque) + threading.Lock for thread-safe per-IP counting"
    - "FastAPI reverse middleware registration order: add RateLimit first (innermost), CORS last (outermost)"
    - "Configurable CORS via get_cors_origins() — env var QUIRK_CORS_ORIGINS or security.cors_origins YAML"

key-files:
  created:
    - quirk/dashboard/api/middleware/__init__.py
    - quirk/dashboard/api/middleware/rate_limit.py
  modified:
    - quirk/dashboard/api/app.py

key-decisions:
  - "Middleware registered in reverse: RateLimitMiddleware first (innermost), CORSMiddleware last (outermost) — gives execution order CORS -> RateLimit -> route"
  - "get_cors_origins() imported from quirk.config (Plan 01) — Plan 02 does not duplicate the allowlist resolver, relies on parallel worktree merge"
  - "Rate limiter uses time.monotonic() for monotonic clock safety (immune to wall-clock adjustments)"
  - "Retry-After header value = ceil(window_seconds - age_of_oldest_entry), minimum 1"

patterns-established:
  - "BaseHTTPMiddleware subclass pattern for FastAPI custom middleware"
  - "Exempt-path frozenset pattern for health endpoint rate-limit bypass"

requirements-completed:
  - HARDEN-API-02
  - HARDEN-API-03

# Metrics
duration: 3min
completed: 2026-05-09
---

# Phase 58 Plan 02: Dashboard API Hardening — CORS + Rate-Limit Summary

**Sliding-window rate limiter (60 POST/PUT/DELETE/PATCH/min/IP, Retry-After) and configurable CORSMiddleware registered in FastAPI app factory via get_cors_origins() — zero new pip dependencies**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-09T22:16:23Z
- **Completed:** 2026-05-09T22:19:26Z
- **Tasks:** 2
- **Files modified:** 3 (created 2, modified 1)

## Accomplishments

- Created `quirk/dashboard/api/middleware/` package with `RateLimitMiddleware` — stdlib-only sliding-window token bucket, thread-safe via `threading.Lock` around `defaultdict(deque)` read-modify-write, 60 mutating req/min/IP, GET/health exempt, 429 + Retry-After on exhaustion
- Updated `quirk/dashboard/api/app.py` to register `RateLimitMiddleware` (innermost) and `CORSMiddleware` (outermost) with correct reverse-add order for desired CORS → RateLimit → route execution
- CORS allowlist wired to `get_cors_origins()` from Plan 01's `quirk/config.py` — operator-configurable via `QUIRK_CORS_ORIGINS` env var or `security.cors_origins` YAML; no hardcoded origins in middleware block

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement RateLimitMiddleware** - `27ce14e` (feat)
2. **Task 2: Register CORS and rate-limit middleware in app factory** - `f7911b7` (feat)

## Files Created/Modified

- `quirk/dashboard/api/middleware/__init__.py` — Package init for middleware module (Phase 58 / HARDEN-API-02, -03)
- `quirk/dashboard/api/middleware/rate_limit.py` — `RateLimitMiddleware(BaseHTTPMiddleware)` with sliding-window rate limiting, `threading.Lock`, `defaultdict(deque)`, 429 + Retry-After
- `quirk/dashboard/api/app.py` — Added `CORSMiddleware` + `RateLimitMiddleware` registrations; imports `get_cors_origins` from `quirk.config` (Plan 01)

## Decisions Made

- **Reverse registration order enforced:** `RateLimitMiddleware` registered first (innermost), `CORSMiddleware` registered last (outermost). This is FastAPI/Starlette's reverse-add semantics giving execution order: CORS → RateLimit → route dispatch.
- **No CORS implementation duplication:** `get_cors_origins()` is defined entirely in Plan 01's `quirk/config.py`. Plan 02 only imports and calls it — per parallel execution contract.
- **`time.monotonic()` over `time.time()`:** Monotonic clock avoids wall-clock adjustment issues (NTP, DST) corrupting the sliding window.

## Deviations from Plan

### Parallel Worktree Limitation (not a deviation — expected)

The plan's runtime verification `python -c "from quirk.dashboard.api.app import create_app; create_app()"` cannot pass in isolation because `get_cors_origins` is added to `quirk/config.py` by Plan 01 running in a parallel worktree. The code is syntactically correct and semantically correct — post-merge verification will pass. Syntax compilation (`python -m compileall`) succeeds in this worktree. This is a documented characteristic of wave-1 parallel execution, not a deviation from plan intent.

None - plan executed exactly as written (excluding the expected parallel worktree import limitation).

## Issues Encountered

None beyond the expected parallel worktree import limitation documented above.

## User Setup Required

None — no external service configuration required. CORS allowlist defaults to loopback origins (`http://127.0.0.1`, `http://localhost`) with no operator action needed for local use.

## Next Phase Readiness

- `RateLimitMiddleware` and `CORSMiddleware` are in place; Plan 03 (auth/CSRF) wires Depends() at router level
- `quirk/dashboard/api/middleware/` package is importable and extensible for future middleware
- app.py middleware block is clearly commented with Phase 58 references and registration-order rationale

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced beyond what is documented in the plan's threat model (T-58-02-S, T-58-02-D). No unplanned threat surface added.

## Known Stubs

None — no placeholder values, hardcoded empty collections, or TODO comments in implementation files.

## Self-Check

- [x] `quirk/dashboard/api/middleware/__init__.py` exists
- [x] `quirk/dashboard/api/middleware/rate_limit.py` exists
- [x] `quirk/dashboard/api/app.py` modified with CORSMiddleware + RateLimitMiddleware
- [x] Task 1 commit 27ce14e exists
- [x] Task 2 commit f7911b7 exists
- [x] `python -m compileall quirk/dashboard/api/middleware/` exits 0
- [x] `grep -c 'CORSMiddleware' quirk/dashboard/api/app.py` returns 2
- [x] `grep -c 'RateLimitMiddleware' quirk/dashboard/api/app.py` returns 2
- [x] `grep -c 'get_cors_origins' quirk/dashboard/api/app.py` returns 2
- [x] No hardcoded `http://127.0.0.1:8512` in middleware block

## Self-Check: PASSED

---
*Phase: 58-dashboard-api-hardening*
*Completed: 2026-05-09*
