---
phase: 19
slug: saml-oidc-scanner
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-08
updated: 2026-04-24
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (in project venv) |
| **Config file** | `pytest.ini` / `pyproject.toml [tool.pytest]` |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_saml_scanner.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds (quick) / ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/test_saml_scanner.py -x -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green (pre-existing `test_pdf_export` failure is acceptable — document with `--ignore` if needed)
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | SAML-01 | unit (mocked) | `pytest tests/test_saml_scanner.py -k "signing_cert" -x` | ✅ | ✅ green |
| 19-01-02 | 01 | 1 | SAML-02 | unit (mocked) | `pytest tests/test_saml_scanner.py -k "encryption_cert" -x` | ✅ | ✅ green |
| 19-01-03 | 01 | 1 | SAML-03 | unit (mocked) | `pytest tests/test_saml_scanner.py -k "oidc" -x` | ✅ | ✅ green |
| 19-01-04 | 01 | 1 | SAML-04 | unit (pure) | `pytest tests/test_saml_scanner.py -k "severity or sha1" -x` | ✅ | ✅ green |
| 19-01-05 | 01 | 1 | SAML-05 | unit (mocked) | `pytest tests/test_saml_scanner.py -k "cbom or protocol or json" -x` | ✅ | ✅ green |
| 19-01-06 | 01 | 1 | SAML-06 | integration (skipif) | `QUIRK_INTEGRATION_TESTS=1 pytest tests/test_saml_scanner.py -k "chaos_lab" -x` | ✅ | ✅ manual |
| 19-02-01 | 02 | 2 | SAML-01,02 | unit (mocked) | `pytest tests/test_saml_scanner.py -k "signing_cert or encryption_cert" -x` | ✅ | ✅ green |
| 19-02-02 | 02 | 2 | SAML-03 | unit (mocked) | `pytest tests/test_saml_scanner.py -k "oidc" -x` | ✅ | ✅ green |
| 19-02-03 | 02 | 2 | SAML-04 | unit (pure) | `pytest tests/test_saml_scanner.py -k "severity or sha1" -x` | ✅ | ✅ green |
| 19-02-04 | 02 | 2 | SAML-05 | unit (mocked) | `pytest tests/test_saml_scanner.py -k "cbom or protocol or json" -x` | ✅ | ✅ green |
| 19-02-05 | 02 | 2 | SAML-06 | integration (skipif) | `QUIRK_INTEGRATION_TESTS=1 pytest tests/test_saml_scanner.py -k "chaos_lab" -x` | ✅ | ✅ manual |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_saml_scanner.py` — RED test scaffold covering SAML-01 through SAML-06 (all tests must fail at start of Plan 02)
- [x] `quirk/scanner/saml_scanner.py` — stub module with `LXML_AVAILABLE` import guard and empty function signatures

*Plan 01 creates both files. Plan 02 makes tests go GREEN.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SimpleSAMLphp chaos lab produces CRITICAL for RSA-1024 cert | SAML-06 | Requires Docker daemon running + `QUIRK_INTEGRATION_TESTS=1` env var | 1. `open -a Docker` (macOS). 2. `docker compose --profile saml up -d`. 3. Wait for healthcheck. 4. `QUIRK_INTEGRATION_TESTS=1 .venv/bin/python -m pytest tests/test_saml_scanner.py -k "chaos_lab" -v`. Assert CRITICAL finding. |
| SimpleSAMLphp cert mount path correct | SAML-06 | Docker filesystem layout requires runtime verification | `docker run --rm kenchan0130/simplesamlphp ls /var/www/simplesamlphp/cert/` — confirm path before writing docker-compose volume mount |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-24

---

## Validation Audit 2026-04-24
| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 9 unit tasks green |
| Escalated | 0 |
| Manual-only | 2 (SAML-06 SimpleSAMLphp chaos lab — requires Docker) |
