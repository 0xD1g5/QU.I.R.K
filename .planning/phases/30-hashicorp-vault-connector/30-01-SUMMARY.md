---
phase: 30
plan: "01"
subsystem: vault-scaffold
tags: [vault, hashicorp, hvac, config, red-tests, tdd, pyproject, scaffold]
dependency_graph:
  requires: []
  provides: [hvac-extras-declared, ConnectorsCfg-vault-fields, vault-test-contract]
  affects: [pyproject.toml, quirk/config.py, quirk/config_template.yaml, tests/test_vault_connector.py]
tech_stack:
  added: [hvac>=2.4.0 (declared in [cloud] extras)]
  patterns: [RED-before-GREEN TDD per v4.3 pattern, ConnectorsCfg dataclass extension, config_template commented block]
key_files:
  created: [tests/test_vault_connector.py]
  modified: [pyproject.toml, quirk/config.py, quirk/config_template.yaml]
decisions:
  - "enable_vault/vault_addr/vault_token/vault_transit_mount/vault_tls_verify all have safe defaults so v4.2 config.yaml loads without TypeError (D-10)"
  - "vault_tls_verify defaults True per D-09 (secure by default; consultant must opt in to false for self-signed)"
  - "vault_token defaults None with VAULT_TOKEN env var fallback documented in comment (D-10 T-30-01 accept)"
  - "hvac>=2.4.0 lower-bound-only pin in [cloud] extras; T-30-02 mitigated by version specifier"
  - "_KNOWN_CONNECTOR_KEYS auto-builds via dataclasses.fields() — no manual update required"
  - "RED state: test_pyproject_has_hvac_in_cloud_extras passes immediately; all 21 scanner tests fail until Plan 02 creates vault_connector.py"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-26"
  tasks_completed: 2
  files_created: 1
  files_modified: 3
---

# Phase 30 Plan 01: HashiCorp Vault RED Scaffold Summary

**One-liner:** RED scaffold for HashiCorp Vault connector — hvac dependency declared, 5 ConnectorsCfg vault fields added with safe defaults, and 22-test RED contract locked for Plan 02 implementation.

## What Was Built

### Task 1: hvac dependency + ConnectorsCfg vault fields + config_template vault block

**pyproject.toml** — line 51 added:
```toml
"hvac>=2.4.0",                     # Phase 30: HashiCorp Vault connector (VAULT-01/02/03)
```
Located inside `cloud = [...]` extras block (line 44–52). ISSUE-2 deliverable satisfied.

**quirk/config.py** — lines 95–99 added immediately after `aks_clusters` field (line 94):
```python
# Vault connector config (v4.3, Phase 30, per D-10)
enable_vault: bool = False
vault_addr: Optional[str] = None        # e.g. "http://localhost:8200"
vault_token: Optional[str] = None       # if None, falls back to VAULT_TOKEN env var
vault_transit_mount: str = "transit"    # default transit mount path (D-10)
vault_tls_verify: bool = True           # passed to hvac.Client(verify=...) — D-09
```
All 5 fields have safe defaults. `_KNOWN_CONNECTOR_KEYS` auto-builds via `dataclasses.fields()` — no manual update needed.

**quirk/config_template.yaml** — lines 97–102 added after K8s block:
```yaml
  # -- HashiCorp Vault connector (optional, requires: pip install quirk[cloud]) --
  # enable_vault: false
  # vault_addr: "http://localhost:8200"
  # vault_token: null               # defaults to VAULT_TOKEN env var
  # vault_transit_mount: "transit"  # default transit mount path
  # vault_tls_verify: true          # set false for self-signed HTTPS Vault
```

### Task 2: RED test file tests/test_vault_connector.py (439 lines, 22 test functions)

**Test functions (22 total):**

