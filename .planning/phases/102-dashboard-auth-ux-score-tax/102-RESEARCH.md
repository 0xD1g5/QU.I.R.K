# Phase 102: Dashboard Auth UX + Score Tax - Research

**Researched:** 2026-05-25
**Domain:** FastAPI auth middleware, React context / localStorage, Python config write-back, CLI subcommand registration, score sourcing refactor
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Token CLI (AUTH-01)**
- Command surface: `quirk token generate` / `quirk token rotate` / `quirk token show`
- Token generation: stdlib `secrets.token_urlsafe(32)`
- Persisted to YAML config `security.api_token` field — same field `require_auth` reads
- Rotation: `rotate` overwrites the stored token in place; old token stops working immediately; no grace window

**API-Key Auth (AUTH-02)**
- Extend existing `require_auth` to accept `X-API-Key: <token>` OR `Authorization: Bearer <token>` — both timing-safe via `hmac.compare_digest`
- CI route-coverage test enumerates all data-returning routes and asserts each is protected by `require_auth`
- Precedence: check `X-API-Key` first, fall back to bearer; either valid → pass
- Preserve existing auth-disabled passthrough (empty configured token = auth disabled)

**Login UX (AUTH-03)**
- Unauthenticated browser sees React login form, not a silent 401
- Client-side token stored in `localStorage`, injected as `X-API-Key` header via existing fetch/client layer
- Auth-state detection: probe request — 401 → show login, 200 → show dashboard
- Failed login shows inline "Invalid token" error; logout control clears localStorage

**Score-Tax Refactor (TRANS-04)**
- CLI executive markdown sources total/band/subscores from shared `exec_content` instead of re-deriving locally
- Cross-surface parity test asserts score number is numerically identical across CLI/HTML/PDF/DOCX
- Pure sourcing refactor — emitted numbers must not change versus current HTML/PDF
- Closes v5.2 backlog item "CLI score should source exec_content"

### Claude's Discretion

None specified beyond the above locked decisions.

### Deferred Ideas (OUT OF SCOPE)

- Multi-tenant auth, user accounts, RBAC, per-route scopes
- OAuth/SSO integration
- Token expiry/TTL (rotation is manual; no auto-expiry in v5.3)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | `quirk token generate/rotate/show` CLI using stdlib `secrets`; persisted to `security.api_token` YAML field | CLI registration pattern in run_scan.py interception block; config write-back via PyYAML dump; SecurityCfg.api_token field verified in quirk/config.py:329 |
| AUTH-02 | Dashboard accepts `X-API-Key` header (in addition to bearer); timing-safe; CI route-coverage test enforces protection | require_auth in quirk/dashboard/api/middleware/auth.py:34; all data-returning routes use router-level Depends(); existing test_api_auth.py D-06 gate only covers mutating routes — extend to ALL routes |
| AUTH-03 | React login form; clear authenticated/unauthenticated state; localStorage token; X-API-Key injection in fetch layer | App.tsx wraps routes in providers; lib/api.ts is the single fetch interception point; context/ dir has existing provider pattern (ScanProvider, QRAMMProvider); UI-SPEC.md is locked |
| TRANS-04 | CLI executive markdown sources score from `exec_content`; cross-surface parity test covers CLI/HTML/PDF/DOCX | build_exec_markdown already uses exec_content for narrative/risks/roadmap; score section (lines 204, 228, 238) still reads score_raw directly — this is the gap; ExecContent.score_total / .score_band / .subscores / .raw_sum carry the canonical values |
</phase_requirements>

---

## Summary

Phase 102 has four deliverables that are technically orthogonal: a new CLI subcommand group, a backend middleware extension, a React auth UX, and a score-sourcing fix. All four touch well-understood seams in the existing codebase.

**AUTH-01 (token CLI)** follows the established `run_scan.py` interception block pattern exactly. The critical gap is config write-back: `load_config` reads YAML but there is no `save_config` function anywhere in the codebase. The token subcommand must implement its own YAML round-trip using `yaml.safe_load` + field update + `yaml.dump`, being careful not to destroy other config keys.

**AUTH-02 (X-API-Key)** is a minimal extension to `require_auth` in `quirk/dashboard/api/middleware/auth.py`. The existing D-06 gate in `tests/test_api_auth.py` already covers **mutating** routes only. AUTH-02 requires extending that gate to cover **all** data-returning routes (GET routes on all non-health routers). All data-returning routes currently use router-level `Depends()` which already populates `route.dependencies` — the introspection works.

**AUTH-03 (login form)** requires creating `AuthProvider.tsx` + `login.tsx`, modifying `App.tsx` to mount a guard, modifying `sidebar.tsx` to add the logout control, and modifying `lib/api.ts` to switch from `window.__QUIRK_CONFIG__.apiToken` (injected server-side) to `localStorage.getItem("quirk_api_token")`. The 102-UI-SPEC.md is a locked design contract; no design decisions are left open.

**TRANS-04 (score tax)** is the smallest change: in `build_exec_markdown` (executive.py, lines ~204 and ~228-238), replace the three `score_raw['score']` / `score_raw['rating']` / `subscores` / `raw_sum` reads with `exec_content.score_total` / `exec_content.score_band` / `exec_content.subscores` / `exec_content.raw_sum`. The `exec_content` parameter is already threaded through from `writer.py`. The backward-compat `exec_content is None` path may keep reading `score_raw` since it's the legacy path. The parity test extends `test_cross_surface_parity.py` with a score-specific assertion.

