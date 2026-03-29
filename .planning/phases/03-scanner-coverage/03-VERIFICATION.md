---
phase: 03-scanner-coverage
verified: 2026-03-29T23:55:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
gaps: []
---

# Phase 3: Scanner Coverage Verification Report

**Phase Goal:** QU.I.R.K. discovers cryptographic material across every major attack surface — APIs, containers, source code, and cloud key management
**Verified:** 2026-03-29T23:55:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A scan of a JWT-issuing API endpoint returns the signing algorithm, key size, and JWKS key IDs — and these appear in the CBOM | VERIFIED | scan_jwt_endpoint returns CryptoEndpoint with protocol="JWT", cert_pubkey_alg="RS256", cert_pubkey_size=2048; build_cbom produces "RS256" algorithm component. Spot-check passed. |
| 2 | Running the container scanner against a Docker image returns the crypto libraries embedded in that image with versions | VERIFIED | scan_container_image filters syft output through CRYPTO_LIB_ALLOWLIST (23 names); returns CryptoEndpoint per library with cipher_suite=name, tls_version=version. Spot-check passed. |
| 3 | Running the source code scanner against a Git repository returns algorithm usage findings with file and line references | VERIFIED | scan_source_repo sets service_detail="file:line" from semgrep finding path/start.line. Spot-check confirmed service_detail="app/auth.py:42". |
| 4 | The AWS connector returns ACM certificates, KMS key specs, and CloudFront/ELB TLS policies for a configured AWS account | VERIFIED | aws_connector.py implements _scan_acm, _scan_kms, _scan_cloudfront, _scan_elbv2 all using get_paginator(). Spot-check returned AWS endpoints. 3/3 AWS tests pass. |
| 5 | The Azure connector returns Key Vault key types and App Gateway TLS policies for a configured Azure subscription | VERIFIED | azure_connector.py implements _scan_keyvault_keys and _scan_app_gateways. Spot-check returned AZURE endpoint with host set. 2/2 Azure tests pass. |
| 6 | CryptoEndpoint model has jwt_scan_json, container_scan_json, source_scan_json, cloud_scan_json columns | VERIFIED | quirk/models.py lines 59-62 confirmed at runtime via hasattr checks. |
| 7 | ConnectorsCfg has all Phase 3 fields with backwards-compatible defaults | VERIFIED | quirk/config.py lines 49-61 confirmed: enable_jwt=False, aws_region="us-east-1", jwt_targets=[], etc. Runtime checks passed. |
| 8 | pyproject.toml includes all 8 Phase 3 dependencies | VERIFIED | httpx>=0.28.0, PyJWT>=2.12.0, python-jose>=3.5.0, boto3>=1.42.0, azure-identity>=1.25.0, azure-keyvault-certificates>=4.10.0, azure-keyvault-keys>=4.11.0, azure-mgmt-network>=30.2.0 all present. Runtime import confirmed httpx 0.28.1, jwt 2.12.1, boto3 1.42.78. |
| 9 | JWT, container, and source scanners degrade gracefully when their tool is absent | VERIFIED | HTTPX_AVAILABLE guard in jwt_scanner.py; shutil.which guards in container_scanner.py and source_scanner.py. Tests test_jwt_httpx_unavailable, test_syft_not_found, test_semgrep_not_found all pass. |
| 10 | AWS and Azure connectors degrade gracefully when their SDK is not installed | VERIFIED | BOTO3_AVAILABLE and AZURE_AVAILABLE flags with ImportError guards. test_aws_boto3_unavailable and test_azure_sdk_unavailable pass. |
| 11 | CBOM classifier recognizes JWT/JOSE algorithms (RS256, ES256, HS256, none, etc.) | VERIFIED | 14 entries in _ALGORITHM_TABLE (rs256..rs512, es256..es512, hs256..hs512, ps256..ps384..ps512, eddsa, none). Runtime classify_algorithm("RS256") returns (SIGNATURE, 0, 112). |
| 12 | New protocol values do NOT fall through to the TLS else clause in builder.py | VERIFIED | builder.py Pass 3 line 450: elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE"): continue. Runtime test with CONTAINER endpoint confirmed zero TLS protocol components. |
| 13 | run_scan.py orchestrates all five new scanners with guarded phase blocks | VERIFIED | Lines 364-423: all five imports present (lines 17-21), five _phase_timer blocks with enable_* guards, endpoint merge on line 421-423 includes all five new lists. |
| 14 | All new scanner endpoints merge into the shared endpoints list before evaluate_endpoints() | VERIFIED | endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints + jwt_endpoints + container_endpoints + source_endpoints + aws_endpoints + azure_endpoints) at line 421-423, directly followed by evaluate_endpoints() call at line 429. |

