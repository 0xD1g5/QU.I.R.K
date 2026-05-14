# Phase 68: Operator Error-Message Pass - Pattern Map

**Mapped:** 2026-05-14
**Files analyzed:** 12 (3 new, 9 modified)
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/errors.py` | utility/registry | transform | `quirk/util/optional_extra.py` | exact (frozen dataclass registry + public helper) |
| `quirk/cli/errors_cmd.py` | CLI command | request-response | `quirk/cli/doctor_cmd.py` | exact (Rich table + sys.exit semantics) |
| `tests/test_install_errors.py` | test | request-response | `tests/test_version.py` + `tests/test_install_all_excludes_impacket.py` | exact (subprocess smoke + `@pytest.mark.slow`) |
| `tests/test_error_codes_freshness.py` | test | request-response | `tests/test_compliance_freshness.py` | exact (staleness/freshness CI gate) |
| `run_scan.py` | entrypoint | request-response | itself (existing subcommand dispatch block lines 365-459) | exact (same file; add errors intercept + format_error calls) |
| `quirk/cli/doctor_cmd.py` | CLI command | request-response | itself (existing `_check_*` functions) | exact (same file; swap freeform strings for `format_error()`) |
| `quirk/dashboard/server.py` | service entrypoint | request-response | itself (existing uvicorn ImportError guard lines 17-24) | exact (same pattern; add OSError guard) |
| `quirk/dashboard/api/middleware/auth.py` | middleware | request-response | itself (existing HTTPException 401 lines 46-48) | exact (replace detail string) |
| `quirk/dashboard/api/middleware/csrf.py` | middleware | request-response | itself (existing HTTPException 403 lines 23-27) | exact (replace detail string) |
| `quirk/dashboard/api/middleware/rate_limit.py` | middleware | request-response | itself (existing Response body line 58) | exact (replace hardcoded JSON body string) |
| `quirk/dashboard/api/routes/scan.py` | route handler | CRUD | itself (existing HTTPException raises lines 912-945) | exact (replace detail strings) |
| `quirk/dashboard/api/routes/jobs.py` + `qramm.py` | route handler | CRUD | itself (existing HTTPException raises lines 137, 194, 345-365) | exact (replace detail strings) |

---

## Pattern Assignments

### `quirk/errors.py` (utility/registry, transform)

**Primary analog:** `quirk/util/optional_extra.py`
**Secondary analog:** `quirk/qramm/model_meta.py` (dataclass registry with lookup helper)

**Imports pattern** (`quirk/util/optional_extra.py` lines 39-43):
```python
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from importlib.util import find_spec
from typing import Optional, Tuple
```

**Frozen dataclass registry pattern** (`quirk/util/optional_extra.py` lines 45-73):
```python
@dataclass(frozen=True)
class OptionalExtra:
    extra: str
    modules: Tuple[str, ...]
    scanner_label: str
    install_hint: str
    enabled_attrs: Tuple[str, ...]
    binary: Optional[str] = None

REGISTRY: Tuple[OptionalExtra, ...] = (
    OptionalExtra(
        extra="identity",
        modules=("impacket",),
        scanner_label="kerberos_scanner",
        install_hint="...",
        enabled_attrs=("enable_kerberos",),
    ),
    ...
)
```

**`errors.py` registry shape** (follows the above pattern exactly — use `@dataclass(frozen=True)` not Pydantic):
```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ErrorEntry:
    code: str    # e.g. "INSTALL-001"
    cause: str   # one-line; NO embedded newlines
    fix: str     # one-line; NO embedded newlines

ERROR_REGISTRY: dict[str, ErrorEntry] = {
    "INSTALL-001": ErrorEntry(
        code="INSTALL-001",
        cause="Optional scanner package not installed.",
        fix="Run `pip install quirk[<extra>]` to enable this scanner.",
    ),
    ...
}

CATEGORY_TO_CODE: dict[str, str] = {
    "missing_extra": "INSTALL-001",
    "coverage_gap":  "CBOM-001",
}

def format_error(code: str) -> str:
    entry = ERROR_REGISTRY.get(code)
    if entry is None:
        return f"[QRK-{code}] Unknown error code."
    return f"[QRK-{entry.code}] {entry.cause} Fix: {entry.fix}"
