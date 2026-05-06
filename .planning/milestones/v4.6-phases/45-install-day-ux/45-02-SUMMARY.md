---
phase: 45-install-day-ux
plan: 02
subsystem: optional-extras
tags: [optional-extras, probe, advisory, install-day]
requires: []
provides:
  - quirk.util.optional_extra.REGISTRY
  - quirk.util.optional_extra.OptionalExtra
  - quirk.util.optional_extra.is_extra_available
  - quirk.util.optional_extra.probe_missing_extras
affects:
  - run_scan.main (single-line probe wired after error_endpoints init)
tech-stack:
  added: []
  patterns: [find_spec-based-import-probe, frozen-dataclass-registry]
key-files:
  created:
    - quirk/util/__init__.py
    - quirk/util/optional_extra.py
    - tests/test_optional_extra.py
  modified:
    - run_scan.py
  deleted:
    - quirk/util.py  # 1-line stub replaced by package directory
decisions:
  - dashboard registry entry uses enabled_attrs=() (always probe) — avoids touching quirk/config.py for an enable_dashboard_pdf flag
  - motion + redis OMITTED from REGISTRY (Q1/Q3) — Phase 41 inline _emit_missing_extra_advisory calls remain authoritative
  - per-scanner *_AVAILABLE flags untouched (D-11) — preserves 9+ test files' patch points
metrics:
  duration: ~12 min
  completed: 2026-05-03
requirements: [INSTALL-01, INSTALL-02, INSTALL-04]
---

# Phase 45 Plan 02: Optional-Extra Registry + Probe Summary

Centralized `quirk.util.optional_extra` registry of optional pip extras (identity, db,
cloud, dashboard) with a `probe_missing_extras()` helper that emits one
`CryptoEndpoint(protocol="ADVISORY", scan_error_category="missing_extra")` row per
enabled-but-unavailable scanner via `importlib.util.find_spec` (no ImportError risk).

## What Was Built

### `quirk/util/optional_extra.py` (new, 157 lines)

- `OptionalExtra` frozen dataclass (extra, modules, scanner_label, install_hint, enabled_attrs).
- `REGISTRY` tuple with **four** entries: identity, db, cloud, dashboard.
- `is_extra_available(extra)` — `find_spec`-based probe (never imports).
- `probe_missing_extras(cfg, error_endpoints)` — appends advisories for
  enabled-and-missing extras; silent for config-disabled or available extras.

### `run_scan.py` (1 insertion)

Six-line block inserted at line ~380, immediately after
`error_endpoints: List[CryptoEndpoint] = []` and before
`tls_targets: List[Tuple[str, int]] = []`. Imports `probe_missing_extras` locally
and invokes it once. Phase 41 inline `_emit_missing_extra_advisory` calls at
lines 788 (email_scanner) and 833 (broker_scanner) are **untouched** — `grep -c
_emit_missing_extra_advisory run_scan.py` returns 3 (definition + 2 inline calls)
exactly as before, and `grep -c probe_missing_extras` returns 1.

### `tests/test_optional_extra.py` (new, 8 tests)

| # | Test                                              | Locks in                                |
| - | ------------------------------------------------- | --------------------------------------- |
| 1 | test_registry_omits_motion_and_redis              | Q1/Q3 — registry shape                  |
| 2 | test_all_hints_contain_pip_install_literal        | INSTALL-04 / D-09 — hint contract       |
| 3 | test_is_extra_available_uses_find_spec            | T-45-07 — no ImportError on partial install |
| 4 | test_probe_emits_one_advisory_per_missing_extra   | INSTALL-02 / D-05 — one advisory per gap |
| 5 | test_probe_silent_when_scanner_disabled           | D-08 — config-disabled = silent         |
| 6 | test_probe_silent_when_extra_available            | D-08 — available = silent               |
| 7 | test_no_importerror_when_extras_missing           | INSTALL-01 — never raises               |
| 8 | test_probe_invoked_in_run_scan_main               | Wiring + Phase 41 inline calls intact   |

## Decisions Made During Execution

### Dashboard `enabled_attrs=()` (option a, per plan recommendation)

The dashboard "scanner" is not behind a `cfg.connectors.enable_*` flag — it's a
separate `quirk serve` / PDF-export concern. To honor D-08 ("only advise if user
turned it on") without touching `quirk/config.py`, the dashboard registry entry
uses an empty `enabled_attrs` tuple, and `probe_missing_extras` interprets an
empty tuple as "always probe". This avoids invasive config schema changes
(option b) and keeps the diff minimal per CLAUDE.md.

### Stub `quirk/util.py` replaced by `quirk/util/` package

The pre-existing `quirk/util.py` was a one-line "reserved for future use" stub
with **zero importers** (verified via repo-wide grep). Replacing it with a
`quirk/util/` package directory was required to host `optional_extra.py` —
no callers were affected.

## Deviations from Plan

None functional. The plan's `<context>` block referenced specific run_scan.py
line numbers (782/827) for the Phase 41 inline calls; current actual line
numbers are 788/833 (drift from intervening commits). The integration test
(test 8) asserts via substring match, not line numbers, so the contract holds.

## Verification

```text
$ pytest tests/test_optional_extra.py -x
8 passed in 0.42s

$ pytest tests/test_infra03_nyquist_coverage.py -x
18 passed in 0.10s   # no Phase 41 regression

$ grep -c "probe_missing_extras(cfg, error_endpoints)" run_scan.py
1

$ grep -c "_emit_missing_extra_advisory" run_scan.py
3   # definition + 2 inline call sites — unchanged from before

$ python -m compileall run_scan.py quirk
clean
```

## Success Criteria Mapping

- **SC #1 (INSTALL-01):** ✅ probe never raises ImportError (test 7; uses `find_spec`).
- **SC #2 (INSTALL-02, advisory emission half):** ✅ one advisory per
  enabled-and-missing scanner (tests 4, 5, 6).
- **SC #4 (INSTALL-04):** ✅ every advisory message contains literal
  `pip install quirk[<extra>]` (test 2).
- **D-05, D-08, D-09, D-10, D-11:** all honored.
- **Q1:** motion omitted; Phase 41 inline calls untouched (test 8 asserts).
- **Q3:** redis not added.

## TDD Gate Compliance

Plan-level `type: execute` (per-task `tdd="true"`); each task followed RED → GREEN
locally:

- d38f97a — `test(45-02): add unit tests …` (RED, 8 tests, 7 fail with `ModuleNotFoundError`)
- 82d7057 — `feat(45-02): add quirk/util/optional_extra.py …` (GREEN for tests 1-7)
- faa8a3a — `feat(45-02): wire probe_missing_extras into run_scan.main` (GREEN for test 8)

## Self-Check: PASSED

- quirk/util/__init__.py — FOUND
- quirk/util/optional_extra.py — FOUND
- tests/test_optional_extra.py — FOUND
- run_scan.py probe wiring — FOUND (1 occurrence)
- d38f97a — FOUND in git log
- 82d7057 — FOUND in git log
- faa8a3a — FOUND in git log
