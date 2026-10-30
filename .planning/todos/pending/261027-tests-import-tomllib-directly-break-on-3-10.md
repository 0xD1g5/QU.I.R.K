---
type: todo
created: 2026-10-27
source: Phase 232 (261015 residue)
priority: P3
area: tests/ (six test files), tests/pyproject_helpers.py
status: pending
owner: 999.119
---

# Six test files import `tomllib` directly and fail to import on Python 3.10

**Owner phase:** 999.119 (CI and chaos-lab hygiene; there is no Python 3.10 CI leg, which is why this is
invisible)

`pyproject.toml` declares `requires-python = ">=3.10"`, and Phase 232 kept that floor (D-06). `tomllib` is
stdlib only from 3.11. Phase 232 (commits `9e58bdb1`, `d61b0f92`) added `tests/pyproject_helpers.py`
(tomllib, then tomli, then a regex tier) and moved the two README tests onto it. Six other test files still
import `tomllib` directly, so on 3.10 they fail at collection.

Measured on 2026-10-27 with `grep -ln "^import tomllib\|^    import tomllib" tests/*.py`:

- `tests/test_brand_assets_freshness.py`
- `tests/test_packaging.py`
- `tests/test_safe_filter_audit.py`
- `tests/test_sanitize_scanner_text.py`
- `tests/test_skip_registry.py`
- `tests/test_version.py`

The research hypothesis was seven. The seventh, `tests/test_install_all_excludes_schemathesis.py`, already
does `try: import tomllib / except ImportError: import tomli` and is 3.10-safe. `quirk/__init__.py` keeps its
development-path `tomllib` import on purpose (D-06) and is not part of this todo.

Fix: move each file onto `tests/pyproject_helpers.py`, or a tomllib-then-tomli fallback where it parses
something other than the project version. Never `pytest.importorskip("tomllib")`: an unregistered skip is
rejected by `tests/test_skip_registry.py`, and a skip would hide the check on 3.10 (232-02 hit this).
Optionally add a 3.10 collection leg, or decide explicitly to raise the floor to 3.11.

## Feasibility & Effort

- **Feasibility:** CONFIRMED. The helper exists and two tests already use it.
- **Effort:** S. Six small import changes plus one collection run under Python 3.10 (for example a
  `python:3.10-slim` container with a fresh clone in a new empty directory) to prove it.
- **Unknowns:** whether any of the six parses TOML other than `pyproject.toml`, which would need the tomli
  fallback instead of the version helper. No spike needed.
