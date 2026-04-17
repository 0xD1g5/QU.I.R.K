---
phase: 23
slug: dnssec-cbom-skip-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_cbom_builder.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q --ignore=tests/test_dashboard_wiring.py` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_cbom_builder.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q --ignore=tests/test_dashboard_wiring.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | DNSSEC-04 | — | N/A | unit | `python -m pytest tests/test_cbom_builder.py::test_dnssec_endpoint_algorithm_registered -x` | ❌ W0 | ⬜ pending |
| 23-01-02 | 01 | 1 | DNSSEC-04 | — | N/A | unit | `python -m pytest tests/test_cbom_builder.py::test_dnssec_endpoint_no_tls_protocol -x` | ❌ W0 | ⬜ pending |
| 23-01-03 | 01 | 1 | DNSSEC-04 | — | N/A | unit | `python -m pytest tests/test_cbom_builder.py::test_dnssec_endpoint_no_certificate -x` | ❌ W0 (RED test) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cbom_builder.py` — add `_dnssec_endpoint()` fixture + 3 DNSSEC test cases (2 immediately GREEN for Pass 1/Pass 3 correctness, 1 RED for Pass 2 skip list gap)

*Existing test infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
