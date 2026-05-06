---
phase: 42
slug: cbom-correctness-audit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Synthesized from `42-RESEARCH.md` §"Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (config in `pyproject.toml` `[tool.pytest.ini_options]`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_cbom_*.py -x` |
| **Full suite command** | `pytest` (excludes `slow` per `addopts = "-m 'not slow'"`) |
| **Estimated runtime** | ~30s for the cbom slice, ~3 min for the full suite |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_cbom_*.py -x`
- **After every plan wave:** `pytest`
- **Before `/gsd-verify-work`:** Full suite green AND `REGEN_CBOM_COVERAGE=1 pytest tests/test_cbom_classifier_coverage.py::test_regenerate_coverage_report -s` produces zero diff in `docs/cbom-classifier-coverage.md`
- **Max feedback latency:** ~30 seconds (cbom slice)

---

## Per-Task Verification Map

> Tasks are placeholder shells until `gsd-planner` writes `*-PLAN.md` files. Each task must be back-mapped here with concrete IDs (`42-01-01`, etc.) before plan-checker passes.

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| CBOM-01 | Per-profile JSON+XML validates against CycloneDX 1.6 strict schema | unit (no-network, no-Docker) | `pytest tests/test_cbom_schema_validation.py -x` | ❌ W0 | ⬜ pending |
| CBOM-02a | No `UNKNOWN` classification for any algorithm name surfaced by any profile | unit | `pytest tests/test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles -x` | ❌ W0 | ⬜ pending |
| CBOM-02b | `docs/cbom-classifier-coverage.md` is regenerable and up-to-date | unit (regen flag) | `REGEN_CBOM_COVERAGE=1 pytest tests/test_cbom_classifier_coverage.py::test_regenerate_coverage_report -s` | ❌ W0 | ⬜ pending |
| CBOM-03a | Existing motion goldens still match | unit | `pytest tests/test_cbom_motion_golden.py::test_email_cbom_matches_snapshot tests/test_cbom_motion_golden.py::test_broker_cbom_matches_snapshot -x` | ✅ | ⬜ pending |
| CBOM-03b | New shape goldens (pki / vault-or-database / saml-or-ldaps) match | unit | `pytest tests/test_cbom_motion_golden.py::test_pki_cbom_matches_snapshot tests/test_cbom_motion_golden.py::test_vault_cbom_matches_snapshot tests/test_cbom_motion_golden.py::test_saml_cbom_matches_snapshot -x` | ❌ W0 | ⬜ pending |
| CBOM-03c | `tests/fixtures/cbom/CHANGELOG.md` exists and references commit | manual (file-presence) | `test -f tests/fixtures/cbom/CHANGELOG.md && grep -q 'Phase 42' tests/fixtures/cbom/CHANGELOG.md` | ❌ W0 | ⬜ pending |
| CBOM-04a | Each label in `MOTION_PLAINTEXT_PROTOCOLS` is skipped at Pass 2 + Pass 3 | unit (parametrized) | `pytest tests/test_cbom_skip_lists.py -x` | ❌ W0 | ⬜ pending |
| CBOM-04b | Each label in `DAR_SKIP_PROTOCOLS` is skipped at Pass 2 + Pass 3 | unit (parametrized) | `pytest tests/test_cbom_skip_lists.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — change pin to `cyclonedx-python-lib[validation]>=11.7.0,<12` and reinstall (`pip install -e .`). Without this, all CBOM-01 tests raise `MissingOptionalDependencyException`.
- [ ] `tests/test_cbom_schema_validation.py` — new file, covers CBOM-01.
- [ ] `tests/test_cbom_classifier_coverage.py` — new file, covers CBOM-02.
- [ ] `tests/test_cbom_skip_lists.py` — new file, covers CBOM-04.
- [ ] Endpoint synthesizers in `tests/test_cbom_motion_endpoints.py` (extend) — `_build_pki_lab_endpoints`, `_build_vault_lab_endpoints` (or `_build_database_lab_endpoints`), `_build_saml_lab_endpoints` (or `_build_ldaps_lab_endpoints`).
- [ ] `tests/fixtures/cbom/expected_pki_cbom.json`, `expected_vault_cbom.json` (or `_database_`), `expected_saml_cbom.json` (or `_ldaps_`) — generated via `REGEN_CBOM_FIXTURES=1`.
- [ ] `tests/fixtures/cbom/CHANGELOG.md` — new file (D-09).
- [ ] `docs/cbom-classifier-coverage.md` — new generated artifact (D-05).
- [ ] `quirk/cbom/builder.py` — extract `MOTION_PLAINTEXT_PROTOCOLS` and `DAR_SKIP_PROTOCOLS` module-level constants; replace literals at lines 436-440 and 519-523.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `tests/fixtures/cbom/CHANGELOG.md` rationale entry is *meaningful* (human-readable explanation, not boilerplate) | CBOM-03 (D-09) | Subjective quality check — automation can confirm presence of "Phase 42" string but not whether the rationale is informative | Reviewer reads CHANGELOG entry and confirms it explains the structural change, not just lists the new fixture filenames |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (8 items above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s for cbom slice
- [ ] `nyquist_compliant: true` set in frontmatter (after planner back-fills task IDs)

**Approval:** pending
