# Phase 102: Dashboard Auth UX + Score Tax - Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 12 (4 new, 8 modified)
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/cli/token_cmd.py` | CLI command module | request-response (YAML I/O) | `quirk/cli/schedule_cmd.py` | exact |
| `quirk/dashboard/api/middleware/auth.py` | middleware | request-response | itself (extend in-place) | exact |
| `tests/test_token_cmd.py` | test | unit | `tests/test_api_auth.py` | role-match |
| `tests/test_api_auth.py` (extend) | test | unit | itself (extend in-place) | exact |
| `tests/test_cross_surface_parity.py` (extend) | test | unit | itself (extend in-place) | exact |
| `quirk/reports/executive.py` (TRANS-04) | report renderer | transform | itself (3-line substitution) | exact |
| `src/dashboard/src/context/AuthProvider.tsx` | React context provider | event-driven | `src/dashboard/src/context/ScanProvider.tsx` + `ScanContext.tsx` | exact |
| `src/dashboard/src/pages/login.tsx` | React page component | request-response | `src/dashboard/src/App.tsx` + UI-SPEC.md | role-match |
| `src/dashboard/src/components/sidebar.tsx` (extend) | React component | event-driven | itself (extend in-place) | exact |
| `src/dashboard/src/App.tsx` (extend) | React root | event-driven | itself (extend in-place) | exact |
| `src/dashboard/src/lib/api.ts` (extend) | frontend utility | request-response | itself (extend in-place) | exact |
| `run_scan.py` (interception block) | CLI entrypoint | request-response | itself — existing interception blocks at lines 464-494 | exact |

---

## Pattern Assignments

### `quirk/cli/token_cmd.py` (CLI command module, YAML I/O)

**Analog:** `quirk/cli/schedule_cmd.py`

**Imports pattern** (schedule_cmd.py lines 1-18):
```python
from __future__ import annotations

import argparse
import os
import sys

from quirk.errors import format_error
```
For token_cmd.py, the minimal set is:
```python
from __future__ import annotations

