---
phase: 102-dashboard-auth-ux-score-tax
verified: 2026-05-24T00:00:00Z
status: human_needed
score: 8/8 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Login form renders on unauthenticated browser visit"
    expected: "Centered Card with 'Dashboard Login' heading, 'API Token' password field, and 'Unlock Dashboard' button — no silent 401, no dashboard content"
    why_human: "Browser rendering cannot be verified via grep; requires visual confirmation in a live browser"
  - test: "Wrong token shows inline error"
    expected: "Inline red text 'Invalid token. Check your token and try again.' appears below the input; input is cleared and refocused; dashboard is not loaded"
    why_human: "Error visibility, input clearing, and focus behavior require browser interaction"
  - test: "Correct token loads the full dashboard"
    expected: "Sidebar and main content render; no login form remains"
    why_human: "Route transition and authenticated state require live browser confirmation"
  - test: "Sign out clears token and returns to login form"
    expected: "localStorage quirk_api_token is removed (visible in DevTools Application tab); login form is re-displayed"
    why_human: "localStorage state and UI transition require browser DevTools inspection"
  - test: "Mid-session 401 bounces to login form"
    expected: "After rotating the token server-side, the next API call triggers a 401 which clears localStorage and returns the app to the login page automatically"
    why_human: "Requires server restart + live trigger of a data fetch; cannot be confirmed without a running server"
  - test: "Auth-disabled passthrough skips login form"
    expected: "With empty security.api_token and no QUIRK_API_TOKEN env var, dashboard loads directly without showing the login form"
    why_human: "Passthrough behavior requires a live server configured with no token"
  - test: "quirk token generate / rotate live round-trip"
    expected: "Token written to config.yaml security.api_token; old token stops working after rotate; QUIRK_API_TOKEN env var note printed when set"
    why_human: "File-system write and precedence note require manual terminal invocation to verify operator UX"
---

# Phase 102: Dashboard Auth + UX + Score Tax Verification Report

