---
phase: 102-dashboard-auth-ux-score-tax
plan: "04"
subsystem: dashboard-auth-react
tags: [auth, react, login-ux, x-api-key, localStorage, AuthProvider, login-form, sidebar, build]
dependency_graph:
  requires: [102-02]
  provides: [AUTH-03]
  affects:
    - src/dashboard/src/lib/api.ts
    - src/dashboard/src/context/AuthProvider.tsx
    - src/dashboard/src/pages/login.tsx
    - src/dashboard/src/components/sidebar.tsx
    - src/dashboard/src/App.tsx
    - quirk/dashboard/static/
tech_stack:
  added: []
  patterns:
    - AuthContext/AuthProvider/useAuth in single file (analog ScanContext/ScanProvider)
    - setUnauthorizedHandler module-level registration (avoids circular AuthContext dep)
    - AppShell mount guard switching on auth status
    - localStorage.getItem("quirk_api_token") as single token source
    - X-API-Key header injection in fetchApi (replaces Authorization: Bearer)
key_files:
  created:
    - src/dashboard/src/context/AuthProvider.tsx
    - src/dashboard/src/pages/login.tsx
  modified:
    - src/dashboard/src/lib/api.ts
    - src/dashboard/src/components/sidebar.tsx
    - src/dashboard/src/App.tsx
    - quirk/dashboard/static/ (rebuilt bundle)
decisions:
  - "Task 3 (mid-session 401 handler) folded into Task 1 commit — both touch identical files (api.ts + AuthProvider.tsx); no separate commit needed"
  - "Mount probe uses raw fetch() not fetchApi to avoid bootstrap ordering: handler registration useEffect runs after probe resolves"
  - "Auth-disabled passthrough: probe hits /api/scans with no token; 200 response sets authenticated (server returns 200 when auth is disabled)"
  - "Network error on probe treated as unauthenticated to avoid stuck loading state"
metrics:
  duration_seconds: 420
  completed_date: "2026-05-24"
  tasks_completed: 4
  files_modified: 6
requirements: [AUTH-03]
---

# Phase 102 Plan 04: AUTH-03 React Login UX Summary

**One-liner:** React login surface with AuthProvider mount probe, LoginPage per UI-SPEC, sidebar Sign-out control, AppShell auth guard, X-API-Key fetch layer, and mid-session 401 logout dispatch — dashboard statics rebuilt.

## What Was Built

### Task 1: Fetch layer + AuthProvider (localStorage / X-API-Key / probe)

**`src/dashboard/src/lib/api.ts`** — two targeted changes plus the Task 3 handler:

- `_resolveToken()` changed from `window.__QUIRK_CONFIG__?.apiToken` to `localStorage.getItem("quirk_api_token")` with try/catch for SSR/test environments
- Header injection changed from `Authorization: Bearer {token}` to `X-API-Key: {token}` — matching the 102-02 backend extension
- `fetchApi` refactored to capture response in a const, then check `response.status === 401 && token && _onUnauthorized` before returning — only fires when a token was sent (preserves auth-disabled passthrough)
- `setUnauthorizedHandler(fn)` exported — module-level callback registration with no import of AuthContext (no circular dependency)

**`src/dashboard/src/context/AuthProvider.tsx`** (new file) — single file combining context + provider + hook:

- `AuthContext` with default `{ status: "loading", setToken: () => {}, logout: () => {} }`
- `AuthProvider` with `useState("loading")` + two `useEffect` calls:
  1. Mount probe: raw `fetch("/api/scans")` with stored token as X-API-Key; 200 → authenticated, 401 → clear localStorage + unauthenticated, network error → unauthenticated
  2. Handler registration: `setUnauthorizedHandler(logout)` on mount, `setUnauthorizedHandler(null)` on unmount
- `logout` is `useCallback`-stable so the handler registration effect does not thrash
- Probe targets `/api/scans` (protected) NOT `/api/health` (auth-exempt)

### Task 2: LoginPage + sidebar Sign-out + App.tsx mount guard

**`src/dashboard/src/pages/login.tsx`** (new file) — exactly per 102-UI-SPEC.md:

- Outer `flex min-h-screen items-center justify-center bg-background`
- `Card w-full max-w-sm shadow-lg` with CardHeader (teal wordmark + "Dashboard Login" + CardDescription)
- `CardContent`: `<form aria-label="Dashboard login">` with `Label htmlFor="token-input"` + `Input id="token-input" type="password" autoFocus autoComplete="current-password" placeholder="Paste your token"` + always-in-DOM error `<p role="alert" aria-live="polite" className="text-sm font-normal text-destructive">` + `Button type="submit" w-full "Unlock Dashboard"`
- `CardFooter`: helper text with `<code className="font-mono">quirk token generate</code>`
- On submit: probes GET /api/scans with entered token; 200 → `setToken(token)`; failure → sets inline error "Invalid token. Check your token and try again.", clears input, refocuses via `inputRef`
- Exactly 2 font weights: `font-normal` (400) and `font-semibold` (600); teal accent on submit button only

