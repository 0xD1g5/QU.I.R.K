---
phase: 3
slug: scanner-coverage
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest tests/test_jwt_scanner.py tests/test_container_scanner.py tests/test_source_scanner.py tests/test_cloud_connectors.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_jwt_scanner.py tests/test_container_scanner.py tests/test_source_scanner.py tests/test_cloud_connectors.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-W0-01 | Wave 0 | 0 | SCAN-03 | unit | `pytest tests/test_jwt_scanner.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-02 | Wave 0 | 0 | SCAN-04 | unit | `pytest tests/test_container_scanner.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-03 | Wave 0 | 0 | SCAN-05 | unit | `pytest tests/test_source_scanner.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-04 | Wave 0 | 0 | SCAN-06, SCAN-07 | unit | `pytest tests/test_cloud_connectors.py -x` | ❌ W0 | ⬜ pending |
| 3-xx-01 | SCAN-03 | 1 | SCAN-03 | unit | `pytest tests/test_jwt_scanner.py -x` | ✅ W0 | ⬜ pending |
| 3-xx-02 | SCAN-03 | 1 | SCAN-03 | unit | `pytest tests/test_jwt_scanner.py::test_multi_key_jwks -x` | ✅ W0 | ⬜ pending |
| 3-xx-03 | SCAN-04 | 1 | SCAN-04 | unit | `pytest tests/test_container_scanner.py::test_syft_not_found -x` | ✅ W0 | ⬜ pending |
| 3-xx-04 | SCAN-04 | 1 | SCAN-04 | unit | `pytest tests/test_container_scanner.py::test_allowlist_filter -x` | ✅ W0 | ⬜ pending |
| 3-xx-05 | SCAN-05 | 1 | SCAN-05 | unit | `pytest tests/test_source_scanner.py::test_semgrep_not_found -x` | ✅ W0 | ⬜ pending |
| 3-xx-06 | SCAN-05 | 1 | SCAN-05 | unit | `pytest tests/test_source_scanner.py -x` | ✅ W0 | ⬜ pending |
| 3-xx-07 | SCAN-06 | 2 | SCAN-06 | unit | `pytest tests/test_cloud_connectors.py::test_aws_acm_pagination -x` | ✅ W0 | ⬜ pending |
| 3-xx-08 | SCAN-06 | 2 | SCAN-06 | unit | `pytest tests/test_cloud_connectors.py::test_kms_key_spec_mapping -x` | ✅ W0 | ⬜ pending |
| 3-xx-09 | SCAN-07 | 2 | SCAN-07 | unit | `pytest tests/test_cloud_connectors.py::test_azure_keyvault -x` | ✅ W0 | ⬜ pending |
| 3-xx-10 | CBOM | 1 | ALL | unit | `pytest tests/test_cbom_builder.py -x -k "jwt or container or source or aws or azure"` | ✅ W0 | ⬜ pending |
| 3-xx-11 | CBOM | 1 | ALL | unit | `pytest tests/test_cbom_classifier.py -x -k "jwt"` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_jwt_scanner.py` — stubs for SCAN-03 with mocked httpx responses
- [ ] `tests/test_container_scanner.py` — stubs for SCAN-04 with mocked syft subprocess output
- [ ] `tests/test_source_scanner.py` — stubs for SCAN-05 with mocked semgrep subprocess output
- [ ] `tests/test_cloud_connectors.py` — stubs for SCAN-06/07 with mocked boto3/azure SDK calls
- [ ] pytest install: `pip install pytest` — not currently installed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| syft binary present and returns correct JSON for a real Docker image | SCAN-04 | Requires Docker daemon and syft installed | Run `syft python:3.12-slim -o json` and verify crypto libs appear in output |
| semgrep `p/cryptography` ruleset scans real repository | SCAN-05 | Requires internet access and semgrep install | Run `semgrep --config p/cryptography .` against a sample repo with known crypto usage |
| AWS ACM/KMS returns live certificates for configured account | SCAN-06 | Requires live AWS credentials and configured account | Configure `aws_access_key_id`, `aws_secret_access_key`, `aws_region` in scan target; verify CBOM output contains ACM certs |
| Azure Key Vault returns live key entries | SCAN-07 | Requires live Azure credentials and vault URL | Configure `azure_keyvault_urls` with real vault URL; verify CBOM output contains key entries |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
