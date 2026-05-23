# Phase 93: Credential Infrastructure — Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/auth/credentials.py` | utility/context | request-response | `quirk/assessment/operator_context.py` | role-match |
| `quirk/util/safe_exc.py` | utility | transform | self (extend `_SENSITIVE_PATTERNS`) | exact |
| `quirk/errors.py` | config/registry | transform | self (extend `ERROR_REGISTRY`) | exact |
| `quirk/config.py` (`ConnectorsCfg`) | config | transform | self (existing `enable_*` fields) | exact |
| `run_scan.py` (`_run_jwt_phase` closure) | controller | request-response | self (existing `_run_jwt_phase` lambda at line 1190) | exact |
| `quirk/scanner/jwt_scanner.py` | service | request-response | self (existing `scan_jwt_targets` / `_fetch_jwks`) | exact |
| `quirk/cli/schedule_cmd.py` (`_cmd_add`) | controller | request-response | self (existing `SCHED-00x` rejection pattern) | exact |
| `tests/test_scan_error_gate.py` | test | transform | self (LEAK-03 AST gate at line 1; extend deny-list) | exact |
| `tests/test_credential_leakage.py` | test | transform | self (LEAK-02 safe_str corpus at line 1; add sentinel test) | exact |

---

## Pattern Assignments

### `quirk/auth/credentials.py` (new file — utility, request-response)

**Analog:** `quirk/assessment/operator_context.py`

No `quirk/auth/` directory exists yet. Create it with `__init__.py`. The `OperatorContext` dataclass is the closest analog: a scan-scoped value object built once in `run_scan.py` after config load, passed by reference into closures. `CredentialContext` follows the same shape but stores a `bytearray` secret, exposes `as_headers()`, and zeroes the buffer in a `finally` / `close()` call.

**Imports pattern** (analog: `operator_context.py` lines 1-7):
```python
from __future__ import annotations

import getpass
import os
from dataclasses import dataclass, field
from typing import Optional
```

Note: zero imports from `quirk.scanner.*` (D-14). Stdlib only: `getpass`, `os`, `re`.

**Module-independence pattern** (analog: `quirk/util/safe_exc.py` module docstring lines 1-13):
```python
"""Ephemeral credential context for QU.I.R.K. authenticated scans (Phase 93).

Decision enforcement:
  D-04: Secret stored as bytearray; zeroed in close()/finally block.
  D-05: Zeroization is best-effort — Python GC may retain heap copies.
  D-14: Zero imports from quirk.scanner.* to prevent circular deps.

Public surface:
  CredentialContext.from_cli(...)  -> CredentialContext
  CredentialContext.as_headers()   -> dict[str, str]
  CredentialContext.close()        -> None
"""
```

**Core dataclass pattern** (analog: `operator_context.py` lines 10-17):
```python
@dataclass
class CredentialContext:
    """In-memory credential holder for a single authenticated scan run.

    Secret is stored as bytearray (D-04). Call close() or use as a
    context manager to zero the buffer when the scan completes.
    """
    scheme: str                  # "bearer" | "api_key_header" | "api_key_query" | "basic"
    _secret_buf: bytearray = field(default_factory=bytearray, repr=False, compare=False)
    _header_name: Optional[str] = field(default=None, repr=False)
    _query_param: Optional[str] = field(default=None, repr=False)

    def as_headers(self) -> dict[str, str]:
        """Materialize auth headers — str only at injection boundary (D-04)."""
        secret = self._secret_buf.decode("utf-8")
        if self.scheme == "bearer":
            return {"Authorization": f"Bearer {secret}"}
        if self.scheme == "api_key_header":
            return {self._header_name or "X-Api-Key": secret}
        if self.scheme == "basic":
            # Caller encodes as base64 for HTTP Basic
            return {"Authorization": f"Basic {secret}"}
        return {}

    def close(self) -> None:
        """Zero the secret buffer (best-effort, D-04/D-05)."""
        n = len(self._secret_buf)
        if n:
            self._secret_buf[:] = b"\x00" * n

    def __enter__(self) -> "CredentialContext":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
```

**`@file` reader pattern** (analog: `quirk/util/targets.py` lines 79-99 + 143-166):

Reuse `load_targets_file` + path-traversal guard directly from `quirk/util/targets.py`. The `from_cli()` classmethod should call into the existing `_real = os.path.realpath(file_path)` / CWD-descent check / blocked-prefix check logic. Do NOT write a new file reader — import and call the existing guard.

