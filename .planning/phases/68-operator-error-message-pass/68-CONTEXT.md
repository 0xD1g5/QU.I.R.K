# Phase 68: Operator Error-Message Pass - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 68 performs a structured pass over every operator-facing error path in QU.I.R.K. and upgrades each one to emit a stable error code, a one-line cause, and a one-line remediation hint. It introduces:

1. **`quirk/errors.py`** — the canonical error registry (central source of truth for all QRK codes)
2. **`quirk errors` CLI command** — prints all codes in a Rich table; supports `--domain` filter and per-code lookup
3. **`docs/error-codes.md`** — auto-generated from the registry via `quirk errors --dump-md`
4. **Instrumented error paths** — CLI exits, dashboard 4xx/5xx, `scan_error_category` rows, `quirk doctor`, and `quirk serve` all use the new format
5. **Install-day smoke test** — `tests/test_install_errors.py` exercises each first-run failure scenario

**In scope:** `quirk/errors.py` registry + `format_error()` helper; `quirk errors` command (`quirk/cli/errors_cmd.py`); wiring existing error paths (run_scan.py, dashboard routes, doctor_cmd.py) to use format_error(); docs/error-codes.md generation; first-run install error detection inline at scan entrypoint; smoke tests.

**Out of scope:** New scan capabilities, UI redesign, scan_error_category DB schema changes, per-target error granularity.

</domain>

<decisions>
## Implementation Decisions

### D-01: Error Code Namespace — Unified QRK-DOMAIN-NNN

All operator-facing errors use the `QRK-<DOMAIN>-NNN` pattern regardless of subsystem. No tiered scheme (scanner-only codes + flat text for others).

**Domains (subsystem-granular):**
- `INSTALL` — missing extras, missing binary, port conflict, unreadable db
- `TLS` — TLS scanner errors
- `SSH` — SSH scanner errors
- `JWT` — JWT/API scanner errors
- `CLOUD` — AWS/Azure/GCP connector errors
- `DB` — Database scanner errors
- `SCHED` — Scheduled scan errors
- `CBOM` — CBOM pipeline errors
- `DASHBOARD` — Dashboard API 4xx/5xx errors

**Numbering:** Flat sequential within each domain (TLS-001, TLS-002, ...). No grouped-by-severity number blocks.

**Wire format (all surfaces):**
```
[QRK-TLS-001] cause message. Fix: remediation hint.
```
- CLI stderr uses this exact string
- `HTTPException(detail=...)` in dashboard routes uses this string
- `scan_error_category` row error messages use this string

### D-02: Error Registry — quirk/errors.py

The canonical registry lives in `quirk/errors.py` as a Python module:

- **Structure:** A dict or frozen dataclass per entry with fields: `code` (e.g., `"TLS-001"`), `cause` (one-line string), `fix` (one-line remediation string).
- **`format_error(code: str) -> str`** helper returns the full `[QRK-TLS-001] cause. Fix: fix.` string. All call sites use this helper — no manual string assembly.
- Imported by: `run_scan.py`, `quirk/cli/errors_cmd.py`, `quirk/cli/doctor_cmd.py`, dashboard route modules.

### D-03: docs/error-codes.md — Auto-Generated

`docs/error-codes.md` is generated from `quirk/errors.py` via:
```
quirk errors --dump-md > docs/error-codes.md
```

CI asserts the file is current (analogous to the model_meta.py staleness check). The file is committed and checked in — it is not generated at build time, but it is verified in CI after any change to quirk/errors.py.

### D-04: scan_error_category Mapping — Render-Time Only

Existing `scan_error_category` values (`missing_extra`, `timeout`, `exception`, `config`, `invalid_input`, `coverage_gap`) are **not** changed in the DB schema. Instead, the mapping to a QRK code happens at render time:

- When rendering CLI output or dashboard API responses, the `scan_error_category` value is looked up in a `CATEGORY_TO_CODE` map (defined in `quirk/errors.py`) to derive the appropriate QRK code.
- No new DB column. The existing `scan_error_category` field remains the internal categorizer.
- Example mapping: `missing_extra` → `QRK-INSTALL-001`, `timeout` → domain-specific code based on context.

### D-05: First-Run Error Surface — Doctor + Inline

First-run install-day errors are surfaced in **two places**:

1. **`quirk doctor`** (extended in Phase 68): Each pre-flight check emits its failure with the new `[QRK-INSTALL-NNN] cause. Fix: hint.` format, replacing the current freeform Rich markup. Port conflict on 8512 shows: `Fix: Run quirk serve --port <other> to use a different port, or lsof -i :8512 to find the conflicting process.`
2. **`run_scan.py` scan entrypoint** (inline detection): Missing extras, unreadable db, and missing nmap binary also caught inline at startup so operators get a clean error even if they never ran doctor.

Both paths call `format_error(code)` from `quirk/errors.py`.

**Smoke test:** `tests/test_install_errors.py` — pytest, uses subprocess calls to test each scenario (missing extra, missing binary, port conflict, unreadable db). Asserts that the output matches the `[QRK-INSTALL-NNN]` format regex.

