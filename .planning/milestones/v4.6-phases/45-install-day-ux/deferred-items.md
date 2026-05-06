# Deferred items — Phase 45

## 2026-05-03 — Plan 45-03 phase-gate sweep
- `tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[*]` — pre-existing failure unrelated to Phase 45. Root cause: `cyclonedx-python-lib` installed without the `json-validation` extra, so `JsonStrictValidator.validate_str` raises `MissingOptionalDependencyException`. Verified pre-existing by `git stash` test on parent commit. Resolution: add `cyclonedx-python-lib[json-validation]` to dev/test requirements (or `pip install 'cyclonedx-python-lib[json-validation]'` in CI). NOT Phase 45's responsibility.
