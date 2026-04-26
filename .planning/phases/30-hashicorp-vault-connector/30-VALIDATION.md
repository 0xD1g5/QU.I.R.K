---
phase: 30
slug: hashicorp-vault-connector
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-26
updated: 2026-04-26
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — no config file, discovered by convention) |
| **Config file** | none — existing pytest infrastructure |
| **Quick run command** | `python -m pytest tests/test_vault_connector.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~12 seconds (vault tests only); ~60 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_vault_connector.py tests/test_dar_vault_scoring.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 12 seconds (per-phase quick run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 30-01-01 | 01 | 1 | ISSUE-2 (D-16) / VAULT-01/02/03 | T-30-02 / T-30-03 | pyproject.toml [cloud] extras has hvac>=2.4.0; ConnectorsCfg has 5 vault fields with safe defaults | unit | `python -m pytest tests/test_vault_connector.py::test_pyproject_has_hvac_in_cloud_extras -x -q` | ❌ W0 (created by 30-01-02) | ⬜ pending |
| 30-01-02 | 01 | 1 | VAULT-01/02/03 + ISSUE-2/ISSUE-3 | T-30-04 | RED scaffold: 22 named tests fail with ImportError on quirk.scanner.vault_connector (only test_pyproject_has_hvac_in_cloud_extras passes) | unit | `python -m pytest tests/test_vault_connector.py --collect-only -q 2>&1 \| grep -c '::test_' \| awk '$1 >= 22 {exit 0} {exit 1}'` | ✅ (this task creates it) | ⬜ pending |
| 30-02-01 | 02 | 2 | VAULT-01/02/03 (D-01..D-06, D-09, D-17) | T-30-05 / T-30-06 / T-30-07 / T-30-08 / T-30-09 | GREEN: all 22 RED tests in tests/test_vault_connector.py pass; tokens never logged; PEM parse failures isolated; 10s timeout; tls_verify default True; session_start threaded | unit | `python -m pytest tests/test_vault_connector.py -x -q` | ✅ | ⬜ pending |
| 30-02-02 | 02 | 2 | VAULT-01/02/03 | T-30-10 | run_scan.py vault_scanning block deferred-imports vault_connector inside `if cfg.connectors.enable_vault:` guard; aggregation tuple includes `+ vault_endpoints` | unit | `python -c "import ast; ast.parse(open('run_scan.py').read())" && grep -c '"vault_scanning"' run_scan.py \| grep -q '^1$' && python -m pytest tests/test_vault_connector.py -x -q` | ✅ | ⬜ pending |
| 30-03-01 | 03 | 3 | VAULT-01/02/03 (D-11, D-12, D-13) | T-30-11 / T-30-13 | dar_vault_weak_count increments only on HIGH severity; dar_vault_weak_ratio in evidence dict; SCORE_WEIGHTS has dar_vault_weak_ratio=8.0; NUM_SUBSCORES still 5 | unit | `python -m pytest tests/test_dar_vault_scoring.py -v` | ✅ (this task creates test_dar_vault_scoring.py) | ⬜ pending |
| 30-03-02 | 03 | 3 | VAULT-01 (D-14, D-15) | T-30-14 | CBOM Pass 2 + Pass 3 skip lists include "VAULT" (no cert/protocol components); Pass 1 unchanged so transit keys register algorithms via _register_algorithm | unit | `grep -c '"KUBERNETES", "VAULT"' quirk/cbom/builder.py \| grep -q '^2$' && python -m pytest tests/test_cbom_builder.py -x -q` | ✅ | ⬜ pending |
| 30-03-03 | 03 | 3 | VAULT-01/02/03 (D-07, D-08) | T-30-12 | docker-compose.yml has dedicated `--profile vault` block at port 28200 (NOT extending storage profile at 20009); seed.sh seeds 4 RED finding paths; labs/vault/expected_results.md documents 5 expected findings | file+yaml | `test -x quantum-chaos-enterprise-lab/vault/seed.sh && python -c "import yaml; yaml.safe_load(open('quantum-chaos-enterprise-lab/docker-compose.yml'))" && test -f labs/vault/expected_results.md` | ✅ (this task creates seed.sh + expected_results.md) | ⬜ pending |
| 30-03-04 | 03 | 3 | VAULT-01/02/03 | T-30-15 / T-30-16 | UAT-30-01/02/03 entries inserted into docs/UAT-SERIES.md; UAT-Series.md synced to Obsidian filesystem; Phase-30-HashiCorp-Vault-Connector.md Obsidian note has status: complete and required sections | file+grep | `grep -c '### UAT-30-0[123]:' docs/UAT-SERIES.md \| grep -q '^3$' && test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-30-HashiCorp-Vault-Connector.md && test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` | ✅ (this task creates Obsidian notes) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Phase Requirements → Test Map

| Requirement | Behavior | Test Type | Command | Wave |
|-------------|----------|-----------|---------|------|
| VAULT-01 | RSA-2048 transit key normalises to alg='RSA', size=2048, severity=None (D-01) | unit | `pytest tests/test_vault_connector.py::test_transit_key_rsa2048_no_severity -x` | Wave 0 |
| VAULT-01 | aes256-gcm96 transit key normalises to alg='AES', size=256 (D-01) | unit | `pytest tests/test_vault_connector.py::test_transit_key_aes256_no_severity -x` | Wave 0 |
| VAULT-01 | ecdsa-p256 transit key normalises to alg='ECDSA', size=256 (D-01) | unit | `pytest tests/test_vault_connector.py::test_transit_key_ecdsa_p256_no_severity -x` | Wave 0 |
| VAULT-01 | ml-dsa-87 transit key produces alg='ml-dsa-87' (matches classifier.py) | unit | `pytest tests/test_vault_connector.py::test_transit_key_ml_dsa_87_quantum_safe_alg_name -x` | Wave 0 |
| VAULT-01 | slh-dsa-shake-128s transit key produces alg='slh-dsa-128' (matches classifier.py) | unit | `pytest tests/test_vault_connector.py::test_transit_key_slh_dsa_128_quantum_safe_alg_name -x` | Wave 0 |
| VAULT-01 | exportable=True transit key → severity=MEDIUM (D-02); MEDIUM does NOT increment dar_vault_weak_count (D-11) | unit | `pytest tests/test_vault_connector.py::test_transit_key_exportable_medium_severity tests/test_dar_vault_scoring.py::test_dar_vault_weak_count_medium_exportable_no_increment -x` | Wave 0 |
| VAULT-02 | PKI mount with RSA-2048 root CA → severity=HIGH (D-03) | unit | `pytest tests/test_vault_connector.py::test_pki_rsa2048_root_ca_high_severity -x` | Wave 0 |
| VAULT-02 | PKI mount with RSA-4096 + SHA-256 root CA → no severity (baseline ok) | unit | `pytest tests/test_vault_connector.py::test_pki_rsa4096_root_ca_no_severity -x` | Wave 0 |
| VAULT-02 | SHA-1 signed CA cert → severity=HIGH (D-03) | unit | `pytest tests/test_vault_connector.py::test_pki_sha1_signed_ca_high_severity -x` | Wave 0 |
| VAULT-02 | PKI mount with intermediate chain → root + intermediate-N endpoints (D-03) | unit | `pytest tests/test_vault_connector.py::test_pki_intermediate_chain_emits_separate_endpoints -x` | Wave 0 |
| VAULT-02 | read_ca_certificate_chain failure swallowed silently — only root endpoint returned (D-04) | unit | `pytest tests/test_vault_connector.py::test_pki_intermediate_failure_swallowed_returns_root_only -x` | Wave 0 |
| VAULT-02 | service_detail strips trailing slash from mount path (Pitfall 3) | unit | `pytest tests/test_vault_connector.py::test_pki_endpoint_strips_trailing_slash_in_mount_path -x` | Wave 0 |
| VAULT-03 | token auth → severity=HIGH unconditional even when AppRole/Kubernetes also enabled (D-05) | unit | `pytest tests/test_vault_connector.py::test_auth_token_unconditional_high -x` | Wave 0 |
| VAULT-03 | ldap auth → severity=HIGH (D-06) | unit | `pytest tests/test_vault_connector.py::test_auth_ldap_high_severity -x` | Wave 0 |
| VAULT-03 | userpass auth → severity=MEDIUM (D-06) | unit | `pytest tests/test_vault_connector.py::test_auth_userpass_medium_severity -x` | Wave 0 |
| VAULT-03 | approle/kubernetes/oidc → no endpoint emitted (D-06) | unit | `pytest tests/test_vault_connector.py::test_auth_approle_kubernetes_oidc_no_finding -x` | Wave 0 |
| VAULT-01/02/03 | dat_scan_json populated with valid JSON on every VAULT endpoint | unit | `pytest tests/test_vault_connector.py::test_dat_scan_json_populated_on_every_vault_endpoint -x` | Wave 0 |
| VAULT-01/02/03 | HVAC_AVAILABLE=False → empty list (no scan_error endpoint) | unit | `pytest tests/test_vault_connector.py::test_hvac_unavailable_returns_empty_list -x` | Wave 0 |
| VAULT-01/02/03 | Missing token → single scan_error endpoint with 'vault-no-token' prefix | unit | `pytest tests/test_vault_connector.py::test_no_token_produces_scan_error -x` | Wave 0 |
| VAULT-01/02/03 | Invalid token / sealed Vault → scan_error endpoint with 'vault-auth-failed' prefix | unit | `pytest tests/test_vault_connector.py::test_invalid_token_produces_scan_error -x` | Wave 0 |
| ISSUE-2 (D-16) | pyproject.toml [cloud] extras includes hvac>=2.4.0 with Phase 30 + VAULT-01/02/03 comment | unit | `pytest tests/test_vault_connector.py::test_pyproject_has_hvac_in_cloud_extras -x` | Wave 0 |
| ISSUE-3 (D-17) | scan_vault_targets accepts session_start parameter and stamps every endpoint | unit | `pytest tests/test_vault_connector.py::test_session_start_threaded_to_scanned_at -x` | Wave 0 |
| evidence (D-11) | dar_vault_weak_count increments only on HIGH-severity VAULT endpoints (PKI HIGH + token/ldap auth HIGH); MEDIUM does NOT increment | unit | `pytest tests/test_dar_vault_scoring.py::test_dar_vault_weak_count_high_pki_increments tests/test_dar_vault_scoring.py::test_dar_vault_weak_count_high_token_auth_increments tests/test_dar_vault_scoring.py::test_dar_vault_weak_count_medium_exportable_no_increment tests/test_dar_vault_scoring.py::test_dar_vault_weak_count_medium_userpass_no_increment tests/test_dar_vault_scoring.py::test_dar_vault_weak_count_no_severity_no_increment -x` | Wave 0 |
| evidence (D-11) | dar_vault_weak_ratio = dar_vault_weak_count / total_endpoints | unit | `pytest tests/test_dar_vault_scoring.py::test_dar_vault_weak_ratio_calculated -x` | Wave 0 |
| scoring (D-12) | SCORE_WEIGHTS['dar_vault_weak_ratio'] == 8.0 | unit | `pytest tests/test_dar_vault_scoring.py::test_score_weights_has_dar_vault_weak_ratio_8 -x` | Wave 0 |
| scoring (D-13) | NUM_SUBSCORES stays 5 (vault impact appended to dar_impacts list, NOT a new subscore) | unit | `pytest tests/test_dar_vault_scoring.py::test_compute_readiness_score_subscores_count_unchanged -x` | Wave 0 |
| scoring (D-12, D-13) | High dar_vault_weak_count drops the data_at_rest subscore | unit | `pytest tests/test_dar_vault_scoring.py::test_compute_readiness_score_vault_impacts_data_at_rest -x` | Wave 0 |
| CBOM (D-14) | Pass 1 NOT skipped for VAULT — transit key cert_pubkey_alg registers as algorithm | unit | `grep -E '"S3", "AZURE_BLOB", "KUBERNETES"\)' quirk/cbom/builder.py \| wc -l` (must = 1, no VAULT in Pass 1) | Wave 0 |
| CBOM (D-15) | Pass 2 + Pass 3 skip lists include "VAULT" (no cert / no protocol components) | unit | `grep -c '"KUBERNETES", "VAULT"' quirk/cbom/builder.py` (must = 2) | Wave 0 |
| chaos lab (D-07, D-08) | docker compose --profile vault block exists at port 28200; seed.sh seeds 4 RED finding paths; expected_results.md documents 5 findings | file+yaml | `python -c "import yaml; yaml.safe_load(open('quantum-chaos-enterprise-lab/docker-compose.yml'))" && test -x quantum-chaos-enterprise-lab/vault/seed.sh && test -f labs/vault/expected_results.md` | Wave 0 |
| docs | docs/UAT-SERIES.md has UAT-30-01/02/03 entries before Series 6 header | grep | `grep -c '### UAT-30-0[123]:' docs/UAT-SERIES.md` (must >= 3) | Wave 0 |
| docs | UAT-Series.md synced to Obsidian filesystem with frontmatter | file | `test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md && head -7 /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md \| grep -c 'project: QU.I.R.K.'` | Wave 0 |
| docs | Phase-30-HashiCorp-Vault-Connector.md Obsidian note exists with status: complete | file | `test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-30-HashiCorp-Vault-Connector.md && head -10 /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-30-HashiCorp-Vault-Connector.md \| grep -c 'status: complete'` | Wave 0 |

---

## Wave 0 Requirements

- [ ] `tests/test_vault_connector.py` — VAULT-01/02/03 + ISSUE-2/ISSUE-3 RED scaffold (22 tests; created in Plan 30-01 Task 2)
- [ ] `tests/test_dar_vault_scoring.py` — evidence/scoring tests (10 tests; created in Plan 30-03 Task 1)

*Existing pytest infrastructure covers all phase requirements — no new framework install needed. The cryptography lib is already a core dep (used by tls_scanner / DNSSEC PEM parsing); the RED test PEM helper relies on it. hvac is added to `[cloud]` extras in Plan 30-01 Task 1 but is not strictly required to RUN the tests because all hvac-touching test paths are mocked.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Vault chaos lab end-to-end (5 expected findings emitted) | VAULT-01/02/03 | Requires Docker daemon running; `vault-30-seed` init container needs ~10s to seed live Vault | UAT-30-01: `cd quantum-chaos-enterprise-lab && docker compose --profile vault up -d` → wait for vault-30-seed exit 0 → run `quirk --config vault_uat.yaml` → verify 5 protocol="VAULT" rows in scan-results.json |
| Vault PKI root + intermediate CA detection on a real chain | VAULT-02 (D-03) | Requires creating a real intermediate CA inside the chaos lab via `vault write pki_int/intermediate/generate/internal ...` | UAT-30-02: see docs/UAT-SERIES.md UAT-30-02 (steps 1-4) |
| Token always-HIGH unconditional with AppRole/Kubernetes also enabled | VAULT-03 (D-05) | Requires `vault auth enable approle && vault auth enable kubernetes` against the chaos lab | UAT-30-03: see docs/UAT-SERIES.md UAT-30-03 (steps 1-4) |

*All scanner-level behaviors have automated unit tests using `unittest.mock.patch` against `quirk.scanner.vault_connector.hvac` — manual verifications are end-to-end live-cluster confirmations only.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task in 30-01/02/03 has an `<automated>` block)
- [x] Wave 0 covers all MISSING references (test_vault_connector.py created in 30-01-02; test_dar_vault_scoring.py created in 30-03-01)
- [x] No watch-mode flags
- [x] Feedback latency < 12s for vault-only quick run
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-26
