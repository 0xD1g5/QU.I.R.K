---
phase: 18
slug: dnssec-scanner
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-08
updated: 2026-04-24
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_dnssec_scanner.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds (unit), ~60 seconds (full with integration) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_dnssec_scanner.py -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green (238 + new tests)
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | DNSSEC-01 | unit (mocked) | `pytest tests/test_dnssec_scanner.py::test_dnskey_query_do_bit -x` | ✅ | ✅ green |
| 18-01-02 | 01 | 1 | DNSSEC-02 | unit | `pytest tests/test_dnssec_scanner.py::test_algorithm_classification -x` | ✅ | ✅ green |
| 18-01-03 | 01 | 1 | DNSSEC-03 | unit (mocked) | `pytest tests/test_dnssec_scanner.py::test_unsigned_zone -x` | ✅ | ✅ green |
| 18-01-04 | 01 | 1 | DNSSEC-04 | unit | `pytest tests/test_dnssec_scanner.py::test_cbom_integration -x` | ✅ | ✅ green |
| 18-01-05 | 01 | 1 | DNSSEC-05 | unit (mocked) | `pytest tests/test_dnssec_scanner.py::test_nsec_detection -x` | ✅ | ✅ green |
| 18-01-06 | 01 | 1 | DNSSEC-06 | unit | `pytest tests/test_dnssec_scanner.py::test_ds_chain_broken -x` | ✅ | ✅ green |
| 18-01-07 | 01 | 1 | DNSSEC-07 | integration | `pytest tests/test_dnssec_scanner.py::test_chaos_lab -x -m integration` | ✅ | ✅ manual |
| 18-02-01 | 02 | 2 | DNSSEC-01 | unit | `pytest tests/test_dnssec_scanner.py -x -q` | ✅ | ✅ green |
| 18-02-02 | 02 | 2 | DNSSEC-02 | unit | `pytest tests/test_dnssec_scanner.py::test_algorithm_classification -x` | ✅ | ✅ green |
| 18-02-03 | 02 | 2 | DNSSEC-03–06 | unit | `pytest tests/test_dnssec_scanner.py -x -q` | ✅ | ✅ green |
| 18-02-04 | 02 | 2 | DNSSEC-04 | unit | `pytest tests/test_dnssec_scanner.py::test_cbom_integration -x` | ✅ | ✅ green |
| 18-02-05 | 02 | 2 | DNSSEC-07 | integration | `pytest tests/test_dnssec_scanner.py::test_chaos_lab -x -m integration` | ✅ | ✅ manual |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_dnssec_scanner.py` — RED scaffold covering all 7 requirements (Plan 01 creates this)
- [x] `quirk/scanner/dnssec_scanner.py` — stub module with `DNSPYTHON_AVAILABLE` guard (Plan 02 implements, stub needed for Plan 01 imports to resolve)

*Wave 0 is Plan 01 itself — it creates the RED test file that all Plan 02 tasks turn GREEN.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| BIND9 container starts and serves signed zones | DNSSEC-07 | Requires Docker daemon + `dnssec` profile running | `docker compose --profile dnssec up -d`; `docker ps` shows bind9 container; `pytest tests/test_dnssec_scanner.py::test_chaos_lab -x -m integration` |
| Pre-signed zone files deterministic across builds | DNSSEC-07 | Zone file content verification | Inspect `quantum-chaos-enterprise-lab/bind9/zones/` — files should be committed, not generated at runtime |

---

## Mocking Strategy

Unit tests mock `dns.query.udp_with_fallback` following the `test_jwt_scanner.py` pattern:

```python
from unittest.mock import patch, MagicMock
with patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback") as mock_udp:
    mock_response = MagicMock()
    mock_udp.return_value = (mock_response, False)
    # test assertions
```

Integration tests (`@pytest.mark.integration`) skip unless `QUIRK_INTEGRATION_TESTS` env var is set.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-24

---

## Validation Audit 2026-04-24
| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 10 unit tasks green |
| Escalated | 0 |
| Manual-only | 2 (DNSSEC-07 chaos lab — requires Docker + BIND9) |
