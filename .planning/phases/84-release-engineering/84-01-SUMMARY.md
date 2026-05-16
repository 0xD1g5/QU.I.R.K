---
phase: 84-release-engineering
plan: 01
subsystem: release-engineering
tags: [releng, packaging, pypi, version-sot, pep621]
requirements_closed: [RELENG-01, RELENG-08]
decisions_logged: [v4.10-D-01, v4.10-D-02]
key_files:
  modified:
    - pyproject.toml
    - quirk/__init__.py
    - quirk/config.py
    - quirk/reports/writer.py
    - tests/test_version.py
    - .planning/PROJECT.md
commit: 9288408
completed: 2026-05-16
---

# Phase 84 Plan 01: PyPI Name Verify + Version Single-Source-of-Truth Summary

D-84-R1 implementation — `pyproject.toml [project.version]` is now the canonical
version source, every other surface derives from it via
`importlib.metadata.version("qu-i-r-k")` (or `tomllib` parse for unpackaged
dev runs), and the Phase 37 parity test was flipped to assert this new
direction across 6 surfaces with zero hardcoded version literals.

## PyPI Distribution Name Verification

**Command:** `pip index versions quirk`
**Date:** 2026-05-16
**Result (verbatim):**

```
quirk (0.1.3)
Available versions: 0.1.3, 0.1.2, 0.1.3
```

(Captured in `/tmp/pypi-quirk-check.txt`.)

The bare `quirk` distribution name is **TAKEN** on PyPI by an unrelated project
already at version 0.1.3. Per the pre-registered fallback decision in D-84-R1,
the distribution name was switched to **`qu-i-r-k`**. This decision is logged
as **v4.10 D-01** in `.planning/PROJECT.md` Key Decisions.

README badges, install commands (e.g. `pip install qu-i-r-k`,
`pip install qu-i-r-k[all]`), GitHub Actions Trusted Publishers config, and
release-process docs in subsequent Phase 84 plans (84-02..84-04) will derive
from this name. The `[project.optional-dependencies]` self-references in
`pyproject.toml` (e.g. `quirk[cloud]` → `qu-i-r-k[cloud]`) were updated in the
same atomic commit so the dependency graph remains internally consistent.

## Version Literal Locations Migrated

| Surface                                                                   | Before                                            | After (derives from pyproject.toml SoT)                       |
| ------------------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------- |
| `pyproject.toml [project.version]`                                        | `version = "4.4.0"`                               | `version = "4.10.0"` (canonical SoT)                          |
| `pyproject.toml [project.name]`                                           | `name = "quirk"`                                  | `name = "qu-i-r-k"`                                           |
| `quirk/__init__.py::__version__`                                          | `__version__ = "4.4.0"`                           | `importlib.metadata.version("qu-i-r-k")` + tomllib fallback   |
| `quirk/config.py::IntelligenceCfg.intelligence_version`                   | `str = "4.4.0"`                                   | `default_factory=lambda: __import__("quirk").__version__`     |
| `quirk/reports/writer.py::INTELLIGENCE_VERSION`                           | `"4.4.0"`                                         | `INTELLIGENCE_VERSION = PLATFORM_VERSION` (aliases SoT)       |
| `quirk/cbom/builder.py::PLATFORM_VERSION`                                 | `from quirk import __version__ as PLATFORM_VERSION` (already dynamic) | unchanged — already derived correctly         |
| `quirk/reports/writer.py::PLATFORM_VERSION`                               | `from quirk import __version__ as PLATFORM_VERSION` (already dynamic) | unchanged — already derived correctly         |
| `tests/test_version.py`                                                   | 4 hardcoded `assert ... == "4.4.0"` assertions    | `TRUTH` parsed from pyproject via tomllib; 6 dynamic assertions + 1 slow CLI subprocess test |

**Regression grep:** `grep -rn '"4.4.0"' quirk/ tests/test_version.py` → no matches.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing Critical Functionality] Extra version literal at `quirk/reports/writer.py:60`**
- **Found during:** Final verification (regression grep)
- **Issue:** The plan's `<interfaces>` block enumerated 4 version-bearing
  surfaces but missed `INTELLIGENCE_VERSION = "4.4.0"` defined as a
  module-level constant in `quirk/reports/writer.py` (used in report
  metadata). This is a 5th version-bearing literal that would have drifted
  silently on the next bump — exactly the failure mode D-84-R1 is designed to
  prevent.
- **Fix:** Replaced `INTELLIGENCE_VERSION = "4.4.0"` with
  `INTELLIGENCE_VERSION = PLATFORM_VERSION` so the constant aliases the
  already-dynamic `PLATFORM_VERSION` (imported from `quirk.__version__`).
- **Files modified:** `quirk/reports/writer.py`
- **Commit:** `9288408` (included in the atomic commit)

**2. [Rule 2 — Missing Critical Functionality] pyproject.toml self-references in `[project.optional-dependencies]`**
- **Found during:** Task 2 edit
- **Issue:** `[motion]` and `[all]` extras included self-references like
  `"quirk[cloud]"`, `"quirk[cbom]"`, etc. After renaming the distribution to
  `qu-i-r-k`, these references would fail to resolve at install time.
- **Fix:** Renamed all 7 self-references from `quirk[xxx]` to
  `qu-i-r-k[xxx]` to keep the dependency graph internally consistent with
  the new distribution name.
- **Files modified:** `pyproject.toml`
- **Commit:** `9288408` (included in the atomic commit)

### Authentication Gates
None.

## Verification Evidence

- `pytest tests/test_version.py -v -m 'not slow'` → **6/6 PASSED, 1 deselected (slow)** in 0.54s
- `python -c "from quirk import __version__; print(__version__)"` → `4.10.0` (resolves from installed package metadata via `importlib.metadata.version("qu-i-r-k")`, not a literal)
- `python -m compileall quirk/ -q` → clean, no warnings
- `grep -rn '"4.4.0"' quirk/ tests/test_version.py` → no matches (regression detection)
- `git log -1 --format='%H %s'` → `9288408 feat(84-01): pypi name verify + version single-source-of-truth (RELENG-01, RELENG-08)`

## Commit

**SHA:** `9288408`
**Message:** `feat(84-01): pypi name verify + version single-source-of-truth (RELENG-01, RELENG-08)`
**Files (6):** pyproject.toml, quirk/__init__.py, quirk/config.py, quirk/reports/writer.py, tests/test_version.py, .planning/PROJECT.md

## Self-Check: PASSED

- `[x]` pyproject.toml exists with `version = "4.10.0"` and `name = "qu-i-r-k"`
- `[x]` quirk/__init__.py uses `importlib.metadata.version` with tomllib fallback (no hardcoded literal)
- `[x]` quirk/config.py:279 `IntelligenceCfg.intelligence_version` derives from `quirk.__version__`
- `[x]` quirk/reports/writer.py:60 `INTELLIGENCE_VERSION` aliases `PLATFORM_VERSION` (SoT-derived)
- `[x]` tests/test_version.py reads TRUTH dynamically via tomllib, no hardcoded "4.4.0" or "4.10.0"
- `[x]` Commit 9288408 exists on HEAD
- `[x]` v4.10 D-01 (PyPI fallback name) logged in PROJECT.md Key Decisions
- `[x]` v4.10 D-02 (pyproject.toml SoT direction) logged in PROJECT.md Key Decisions
