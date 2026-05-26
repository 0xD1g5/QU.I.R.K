---
phase: 110
slug: cross-sensor-merge-scoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-25
---

# Phase 110 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml / pytest.ini (existing) |
| **Quick run command** | `pytest tests/ -k "merge or cbom_sensor or coverage_warning" -q` |
| **Full suite command** | `pytest tests/ -q && python -m compileall quirk run_scan.py` |
| **Estimated runtime** | ~60 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Requirement | Secure/Correct Behavior | Test Type | Automated Command | Status |
|-------------|------------------------|-----------|-------------------|--------|
| MERGE-01 | merge runs build_evidence_summary→compute_readiness_score→build_cbom over the union; engines not forked | unit | `pytest tests/ -k merge_pipeline` | ⬜ pending |
| MERGE-02 | merged score = Option A (union through engine), not an average of per-segment scores | unit | `pytest tests/ -k option_a` | ⬜ pending |
| MERGE-03 | same host:port in 2 segments → 2 distinct CBOM components (sensor_id in bom_ref); single-host (NULL) byte-stable | regression | `pytest tests/ -k "two_segment or bom_ref_stable"` | ⬜ pending |
| MERGE-04 | overdue enrolled sensor → non-null coverage_warning {missing_sensors,reason}; partial scored+flagged | unit | `pytest tests/ -k coverage_warning` | ⬜ pending |
| MERGE-05 | merged result has new scan_id; per-endpoint scanned_at NOT rewritten to merge time | unit | `pytest tests/ -k "scanned_at_preserved or merge_scan_id"` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Reuse `tests/test_cbom_builder.py` fixtures for the MERGE-03 two-segment regression
- [ ] Reuse `QUIRK_DB_PATH` conftest fixture for union-query / coverage tests
- [ ] No new pip dependencies (reuse existing scoring/CBOM engines)

*If a `merge_runs` table is added, declare it via the additive ORM-model path (Phase 107 D-01 idiom).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Physical two-segment same-IP reproduction | MERGE-03 / LAB-02 | Requires a real multi-network lab topology | Deferred to Phase 112 chaos-lab E2E |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