```

**Anti-pattern to avoid:** `quirk/models.py` is NOT an import site for `quirk.errors` — circular import risk. `CATEGORY_TO_CODE` lookups happen only at display/render time in CLI output functions and route handlers.

---

### `quirk/cli/errors_cmd.py` (CLI command, request-response)

**Primary analog:** `quirk/cli/doctor_cmd.py` (entire file)
**Secondary analog:** `quirk/cli/schedule_cmd.py` (argparse sub-action dispatch pattern)

**Module-level imports pattern** (`quirk/cli/doctor_cmd.py` lines 1-19):
```python
"""quirk errors — ..."""
from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table
```

**Public function signature pattern** (`quirk/cli/doctor_cmd.py` line 123):
```python
def run_errors(args) -> None:
    """quirk errors entrypoint."""
    console = Console()
    ...
    sys.exit(0)
```

**Rich Table construction pattern** (`quirk/cli/doctor_cmd.py` lines 125-129):
```python
table = Table(title="QU.I.R.K. Error Codes", show_header=True, header_style="bold")
table.add_column("Code", style="bold")
table.add_column("Cause")
table.add_column("Fix")
```

**Domain-grouped table rows** — iterate `sorted(ERROR_REGISTRY.items())`, split `code` on `-` to get domain, emit a section header row when domain changes. Mirror the `_cmd_list` pattern in `schedule_cmd.py` lines 76-107.

**argparse multi-action dispatch pattern** (`quirk/cli/schedule_cmd.py` lines 143-195):
```python
def run_errors(argv: list[str]) -> None:
    console = Console()
    parser = argparse.ArgumentParser(prog="quirk errors", description="...")
    parser.add_argument("code", nargs="?", help="Positional code lookup (e.g. QRK-TLS-001)")
    parser.add_argument("--domain", help="Filter by domain (e.g. TLS)")
    parser.add_argument("--dump-md", action="store_true", help="Print Markdown to stdout")
    args = parser.parse_args(argv)

    if args.dump_md:
        print(_dump_markdown())
        return
    if args.code:
        _lookup_single(args.code, console)
        return
    _print_table(args.domain, console)
