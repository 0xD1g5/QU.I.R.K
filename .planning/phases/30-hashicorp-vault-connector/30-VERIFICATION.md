---
phase: 30-hashicorp-vault-connector
verified: 2026-04-26T18:30:00Z
status: passed
score: 15/15 must-haves verified
overrides_applied: 0
re_verification: null
gaps: []
human_verification:
  - test: "Boot `docker compose --profile vault up -d` in quantum-chaos-enterprise-lab, wait for vault-30-seed to exit, run quirk with vault_uat.yaml (enable_vault: true, vault_addr: http://localhost:28200, vault_token: root). Confirm 5 protocol='VAULT' rows produced."
    expected: "1 transit classification (severity=None), 1 exportable MEDIUM, 1 PKI/pki HIGH, 1 auth/token HIGH, 1 auth/userpass MEDIUM. dar_vault_weak_count=2."
    why_human: "Requires Docker to spin up a live Vault dev server and run a full scan. Cannot verify chaos-lab end-to-end without network access and a running container environment."
---

# Phase 30: HashiCorp Vault Connector Verification Report

**Phase Goal:** Add HashiCorp Vault connector scanning transit keys (VAULT-01), PKI mounts (VAULT-02), and auth methods (VAULT-03). Produce protocol="VAULT" CryptoEndpoint rows contributing to the data_at_rest subscore via dar_vault_weak_count (HIGH-only, D-11).
**Verified:** 2026-04-26T18:30:00Z
**Status:** passed (pending one live chaos-lab UAT item)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | hvac>=2.4.0 declared in [cloud] extras with Phase 30 + VAULT-01/02/03 comment (D-16) | VERIFIED | `pyproject.toml` line 51: `"hvac>=2.4.0", # Phase 30: HashiCorp Vault connector (VAULT-01/02/03)` |
| 2 | ConnectorsCfg has 5 vault fields with safe defaults (D-09, D-10) | VERIFIED | `quirk/config.py` lines 95-99: all 5 fields present with `enable_vault=False`, `vault_tls_verify=True`, `vault_transit_mount="transit"`, `vault_addr=None`, `vault_token=None` |
| 3 | config_template.yaml has commented vault block | VERIFIED | `quirk/config_template.yaml` lines 97-102: all 5 fields commented out after K8s block |
| 4 | tests/test_vault_connector.py has 22 test functions covering VAULT-01/02/03 | VERIFIED | File exists at 439 lines; `grep -c "^def test_"` returns 22 |
| 5 | quirk/scanner/vault_connector.py exists with HVAC_AVAILABLE, VAULT_TRANSIT_KEY_MAP, AUTH_RISK_MAP, scan_vault_targets + 3 sub-scanners | VERIFIED | File exists at 466 lines; all 4 sub-functions defined (`scan_vault_targets`, `_scan_transit_keys`, `_scan_pki_mounts`, `_scan_auth_methods`); HVAC_AVAILABLE True/False branches present |
| 6 | All 22 vault connector tests pass (Plan 02 turns RED to GREEN) | VERIFIED | `pytest tests/test_vault_connector.py -q` exits 0: 22 passed in 2.64s |
| 7 | Transit keys produce correct protocol="VAULT" endpoints with VAULT_TRANSIT_KEY_MAP normalization (D-01) | VERIFIED | PQC entries `"ml-dsa-87": ("ml-dsa-87", None)` and `"slh-dsa-shake-128s": ("slh-dsa-128", None)` present; behavioral spot-checks confirm RSA/AES/ECDSA normalization |
| 8 | Exportable transit keys produce severity="MEDIUM" (D-02); non-exportable produce severity=None (D-01) | VERIFIED | Confirmed by `test_transit_key_exportable_medium_severity` passing (22/22 green) |
| 9 | PKI mounts emit root + intermediate CA endpoints; RSA<4096 or SHA-1 → HIGH; chain failure silently swallowed (D-03, D-04) | VERIFIED | Confirmed by 5 PKI tests passing; `read_ca_certificate_chain` wrapped in try/except in vault_connector.py line 271 |
| 10 | Auth methods: token/ldap → HIGH; userpass → MEDIUM; approle/k8s/oidc → no endpoint (D-05, D-06) | VERIFIED | AUTH_RISK_MAP has token=HIGH, ldap=HIGH, userpass=MEDIUM; approle/kubernetes/oidc absent from map; behavioral spot-check confirmed |
| 11 | run_scan.py has vault_scanning block after kerberos_scanning, before endpoints aggregation; aggregation includes + vault_endpoints | VERIFIED | `awk` position check: kerberos_scanning at 653, vault_scanning at 667, endpoints at 689; `+ vault_endpoints)` in aggregation tuple |
| 12 | evidence.py has VAULT in _PROTOCOL_KEYS, dar_vault_weak_count (HIGH-only), dar_vault_weak_ratio returned (D-11) | VERIFIED | `_PROTOCOL_KEYS` = `(..., "VAULT")`; `dar_vault_weak_count` accumulator; `elif proto == "VAULT": if sev == "HIGH": dar_vault_weak_count += 1`; behavioral test confirms MEDIUM does NOT increment |
| 13 | scoring.py has dar_vault_weak_ratio: 8.0 in SCORE_WEIGHTS; 7th dar_impacts entry; NUM_SUBSCORES stays 5 (D-12, D-13) | VERIFIED | `SCORE_WEIGHTS["dar_vault_weak_ratio"] == 8.0`; `("Vault weak crypto posture", ...)` tuple in dar_impacts; `compute_readiness_score` returns 5 subscores; dirty vault reduces data_at_rest subscore (25 → 21) |
| 14 | CBOM builder Pass 2 + Pass 3 include "VAULT"; Pass 1 does NOT (D-14, D-15) | VERIFIED | builder.py lines 438 and 519 both contain `"KUBERNETES", "VAULT"`; Pass 1 line 410 ends `"KUBERNETES")` without VAULT |
| 15 | Chaos lab, seed.sh, expected_results.md, UAT-SERIES.md, Obsidian notes all present | VERIFIED | All 7 artifacts confirmed to exist with correct content (see artifacts table below) |