Key guard excerpt (`quirk/util/targets.py` lines 148-157):
```python
_real = os.path.realpath(file_path)
_cwd_real = os.path.realpath(os.getcwd())
if not (_real.startswith(_cwd_real + os.sep) or _real == _cwd_real):
    raise TargetFileError(file_path, RC_PATH_TRAVERSAL)
if any(_real.startswith(p) for p in _BLOCKED_PREFIXES):
    raise TargetFileError(file_path, RC_PATH_NOT_ALLOWED_PREFIX)
```

**Precedence + `getpass` pattern** for `from_cli()` (D-01, D-02):
```python
@classmethod
def from_cli(cls, bearer: Optional[str] = None, ...) -> Optional["CredentialContext"]:
    """Build CredentialContext from CLI args (D-01/D-02).

    Precedence: interactive prompt > env var > @file / bare-ref flag.
    A bare flag with no argument triggers getpass.getpass().
    """
    # interactive prompt path
    raw = getpass.getpass("Bearer token: ")
    # env-var path
    raw = os.environ[bearer]        # when bearer looks like an env-var name
    # @file path — reuse quirk.util.targets load_targets_file + path guard
    from quirk.util.targets import load_targets_file, TargetFileError
    raw = load_targets_file(bearer[1:]).strip()
```

---

### `quirk/util/safe_exc.py` — extend `_SENSITIVE_PATTERNS` (D-08)

**Analog:** self (current file, lines 21-33)

**Current pattern list** (`quirk/util/safe_exc.py` lines 21-33):
```python
_SENSITIVE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\b(s\.|hvs\.)[A-Za-z0-9_\-]{20,}"),
    re.compile(r"://[^:@\s]+:[^@\s]+@"),
    re.compile(r"[\\/]\.?config[\\/]gcloud[\\/]"),
    re.compile(r"gcloud[\\/]application_default_credentials"),
    re.compile(r"Authorization:\s*(Bearer|Basic)\s+\S+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
)
```

**Extension to add** (append after existing patterns; follow the same `re.compile(...)` tuple entry format):
```python
    # API-key header name + value shapes (D-08)
    re.compile(r"X-Api-Key\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"X-Auth-Token\s*:\s*\S+", re.IGNORECASE),
    # Query-param API key shapes (D-08): ?api_key=<value> or &token=<value>
    re.compile(r"[?&](api_key|token|key|auth_token)=[^&\s]{8,}", re.IGNORECASE),
    # HTTP Basic credential payload
    re.compile(r"Authorization:\s*Basic\s+[A-Za-z0-9+/]{8,}={0,2}", re.IGNORECASE),
```

**safe_str function signature** (lines 36-53) — unchanged; only `_SENSITIVE_PATTERNS` tuple is extended.

---

### `quirk/errors.py` — add `SCHED-AUTH-001` entry (D-11)

**Analog:** self (current file, lines 141-160 — existing `SCHED` domain)

**Existing SCHED domain pattern** (`quirk/errors.py` lines 141-160):
```python
    # --- SCHED domain (scheduled scans) ---
    "SCHED-001": ErrorEntry(
        code="SCHED-001",
        cause="Invalid schedule name.",
        fix="Schedule names must match [A-Za-z0-9_-]+ and be 1-64 chars.",
    ),
    "SCHED-002": ErrorEntry(
        code="SCHED-002",
        cause="Invalid cron expression.",
        fix="Use a 5-field cron expression (e.g. `0 2 * * *`). See `man 5 crontab`.",
    ),
```

**New entry to add** (insert after `SCHED-004` entry, before the CBOM domain comment):
```python
    "SCHED-AUTH-001": ErrorEntry(
        code="SCHED-AUTH-001",
        cause="Authenticated scan configs cannot be scheduled — credentials are ephemeral and cannot be persisted.",
        fix="Run an authenticated scan interactively with `quirk --auth-bearer` (or `--auth-api-key` / `--auth-basic`).",
    ),
```

**`format_error` wire format** (line 254-263) — unchanged; `format_error("SCHED-AUTH-001")` will emit `[QRK-SCHED-AUTH-001] ... Fix: ...` automatically.

---

### `quirk/config.py` — add `enable_authenticated_mode` to `ConnectorsCfg` (D-11)

**Analog:** self (`ConnectorsCfg` dataclass, lines 191-270 — existing `enable_*` boolean fields)

**Existing opt-in flag pattern** (`quirk/config.py` lines 193-200):
```python
@dataclass
class ConnectorsCfg:
    enable_aws: bool = False
    enable_azure: bool = False
    # Phase 3 scanner enable flags (per D-04)
    enable_jwt: bool = False
    enable_container: bool = False
    enable_source: bool = False
    enable_nmap: bool = False
```