**Primary recommendation:** Build in plan order AUTH-01 → AUTH-02 → TRANS-04 → AUTH-03, where AUTH-01 and TRANS-04 are pure Python, AUTH-02 adds one CI test, and AUTH-03 is the only frontend plan requiring `npm run build`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Token generate/rotate/show | CLI (run_scan.py + quirk/cli/token_cmd.py) | Config file (YAML) | Pure CLI operation; persists to YAML via yaml.dump |
| X-API-Key auth enforcement | API/Backend (auth.py middleware) | — | All auth enforcement is server-side; frontend only supplies the header |
| Route-coverage CI test | Test layer (tests/test_api_auth.py) | API/Backend (app.routes introspection) | Test enumerates routes at import time; no runtime enforcement |
| Login form / auth state | Frontend (React context + pages) | — | Auth gate is client-side UX; server always enforces via require_auth |
| Token injection on fetch | Frontend (lib/api.ts) | — | Single interception point; all components call fetchApi() |
| Score sourcing from exec_content | Backend (quirk/reports/executive.py) | — | build_exec_markdown already receives exec_content; gap is which fields it reads |
| Cross-surface score parity test | Test layer (tests/test_cross_surface_parity.py) | — | Extend existing parity test file |

---

## Standard Stack

### Core (all existing — no new pip deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `secrets` (stdlib) | Python 3.11+ stdlib | Token generation | Cryptographically secure; AUTH-01 locked decision |
| `yaml` (PyYAML) | existing dep | Config read/write | Already used throughout; `yaml.safe_load` + `yaml.dump` for round-trip |
| `hmac` (stdlib) | stdlib | Timing-safe comparison | Already used in auth.py; extend pattern |
| `fastapi` | existing | Route introspection for CI test | `app.routes`, `APIRoute.dependencies` |
| `react` + TypeScript | existing (Vite) | AuthContext + LoginPage | Project stack |
| `localStorage` (Web API) | browser native | Token persistence | AUTH-03 locked decision |

### No New npm Packages

The UI-SPEC.md explicitly states: "No new npm packages. No new shadcn registry blocks. All primitives are already present in the codebase." All shadcn primitives needed (Card, Input, Label, Button, Separator, Tooltip) are already installed. `LogOut` is already imported by sidebar.tsx pattern.

**Installation:** none required.

---

## Package Legitimacy Audit

> No new packages introduced by this phase. All dependencies are existing codebase dependencies or Python/browser stdlib.

| Package | Registry | Status | Disposition |
|---------|----------|--------|-------------|
| `secrets` | Python stdlib | stdlib | Approved |
| `yaml` (PyYAML) | existing dep | existing | Approved |
| `hmac` | Python stdlib | stdlib | Approved |

**Packages removed due to slopcheck:** none
**Packages flagged as suspicious:** none
**New npm packages:** none

---

## Architecture Patterns

### System Architecture Diagram

```
AUTH-01 token CLI
  run_scan.py (argv interception: _sys.argv[1] == "token")
    └─> quirk/cli/token_cmd.py::run_token(argv)
          ├─> generate: secrets.token_urlsafe(32); write to YAML security.api_token
          ├─> rotate:   same as generate (overwrites, old token immediately invalid)
          └─> show:     load_config(path); print cfg.security.api_token (masked)

AUTH-02 backend
  FastAPI request
    └─> require_auth(request, credentials) [Depends()]
          ├─> _get_configured_token() → env var / YAML
          ├─> check Request.headers.get("X-API-Key") first [NEW]
          │     └─> hmac.compare_digest(x_api_key, configured) → pass/401
          └─> fallback to credentials (HTTPBearer) [existing]
                └─> hmac.compare_digest(bearer, configured) → pass/401

  CI gate (test_api_auth.py — extended)
    create_app().routes → APIRoute instances
      ├─> for each GET/POST/PUT/DELETE route except /api/health:
      │     assert require_auth in {dep.dependency for dep in route.dependencies}
      └─> violations list → assert == []

AUTH-03 frontend
  Browser boots → AuthProvider mounts
    └─> probe GET /api/health (no auth header needed — health is exempt)
          ├─> 200 + stored token valid → status = "authenticated"
          ├─> 200 (auth disabled) → status = "authenticated"
          └─> 401 → status = "unauthenticated"
    status === "loading"        → render blank dark screen
    status === "unauthenticated"→ render <LoginPage />
    status === "authenticated"  → render <Sidebar /> + routes

  LoginPage submits token
    └─> probe GET /api/scans (or /api/health with X-API-Key)
          ├─> 200 → localStorage.setItem("quirk_api_token", token) → authenticated
          └─> 401 → show inline error, refocus input

  lib/api.ts (fetchApi)
    └─> reads localStorage.getItem("quirk_api_token") [CHANGED from window.__QUIRK_CONFIG__]
          └─> injects X-API-Key header [NEW] instead of Authorization: Bearer [CHANGED]
          └─> if fetch returns 401 while authenticated → logout (clear storage)

TRANS-04 score sourcing
  build_exec_markdown(cfg, endpoints, findings, *, exec_content)
    ├─> [currently] "Quantum Readiness Score" section reads score_raw['score'],
    │     score_raw['rating'], score_raw.get('subscores'), and locally computes raw_sum
    └─> [after TRANS-04] reads exec_content.score_total, exec_content.score_band,
          exec_content.subscores, exec_content.raw_sum
          (backward-compat exec_content is None path may keep score_raw reads)
```

### Recommended Project Structure

```
quirk/
├── cli/
│   └── token_cmd.py          # NEW — run_token(argv) with generate/rotate/show
├── dashboard/api/middleware/
│   └── auth.py               # MODIFY — add X-API-Key header check
tests/
├── test_api_auth.py          # MODIFY — extend D-06 gate to GET routes
├── test_token_cmd.py         # NEW — token generate/rotate/show + config write-back
├── test_cross_surface_parity.py  # MODIFY — add score parity assertions
src/dashboard/src/
├── context/
│   └── AuthProvider.tsx      # NEW
├── pages/
│   └── login.tsx             # NEW
├── components/
│   └── sidebar.tsx           # MODIFY — add logout control
├── App.tsx                   # MODIFY — wrap in AuthProvider, mount guard
└── lib/
    └── api.ts                # MODIFY — localStorage token, X-API-Key header
```