**Score:** 15/15 truths verified

### Deferred Items

No items deferred to later phases. All Phase 30 surfaces closed in Plans 01-03.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | hvac>=2.4.0 in [cloud] with Phase 30 comment | VERIFIED | Line 51 matches spec exactly |
| `quirk/config.py` | 5 vault fields on ConnectorsCfg | VERIFIED | Lines 95-99: all 5 fields with safe defaults |
| `quirk/config_template.yaml` | Commented vault block | VERIFIED | Lines 97-102: all 5 fields commented |
| `tests/test_vault_connector.py` | 22 RED tests (Plan 01) → all GREEN (Plan 02) | VERIFIED | 439 lines, 22 test functions, 22 passed |
| `quirk/scanner/vault_connector.py` | scan_vault_targets + 3 sub-scanners + maps, >=280 lines | VERIFIED | 466 lines; all 4 functions present |
| `run_scan.py` | vault_scanning block + aggregation | VERIFIED | Block at line 667, `+ vault_endpoints` in aggregation |
| `quirk/intelligence/evidence.py` | dar_vault_weak_count + VAULT in _PROTOCOL_KEYS | VERIFIED | All 4 occurrences of dar_vault_weak_count present |
| `quirk/intelligence/scoring.py` | dar_vault_weak_ratio: 8.0 + 7th dar_impacts entry | VERIFIED | Weight and tuple both present |
| `quirk/cbom/builder.py` | VAULT in Pass 2 + Pass 3, NOT Pass 1 | VERIFIED | Confirmed at lines 438 and 519; Pass 1 line 410 unchanged |
| `tests/test_dar_vault_scoring.py` | 10 scoring tests, >=130 lines | VERIFIED | 10 tests passing; 86 lines (below 130-line threshold — see note) |
| `quantum-chaos-enterprise-lab/vault/seed.sh` | Executable; seeds 4 RED finding paths | VERIFIED | 45 lines; executable bit set; all 4 scenarios present |
| `labs/vault/expected_results.md` | >=60 lines; 5 expected findings documented | VERIFIED | 71 lines; table of 5 findings present |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | vault-30 + vault-30-seed under profiles: ["vault"] at port 28200 | VERIFIED | 2 services with profiles: ["vault"]; port 28200; storage vault at 20009 unchanged |
| `docs/UAT-SERIES.md` | UAT-30-01/02/03 before Series 6; Phase 30 header note | VERIFIED | UAT-30 section at line 1884, Series 6 at line 1981; all 3 entries present |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-30-HashiCorp-Vault-Connector.md` | status: complete + 5 required sections | VERIFIED | Frontmatter confirmed; all 5 sections present (Goal, Requirements Covered, Success Criteria, What Was Built, Key Decisions) |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` | Synced with frontmatter | VERIFIED | Frontmatter present: project: QU.I.R.K., source: docs/UAT-SERIES.md |