**New field to add** (append at end of `ConnectorsCfg` field list, before `_user_set_fields`):
```python
    # Phase 93 AUTH-01: opt-in flag for authenticated scanning (ephemeral credentials only).
    # Scheduler rejects configs where this is True (D-11 / QRK-SCHED-AUTH-001).
    enable_authenticated_mode: bool = False
```

No `__init__` changes needed — `@dataclass` generates init automatically for the new field.

---

### `run_scan.py` — credential build + `_run_jwt_phase` closure capture (D-14)

**Analog:** self (existing `_run_jwt_phase` closure at lines 1190-1202; config-load seam at lines 683-708)

**Config-load seam** (lines 683-691) — build `CredentialContext` immediately after `load_config`:
```python
    cfg = load_config(args.config)
    used_config_file = True
    # ... (existing apply_profile / broker / targets / security lines stay here)
```

**Credential build pattern** (after `apply_security_cli_overrides`, before `init_db`):
```python
    # Phase 93 / D-14: build CredentialContext after config load; zero imports
    # from scanner modules in credentials.py prevents circular deps.
    cred_ctx: Optional["CredentialContext"] = None
    if cfg.connectors.enable_authenticated_mode:
        from quirk.auth.credentials import CredentialContext
        cred_ctx = CredentialContext.from_cli(
            bearer=getattr(args, "auth_bearer", None),
            api_key=getattr(args, "auth_api_key", None),
            basic=getattr(args, "auth_basic", None),
        )
```

**Closure-capture pattern** (analog: existing `_run_jwt_phase` at lines 1190-1202):
```python
    def _run_jwt_phase():
        if not (cfg.connectors.enable_jwt and cfg.connectors.jwt_targets):
            return []
        return scan_jwt_targets(
            cfg.connectors.jwt_targets,
            timeout=cfg.scan.timeouts.jwt_seconds,
            logger=logger,
            allow_insecure_jwks=cfg.security.allow_insecure_jwks,
        )
    jwt_endpoints = _wrapped_phase(
        run_stats, "jwt_scanning", "jwt_scanner",
        _run_jwt_phase, error_endpoints, logger,
    ) or []
```

**Updated closure** — captures `cred_ctx` by name (no signature change to `_wrapped_phase`):
```python
    def _run_jwt_phase():
        if not (cfg.connectors.enable_jwt and cfg.connectors.jwt_targets):
            return []
        return scan_jwt_targets(
            cfg.connectors.jwt_targets,
            timeout=cfg.scan.timeouts.jwt_seconds,
            logger=logger,
            allow_insecure_jwks=cfg.security.allow_insecure_jwks,
            cred_ctx=cred_ctx,          # None when not authenticated
        )
```

**Zeroization finally block** — wrap the full scan body in `try/finally`:
```python
    try:
        # ... entire scan phases ...
    finally:
        if cred_ctx is not None:
            cred_ctx.close()
```

---

### `quirk/scanner/jwt_scanner.py` — consume `CredentialContext.as_headers()` (D-12)

**Analog:** self (existing `_fetch_jwks` function, lines 49-114, and `scan_jwt_targets` signature, lines 202-234)

**Existing httpx call pattern** (`jwt_scanner.py` lines 71-83):
```python
        resp = httpx.get(url, timeout=timeout, follow_redirects=True, verify=verify_tls)
```

**Updated signature** for `scan_jwt_targets` and `scan_jwt_endpoint` — add optional `cred_ctx`:
```python
def scan_jwt_targets(
    targets: list,
    timeout: int = 10,
    logger=None,
    *,
    allow_insecure_jwks: bool = False,
    cred_ctx=None,           # Optional[CredentialContext]; None = unauthenticated
) -> List[CryptoEndpoint]:
```

**httpx auth-header injection pattern** — extract headers once before the loop:
```python
    _auth_headers: dict[str, str] = cred_ctx.as_headers() if cred_ctx is not None else {}
```

Then pass to httpx via `headers=` in `_fetch_jwks`:
```python
    resp = httpx.get(url, timeout=timeout, follow_redirects=True, verify=verify_tls,
                     headers=_auth_headers)
```

**`event_hooks` log-scrubbing pattern** (D-10) — applied at httpx.Client construction if a persistent client is used; in jwt_scanner's current one-shot `httpx.get()` style, apply the hook via a short-lived `httpx.Client`:
```python
def _strip_auth_from_log(request):
    """event_hooks request filter — remove auth headers before any log handler sees them."""
    request.headers.pop("Authorization", None)
    request.headers.pop("X-Api-Key", None)
    request.headers.pop("X-Auth-Token", None)

# Usage inside _fetch_jwks when auth_headers is non-empty:
with httpx.Client(
    timeout=timeout,
    follow_redirects=True,
    verify=verify_tls,
    event_hooks={"request": [_strip_auth_from_log]},
) as client:
    resp = client.get(url, headers=_auth_headers)
```

