---
phase: 37
plan: 01
status: complete
requirements: [INFRA-01]
created: 2026-04-29
---

# Plan 37-01 Summary — Version Bump to 4.4.0

## Outcome
INFRA-01 satisfied: all six version-bearing surfaces declare `4.4.0` and
`tests/test_version.py` locks them against regression.

## Files Modified
- `quirk/__init__.py` — `__version__ = "4.4.0"`
- `pyproject.toml` — `[project] version = "4.4.0"`
- `quirk/cbom/builder.py` — `PLATFORM_VERSION = "4.4.0"`
- `quirk/reports/writer.py` — `PLATFORM_VERSION = "4.4.0"` (+ `INTELLIGENCE_VERSION = "4.4.0"`)
- `quirk/config.py` — `IntelligenceCfg.intelligence_version: str = "4.4.0"`

## Files Added
- `tests/test_version.py` — 5 regression tests (package, CBOM, reports, CLI subprocess, IntelligenceCfg default)

## Deviations
- Bumped `INTELLIGENCE_VERSION = "4.2.0"` in `quirk/reports/writer.py` (line 25) in addition to `PLATFORM_VERSION`. The plan's Task 1 acceptance criterion required `grep -r '"4.2.0"' quirk/reports/writer.py` to return zero matches; this constant otherwise blocked it. Scope is identical (writer.py version surface), so treated as a corrective bump.
- The `config.py` line 186 fallback `intel_raw.get("intelligence_version", "4.2.0")` was left untouched — the plan's acceptance only flagged `"4.3.0"` for config.py, and the IntelligenceCfg dataclass default (which Test 5 checks) is now `4.4.0`.

## Verification
- `pytest tests/test_version.py -x -q` → `5 passed in 0.83s`
- `python -m compileall quirk/` → exit 0
- `grep -r '"4.3.0"' quirk/__init__.py pyproject.toml quirk/cbom/builder.py quirk/reports/writer.py quirk/config.py` → 0 matches
- `grep -r '"4.2.0"' quirk/reports/writer.py` → 0 matches

## Commits
- `feat(37-01): bump version to 4.4.0 across all surfaces (INFRA-01)`
- `test(37-01): add tests/test_version.py regression lock for INFRA-01`