| # | Function | Requirement | Status |
|---|----------|-------------|--------|
| 1 | `test_pyproject_has_hvac_in_cloud_extras` | ISSUE-2/D-16 | PASSES (Task 1 satisfied) |
| 2 | `test_hvac_unavailable_returns_empty_list` | HVAC_AVAILABLE=False | FAILS (Plan 02 needed) |
| 3 | `test_no_token_produces_scan_error` | D-10 vault-no-token | FAILS |
| 4 | `test_invalid_token_produces_scan_error` | vault-auth-failed | FAILS |
| 5 | `test_session_start_threaded_to_scanned_at` | ISSUE-3/D-17 | FAILS |
| 6 | `test_transit_key_rsa2048_no_severity` | VAULT-01/D-01 | FAILS |
| 7 | `test_transit_key_aes256_no_severity` | VAULT-01/D-01 | FAILS |
| 8 | `test_transit_key_ecdsa_p256_no_severity` | VAULT-01/D-01 | FAILS |
| 9 | `test_transit_key_ml_dsa_87_quantum_safe_alg_name` | VAULT-01/PQC | FAILS |
| 10 | `test_transit_key_slh_dsa_128_quantum_safe_alg_name` | VAULT-01/PQC | FAILS |
| 11 | `test_transit_key_exportable_medium_severity` | VAULT-01/D-02 | FAILS |
| 12 | `test_pki_rsa2048_root_ca_high_severity` | VAULT-02/D-03 | FAILS |
| 13 | `test_pki_rsa4096_root_ca_no_severity` | VAULT-02/D-03 | FAILS |
| 14 | `test_pki_sha1_signed_ca_high_severity` | VAULT-02/D-03 | FAILS |
| 15 | `test_pki_intermediate_chain_emits_separate_endpoints` | VAULT-02/D-03 | FAILS |
| 16 | `test_pki_intermediate_failure_swallowed_returns_root_only` | VAULT-02/D-04 | FAILS |
| 17 | `test_pki_endpoint_strips_trailing_slash_in_mount_path` | VAULT-02/Pitfall-3 | FAILS |
| 18 | `test_auth_token_unconditional_high` | VAULT-03/D-05 | FAILS |
| 19 | `test_auth_ldap_high_severity` | VAULT-03/D-06 | FAILS |
| 20 | `test_auth_userpass_medium_severity` | VAULT-03/D-06 | FAILS |
| 21 | `test_auth_approle_kubernetes_oidc_no_finding` | VAULT-03/D-06 | FAILS |
| 22 | `test_dat_scan_json_populated_on_every_vault_endpoint` | VAULT-01/02/03 | FAILS |

**ISSUE-2 invariant:** Only `test_pyproject_has_hvac_in_cloud_extras` passes. All 21 scanner tests fail with `AttributeError: module 'quirk.scanner' has no attribute 'vault_connector'` — confirming RED state is locked.

## Plan 02 Required Signature

Plan 02 must create `quirk/scanner/vault_connector.py` implementing:

```python
# Module-level
HVAC_AVAILABLE: bool   # True if hvac importable, False otherwise
hvac: Optional[ModuleType]   # None when unavailable

def scan_vault_targets(
    vault_addr: str,
    token: Optional[str] = None,
    transit_mount: str = "transit",
    tls_verify: bool = True,
    logger=None,
    session_start: Optional[datetime] = None,
) -> List[CryptoEndpoint]: ...
```

Key behaviors Plan 02 must satisfy (from test contract):
- `VAULT_TRANSIT_KEY_MAP` normalization: `rsa-2048→("RSA",2048)`, `aes256-gcm96→("AES",256)`, `ecdsa-p256→("ECDSA",256)`, `ml-dsa-87→("ml-dsa-87",None)`, `slh-dsa-shake-128s→("slh-dsa-128",None)`
- `exportable=True` → `severity="MEDIUM"` (D-02)
- PKI root + intermediate endpoints per mount; RSA<4096 or SHA-1 → HIGH (D-03)
- Intermediate chain failure swallowed silently (D-04)
- Mount path trailing slash stripped before API calls (Pitfall 3)
- Token auth always HIGH unconditional (D-05)
- AUTH_RISK_MAP: token/ldap=HIGH, userpass=MEDIUM, approle/k8s/oidc=no endpoint (D-06)
- `scanned_at = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)` (D-17/ISSUE-3)
- `dat_scan_json` populated on every non-error endpoint
- No-token → single `scan_error="vault-no-token: ..."` endpoint
- Auth failure → single `scan_error="vault-auth-failed: ..."` endpoint

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

No new threat surface introduced in this plan. T-30-01/T-30-02/T-30-03/T-30-04 from the plan threat model are all addressed: vault_tls_verify defaults True (T-30-03 mitigated), hvac>=2.4.0 lower-bound pin (T-30-02 mitigated), vault_token field documented with env var fallback (T-30-01 accept), PEM helper uses ephemeral in-process certs (T-30-04 accept).

## Known Stubs

None — this is a scaffold plan (no scanner implementation). The vault connector itself is stub-free because Plan 02 implements it.

## Self-Check

- [x] `pyproject.toml` contains `hvac>=2.4.0` at line 51
- [x] `quirk/config.py` contains 5 vault fields at lines 95–99
- [x] `quirk/config_template.yaml` contains commented vault block at lines 97–102
- [x] `tests/test_vault_connector.py` exists at 439 lines with 22 test functions
- [x] Commit e522191 (Task 1) exists
- [x] Commit fb75ab8 (Task 2) exists
- [x] test_pyproject_has_hvac_in_cloud_extras passes
- [x] 41 existing tests pass (no regression)

## Self-Check: PASSED
