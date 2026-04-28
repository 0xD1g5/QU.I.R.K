---
phase: 33-broker-scanner
plan: "02"
subsystem: config
tags: [phase-33, broker-scanner, config, profile-gating, pyproject]
dependency_graph:
  requires: []
  provides: [ConnectorsCfg.enable_broker, ConnectorsCfg.broker_azure_namespaces, ConnectorsCfg.broker_sqs_regions, apply_profile-broker-gating, pyproject-kafka-redis-extras]
  affects: [quirk/config.py, quirk/engine/profiles.py, pyproject.toml, quirk/config_template.yaml]
tech_stack:
  added: []
  patterns: [dataclass-field-extension, profile-gate-mirror, _as_str_list-coercion, pyproject-sub-extras]
key_files:
  created: [tests/test_broker_config_and_profile.py]
  modified: [quirk/config.py, quirk/engine/profiles.py, pyproject.toml, quirk/config_template.yaml]
decisions:
  - cfg.connectors namespace chosen over cfg.scanners — mirrors Phase 32 email precedent; cfg.scanners does not exist in config.py
  - _as_str_list() coercion added explicitly for broker list fields (T-33-03 mitigate disposition)
  - SimpleNamespace duck-type used for profile tests (mirrors Phase 32 test_email_findings.py _mk_cfg() pattern)
metrics:
  duration: "~15 minutes"
  completed: "2026-04-28"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 5
---

# Phase 33 Plan 02: Broker Config + Profile Gating Summary

**One-liner:** Wired `enable_broker` flag + cloud-target list fields into `ConnectorsCfg`, added `_as_str_list()` coercion for T-33-03, gated broker in `apply_profile()` (standard/deep=True, quick=False), and declared `[kafka]`/`[redis]` sub-extras in `pyproject.toml` per D-06/STRUCT-02.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add enable_broker + cloud-target list fields to ConnectorsCfg | 5e58d5c | quirk/config.py, quirk/config_template.yaml |
| 2 | Profile gating in apply_profile() + pyproject.toml sub-extras | 67b1537 | quirk/engine/profiles.py, pyproject.toml |
| 3 | tests/test_broker_config_and_profile.py — 5 tests | 0879d30 | tests/test_broker_config_and_profile.py |

## What Was Built

### Task 1: ConnectorsCfg fields + config_template.yaml

Added three new fields to `ConnectorsCfg` in `quirk/config.py`:

```python
# Broker scanner enable flag (v4.4 Phase 33 — D-10)
enable_broker: bool = False
# Cloud broker targets (D-01) — supplied via CLI/config only; no SDK enumeration (D-02)
broker_azure_namespaces: List[str] = field(default_factory=list)
broker_sqs_regions: List[str] = field(default_factory=list)
```

Added explicit `_as_str_list()` coercion in `config_from_dict()` before the `ConnectorsCfg(**conn_raw)` splat — ensures scalar YAML values (`broker_azure_namespaces: ns-prod`) are coerced to lists before hostname construction downstream (T-33-03 mitigate).

`quirk/config_template.yaml` documents the defaults under the connectors block.

### Task 2: Profile gating + pyproject.toml

`apply_profile()` in `quirk/engine/profiles.py` now gates `enable_broker` identically to `enable_email`:
- **quick:** no mutation (default `False` stays)
- **standard:** sets `enable_broker = True` if not already True
- **deep:** sets `enable_broker = True` if not already True

All three blocks are `hasattr`-guarded to survive duck-type configs used in tests.

`pyproject.toml` updated:
- Removed Phase 33 placeholder comment from `motion = [...]`
- Added `kafka = ["kafka-python>=2.0"]` (D-06, STRUCT-02)
- Added `redis = ["redis>=5.0"]` (D-06, STRUCT-02)

### Task 3: Regression tests

`tests/test_broker_config_and_profile.py` — 5 tests, all passing:

1. `test_connectors_cfg_defaults` — verifies `enable_broker=False`, both lists empty
2. `test_config_from_dict_hydrates_broker_lists` — verifies D-01 list hydration from raw dict
3. `test_apply_profile_standard_enables_broker` — standard profile gates broker on
4. `test_apply_profile_deep_enables_broker` — deep profile gates broker on
5. `test_apply_profile_quick_leaves_broker_disabled` — quick profile leaves broker off

## Namespace Decision

The plan originally cited `cfg.scanners.broker_enabled` in some places. The actual codebase uses `cfg.connectors.*` for all scanner enable flags (verified from Phase 32 `enable_email` precedent at line 101 of config.py). This plan correctly uses `cfg.connectors.enable_broker`. The revision note in CONTEXT.md D-10 confirms this decision.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] config_from_dict({}) fails without required fields**
- **Found during:** Task 3 test execution
- **Issue:** The plan's `_base_cfg()` helper called `config_from_dict({})` which raised `KeyError: 'assessment'` because AppConfig requires assessment, scan, targets, output blocks
- **Fix:** Used `SimpleNamespace` duck-type pattern from Phase 32's `test_email_findings.py:_mk_cfg()` for profile-gating tests; added `_MINIMAL_RAW` dict for the `config_from_dict` hydration test
- **Files modified:** tests/test_broker_config_and_profile.py
- **Commit:** 0879d30

**2. [Rule 3 - Blocking] pyproject.toml tomllib verify command mode mismatch**
- **Found during:** Task 2 verification
- **Issue:** Plan's verify command used `open('pyproject.toml','rb').read()` but `tomllib.loads()` requires `str` not `bytes` in Python 3.14 (use `tomllib.load(rb_file)` or `tomllib.loads(str_text)`)
- **Fix:** Used `open('pyproject.toml','r').read()` for verification — did not change implementation files, only corrected the test command
- **Commit:** n/a (verification only)

## Threat Surface

No new network endpoints or auth paths introduced. All changes are config-layer only. T-33-03 mitigation applied via `_as_str_list()` coercion before downstream hostname construction.

## Known Stubs

None. Fields are wired and tested; no placeholder values flow to rendering.

## Self-Check: PASSED

- quirk/config.py: enable_broker, broker_azure_namespaces, broker_sqs_regions fields present
- quirk/engine/profiles.py: enable_broker gating in standard and deep branches
- pyproject.toml: kafka and redis sub-extras declared
- quirk/config_template.yaml: broker scanner section documented
- tests/test_broker_config_and_profile.py: 5/5 tests passing
- Commits 5e58d5c, 67b1537, 0879d30 present in git log
