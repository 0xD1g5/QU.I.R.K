# Phase 68: Operator Error-Message Pass - Research

**Researched:** 2026-05-14
**Domain:** Python error registry, CLI command authoring, FastAPI HTTPException patterns, subprocess smoke testing
**Confidence:** HIGH (all findings verified from codebase source; no assumptions required)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Error Code Namespace — Unified QRK-DOMAIN-NNN**
All operator-facing errors use `QRK-<DOMAIN>-NNN`. Domains: `INSTALL`, `TLS`, `SSH`, `JWT`, `CLOUD`, `DB`, `SCHED`, `CBOM`, `DASHBOARD`. Flat sequential numbering within each domain. Wire format on all surfaces: `[QRK-TLS-001] cause message. Fix: remediation hint.`

**D-02: Error Registry — quirk/errors.py**
Dict or frozen dataclass per entry with fields: `code`, `cause`, `fix`. `format_error(code: str) -> str` returns the full formatted string. No Pydantic in errors.py. Imported by run_scan.py, errors_cmd.py, doctor_cmd.py, and dashboard route modules.

**D-03: docs/error-codes.md — Auto-Generated**
Generated via `quirk errors --dump-md > docs/error-codes.md`. CI asserts file is current after any change to quirk/errors.py.

**D-04: scan_error_category Mapping — Render-Time Only**
No DB schema change. `CATEGORY_TO_CODE` map in `quirk/errors.py` maps existing category values to QRK codes at render time. `missing_extra` → `QRK-INSTALL-001`; domain-specific timeout codes per scanner.

**D-05: First-Run Error Surface — Doctor + Inline**
`quirk doctor` failures use `format_error()`. `run_scan.py` entrypoint catches missing extras, unreadable db, and missing nmap binary inline with the same format. Both paths call `format_error()`.

**D-06: quirk errors Command**
Module: `quirk/cli/errors_cmd.py`, function `run_errors(args)`. Wired into `run_scan.py` argparse. Behaviors: full Rich table; `--domain TLS` filter; positional lookup `quirk errors QRK-TLS-001`; `--dump-md` to stdout.

### Claude's Discretion

- Exact number of initial codes per domain (audit-driven by researcher/planner)
- Exact `CATEGORY_TO_CODE` mapping details for domain-ambiguous categories (timeout per scanner)
- Whether `quirk/errors.py` uses a plain dict, `NamedTuple`, or `@dataclass(frozen=True)` (planner picks per codebase conventions)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UX-01 | Every operator-facing error path (CLI exit, dashboard 4xx/5xx, scan_error_category rows) includes a one-line cause, one-line remediation hint, and a stable error code; `quirk errors` reference page documents all codes | Audit of all sys.exit, HTTPException, and scan_error_category sites complete — 28 call sites enumerated below |
| UX-02 | First-run install-day errors (missing extras, missing nmap binary, port-conflict on `quirk serve`) render with one-line-cause + one-line-fix format referencing a `QRK-INSTALL-NNN` code; smoke test exercises each scenario | Install-day error paths located in server.py, optional_extra.py, run_scan.py, doctor_cmd.py |
</phase_requirements>

---

## Summary

Phase 68 introduces a canonical error registry (`quirk/errors.py`), threads it through every operator-facing error surface, and ships a `quirk errors` CLI command and auto-generated `docs/error-codes.md`. The codebase currently has 28 distinct error-emitting call sites spread across CLI modules, dashboard route handlers, middleware, and the scan entrypoint. None carry stable codes or structured cause/fix strings today.

The migration is additive: `quirk/errors.py` is a new module; `format_error()` is imported at each call site; the `detail=` strings in `HTTPException` calls become `format_error(...)` returns. No DB schema changes are required — the existing `scan_error_category` field is unchanged, and a `CATEGORY_TO_CODE` render-time map derives QRK codes when error rows are displayed.

Three categories of work require special care: (1) existing tests that do exact-match assertions on current error detail strings will need updating alongside the production changes; (2) the `quirk serve` port-conflict case has **no current error handling** — uvicorn swallows the `OSError: [Errno 48] Address already in use` silently, so Phase 68 must add a try/except in `server.py`; (3) the `QRAMM_MULTIPLIER_OUT_OF_RANGE` error already uses a structured dict `detail`, which must be converted to the string wire format.