import argparse
import os
import secrets
import sys
import yaml
```
All imports at module scope unconditionally — never conditional inside a function branch (local-import shadow trap per project memory `feedback_local_import_shadow_trap.md`).

**run_* entrypoint pattern** (schedule_cmd.py lines 204-255):
```python
def run_schedule(argv: list[str]) -> None:
    """Main entrypoint for `quirk schedule` subcommands.

    argv = sys.argv[2:] — does NOT include 'quirk' or 'schedule'.
    """
    console = Console()

    parser = argparse.ArgumentParser(
        prog="quirk schedule",
        description="Manage scheduled scans (Phase 63 SCHED-01)",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    # --- add ---
    add_parser = subparsers.add_parser("add", help="Add a new scheduled scan")
    add_parser.add_argument("--config", default=None, help="...")

    args = parser.parse_args(argv)

    if args.action == "add":
        _cmd_add(args, console)
    elif args.action == "list":
        _cmd_list(args, console)
    ...
```
For token_cmd.py, `run_token(argv: list[str]) -> None` follows the same shape: one `ArgumentParser(prog="quirk token")`, one `add_subparsers(dest="action", required=True)`, three `add_parser` calls ("generate", "rotate", "show"), one `--config` argument added to each sub-parser (default `"config.yaml"`), then `if args.action ==` dispatch.

**YAML round-trip write-back pattern** (jobs.py lines 99-101 — the only existing YAML write in the codebase):
```python
config_path = str(output_dir / "config.yaml")
with open(config_path, "w") as fh:
    yaml.dump(config, fh, default_flow_style=False)
```
For token_cmd.py, the full-safe round-trip pattern (must NOT write a partial dict):
```python
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
Critical: always `yaml.safe_load` the full file first, update only `raw["security"]["api_token"]`, then `yaml.dump(raw, ...)`. Never write a partial dict — this clobbers other config keys (Pitfall 2 in RESEARCH.md).

**Token generation** (no codebase analog — stdlib pattern):
```python
token = secrets.token_urlsafe(32)
```

**show subcommand** — read directly from YAML (NOT via `_get_configured_token()`) so operator sees persisted value. Print note when `QUIRK_API_TOKEN` env var is also set (Pitfall 3 in RESEARCH.md):
```python
if args.action == "show":
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        token = (raw.get("security") or {}).get("api_token", "")
    except FileNotFoundError:
        print(f"Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    env_token = os.environ.get("QUIRK_API_TOKEN", "")
    if env_token:
        print("Note: QUIRK_API_TOKEN env var is set and takes precedence over the YAML value.")
    print(token if token else "(no token configured)")
    sys.exit(0)
```

---

### `run_scan.py` — interception block (lines ~484-494 insertion point)

**Analog:** existing interception blocks at lines 464-494

**Insertion pattern** (run_scan.py lines 464-468 — `schedule` block as exact template):
```python
# --- schedule subcommand: intercept before scan argparse (Phase 63 SCHED-01) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "schedule":
    from quirk.cli.schedule_cmd import run_schedule
    run_schedule(_sys.argv[2:])
    return
```
New token block follows the same structure, inserted after `analyze-token` (line 488) and before `errors` (line 491):
```python
# --- token subcommand: intercept before scan argparse (Phase 102 AUTH-01) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "token":
    from quirk.cli.token_cmd import run_token
    run_token(_sys.argv[2:])
    return
```

---

### `quirk/dashboard/api/middleware/auth.py` (middleware, extend in-place)

**Analog:** itself — full file (51 lines)

**Current full file** (auth.py lines 1-51):
```python
"""Bearer token auth dependency for the dashboard API — Phase 58 / CR-03 / HARDEN-API-01."""
from __future__ import annotations

import hmac
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from quirk.errors import format_error


def _get_configured_token() -> str:
    """Priority: QUIRK_API_TOKEN env var -> security.api_token YAML field -> ''.

    Returns empty string when auth is disabled (D-02).
    Env var wins when both are set (D-01).
    """
    if val := os.environ.get("QUIRK_API_TOKEN"):
        return val
    try:
        from quirk.config import load_config
        cfg = load_config()
        return cfg.security.api_token or ""
    except Exception:
        return ""


_bearer = HTTPBearer(auto_error=False)


def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    configured = _get_configured_token()
    if not configured:
        return  # D-02: auth disabled
    if credentials is None:
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
    if not hmac.compare_digest(credentials.credentials, configured):  # D-03
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
```

**AUTH-02 extension pattern** — insert X-API-Key check before the existing bearer check. The `request: Request` parameter is already in the signature. Both operands to `hmac.compare_digest` must be `str` — no `.encode()` on either side (Pitfall 1 in RESEARCH.md):
```python
def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    configured = _get_configured_token()
    if not configured:
        return  # D-02: auth disabled

    # AUTH-02: check X-API-Key header first (precedence per CONTEXT.md D-01)
    x_api_key = request.headers.get("X-API-Key", "")
    if x_api_key:
        if hmac.compare_digest(x_api_key, configured):
            return  # valid X-API-Key
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))

    # Fallback to bearer (existing path — preserved unchanged)
    if credentials is None:
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
    if not hmac.compare_digest(credentials.credentials, configured):  # D-03
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
```
No import additions required — `Request` is already imported.

---

### `tests/test_token_cmd.py` (unit test, new file)

**Analog:** `tests/test_api_auth.py`

**Test file header and fixture pattern** (test_api_auth.py lines 1-51):
```python
"""Auth + CSRF + rate-limit + CORS + GET-route auth + pdf port-clamp integration tests.

Phase 58 Plan 04 — HARDEN-API-01/02/03/05
...
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
...
```
For test_token_cmd.py:
```python
"""Phase 102 AUTH-01 — token CLI: generate / rotate / show / no-clobber."""
from __future__ import annotations

import os
import pytest
import yaml

from quirk.cli.token_cmd import run_token, _write_token_to_config
```

**Fixture pattern using `tmp_path`** (mirrors test_cross_surface_parity.py's use of `tmp_path`):
```python
def _make_config(tmp_path, extra: dict = None) -> str:
    """Write a minimal config.yaml with optional extra keys."""
    data = {
        "assessment": {"name": "test"},
        "security": {"api_token": ""},
    }
    if extra:
        data.update(extra)
    path = str(tmp_path / "config.yaml")
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    return path
```

**Test structure** — four tests required (from RESEARCH.md Validation Architecture):
- `test_token_generate_writes_config` — run_token(["generate", "--config", path]); reload YAML; assert `security.api_token` is non-empty
- `test_token_rotate_overwrites` — generate twice; assert second token != first
- `test_token_show` — write known token to YAML; run_token(["show", "--config", path]); assert token in stdout (use `capsys`)
- `test_token_generate_preserves_other_keys` — config has `assessment` + `targets` keys; after generate, reload and assert those keys still present

---

### `tests/test_api_auth.py` — extend with AUTH-02 tests

**Analog:** itself — existing `test_all_mutating_routes_have_auth_dependency` (lines 303-338) as the template

**Route-coverage gate extension pattern** (test_api_auth.py lines 303-338):
```python
def test_all_mutating_routes_have_auth_dependency(monkeypatch):
    """D-06 gate: every POST/PUT/DELETE/PATCH (except /api/health) must have require_auth."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    from fastapi.routing import APIRoute
    from quirk.dashboard.api.middleware.auth import require_auth

    app = create_app()
    mutating_methods = {"POST", "PUT", "DELETE", "PATCH"}
    violations: list[str] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        route_methods = route.methods or set()
        if not (route_methods & mutating_methods):
            continue
        if route.path in {"/api/health", "/api/health/"}:
            continue
        dep_callables = {dep.dependency for dep in route.dependencies}
        if require_auth not in dep_callables:
            violations.append(
                f"{sorted(route_methods & mutating_methods)} {route.path} — missing require_auth"
            )

    assert violations == [], (
        "The following mutating routes are missing require_auth (D-06 violation):\n"
        + "\n".join(violations)
    )
```
New ALL-routes gate follows the same introspection pattern but removes the mutating-methods filter:
```python
def test_all_data_routes_have_auth_dependency(monkeypatch):
    """AUTH-02 gate: every route except /api/health must have require_auth."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    from fastapi.routing import APIRoute
    from quirk.dashboard.api.middleware.auth import require_auth

    app = create_app()
    violations: list[str] = []
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

**X-API-Key functional tests** — use the existing `authed_client` fixture pattern (lines 67-71):
```python
@pytest.fixture
def authed_client(monkeypatch):
    """TestClient with QUIRK_API_TOKEN=test-token — auth enabled."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _app, tc = _app_with_db()
    return _app, tc
```
New tests send `X-API-Key: test-token` header on a GET route (e.g., `/api/scans`) and assert `!= 401`. Wrong key asserts `== 401`. Precedence test sends both `X-API-Key` and `Authorization: Bearer wrong-token` and asserts `!= 401` (X-API-Key wins).

---

### `tests/test_cross_surface_parity.py` — extend with TRANS-04 score test

**Analog:** itself — `test_narrative_content_parity` (lines 91-160) as the exact template

**Shared fixture shape** (test_cross_surface_parity.py lines 27-84 — reuse `_SCORE_RAW`, `_FINDINGS`, `_make_minimal_cfg`):
```python
_SCORE_RAW = {
    "score": 42,
    "rating": "FAIR",
    "subscores": {
        "hygiene": 10, "modern_tls": 7, "identity_trust": 11,
        "agility_signals": 6, "data_at_rest": 5, "data_in_motion": 3,
    },
    "drivers": [...],
}
```

**New score parity test** — same build + CLI render pattern as existing tests:
```python
def test_score_parity_across_surfaces(tmp_path):
    """TRANS-04: score_total, score_band, and subscores numerically identical in CLI vs exec_content."""
    from quirk.reports.content_model import build_exec_content
    from quirk.reports.executive import build_exec_markdown

    exec_content = build_exec_content(
        score_raw=_SCORE_RAW,
        findings=_FINDINGS,
        roadmap_items=_ROADMAP_ITEMS_RAW,
    )
    cfg = _make_minimal_cfg()
    cli_output: str = build_exec_markdown(
        cfg=cfg, endpoints=[], findings=_FINDINGS, exec_content=exec_content,
    )

    assert str(exec_content.score_total) in cli_output, ...
    assert exec_content.score_band in cli_output, ...
    for key, val in exec_content.subscores.items():
        assert str(val) in cli_output, ...
```

---

### `quirk/reports/executive.py` — TRANS-04 score section (lines 203-238)

**Analog:** itself — the `exec_content is not None` narrative branch (lines 184-201) as the template for how the already-extended path consumes `exec_content` fields

**Current score section that needs changing** (executive.py lines 203-238):
```python
lines.append("## Quantum Readiness Score")
lines.append(f"**Score:** **{score_raw['score']}/100**  \n**Rating:** **{score_raw['rating']}**")
...
subscores = score_raw.get("subscores") or {}
...
for key, label in _SUBSCORE_LABELS:
    lines.append(f"| {label} | {subscores.get(key, '—')} | /25 |")
raw_sum = (
    exec_content.raw_sum
    if exec_content is not None
    else sum(subscores.get(k, 0) for k, _ in _SUBSCORE_LABELS)
)
lines.append(f"**Rollup:** {raw_sum} ÷ 1.5 = **{score_raw['score']} / 100**")
```

**Pattern for the exec_content-path replacement** — mirror how narrative (lines 184-201) gates on `exec_content is not None`:
```python
# Inside the exec_content is not None branch:
lines.append("## Quantum Readiness Score")
lines.append(
    f"**Score:** **{exec_content.score_total}/100**  \n"
    f"**Rating:** **{exec_content.score_band}**"
)
...
subscores = exec_content.subscores  # replaces: score_raw.get("subscores") or {}
...
for key, label in _SUBSCORE_LABELS:
    lines.append(f"| {label} | {subscores.get(key, '—')} | /25 |")
lines.append(f"**Rollup:** {exec_content.raw_sum} ÷ 1.5 = **{exec_content.score_total} / 100**")
```
The backward-compat `exec_content is None` path (lines 192-202) keeps reading `score_raw` — writer.py always passes exec_content, so this path only affects external callers.

**ExecContent fields verified** (content_model.py lines 73-77):
```python
score_total: int
score_band: str
subscores: Dict[str, Any]
raw_sum: int
```

---

### `src/dashboard/src/context/AuthProvider.tsx` (React context provider, new file)

**Analog:** `src/dashboard/src/context/ScanContext.tsx` + `ScanProvider.tsx`

**Context shape pattern** (ScanContext.tsx lines 1-11):
```typescript
import { createContext } from "react"

interface ScanContextValue {
  selectedScanId: string | null
  setSelectedScanId: (id: string | null) => void
}

export const ScanContext = createContext<ScanContextValue>({
  selectedScanId: null,
  setSelectedScanId: () => {},
})
```

**Provider component pattern** (ScanProvider.tsx lines 1-12):
```typescript
import { useState } from "react"
import type { ReactNode } from "react"
import { ScanContext } from "./ScanContext"

export function ScanProvider({ children }: { children: ReactNode }) {
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null)
  return (
    <ScanContext.Provider value={{ selectedScanId, setSelectedScanId }}>
      {children}
    </ScanContext.Provider>
  )
}
```

**AuthProvider adaptation** — combine context + provider in one file (AuthProvider.tsx), with `useEffect` for the probe on mount. State type per UI-SPEC.md:
```typescript
type AuthStatus = "loading" | "authenticated" | "unauthenticated"
interface AuthState {
  status: AuthStatus
  setToken: (token: string) => void
  logout: () => void
}
```
Provider initializes `status: "loading"`, fires `GET /api/scans` with stored localStorage token as `X-API-Key`, then transitions to `"authenticated"` or `"unauthenticated"`. Export a `useAuth()` hook via `useContext(AuthContext)`.

The probe must target `/api/scans` (a protected route) NOT `/api/health` (auth-exempt, always 200 — Pitfall 6 in RESEARCH.md).

---

### `src/dashboard/src/pages/login.tsx` (React page component, new file)

**Analog:** UI-SPEC.md component inventory + existing page files for import conventions

**Import conventions** (from sidebar.tsx and App.tsx):
```typescript
import { ... } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
```

**UI-SPEC.md component structure** (login.tsx lines 136-170 of UI-SPEC):
- Outer: `<div className="flex min-h-screen items-center justify-center bg-background">`
- Card: `w-full max-w-sm shadow-lg`
- CardHeader: wordmark (`text-accent font-semibold text-base tracking-widest font-mono`) + CardTitle + CardDescription
- CardContent: `<form aria-label="Dashboard login" onSubmit={...} className="space-y-4">`
  - Label + Input (`type="password"` `id="token-input"` `autoFocus` `autoComplete="current-password"`)
  - Error `<p>` always in DOM (`role="alert"` `aria-live="polite"` `text-destructive`), empty string when no error
  - Submit Button (`type="submit"` `w-full`) — "Unlock Dashboard"
- CardFooter: `<p className="text-xs text-muted-foreground">` with `<code className="font-mono">quirk token generate</code>`

**Interaction**: on submit, call `setToken` from `useAuth()` after a successful probe. On 401, clear input value and call `inputRef.current?.focus()`.

---

### `src/dashboard/src/components/sidebar.tsx` — extend logout control

**Analog:** itself — the ModeToggle div (lines 121-124) and the nav Tooltip pattern (lines 90-113)

**Insertion point** (sidebar.tsx lines 121-126 — after ModeToggle, before closing `</aside>`):
```tsx
{/* Theme toggle at bottom */}
<div className="px-2 py-4 border-t border-border">
  <ModeToggle />
</div>
```

**Logout control pattern** (follows the collapsed/expanded Tooltip pattern from nav items):
```tsx
import { LogOut } from "lucide-react"        // add to existing lucide-react import
import { Separator } from "@/components/ui/separator"  // add import
import { useAuth } from "@/context/AuthProvider"       // add import

// Inside Sidebar():
const { logout } = useAuth()

// Insertion after ModeToggle div:
<Separator />
<div className="px-2 py-2">
  <Tooltip>
    <TooltipTrigger asChild>
      <Button
        variant="ghost"
        size="icon"
        onClick={logout}
        aria-label="Sign out"
        className="w-full lg:hidden"
      >
        <LogOut className="h-4 w-4" />
      </Button>
    </TooltipTrigger>
    <TooltipContent side="right" className="lg:hidden">Sign out</TooltipContent>
  </Tooltip>
  <Button
    variant="ghost"
    onClick={logout}
    className="w-full justify-start gap-2 hidden lg:flex"
  >
    <LogOut className="h-4 w-4" />
    Sign out
  </Button>
</div>
```
`LogOut` is not currently in the lucide-react import block (line 4-19 of sidebar.tsx); it must be added. `Separator` must also be added.

---

### `src/dashboard/src/App.tsx` — wrap in AuthProvider + mount guard

**Analog:** itself — lines 1-65

**Current provider tree** (App.tsx lines 27-64):
```tsx
<ThemeProvider defaultTheme="dark" storageKey="quirk-ui-theme">
  <ScanProvider>
    <QRAMMProvider>
      <TooltipProvider>
        <BrowserRouter>
          <div className="flex min-h-screen bg-background text-foreground">
            <Sidebar />
            <main ...>...</main>
          </div>
        </BrowserRouter>
      </TooltipProvider>
    </QRAMMProvider>
  </ScanProvider>
</ThemeProvider>
```

**AUTH-03 modification** — insert `AuthProvider` between `ThemeProvider` and `ScanProvider` (ScanProvider/QRAMMProvider make API calls that need auth; they must be inside AuthProvider). Replace the unconditional `<Sidebar>` + `<main>` tree with a guard:
```tsx
import { AuthProvider, useAuth } from "@/context/AuthProvider"
import { LoginPage } from "@/pages/login"

function AppShell() {
  const { status } = useAuth()
  if (status === "loading") return <div className="min-h-screen bg-background" />
  if (status === "unauthenticated") return <LoginPage />
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar />
      <main ...>...</main>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="quirk-ui-theme">
      <AuthProvider>
        <ScanProvider>
          <QRAMMProvider>
            <TooltipProvider>
              <BrowserRouter>
                <AppShell />
              </BrowserRouter>
            </TooltipProvider>
          </QRAMMProvider>
        </ScanProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
```

---

### `src/dashboard/src/lib/api.ts` — localStorage token + X-API-Key header

**Analog:** itself — lines 1-73

**Current `_resolveToken`** (api.ts lines 29-35):
```typescript
function _resolveToken(): string {
  try {
    return window.__QUIRK_CONFIG__?.apiToken ?? ""
  } catch {
    return ""
  }
}
```

**Current header injection** (api.ts lines 67-69):
```typescript
const token = _resolveToken()
if (token) {
  headers["Authorization"] = `Bearer ${token}`
}
```

**AUTH-03 changes** — two targeted substitutions only; all other logic unchanged:
```typescript
// Change 1: _resolveToken reads localStorage
function _resolveToken(): string {
  try {
    return localStorage.getItem("quirk_api_token") ?? ""
  } catch {
    return ""  // SSR/test environments where localStorage is unavailable
  }
}

// Change 2: inject X-API-Key instead of Authorization: Bearer
const token = _resolveToken()
if (token) {
  headers["X-API-Key"] = token  // matches AUTH-02 server-side header name
}
```
The `window.__QUIRK_CONFIG__` global declaration (lines 14-20) may be left in place or removed; it is no longer used for auth.

---

## Shared Patterns

### Timing-Safe Token Comparison
**Source:** `quirk/dashboard/api/middleware/auth.py` lines 49-50
**Apply to:** `auth.py` extension (both X-API-Key and bearer paths) and `token_cmd.py` (no comparison needed there — comparison is server-side only)
```python
if not hmac.compare_digest(credentials.credentials, configured):  # D-03
    raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
```
Rule: both arguments to `hmac.compare_digest` must be `str`. Do not encode either side. The `if x_api_key:` guard before the compare prevents calling `compare_digest` on an empty string.

### FastAPI Route Introspection
**Source:** `tests/test_api_auth.py` lines 303-338
**Apply to:** New `test_all_data_routes_have_auth_dependency` in `test_api_auth.py`
```python
from fastapi.routing import APIRoute
from quirk.dashboard.api.middleware.auth import require_auth

app = create_app()
for route in app.routes:
    if not isinstance(route, APIRoute):
        continue
    dep_callables = {dep.dependency for dep in route.dependencies}
    if require_auth not in dep_callables:
        violations.append(...)
```
Router-level `dependencies=[Depends(require_auth)]` propagates to `route.dependencies` on each `APIRoute` — verified working in existing D-06 gate.

### YAML Write-Back (No Partial Dict)
**Source:** `quirk/dashboard/api/routes/jobs.py` line 101 (precedent); `quirk/cli/schedule_cmd.py` lines 60-62 (yaml.safe_load precedent)
**Apply to:** `token_cmd.py::_write_token_to_config`
Always: `yaml.safe_load(full_file)` → update single key → `yaml.dump(full_dict, default_flow_style=False, allow_unicode=True)`. Never write a partial dict.

### React Context + Provider Pattern
**Source:** `src/dashboard/src/context/ScanContext.tsx` (lines 1-11) + `ScanProvider.tsx` (lines 1-12)
**Apply to:** `AuthProvider.tsx`
```typescript
// Context: createContext with typed value + default
export const AuthContext = createContext<AuthState>({
  status: "loading",
  setToken: () => {},
  logout: () => {},
})

// Provider: useState + useEffect probe + Context.Provider wrapper
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading")
  useEffect(() => { /* probe GET /api/scans */ }, [])
  ...
  return <AuthContext.Provider value={...}>{children}</AuthContext.Provider>
}

// Hook: useContext shorthand
export function useAuth() { return useContext(AuthContext) }
```

### Error Formatting
**Source:** `quirk/errors.py` — `format_error("DASHBOARD-001")`
**Apply to:** `auth.py` X-API-Key rejection path (reuse same error code as bearer rejection — single error code for all 401s, per existing pattern)

### Module-Scope Imports Only (Local-Import Shadow Trap)
**Source:** Project memory `feedback_local_import_shadow_trap.md`; illustrated by `quirk/cli/schedule_cmd.py` lines 3-18 (all imports at top)
**Apply to:** `token_cmd.py` — import `secrets`, `yaml`, `os`, `sys`, `argparse` at module scope unconditionally. Never import conditionally inside a branch except for the lazy `load_config` import pattern in `auth.py` (which is a documented circular-import workaround, not a general pattern).

### npm Build Required After .tsx Changes
**Source:** Project memory `feedback_dashboard_build_required.md`; CONTEXT.md established patterns
**Apply to:** All AUTH-03 plans. Every plan touching `.tsx` files must include as a final task: `cd src/dashboard && npm run build`. FastAPI serves `quirk/dashboard/static/` which is the Vite build output; edits to `src/dashboard/src/` are invisible until rebuilt.

---

## No Analog Found

All files have direct analogs. No files in this phase require pattern inference from RESEARCH.md alone.

---

## Metadata

**Analog search scope:** `quirk/cli/`, `quirk/dashboard/`, `quirk/reports/`, `tests/`, `src/dashboard/src/`
**Files read for extraction:** 14 source files
**Pattern extraction date:** 2026-05-25