**`src/dashboard/src/components/sidebar.tsx`** — minimal additions:
- Added `LogOut` to lucide-react import
- Added `Separator` import from `@/components/ui/separator`
- Added `useAuth` import from `@/context/AuthProvider`
- `const { logout } = useAuth()` at top of `Sidebar()`
- After ModeToggle div: `<Separator />` + collapsed icon-only ghost Button with `aria-label="Sign out"` + Tooltip "Sign out" + expanded `hidden lg:flex` full-width ghost Button "Sign out", both wired to `onClick={logout}`

**`src/dashboard/src/App.tsx`** — restructured:
- New `AppShell()` function using `useAuth().status` to switch: loading → blank `bg-background` div, unauthenticated → `<LoginPage />`, authenticated → existing Sidebar + main routes tree
- `AuthProvider` inserted between `ThemeProvider` and `ScanProvider` (ScanProvider/QRAMMProvider make API calls, must be inside AuthProvider)
- `<AppShell />` rendered inside BrowserRouter

### Task 3: Mid-session 401 → logout (shared util in lib/api.ts)

Folded into Task 1 commit (same files). All acceptance criteria satisfied:
- `setUnauthorizedHandler` exported from api.ts, invoked on `response.status === 401 && token`
- Auth-disabled passthrough preserved (handler not invoked when no token)
- No import of AuthContext into api.ts (no circular dependency)
- AuthProvider registers `logout` via `setUnauthorizedHandler` on mount, unregisters on unmount

### Task 4: Rebuild dashboard statics

`npm run build` in `src/dashboard/` completed successfully (657ms, 2419 modules transformed). Vite output updated in `quirk/dashboard/static/`. FastAPI now serves the bundle containing the full login surface.

### Task 5: Human-verify login flow (AUTH-03)

**Status: PENDING HUMAN-UAT** — this is a `checkpoint:human-verify` task. The executor stopped before this task as instructed. The full walkthrough steps are in the plan (102-04-PLAN.md, Task 5):

1. Start server with a configured token (`QUIRK_API_TOKEN=<token> python run_scan.py serve`)
2. Open dashboard → expect "Dashboard Login" Card with password input and teal "Unlock Dashboard" button
3. Submit wrong token → expect inline red "Invalid token. Check your token and try again." error
4. Submit correct token → expect full dashboard loads
5. Click "Sign out" → expect return to login form; localStorage `quirk_api_token` cleared
6. Mid-session 401: log in, rotate token via `python run_scan.py token rotate`, trigger a data fetch → expect automatic return to login form
7. Auth-disabled: unset token + restart → expect dashboard loads directly (no login form)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 3 implementation folded into Task 1 commit**
- **Found during:** Task 1 planning
- **Issue:** Tasks 1 and 3 both modify the identical pair of files (`api.ts` + `AuthProvider.tsx`). Splitting them into two commits would require either an empty commit or a partial implementation that fails TypeScript between commits.
- **Fix:** All Task 3 code (`setUnauthorizedHandler`, 401 check in `fetchApi`, `useEffect` handler registration in `AuthProvider`) implemented in the Task 1 commit. Task 3 commit recorded as satisfied by c9cffaf.
- **Files modified:** `src/dashboard/src/lib/api.ts`, `src/dashboard/src/context/AuthProvider.tsx`
- **Commit:** c9cffaf

## Known Stubs

None — all auth state transitions are wired to real localStorage + real API probes. No placeholder or hardcoded values.

## Threat Flags

No new security surface beyond the plan's threat model. The `window.__QUIRK_CONFIG__` global declaration was simplified to `Record<string, unknown>` (the `apiToken` field removed from the type since it is no longer read). No new endpoints.

## Self-Check

### Files exist:

- src/dashboard/src/context/AuthProvider.tsx: FOUND
- src/dashboard/src/pages/login.tsx: FOUND
- src/dashboard/src/components/sidebar.tsx: FOUND (modified)
- src/dashboard/src/App.tsx: FOUND (modified)
- src/dashboard/src/lib/api.ts: FOUND (modified)
- quirk/dashboard/static/index.html: FOUND (rebuilt)

### Commits exist:

- c9cffaf: feat(102-04): fetch layer + AuthProvider — FOUND
- a123a0d: feat(102-04): LoginPage + sidebar Sign-out + App.tsx mount guard — FOUND
- f926782: chore(102-04): rebuild dashboard statics — FOUND

## Self-Check: PASSED