**Primary recommendation:** Build `quirk/errors.py` first (Wave 0/1), wire it into all call sites in a single wave (Wave 2), and update tests last (Wave 3). The CI check for `docs/error-codes.md` freshness follows the existing `python-staleness.yml` pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Error registry definition | Python package (quirk/errors.py) | — | Single source of truth; imported everywhere |
| CLI error emission (sys.exit paths) | CLI module (run_scan.py, *_cmd.py) | — | CLI modules own their own output |
| Dashboard error emission (HTTPException) | API route handlers + middleware | — | FastAPI detail= is the operator-facing channel |
| scan_error_category → QRK code mapping | quirk/errors.py (CATEGORY_TO_CODE) | Rendered at CLI/dashboard display time | Keeps DB schema stable; D-04 locked |
| Install-day errors (serve port conflict) | server.py (quirk serve entrypoint) | doctor_cmd.py | Port-conflict is a serve-time failure |
| quirk errors command | quirk/cli/errors_cmd.py | run_scan.py argparse dispatch | Follows existing CLI module pattern |
| docs/error-codes.md generation | quirk errors --dump-md | CI verification | Auto-generated; not built at runtime |

---

## Complete Error Path Audit

### Category A: CLI sys.exit Paths (non-zero exits needing codes)

These are operator-visible exits that currently produce bare text or Rich markup with no stable code.

| File | Line(s) | Current message | Proposed code |
|------|---------|-----------------|---------------|
| `quirk/dashboard/server.py` | 20–24 | `"ERROR: uvicorn not installed. Run: pip install 'quirk[dashboard]'"` + `sys.exit(1)` | `QRK-INSTALL-002` |
| `quirk/dashboard/server.py` | (missing) | No handling for `OSError: Address already in use` from uvicorn | `QRK-INSTALL-004` (NEW — port conflict) |
| `quirk/cli/doctor_cmd.py` | 31 | `"[red][✗] Python ... < ..."` | `QRK-INSTALL-005` |
| `quirk/cli/doctor_cmd.py` | 37 | `"[red][✗] {name} not found in PATH"` | `QRK-INSTALL-006` (nmap), `QRK-INSTALL-007` (syft), `QRK-INSTALL-008` (semgrep) |
| `quirk/cli/doctor_cmd.py` | 57 | `"[red][✗] {N} compliance entries stale"` | `QRK-INSTALL-009` |
| `quirk/cli/doctor_cmd.py` | 81 | `"[red][✗] cannot open {db_path}: {exc}"` | `QRK-INSTALL-003` |
| `quirk/cli/doctor_cmd.py` | 100 | `"[red][✗] {config_path} malformed: {exc}"` | `QRK-INSTALL-010` |
| `quirk/cli/schedule_cmd.py` | 43–44 | Rich `Invalid schedule name` + `sys.exit(2)` | `QRK-SCHED-001` |
| `quirk/cli/schedule_cmd.py` | 47–49 | Rich `Invalid cron expression` + `sys.exit(2)` | `QRK-SCHED-002` |
| `quirk/cli/schedule_cmd.py` | 69–71 | Rich `Schedule already exists` + `sys.exit(2)` | `QRK-SCHED-003` |
| `quirk/cli/schedule_cmd.py` | 117–119 | Rich `Schedule not found` (enable/disable) + `sys.exit(2)` | `QRK-SCHED-004` |
| `quirk/cli/schedule_cmd.py` | 133–136 | Rich `Schedule not found` (remove) + `sys.exit(2)` | `QRK-SCHED-004` (same code, same cause) |
| `run_scan.py` | 156–165 | `"[advisory] scanner=... extra=... not installed"` (stderr print) | `QRK-INSTALL-001` |
| `run_scan.py` | 246 | `"No database path available"` (stderr) | `QRK-INSTALL-003` |
| `run_scan.py` | 252 | `"[error] cannot open database: {exc}"` (stderr) | `QRK-INSTALL-003` |
| `run_scan.py` | 688 | `"[warn] scan checkpoint ... is {N}h old"` (stderr) | No code needed — informational warning, not an error exit |
| `quirk/scanner/kerberos_scanner.py` | 248–256 | Multi-line `[QUIRK] Kerberos scanning requires...` (stderr) | `QRK-INSTALL-001` (same as missing extra — identity extra) |

### Category B: Dashboard HTTPException Paths (need codes in detail=)