---

## Domain 1: CLI Subcommand Registration (AUTH-01)

### Pattern

`run_scan.py` uses a chain of `if len(_sys.argv) > 1 and _sys.argv[1] == "<subcommand>"` blocks to intercept before the scan argparse. The `token` interception block goes at line ~484 (after `analyze-token`, before `errors`). [VERIFIED: codebase grep]

```python
# run_scan.py — interception block
if len(_sys.argv) > 1 and _sys.argv[1] == "token":
    from quirk.cli.token_cmd import run_token
    run_token(_sys.argv[2:])
    return
```

`run_token` in `quirk/cli/token_cmd.py` uses `argparse.ArgumentParser` with `add_subparsers` (same pattern as `quirk/cli/schedule_cmd.py`):

```python
def run_token(argv):
    parser = argparse.ArgumentParser(prog="quirk token", ...)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("generate", ...)
    sub.add_parser("rotate", ...)
    sub.add_parser("show", ...)
    # Each accepts --config <path>
    args = parser.parse_args(argv)
    ...
```

### Config Write-Back — Critical Detail

`load_config(path)` in `quirk/config.py:491` reads YAML and returns an `AppConfig`. There is **no `save_config` function anywhere in the codebase** — this has been verified by grep. [VERIFIED: codebase grep]

The token subcommand must implement its own round-trip:

```python
import yaml

def _write_token_to_config(config_path: str, token: str) -> None:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if "security" not in raw or not isinstance(raw.get("security"), dict):
        raw["security"] = {}
    raw["security"]["api_token"] = token
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, default_flow_style=False, allow_unicode=True)
```

**Pitfall:** `yaml.dump` without `allow_unicode=True` may escape non-ASCII in existing YAML values. Use `allow_unicode=True` to match other YAML writers in the codebase (see `jobs.py:101`).

**Pitfall:** The YAML round-trip via `yaml.safe_load` + `yaml.dump` loses comments and may reorder keys. This is acceptable for a config file (`config.yaml`). The existing `jobs.py:101` sets the precedent with `yaml.dump(config, fh, default_flow_style=False)`.

**Config path resolution:** All existing CLI subcommands accept `--config` pointing to a `config.yaml`. The `QUIRK_API_TOKEN` env var wins over YAML (D-01 from auth.py). Document clearly in `quirk token --help` that the env var always takes precedence.

**`show` subcommand:** Print only a masked version (e.g., first 6 chars + `...`) to avoid echoing the full token in terminal history. Or print full token to stdout only when the terminal is not a TTY / when redirected — match the existing `getpass` pattern. CONTEXT.md does not specify masking behavior; suggest printing the full token since the command exists for retrieval.

---

## Domain 2: require_auth Extension (AUTH-02)

### Current Signature [VERIFIED: codebase read]

```python
# quirk/dashboard/api/middleware/auth.py
def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    configured = _get_configured_token()
    if not configured:
        return  # auth disabled
    if credentials is None:
        raise HTTPException(status_code=401, ...)
    if not hmac.compare_digest(credentials.credentials, configured):
        raise HTTPException(status_code=401, ...)
```

### Extension Pattern

Add `X-API-Key` check before the bearer check. The `Request` parameter is already in the signature:

```python
def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    configured = _get_configured_token()
    if not configured:
        return  # D-02: auth disabled

    # AUTH-02: check X-API-Key first (precedence per CONTEXT.md)
    x_api_key = request.headers.get("X-API-Key", "")
    if x_api_key:
        if hmac.compare_digest(x_api_key, configured):
            return  # valid X-API-Key
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))

    # Fallback to bearer (existing path)
    if credentials is None:
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
    if not hmac.compare_digest(credentials.credentials, configured):
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
```

**Timing-safe correctness:** `hmac.compare_digest` requires both arguments to be the same type (str or bytes). When `x_api_key` is an empty string from `headers.get("X-API-Key", "")`, the guard `if x_api_key:` prevents calling `compare_digest` on an empty string against the configured token (which would be a timing leak only if the attacker can observe the short-circuit, which they cannot from HTTP). This is acceptable.

**Pitfall — local-import shadow trap:** The extension adds `x_api_key = request.headers.get(...)` inside the function. `x_api_key` must NOT shadow any module-level import or be conditionally imported elsewhere in the same function scope. The current function has no imports; this pitfall does not apply here, but it applies in `token_cmd.py` if `secrets` or `yaml` is imported conditionally.

### Route Coverage Analysis [VERIFIED: codebase grep]

All data-returning routes use router-level `dependencies=[Depends(require_auth)]`. No route is missing auth:

| Router | Module | Auth method |
|--------|--------|-------------|
| `scan.router` | routes/scan.py:81 | `APIRouter(dependencies=[Depends(require_auth)])` |
| `trends.router` | routes/trends.py:38 | `APIRouter(dependencies=[Depends(require_auth)])` |
| `qramm.router` | routes/qramm.py:50 | `APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])` |
| `schedules.router` | routes/schedules.py:33 | `APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])` |
| `jobs.read_router` | routes/jobs.py:38 | `APIRouter(dependencies=[Depends(require_auth)])` |
| `jobs.write_router` | routes/jobs.py:39 | `APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])` |
| `pdf.router` | routes/pdf.py:23 | `APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])` |
| `health.router` | routes/health.py:6 | `APIRouter()` — **no auth, intentionally exempt** |