```

**sys.exit semantics** — same as `doctor_cmd.py`: `sys.exit(0)` on success, `sys.exit(1)` on unknown code lookup. Never `sys.exit(2)` for errors subcommand (2 is reserved for schedule validation failures).

---

### `tests/test_install_errors.py` (test, subprocess smoke)

**Primary analog:** `tests/test_version.py` (subprocess pattern with `@pytest.mark.slow`)
**Secondary analog:** `tests/test_install_all_excludes_impacket.py` (REPO_ROOT + subprocess + structured assertions)

**File header + imports pattern** (`tests/test_version.py` lines 1-7, `tests/test_install_all_excludes_impacket.py` lines 22-33):
```python
"""Phase 68 UX-02: install-day smoke tests for QRK-INSTALL-NNN error format."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
QRK_FORMAT = re.compile(r"\[QRK-[A-Z]+-\d{3}\] .+\. Fix: .+")
```

**`@pytest.mark.slow` subprocess pattern** (`tests/test_version.py` lines 23-37):
```python
@pytest.mark.slow
def test_missing_extra_format():
    result = subprocess.run(
        [sys.executable, "run_scan.py", ...],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=REPO_ROOT,
    )
    stderr = result.stderr or ""
    assert QRK_FORMAT.search(stderr), f"Expected QRK format, got: {stderr!r}"
```

**Unit-style monkeypatch pattern** (for non-subprocess scenarios — DB check, binary check):
```python
def test_unreadable_db_format(tmp_path, monkeypatch):
    import os
    db_path = tmp_path / "quirk.db"
    db_path.write_bytes(b"")
    os.chmod(db_path, 0o000)
    from quirk.cli import doctor_cmd
    ok, msg = doctor_cmd._check_db(str(db_path))
    assert not ok
    # After Phase 68 migration: msg contains [QRK-INSTALL-003]
    assert "QRK-INSTALL-003" in msg
    os.chmod(db_path, 0o644)  # cleanup
```

---

### `tests/test_error_codes_freshness.py` (test, CI gate)

**Primary analog:** `tests/test_compliance_freshness.py` (entire file — same structural intent)

**Pattern** (`tests/test_compliance_freshness.py` lines 1-26):
```python
"""Phase 68 D-03 gate: docs/error-codes.md must match `quirk errors --dump-md`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_error_codes_md_is_current():
    result = subprocess.run(
        [sys.executable, "run_scan.py", "errors", "--dump-md"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=10,
    )
    assert result.returncode == 0
    generated = result.stdout
    current = (REPO_ROOT / "docs" / "error-codes.md").read_text()
    assert generated == current, (
        "docs/error-codes.md is stale. Regenerate: quirk errors --dump-md > docs/error-codes.md"
    )
```

---

### `run_scan.py` — errors subcommand wiring + inline error path updates

**Analog:** `run_scan.py` lines 365-459 (the existing subcommand intercept block)

**Subcommand intercept pattern** (copy structure of the `doctor` intercept — lines 435-439, the simplest form):
```python
# --- errors subcommand: intercept before scan argparse (Phase 68 UX-01) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "errors":
    from quirk.cli.errors_cmd import run_errors
    run_errors(_sys.argv[2:])
    return
```

Insert this block **after** the `qramm` intercept (line ~459) and **before** the main scan argparse. Matches placement of all other subcommands in the dispatch chain.

**Inline error emission migration** (`run_scan.py` lines 154-165 — `_emit_missing_extra_advisory`):

Current (lines 154-158):
```python
print(
    f"[advisory] scanner={scanner_name} extra={extra_group} not installed"
    f" -- run `pip install quirk[{extra_group}]` to enable",
    file=sys.stderr,
)
```

After Phase 68:
```python
from quirk.errors import format_error
print(format_error("INSTALL-001"), file=sys.stderr)
```

**DB path error paths** (`run_scan.py` lines 246, 252):

Current:
```python
print("No database path available. Use --db-path or --config.", file=sys.stderr)
# ...
print(f"[error] cannot open database: {exc}", file=sys.stderr)
```

After Phase 68 — both become `print(format_error("INSTALL-003"), file=sys.stderr)`. The `exc` detail is not interpolated into the message (static registry strings only — no exception text leaks).

---

### `quirk/cli/doctor_cmd.py` — _check_* function updates

**Analog:** itself (entire file — modify in-place)

**Current failure return pattern** (`doctor_cmd.py` lines 31, 38, 58, 81, 100):
```python
return False, f"[red][✗] {name} not found in PATH[/red]"
return False, f"[red][✗] cannot open {db_path}: {exc}[/red]"
```

**After Phase 68** — wrap `format_error()` return in Rich markup for display consistency:
```python
from quirk.errors import format_error

# In _check_binary():
return False, f"[red][✗] {format_error('INSTALL-006')}[/red]"

# In _check_db():
return False, f"[red][✗] {format_error('INSTALL-003')}[/red]"
```

The Rich markup `[red]...[/red]` stays as the display layer; `format_error()` provides the stable code + cause + fix string inside it. This matches how `schedule_cmd.py` wraps error text: `console.print(f"[red]{...}[/]")`.

---

### `quirk/dashboard/server.py` — port conflict error (NEW handling)

**Analog:** `quirk/dashboard/server.py` lines 17-24 (the existing `ImportError` guard — same shape)

**Existing ImportError guard** (lines 17-24):
```python
try:
    import uvicorn
except ImportError:
    print(
        "ERROR: uvicorn not installed. Run: pip install 'quirk[dashboard]'",
        file=sys.stderr,
    )
    sys.exit(1)
```

**New OSError guard** (wrap the `uvicorn.run(...)` call on line 40):
```python
try:
    uvicorn.run(
        "quirk.dashboard.api.app:app",
        host=host,
        port=port,
        log_level="info",
    )
except OSError as exc:
    if "address already in use" in str(exc).lower():
        from quirk.errors import format_error
        print(format_error("INSTALL-004"), file=sys.stderr)
        sys.exit(1)
    raise
```

The `ImportError` guard above also needs its string replaced: `print(format_error("INSTALL-002"), file=sys.stderr)` — same try/except shape, just swap the detail string.

---

### `quirk/dashboard/api/middleware/auth.py` — 401 update

**Analog:** itself (lines 46-48)

**Current** (`auth.py` lines 46, 48):
```python
raise HTTPException(status_code=401, detail="Authentication required")
```

**After Phase 68:**
```python
from quirk.errors import format_error
raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
```

Import `format_error` at the top of the file alongside the existing FastAPI imports (line 8 block).

---

### `quirk/dashboard/api/middleware/csrf.py` — 403 update

**Analog:** itself (lines 22-27)

**Current** (`csrf.py` lines 23-27):
```python
raise HTTPException(
    status_code=403,
    detail=f"Missing CSRF header: {CSRF_HEADER}",
)
```

**After Phase 68:**
```python
from quirk.errors import format_error
raise HTTPException(
    status_code=403,
    detail=format_error("DASHBOARD-002"),
)
```

The header name detail is absorbed into the `ErrorEntry.fix` field in the registry (e.g. `fix="Add header X-Quirk-Request: 1 to mutating requests."`).

---

### `quirk/dashboard/api/middleware/rate_limit.py` — 429 update (special case)

**Analog:** itself (lines 54-62). This middleware returns a `starlette.responses.Response` directly — it does NOT raise `HTTPException`. The migration must embed `format_error()` into the JSON body.

**Current** (`rate_limit.py` lines 57-62):
```python
return Response(
    content='{"detail":"Rate limit exceeded"}',
    status_code=429,
    media_type="application/json",
    headers={"Retry-After": str(max(retry_after, 1))},
)
```

**After Phase 68:**
```python
import json
from quirk.errors import format_error
return Response(
    content=json.dumps({"detail": format_error("DASHBOARD-003")}).encode(),
    status_code=429,
    media_type="application/json",
    headers={"Retry-After": str(max(retry_after, 1))},
)
```

Add `import json` to the top-level imports (line 10 block). Add `from quirk.errors import format_error` to the imports. Do NOT change the `Response` return path to `HTTPException` — `BaseHTTPMiddleware` cannot raise `HTTPException`.

---

### `quirk/dashboard/api/routes/scan.py` — HTTPException updates

**Analog:** itself (lines 908-945). All raises follow the same shape.

**Current pattern** (`scan.py` lines 912, 922, 931-934, 944-945):
```python
raise HTTPException(status_code=400, detail=f"Invalid scan_id format: {scan_id!r}")
raise HTTPException(status_code=404, detail=f"No scan found with scan_id={scan_id!r}")
raise HTTPException(
    status_code=404,
    detail="No scan results found. Run your first scan: quirk --config config.yaml",
)
raise HTTPException(status_code=404, detail="No endpoints found for latest scan.")
```

**After Phase 68** — all detail strings replaced with `format_error(code)` calls:
```python
from quirk.errors import format_error
raise HTTPException(status_code=400, detail=format_error("DASHBOARD-004"))
raise HTTPException(status_code=404, detail=format_error("DASHBOARD-005"))
raise HTTPException(status_code=404, detail=format_error("DASHBOARD-006"))
```

The `scan_id` value is NOT interpolated into the format_error string (static registry strings only).

---

### `quirk/dashboard/api/routes/jobs.py` — HTTPException update

**Analog:** itself (`_get_or_404` function, line 134-138)

**Current** (`jobs.py` line 137):
```python
raise HTTPException(status_code=404, detail="Job not found")
```

**After Phase 68:**
```python
from quirk.errors import format_error
raise HTTPException(status_code=404, detail=format_error("DASHBOARD-008"))
```

Add the import at the top of the file alongside existing `from fastapi import APIRouter, Depends, HTTPException` (line 26).

---

### `quirk/dashboard/api/routes/qramm.py` — HTTPException updates (includes dict-detail conversion)

**Analog:** itself (lines 191-195, 343-365)

**Current — simple 404** (`qramm.py` line 194):
```python
raise HTTPException(status_code=404, detail="Session not found")
```

**Current — dict detail (MUST be converted)** (`qramm.py` lines 345-352):
```python
raise HTTPException(
    status_code=400,
    detail={
        "error_code": "QRAMM_MULTIPLIER_OUT_OF_RANGE",
        "message": "profile_multiplier must be in [0.8, 1.5]",
        "valid_range": [0.8, 1.5],
    },
)
```

**After Phase 68** (both):
```python
from quirk.errors import format_error
raise HTTPException(status_code=404, detail=format_error("DASHBOARD-009"))
raise HTTPException(status_code=400, detail=format_error("DASHBOARD-010"))
raise HTTPException(status_code=422, detail=format_error("DASHBOARD-011"))
```

The `valid_range` info belongs in `ErrorEntry.fix` in the registry (e.g. `fix="profile_multiplier must be in [0.8, 1.5]."`). Also update the schema docstring at line ~340 that references `QRAMM_MULTIPLIER_OUT_OF_RANGE` — make it reference `QRK-DASHBOARD-010` instead.

---

## Shared Patterns

### Import placement for `format_error`
**Source:** Every analog file uses top-of-file imports alongside the existing FastAPI/Rich imports.
**Apply to:** All middleware, route, and CLI files that call `format_error()`.
```python
from quirk.errors import format_error
```
Add as a project-local import in the appropriate import group (after stdlib, after third-party, in the project-local group).

### Static-string-only error messages
**Source:** `quirk/dashboard/server.py` lines 20-23 — exception variable is NOT interpolated into the user-facing message.
**Apply to:** All `format_error()` call sites. The `exc` binding from a `try/except` block must never be passed to or embedded in `format_error()` output. Exception details go only to a logger, never to the operator-facing string.
```python
# Correct:
print(format_error("INSTALL-003"), file=sys.stderr)

# Wrong (leaks exception internals):
print(f"{format_error('INSTALL-003')}: {exc}", file=sys.stderr)
```

### Rich markup wrapper for CLI failures
**Source:** `quirk/cli/doctor_cmd.py` lines 31, 38, 58, 81, 100 — `[red][✗] ...[/red]`.
**Apply to:** All `doctor_cmd.py` `_check_*` failure returns. Wrap the `format_error()` call in the existing `[red][✗] ...[/red]` markup:
```python
return False, f"[red][✗] {format_error('INSTALL-006')}[/red]"
```

### `@pytest.mark.slow` for subprocess tests
**Source:** `tests/test_version.py` line 23, `tests/test_install_all_excludes_impacket.py` line 35.
**Apply to:** All tests in `test_install_errors.py` that invoke subprocess (missing extra, port conflict). Unit-style tests (monkeypatch, unreadable db) do NOT need the marker.

### `REPO_ROOT` path resolution
**Source:** `tests/test_install_all_excludes_impacket.py` line 32.
**Apply to:** `test_install_errors.py` and `test_error_codes_freshness.py`.
```python
REPO_ROOT = Path(__file__).resolve().parent.parent
```

---

## No Analog Found

All files in scope have close matches. No entry needed.

---

## Existing Tests That Break on Migration

These files need updates **in the same wave** as their production counterparts:

| Test file | Assertion that breaks | Required change |
|---|---|---|
| `tests/test_api_auth.py` line 136 | `== "Authentication required"` | Assert string contains `"QRK-DASHBOARD-001"` |
| `tests/test_api_auth.py` line 197 | `== "Missing CSRF header: X-Quirk-Request"` | Assert string contains `"QRK-DASHBOARD-002"` |
| `tests/test_jobs_api.py` line 198 | `"Job not found" in data["detail"]` | Assert `"QRK-DASHBOARD-008" in data["detail"]` |
| `tests/test_qramm_router.py` line 106 | `== "Session not found"` | Assert string contains `"QRK-DASHBOARD-009"` |
| `tests/test_schedules_api.py` line 113 | `"dup-test" in data["detail"]` | Assert `"QRK-SCHED-003" in data["detail"]` |
| `tests/test_scan_robustness.py` line 26 | `"[advisory] scanner=" in src` | Assert `"format_error" in src` and `"INSTALL-001" in src` |

---

## Metadata

**Analog search scope:** `quirk/cli/`, `quirk/dashboard/`, `quirk/util/`, `run_scan.py`, `tests/`
**Files scanned:** 14 source files read directly
**Pattern extraction date:** 2026-05-14
