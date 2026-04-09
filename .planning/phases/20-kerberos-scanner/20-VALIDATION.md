---
phase: 20
slug: kerberos-scanner
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_kerberos_scanner.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_kerberos_scanner.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 0 | KERB-01 | unit (RED) | `python -m pytest tests/test_kerberos_scanner.py::test_as_req_probe_returns_etypes -x -q` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 0 | KERB-02 | unit (RED) | `python -m pytest tests/test_kerberos_scanner.py::test_etype_classifier -x -q` | ❌ W0 | ⬜ pending |
| 20-01-03 | 01 | 0 | KERB-03 | unit (RED) | `python -m pytest tests/test_kerberos_scanner.py::test_tcp_fallback_on_udp_block -x -q` | ❌ W0 | ⬜ pending |
| 20-01-04 | 01 | 0 | KERB-04 | unit (RED) | `python -m pytest tests/test_kerberos_scanner.py::test_kerberos_db_row -x -q` | ❌ W0 | ⬜ pending |
| 20-01-05 | 01 | 0 | KERB-05 | integration (RED) | `python -m pytest tests/test_kerberos_scanner.py::test_ldap_graceful_degrade -x -q` | ❌ W0 | ⬜ pending |
| 20-02-01 | 02 | 1 | KERB-01 | unit (GREEN) | `python -m pytest tests/test_kerberos_scanner.py::test_as_req_probe_returns_etypes -x -q` | ✅ | ⬜ pending |
| 20-02-02 | 02 | 1 | KERB-02 | unit (GREEN) | `python -m pytest tests/test_kerberos_scanner.py::test_etype_classifier -x -q` | ✅ | ⬜ pending |
| 20-02-03 | 02 | 1 | KERB-03 | unit (GREEN) | `python -m pytest tests/test_kerberos_scanner.py::test_tcp_fallback_on_udp_block -x -q` | ✅ | ⬜ pending |
| 20-02-04 | 02 | 1 | KERB-04 | integration (GREEN) | `python -m pytest tests/test_kerberos_scanner.py::test_kerberos_db_row -x -q` | ✅ | ⬜ pending |
| 20-02-05 | 02 | 1 | KERB-05 | integration (GREEN) | `python -m pytest tests/test_kerberos_scanner.py::test_ldap_graceful_degrade -x -q` | ✅ | ⬜ pending |
| 20-02-06 | 02 | 2 | KERB-05 | integration | `docker compose --profile kerberos up -d && python -m pytest tests/test_kerberos_integration.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_kerberos_scanner.py` — unit test stubs for KERB-01 through KERB-05 (all RED initially)
- [ ] `tests/test_kerberos_integration.py` — Samba DC integration test stub (RED)
- [ ] `tests/conftest.py` — update with kerberos mock fixtures (mock KDC response, mock LDAP)

*Existing pytest infrastructure covers framework; only test files need creation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Samba DC responds to real AS-REQ with RC4 etype 23 | KERB-01 | Requires live Docker Samba DC | `docker compose --profile kerberos up -d; python run_scan.py --target localhost --enable-kerberos` |
| Port 389 conflict not triggered when both kerberos+identity profiles active | KERB-05 | Mutual-exclusion must be verified by observation | Start only one profile at a time; document in chaos lab README |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
