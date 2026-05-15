---
phase: 75-api-cli-core-warnings
plan: 01
subsystem: api-cli-core
tags: [apcl-01, doctor, deps, fail-loud, typed-status, audit-ledger]
requires:
  - Phase 59 quirk/util/safe_exc.py::safe_str (credential-safe exception text)
  - Phase 74 D-05 canonical ./quirk-output/quirk.db precedent
provides:
  - quirk.cli.doctor_cmd._check_dashboard / _check_network typed status dicts
  - quirk.cli.doctor_cmd._check_db QUIRK_DB_PATH-aware resolution
  - quirk.dashboard.api.deps._default_db_path fail-loud single-canonical resolver
affects:
  - run_doctor() table renderer (typed-dict consumer)
  - tests/test_doctor_cmd.py (probe surface updated; exit semantics preserved per D-18)
  - tests/test_dashboard_wiring.py (canonical fallback path updated per D-03)
tech-stack:
  added: []
  patterns: [typed status dict, fail-loud ValueError, credential-safe exception stringification]
key-files:
  created:
    - tests/test_doctor_actionable.py
  modified:
    - quirk/cli/doctor_cmd.py
    - quirk/dashboard/api/deps.py
    - tests/test_doctor_cmd.py
    - tests/test_dashboard_wiring.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - D-01: Typed status dict {ok, detail, remediation} populated by HTTP HEAD + DNS probes
  - D-02: QUIRK_DB_PATH env precedence with existence + readability validation
  - D-03: Single canonical ./quirk-output/quirk.db; multi-DB raises ValueError
  - D-18: Exit-code semantics of `quirk doctor` unchanged (Phase 52 DOCS-05 preserved)
metrics:
  duration: ~12 min
  completed: 2026-05-15
  tasks: 3
  files_touched: 5
---

# Phase 75 Plan 01: APCL-01 Doctor Actionability + DB Path Determinism Summary

One-liner: Doctor checks now return typed status dicts with real probes (HTTP HEAD + DNS), `_check_db` honors `QUIRK_DB_PATH`, and `_default_db_path` is fail-loud single-canonical — closing WR-01, WR-02, WR-03.

## What Was Built

### D-01 / WR-01 — Typed status dicts in doctor probes

`quirk/cli/doctor_cmd.py::_check_dashboard` now performs an HTTP HEAD against
`http://127.0.0.1:8512/` via stdlib `urllib.request.urlopen(timeout=2)` and
returns `{"ok": bool, "detail": str, "remediation": str}`. `_check_network`
switched from the TCP-to-8.8.8.8:53 probe to `socket.gethostbyname("example.com")`,
returning the same typed dict shape. On failure, `detail` describes the symptom
(routed through `safe_str` per Phase 59) and `remediation` gives the operator a
next-step action ("Start the dashboard with `quirk dashboard up` and retry.",
"Verify /etc/resolv.conf or run `quirk config --dns ...`.").

`run_doctor()` gained two helpers — `_render_status` (red [✗] + remediation
suffix) and `_render_status_informational` (yellow [!] for the two
informational rows) — that consume the typed-dict shape and render it into
Rich table cells.

### D-02 / WR-02 — QUIRK_DB_PATH-aware `_check_db`

Replaced the `_DB_DEFAULT_PATH = "./quirk.db"` module constant with explicit
env precedence inside `_check_db()`:

1. `os.environ.get("QUIRK_DB_PATH")` is read first.
2. If set, the path is validated with `os.path.exists` + `os.access(..., os.R_OK)`.
3. If unset, `_check_db` defers to `_default_db_path()` (the D-03 single
   canonical resolver).
4. A `ValueError` from `_default_db_path()` (the multi-DB fail-loud case) is
   caught and surfaced as `ok=False` with a remediation pointing operators at
   `QUIRK_DB_PATH` for disambiguation.

### D-03 / WR-03 — Fail-loud single-canonical `_default_db_path`

`quirk/dashboard/api/deps.py::_default_db_path` was rewritten:

- Canonical path is `./quirk-output/quirk.db` (RESEARCH A1; matches Phase 74
  D-05 and `quirk/interactive.py:180` precedent).
- Legacy search list (`./quirk.db`, `./output/quirk.db`, canonical) is
  evaluated for actual file presence.
- `len(found) > 1` → `raise ValueError("Multiple QU.I.R.K. DBs found at {sorted}; set QUIRK_DB_PATH explicitly")`.
- `len(found) == 1` → return that path (legacy compatibility).
- Otherwise → return the canonical path.

The mtime-newest-wins heuristic is fully removed (no remaining `mtime` outside
comments).

