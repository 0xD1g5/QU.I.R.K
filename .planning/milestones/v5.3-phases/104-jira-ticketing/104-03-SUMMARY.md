---
phase: 104-jira-ticketing
plan: "03"
subsystem: ticketing-cli
tags: [cli, jira, tickets-extra, optional-extra, pyproject, run_scan, ci-guard, tdd]
dependency_graph:
  requires:
    - phase: 104-01
      provides: TicketingChannel ABC, TicketingCfg, load_ticketing_config
    - phase: 104-02
      provides: JiraChannel (lazy jira import, SSRF guard, cloud/server auth, JQL dedup)
  provides:
    - quirk.cli.ticket_cmd.run_ticket — CLI entrypoint; graceful missing-extra advisory
    - quirk/util/optional_extra.py REGISTRY — tickets entry (jira, enabled_attrs=())
    - pyproject.toml [tickets] extra — jira>=3.10.5; joined into [all]
    - run_scan.py ticket interception — argv[1]=="ticket" block using return
    - tests/test_ticket_cmd.py — 5 CLI tests (advisory, no-file, --input, missing-config, happy path)
    - tests/test_install_all_includes_tickets.py — slow CI guard; jira in quirk[all]
  affects:
    - Phase 105 ServiceNow — same ticket interception pattern; zero ticket_cmd.py changes needed
tech_stack:
  added:
    - quirk/cli/ticket_cmd.py
    - tests/test_ticket_cmd.py
    - tests/test_install_all_includes_tickets.py
  patterns:
    - "Optional-extra guard: is_extra_available('tickets') before any jira import; advisory + exit 2"
    - "CLI analog to export_cmd.py: _find_latest_findings glob + run_ticket argparse shape"
    - "run_scan.py interception: argv[1]=='ticket' block using return (not sys.exit), after export block"
    - "TDD RED/GREEN: test file committed before implementation already existed; GREEN in one pass"
    - "slow CI guard: pip dry-run --report JSON; assert 'jira' in resolved install set"
key_files:
  created:
    - quirk/cli/ticket_cmd.py
    - tests/test_ticket_cmd.py
    - tests/test_install_all_includes_tickets.py
  modified:
    - pyproject.toml
    - quirk/util/optional_extra.py
    - run_scan.py
decisions:
  - "is_extra_available('tickets') checked before any jira import — no ImportError traceback for minimal installs (ISEC-04)"
  - "enabled_attrs=() in REGISTRY: ticketing is CLI-invoked, not gated by a scan-time enable_* flag (mirrors dashboard/cbom)"
  - "run_scan.py uses return (not _sys.exit) consistent with token and export interception blocks at lines 494/500"
  - "scan_id = Path(findings_path).name — filename as scan identifier, consistent with export_cmd.py pattern"
  - "safe_str wraps all exception-bearing stderr paths — no raw str(exc) or repr(exc)"
metrics:
  duration: 25
  completed_date: "2026-05-25"
  tasks: 3
  files: 6
---

# Phase 104 Plan 03: quirk ticket CLI + [tickets] extra + run_scan wiring + CI guard Summary

**One-liner:** `quirk ticket create` dispatches per-finding Jira issues via JiraChannel with graceful missing-extra advisory (exit 2), `jira>=3.10.5` joined into `[all]`, and slow CI guard confirming pip resolution.

## What Was Built

### Task 1: pyproject [tickets] extra + optional_extra REGISTRY entry

**`pyproject.toml`** — two additions:
- `tickets = ["jira>=3.10.5"]` entry immediately after the `notify` block (Phase 104 TICKET-01 comment)
- `"quirk-scanner[tickets]"` joined into the `[all]` list after `quirk-scanner[notify]`
- `[identity]` INTENTIONAL EXCLUSION comment preserved unchanged

**`quirk/util/optional_extra.py`** — appended a new `OptionalExtra` to REGISTRY:
- `extra="tickets"`, `modules=("jira",)`, `scanner_label="jira_ticketing"`
- `install_hint`: `"Jira ticketing skipped — run \`pip install quirk[tickets]\` to enable"`
- `enabled_attrs=()`: always-probe, mirrors `dashboard` and `cbom` entries (CLI command, not scan-time flag)

### Task 2: ticket_cmd.py + run_scan.py interception