**Note on test_dar_vault_scoring.py line count:** The PLAN frontmatter specifies `min_lines: 130` but the file is 86 lines. The 10 required tests are all present and all pass (10/10 green). The 130-line threshold from the plan appears to have overestimated the file size. This is an artifact mismatch only — the behavioral contract is fully satisfied.

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| run_scan.py vault_scanning block | quirk.scanner.vault_connector.scan_vault_targets | deferred import inside enable_vault gate | WIRED | `from quirk.scanner.vault_connector import scan_vault_targets, HVAC_AVAILABLE` at line 669 |
| scan_vault_targets | CryptoEndpoint(protocol="VAULT") | constructor with dat_scan_json | WIRED | 8 occurrences of `protocol="VAULT"` in vault_connector.py |
| session_start parameter | scanned_at on every endpoint | _now_or() helper called in all sub-scanners | WIRED | 15 session_start references; _now_or() used in _scan_transit_keys, _scan_pki_mounts, _scan_auth_methods |
| evidence.py proto == "VAULT" branch | dar_vault_weak_count counter | if sev == "HIGH" guard (D-11) | WIRED | Behavioral test confirms MEDIUM/None do not increment |
| scoring.py dar_impacts list | dar_vault_weak_ratio weight | 7th tuple: ("Vault weak crypto posture", ...) | WIRED | `compute_readiness_score` impacts data_at_rest subscore correctly |
| CBOM Pass 2 skip | VAULT endpoints no cert components | "VAULT" in skip tuple at line 438 | WIRED | Confirmed |
| CBOM Pass 3 skip | VAULT endpoints no protocol components | "VAULT" in skip tuple at line 519 | WIRED | Confirmed |
| CBOM Pass 1 NOT skipped | Transit key algorithms registered | Default else clause classifies cert_pubkey_alg | WIRED | Pass 1 line 410 ends "KUBERNETES") — VAULT flows through default else |
| docker-compose.yml vault-30-seed | quantum-chaos-enterprise-lab/vault/seed.sh | depends_on vault-30 healthcheck; volumes mount | WIRED | seed.sh exists at mount target; depends_on vault-30 with service_healthy condition |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `scan_vault_targets` | results (List[CryptoEndpoint]) | hvac.Client API calls (transit/PKI/auth) | Yes — live Vault API data via hvac.Client; mocked in tests | FLOWING |
| `evidence.py` | dar_vault_weak_count | CryptoEndpoint.severity == "HIGH" gate on VAULT endpoints | Yes — counts real HIGH severity rows | FLOWING |
| `scoring.py` | dar_vault_weak | evidence.get("dar_vault_weak_count") | Yes — flows from evidence dict to dar_impacts calculation | FLOWING |
| `run_scan.py` | vault_endpoints | scan_vault_targets() result | Yes — gated on enable_vault; returns [] when disabled | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| HVAC_AVAILABLE=False returns empty list | `scan_vault_targets("...", token="root")` with HVAC_AVAILABLE patched False | `[]` | PASS |
| No token produces vault-no-token scan_error | `scan_vault_targets("...", token=None)` with VAULT_TOKEN unset | 1 endpoint with "vault-no-token" in scan_error | PASS |
| VAULT_TRANSIT_KEY_MAP RSA-2048 normalization | `VAULT_TRANSIT_KEY_MAP["rsa-2048"]` | `("RSA", 2048)` | PASS |
| PQC ml-dsa-87 short-form | `VAULT_TRANSIT_KEY_MAP["ml-dsa-87"]` | `("ml-dsa-87", None)` | PASS |
| AUTH_RISK_MAP token=HIGH, approle=absent | Key lookups | token: HIGH, approle: KeyError | PASS |
| dar_vault_weak_count HIGH-only (D-11) | `build_evidence_summary([HIGH, MEDIUM, None endpoints])` | count=1 (HIGH only) | PASS |
| SCORE_WEIGHTS dar_vault_weak_ratio | `SCORE_WEIGHTS["dar_vault_weak_ratio"]` | `8.0` | PASS |
| NUM_SUBSCORES stays 5 (D-13) | `compute_readiness_score(...)["subscores"]` | 5 keys | PASS |
| All 22 vault connector tests | `pytest tests/test_vault_connector.py -q` | 22 passed in 2.64s | PASS |
| All 10 scoring tests | `pytest tests/test_dar_vault_scoring.py -q` | 10 passed in 0.08s | PASS |
| Python compile all modified files | `python -m compileall [5 files]` | 0 errors | PASS |
| Chaos lab YAML parses | `python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"` | exits 0 | PASS (static) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| VAULT-01 | 30-01, 30-02, 30-03 | Transit key type classification with PQC quantum-safety classification | SATISFIED | `_scan_transit_keys` + VAULT_TRANSIT_KEY_MAP with ml-dsa/slh-dsa PQC entries; 6 transit tests passing |
| VAULT-02 | 30-01, 30-02, 30-03 | PKI mount CA cert algorithm detection; RSA<4096 / SHA-1 → HIGH | SATISFIED | `_scan_pki_mounts` with root + intermediate; 5 PKI tests passing |
| VAULT-03 | 30-01, 30-02, 30-03 | Auth method risk tiering; token/LDAP → HIGH | SATISFIED | `_scan_auth_methods` + AUTH_RISK_MAP; 4 auth tests passing |