**Finding:** All data-returning routes are currently protected. No unprotected data route found. [VERIFIED: codebase grep]

### Extending the CI Gate

The existing `test_all_mutating_routes_have_auth_dependency` in `test_api_auth.py` checks only `POST/PUT/DELETE/PATCH` routes. AUTH-02 requires a new test (or extended test) that checks **all** routes except `/api/health`:

```python
def test_all_data_routes_have_auth_dependency(monkeypatch):
    from fastapi.routing import APIRoute
    from quirk.dashboard.api.middleware.auth import require_auth
    app = create_app()
    violations = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path in {"/api/health", "/api/health/"}:
            continue
        dep_callables = {dep.dependency for dep in route.dependencies}
        if require_auth not in dep_callables:
            violations.append(f"{sorted(route.methods)} {route.path}")
    assert violations == [], ...
```

**How router-level dependencies propagate:** When `APIRouter(dependencies=[Depends(require_auth)])` is used, FastAPI copies those dependencies onto each route registered with that router. At the `app.routes` level, each `APIRoute.dependencies` list contains the router-level dependencies merged with any per-route dependencies. The introspection `{dep.dependency for dep in route.dependencies}` correctly surfaces them. [VERIFIED: matches existing working test at test_api_auth.py:329]

---

## Domain 3: Login Form (AUTH-03)

### Fetch Layer Change (lib/api.ts)

The current `fetchApi()` in `src/dashboard/src/lib/api.ts` reads the token from `window.__QUIRK_CONFIG__.apiToken` and injects it as `Authorization: Bearer`. AUTH-03 changes this to read from `localStorage` and inject as `X-API-Key`. [VERIFIED: codebase read]

```typescript
// Current (lib/api.ts:29-35, 67-69):
function _resolveToken(): string {
  return window.__QUIRK_CONFIG__?.apiToken ?? ""
}
// ...
if (token) {
  headers["Authorization"] = `Bearer ${token}`
}

// After AUTH-03:
function _resolveToken(): string {
  return localStorage.getItem("quirk_api_token") ?? ""
}
// ...
if (token) {
  headers["X-API-Key"] = token  // matches AUTH-02 header name
}
```

**Pitfall:** If `window.__QUIRK_CONFIG__` was used to inject the token server-side during `quirk serve`, that injection path must either be removed or kept as a secondary fallback. The CONTEXT.md decision is clear — localStorage is the single source — so the server-side injection can be dropped.

**401-while-authenticated logout:** After the change, if any `fetchApi()` call returns 401 while `status === "authenticated"`, the app must call `logout()` from AuthContext. This requires AuthContext to expose `logout` and for hooks to call it on 401. The cleanest approach: `fetchApi()` itself does not know about auth state; instead, individual hooks check response status and call `useAuth().logout()` on 401.

Simpler alternative: make `fetchApi()` accept an optional `onUnauthorized` callback, or have hooks wrap fetchApi with a 401 check. The UI-SPEC.md specifies this behavior ("if a fetch returns 401 while authenticated: treat as logout") but does not prescribe the implementation. The planner should decide which hook pattern to use; the recommendation is a thin wrapper in each hook that checks `response.status === 401 && authStatus === "authenticated"`.

### AuthContext (context/AuthProvider.tsx) — New File

Existing provider pattern in `context/ScanProvider.tsx` and `context/QRAMMProvider.tsx` shows the standard shape: a `createContext` + a `Provider` component + a `use*` hook. The `AuthProvider.tsx` follows the same pattern. [VERIFIED: codebase ls]

App.tsx currently wraps routes in `<ThemeProvider><ScanProvider><QRAMMProvider><TooltipProvider><BrowserRouter>...`. AuthProvider must wrap the entire tree (or at minimum wrap the route-tree), sitting outside `ScanProvider` and `QRAMMProvider` since those providers make API calls that need auth. Recommended placement: `<ThemeProvider><AuthProvider><ScanProvider>...`.

### Auth-Init Probe

The UI-SPEC.md specifies probing `GET /api/health` or a first data call. `/api/health` is auth-exempt (returns 200 always), so it cannot distinguish "auth enabled and token present" from "auth disabled". The correct probe is a protected route — e.g., `GET /api/scans` with the stored token. [VERIFIED: codebase read — health.py has no require_auth]

**If token is absent from localStorage:** probe returns 401 (when auth enabled) or 200 (when auth disabled). Behavior:
- 401 → unauthenticated → show login
- 200 → authenticated (auth disabled) → show dashboard

**If token is present in localStorage:** probe with `X-API-Key: <token>`:
- 200 → authenticated → show dashboard
- 401 → token is stale/rotated → show login (clear localStorage first)

This means the probe must be a protected route, not `/api/health`. Use `GET /api/scans` as the probe target (lightweight, always returns a list even for an empty DB).

### App.tsx Modification

Current App.tsx renders `<Sidebar />` unconditionally inside the BrowserRouter. After AUTH-03, the mount guard wraps the entire `<div className="flex min-h-screen ...">` tree:

```tsx
// status === "loading"         → <div className="min-h-screen bg-background" />
// status === "unauthenticated" → <LoginPage />
// status === "authenticated"   → existing Sidebar + routes tree
```

The `AuthProvider` must be placed before `ScanProvider`/`QRAMMProvider` in the provider tree since those providers call `fetchApi()` which requires auth. [VERIFIED: App.tsx read]

### Sidebar Modification

Current sidebar.tsx ends at line 126 with `</aside>`. The logout control inserts before the closing `</aside>`, after the `ModeToggle` div. The `LogOut` icon from lucide-react is imported by the existing sidebar.tsx import block, but the `LogOut` named export is not currently imported — it must be added to the destructured import. `Separator` must also be imported if not already. [VERIFIED: sidebar.tsx read — current lucide-react imports do not include LogOut]

