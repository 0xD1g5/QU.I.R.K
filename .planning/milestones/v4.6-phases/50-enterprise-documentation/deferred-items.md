# Phase 50 — Deferred Items

| Category | Item | Status |
|----------|------|--------|
| test_env | `tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[broker]` (and other parametrizations) fails with `cyclonedx.exception.MissingOptionalDependencyException: This functionality requires optional dependencies. Please install cyclonedx-python-lib with the extra "json-validation"`. Pre-existing local-environment issue — unrelated to Phase 50 docs work (Phase 50 only modified `docs/architecture.md`, `docs/operators-guide.md`, `docs/UAT-SERIES.md`, the Obsidian vault, ROADMAP/STATE/REQUIREMENTS). | deferred — environment fix (install `cyclonedx-python-lib[json-validation]`); track separately from Phase 50 close |

Phase 50 docs-presence gate (`tests/test_phase50_docs_presence.py`) passed clean — 2 passed in 0.01s.
