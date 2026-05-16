# Phase 58: Dashboard API Hardening - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/dashboard/api/app.py` | config | request-response | `quirk/dashboard/api/app.py` (self) | exact — add middleware registrations |
| `quirk/dashboard/api/middleware/auth.py` | middleware | request-response | `quirk/dashboard/api/deps.py` + `quirk/util/url_allowlist.py` | role-match |
| `quirk/dashboard/api/middleware/csrf.py` | middleware | request-response | `quirk/dashboard/api/deps.py` | role-match |
| `quirk/dashboard/api/middleware/rate_limit.py` | middleware | request-response | `quirk/dashboard/api/deps.py` | role-match |
| `quirk/dashboard/api/routes/pdf.py` | route | request-response | `quirk/dashboard/api/routes/pdf.py` (self) | exact — add guards |
| `quirk/cli/init_cmd.py` | utility | request-response | `quirk/util/subprocess_input.py` | role-match |
| `quirk/util/targets.py` | utility | transform | `quirk/util/subprocess_input.py` + `quirk/util/url_allowlist.py` | exact |
| `quirk/config_template.yaml` | config | — | `quirk/config_template.yaml` (self) | exact — extend security block |
| `quirk/config.py` | config | — | `quirk/config.py` (self) | exact — extend SecurityCfg |
| `src/dashboard/src/lib/api.ts` | utility | request-response | `src/dashboard/src/hooks/useQRAMMSession.ts` | role-match |
| `tests/test_api_auth.py` | test | — | `tests/util/test_subprocess_input.py` | exact |
| `tests/test_init_cmd.py` | test | — | `tests/util/test_subprocess_input.py` | exact |

---

## Pattern Assignments

### `quirk/dashboard/api/app.py` — add middleware registrations

**Analog:** `quirk/dashboard/api/app.py` lines 32–88 (current factory); FastAPI CORSMiddleware docs pattern.

**Imports to add** (after existing imports):
```python
from fastapi.middleware.cors import CORSMiddleware
from quirk.dashboard.api.middleware.rate_limit import RateLimitMiddleware
```

**Middleware registration pattern** — insert before router includes (lines 39–44), in CORS→RateLimit order.
FastAPI applies `add_middleware` in reverse-registration order (last added = outermost), so register
rate limit first, CORS last so CORS executes outermost:
```python
def create_app() -> FastAPI:
    application = FastAPI(...)

    # Middleware — registered in reverse execution order (last-added = outermost).
    # Execution order: CORS → auth (Depends) → CSRF (Depends) → rate limit → route.
    application.add_middleware(
        RateLimitMiddleware,  # innermost middleware — runs after CORS
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:8512", "http://localhost:8512"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    application.include_router(health.router, prefix="/api")
    application.include_router(pdf.router, prefix="/api")
    ...
```

**Note:** Auth and CSRF are `Depends()`-injected at the router/route level, not `add_middleware()`,
so they do not appear in the factory. Health router is included WITHOUT auth dependency per D-05.

---

### `quirk/dashboard/api/middleware/auth.py` (middleware, request-response)

**Analog:** `quirk/dashboard/api/deps.py` (Depends pattern) + `quirk/util/url_allowlist.py` (ValidationResult + reason-code constants pattern).

**Imports pattern** — copy from `quirk/dashboard/api/deps.py` lines 1–9:
```python
from __future__ import annotations

import hmac
import os

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
```

**Config-loading pattern** — extend existing env-var-first convention from `quirk/dashboard/api/deps.py` lines 12–26:
```python
def _get_configured_token() -> str:
    """Priority: QUIRK_API_TOKEN env var → security.api_token YAML field → "".

    Returns empty string when auth is disabled (D-02).
    """
    if val := os.environ.get("QUIRK_API_TOKEN"):
        return val
    # YAML fallback: load config if present, return security.api_token
    # (same pattern as _default_db_path() checking QUIRK_DB_PATH first)
    return ""
```

**Core auth dependency pattern** — `Depends()` function, mirrors `get_db()` in `quirk/dashboard/api/deps.py` lines 29–49:
```python
_bearer = HTTPBearer(auto_error=False)

def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    """FastAPI Depends() — enforces bearer token when QUIRK_API_TOKEN is configured.

    Raises HTTPException 401 when auth is enabled and token is missing/wrong.
    Passthrough when auth is disabled (empty configured token).
    """
    configured = _get_configured_token()
    if not configured:
        return  # D-02: auth disabled, no token configured
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not hmac.compare_digest(credentials.credentials, configured):  # D-03
        raise HTTPException(status_code=401, detail="Authentication required")
```