| File | Line(s) | Status | Current detail | Proposed code |
|------|---------|--------|-----------------|---------------|
| `quirk/dashboard/api/middleware/auth.py` | 46, 48 | 401 | `"Authentication required"` | `QRK-DASHBOARD-001` |
| `quirk/dashboard/api/middleware/csrf.py` | 24–27 | 403 | `"Missing CSRF header: X-Quirk-Request"` | `QRK-DASHBOARD-002` |
| `quirk/dashboard/api/middleware/rate_limit.py` | 57–62 | 429 | `'{"detail":"Rate limit exceeded"}'` (Response, not HTTPException) | `QRK-DASHBOARD-003` |
| `quirk/dashboard/api/routes/scan.py` | 912 | 400 | `"Invalid scan_id format: ..."` | `QRK-DASHBOARD-004` |
| `quirk/dashboard/api/routes/scan.py` | 922 | 404 | `"No scan found with scan_id=..."` | `QRK-DASHBOARD-005` |
| `quirk/dashboard/api/routes/scan.py` | 931 | 404 | `"No scan results found. Run your first scan: quirk --config config.yaml"` | `QRK-DASHBOARD-006` |
| `quirk/dashboard/api/routes/scan.py` | 945 | 404 | `"No endpoints found for latest scan."` | `QRK-DASHBOARD-006` (same condition, same code) |
| `quirk/dashboard/api/routes/scan.py` | 1124 | 400 | `"Cannot compare a scan to itself."` | `QRK-DASHBOARD-007` |
| `quirk/dashboard/api/routes/scan.py` | 1129 | 400 | `"Invalid scan_id format."` | `QRK-DASHBOARD-004` (same condition) |
| `quirk/dashboard/api/routes/scan.py` | 1134, 1136 | 404 | `"No scan found: {a!r}"` / `"No scan found: {b!r}"` | `QRK-DASHBOARD-005` |
| `quirk/dashboard/api/routes/jobs.py` | 137 | 404 | `"Job not found"` | `QRK-DASHBOARD-008` |
| `quirk/dashboard/api/routes/qramm.py` | 194 | 404 | `"Session not found"` | `QRK-DASHBOARD-009` |
| `quirk/dashboard/api/routes/qramm.py` | 345–352 | 400 | `{"error_code": "QRAMM_MULTIPLIER_OUT_OF_RANGE", ...}` (dict detail — must be converted to string) | `QRK-DASHBOARD-010` |
| `quirk/dashboard/api/routes/qramm.py` | 362–365 | 422 | `"Cannot score a session with no answered questions"` | `QRK-DASHBOARD-011` |
| `quirk/dashboard/api/routes/schedules.py` | 101 | 404 | `"Schedule not found"` | `QRK-SCHED-004` |
| `quirk/dashboard/api/routes/schedules.py` | 136–139 | 400 | `"Invalid cron expression: ..."` | `QRK-SCHED-002` |
| `quirk/dashboard/api/routes/schedules.py` | 157–160 | 409 | `"Schedule '{name}' already exists"` | `QRK-SCHED-003` |
| `quirk/dashboard/api/routes/pdf.py` | 40–46 | 503 (Response) | `"Playwright not installed. Run: pip install playwright && playwright install chromium"` | `QRK-INSTALL-002` or separate `QRK-DASHBOARD-012` |

### Category C: scan_error_category Rows (render-time mapping needed)

These are values written to `CryptoEndpoint.scan_error_category`. The DB field is unchanged; the `CATEGORY_TO_CODE` map in `quirk/errors.py` handles display.

| Category value | Write sites | Proposed mapping |
|----------------|-------------|-----------------|
| `"missing_extra"` | `run_scan.py:164`, `optional_extra.py:228` | `QRK-INSTALL-001` (context-free; install hint carries the specific extra) |
| `"exception"` | `run_scan.py:140` (`_wrapped_phase`) | Domain-specific: needs scanner label from `host` field to pick TLS/SSH/JWT/etc code — or a generic `QRK-TLS-099` / `QRK-SSH-099` etc. Planner decides the per-domain fallback code numbering |
| `"config"` | `broker_scanner.py:618,629`, `jwt_scanner.py:136,182`, `saml_scanner.py:451` | Domain-specific: `QRK-JWT-001`, `QRK-SSH-001` (SAML is SSH domain? or new IDENTITY domain — planner decides) |
| `"invalid_input"` | `container_scanner.py:67`, `source_scanner.py:44` | `QRK-TLS-001` (container) or new domain — planner assigns |
| `"coverage_gap"` | `cbom/writer.py:80,95` | `QRK-CBOM-001` |
| `"timeout"` | Referenced in `models.py` comment, used in test fixture only (`test_risk_engine_coverage_gap.py:79`) — NO actual writer found in production code | Listed in schema but not actively written — flag as dormant; assign `QRK-TLS-002` / `QRK-SSH-002` etc. as reserved codes for future use |

---

## Standard Stack

### Core (all already in project dependencies)

| Library | Version | Purpose | Verified |
|---------|---------|---------|---------|
| `rich` | `>=13.0.0` | `Console` + `Table` for `quirk errors` output | [VERIFIED: pyproject.toml] |
| `dataclasses` | stdlib | `@dataclass(frozen=True)` for error registry entries | [VERIFIED: stdlib] |
| `pytest` | `9.0.2` | Test framework for smoke tests | [VERIFIED: `pytest --version`] |
| `subprocess` | stdlib | Subprocess-based smoke test calls | [VERIFIED: existing tests in test_cli_init.py, test_version.py] |
| `argparse` | stdlib | CLI argument parsing (existing pattern in run_scan.py) | [VERIFIED: run_scan.py] |

