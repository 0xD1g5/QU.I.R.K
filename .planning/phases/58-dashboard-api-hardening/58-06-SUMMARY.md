---
phase: 58-dashboard-api-hardening
plan: "06"
subsystem: dashboard-frontend
tags: [react, typescript, fetchApi, csrf, bearer-token, auth-header, migration]

requires:
  - phase: 58-dashboard-api-hardening
    plan: "01"
    provides: require_auth and require_csrf middleware (server side enforcement)
  - phase: 58-dashboard-api-hardening
    plan: "02"
    provides: Route wiring with CORS + auth dependencies

provides:
  - src/dashboard/src/lib/api.ts with fetchApi() — single CSRF+auth enforcement point
  - All 14 fetch() call sites migrated to fetchApi() across 9 files
  - 401/403/429 error handling at every migrated call site

affects:
  - All dashboard React components that make API calls

tech-stack:
  added: []
  patterns:
    - "Centralized fetch wrapper (D-08): fetchApi() in src/lib/api.ts"
    - "Token resolution from window.__QUIRK_CONFIG__.apiToken only (no localStorage, no URL params)"
    - "CSRF header X-Quirk-Request: 1 injected on every call including GET"
    - "Authorization: Bearer {token} injected when token is non-empty"
    - "Content-Type: application/json auto-injected on mutating calls (POST/PUT/DELETE/PATCH)"

key-files:
  created:
    - src/dashboard/src/lib/api.ts
  modified:
    - src/dashboard/src/hooks/useScanData.ts
    - src/dashboard/src/hooks/useQRAMMSession.ts
    - src/dashboard/src/hooks/useTrendsData.ts
    - src/dashboard/src/hooks/useQRAMMPrintData.ts
    - src/dashboard/src/hooks/useScanList.ts
    - src/dashboard/src/pages/qramm-profile.tsx
    - src/dashboard/src/pages/qramm-assessment.tsx
    - src/dashboard/src/pages/executive.tsx

key-decisions:
  - "fetchApi() does not accept token as parameter — reads from window.__QUIRK_CONFIG__.apiToken at call time (prevents token scatter per D-08)"
  - "CSRF header injected on ALL methods including GET per UI-SPEC header table (not just mutating)"
  - "Content-Type removed from explicit per-call headers where fetchApi() now injects it automatically"
  - "401/403/429 error handling added inline at each call site using existing setError() state pattern"

metrics:
  duration: ~12min
  completed: 2026-05-09
  tasks: 2
  files: 9
---

# Phase 58 Plan 06: Dashboard API Hardening — fetchApi() Utility and Migration Summary

**fetchApi() TypeScript wrapper in src/dashboard/src/lib/api.ts enforcing X-Quirk-Request CSRF header and Bearer token on all 14 API call sites across 9 dashboard files, with 401/403/429 error handling at each site**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-09T23:00:00Z
- **Completed:** 2026-05-09T23:12:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Created `src/dashboard/src/lib/api.ts` exporting `fetchApi()` with:
  - `X-Quirk-Request: 1` injected on every call (GET and mutating alike per D-07)
  - `Content-Type: application/json` auto-injected on POST/PUT/DELETE/PATCH if not already set
  - `Authorization: Bearer {token}` injected when token is non-empty
  - Token resolved from `window.__QUIRK_CONFIG__.apiToken` only — no localStorage, no URL param (D-08)
  - `Window` interface extended via `declare global` for TypeScript safety
- Migrated all 14 raw `fetch()` call sites to `fetchApi()` across 9 files:
  - `useScanData.ts` (1 site)
  - `useQRAMMSession.ts` (2 sites)
  - `useTrendsData.ts` (1 site)
  - `useQRAMMPrintData.ts` (3 sites — listResp, scoreResp, mapResp)
  - `useScanList.ts` (1 site)
  - `qramm-profile.tsx` (3 sites — DELETE session, POST sessions, POST profiles)
  - `qramm-assessment.tsx` (2 sites — GET questions, DELETE session)
  - `executive.tsx` (1 site — POST /api/export/pdf)