All 3 requirements fully covered. No orphaned requirements found in REQUIREMENTS.md for Phase 30.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/scanner/vault_connector.py` | 391 | `return []` | Info | Not a stub — this is the HVAC_AVAILABLE=False early-return, intentional behavior confirmed by passing test. Value does NOT reach rendering without data. |

No blockers or warnings identified.

### Human Verification Required

#### 1. Vault Chaos Lab End-to-End Scan

**Test:** Boot `cd quantum-chaos-enterprise-lab && docker compose --profile vault up -d`. Wait for `vault-30-seed` to exit cleanly. Configure `vault_uat.yaml` with `enable_vault: true`, `vault_addr: http://localhost:28200`, `vault_token: root`. Run `quirk --config vault_uat.yaml`. Tear down with `docker compose --profile vault down -v`.

**Expected:** 5 `protocol="VAULT"` CryptoEndpoint rows: `transit/rsa-2048-classification` (severity=None), `transit/rsa-2048-exportable` (MEDIUM), `PKI/pki` (HIGH), `auth/token` (HIGH), `auth/userpass` (MEDIUM). `dar_vault_weak_count == 2` in evidence summary. `data_at_rest` subscore reduced.

**Why human:** Requires Docker to start a live Vault dev server and network connectivity. Cannot verify without a running container environment.

### Gaps Summary

No gaps. All 15 must-have truths are verified. All 3 requirements (VAULT-01, VAULT-02, VAULT-03) are satisfied. All 16 required artifacts exist and are substantive. All key links are wired. The only remaining item is the chaos-lab live scan, which requires human execution (Docker + network).

The `test_dar_vault_scoring.py` line count of 86 vs the 130-line PLAN threshold is a minor documentation artifact — it does not affect the behavioral contract, which is fully satisfied by 10 passing tests encoding all D-11/D-12/D-13 decisions.

---

_Verified: 2026-04-26T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