**No new pip dependencies required.** [VERIFIED: CONTEXT.md — "zero new pip deps" is an implied constraint from v4.6 mandate; rich already installed]

### Installation

None required — all dependencies present.

---

## Architecture Patterns

### System Architecture Diagram

```
Operator Action
      |
      +--> CLI exit path (sys.exit)
      |         |
      |         v
      |    format_error(code)  <---+
      |         |                  |
      |         v                  |
      |    stderr: [QRK-X-NNN] cause. Fix: hint.
      |
      +--> dashboard API request
      |         |
      |         v
      |    HTTPException(detail=format_error(code))
      |         |
      |         v
      |    JSON: {"detail": "[QRK-X-NNN] cause. Fix: hint."}
      |
      +--> scan run (scan_error_category row)
                |
                v
           CryptoEndpoint persisted with category value unchanged
                |
           (at render time)
                |
                v
           CATEGORY_TO_CODE[category] -> code
                |
                v
           format_error(code) displayed in CLI/API response

All paths import from:
    quirk/errors.py
      - ERROR_REGISTRY: dict[str, ErrorEntry]
      - CATEGORY_TO_CODE: dict[str, str]
      - format_error(code: str) -> str
```

### Recommended Project Structure (new files only)

```
quirk/
├── errors.py                  # NEW — canonical error registry
└── cli/
    └── errors_cmd.py          # NEW — quirk errors subcommand
tests/
└── test_install_errors.py     # NEW — install-day smoke tests
docs/
└── error-codes.md             # NEW — auto-generated via quirk errors --dump-md
```

### Pattern 1: Error Registry Structure

The `@dataclass(frozen=True)` pattern is consistent with `OptionalExtra` in `quirk/util/optional_extra.py` (lines 45–73). That is the correct model to follow.

```python
# Source: quirk/util/optional_extra.py lines 45-73 [VERIFIED: codebase]
from dataclasses import dataclass

@dataclass(frozen=True)
class ErrorEntry:
    code: str      # e.g. "INSTALL-001"
    cause: str     # one-line cause
    fix: str       # one-line remediation

ERROR_REGISTRY: dict[str, ErrorEntry] = {
    "INSTALL-001": ErrorEntry(
        code="INSTALL-001",
        cause="Optional scanner extra not installed.",
        fix="Run `pip install quirk[<extra>]` to enable the scanner.",
    ),
    ...
}

CATEGORY_TO_CODE: dict[str, str] = {
    "missing_extra": "INSTALL-001",
    "coverage_gap": "CBOM-001",
    # exception and config entries are domain-specific — planner assigns per-domain codes
}

def format_error(code: str) -> str:
    """Return '[QRK-{code}] cause. Fix: fix.' or a fallback for unknown codes."""
    entry = ERROR_REGISTRY.get(code)
    if entry is None:
        return f"[QRK-{code}] Unknown error."
    return f"[QRK-{entry.code}] {entry.cause} Fix: {entry.fix}"
```

### Pattern 2: CLI Module Shape (`errors_cmd.py`)

Mirror `quirk/cli/doctor_cmd.py` exactly:

```python
# Source: quirk/cli/doctor_cmd.py [VERIFIED: codebase]
from rich.console import Console
from rich.table import Table
import sys

def run_errors(args) -> None:
    """quirk errors entrypoint."""
    console = Console()
    ...
    # positional lookup: args.code
    # --domain filter: args.domain
    # --dump-md: args.dump_md
    sys.exit(0)
```

### Pattern 3: run_scan.py Argparse Wiring

The `quirk errors` subcommand follows the identical early-intercept pattern used by `init`, `serve`, `doctor`, `schedule`, `scheduler`, `compliance`, and `qramm`:

```python
# Source: run_scan.py lines 365-458 [VERIFIED: codebase]
if len(_sys.argv) > 1 and _sys.argv[1] == "errors":
    from quirk.cli.errors_cmd import run_errors
    # parse errors-specific args here
    run_errors(errors_args)
    return
```

### Pattern 4: HTTPException Migration

```python
# Before (current):
raise HTTPException(status_code=401, detail="Authentication required")

# After:
from quirk.errors import format_error
raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
```

The `detail=` field must remain a plain string (not a dict) to match the new wire format. The one existing dict-detail case (`QRAMM_MULTIPLIER_OUT_OF_RANGE` at `qramm.py:345`) must be converted to string.

### Pattern 5: Rate Limit Middleware (special case)

`rate_limit.py` returns a `starlette.responses.Response` directly rather than raising `HTTPException`. The detail string is embedded in a JSON-encoded body string. Migration:

```python
# Before:
content='{"detail":"Rate limit exceeded"}'

# After:
import json
from quirk.errors import format_error
content=json.dumps({"detail": format_error("DASHBOARD-003")}).encode()
```

### Pattern 6: Port Conflict Handling (NEW — currently missing)

`quirk/dashboard/server.py` currently has no try/except around `uvicorn.run()`. The `OSError: [Errno 48] Address already in use` propagates uncaught. Phase 68 must add:

```python
# In server.py serve() function, around uvicorn.run():
try:
    uvicorn.run(...)
except OSError as exc:
    if "address already in use" in str(exc).lower():
        from quirk.errors import format_error
        print(format_error("INSTALL-004"), file=sys.stderr)
        sys.exit(1)
    raise
```

The fix hint for `INSTALL-004` must include `lsof -i :8512` per CONTEXT.md specifics.

### Pattern 7: Install-Day Smoke Test Shape

Mirror `tests/test_version.py:test_cli_version_subprocess` and `tests/test_install_all_excludes_impacket.py`:

```python
# Source: tests/test_version.py:24-35 [VERIFIED: codebase]
import subprocess, sys, re, pytest

QRK_CODE_PATTERN = re.compile(r"\[QRK-[A-Z]+-\d{3}\]")

@pytest.mark.slow
def test_missing_extra_format(monkeypatch, tmp_path):
    """run_scan missing extra emits [QRK-INSTALL-001] format."""
    result = subprocess.run(
        [sys.executable, "run_scan.py", ...],
        capture_output=True, text=True, timeout=15,
    )
    assert QRK_CODE_PATTERN.search(result.stderr), "No QRK code in stderr"
```

Scenarios to cover: missing extra (monkeypatch `shutil.which`), missing nmap binary, unreadable db (chmod 000), port conflict (bind a socket first).

### Anti-Patterns to Avoid

- **Dict `detail=` in HTTPException:** The one existing case (`QRAMM_MULTIPLIER_OUT_OF_RANGE`) uses `detail={"error_code": ..., "message": ...}`. This is a divergent pattern — Phase 68 converts it to the string wire format. Do not introduce new dict-detail responses.
- **Multi-line cause or fix strings:** The wire format is strictly one-line cause + one-line fix. No embedded newlines in `ErrorEntry.cause` or `ErrorEntry.fix`.
- **Importing `quirk.errors` inside `quirk/models.py`:** models.py is imported by nearly everything; adding an import there risks circular imports. The `CATEGORY_TO_CODE` lookup should happen at display/render time in CLI output functions and route handlers, not in the model layer.
- **Pydantic in errors.py:** Per CONTEXT.md code_context: `quirk/errors.py` should not use Pydantic. Use `@dataclass(frozen=True)`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rich table formatting | Custom string formatting | `rich.Table` + `rich.Console` (already in project) | Already used in doctor_cmd.py; consistent look |
| Subprocess test isolation | Custom venv setup | `monkeypatch` + `sys.executable` + `subprocess.run(..., capture_output=True)` | Existing pattern in test_version.py; no venv needed for unit-level mocking |
| CI docs freshness check | Custom hash/diff script | Pattern from `python-staleness.yml` + a new test in `tests/test_error_codes_freshness.py` | Existing CI workflow can be extended |

---

## Existing Tests That Will Break on Migration

These tests do exact-match or `in` assertions on current error strings. They must be updated **in the same wave** as the production changes.

| Test file | Line | Current assertion | Impact |
|-----------|------|-------------------|--------|
| `tests/test_api_auth.py` | 136 | `== "Authentication required"` | Breaks when auth.py uses `format_error("DASHBOARD-001")` |
| `tests/test_api_auth.py` | 197 | `== "Missing CSRF header: X-Quirk-Request"` | Breaks when csrf.py uses `format_error("DASHBOARD-002")` |
| `tests/test_api_auth.py` | 433 | `"QUIRK_SERVE_PORT is out of allowed range (1024–65535)."` (pdf.py Response) | Breaks if pdf.py error is migrated |
| `tests/test_jobs_api.py` | 198 | `"Job not found" in data["detail"]` | Breaks when jobs.py uses `format_error("DASHBOARD-008")` |
| `tests/test_qramm_router.py` | 106 | `== "Session not found"` | Breaks when qramm.py uses `format_error("DASHBOARD-009")` |
| `tests/test_schedules_api.py` | 113 | `"dup-test" in data["detail"]` | The new format_error string won't contain the schedule name — test logic must change to check for `QRK-SCHED-003` |
| `tests/test_scan_robustness.py` | 26 | `"[advisory] scanner=" in src` | Breaks when `_emit_missing_extra_advisory` in run_scan.py is replaced by `format_error()` — test must be rewritten to check for `QRK-INSTALL-001` |