**Reason-code constants pattern** — copy directly from `quirk/util/url_allowlist.py` lines 45–49:
```python
# No reason-code constants needed for auth — HTTP status codes carry the signal.
# Pattern: raise HTTPException directly (not ValidationResult) because this is
# a FastAPI dependency, not a util validator.
```

---

### `quirk/dashboard/api/middleware/csrf.py` (middleware, request-response)

**Analog:** `quirk/dashboard/api/deps.py` (Depends pattern).

**Core CSRF dependency pattern** — same `Depends()` shape as `require_auth`:
```python
from __future__ import annotations

from fastapi import HTTPException, Request

CSRF_HEADER = "X-Quirk-Request"


def require_csrf(request: Request) -> None:
    """FastAPI Depends() — requires X-Quirk-Request: 1 on mutating methods (D-07).

    Only enforced on POST/PUT/DELETE/PATCH. GET/HEAD/OPTIONS pass through.
    Missing header → 403 (distinguishes from 401 auth failure).
    """
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        if request.headers.get(CSRF_HEADER) != "1":
            raise HTTPException(
                status_code=403,
                detail=f"Missing CSRF header: {CSRF_HEADER}",
            )
```

**Wiring into routes** — applied as a router-level dependency to all mutating routes.
Pattern from `quirk/dashboard/api/routes/scan.py` lines 736–759 (router-level `Depends`):
```python
# In each mutating route file (pdf.py, qramm.py):
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf

router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
# OR per-route: @router.post("/...", dependencies=[Depends(require_auth), Depends(require_csrf)])
```

---

### `quirk/dashboard/api/middleware/rate_limit.py` (middleware, request-response)

**Analog:** No existing rate-limit middleware. Pattern: `BaseHTTPMiddleware` + stdlib-only token bucket (D-09/D-10).

**Imports and class skeleton** — BaseHTTPMiddleware is FastAPI built-in, zero new deps:
```python
from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque

from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_WINDOW_SECONDS = 60
_MAX_REQUESTS = 60
_MUTATING_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})
_EXEMPT_PATHS = frozenset({"/api/health"})


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-process sliding-window token bucket, 60 mutating req/min/IP (D-09/D-10).

    Thread-safe via a single threading.Lock around deque read-modify-write.
    Data structure: defaultdict(deque) mapping client_host → deque[float] of
    time.monotonic() timestamps within the current window.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._buckets: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        if request.method not in _MUTATING_METHODS or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        with self._lock:
            bucket = self._buckets[client_ip]
            # Trim expired entries
            cutoff = now - _WINDOW_SECONDS
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= _MAX_REQUESTS:
                oldest = bucket[0]
                retry_after = math.ceil(_WINDOW_SECONDS - (now - oldest))
                return Response(
                    content='{"detail":"Rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)

        return await call_next(request)
```

---

### `quirk/dashboard/api/routes/pdf.py` — port clamp + redirect guard

**Analog:** `quirk/dashboard/api/routes/pdf.py` lines 29–93 (self — extend existing function).

**Port clamp pattern** — insert after lines 46–52 (existing ValueError check), before `print_url` is constructed:
```python
    try:
        port = int(os.environ.get("QUIRK_SERVE_PORT", "8512"))
    except ValueError:
        return Response(
            content=json.dumps({"detail": "QUIRK_SERVE_PORT is not a valid integer."}).encode(),
            status_code=500,
            media_type="application/json",
        )

    # D-11: port range clamp — reject values outside safe ephemeral range
    if not (1024 <= port <= 65535):
        return Response(
            content=json.dumps(
                {"detail": "QUIRK_SERVE_PORT is out of allowed range (1024–65535)."}
            ).encode(),
            status_code=500,
            media_type="application/json",
        )
    print_url = f"http://127.0.0.1:{port}/print"
```

**Playwright redirect guard pattern** — insert inside `with sync_playwright() as p:` block, after `page = context.new_page()` (before `page.goto()`):
```python
                # D-12: abort navigations that resolve to non-loopback hosts
                _LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}

                def _abort_non_loopback(route):
                    from urllib.parse import urlparse
                    host = urlparse(route.request.url).hostname or ""
                    if host not in _LOOPBACK_HOSTS:
                        route.abort()
                    else:
                        route.continue_()

                page.route("**/*", _abort_non_loopback)
                page.goto(print_url, wait_until="networkidle", timeout=30_000)
```