---

## Domain 4: TRANS-04 Score Sourcing

### The Gap [VERIFIED: codebase read]

`build_exec_markdown` in `quirk/reports/executive.py` already receives `exec_content` and uses it for narrative, risks, and roadmap. However, the **score section** (the "Quantum Readiness Score" heading block) still reads from the locally-computed `score_raw`:

- Line 204: `f"**Score:** **{score_raw['score']}/100**  \n**Rating:** **{score_raw['rating']}**"`
- Lines 227-228: `subscores = score_raw.get("subscores") or {}` + per-key rendering
- Lines 233-238: `raw_sum = exec_content.raw_sum if exec_content is not None else ...` ← already uses exec_content for raw_sum!
- Line 238: `f"**Rollup:** {raw_sum} ÷ 1.5 = **{score_raw['score']} / 100**"` ← reads score_raw again

The `raw_sum` is already sourced from `exec_content` when present (executive.py:233). The fix is:
1. Replace `score_raw['score']` → `exec_content.score_total` (lines 204, 238)
2. Replace `score_raw['rating']` → `exec_content.score_band` (line 204)
3. Replace `score_raw.get("subscores") or {}` → `exec_content.subscores` (line 227/228 area)

The backward-compat `exec_content is None` path (lines 192-202, 334-343) can keep reading `score_raw` since it is the legacy path that `writer.py` never uses (it always passes `exec_content`).

**`_scorecard_markdown` in writer.py:** This function reads `score.get('total')` from the compat wrapper dict (not `exec_content`). It is a separate markdown artifact (scorecard-*.md) separate from the executive markdown. TRANS-04 scopes to the executive markdown only — `_scorecard_markdown` is out of scope unless the parity test reveals a discrepancy. [VERIFIED: writer.py:75-112]

### Parity Test

The existing `test_cross_surface_parity.py` tests narrative and top_risks parity across CLI/HTML/DOCX. TRANS-04 adds a score parity assertion:

```python
def test_score_parity_across_surfaces(tmp_path):
    """TRANS-04: score_total and subscores are numerically identical across CLI/HTML/PDF/DOCX."""
    exec_content = build_exec_content(score_raw=_SCORE_RAW, ...)
    cli_output = build_exec_markdown(cfg, endpoints=[], findings=_FINDINGS, exec_content=exec_content)
    # Assert exec_content.score_total appears as literal integer in CLI output
    assert str(exec_content.score_total) in cli_output
    assert exec_content.score_band in cli_output
    # For each subscore key, assert value appears in CLI
    for key, val in exec_content.subscores.items():
        assert str(val) in cli_output
```

The HTML parity check is implicit — HTML already sources from exec_content (pre-existing). The new test validates the CLI surface now matches.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token generation | Custom PRNG or os.urandom hex | `secrets.token_urlsafe(32)` | stdlib crypto-safe; locked decision |
| Timing-safe comparison | Manual string equality | `hmac.compare_digest` | Already in codebase; prevents timing attacks |
| Config YAML round-trip | Custom parser | `yaml.safe_load` + `yaml.dump` | Existing pattern (jobs.py:101); safe and standard |
| FastAPI route introspection | Custom middleware scan | `app.routes` + `isinstance(route, APIRoute)` | Existing pattern in test_api_auth.py; verified to work |
| React auth state | Custom event bus | React context + `createContext` | Existing provider pattern (ScanProvider, QRAMMProvider) |

---

## Common Pitfalls

### Pitfall 1: `hmac.compare_digest` requires same-type arguments
**What goes wrong:** Calling `hmac.compare_digest(x_api_key, configured)` where one is bytes and one is str raises `TypeError`.
**Why it happens:** `request.headers.get()` returns `str`; `_get_configured_token()` returns `str`. This is safe, but if anyone introduces `.encode()` on one side only, it breaks.
**How to avoid:** Keep both operands as `str`. Do not encode either side.
**Warning signs:** `TypeError: a bytes-like object is required` in test or runtime.

### Pitfall 2: Config write-back clobbers other keys
**What goes wrong:** `yaml.dump({"security": {"api_token": token}}, ...)` writes only the security block, losing all other config sections.
**Why it happens:** Writing a partial dict instead of the full loaded dict.
**How to avoid:** Always `yaml.safe_load` the full file first, update only `raw["security"]["api_token"]`, then `yaml.dump(raw, ...)`.
**Warning signs:** After `quirk token generate`, running `quirk scan` fails because config is missing `assessment`/`scan`/`targets` blocks.

### Pitfall 3: The `show` subcommand triggers the env var path
**What goes wrong:** `quirk token show` prints the env var value, not the YAML value, when `QUIRK_API_TOKEN` is set.
**Why it happens:** `_get_configured_token()` in auth.py gives env var priority (D-01). The `show` subcommand should document this: "If QUIRK_API_TOKEN is set, that value is active regardless of the YAML value."
**How to avoid:** In `token show`, always read directly from YAML (not via `_get_configured_token`) so the operator sees the persisted YAML value. Print a note if `QUIRK_API_TOKEN` env var is also set.

### Pitfall 4: local-import shadow trap in token_cmd.py
**What goes wrong:** If `secrets` is imported at module scope and also conditionally referenced inside a branch, Python compile-time scoping makes it function-local for the whole function.
**Why it happens:** Python compile-time rule (per project memory `feedback_local_import_shadow_trap.md`).
**How to avoid:** Import `secrets` at module scope unconditionally (it is always available as stdlib). Same for `yaml`.