**Note on `test_scan_robustness.py`:** This test inspects source code of `run_scan.py` with `inspect.getsource`. The canonical advisory string `"[advisory] scanner="` will no longer appear once migrated. The structural assertion must change to check for `format_error` and `QRK-INSTALL-001` references instead.

---

## Common Pitfalls

### Pitfall 1: QRAMM Multiplier Dict Detail
**What goes wrong:** `qramm.py:345` uses `detail={"error_code": "QRAMM_MULTIPLIER_OUT_OF_RANGE", "message": ..., "valid_range": [...]}` — a dict, not a string. FastAPI serializes dicts as nested JSON objects under `{"detail": {...}}`.
**Why it happens:** This was a pre-Phase-68 custom error structure.
**How to avoid:** Convert to `format_error("DASHBOARD-010")` which returns a plain string. The `valid_range` info belongs in the `fix` field of the registry entry.
**Warning signs:** If `response.json()["detail"]` is a dict in tests, the migration missed this site.

### Pitfall 2: Rate Limiter Uses Response, Not HTTPException
**What goes wrong:** `rate_limit.py` returns a `starlette.responses.Response` with a manually encoded JSON body — it does not raise `HTTPException`. The standard `format_error()` call must be embedded differently.
**Why it happens:** BaseHTTPMiddleware cannot raise HTTPException directly; it must return a Response.
**How to avoid:** Import `format_error` and use `json.dumps({"detail": format_error("DASHBOARD-003")}).encode()` as the body.

### Pitfall 3: Port Conflict Is Currently Silent
**What goes wrong:** `server.py` calls `uvicorn.run()` with no error handling. An `OSError: Address already in use` will print a uvicorn traceback instead of a structured QRK error.
**Why it happens:** No error handling was added when `quirk serve` was implemented.
**How to avoid:** Wrap `uvicorn.run()` with a try/except OSError that checks the message and emits `format_error("INSTALL-004")` before `sys.exit(1)`.

### Pitfall 4: Kerberos Scanner Has Its Own Legacy Advisory Print
**What goes wrong:** `kerberos_scanner.py:248–256` has a multi-line `print(..., file=sys.stderr)` advisory that is independent of `run_scan.py`'s `_emit_missing_extra_advisory`. Both paths fire for the same condition (impacket not installed).
**Why it happens:** The kerberos scanner has a guard at its own entry point before the missing-extra advisory in run_scan.py fires.
**How to avoid:** The kerberos scanner's legacy print should be converted to `format_error("INSTALL-001")` or silenced entirely since `probe_missing_extras()` already handles the advisory row. Decide in planning: keep one emit point.

### Pitfall 5: test_scan_robustness Source Inspection
**What goes wrong:** `test_scan_robustness.py` uses `inspect.getsource(run_scan)` and asserts `"[advisory] scanner=" in src`. Once `_emit_missing_extra_advisory` is replaced by `format_error()`, this assertion fails.
**Why it happens:** Source-level structural assertions lock in implementation details.
**How to avoid:** Update the test in the same wave as run_scan.py changes. New assertion: check that `format_error` is called and `"INSTALL-001"` appears in the source.

### Pitfall 6: schedule_cmd.py sys.exit(2) Exits Are Already Printing Rich Markup
**What goes wrong:** `schedule_cmd.py` uses `console.print("[red]...[/]")` before `sys.exit(2)`. The Rich markup is the current human-facing message. After Phase 68, the message body should come from `format_error()` but the Rich color markup can wrap it.
**How to avoid:** The `format_error()` return value is a plain string (no Rich markup). Wrap in `f"[red]{format_error('SCHED-001')}[/]"` for the CLI display, or print without markup to stderr. Be consistent with doctor_cmd.py's approach.

---

## Code Examples

### Error Registry (errors.py skeleton)

```python
# Source: pattern from quirk/util/optional_extra.py [VERIFIED: codebase]
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ErrorEntry:
    code: str
    cause: str
    fix: str

ERROR_REGISTRY: dict[str, ErrorEntry] = {
    "INSTALL-001": ErrorEntry(
        code="INSTALL-001",
        cause="Optional scanner package not installed.",
        fix="Run `pip install quirk[<extra>]` to enable this scanner.",
    ),
    "INSTALL-002": ErrorEntry(
        code="INSTALL-002",
        cause="Dashboard extras not installed.",
        fix="Run `pip install quirk[dashboard]` then retry.",
    ),
    "INSTALL-003": ErrorEntry(
        code="INSTALL-003",
        cause="Cannot open the scan database.",
        fix="Run `quirk doctor` to diagnose database access. Ensure quirk.db is readable.",
    ),
    "INSTALL-004": ErrorEntry(
        code="INSTALL-004",
        cause="Port 8512 is already in use.",
        fix="Run `lsof -i :8512` to find the conflicting process, or use `quirk serve --port <other>`.",
    ),
    # ... additional entries per domain
}

CATEGORY_TO_CODE: dict[str, str] = {
    "missing_extra": "INSTALL-001",
    "coverage_gap": "CBOM-001",
    # "exception" and "config" need per-scanner dispatch in display code
}

def format_error(code: str) -> str:
    """Return '[QRK-{code}] cause. Fix: fix.' string."""
    entry = ERROR_REGISTRY.get(code)
    if entry is None:
        return f"[QRK-{code}] Unknown error code."
    return f"[QRK-{entry.code}] {entry.cause} Fix: {entry.fix}"
```