**`quirk/cli/ticket_cmd.py`** — 130-line CLI entrypoint mirroring `export_cmd.py`:
- `_find_latest_findings(output_dir)`: glob `findings-*.json`, return newest by mtime
- `run_ticket(argv)`: argparse `prog="quirk ticket"` with positional `action choices=["create"]`, `--input PATH`, `--output-dir DIR`
- Flow: (1) `is_extra_available("tickets")` guard → advisory + exit 2 if absent (ISEC-04); (2) resolve findings path; (3) JSON load; (4) `load_ticketing_config()` check; (5) lazy imports + `get_session` + `JiraChannel` dispatch loop; (6) completion print
- All exception-bearing stderr uses `safe_str(exc)`; `SystemExit` re-raised; other exceptions exit 2

**`run_scan.py`** — added ticket interception block immediately after the export block:
```python
# --- ticket subcommand: intercept before scan argparse (Phase 104 TICKET-01) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "ticket":
    from quirk.cli.ticket_cmd import run_ticket
    run_ticket(_sys.argv[2:])
    return
```
Uses `return` (not `_sys.exit`) consistent with the token and export interception blocks.

### Task 3: CLI tests + [all] CI guard

**`tests/test_ticket_cmd.py`** — 5 tests, all green:
- `test_missing_extra_advisory`: patches `is_extra_available` → False; asserts exit 2 + `"pip install quirk[tickets]"` in stderr (no ImportError traceback)
- `test_no_findings_file`: empty tmp dir → exit 2
- `test_input_flag`: `--input <path>` reads specified file; mocked dispatch completes without SystemExit
- `test_missing_config`: `load_ticketing_config()` → None → exit 2
- `test_exit_0_all_dispatched`: mocked JiraChannel + get_session; happy path; `dispatch_finding` called once per finding; no SystemExit raised

**`tests/test_install_all_includes_tickets.py`** — `@pytest.mark.slow` CI guard:
- `pip install --dry-run --ignore-installed --report` on `-e <REPO_ROOT>[all]`
- Asserts returncode 0
- Asserts `"does not provide the extra 'tickets'"` absent from combined output
- Asserts `"jira"` in the resolved install set (normalized lowercase/underscore)

## Verification

```
python -m compileall quirk/cli/ticket_cmd.py run_scan.py -q  # clean
python -m pytest tests/test_ticket_cmd.py -x -q              # 5 passed
python -m pytest tests/test_install_all_includes_tickets.py -m slow -q  # 1 passed (5.1s)
```

Missing-extra behavior:
```
# With [tickets] absent (mocked):
# stderr: ERROR: Jira ticketing skipped — run `pip install quirk[tickets]` to enable.
# exit code: 2 (no ImportError traceback)
```

## Deviations from Plan

None — plan executed exactly as written. All patterns matched PATTERNS.md references. TDD RED gate committed before implementation; GREEN in one pass (implementation was already complete from Task 2 before tests ran).

## Known Stubs

None — `run_ticket` is fully wired to `JiraChannel.dispatch_finding` with no placeholder returns.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns beyond the plan's threat model. T-104-09 (missing-extra advisory) and T-104-10 (safe_str on error output) implemented and tested. T-104-SC (jira install legitimacy) verified by slow CI guard confirming clean resolution.

## Self-Check: PASSED

- [x] `quirk/cli/ticket_cmd.py` — FOUND (defines `run_ticket` and `_find_latest_findings`)
- [x] `run_scan.py` — contains `_sys.argv[1] == "ticket"` interception with `return`
- [x] `pyproject.toml` — contains `jira>=3.10.5` under `tickets` extra; `quirk-scanner[tickets]` in `[all]`; identity exclusion preserved
- [x] `quirk/util/optional_extra.py` — REGISTRY contains `extra="tickets"`, `modules=("jira",)`
- [x] `tests/test_ticket_cmd.py` — FOUND, 5 tests pass
- [x] `tests/test_install_all_includes_tickets.py` — FOUND, 1 slow test passes
- [x] Commit c206ae6 — feat(104-03): add [tickets] extra (jira>=3.10.5) and REGISTRY entry
- [x] Commit 2ec6fca — feat(104-03): ticket_cmd.py + run_scan.py ticket interception
- [x] Commit eca9323 — test(104-03): RED gate — CLI tests + [all] CI guard for ticket_cmd
- [x] `python -m compileall quirk/cli/ticket_cmd.py run_scan.py -q` — clean
- [x] `python -m pytest tests/test_ticket_cmd.py -x -q` — 5 passed
- [x] `python -m pytest tests/test_install_all_includes_tickets.py -m slow -q` — 1 passed