---

### `quirk/cli/schedule_cmd.py` — reject `enable_authenticated_mode: true` (D-11)

**Analog:** self (existing `_cmd_add` function, lines 37-71 — `SCHED-001`/`SCHED-002` validation pattern)

**Existing validation + rejection pattern** (`schedule_cmd.py` lines 37-48):
```python
def _cmd_add(args: argparse.Namespace, console: Console) -> None:
    """Handle `quirk schedule add` — validate and insert a new ScheduledScan row."""
    if not _NAME_RE.match(args.name):
        console.print(f"[red]{format_error('SCHED-001')}[/red]")
        sys.exit(2)

    if not croniter.is_valid(args.cron):
        console.print(f"[red]{format_error('SCHED-002')}[/red]")
        sys.exit(2)
```

**New rejection block** (add before `db_path = _resolve_db_path(...)`, after cron validation):
```python
    # Phase 93 / D-11: authenticated scheduled scans are architecturally prohibited.
    # Check if the target config enables authenticated mode; reject immediately.
    if _config_has_authenticated_mode(args.config):
        console.print(f"[red]{format_error('SCHED-AUTH-001')}[/red]")
        sys.exit(2)
```

Where `_config_has_authenticated_mode(config_path)` is a new private helper that loads the YAML and checks `connectors.enable_authenticated_mode`. Pattern for config loading without full parse: read YAML, do a single key lookup — no `load_config` import needed (avoids pulling in all scanner deps).

---

### `tests/test_scan_error_gate.py` — extend LEAK-03 deny-list (D-09)

**Analog:** self (entire file; the `SCANNER_DIRS`, `_collect_violations`, and corpus pattern)

**Existing gate structure** (lines 28-32, 147-170):
```python
SCANNER_DIRS = [
    PROJECT_ROOT / "quirk" / "scanner",
    PROJECT_ROOT / "quirk" / "discovery",
    PROJECT_ROOT / "quirk" / "cbom",
]
```

**Extension needed** — add `quirk/auth/` to the walk scope AND add a second AST gate that checks for credential field names reaching `json.dumps()` / `model_dump()`:

```python
SCANNER_DIRS = [
    PROJECT_ROOT / "quirk" / "scanner",
    PROJECT_ROOT / "quirk" / "discovery",
    PROJECT_ROOT / "quirk" / "cbom",
    PROJECT_ROOT / "quirk" / "auth",      # Phase 93: cover new credential module
]

# Phase 93 / D-09: field-name deny-list for json.dumps / model_dump call arguments
CREDENTIAL_FIELD_NAMES = frozenset({
    "bearer", "api_key", "authorization", "token", "password",
    "credential", "secret", "key",
})
```

The new test function mirrors the `test_scan_error_writes_use_safe_str` pattern (lines 147-170) but walks `ast.Call` nodes where `func.id == "json.dumps"` or `func.attr in {"dumps", "model_dump"}` and checks keyword/positional argument names against `CREDENTIAL_FIELD_NAMES`.

**Schema CI assertion** (also D-09) — add a separate test that greps SQLite schema creation SQL in `quirk/db.py` for column names matching `CREDENTIAL_FIELD_NAMES`:
```python
def test_no_credential_column_in_schema() -> None:
    source = (PROJECT_ROOT / "quirk" / "db.py").read_text(encoding="utf-8")
    for field in CREDENTIAL_FIELD_NAMES:
        assert f'"{field}"' not in source and f"'{field}'" not in source, (
            f"Column named {field!r} found in db.py schema — D-09 violation"
        )
```

---

### `tests/test_credential_leakage.py` — extend LEAK-02 with sentinel test (D-06, D-07)

**Analog:** self (existing file; the sentinel pattern is the main new shape)

**Existing structure** (lines 1-92): `MODIFIED_FILES` list + behavior tests + import-presence gate.

**New additions:**

1. Add `quirk/auth/credentials.py` to `MODIFIED_FILES` so the import-presence gate covers it:
```python
MODIFIED_FILES = [
    ...existing entries...,
    "quirk/auth/credentials.py",   # Phase 93: credential module must import safe_str
]
```