**Error handling pattern** — reuse existing pattern from `quirk/dashboard/api/routes/pdf.py` lines 80–93:
```python
    except Exception as exc:
        msg = str(exc)
        # ... existing chromium error check ...
        return Response(
            content=json.dumps({"detail": f"PDF export failed: {msg}"}).encode(),
            status_code=500,
            media_type="application/json",
        )
```

---

### `quirk/cli/init_cmd.py` — path-traversal guard (CR-01)

**Analog:** `quirk/util/subprocess_input.py` lines 102–140 (`validate_repo_path`) — exact pattern for os.path.realpath + cwd-anchored check.

**Imports to add** to `quirk/cli/init_cmd.py` line 2:
```python
import os
import shutil
# add:
import sys
```

**Core guard pattern** — insert after `output_path = os.path.abspath(output_path)` (line 21), before `os.path.exists()` check. Mirrors `validate_repo_path` logic from `quirk/util/subprocess_input.py` lines 125–140:
```python
    output_path = os.path.abspath(output_path)

    # CR-01 / D-01: path-traversal guard — resolved path must descend from CWD.
    _cwd_real = os.path.realpath(os.getcwd())
    _out_real  = os.path.realpath(output_path)

    # Reject if resolved path does not start with CWD (handles symlink escapes too).
    if not _out_real.startswith(_cwd_real + os.sep) and _out_real != _cwd_real:
        _warn(
            f"Output path '{output_path}' resolves outside the current working directory. "
            "Absolute paths and symlinks escaping CWD are not allowed."
        )
        return

    # Reject explicit dotdot segments before resolution (defense-in-depth).
    if ".." in os.path.normpath(output_path).split(os.sep):
        _warn(f"Output path '{output_path}' contains path-traversal segments (..).")
        return
```

**Warning style** — copy `_warn` lambda pattern from `quirk/cli/init_cmd.py` lines 14–18 (already in file, no change needed).

---

### `quirk/util/targets.py` — `@file` guards (CR-09)

**Analog:** `quirk/util/subprocess_input.py` lines 26–54 (ValidationResult + reason-code constants pattern) and `quirk/util/url_allowlist.py` lines 25–38.

**TargetFileError class pattern** — mirrors `ValidationResult` frozen dataclass from `quirk/util/subprocess_input.py` lines 26–43, but as a raised exception:
```python
# Add at top of quirk/util/targets.py, after existing imports:
import os
from dataclasses import dataclass
from typing import Final

# Reason-code constants (D-13 — mirrors subprocess_input.py RC_* pattern)
RC_PATH_TRAVERSAL: Final[str] = "path_traversal"
RC_PATH_NOT_ALLOWED_PREFIX: Final[str] = "path_not_allowed_prefix"
RC_TARGET_FILE_TOO_LARGE: Final[str] = "target_file_too_large"
RC_TARGET_FILE_TOO_MANY_LINES: Final[str] = "target_file_too_many_lines"

_BLOCKED_PREFIXES = ("/etc", "/proc", "/sys", "/dev")
_MAX_FILE_SIZE = 1_048_576   # 1 MB
_MAX_LINE_COUNT = 10_000


class TargetFileError(ValueError):
    """Raised by parse_target_tokens() when @file validation fails (D-13/D-14).

    Extends ValueError for backward compat with callers catching ValueError.

    Attributes:
        path: The file path that failed validation.
        reason: One of RC_PATH_TRAVERSAL, RC_PATH_NOT_ALLOWED_PREFIX,
            RC_TARGET_FILE_TOO_LARGE, RC_TARGET_FILE_TOO_MANY_LINES.
    """
    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Target file rejected ({reason}): {path!r}")
```

