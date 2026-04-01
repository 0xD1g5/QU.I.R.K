---
phase: 07-polish-and-packaging
plan: 05
subsystem: packaging
tags: [version-bump, cli, init-command, importlib-resources, config-template, docs]

# Dependency graph
requires:
  - phase: 07-01
    provides: jinja2+rich as core deps, TDD scaffold with test stubs, init subcommand intercept in run_scan.py
  - phase: 07-02
    provides: CLI banner and --version flag updated to show QU.I.R.K. branding
provides:
  - quirk/__init__.py with __version__ = "4.0.0"
  - pyproject.toml with version = "4.0.0" and config_template.yaml in package-data
  - quirk/config_template.yaml bundled starter config with 127.0.0.1 default target
  - quirk/cli/init_cmd.py run_init() function using importlib.resources, warns on overwrite
  - docs/getting-started.md updated with git+https install as primary path and quirk init quick start
affects: [07-03, 07-04, packaging, docs, onboarding]

# Tech tracking
tech-stack:
  added: [importlib.resources (Python 3.10+ stdlib), shutil.copy2]
  patterns: [bundled config template via importlib.resources, overwrite-safe init command]

key-files:
  created:
    - quirk/config_template.yaml
    - (quirk/cli/init_cmd.py fully implemented — was stub)
  modified:
    - quirk/__init__.py
    - pyproject.toml
    - quirk/reports/writer.py
    - docs/getting-started.md

key-decisions:
  - "importlib.resources.files('quirk').joinpath('config_template.yaml') used for template lookup — works after pip install; os.path fallback for dev installs"
  - "config_template.yaml defaults to 127.0.0.1 so quirk init + quirk scan --config config.yaml works out-of-box with chaos lab loopback target"
  - "quirk init warns (not errors) on overwrite — exits 0 with warning, preserving idempotent UX for automation"
  - "docs/getting-started.md primary install path changed to git+https GitHub URL; PyPI coming-soon note removed"

patterns-established:
  - "Bundled config template: package resource loaded via importlib.resources.files() then str() for path extraction"
  - "Overwrite-safe file creation: os.path.exists check before copy, warning on collision"

requirements-completed: [BRAND-04]

# Metrics
duration: 8min
completed: 2026-04-01
---

# Phase 7 Plan 05: Version Bump, quirk init, and Getting-Started Update Summary

**Version bumped to 4.0.0 across __init__.py, pyproject.toml, and writer.py; quirk init implemented using importlib.resources with bundled config_template.yaml; getting-started.md updated to git+https install path**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-01T01:42:03Z
- **Completed:** 2026-04-01T01:50:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- `quirk/__version__` = "4.0.0" — bumped from 3.9.0 throughout (init, pyproject.toml, writer.py)
- `quirk init --output config.yaml` now creates a valid config from bundled template; warns instead of overwriting on re-run
- `docs/getting-started.md` shows GitHub git+https URL as primary install path with a Quick Start section for `quirk init`
- `quirk/config_template.yaml` created with 127.0.0.1 default target, all top-level config keys with inline comments

## Task Commits

1. **Task 1: Bump version to 4.0.0 and create quirk/config_template.yaml** - `8dfdff9` (feat)
2. **Task 2: Implement quirk/cli/init_cmd.py and update docs/getting-started.md** - `51d367d` (feat)

## Files Created/Modified

- `quirk/__init__.py` — __version__ bumped to "4.0.0"
- `pyproject.toml` — version bumped to "4.0.0", [tool.setuptools.package-data] section added
- `quirk/reports/writer.py` — PLATFORM_VERSION="4.0", INTELLIGENCE_VERSION="4.0.0"
- `quirk/config_template.yaml` — bundled starter config with assessment/targets/scan/output keys and inline docs
- `quirk/cli/init_cmd.py` — full run_init() implementation replacing stub
- `docs/getting-started.md` — primary install via git+https, Quick Start section with quirk init steps

## Decisions Made

- Used `importlib.resources.files('quirk').joinpath('config_template.yaml')` — works for both editable installs and pip-installed packages, with `os.path` fallback for edge cases
- `quirk init` exits 0 on overwrite (warning only) — idempotent behavior suits automation / CI workflows
- Getting-started.md primary path is git+https GitHub install; git clone / editable install retained as secondary option for contributors

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

`tests/test_packaging.py::test_package_data_templates` (templates dir / report.html.j2) was already failing before this plan ran — it depends on Plan 03 (HTML report template) which runs in parallel. This failure is pre-existing and out of scope per deviation rules scope boundary. Plan 05's 6 directly-owned tests all pass (test_version_is_4_0_0, test_run_scan_importable, test_pyproject_has_jinja2, test_pyproject_has_rich, test_init_creates_config, test_init_no_overwrite).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Version 4.0.0 is canonical throughout the codebase — ready for final polish/packaging steps
- `quirk init` is fully functional; onboarding flow (install → init → scan) is complete end-to-end
- Plan 03 (HTML report template) must run to resolve `test_package_data_templates` pre-existing failure

---
*Phase: 07-polish-and-packaging*
*Completed: 2026-04-01*