**Phase Goal:** A team can share a single-tenant dashboard instance via a rotatable API token and a login form, and the CLI executive report sources its score numbers from the same shared content model as HTML/PDF.
**Verified:** 2026-05-24
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | An operator can run `quirk token generate` and get a fresh token written to security.api_token in config.yaml | VERIFIED | `quirk/cli/token_cmd.py` implements `run_token` with generate/rotate/show; uses `secrets.token_urlsafe(32)`; `_write_token_to_config` does full-file yaml.safe_load → update `raw["security"]["api_token"]` → yaml.dump |
| 2 | `quirk token rotate` overwrites the stored token so the old one stops working immediately | VERIFIED | generate and rotate share identical code paths in token_cmd.py; `test_token_rotate_overwrites` passes in test suite |
| 3 | `quirk token show` prints the persisted YAML token (not the env-var value) | VERIFIED | show subcommand reads YAML directly via yaml.safe_load, not via `_get_configured_token()`; prints precedence note when QUIRK_API_TOKEN is set |
| 4 | Generating or rotating a token never destroys other config keys | VERIFIED | `_write_token_to_config` loads full file first; `test_token_generate_preserves_other_keys` asserts assessment + targets keys survive; test passes |
| 5 | The dashboard accepts X-API-Key header on protected routes, timing-safe, with precedence over bearer; auth-disabled passthrough preserved | VERIFIED | `auth.py` checks `request.headers.get("X-API-Key","")` before bearer; uses `hmac.compare_digest` for both paths; `if x_api_key:` guard prevents empty-string compare; passthrough guard `if not configured: return` unchanged |
| 6 | A CI test fails the build if any non-health data-returning route ships without require_auth | VERIFIED | `tests/test_route_coverage.py::test_all_data_routes_have_auth_dependency` introspects app.routes, excludes /api/health, asserts violations == []; passes (27 tests total, all green) |
| 7 | CLI executive markdown score total, band, and subscores come from the shared exec_content, not a local re-derivation | VERIFIED | `executive.py` lines 218–236: active branch reads `exec_content.score_total`, `exec_content.score_band`, `exec_content.subscores`, `exec_content.raw_sum`; no `score_raw['score']` or `score_raw['rating']` in the active branch |
| 8 | A cross-surface parity test asserts CLI score equals exec_content values | VERIFIED | `tests/test_score_parity.py::test_score_parity_across_surfaces` asserts str(exec_content.score_total), exec_content.score_band, and all subscore values appear in CLI markdown; passes |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/cli/token_cmd.py` | run_token entrypoint with generate/rotate/show + _write_token_to_config YAML round-trip | VERIFIED | All subcommands present; `secrets.token_urlsafe(32)`; full-file YAML write-back confirmed at line 25 |
| `run_scan.py` | token subcommand interception block | VERIFIED | Line 491: `_sys.argv[1] == "token"` with import and call to `run_token` at line 492 |
| `tests/test_token_cmd.py` | AUTH-01 unit coverage (4 tests) | VERIFIED | All four required tests present and passing |
| `quirk/dashboard/api/middleware/auth.py` | require_auth extended with X-API-Key + hmac.compare_digest precedence | VERIFIED | X-API-Key path added at lines 52–56; timing-safe; bearer fallback preserved |
| `tests/test_dashboard_auth_apikey.py` | AUTH-02 functional coverage (5 tests) | VERIFIED | All five tests present and passing |
| `tests/test_route_coverage.py` | Route-coverage CI gate for all /api/* data routes | VERIFIED | `test_all_data_routes_have_auth_dependency` present and passes |
| `quirk/reports/executive.py` | Score section sources exec_content.score_total/score_band/subscores/raw_sum | VERIFIED | Active branch (exec_content is not None) uses all four exec_content fields; legacy None-branch unchanged |
| `tests/test_score_parity.py` | TRANS-04 cross-surface score parity test | VERIFIED | `test_score_parity_across_surfaces` present and passes |
| `src/dashboard/src/context/AuthProvider.tsx` | AuthContext + AuthProvider + useAuth; mount probe on /api/scans; setUnauthorizedHandler registration | VERIFIED | Probes /api/scans (not /api/health); registers logout via setUnauthorizedHandler on mount; unregisters on unmount |
| `src/dashboard/src/pages/login.tsx` | LoginPage per 102-UI-SPEC (Card/Input/Button/Label, "Unlock Dashboard", inline error, "quirk token generate") | VERIFIED | All required copy strings present: "Dashboard Login", "Unlock Dashboard", "Invalid token. Check your token and try again.", "quirk token generate"; type="password"; aria-label="Dashboard login"; role="alert" aria-live="polite" |
| `src/dashboard/src/components/sidebar.tsx` | Sign out control wired to useAuth().logout | VERIFIED | LogOut + Separator + useAuth imported; "Sign out" text rendered; onClick={logout} wired |
| `src/dashboard/src/App.tsx` | AuthProvider wrapping + AppShell mount guard on status | VERIFIED | AuthProvider between ThemeProvider and ScanProvider; AppShell switches on loading/unauthenticated/authenticated |
| `src/dashboard/src/lib/api.ts` | localStorage token source + X-API-Key injection + setUnauthorizedHandler + 401 mid-session handler | VERIFIED | _resolveToken reads localStorage; `headers["X-API-Key"] = token`; setUnauthorizedHandler exported; 401 check fires when token was sent |
| `quirk/dashboard/static/` (built bundle) | Rebuilt statics include AuthProvider/LoginPage | VERIFIED | Build output at `quirk/dashboard/static/` (vite.config.ts outDir); index.html + assets present; "Unlock Dashboard" and "quirk_api_token" confirmed in built JS bundle |
| `docs/configuration.md` | quirk token CLI + X-API-Key auth documented | VERIFIED | "quirk token" and "X-API-Key" both present |
| `docs/UAT-SERIES.md` | Updated test cases for token CLI + login flow + score parity | VERIFIED | UAT-102-01..07 sections added; Last Updated bumped to 2026-05-25 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_scan.py` | `quirk.cli.token_cmd.run_token` | `_sys.argv[1] == "token"` interception | WIRED | Line 491 interception + line 492 import + call |
| `quirk/cli/token_cmd.py` | `config.yaml security.api_token` | yaml.safe_load full file → update single key → yaml.dump | WIRED | `raw["security"]["api_token"] = token` with full-file round-trip |
| `auth.py::require_auth` | `request.headers X-API-Key` | `request.headers.get("X-API-Key","")` checked before bearer, hmac.compare_digest | WIRED | Lines 52–56 |
| `tests/test_route_coverage.py` | `app.routes` introspection | `{dep.dependency for dep in route.dependencies}`, exclude /api/health | WIRED | Passes; all data routes covered |
| `executive.py::build_exec_markdown` | `exec_content.score_total / .score_band / .subscores / .raw_sum` | active exec_content-is-not-None branch | WIRED | All four fields referenced in lines 218–236 |
| `src/dashboard/src/lib/api.ts` | `localStorage quirk_api_token` | `_resolveToken()` reads localStorage; `headers["X-API-Key"] = token` | WIRED | Lines 29–33 (resolve) + line 79 (inject) |
| `src/dashboard/src/lib/api.ts` | AuthProvider logout (mid-session 401) | `setUnauthorizedHandler` registered by AuthProvider; fired when response.status===401 AND token present | WIRED | api.ts lines 85–87; AuthProvider.tsx lines 122–127 |
| `src/dashboard/src/context/AuthProvider.tsx` | `GET /api/scans` (protected probe) | mount useEffect probes /api/scans | WIRED | Line 99 in AuthProvider.tsx |
| `src/dashboard/src/App.tsx` | `AuthProvider + LoginPage` | AppShell switches on `status === "unauthenticated"` | WIRED | Lines 46–48 in App.tsx |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend test suite (AUTH-01/02, TRANS-04) | `python -m pytest tests/test_token_cmd.py tests/test_dashboard_auth_apikey.py tests/test_route_coverage.py tests/test_score_parity.py tests/test_api_auth.py -q` | 27 passed in 1.22s | PASS |
| TypeScript typecheck (AUTH-03 frontend) | `cd src/dashboard && npx tsc --noEmit -p tsconfig.json` | No output (clean) | PASS |
| Built bundle contains auth artifacts | grep "Unlock Dashboard" + "quirk_api_token" in quirk/dashboard/static/assets/index-B3gjlzaG.js | Both strings found (count=1 each) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTH-01 | 102-01 | CLI token generate/rotate/show persisted to security.api_token | SATISFIED | token_cmd.py fully implemented; 4 tests passing |
| AUTH-02 | 102-02 | Dashboard accepts X-API-Key + bearer, timing-safe, route-coverage CI gate | SATISFIED | auth.py extended; route_coverage test passes |
| AUTH-03 | 102-04 | Login form + AuthProvider + sidebar Sign-out + App.tsx auth gate + built statics | SATISFIED | All frontend artifacts verified; build output confirmed |
| TRANS-04 | 102-03 | CLI executive score sourced from exec_content; parity test enforces it | SATISFIED | executive.py active branch uses exec_content fields; test_score_parity passes |