**Score:** 14/14 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/models.py` | 4 new nullable Text columns on CryptoEndpoint | VERIFIED | jwt_scan_json, container_scan_json, source_scan_json, cloud_scan_json at lines 59-62 |
| `quirk/config.py` | Extended ConnectorsCfg with Phase 3 fields | VERIFIED | 11 new fields with defaults: enable_jwt/container/source, aws_region/profile, azure_subscription_id/keyvault_urls, jwt/container/source_targets |
| `pyproject.toml` | All Phase 3 Python dependencies | VERIFIED | 8 dependencies confirmed present (lines 13-20) |
| `tests/test_jwt_scanner.py` | Test scaffold for SCAN-03 | VERIFIED | 5 tests: test_multi_key_jwks, test_jwt_rsa_key_size, test_jwt_ec_key_size, test_jwt_endpoint_not_found, test_jwt_httpx_unavailable |
| `tests/test_container_scanner.py` | Test scaffold for SCAN-04 | VERIFIED | 4 tests: test_syft_not_found, test_allowlist_filter, test_container_endpoint_fields, test_syft_json_parse_error |
| `tests/test_source_scanner.py` | Test scaffold for SCAN-05 | VERIFIED | 5 tests: test_semgrep_not_found, test_semgrep_findings_parsed, test_semgrep_service_detail_format, test_semgrep_cipher_suite_is_rule_id, test_semgrep_json_parse_error |
| `tests/test_cloud_connectors.py` | Test scaffold for SCAN-06/07 | VERIFIED | 5 tests: test_aws_acm_pagination, test_kms_key_spec_mapping, test_aws_boto3_unavailable, test_azure_keyvault, test_azure_sdk_unavailable |
| `quirk/scanner/jwt_scanner.py` | JWT/JWKS scanner module | VERIFIED | 155 lines. Exports: scan_jwt_targets, scan_jwt_endpoint, HTTPX_AVAILABLE. Contains _rsa_key_bits_from_n, JWKS_PATHS, protocol="JWT", jwt_scan_json= |
| `quirk/scanner/container_scanner.py` | Container/binary scanner module | VERIFIED | 108 lines. Exports: scan_container_targets, scan_container_image, CRYPTO_LIB_ALLOWLIST. Contains shutil.which("syft"), protocol="CONTAINER", container_scan_json= |
| `quirk/scanner/source_scanner.py` | Source code scanner module | VERIFIED | 88 lines. Exports: scan_source_targets, scan_source_repo. Contains shutil.which("semgrep"), protocol="SOURCE", source_scan_json=, p/cryptography |
| `quirk/scanner/aws_connector.py` | AWS cloud connector module | VERIFIED | 202 lines. Exports: scan_aws_targets, BOTO3_AVAILABLE. Contains KMS_KEY_SPEC_MAP, _scan_acm, _scan_kms, _scan_cloudfront, _scan_elbv2, get_paginator("list_certificates"), protocol="AWS" |
| `quirk/scanner/azure_connector.py` | Azure cloud connector module | VERIFIED | 146 lines. Exports: scan_azure_targets, AZURE_AVAILABLE. Contains DefaultAzureCredential, KeyClient at module level, _scan_keyvault_keys, protocol="AZURE" |
| `quirk/cbom/classifier.py` | JWT algorithm entries in _ALGORITHM_TABLE | VERIFIED | 14 JWT/JOSE entries: rs256..rs512, es256..es512, hs256..hs512, ps256..ps384..ps512, eddsa, none |
| `quirk/cbom/builder.py` | Protocol branching for JWT, CONTAINER, SOURCE, AWS, AZURE | VERIFIED | Lines 321-450: explicit elif chain in all 3 passes; _extract_algo_from_rule_id and _normalize_cloud_key_spec helpers; no TLS fallthrough |
| `run_scan.py` | Guarded phase blocks for all five new scanners | VERIFIED | 5 imports (lines 17-21), 5 phase blocks (lines 364-419), endpoint merge (lines 421-423) includes all 5 new lists |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/config.py` | `quirk/models.py` | ConnectorsCfg fields drive which scanners run; model columns store results | WIRED | enable_jwt/container/source flags present; jwt_scan_json/container_scan_json/source_scan_json/cloud_scan_json columns confirmed |
| `quirk/scanner/jwt_scanner.py` | `quirk/models.py` | CryptoEndpoint construction with protocol="JWT" | WIRED | protocol="JWT" at line 119; jwt_scan_json= at line 122 |
| `quirk/scanner/container_scanner.py` | `quirk/models.py` | CryptoEndpoint construction with protocol="CONTAINER" | WIRED | protocol="CONTAINER" at line 80; container_scan_json= at line 83 |
| `quirk/scanner/source_scanner.py` | `quirk/models.py` | CryptoEndpoint construction with protocol="SOURCE" | WIRED | protocol="SOURCE" at line 60; source_scan_json= at line 63 |
| `quirk/scanner/aws_connector.py` | `quirk/models.py` | CryptoEndpoint construction with protocol="AWS" | WIRED | protocol="AWS" at lines 59, 92, 128, 160; cloud_scan_json= confirmed |
| `quirk/scanner/azure_connector.py` | `quirk/models.py` | CryptoEndpoint construction with protocol="AZURE" | WIRED | protocol="AZURE" at lines 63, 101; cloud_scan_json= confirmed |
| `run_scan.py` | `quirk/scanner/jwt_scanner.py` | import and call scan_jwt_targets | WIRED | Line 17: from quirk.scanner.jwt_scanner import scan_jwt_targets; called at line 367 |
| `run_scan.py` | `quirk/scanner/container_scanner.py` | import and call scan_container_targets | WIRED | Line 18: from quirk.scanner.container_scanner import scan_container_targets; called at line 379 |
| `run_scan.py` | `quirk/scanner/source_scanner.py` | import and call scan_source_targets | WIRED | Line 19: from quirk.scanner.source_scanner import scan_source_targets; called at line 391 |
| `run_scan.py` | `quirk/scanner/aws_connector.py` | import and call scan_aws_targets | WIRED | Line 20: from quirk.scanner.aws_connector import scan_aws_targets; called at line 403 |
| `run_scan.py` | `quirk/scanner/azure_connector.py` | import and call scan_azure_targets | WIRED | Line 21: from quirk.scanner.azure_connector import scan_azure_targets; called at line 415 |
| `quirk/cbom/builder.py` | `quirk/cbom/classifier.py` | classify_algorithm called for JWT/cloud algorithms | WIRED | pattern "classify_algorithm" confirmed present; JWT endpoint produces RS256 algorithm component in CBOM (runtime verified) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `quirk/scanner/jwt_scanner.py` | endpoints list | httpx.get() → JWKS JSON → key_entry loop | Yes — one CryptoEndpoint per key with jwt_scan_json=json.dumps(key_entry) | FLOWING |
| `quirk/scanner/container_scanner.py` | endpoints list | subprocess.run(syft) → JSON artifacts → allowlist filter | Yes — filtered artifact list produces real CryptoEndpoint per match | FLOWING |
| `quirk/scanner/source_scanner.py` | endpoints list | subprocess.run(semgrep) → JSON results → finding loop | Yes — each finding produces CryptoEndpoint with source_scan_json | FLOWING |
| `quirk/scanner/aws_connector.py` | endpoints list | boto3.Session().client() → paginators → describe_* calls | Yes — ACM/KMS/CloudFront/ELBv2 resources produce endpoints with cloud_scan_json | FLOWING |
| `quirk/scanner/azure_connector.py` | endpoints list | DefaultAzureCredential → KeyClient → list_properties_of_keys | Yes — Key Vault keys produce endpoints with cloud_scan_json | FLOWING |
| `run_scan.py` | endpoints (merged) | All five new scanner lists merged at lines 421-423 | Yes — flows directly into evaluate_endpoints() at line 429 | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| JWT endpoint → alg RS256, key size 2048 → appears in CBOM | python3.14 runtime + mock httpx | RS256 in CBOM algo components, size 2048 | PASS |
| Container scan returns crypto libs with versions, curl filtered | python3.14 runtime + mock syft | openssl/cryptography returned, curl absent, version 3.0.2 confirmed | PASS |
| Source scan returns finding at file:line | python3.14 runtime + mock semgrep | service_detail="app/auth.py:42" confirmed | PASS |
| AWS connector returns AWS-protocol endpoints | python3.14 runtime + mock boto3 | 1 endpoint with protocol="AWS" returned | PASS |
| Azure connector returns AZURE-protocol endpoints | python3.14 runtime + mock azure SDK | 1 endpoint with protocol="AZURE", host set | PASS |
| CONTAINER endpoint does NOT create TLS protocol component | python3.14 runtime build_cbom | 0 TLS protocol components for CONTAINER endpoint | PASS |
| run_scan.py imports cleanly | python3.14 -c "import run_scan" | No ImportError | PASS |
| 19 new scanner tests pass | .venv/bin/pytest test_jwt/container/source/cloud | 19/19 passed in 0.86s | PASS |
| 52 CBOM classifier+builder tests pass | .venv/bin/pytest test_cbom_classifier+builder | 52/52 passed in 0.21s | PASS |
| Full test suite (no regressions) | .venv/bin/pytest tests/ | 139/139 passed in 0.83s | PASS |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| SCAN-03 | 03-01, 03-02, 03-04 | API/JWT scanner — REST endpoint discovery, JWKS fetch, JWT algorithm and key-size classification | SATISFIED | quirk/scanner/jwt_scanner.py (155 lines): JWKS path probing, RSA/EC key size extraction, protocol="JWT", HTTPX_AVAILABLE guard. 5/5 test_jwt_scanner.py tests pass. CBOM integration verified. |
| SCAN-04 | 03-01, 03-02, 03-04 | Container/binary crypto scanner — Syft subprocess wrapper for crypto library inventory | SATISFIED | quirk/scanner/container_scanner.py (108 lines): CRYPTO_LIB_ALLOWLIST (23 names), syft subprocess, shutil.which guard, protocol="CONTAINER". 4/4 test_container_scanner.py tests pass. |
| SCAN-05 | 03-01, 03-02, 03-04 | Source code scanner — semgrep p/cryptography integration for code-level crypto detection | SATISFIED | quirk/scanner/source_scanner.py (88 lines): semgrep subprocess, p/cryptography ruleset, service_detail="file:line", shutil.which guard, protocol="SOURCE". 5/5 test_source_scanner.py tests pass. |
| SCAN-06 | 03-01, 03-03, 03-04 | AWS cloud connector — ACM, KMS, CloudFront, ELB/ALB via boto3 | SATISFIED | quirk/scanner/aws_connector.py (202 lines): BOTO3_AVAILABLE guard, paginator-based _scan_acm/_scan_kms/_scan_cloudfront/_scan_elbv2, KMS_KEY_SPEC_MAP (13 entries), protocol="AWS". 3/3 AWS tests pass. |
| SCAN-07 | 03-01, 03-03, 03-04 | Azure cloud connector — Key Vault, App Gateway via azure-sdk-for-python | SATISFIED | quirk/scanner/azure_connector.py (146 lines): AZURE_AVAILABLE guard, DefaultAzureCredential, KeyClient at module level, _scan_keyvault_keys/_scan_app_gateways, protocol="AZURE". 2/2 Azure tests pass. |