### D-06: quirk errors Command

**Module:** `quirk/cli/errors_cmd.py` with `run_errors(args)` function, wired into `run_scan.py` argparse as `quirk errors`. Follows the pattern of `doctor_cmd.py`, `init_cmd.py`, `schedule_cmd.py`.

**Behaviors:**
- `quirk errors` — prints full Rich table of all codes grouped by domain header: `Code | Cause | Fix`
- `quirk errors --domain TLS` — filters the table to the TLS domain only
- `quirk errors QRK-TLS-001` — positional arg lookup: prints the single entry for that code to stdout (useful for scripts and runbooks)
- `quirk errors --dump-md` — generates docs/error-codes.md markdown output to stdout

### Claude's Discretion

- Exact number of initial codes per domain (researcher/planner will audit existing error paths to assign codes)
- Exact `CATEGORY_TO_CODE` mapping details for domain-ambiguous categories (e.g., a `timeout` in the TLS scanner gets TLS-NNN; in SSH scanner gets SSH-NNN — planner decides the per-scanner mapping)
- Whether `quirk/errors.py` uses a plain dict, `NamedTuple`, or `@dataclass(frozen=True)` for entries (planner picks based on codebase conventions)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Error Taxonomy (existing)
- `quirk/models.py` — `CryptoEndpoint.scan_error_category` column definition and existing category values
- `quirk/util/optional_extra.py` — `_emit_missing_extra_advisory()` — existing missing-extra error emission pattern to be migrated to `format_error()`
- `run_scan.py` lines 70–165 — `_wrapped_phase()`, `_error_category()`, inline stderr prints — primary migration targets

### CLI Architecture
- `quirk/cli/doctor_cmd.py` — existing doctor command pattern (Rich table + sys.exit semantics)
- `quirk/cli/schedule_cmd.py` — another CLI module pattern to follow
- `run_scan.py` argparse wiring — how new `quirk errors` subcommand must be wired

### Dashboard Error Paths
- `quirk/dashboard/api/routes/scan.py` — HTTPException usage patterns (lines ~900-935)
- `quirk/dashboard/api/routes/jobs.py` — HTTPException at line 137
- `quirk/dashboard/api/routes/qramm.py` — HTTPException at lines 194, 345-363
- `quirk/dashboard/api/middleware/auth.py` — 401 raise pattern
- `quirk/dashboard/api/middleware/csrf.py` — 403 raise pattern
- `quirk/dashboard/api/middleware/rate_limit.py` — 429 raise pattern
- `quirk/dashboard/api/schemas.py` — existing error_category schema definitions

### Requirements
- `.planning/REQUIREMENTS.md` — UX-01, UX-02 requirement definitions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/cli/doctor_cmd.py` — Rich `Console` + `Table` pattern for structured CLI output; `(bool, str)` return type per check — use same pattern in `errors_cmd.py`
- `rich.console.Console` + `rich.table.Table` — already a dependency, used for doctor output; use for `quirk errors` table
- `run_scan.py:_wrapped_phase()` — the error capture wrapper that populates `scan_error_category`; Phase 68 wires its output through `format_error()`
- `quirk/util/optional_extra.py:_emit_missing_extra_advisory()` — existing stderr advisory; replace with `format_error('INSTALL-001')` call

### Established Patterns
- **argparse subcommand wiring** — `run_scan.py` dispatches to `run_doctor()`, `run_init()`, `run_schedule()` via `args.command` check; `run_errors()` follows the same pattern
- **CLI module shape** — each `quirk/cli/*_cmd.py` has one public `run_*()` function, takes `args` namespace, uses `sys.exit()` for non-zero exits
- **Rich markup in CLI** — doctor uses `[green][✓]`, `[red][✗]`, `[yellow][!]` — errors table should use similar styling
- **Pydantic at API boundary only** — `quirk/dashboard/api/schemas.py` is the only place for Pydantic models; `quirk/errors.py` should not use Pydantic

### Integration Points
- `run_scan.py` main() — add `errors` subcommand dispatch before the scan path
- `quirk/cli/doctor_cmd.py` — update each `_check_*()` function to use `format_error()` for failures
- `quirk/dashboard/api/routes/*.py` — update `HTTPException(detail=...)` calls to use `format_error()` for operator-facing errors
- `quirk/dashboard/api/middleware/*.py` — update 401/403/429 raises similarly

</code_context>

<specifics>
## Specific Ideas

- The roadmap explicitly names `QRK-NMAP-001` and `QRK-INSTALL-NNN` as example codes — use these exact codes in the registry
- `quirk errors QRK-TLS-001` positional lookup is explicitly wanted for scripting/runbook use cases
- Port conflict fix hint should include the literal `lsof -i :8512` command as an operator action
- `quirk errors --dump-md` stdout redirect pattern (`quirk errors --dump-md > docs/error-codes.md`) is the intended generation workflow

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 68-operator-error-message-pass*
*Context gathered: 2026-05-14*