---

### Anti-Patterns Found

No debt markers (TBD, FIXME, XXX) found in any file modified by this phase.

No stub patterns detected. All implementations are substantive and wired.

---

### Human Verification Required

The following items require manual browser and terminal walkthrough. All automated checks pass.

#### 1. Login form renders on unauthenticated browser visit

**Test:** Start the dashboard with auth enabled (`quirk token generate --config config.yaml`, then `QUIRK_API_TOKEN=<token> python run_scan.py serve`). Open the dashboard in a browser.
**Expected:** A centered "Dashboard Login" Card with an "API Token" password field and "Unlock Dashboard" button — not the dashboard content or a silent 401.
**Why human:** Browser rendering cannot be confirmed with grep.

#### 2. Wrong token shows inline error

**Test:** On the login form, enter a wrong token and click Unlock Dashboard.
**Expected:** Inline red text "Invalid token. Check your token and try again." appears; input is cleared and refocused; no dashboard content loads.
**Why human:** Error rendering, input clearing, and focus restoration require browser interaction.

#### 3. Correct token loads the full dashboard

**Test:** Enter the correct token on the login form.
**Expected:** Full sidebar + dashboard content is displayed; login form is gone.
**Why human:** Authenticated route rendering requires live browser confirmation.

#### 4. Sign out clears token and returns to login form

**Test:** While authenticated, click "Sign out" in the sidebar bottom section.
**Expected:** localStorage `quirk_api_token` is cleared (verify DevTools → Application → Local Storage); login form is re-displayed.
**Why human:** localStorage state change and UI transition require DevTools inspection.

#### 5. Mid-session 401 bounces to login form

**Test:** Log in with the correct token, then in another terminal run `python run_scan.py token rotate --config config.yaml` and restart the server with the new token. Trigger any dashboard data fetch (navigate to a tab).
**Expected:** The next API call 401s and the app automatically returns to the login form; localStorage is cleared.
**Why human:** Requires a server restart and a live 401 trigger; cannot be confirmed without a running server.

#### 6. Auth-disabled passthrough skips login form

**Test:** Stop the server, clear `security.api_token` in config.yaml, unset `QUIRK_API_TOKEN`, restart serve.
**Expected:** Dashboard loads directly with no login form (passthrough preserved).
**Why human:** Requires a live server configured with no token.

#### 7. quirk token generate / rotate live round-trip

**Test:** Run `python run_scan.py token generate --config /tmp/test.yaml`, then `python run_scan.py token show --config /tmp/test.yaml`. Also run rotate and verify a new token replaces the old one.
**Expected:** Token written to file; show prints the same value; rotate produces a different token; QUIRK_API_TOKEN precedence note printed when env var is set.
**Why human:** File-system write and precedence note require manual terminal inspection to verify operator UX feel.

---

### Gaps Summary

No gaps. All automated verifications passed. The human verification items above are browser/terminal UX checks that cannot be confirmed programmatically — they are classified as human_needed, not gaps_found.

---

_Verified: 2026-05-24_
_Verifier: Claude (gsd-verifier)_
