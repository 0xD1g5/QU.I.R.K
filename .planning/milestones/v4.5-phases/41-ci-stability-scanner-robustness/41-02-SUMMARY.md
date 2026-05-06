---
phase: 41-ci-stability-scanner-robustness
plan: 02
subsystem: config
tags: [config, dataclass, deprecation, timeouts, retry]

requires:
  - phase: 41-ci-stability-scanner-robustness
    plan: 01
    provides: tests/test_timeouts_config.py xfail stubs (4) + ScanError column infra
provides:
  - "TimeoutsCfg dataclass — 14 per-scanner *_seconds fields with documented defaults"
  - "RetryCfg dataclass — retry_count + backoff_base_seconds + backoff_max_seconds"
  - "ScanCfg.timeouts and ScanCfg.retry nested fields"
  - "Four deprecation-alias properties (timeout_seconds, fingerprint_timeout_seconds, tls_timeout_seconds, ssh_timeout_seconds) — warn-on-read, silent setters route to TimeoutsCfg"
  - "config_from_dict loader: [scan.timeouts] / [scan.retry] sub-tables + legacy flat key backward-compat"
affects: [41-03, 41-04, 41-08]

tech-stack:
  added: []
  patterns:
    - "@dataclass(init=False) + custom __init__ to accept legacy kwargs alongside new nested fields"
    - "Property + setter pair for deprecation aliases (read warns, write routes silently)"
    - "Sub-table loader pattern: pop sub-block from raw scan dict, route legacy flat keys only when sub-block absent"

key-files:
  created: []
  modified:
    - quirk/config.py
    - tests/test_timeouts_config.py
    - tests/test_cli_correctness.py

key-decisions:
  - "Property setters added (not just getters) — apply_profile() in quirk/engine/profiles.py still writes through legacy names; Plan 03 cleans the writers up"
  - "Setters route silently (no DeprecationWarning) — read-side warns are sufficient signal; double-warning on profile application would noise-flood the suite"
  - "@dataclass(init=False) + custom __init__ chosen over __post_init__ to make legacy kwarg routing explicit and self-documenting in the signature"
  - "test_template_field_alignment relaxed to allow legacy *_timeout_seconds keys — they're not fields anymore but remain valid template inputs through the loader's backward-compat path"

patterns-established:
  - "Deprecation-alias property pattern: getter emits DeprecationWarning + redirects to nested field; setter routes silently"
  - "Sub-table loader: pop sub-block, build cfg with only valid fields, then conditionally route legacy flat keys"

requirements-completed: [ROBUST-02, ROBUST-04]

duration: ~10 min
completed: 2026-04-29
---

# Phase 41 Plan 02: Wave 1 — TimeoutsCfg + RetryCfg + Deprecation Aliases Summary

**Canonical [scan.timeouts] / [scan.retry] sub-tables landed on ScanCfg with warn-on-read deprecation aliases for the four legacy flat fields; config_from_dict loads sub-tables and falls back to legacy flat keys when no sub-table is present.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-29
- **Completed:** 2026-04-29
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `TimeoutsCfg` dataclass added to `quirk/config.py` with 14 per-scanner timeout fields and the documented effective post-profile defaults (default=5, fingerprint=4, tls=6, ssh=6, jwt=10, container=120, source=300, dnssec=10, saml=10, kerberos=10, vault=10, db_connect=5, broker=10, email=10).
- `RetryCfg` dataclass added with `retry_count=0`, `backoff_base_seconds=1.0`, `backoff_max_seconds=5.0`.
- `ScanCfg` augmented with `timeouts: TimeoutsCfg` and `retry: RetryCfg` nested fields. Legacy flat fields (`timeout_seconds`, `fingerprint_timeout_seconds`, `tls_timeout_seconds`, `ssh_timeout_seconds`) converted to `@property` + `@*.setter` pairs — getters emit `DeprecationWarning` and redirect to `self.timeouts.*_seconds`; setters route silently to the same target.
- Custom `__init__` on `ScanCfg` accepts legacy `*_timeout_seconds` kwargs (e.g. `ScanCfg(timeout_seconds=5, ...)`) and routes them into the nested `TimeoutsCfg` so existing callers (`tests/test_broker_config_and_profile.py`, `tests/test_email_findings.py`, `quirk/interactive.py`) continue to work without DeprecationWarning noise at construction time.
- `config_from_dict` updated to pop `timeouts` / `retry` sub-blocks from `raw["scan"]`, build the nested cfgs, then conditionally route legacy flat keys into `TimeoutsCfg` only when no sub-block was provided.
- `tests/test_timeouts_config.py` rewritten — 4 xfail stubs replaced with 5 real test functions (sub-table load, deprecation warns, legacy flat backward-compat). All green.
- `tests/test_cli_correctness.py::test_template_field_alignment` relaxed to allow the four legacy `*_timeout_seconds` keys as valid template inputs.

