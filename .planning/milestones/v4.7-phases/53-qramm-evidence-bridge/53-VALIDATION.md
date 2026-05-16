---
phase: 53
slug: qramm-evidence-bridge
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-07
---

# Phase 53 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project standard) |
| **Config file** | none — pytest discovers `tests/test_*.py` |
| **Quick run command** | `python -m pytest tests/test_qramm_evidence_bridge.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_qramm_evidence_bridge.py -x`
- **After every plan wave:** Run `python -m pytest tests/test_qramm_evidence_bridge.py tests/test_qramm_router.py tests/test_qramm_scoring.py -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 53-01-01 | 01 | 1 | QRAMM-12 | — | Bridge reads only from internal DB, no user input | unit | `pytest tests/test_qramm_evidence_bridge.py::test_no_risk_engine_import -x` | ❌ W0 | ⬜ pending |
| 53-01-02 | 01 | 1 | QRAMM-12 | — | D-02 skip-silently when no scan data | unit | `pytest tests/test_qramm_evidence_bridge.py::test_bridge_skips_when_no_scan_data -x` | ❌ W0 | ⬜ pending |
| 53-01-03 | 01 | 1 | QRAMM-12 | — | Bridge populates 30 CVI rows on session create | integration | `pytest tests/test_qramm_evidence_bridge.py::test_bridge_populates_on_session_create -x` | ❌ W0 | ⬜ pending |
| 53-01-04 | 01 | 1 | QRAMM-13 | — | RC4-HMAC scan → lower CVI 1.2 score than AES-256 scan | unit | `pytest tests/test_qramm_evidence_bridge.py::test_rc4_scan_lower_score_than_aes256 -x` | ❌ W0 | ⬜ pending |
| 53-02-01 | 02 | 1 | QRAMM-13 | — | Unconfirmed rows excluded from score; confirmed rows included | integration | `pytest tests/test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score -x` | ❌ W0 | ⬜ pending |
| 53-02-01b | 02 | 1 | QRAMM-13 | — | Confirmed rows (answer_value written via save_answers) included in score | integration | `pytest tests/test_qramm_evidence_bridge.py::test_confirmed_included_in_score -x` | ❌ W0 | ⬜ pending |
| 53-02-02 | 02 | 1 | QRAMM-13 | — | `confirmed_at` auto-set when `save_answers` writes `answer_value` | unit | `pytest tests/test_qramm_evidence_bridge.py::test_confirmed_at_auto_set -x` | ❌ W0 | ⬜ pending |
| 53-02-03 | 02 | 1 | QRAMM-14 | — | Badge signal: `suggested_answer IS NOT NULL AND answer_value IS NULL` | unit | `pytest tests/test_qramm_evidence_bridge.py::test_badge_signal_data_model -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_qramm_evidence_bridge.py` — stubs for QRAMM-12, QRAMM-13, QRAMM-14 (all tests in the verification map above)

*Existing `conftest.py` and the UUID-named in-memory DB pattern from `tests/test_qramm_router.py` covers all fixture needs — no new conftest additions required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| JSON blob extraction correctness (kerberos/ssh shape) | QRAMM-12 | Blob schemas assumed; automated tests use mocked blobs | Feed a real kerberos scan blob through `_walk_json_for_alg_strings` and verify algorithm strings are extracted |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (revision iter 1)