**Guard insertion point** — inside `parse_target_tokens()` at line 101, before `load_targets_file(file_path)`:
```python
        if token.startswith("@") and not _in_file:
            file_path = token[1:]

            # D-13: validate @file path before loading
            _real = os.path.realpath(file_path)
            _cwd_real = os.path.realpath(os.getcwd())

            # Check 1: must descend from CWD
            if not _real.startswith(_cwd_real + os.sep) and _real != _cwd_real:
                raise TargetFileError(file_path, RC_PATH_TRAVERSAL)

            # Check 2: blocked system prefixes
            if any(_real.startswith(p) for p in _BLOCKED_PREFIXES):
                raise TargetFileError(file_path, RC_PATH_NOT_ALLOWED_PREFIX)

            # Check 3: size cap
            try:
                if os.path.getsize(file_path) > _MAX_FILE_SIZE:
                    raise TargetFileError(file_path, RC_TARGET_FILE_TOO_LARGE)
            except OSError:
                pass  # FileNotFoundError will surface naturally in load_targets_file

            # Check 4: line cap (stream, don't load full file into memory)
            try:
                with open(file_path, encoding="utf-8") as _fh:
                    if sum(1 for _ in _fh) > _MAX_LINE_COUNT:
                        raise TargetFileError(file_path, RC_TARGET_FILE_TOO_MANY_LINES)
            except TargetFileError:
                raise
            except OSError:
                pass  # FileNotFoundError will surface naturally in load_targets_file

            file_raw = load_targets_file(file_path)
            ...
```

---

### `quirk/config_template.yaml` — add `security.api_token`

**Analog:** `quirk/config_template.yaml` lines 122–130 (existing `security:` block, Phase 57).

**Extension pattern** — append `api_token` field inside the existing `security:` block:
```yaml
# -- Security hardening (Phase 57 / HARDEN-SCAN-01..06) --------------------
security:
  allow_internal_targets: false        # CR-04: permit RFC1918/loopback SAML/broker URLs
  allow_cleartext_broker_probe: false  # CR-06: permit HTTP/no-TLS broker mgmt API probes
  allow_insecure_jwks: false           # CR-01: permit verify=False JWKS fetches
  api_token: ""                        # CR-03: bearer token for dashboard API (leave blank to disable)
                                       # Env var QUIRK_API_TOKEN takes priority when both are set.
```

---

### `quirk/config.py` — load `security.api_token`

**Analog:** `quirk/config.py` lines 270–283 (`SecurityCfg` dataclass) and lines 405–411 (`config_from_dict` security block).

**Dataclass extension** — add `api_token` field to `SecurityCfg` (lines 270–283):
```python
@dataclass
class SecurityCfg:
    """Phase 57 / D-04: operator safety-override knobs. All default False.
    Phase 58 / D-01: api_token for dashboard bearer auth. Default "" (disabled).
    """
    allow_internal_targets: bool = False
    allow_cleartext_broker_probe: bool = False
    allow_insecure_jwks: bool = False
    api_token: str = ""   # NEW — Phase 58 CR-03; "" means auth disabled (D-02)
```

**Config loading extension** — extend `config_from_dict` security block (lines 405–411):
```python
    security_raw = raw.get("security") or {}
    security_cfg = SecurityCfg(
        allow_internal_targets=bool(security_raw.get("allow_internal_targets", False)),
        allow_cleartext_broker_probe=bool(security_raw.get("allow_cleartext_broker_probe", False)),
        allow_insecure_jwks=bool(security_raw.get("allow_insecure_jwks", False)),
        api_token=str(security_raw.get("api_token", "") or ""),  # NEW Phase 58
    )
```

---

### `src/dashboard/src/lib/api.ts` (new utility, request-response)

**Analog:** `src/dashboard/src/hooks/useQRAMMSession.ts` lines 23–53 and `src/dashboard/src/context/QRAMMProvider.tsx` lines 23–40 — both show current raw `fetch()` call patterns that `fetchApi()` will centralize.

**Current fetch pattern in hooks** (from `useQRAMMSession.ts` lines 28–33 and `QRAMMProvider.tsx` lines 25–36):
```typescript
// BEFORE (pattern to replace in all hooks/providers):
const listResp = await fetch("/api/qramm/sessions")
// and
await fetch("/api/qramm/assessment/draft", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ ... }),
})
```