2. Add sentinel-based leak-detection test (D-06):
```python
SENTINEL = "QUIRK_SENTINEL_CRED_d41d8cd9"

def test_sentinel_not_in_safe_str_output() -> None:
    """D-06/D-07: credential sentinel must never survive safe_str()."""
    exc = Exception(f"Authorization: Bearer {SENTINEL}")
    result = safe_str(exc)
    assert SENTINEL not in result, f"Sentinel leaked through safe_str: {result!r}"

def test_sentinel_not_in_scan_error_field() -> None:
    """D-06/D-07: sentinel in a CryptoEndpoint scan_error field must not
    appear in json.dumps output of that endpoint's fields."""
    import json
    from quirk.models import CryptoEndpoint
    ep = CryptoEndpoint(host="example.com", port=443, protocol="JWT",
                        scan_error=safe_str(Exception(f"Bearer {SENTINEL}")))
    dumped = json.dumps({"scan_error": ep.scan_error})
    assert SENTINEL not in dumped, f"Sentinel leaked into JSON: {dumped!r}"
```

---

## Shared Patterns

### Module Independence (zero cross-imports from scanner)
**Source:** `quirk/util/safe_exc.py` module docstring (lines 1-13)
**Apply to:** `quirk/auth/credentials.py`

Every util module in `quirk/util/` enforces module independence — imports only stdlib and `quirk.models` at most. The `credentials.py` module must follow the same rule: zero imports from `quirk.scanner.*`. Circular-dep direction: `run_scan.py` → `quirk.auth.credentials` → stdlib only.

### Error Registration + `format_error` Wire Format
**Source:** `quirk/errors.py` lines 20-21, 254-263
**Apply to:** `quirk/cli/schedule_cmd.py` (SCHED-AUTH-001 rejection)

All operator-facing error strings go through `format_error(code)` which adds the `[QRK-...]` prefix automatically. Never hand-craft the bracket prefix in call sites — always register in `ERROR_REGISTRY` then call `format_error()`.

### `enable_*` Boolean Opt-in Gate
**Source:** `quirk/config.py` lines 193-264 (`ConnectorsCfg`)
**Apply to:** `enable_authenticated_mode` field; scheduler rejection in `schedule_cmd.py`

Every intrusive / opt-in behavior is a `bool = False` field on `ConnectorsCfg`. The field is checked inline in the closure (`if not cfg.connectors.enable_authenticated_mode: return None`) and also at the scheduler-rejection seam.

### `_wrapped_phase` Closure Capture
**Source:** `run_scan.py` lines 115-143 (`_wrapped_phase`) + lines 1190-1202 (`_run_jwt_phase`)
**Apply to:** Updated `_run_jwt_phase` closure in `run_scan.py`

`_wrapped_phase` signature is **never changed**. Credentials are injected purely via Python closure capture of `cred_ctx` — the lambda closes over the local variable, no new parameters needed. This is the D-14 invariant.

### AST Gate Structure (ADCS/SMIME precedent)
**Source:** `tests/test_adcs_ast_gate.py` (full file — `_collect_violations` + positive + negative self-tests)
**Apply to:** New credential-field AST gate in `tests/test_scan_error_gate.py`

Every AST gate must include: (a) the real-module gate test, (b) a positive self-test that proves the gate catches synthetic violations, (c) a negative self-test that proves the gate does not flag clean code.

### `safe_str` Import-presence Gate
**Source:** `tests/test_credential_leakage.py` lines 86-92
**Apply to:** `quirk/auth/credentials.py` (add to `MODIFIED_FILES`)

Any module that handles exceptions involving credential-shaped data must import `safe_str` and be present in the `MODIFIED_FILES` list. The import-presence gate `@pytest.mark.parametrize` test enforces this mechanically.

---

## No Analog Found

All files have usable analogs in the codebase. No files require falling back to RESEARCH.md patterns exclusively.

| File | Note |
|------|------|
| `quirk/auth/__init__.py` | Trivial new package init — copy any existing `quirk/util/__init__.py` or `quirk/assessment/__init__.py` (both are empty stubs with `from __future__ import annotations` only) |
| `docs/` security-review gate markdown | Authoring task only; no code analog needed |

---

## Metadata

**Analog search scope:** `quirk/`, `run_scan.py`, `tests/`
**Files read directly:** `quirk/util/safe_exc.py`, `quirk/errors.py`, `quirk/config.py` (lines 1-290), `run_scan.py` (lines 110-215, 680-740, 1185-1215), `quirk/scanner/jwt_scanner.py`, `quirk/util/targets.py`, `quirk/assessment/operator_context.py`, `quirk/cli/schedule_cmd.py`, `tests/test_scan_error_gate.py`, `tests/test_credential_leakage.py`, `tests/test_safe_exc.py`, `tests/test_adcs_ast_gate.py`, `quirk/util/subprocess_input.py`
**Pattern extraction date:** 2026-05-22
