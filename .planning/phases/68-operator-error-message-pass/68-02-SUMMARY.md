---
phase: 68
plan: "02"
subsystem: errors-cli
tags: [errors-cmd, cli, tdd, docs, operator-ux]
dependency_graph:
  requires: [quirk/errors.py]
  provides: [quirk/cli/errors_cmd.py, docs/error-codes.md, tests/test_errors_cmd.py]
  affects: [run_scan.py subcommand dispatch, Plan 05 freshness gate]
tech_stack:
  added: []
  patterns: [argparse-multi-action-dispatch, rich-table-grouped, dump-md-generator]
key_files:
  created:
    - quirk/cli/errors_cmd.py
    - tests/test_errors_cmd.py
    - docs/error-codes.md
  modified:
    - run_scan.py
decisions:
  - "Inserted errors intercept at run_scan.py lines 461-465 (after qramm intercept, before main scan argparse)"
  - "_normalize_code strips QRK- prefix; both QRK-TLS-001 and TLS-001 forms accepted"
  - "_filtered_entries is case-insensitive for domain matching (install == INSTALL)"
  - "docs/error-codes.md generated via python run_scan.py errors --dump-md; 88 lines covering all 36 codes across 9 domains"
metrics:
  duration: "~12 minutes"
  completed: "2026-05-14"
  tasks: 3
  files: 4
---

# Phase 68 Plan 02: errors CLI Command Summary

**One-liner:** `quirk errors` CLI command with four invocation modes (table/filter/lookup/dump-md), wired into run_scan.py argparse intercept, plus generated `docs/error-codes.md` — TDD RED/GREEN with 12 passing tests.

## What Was Built

### Task 1: quirk/cli/errors_cmd.py

Created `quirk/cli/errors_cmd.py` as the CLI frontend for `quirk/errors.py`.

**Public API:**
- `run_errors(argv: list[str]) -> None` — main entrypoint, dispatches to four modes
- `_normalize_code(raw: str) -> str` — accepts `QRK-TLS-001` or `TLS-001`, returns registry key
- `_domain_of(code: str) -> str` — extracts domain prefix
- `_filtered_entries(domain: str | None) -> list[tuple[str, ErrorEntry]]` — case-insensitive domain filter
- `_print_table(domain, console)` — Rich table with domain section breaks
- `_lookup_single(raw_code, console)` — single-code lookup, exits 1 on unknown
- `_dump_markdown() -> str` — returns plain Markdown string starting with `# QU.I.R.K. Error Code Reference`

**Invocation modes:**

| Command | Behavior |
|---------|----------|
| `quirk errors` | Rich table of all 36 codes, grouped by domain |
| `quirk errors --domain TLS` | Rich table filtered to TLS codes only |
| `quirk errors QRK-INSTALL-001` | Single entry with cause/fix breakdown; exits 0 |
| `quirk errors TLS-001` | Same (QRK- prefix optional) |
| `quirk errors BOGUS-999` | Unknown code message; exits 1 |
| `quirk errors --dump-md` | Markdown to stdout; exits 0 |

### Task 2: run_scan.py errors intercept

Inserted 4-line intercept block at **run_scan.py lines 461-465** (after `qramm` intercept, before main scan `argparse.ArgumentParser()`):

```python
# --- errors subcommand: intercept before scan argparse (Phase 68 UX-01) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "errors":
    from quirk.cli.errors_cmd import run_errors
    run_errors(_sys.argv[2:])
    return
```

Uses `_sys` alias consistent with all other intercepts in the block.

### Task 3: tests/test_errors_cmd.py + docs/error-codes.md

Created `tests/test_errors_cmd.py` with 12 tests. All pass green.

**Test coverage:**
- `test_dump_md_starts_with_header` — header assertion
- `test_dump_md_contains_install_section` — INSTALL section present
- `test_dump_md_contains_all_domains` — all domain headers present
- `test_dump_md_contains_install_001_row` — specific row present
- `test_normalize_code_strips_qrk_prefix` — both code forms normalized
- `test_filtered_entries_respects_domain` — domain filter correctness
- `test_filtered_entries_empty_for_unknown_domain` — empty result for BOGUS
- `test_filtered_entries_case_insensitive_domain` — install == INSTALL
- `test_lookup_single_known_returns_zero` (slow) — subprocess exits 0
- `test_lookup_single_unknown_exits_nonzero` (slow) — subprocess exits non-zero
- `test_dump_md_subprocess_matches_helper` (slow) — subprocess stdout matches _dump_markdown()
- `test_domain_filter_subprocess` (slow) — SCHED domain filter via subprocess

Generated `docs/error-codes.md` — **88 lines**, all 36 codes across 9 domains. Verified with `diff <(python run_scan.py errors --dump-md) docs/error-codes.md` → no output (exact match).

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (tests) | a2bd16f | `test(68-02): add failing tests for errors_cmd (RED)` |
| GREEN (implementation) | 89d05d9 | `feat(68-02): implement quirk/cli/errors_cmd.py and wire errors subcommand (GREEN)` |
| docs generation | 9260ec3 | `feat(68-02): generate initial docs/error-codes.md from error registry` |

## Commits

| Task | Hash | Message |
|------|------|---------|
| RED (tests) | a2bd16f | test(68-02): add failing tests for errors_cmd (RED) |
| GREEN (impl + wiring) | 89d05d9 | feat(68-02): implement quirk/cli/errors_cmd.py and wire errors subcommand (GREEN) |
| docs/error-codes.md | 9260ec3 | feat(68-02): generate initial docs/error-codes.md from error registry |

## Deviations from Plan

### Minor: 12 tests vs plan's stated "11"

**Found during:** Task 3
**Issue:** The plan's `<action>` block included 12 test functions (including `test_dump_md_contains_install_001_row` and `test_filtered_entries_case_insensitive_domain`) but the `<acceptance_criteria>` stated `grep -c 'def test_' returns 11`. The code block in the plan contained all 12.
**Fix:** Kept all 12 tests as the extra tests provide stronger coverage. This mirrors Plan 01's pattern (11 vs 10).
**Files modified:** tests/test_errors_cmd.py

## Known Stubs

None — all four invocation modes are fully implemented and wired.

## Self-Check: PASSED

- [x] `quirk/cli/errors_cmd.py` exists
- [x] `tests/test_errors_cmd.py` exists
- [x] `docs/error-codes.md` exists (88 lines, non-empty)
- [x] `grep -c 'def run_errors' quirk/cli/errors_cmd.py` → 1
- [x] `grep -c 'def _dump_markdown' quirk/cli/errors_cmd.py` → 1
- [x] `grep -c 'from quirk.cli.errors_cmd import run_errors' run_scan.py` → 1
- [x] `head -1 docs/error-codes.md` → `# QU.I.R.K. Error Code Reference`
- [x] `python -m pytest tests/test_errors_cmd.py -x -q -m ""` → 12 passed
- [x] `diff <(python run_scan.py errors --dump-md) docs/error-codes.md` → no output
- [x] Commits a2bd16f (RED), 89d05d9 (GREEN), 9260ec3 (docs) confirmed in git log
