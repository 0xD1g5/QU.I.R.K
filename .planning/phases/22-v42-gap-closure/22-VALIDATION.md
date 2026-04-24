---
phase: 22
slug: v42-gap-closure
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-24
---

# Phase 22 — Validation Strategy

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
| 22-01-01 | 01 | 1 | DNSSEC-04 | T-22-02 | No NameError crash when identity scanners invoked | static | `python -c "with open('run_scan.py') as f: assert 'main_logger' not in f.read()"` | ✅ | ✅ green |
| 22-01-02 | 01 | 1 | SAML-05 | T-22-01 | SAML algorithm registered in CBOM Pass 1 | unit | `python -m pytest tests/test_cbom_builder.py::test_saml_endpoint_algorithm_registered -x` | ✅ | ✅ green |
| 22-01-03 | 01 | 1 | SAML-05 | T-22-01 | No spurious TLS protocol for SAML | unit | `python -m pytest tests/test_cbom_builder.py::test_saml_endpoint_no_tls_protocol -x` | ✅ | ✅ green |
| 22-01-04 | 01 | 1 | SAML-05 | T-22-01 | No spurious certificate for SAML | unit | `python -m pytest tests/test_cbom_builder.py::test_saml_endpoint_no_certificate -x` | ✅ | ✅ green |
| 22-01-05 | 01 | 1 | KERB-04 | T-22-01 | Kerberos etype algorithm registered in CBOM | unit | `python -m pytest tests/test_cbom_builder.py::test_kerberos_endpoint_algorithm_registered -x` | ✅ | ✅ green |
| 22-01-06 | 01 | 1 | KERB-04 | T-22-01 | No spurious TLS protocol for Kerberos | unit | `python -m pytest tests/test_cbom_builder.py::test_kerberos_endpoint_no_tls_protocol -x` | ✅ | ✅ green |
| 22-01-07 | 01 | 1 | KERB-04 | T-22-01 | No spurious certificate for Kerberos | unit | `python -m pytest tests/test_cbom_builder.py::test_kerberos_endpoint_no_certificate -x` | ✅ | ✅ green |
| 22-01-08 | 01 | 1 | KERB-04 | — | Synthetic kerberos-unreachable excluded | unit | `python -m pytest tests/test_cbom_builder.py::test_kerberos_unreachable_excluded -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing test infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E identity scan completes and populates DB columns | DNSSEC-04, SAML-05, KERB-04 (SC #2) | Requires live targets: DNS zone with DNSSEC, SAML IdP metadata URL, Kerberos KDC | Configure `enable_dnssec: true`, `enable_saml: true`, `enable_kerberos: true` with valid targets. Run `python run_scan.py`. Verify `dnssec_scan_json`, `saml_scan_json`, `kerberos_scan_json` columns are non-null in SQLite. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-24

---

## Validation Audit 2026-04-24

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Manual-only | 1 |
| Total automated | 8 |