## Task Commits

1. **Task 1: TimeoutsCfg + RetryCfg dataclasses + ScanCfg integration + loader** — `758e4c0` (feat)
2. **Task 2: Convert xfail stubs to real assertions + add property setters + relax template alignment test** — `855ea2e` (test)

## Files Created/Modified

- `quirk/config.py` — Added `TimeoutsCfg`, `RetryCfg`, `_LEGACY_TIMEOUT_KWARG_MAP`; replaced flat `*_timeout_seconds` fields on `ScanCfg` with `@property` + `@*.setter` pairs; added custom `__init__` for legacy-kwarg routing; updated `config_from_dict` to load sub-tables and route legacy flat keys.
- `tests/test_timeouts_config.py` — 4 xfail stubs replaced with 5 real test functions covering sub-table load, deprecation warns, and legacy backward-compat.
- `tests/test_cli_correctness.py` — `test_template_field_alignment` updated to accept legacy `*_timeout_seconds` keys.

## Decisions Made

- **Property setters in addition to getters:** `apply_profile()` in `quirk/engine/profiles.py` still does `setattr(scan, "tls_timeout_seconds", ...)` etc. Plan 03 will refactor it to write through `scan.timeouts.tls_seconds` directly, but until then, read-only properties broke the broker profile test. Added setters that route silently (no warning) to keep Plan 03's scope clean.
- **`@dataclass(init=False)` + custom `__init__`:** Chosen over `__post_init__` because legacy kwargs need to be _accepted but suppressed from the dataclass field set_. A custom `__init__` makes the legacy-kwarg signature explicit and self-documenting.
- **Setters silent, getters loud:** Construction-time warnings (e.g. when `apply_profile` writes through the alias) would create dozens of warnings per test run. Read-side warnings are the canonical signal; setters just need to work.
- **Template alignment test relaxed, not source-of-truth changed:** `config_template.yaml` could be migrated to use `[scan.timeouts]` syntax, but that's a Plan 03 / docs task. For Plan 02, the loader's backward-compat path is the contract; updating the test reflects that contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] apply_profile() writes through legacy alias names**
- **Found during:** Task 2 verification (broker profile test)
- **Issue:** `quirk/engine/profiles.py` calls `setattr(scan, "fingerprint_timeout_seconds", 4)` and similar for the other three legacy names. With Task 1's read-only `@property` declarations, these `setattr` calls raised `AttributeError: property 'fingerprint_timeout_seconds' of 'ScanCfg' object has no setter`, breaking `test_apply_profile_standard_enables_broker` and friends.
- **Fix:** Added `@*.setter` for each of the four deprecation-alias properties. Setters route silently to the corresponding `TimeoutsCfg.*_seconds` field (no DeprecationWarning fired on write — getter-only is the canonical signal, and setter warnings would noise-flood the suite during profile application).
- **Files modified:** `quirk/config.py`
- **Verification:** `pytest tests/test_broker_config_and_profile.py` — 5/5 pass.
- **Committed in:** `855ea2e`