**New `fetchApi()` utility pattern** — single enforcement point for auth + CSRF headers:
```typescript
// src/dashboard/src/lib/api.ts
const CSRF_HEADER = "X-Quirk-Request"

/**
 * Shared fetch wrapper that injects auth + CSRF headers on every API call (D-08).
 *
 * - GET requests: no CSRF header (browser-safe, no side effects).
 * - POST/PUT/DELETE/PATCH: adds X-Quirk-Request: 1 and Content-Type: application/json.
 * - Authorization: Bearer added when QUIRK_API_TOKEN is set in localStorage or env.
 *
 * All components must call fetchApi() instead of fetch() directly.
 */
export async function fetchApi(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const method = (options.method ?? "GET").toUpperCase()
  const isMutating = ["POST", "PUT", "DELETE", "PATCH"].includes(method)

  const headers: HeadersInit = {
    ...(options.headers ?? {}),
  }

  if (isMutating) {
    (headers as Record<string, string>)[CSRF_HEADER] = "1"
    ;(headers as Record<string, string>)["Content-Type"] = "application/json"
  }

  // Bearer token — read from localStorage (set by user at first auth prompt)
  const token = localStorage.getItem("quirk_api_token")
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`
  }

  return fetch(path, { ...options, headers })
}
```

**Type file to check:** `src/dashboard/src/types/api.ts` — import types from there, not inline.

---

### `tests/test_api_auth.py` (new test file)

**Analog:** `tests/util/test_subprocess_input.py` — parametrized `pytest.mark.parametrize` pattern; `tests/conftest.py` — `dashboard_client` fixture pattern.

**File structure pattern** — copy from `tests/util/test_subprocess_input.py` lines 1–35:
```python
"""Dashboard API auth, CSRF, and rate-limit tests — Phase 58 / CR-03.

Test IDs match HARDEN-API-01..03.
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def authed_client(monkeypatch):
    """TestClient with QUIRK_API_TOKEN set to 'test-token'."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    from quirk.dashboard.api.app import create_app
    app = create_app()
    return TestClient(app)


@pytest.fixture
def unauthed_client():
    """TestClient with no token configured (auth disabled)."""
    from quirk.dashboard.api.app import create_app
    app = create_app()
    return TestClient(app)
```

**Route introspection test pattern** (D-06) — enumerate app.routes:
```python
def test_all_mutating_routes_have_auth_dependency(authed_client):
    """SC-1 gate: every POST/PUT/DELETE/PATCH route (except /api/health)
    must have require_auth in its dependencies."""
    from quirk.dashboard.api.middleware.auth import require_auth
    from starlette.routing import Route

    app = authed_client.app
    mutating_methods = {"POST", "PUT", "DELETE", "PATCH"}
    violations = []

    for route in app.routes:
        if not isinstance(route, Route):
            continue
        if not route.methods or not (route.methods & mutating_methods):
            continue
        if route.path in {"/api/health"}:
            continue
        dep_funcs = {d.dependency for d in (route.dependencies or [])}
        if require_auth not in dep_funcs:
            violations.append(f"{route.methods} {route.path}")

    assert violations == [], f"Routes missing require_auth: {violations}"
```

**Auth test parametrize pattern** — copy `@pytest.mark.parametrize` structure from `tests/util/test_subprocess_input.py` lines 42–76:
```python
@pytest.mark.parametrize("path,method,body", [
    ("/api/export/pdf", "POST", None),
    ("/api/qramm/sessions", "POST", {}),
    ("/api/qramm/profiles", "POST", {}),
])
def test_mutating_routes_require_auth_when_token_set(authed_client, path, method, body):
    """All mutating routes return 401 when Authorization header is missing (D-04)."""
    resp = authed_client.request(method, path, json=body)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Authentication required"
```

---

### `tests/test_init_cmd.py` — path-traversal fuzz corpus

**Analog:** `tests/util/test_subprocess_input.py` lines 42–76 (50+ parametrized traversal patterns); `tests/test_cli_init.py` lines 1–45 (existing init test structure to extend).

**File structure pattern** — extend `tests/test_cli_init.py` with parametrized fuzz corpus:
```python
"""Phase 58 / CR-01: path-traversal guard tests for quirk init --output."""
import pytest
from quirk.cli.init_cmd import run_init