**All 5 phase requirements SATISFIED.** No orphaned requirements for Phase 3 (REQUIREMENTS.md traceability table confirms SCAN-03..07 mapped to Phase 3, all marked Complete).

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | Zero TODO/FIXME/HACK/PLACEHOLDER comments found in any Phase 3 file. No empty implementations. All scan functions return populated CryptoEndpoint lists or empty list on graceful degradation. |

No anti-patterns detected across all 7 new/modified production files.

---

### Human Verification Required

None. All success criteria are verifiable programmatically via mock-based unit tests and runtime Python checks. Cloud scanning requires live credentials by nature — the connectors degrade gracefully when credentials are absent, and their correctness is validated by the mock-based test suite.

---

### Gaps Summary

No gaps. All 14 must-haves verified, all 5 ROADMAP success criteria confirmed, all 5 requirements satisfied, zero anti-patterns, 139/139 tests passing, no regressions.

---

## Verification Methodology

- **Level 1 (Exists):** All 15 artifact files confirmed present
- **Level 2 (Substantive):** Line counts confirmed (jwt_scanner 155, container 108, source 88, aws 202, azure 146 lines); key patterns grep-confirmed in each file
- **Level 3 (Wired):** All 12 key links confirmed: imports in run_scan.py (lines 17-21), CryptoEndpoint construction patterns in each scanner, CBOM builder protocol branching (lines 321-450)
- **Level 4 (Data Flowing):** 6 end-to-end data-flow spot-checks passed via runtime Python; endpoints merge confirmed to reach evaluate_endpoints()
- **Behavioral:** 10 spot-checks passed including full pytest runs

---

_Verified: 2026-03-29T23:55:00Z_
_Verifier: Claude (gsd-verifier)_
