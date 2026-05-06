---
phase: 51
slug: qramm-core-infrastructure
status: active
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-05
---

# Phase 51 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none (pytest discovers `tests/test_*.py` by convention) |
| **Quick run command** | `python -m pytest tests/test_qramm_questions.py tests/test_qramm_scoring.py tests/test_qramm_router.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_qramm_questions.py tests/test_qramm_scoring.py tests/test_qramm_router.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 51-01-01 | 01 | 1 | QRAMM-01 | T-51-01 | ORM models extend Base with correct column types; no raw DDL strings | unit | `python -m pytest tests/ -x -k "qramm"` | ⬜ pending |
| 51-01-02 | 01 | 1 | QRAMM-01 | T-51-01 | `_ensure_qramm_tables()` uses `create_all(checkfirst=True)`; idempotent on existing DB | unit | `python -m pytest tests/ -x -k "qramm"` | ⬜ pending |
| 51-02-01 | 02 | 1 | QRAMM-04 | — | scoring.py has zero imports from risk_engine or scanner modules | unit | `python -m pytest tests/test_qramm_scoring.py -x` | ⬜ pending |
| 51-02-02 | 02 | 1 | QRAMM-03 | — | QRAMM_QUESTIONS list has exactly 120 entries with required schema fields | unit | `python -m pytest tests/test_qramm_questions.py -x` | ⬜ pending |
| 51-03-01 | 03 | 2 | QRAMM-02 | T-51-02 | All 5 endpoint families return correct HTTP status codes; Pydantic validates payloads | integration | `python -m pytest tests/test_qramm_router.py -x` | ⬜ pending |
| 51-03-02 | 03 | 2 | QRAMM-02 | T-51-02 | Router registered at `/api/qramm/`; `quirk serve` starts without ImportError | integration | `python -m compileall quirk/ && python -m pytest tests/test_qramm_router.py -x` | ⬜ pending |
| 51-04-01 | 04 | 3 | QRAMM-03, QRAMM-04 | — | test_qramm_questions: count==120, schema fields present; test_qramm_scoring: weakest-link = min(), reference calc matches | unit | `python -m pytest tests/test_qramm_questions.py tests/test_qramm_scoring.py -x` | ⬜ pending |
| 51-04-02 | 04 | 3 | QRAMM-01, QRAMM-02 | T-51-01, T-51-02 | test_qramm_router: all 5 families smoke-tested; table-existence verified on fresh DB | integration | `python -m pytest tests/test_qramm_router.py -x` | ⬜ pending |
| 51-05-01 | 05 | 1 | DEBT-01 | — | Zero `DeprecationWarning: datetime.utcnow()` in test output after fix | unit | `python -m pytest tests/test_saml_scanner.py tests/test_broker_scanner_redis.py -x -W error::DeprecationWarning` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — pytest is already installed and `tests/conftest.py` provides shared fixtures. No Wave 0 setup needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0: existing infrastructure sufficient (no stubs needed)
- [x] No watch-mode flags
- [x] Feedback latency < 51s (~30s estimated)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-05