### quirk errors --dump-md Output Pattern

```python
# Source: pattern from quirk/compliance/__init__.py status_report() [VERIFIED: codebase]
def _dump_markdown() -> str:
    lines = ["# QU.I.R.K. Error Code Reference\n"]
    current_domain = None
    for code, entry in sorted(ERROR_REGISTRY.items()):
        domain = code.split("-")[0]
        if domain != current_domain:
            lines.append(f"\n## {domain}\n")
            lines.append("| Code | Cause | Fix |")
            lines.append("|------|-------|-----|")
            current_domain = domain
        lines.append(f"| QRK-{code} | {entry.cause} | {entry.fix} |")
    return "\n".join(lines)
```

---

## Install-Day Smoke Test Architecture

`tests/test_install_errors.py` is a new file using `@pytest.mark.slow`. It does not create a full venv — instead it uses `monkeypatch` at the module level for unit-style scenarios and `subprocess.run` for scenarios requiring a real process boundary.

**Scenarios and test strategies:**

| Scenario | Strategy | Why subprocess vs monkeypatch |
|----------|----------|-------------------------------|
| Missing extra (e.g., dashboard) | Monkeypatch `shutil.which` + call `run_scan.py` entrypoint via subprocess | Subprocess needed to capture stderr output with the QRK format |
| Missing nmap binary | Monkeypatch `shutil.which("nmap") = None` in unit test | Can be asserted via inspect of optional_extra.py |
| Port conflict on `quirk serve` | Pre-bind a socket to 8512, then call `server.serve(port=8512)` in subprocess | Must be subprocess — uvicorn.run() blocks |
| Unreadable quirk.db | Create tmp db, chmod 000, call doctor check inline | Unit test sufficient — `_check_db()` is pure function |

**All scenarios assert:**
```python
import re
QRK_FORMAT = re.compile(r"\[QRK-[A-Z]+-\d{3}\] .+\. Fix: .+")
assert QRK_FORMAT.search(stderr_output), f"Expected QRK format, got: {stderr_output!r}"
```

---

## CI Freshness Check for docs/error-codes.md

Follow the same pattern as `tests/test_compliance_freshness.py` and `tests/test_qramm_staleness.py`.

New file: `tests/test_error_codes_freshness.py`

```python
# Source: pattern from tests/test_compliance_freshness.py [VERIFIED: codebase]
import subprocess, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_error_codes_md_is_current(tmp_path):
    """docs/error-codes.md must match `quirk errors --dump-md` output."""
    result = subprocess.run(
        [sys.executable, "run_scan.py", "errors", "--dump-md"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=10,
    )
    assert result.returncode == 0
    generated = result.stdout
    current = (REPO_ROOT / "docs" / "error-codes.md").read_text()
    assert generated == current, (
        "docs/error-codes.md is stale. Regenerate with: quirk errors --dump-md > docs/error-codes.md"
    )
```

