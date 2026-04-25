---
phase: 26
slug: gcp-connector
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | pytest.ini / inferred from pyproject.toml |
| **Quick run command** | `pytest tests/test_cloud_connectors.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_cloud_connectors.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | GCP-01 | — | GCP_AVAILABLE=False returns empty list, no crash | unit | `pytest tests/test_cloud_connectors.py::test_gcp_unavailable -x` | ❌ W0 | ⬜ pending |
| 26-01-02 | 01 | 1 | GCP-01 | — | KMS key spec RSA/ECDSA/AES/HMAC maps to CryptoEndpoint correctly | unit | `pytest tests/test_cloud_connectors.py::test_gcp_kms_algorithm_mapping -x` | ❌ W0 | ⬜ pending |
| 26-01-03 | 01 | 1 | GCP-01 | — | DefaultCredentialsError at API call time → scan_error endpoint, no crash | unit | `pytest tests/test_cloud_connectors.py::test_gcp_credentials_error_graceful -x` | ❌ W0 | ⬜ pending |
| 26-02-01 | 02 | 1 | GCP-02 | — | ALLOW_UNENCRYPTED_AND_ENCRYPTED → HIGH finding | unit | `pytest tests/test_cloud_connectors.py::test_gcp_cloud_sql_plaintext_allowed -x` | ❌ W0 | ⬜ pending |
| 26-02-02 | 02 | 1 | GCP-02 | — | ENCRYPTED_ONLY → MEDIUM finding | unit | `pytest tests/test_cloud_connectors.py::test_gcp_cloud_sql_encrypted_only -x` | ❌ W0 | ⬜ pending |
| 26-02-03 | 02 | 1 | GCP-02 | — | TRUSTED_CLIENT_CERTIFICATE_REQUIRED → no finding | unit | `pytest tests/test_cloud_connectors.py::test_gcp_cloud_sql_mtls_no_finding -x` | ❌ W0 | ⬜ pending |
| 26-02-04 | 02 | 1 | GCP-02 | — | SSL_MODE_UNSPECIFIED / null sslMode → HIGH finding | unit | `pytest tests/test_cloud_connectors.py::test_gcp_cloud_sql_null_ssl_mode -x` | ❌ W0 | ⬜ pending |
| 26-03-01 | 03 | 2 | GCP-03 | — | GCS bucket CMEK vs Google-managed key detected | unit | `pytest tests/test_cloud_connectors.py::test_gcp_gcs_cmek_detection -x` | ❌ W0 | ⬜ pending |
| 26-03-02 | 03 | 2 | GCP-03, STOR-03 | — | gcs_scan_json column written once per scan (zero duplicate API calls) | unit | `pytest tests/test_cloud_connectors.py::test_gcp_gcs_scan_json_written -x` | ❌ W0 | ⬜ pending |
| 26-04-01 | 04 | 1 | GCP-01 | — | _ensure_gcp_columns() idempotent on v4.2 DB (no migration error) | unit | `pytest tests/ -k gcp -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cloud_connectors.py` — GCP test class covering GCP-01, GCP-02, GCP-03; all tests mock `_gcp_build` and `google.auth` at module level (no real GCP credentials required)
- [ ] `_ensure_gcp_columns()` test case (extend `tests/test_identity_infra.py` or add to cloud connectors test)
- [ ] All module-level mocks must support `GCP_AVAILABLE=False` path (mirrors `BOTO3_AVAILABLE` pattern in `tests/test_aws_connector.py`)

*Note: `tests/test_cloud_connectors.py` does not currently exist — Wave 0 must create it.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `pip install quirk[cloud]` resolves without grpcio/protobuf conflict | GCP-01 (success criteria 5) | Requires real pip resolver; cannot mock dependency resolution | Run `pip install -e ".[cloud]"` in a fresh venv; confirm no grpcio is pulled; verify `google-api-python-client` installs cleanly |
| Live GCP scan against a real project returns KMS keys in CBOM output | GCP-01 | Requires live GCP credentials and project | Configure ADC, set `gcp_project_id`, run `python run_scan.py`; check CBOM for `cryptoComponents` with `type: algorithm` from GCP source |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
