---
phase: 151
slug: phase-completion-artifact-gates
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-13
updated: 2026-08-14
---

# Phase 151 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing project standard) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| **Quick run command** | `pytest tests/test_verify_phase_gates.py -x` |
| **Full suite command** | `pytest -q -m ""` (per `CONTRIBUTING.md`) |
| **Estimated runtime** | 0.78s (measured, `44 passed`) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_verify_phase_gates.py -x`
- **After every plan wave:** Run `pytest -q -m ""`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 151-01-01 | 01 | 1 | ARTIFACT-01/02/03 | — | `check_phase_close()` + loaders implemented, pure/unit-tested | unit | `pytest tests/test_verify_phase_gates.py -x -k "check_phase_close or is_validation_stale or user_facing or uat_series or load_validation or load_phase_plan"` | ✅ | ✅ green |
| 151-01-02 | 01 | 1 | ARTIFACT-04 | — | `check_destructive_archive()` + loaders implemented, pure/unit-tested | unit | `pytest tests/test_verify_phase_gates.py -x -k "check_destructive_archive or disk_phase_dirs or archived_phase_dirs or parse_state_phase_maps"` | ✅ | ✅ green |
| 151-02-01 | 02 | 2 | ARTIFACT-01..04 | — | `main()` CLI glue wires loaders into the pure functions; multi-phase and STATE.md-only triggers detected | unit | `pytest tests/test_verify_phase_gates.py -x -k "main_returns or extract_phase_close_trigger or extract_state_phase_close"` | ✅ | ✅ green |
| 151-02-02 | 02 | 2 | ARTIFACT-01..04 | — | `.githooks/pre-commit` wrapper correctly invokes `main()` and propagates exit code against a real git repo | integration | `pytest tests/test_verify_phase_gates.py -x -k hook_integration` | ✅ | ✅ green |
| 151-02-03 | 02 | 2 | — | — | `CONTRIBUTING.md` documents the one-time `core.hooksPath` install | doc | `grep -c "Installing the pre-commit artifact gate" CONTRIBUTING.md` | ✅ | ✅ green |
| 151-03-01 | 03 | 3 | ARTIFACT-03 | — | `docs/UAT-SERIES.md` Series 151 entry exists | doc | `grep -c "## Series 151" docs/UAT-SERIES.md` | ✅ | ✅ green |
| 151-03-02 | 03 | 3 | — | — | Obsidian phase note + vault sync | doc | `obsidian vault="Digs" search query="path:20_Dev-Work/QUIRK/Phases/Phase-151"` | ✅ | ✅ green |
| (post-execution) | fix | — | ARTIFACT-04 | — | `_ACCEPTED_HISTORICAL_ARCHIVE_GAPS` exemption for Phase 144's permanent historical gap, milestone-scoped | unit | `pytest tests/test_verify_phase_gates.py -x -k accepted_historical_or_exception_is_milestone_scoped` | ✅ | ✅ green |
| (post-execution) | review-fix | — | ARTIFACT-01..04 | — | WR-01..04 (multi-phase trigger, STATE.md-only trigger, decimal sub-phases, dead-constant removal) | unit | `pytest tests/test_verify_phase_gates.py -q` (full file) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Post-execution result (2026-08-14):** `pytest tests/test_verify_phase_gates.py -q` → **44 passed**
in 0.78s. All ARTIFACT-01..04 gates, both post-execution fix rounds (Phase 144 exemption, 4
code-review Warnings), and the real end-to-end `hook_integration` suite (disposable temp git
repos, real `git commit` subprocess calls) are green.

---

## Wave 0 Requirements

- [x] `tests/test_verify_phase_gates.py` — created, covers ARTIFACT-01, ARTIFACT-02, ARTIFACT-03, ARTIFACT-04 (44 tests)
- [x] Fixture VALIDATION.md/VERIFICATION.md/UAT-SERIES.md snippets — reused real
  `147-VALIDATION.md` and `docs/UAT-SERIES.md` Series 150 heading as literal test fixtures
- [x] `.githooks/pre-commit` — created, executable, thin shell wrapper around `main()`

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s (measured: 0.78s for the full file)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-14 — reconciled post-execution against the real 44-test suite and
two post-execution fix rounds (Phase 144 historical-gap exemption, code-review Warnings WR-01..04).
This file was left in its pre-planning draft state after execution completed — caught by the
v5.12 milestone integration check, which is itself a live demonstration of exactly the staleness
class ARTIFACT-02 exists to prevent.