### Pitfall 5: npm run build not run after frontend changes
**What goes wrong:** `.tsx` edits are invisible in the browser; FastAPI serves stale pre-built statics.
**Why it happens:** FastAPI serves the Vite build output in `quirk/dashboard/static/`; the build step copies from `src/dashboard/dist/`.
**How to avoid:** Every plan touching `.tsx` files must include a task: `cd src/dashboard && npm run build`. The plan must verify the build succeeds before marking the task done.

### Pitfall 6: Auth probe uses /api/health (auth-exempt route)
**What goes wrong:** `AuthContext` probes `/api/health` — it always returns 200 regardless of auth state. The app immediately shows the authenticated dashboard with no token, then every subsequent API call fails with 401.
**Why it happens:** `/api/health` has no `require_auth` dependency (health.py:6 — bare `APIRouter()`).
**How to avoid:** Use a protected route as the auth probe — `GET /api/scans` is the recommended probe target (lightweight, always available).

### Pitfall 7: Token injection switches header name but server still expects Bearer
**What goes wrong:** Frontend sends `X-API-Key` but `require_auth` is extended without the new header check; all API calls return 401.
**Why it happens:** AUTH-02 backend and AUTH-03 frontend must ship together in the correct order.
**How to avoid:** Plan AUTH-02 (backend extension) before AUTH-03 (frontend). The existing `Authorization: Bearer` path must remain functional until AUTH-03 ships — since the extension is additive, this is automatic.

### Pitfall 8: YAML dump reorders keys or loses block style
**What goes wrong:** `yaml.dump` with default settings writes flow-style dicts `{key: val}` instead of block style, or alphabetizes keys, making the config file harder to read.
**How to avoid:** Always pass `default_flow_style=False` to `yaml.dump`. Do not pass `sort_keys=True` (let existing key order be preserved by Python dict insertion order, Python 3.7+).

---

## Code Examples

### Token Generation and Write-Back [ASSUMED — pattern derived from codebase conventions]

```python
# quirk/cli/token_cmd.py
import argparse
import secrets
import sys
import yaml

def run_token(argv):
    parser = argparse.ArgumentParser(prog="quirk token", description="Dashboard API token management")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("generate", help="Generate a new API token and write to config")
    sub.add_parser("rotate", help="Rotate the API token (overwrites; old token stops working immediately)")
    sub.add_parser("show", help="Show the current API token from config")
    args = parser.parse_args(argv)

    config_path = args.config

    if args.action in ("generate", "rotate"):
        token = secrets.token_urlsafe(32)
        _write_token_to_config(config_path, token)
        print(f"Token written to {config_path}. Set QUIRK_API_TOKEN={token} or restart the server.")
        sys.exit(0)

    if args.action == "show":
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            token = (raw.get("security") or {}).get("api_token", "")
        except FileNotFoundError:
            print(f"Config file not found: {config_path}", file=sys.stderr)
            sys.exit(1)
        import os
        env_token = os.environ.get("QUIRK_API_TOKEN", "")
        if env_token:
            print("Note: QUIRK_API_TOKEN env var is set and takes precedence over the YAML value.")
        print(token if token else "(no token configured)")
        sys.exit(0)


def _write_token_to_config(config_path: str, token: str) -> None:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raw = {}
    if not isinstance(raw.get("security"), dict):
        raw["security"] = {}
    raw["security"]["api_token"] = token
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, default_flow_style=False, allow_unicode=True)
```

### require_auth Extension [VERIFIED: auth.py:34 read + pattern derived]

```python
def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    configured = _get_configured_token()
    if not configured:
        return  # D-02: auth disabled

    # AUTH-02: X-API-Key header check (precedence per CONTEXT.md)
    x_api_key = request.headers.get("X-API-Key", "")
    if x_api_key:
        if hmac.compare_digest(x_api_key, configured):
            return
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))

    # Existing bearer path (preserved unchanged)
    if credentials is None:
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
    if not hmac.compare_digest(credentials.credentials, configured):
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
```

### fetchApi Token Switch [VERIFIED: lib/api.ts read + pattern derived]

```typescript
// Change _resolveToken() from:
function _resolveToken(): string {
  return window.__QUIRK_CONFIG__?.apiToken ?? ""
}
// To:
function _resolveToken(): string {
  try {
    return localStorage.getItem("quirk_api_token") ?? ""
  } catch {
    return ""  // SSR/test environments where localStorage is unavailable
  }
}

// Change header injection from Authorization: Bearer to X-API-Key:
if (token) {
  headers["X-API-Key"] = token
}
```

### TRANS-04 Score Section Fix [VERIFIED: executive.py:204-238 read]

```python
# In build_exec_markdown, when exec_content is not None:
# BEFORE (reads score_raw):
lines.append(f"**Score:** **{score_raw['score']}/100**  \n**Rating:** **{score_raw['rating']}**")
# ...
subscores = score_raw.get("subscores") or {}
# ...
raw_sum = exec_content.raw_sum if exec_content is not None else ...
lines.append(f"**Rollup:** {raw_sum} ÷ 1.5 = **{score_raw['score']} / 100**")

# AFTER (reads exec_content):
lines.append(f"**Score:** **{exec_content.score_total}/100**  \n**Rating:** **{exec_content.score_band}**")
# ...
subscores = exec_content.subscores
# ...
lines.append(f"**Rollup:** {exec_content.raw_sum} ÷ 1.5 = **{exec_content.score_total} / 100**")
```

