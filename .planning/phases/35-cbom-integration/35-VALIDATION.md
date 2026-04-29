---
phase: 35
slug: cbom-integration
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
updated: 2026-04-29
---

<!-- Generated 2026-04-29 by Phase 37 Plan 37-04 (D-05): file did not exist; phase 35 shipped CBOM-01..04 (Plans 35-01..35-04) but the VALIDATION trail was missing. Re-validated against `python -m pytest tests/test_cbom*.py` → 101 passed, 1 skipped. -->

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_cbom_motion_endpoints.py tests/test_cbom_motion_golden.py -q` |
| **Full suite command** | `python -m pytest tests/test_cbom*.py -q` |
| **Estimated runtime** | ~5 seconds (motion subset) / ~10 seconds (all CBOM) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (CBOM motion subset)
- **After every plan wave:** Run full CBOM suite
- **Before `/gsd-verify-work`:** Full suite must be green (`python -m pytest -x -q`)
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirements | Test Type | Automated Command | Status |
|---------|------|------|--------------|-----------|-------------------|--------|
| 35-01-01 | 01 | 1 | CBOM-01 (TDD RED) | unit (synthesized endpoints) | `python -m pytest tests/test_cbom_motion_endpoints.py -q` | ✅ green |
| 35-02-01 | 02 | 2 | CBOM-02 (motion endpoint emission) | unit | `python -m pytest tests/test_cbom_builder.py -q` | ✅ green |
| 35-02-02 | 02 | 2 | CBOM-02 (classifier coverage) | unit | `python -m pytest tests/test_cbom_classifier.py -q` | ✅ green |
| 35-03-01 | 03 | 3 | CBOM-03 (writer integration) | unit | `python -m pytest tests/test_cbom_writer.py -q` | ✅ green |
| 35-03-02 | 03 | 3 | CBOM-03 (end-to-end CBOM) | integration | `python -m pytest tests/test_cbom_integration.py -q` | ✅ green |
| 35-04-01 | 04 | 4 | CBOM-04 (golden fixtures) | snapshot | `python -m pytest tests/test_cbom_motion_golden.py -q` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Aggregate: `python -m pytest tests/test_cbom*.py -q` → **101 passed, 1 skipped** as of 2026-04-29.

---

## Wave 0 Requirements

- [x] `tests/test_cbom_motion_endpoints.py` — RED-state TDD harness (created by Plan 35-01)
- [x] `tests/test_cbom_motion_golden.py` — golden snapshots (created by Plan 35-04)
- [x] No new framework install — pytest already in project

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generated CBOM is CycloneDX-spec valid | CBOM-03 | XSD validation lives outside pytest harness | Generate a CBOM (`run_scan.py --output …`) and run `cyclonedx validate --input-file <cbom.json>`; expect zero errors |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers MISSING references — Plan 35-01 created the RED harness
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-29 (generated retroactively by Phase 37 Plan 37-04)