### Audit ledger

Rows `api-cli-core/WR-01`, `WR-02`, `WR-03` of `.planning/audit-2026-05-08/AUDIT-TASKS.md`
flipped from `| — | [ ] open |` to `| Phase 75 | [x] closed |`.

## C-1 File-Path Correction

CONTEXT D-01/D-02 referenced `quirk/cli/doctor.py`; RESEARCH C-1 corrected this
to the actual on-disk module `quirk/cli/doctor_cmd.py`. All edits landed in the
real file.

## Test Coverage

`tests/test_doctor_actionable.py` (9 tests, RED-then-GREEN):

- `test_check_dashboard_returns_typed_status_dict`
- `test_check_network_returns_typed_status_dict`
- `test_check_dashboard_unreachable_has_remediation`
- `test_check_network_dns_failure_has_remediation`
- `test_check_db_uses_quirk_db_path_env`
- `test_check_db_quirk_db_path_nonexistent_fails`
- `test_default_db_path_no_dbs_returns_canonical`
- `test_default_db_path_single_legacy_returns_it`
- `test_default_db_path_multiple_legacy_raises_valueerror`

Plan required `>= 6` test functions; delivered 9.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Test contract drift] `tests/test_dashboard_wiring.py::test_deps_default_db_path`**
- **Found during:** Task 2 GREEN verification.
- **Issue:** Pre-existing test asserted the old `./quirk.db` fallback contract
  from before D-03 was authored.
- **Fix:** Updated the assertion to `./quirk-output/quirk.db` and the comment
  to cite Phase 75 D-03. Mock context (`patch("os.path.isfile", return_value=False)`)
  preserved.
- **Files modified:** `tests/test_dashboard_wiring.py`
- **Commit:** `4ea8c87` (rolled into the GREEN commit).

**2. [Rule 1 — Test probe-surface drift] `tests/test_doctor_cmd.py`**
- **Found during:** Task 2 GREEN verification.
- **Issue:** Three tests mocked `socket.create_connection` (the old TCP probe)
  which D-01 removed. After the rewrite they hit the real `urlopen` and either
  type-errored on a `MagicMock` or short-circuited the run.
- **Fix:** Switched mocks to `quirk.cli.doctor_cmd.urlopen` (HTTP HEAD) and
  `quirk.cli.doctor_cmd.socket.gethostbyname` (DNS). Added env-var + os
  monkeypatches so `_check_db` resolves deterministically. Exit-code semantics
  (D-18) preserved — tests still assert exit 0 / exit 1 at the same gates.
- **Files modified:** `tests/test_doctor_cmd.py`
- **Commit:** `4ea8c87` (rolled into the GREEN commit).

### Audit-ledger Drift (informational)

The plan's Task 3 acceptance criteria expected 14 remaining `[ ] open`
api-cli-core/WR-04..17 rows after Task 3. Three rows (WR-07, WR-08, WR-17)
were already closed by Phase 75 sibling plans (likely 75-02/75-03 already
committed to the ledger by an earlier wave), leaving 11 open. This is benign
drift — none of the three rows are owned by this plan, and WR-01/WR-02/WR-03
closure (the only mutation this plan performs) is correct (`grep` count = 3).

## Threat Mitigations Applied

- **T-75-01 (Tampering — silent legacy-DB selection):** mitigated by D-03
  fail-loud `ValueError`.
- **T-75-02 (Repudiation — bare True/False status):** mitigated by D-01 typed
  dict with `remediation`.
- **T-75-03 (Info Disclosure — exception text leakage):** all exception
  stringification in `_check_db` / `_check_network` / `_check_dashboard`
  routes through `quirk.util.safe_exc.safe_str` (Phase 59).
- **T-75-04 (Tampering — silent fallback on unreadable QUIRK_DB_PATH):**
  mitigated by D-02 explicit `os.path.exists` + `os.access` validation.

## Self-Check

- `tests/test_doctor_actionable.py` — FOUND
- `quirk/cli/doctor_cmd.py` (typed-dict probes + QUIRK_DB_PATH) — FOUND
- `quirk/dashboard/api/deps.py` (fail-loud single canonical) — FOUND
- Commit `87538dc` (RED) — FOUND
- Commit `4ea8c87` (GREEN) — FOUND
- Commit `dbfd59e` (audit flip) — FOUND
- AUDIT-TASKS WR-01/02/03 marked `Phase 75 | [x] closed` — VERIFIED (count = 3)
- `pytest tests/test_doctor_actionable.py` — 9 passed
- `pytest -k "doctor or deps or wiring"` — 30 passed, 0 regressions

## Self-Check: PASSED