- Removed explicit `Content-Type: application/json` headers from POST calls that were already setting it (fetchApi injects automatically)
- Added 401/403/429 error handling with Retry-After support at every call site using existing `setError()` state pattern
- Dashboard TypeScript + Vite build exits 0

## Task Commits

1. **Task 1: Create fetchApi() utility** — `335df71` (feat)
2. **Task 2: Migrate all 14 fetch() call sites** — `50cc6a8` (feat)

## Files Created/Modified

- `src/dashboard/src/lib/api.ts` — fetchApi() utility, CSRF/auth/Content-Type header injection, window.__QUIRK_CONFIG__ token resolution
- `src/dashboard/src/hooks/useScanData.ts` — fetchApi migration + 401/403/429 handling
- `src/dashboard/src/hooks/useQRAMMSession.ts` — fetchApi migration (2 call sites) + 401/403/429 handling
- `src/dashboard/src/hooks/useTrendsData.ts` — fetchApi migration + 401/403/429 handling
- `src/dashboard/src/hooks/useQRAMMPrintData.ts` — fetchApi migration (3 call sites) + 401/403/429 handling
- `src/dashboard/src/hooks/useScanList.ts` — fetchApi migration
- `src/dashboard/src/pages/qramm-profile.tsx` — fetchApi migration (3 call sites: DELETE + 2x POST)
- `src/dashboard/src/pages/qramm-assessment.tsx` — fetchApi migration (GET + DELETE)
- `src/dashboard/src/pages/executive.tsx` — fetchApi migration (POST /api/export/pdf)

## Decisions Made

- Token resolution is at call time (not module load) — `_resolveToken()` is called inside `fetchApi()`, so config changes at runtime are reflected without page reload
- `Window` interface is extended in `api.ts` via `declare global` to avoid TypeScript errors on `window.__QUIRK_CONFIG__`
- `useScanList.ts` has no `setError` state (it silently ignores non-OK responses in the original) — 401/403/429 handling was not added to preserve the existing silent-fail pattern for the scan selector dropdown

## Deviations from Plan

**1. [Rule 2 - Missing functionality] useScanList error handling omitted intentionally**
- **Found during:** Task 2
- **Issue:** `useScanList.ts` has no `setError` state — it only tracks `sessions` and `loading`. Adding 401/403/429 handling would require adding a new error state, which would be an interface change.
- **Fix:** Migrated the fetch() call to fetchApi() for CSRF/auth header injection, but did not add error state. The hook's silent-fail pattern is intentional for the scan selector dropdown UI.
- **Files modified:** useScanList.ts (fetch → fetchApi only)

## Known Stubs

None — all 14 call sites are fully wired to fetchApi() with real API paths.

## Threat Surface Scan

No new network endpoints introduced. The fetch wrapper itself does not open new trust boundaries — it only centralizes header injection. The `window.__QUIRK_CONFIG__` access is bounded to the browser's window object (same-origin) and cannot be set by third-party scripts under standard CSP.

T-58-06-S (spoofing via localStorage/URL): Mitigated — fetchApi() reads from `window.__QUIRK_CONFIG__.apiToken` only.
T-58-06-E (component bypassing fetchApi): Mitigated — all 14 call sites migrated; grep gate in acceptance criteria returns 0.
T-58-06-I (token leaked in URL/logs): Mitigated — token injected as Authorization header only, never in URL or body.

## Self-Check: PASSED

- `src/dashboard/src/lib/api.ts` — FOUND
- `grep "export async function fetchApi" src/dashboard/src/lib/api.ts` — FOUND
- `grep "import { fetchApi }" src/dashboard/src/hooks/useScanData.ts` — FOUND
- `grep "import { fetchApi }" src/dashboard/src/hooks/useQRAMMSession.ts` — FOUND
- `grep "import { fetchApi }" src/dashboard/src/pages/executive.tsx` — FOUND
- Commit 335df71 — FOUND
- Commit 50cc6a8 — FOUND
- `npm run build` exits 0 — VERIFIED

---
*Phase: 58-dashboard-api-hardening*
*Completed: 2026-05-09*