The `exec_content is None` backward-compat block (lines 192-202 area) remains reading `score_raw` — this path is never invoked from `writer.py` but exists for external callers that don't build `exec_content`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No auth on GET routes | Auth on all data routes via router-level Depends() | Phase 58 | All reads protected |
| Server-injected `window.__QUIRK_CONFIG__.apiToken` | localStorage + X-API-Key (post-AUTH-03) | Phase 102 | Client-controls token; works across tab sessions |
| CLI score re-derived locally in executive.py | Score sourced from exec_content (post-TRANS-04) | Phase 102 | Closes v5.2 tech debt; all surfaces guaranteed numerically identical |

**Deprecated / outdated:**
- `window.__QUIRK_CONFIG__.apiToken` path in `lib/api.ts`: removed by AUTH-03 (or demoted to secondary fallback if the serve command still injects it for non-auth flows).
- Locally-computed `score_raw['score']` reads in score section of `build_exec_markdown`: replaced by `exec_content.score_total`.

---

## Open Questions

1. **`quirk token show` — masked vs full output**
   - What we know: CONTEXT.md does not specify; "show" implies retrieval.
   - What's unclear: Should the token be printed in full (useful for copy-paste) or masked (security theater since the user runs the command)?
   - Recommendation: Print in full (the user controls their terminal; masking adds friction with no real security benefit for a local tool).

2. **`window.__QUIRK_CONFIG__` — remove or fallback?**
   - What we know: `quirk serve` currently injects `apiToken` into the HTML via `__QUIRK_CONFIG__`. After AUTH-03, `fetchApi` reads localStorage instead.
   - What's unclear: Does the serve command still need to inject the token? If auth is enabled, the user must enter the token in the login form — so no server-side injection is needed.
   - Recommendation: Remove the `window.__QUIRK_CONFIG__.apiToken` injection from `quirk serve`. Keep `__QUIRK_CONFIG__` for non-auth config (if any) but strip the `apiToken` field.

3. **401-while-authenticated hook pattern**
   - What we know: UI-SPEC.md requires treating a 401 while authenticated as a logout trigger.
   - What's unclear: Whether to implement this in `fetchApi()` (requires access to AuthContext, creating a circular dependency) or in each hook.
   - Recommendation: Implement in individual hooks (`useScanData`, `useTrendsData`, etc.) using a shared utility `handleAuthError(status, logout)`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | token_cmd.py `secrets` | ✓ | existing | — |
| PyYAML | config write-back | ✓ | existing dep | — |
| Node.js + npm | `npm run build` in src/dashboard/ | ✓ | existing | — |
| pytest | test suite | ✓ | existing | — |