This test is added to the staleness CI workflow invocation.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_errors.py tests/test_error_codes_freshness.py -x` |
| Full suite command | `pytest tests/ -m 'not slow'` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UX-01 | format_error() returns correct wire format | unit | `pytest tests/test_errors.py::test_format_error_wire_format -x` | Wave 0 |
| UX-01 | All dashboard HTTPException details use QRK format | unit | `pytest tests/test_api_auth.py tests/test_qramm_router.py tests/test_jobs_api.py tests/test_schedules_api.py -x` | Existing (needs update) |
| UX-01 | `quirk errors` prints Rich table | unit | `pytest tests/test_errors_cmd.py -x` | Wave 0 |
| UX-01 | `quirk errors --dump-md` matches docs/error-codes.md | unit | `pytest tests/test_error_codes_freshness.py -x` | Wave 0 |
| UX-01 | `quirk errors QRK-TLS-001` positional lookup | unit | `pytest tests/test_errors_cmd.py::test_positional_lookup -x` | Wave 0 |
| UX-02 | Missing extra emits QRK-INSTALL-001 format | slow | `pytest tests/test_install_errors.py::test_missing_extra_format -x -m slow` | Wave 0 |
| UX-02 | Port conflict emits QRK-INSTALL-004 format | slow | `pytest tests/test_install_errors.py::test_port_conflict_format -x -m slow` | Wave 0 |
| UX-02 | Unreadable db emits QRK-INSTALL-003 format | unit | `pytest tests/test_install_errors.py::test_unreadable_db_format -x` | Wave 0 |
| UX-02 | Missing nmap binary emits correct format | unit | `pytest tests/test_install_errors.py::test_missing_nmap_format -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_errors.py tests/test_errors_cmd.py -x`
- **Per wave merge:** `pytest tests/ -m 'not slow'`
- **Phase gate:** `pytest tests/ -m 'not slow'` green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_errors.py` — unit tests for `quirk/errors.py` (format_error, registry completeness, CATEGORY_TO_CODE)
- [ ] `tests/test_errors_cmd.py` — unit tests for `quirk/cli/errors_cmd.py` (table output, domain filter, positional lookup, --dump-md)
- [ ] `tests/test_install_errors.py` — install-day smoke tests (marked `@pytest.mark.slow`)
- [ ] `tests/test_error_codes_freshness.py` — CI gate asserting docs/error-codes.md is current
- [ ] `quirk/errors.py` — the registry module itself
- [ ] `quirk/cli/errors_cmd.py` — the CLI command module

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (QRK code lookup) | `ERROR_REGISTRY.get(code)` with fallback — never interpolates `code` into shell commands |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Error message information disclosure | Information Disclosure | All error messages are static strings from registry — no exception text leaks via format_error() |
| Unknown code injection | Tampering | `format_error()` returns `"[QRK-{code}] Unknown error code."` for unregistered codes — no dynamic interpolation of operator-supplied values |

**Note:** The existing `safe_str()` chokepoint (Phase 59 LEAK-01) protects `scan_error` field writes. `format_error()` is separate — it returns static registry strings, not exception text. No LEAK concern.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 68 has no external tool dependencies. All required libraries (rich, pytest, subprocess) are stdlib or already-installed project dependencies.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**All claims in this research were verified or cited — no user confirmation needed.**

---

## Open Questions

1. **`scan_error_category="exception"` code assignment**
   - What we know: `_wrapped_phase()` in `run_scan.py` writes `scan_error_category="exception"` and sets `host=scanner_label` (e.g., "tls_scanner", "ssh_scanner").
   - What's unclear: The planner needs to decide whether to (a) use the `host` field to dispatch to domain-specific `QRK-TLS-099` / `QRK-SSH-099` exception codes at render time, or (b) use a single generic `QRK-SCAN-001` exception code for all unexpected scanner failures.
   - Recommendation: Option (a) — use `host` field to map to domain exception codes. Each domain (TLS, SSH, JWT, etc.) should have a reserved `NNN-099` "unexpected error" code. This requires the `CATEGORY_TO_CODE` map to accept a second `context` parameter (or the lookup to be done by callers with scanner-name awareness).

2. **`QRAMM_MULTIPLIER_OUT_OF_RANGE` schema field documentation**
   - What we know: The `qramm.py` schema docstring at line ~340 explicitly references `QRAMM_MULTIPLIER_OUT_OF_RANGE` as the error code. If the format changes to `QRK-DASHBOARD-010`, this docstring becomes stale.
   - What's unclear: Whether the schema docstring update is in-scope for Phase 68.
   - Recommendation: Yes — update the docstring in the same edit as the HTTPException migration.

---

## Sources

### Primary (HIGH confidence)
- Codebase direct inspection — `quirk/cli/doctor_cmd.py`, `run_scan.py`, `quirk/dashboard/api/middleware/*.py`, `quirk/dashboard/api/routes/*.py`, `quirk/util/optional_extra.py`, `quirk/models.py` [VERIFIED: Read tool]
- `pyproject.toml` — confirmed project dependencies and pytest config [VERIFIED: Read tool]
- `tests/` directory — confirmed all test files that will be affected [VERIFIED: Bash grep + Read tool]

### Secondary (MEDIUM confidence)
- `quirk/cbom/writer.py` — confirmed `coverage_gap` category usage [VERIFIED: Read tool]
- `quirk/scanner/kerberos_scanner.py` — confirmed duplicate advisory print [VERIFIED: Read tool]

---

## Metadata

**Confidence breakdown:**
- Error path audit: HIGH — every call site read directly from source
- Standard stack: HIGH — all in pyproject.toml
- Architecture patterns: HIGH — derived from existing doctor_cmd.py, optional_extra.py patterns
- Test breakage risk: HIGH — exact assertion strings confirmed from test source
- Port conflict gap: HIGH — confirmed absence of try/except in server.py

**Research date:** 2026-05-14
**Valid until:** 2026-06-14 (stable codebase; 30-day window)