@pytest.mark.parametrize("bad_path", [
    # Classic dotdot traversal
    "../evil.yaml",
    "../../etc/passwd",
    "subdir/../../evil.yaml",
    # Absolute paths outside CWD
    "/tmp/evil.yaml",
    "/etc/passwd",
    "/var/log/evil.yaml",
    # Null bytes and control chars
    "file\x00.yaml",
    "fi\x01le.yaml",
    # URL-encoded traversal (after abspath normalization these become dotdots)
    # Symlink escape would need tmp_path setup — covered in integration tests
    # Windows-style (no effect on POSIX, defense-in-depth)
    "..\\evil.yaml",
    # Deep traversal
    "a/b/c/../../../../../../../etc/passwd",
], ids=lambda p: repr(p[:40]))
def test_init_rejects_traversal_paths(bad_path, capsys):
    """quirk init must refuse --output paths that escape CWD (CR-01 / D-01)."""
    run_init(bad_path)
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert any(
        keyword in output.lower()
        for keyword in ("outside", "traversal", "not allowed", "warning")
    ), f"Expected traversal rejection message for {bad_path!r}, got: {output!r}"
```

---

## Shared Patterns

### FastAPI `Depends()` injection
**Source:** `quirk/dashboard/api/deps.py` lines 29–49
**Apply to:** `auth.py`, `csrf.py` — both implement the same `def func(request: Request) -> None` shape.
```python
def get_db() -> Generator[Session, None, None]:
    """FastAPI Depends() dependency — yields a SQLAlchemy session.

    Usage:
        @router.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
```
New auth/CSRF dependencies follow the same docstring convention and `Depends()` wiring.

### ValidationResult + reason-code constant pattern
**Source:** `quirk/util/subprocess_input.py` lines 26–54; `quirk/util/url_allowlist.py` lines 25–49
**Apply to:** `quirk/util/targets.py` `TargetFileError` + RC constants (D-13)
```python
# Frozen dataclass with ok/reason/redacted_preview — the established shape.
# TargetFileError mirrors this as a raised exception rather than a return value
# because parse_target_tokens already raises (not returns) on error (D-05).
RC_PATH_TRAVERSAL: Final[str] = "path_traversal"
RC_PATH_NOT_ALLOWED_PREFIX: Final[str] = "path_not_allowed_prefix"
```

### Environment variable priority pattern
**Source:** `quirk/dashboard/api/deps.py` lines 12–26 (`QUIRK_DB_PATH` check); `quirk/dashboard/api/routes/pdf.py` line 46 (`QUIRK_SERVE_PORT` check)
**Apply to:** `auth.py` `_get_configured_token()` — `QUIRK_API_TOKEN` env var wins over YAML.
```python
# Pattern: env var first, named consistently as QUIRK_<FEATURE>
if val := os.environ.get("QUIRK_DB_PATH"):
    return val
```

### Test fixture + dependency override pattern
**Source:** `tests/conftest.py` lines 75–111 (`dashboard_client` fixture)
**Apply to:** `tests/test_api_auth.py` — auth test fixtures should follow same `create_app()` + `TestClient` + `dependency_overrides` structure.
```python
app = create_app()
app.dependency_overrides[get_db] = override_get_db
return TestClient(app)
```

### `pytest.mark.parametrize` with 50+ inputs pattern
**Source:** `tests/util/test_subprocess_input.py` lines 42–76 (10 paths, each with 3 fields)
**Apply to:** `tests/test_init_cmd.py` fuzz corpus (D-06 in CONTEXT.md Specifics section) — same `ids=lambda` pattern for readable test names.

### Raw `fetch()` calls to centralize
**Source:** `src/dashboard/src/hooks/useQRAMMSession.ts` lines 28–53; `src/dashboard/src/context/QRAMMProvider.tsx` lines 25–36
**Apply to:** All hooks/providers that call `fetch("/api/...")` — replace with `fetchApi()` from `src/dashboard/src/lib/api.ts`. The `useScanData.ts`, `useTrendsData.ts`, `useScanList.ts`, `useQRAMMPrintData.ts` hooks all use raw `fetch()` and must be updated.

---

## No Analog Found

All files have codebase analogs. The rate-limit middleware (`rate_limit.py`) has no existing
middleware analog — the planner should use the stdlib-only token-bucket pattern described in D-09
of CONTEXT.md and the `RateLimitMiddleware` excerpt above.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `quirk/dashboard/api/middleware/rate_limit.py` | middleware | request-response | No existing `BaseHTTPMiddleware` subclass in codebase — use D-09 pattern from CONTEXT.md |

---

## Metadata

**Analog search scope:** `quirk/dashboard/api/`, `quirk/util/`, `quirk/cli/`, `quirk/config.py`, `src/dashboard/src/`, `tests/`
**Files scanned:** 18
**Pattern extraction date:** 2026-05-09