Step 2.6: No missing dependencies. All tools already present in the development environment.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_token_cmd.py tests/test_api_auth.py tests/test_cross_surface_parity.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | `quirk token generate` writes token to YAML security.api_token | unit | `pytest tests/test_token_cmd.py::test_token_generate_writes_config -x` | ❌ Wave 0 |
| AUTH-01 | `quirk token rotate` overwrites old token | unit | `pytest tests/test_token_cmd.py::test_token_rotate_overwrites -x` | ❌ Wave 0 |
| AUTH-01 | `quirk token show` prints configured token | unit | `pytest tests/test_token_cmd.py::test_token_show -x` | ❌ Wave 0 |
| AUTH-01 | `quirk token generate` does not clobber other config keys | unit | `pytest tests/test_token_cmd.py::test_token_generate_preserves_other_keys -x` | ❌ Wave 0 |
| AUTH-02 | `X-API-Key` header accepted as valid auth | unit | `pytest tests/test_api_auth.py::test_x_api_key_accepted -x` | ❌ Wave 0 |
| AUTH-02 | `X-API-Key` takes precedence over bearer when both present | unit | `pytest tests/test_api_auth.py::test_x_api_key_precedence_over_bearer -x` | ❌ Wave 0 |
| AUTH-02 | Wrong `X-API-Key` returns 401 | unit | `pytest tests/test_api_auth.py::test_invalid_x_api_key_returns_401 -x` | ❌ Wave 0 |
| AUTH-02 | All data-returning GET routes (non-health) have require_auth | CI gate | `pytest tests/test_api_auth.py::test_all_data_routes_have_auth_dependency -x` | ❌ Wave 0 |
| AUTH-03 | fetchApi injects X-API-Key from localStorage | unit | vitest (frontend) — manual UAT for actual browser behavior | N/A |
| AUTH-03 | Login form visible on 401 probe, hidden on 200 | manual UAT | human visual confirmation | N/A |
| AUTH-03 | Logout clears localStorage and returns to login | manual UAT | human visual confirmation | N/A |
| TRANS-04 | CLI executive markdown score_total matches exec_content | unit | `pytest tests/test_cross_surface_parity.py::test_score_parity_across_surfaces -x` | ❌ Wave 0 |
| TRANS-04 | CLI band/subscores match exec_content | unit | included in test above | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_token_cmd.py tests/test_api_auth.py tests/test_cross_surface_parity.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_token_cmd.py` — covers AUTH-01 (generate, rotate, show, no-clobber)
- [ ] New test functions in `tests/test_api_auth.py` — covers AUTH-02 X-API-Key acceptance + route-coverage gate extended to GET routes
- [ ] New test function in `tests/test_cross_surface_parity.py` — covers TRANS-04 score parity
- [ ] Framework install: not required — pytest already present

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `secrets.token_urlsafe(32)` for generation; `hmac.compare_digest` for verification |
| V3 Session Management | yes | localStorage token; logout clears storage; 401 while authenticated triggers logout |
| V4 Access Control | yes | All data-returning routes gated by `require_auth`; CI gate enforces coverage |
| V5 Input Validation | yes | `request.headers.get("X-API-Key", "")` — raw string, no parsing needed; compare_digest is constant-time |
| V6 Cryptography | yes | `secrets.token_urlsafe(32)` = 32 bytes of CSPRNG = 256 bits entropy; URL-safe base64 encoding |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token in browser history (URL param) | Information Disclosure | Header injection only — never query param |
| Token visible in terminal history | Information Disclosure | `quirk token show` acceptable (local tool); document risk |
| Timing oracle on token comparison | Spoofing | `hmac.compare_digest` (constant-time) for all comparisons |
| Config write-back race condition | Tampering | YAML file write is single-threaded CLI operation; not a concurrent API path |
| Token in localStorage XSS-accessible | Tampering | Single-tenant local use case; acceptable per CONTEXT.md scope |
| Empty X-API-Key accepted | Spoofing | `if x_api_key:` guard prevents comparing empty string against configured token |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `quirk token show` should print the full token (not masked) | Domain 1 | Low — can be changed to masked; UX only |
| A2 | `window.__QUIRK_CONFIG__.apiToken` injection from `quirk serve` can be removed (not a dependency for other features) | Domain 3 | Low — if other features rely on it, keep as fallback in _resolveToken |
| A3 | 401-while-authenticated handling should be in individual hooks, not in fetchApi | Domain 3 | Low — implementation detail; either approach works |
| A4 | `GET /api/scans` is the correct auth probe (not `/api/health`) | Domain 3 | High — if health is used, auth-disabled passthrough works but token validation does not; login never shows |

---

## Sources

### Primary (HIGH confidence)

- `quirk/dashboard/api/middleware/auth.py` — verified require_auth signature, hmac.compare_digest usage, _get_configured_token priority
- `quirk/config.py` — verified SecurityCfg.api_token field (line 329), load_config signature, no save_config function
- `quirk/reports/executive.py` — verified score_raw reads in score section (lines 204, 228, 238), exec_content usage pattern
- `quirk/reports/content_model.py` — verified ExecContent.score_total, score_band, subscores, raw_sum fields
- `quirk/reports/writer.py` — verified exec_content is always passed to build_exec_markdown; compat wrapper dict shape
- `quirk/dashboard/api/routes/*.py` — verified all 7 data-returning routers have router-level require_auth; health.py is exempt
- `quirk/dashboard/api/app.py` — verified create_app() factory, router registration, app.routes introspection point
- `src/dashboard/src/lib/api.ts` — verified current token resolution path (window.__QUIRK_CONFIG__) and header injection (Authorization: Bearer)
- `src/dashboard/src/App.tsx` — verified current provider tree structure and route tree
- `src/dashboard/src/components/sidebar.tsx` — verified current structure and bottom section (ModeToggle div) where logout goes
- `tests/test_api_auth.py` — verified existing D-06 gate pattern for mutating routes (test_all_mutating_routes_have_auth_dependency)
- `tests/test_cross_surface_parity.py` — verified existing parity test structure and fixture shape
- `.planning/phases/102-dashboard-auth-ux-score-tax/102-UI-SPEC.md` — verified login page component spec, interaction contract, files affected
- `run_scan.py` lines 364-494 — verified interception block pattern for all existing subcommands

### Secondary (MEDIUM confidence)

- `.planning/phases/102-dashboard-auth-ux-score-tax/102-CONTEXT.md` — user decisions (locked)
- `.planning/REQUIREMENTS.md` — AUTH-01..03, TRANS-04 requirement text

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are existing codebase dependencies; no new deps introduced
- Architecture: HIGH — all seams verified by codebase read; no speculation
- Pitfalls: HIGH — local-import shadow trap and config clobber are project-documented patterns; YAML round-trip verified against jobs.py precedent

**Research date:** 2026-05-25
**Valid until:** 2026-06-24 (stable codebase; 30-day window)

---

## RESEARCH COMPLETE

**Phase:** 102 — Dashboard Auth UX + Score Tax
**Confidence:** HIGH

### Key Findings

- **No `save_config` exists** — token_cmd.py must implement its own YAML round-trip (`yaml.safe_load` → update `raw["security"]["api_token"]` → `yaml.dump`). The `jobs.py:101` YAML write precedent confirms the pattern.
- **All data routes already protected** — no unprotected data-returning route found. The AUTH-02 CI gate extends the existing D-06 test from mutating-only to all routes.
- **`exec_content.score_total/score_band/subscores/raw_sum` already exists** — ExecContent already carries all four score fields. TRANS-04 is a targeted 3-line substitution in `build_exec_markdown`.
- **Auth probe must use a protected route** — `/api/health` is auth-exempt and cannot distinguish auth states; `GET /api/scans` is the correct probe.
- **`fetchApi` token injection requires two changes** — both `_resolveToken()` (localStorage vs window.__QUIRK_CONFIG__) and the header name (`X-API-Key` vs `Authorization: Bearer`).

### File Created

`.planning/phases/102-dashboard-auth-ux-score-tax/102-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| AUTH-01 CLI registration | HIGH | Interception block pattern verified in run_scan.py; YAML write precedent in jobs.py |
| AUTH-02 middleware extension | HIGH | auth.py fully read; route audit complete; test introspection pattern verified |
| AUTH-03 frontend | HIGH | App.tsx, sidebar.tsx, lib/api.ts fully read; UI-SPEC.md is locked |
| TRANS-04 score refactor | HIGH | executive.py score section lines identified; ExecContent fields verified |

### Open Questions

- `quirk token show` — masked vs full output (recommend full; planner decides)
- `window.__QUIRK_CONFIG__.apiToken` — remove injection from `quirk serve` or keep as fallback (recommend remove)
- 401-while-authenticated handling pattern — fetchApi callback vs per-hook check (recommend per-hook)

### Ready for Planning

Research complete. Planner can now create PLAN.md files for AUTH-01, AUTH-02+route-coverage, TRANS-04, and AUTH-03 (frontend).
