---
phase: 01-foundation-fixes
plan: 04
subsystem: packaging
tags: [rename, branding, pyproject, quirk, qcscan, QU.I.R.K.]

# Dependency graph
requires:
  - phase: 01-foundation-fixes/01
    provides: scoring consolidation (writer.py stable before rename)
  - phase: 01-foundation-fixes/02
    provides: ssh-audit integration (all imports stable before rename)
  - phase: 01-foundation-fixes/03
    provides: sslyze integration (all imports stable before rename)
provides:
  - quirk/ package directory (renamed from qcscan/)
  - pyproject.toml with name=quirk and quirk=run_scan:main entry point
  - quirk/__init__.py with __version__ = "3.9.0"
  - Zero remaining qcscan/QuRisk references in .py files
affects: [all future phases — import from quirk.xxx not qcscan.xxx]

# Tech tracking
tech-stack:
  added: [pyproject.toml (setuptools>=68 build system)]
  patterns: [package named quirk, entry point via run_scan:main]

key-files:
  created:
    - quirk/__init__.py
    - pyproject.toml
  modified:
    - quirk/ (entire package — renamed from qcscan/)
    - run_scan.py
    - tests/*.py
    - config.yaml

key-decisions:
  - "Package renamed qcscan -> quirk per D-13; sed sweep across all .py files"
  - "pyproject.toml created with setuptools>=68 build backend per D-14"
  - "CLI entry point: quirk = run_scan:main per D-15"
  - "User-Agent header in fingerprint.py updated from qcscan to quirk"
  - "config.yaml db_path updated from output/qcscan.db to output/quirk.db"

patterns-established:
  - "All imports use from quirk.xxx — never from qcscan.xxx"
  - "Product name in user-facing strings is QU.I.R.K. (not QuRisk or qcscan)"

requirements-completed: [CORE-03]

# Metrics
duration: 3min
completed: 2026-03-29
---

# Phase 01 Plan 04: Package Rename Summary

**Full qcscan -> quirk rename with pyproject.toml: zero remaining qcscan/QuRisk references in .py files, all 56 tests pass, `python3 -c "import quirk; print(quirk.__version__)"` prints 3.9.0**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-29T19:16:26Z
- **Completed:** 2026-03-29T19:19:00Z
- **Tasks:** 2 of 2
- **Files modified:** 52 (including 47 renamed package files)

## Accomplishments

- Renamed `qcscan/` directory to `quirk/` — full git rename with history preserved
- Swept all 56 Python files: replaced `from qcscan.` imports, `@patch("qcscan.xxx")` strings, `"qcscan"` string literals
- Updated user-facing strings: argparse description, validate.py docstring, User-Agent header, config.yaml db_path
- Created `quirk/__init__.py` with `__version__ = "3.9.0"` and package docstring
- Created `pyproject.toml` with `name = "quirk"`, version, entry point `quirk = "run_scan:main"`
- Full test suite: 56/56 tests pass after rename

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename qcscan -> quirk package, update all references** - `3f0fd55` (feat)
2. **Task 2: Create pyproject.toml, verify test suite** - `64ec631` (chore)

## Files Created/Modified

- `quirk/` — renamed from `qcscan/`, all 47 source files preserved with content updated
- `quirk/__init__.py` — new: package init with `__version__ = "3.9.0"`
- `pyproject.toml` — new: build system config with quirk package metadata and entry point
- `run_scan.py` — description string updated to "QU.I.R.K. -- Quantum Infrastructure Readiness Kit"
- `quirk/validate.py` — docstring QuRisk -> QU.I.R.K.
- `quirk/scanner/fingerprint.py` — User-Agent header qcscan -> quirk
- `quirk/db.py` — comment updated from qcscan/models.py to quirk/models.py
- `config.yaml` — db_path updated from output/qcscan.db to output/quirk.db
- `tests/test_ssh_scanner.py`, `tests/test_sslyze_integration.py`, `tests/test_scoring_consolidation.py`, `tests/test_cert_pubkey_fix.py` — @patch paths updated

## Decisions Made

- Used `sed -i ''` multi-pass sweep: first pass for import statements, second for string literals, third broader pass for remaining `qcscan.` in any context (@patch strings in tests)
- `quirk/__init__.py` was empty (1 blank line) in original — replaced with docstring + `__version__`
- config.yaml `db_path` updated even though it's a YAML file (plan step 8 — correct behavior)
- `.claude/worktrees/` references intentionally left untouched — separate worktree scope

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Three-pass sed sweep to catch @patch strings in tests**
- **Found during:** Task 1 verification
- **Issue:** The initial two-pass sed only caught import lines and quoted string literals. The `@patch("qcscan.xxx")` decorator strings in tests had `qcscan.` embedded in a double-quoted string — a different pattern than `"qcscan"` (the package name alone).
- **Fix:** Added third sed pass: `s/qcscan\./quirk./g` on all `.py` files to catch any remaining `qcscan.` substring in any context.
- **Files modified:** `tests/test_ssh_scanner.py`, `tests/test_scoring_consolidation.py`
- **Verification:** `grep -rn "qcscan" . --include="*.py" --exclude-dir=.claude` returns 0 matches
- **Committed in:** `3f0fd55` (Task 1 commit)

**2. [Rule 1 - Bug] config.yaml db_path contained qcscan.db**
- **Found during:** Task 1 step 8 (config.yaml check)
- **Issue:** `config.yaml` had `db_path: "output/qcscan.db"` — not caught by the `.py`-only sed sweeps
- **Fix:** Updated directly via Edit tool to `output/quirk.db`
- **Files modified:** `config.yaml`
- **Committed in:** `3f0fd55` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes required for complete rename. No scope creep.

## Issues Encountered

- `python` command not available in shell (macOS system Python removed) — used `.venv/bin/python` and `python3` for verification. No code impact.

## Known Stubs

None — this plan performs a rename operation, not feature implementation. No data sources or UI rendering involved.

## Next Phase Readiness

- All imports across the codebase now use `from quirk.xxx` — Phase 01 is complete
- `python -c "import quirk; print(quirk.__version__)"` confirms package is importable
- `pyproject.toml` enables `pip install -e .` for future venv setup
- 56/56 tests pass — foundation is stable for Phase 2 (CBOM Pipeline)

---
*Phase: 01-foundation-fixes*
*Completed: 2026-03-29*