**2. [Rule 3 — Blocking issue] test_template_field_alignment treats legacy aliases as unknown keys**
- **Found during:** Task 2 verification (full-suite regression check)
- **Issue:** `tests/test_cli_correctness.py::test_template_field_alignment` iterates `dataclasses.fields(ScanCfg)` and asserts every key in `config_template.yaml`'s `scan:` block maps to a real field. The four `*_timeout_seconds` keys are no longer fields (now properties), so the assertion failed — even though the loader still accepts them as valid template inputs.
- **Fix:** Extended the test's allowed-key set to include the four legacy aliases, with a comment explaining they're loader-routed for backward compat.
- **Files modified:** `tests/test_cli_correctness.py`
- **Verification:** `pytest tests/test_cli_correctness.py` — all 6 tests pass.
- **Committed in:** `855ea2e`

---

**Total deviations:** 2 auto-fixed Rule 3 (blocking) issues. No scope creep — both are direct backward-compat support for the dataclass-to-property migration that Task 1 introduced.

## Issues Encountered

None of substance. The pre-existing `tests/test_skip_registry.py::test_no_unregistered_skips` failure (3 unregistered skips in `conftest.py:111`, `test_broker_db_schema.py:70`, `test_cloud_connectors.py:154`) is by design — Plan 05 (D-04 stale-skip deletion) closes it. Verified by `git stash`-ing Plan 02 changes and re-running the gate test: same failure, same 3 lines. Not caused by this plan.

## Threat Flags

None. This plan changes config dataclass shape and adds backward-compat shims; no new network surface, auth path, file access, or trust boundary.

## Next Phase Readiness

- Plan 03 can now refactor `quirk/engine/profiles.py` to write through `scan.timeouts.*` directly (the setters added here let it proceed incrementally).
- Plan 03 can refactor scanners (`quirk/scanner/tls_scanner.py`, `quirk/scanner/ssh_scanner.py`, `quirk/discovery/*.py`) to read `cfg.scan.timeouts.<name>_seconds` instead of the legacy flat aliases.
- Plan 03 can also retire the `setattr`-by-string pattern in `apply_profile` once all writers move to the new sub-table.
- `RetryCfg` is in place for any retry/backoff wiring downstream plans need.

## Self-Check: PASSED

Files verified present:
- `quirk/config.py` (modified — `class TimeoutsCfg`, `class RetryCfg`, `timeouts: TimeoutsCfg`, `DeprecationWarning` all present)
- `tests/test_timeouts_config.py` (modified — 5 real test functions, 0 `@pytest.mark.xfail`, 0 `NotImplementedError`)
- `tests/test_cli_correctness.py` (modified — `legacy_timeout_aliases` block added)

Commits verified in `git log`:
- `758e4c0` — Task 1
- `855ea2e` — Task 2

Acceptance criteria all green:
- `grep -q "class TimeoutsCfg" quirk/config.py` ✓
- `grep -q "class RetryCfg" quirk/config.py` ✓
- `grep -q "DeprecationWarning" quirk/config.py` ✓
- `grep -q "timeouts: TimeoutsCfg" quirk/config.py` ✓
- `python -m compileall quirk/config.py -q` exit 0 ✓
- `pytest tests/test_timeouts_config.py` 5/5 pass ✓
- Smoke test (`config_from_dict({'scan':{'timeout_seconds':7,...}})` → `c.scan.timeouts.default_seconds == 7`) ✓
- `grep -c "@pytest.mark.xfail" tests/test_timeouts_config.py` → 0 ✓
- `grep -c "NotImplementedError" tests/test_timeouts_config.py` → 0 ✓
- 5 test functions in `tests/test_timeouts_config.py` ✓
- Full test suite: 678 passed, 7 skipped, 5 xfailed (1 deselected = the known Plan 05 gate-test stub) ✓

---
*Phase: 41-ci-stability-scanner-robustness*
*Plan: 02*
*Completed: 2026-04-29*
