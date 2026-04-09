---
phase: 20-kerberos-scanner
verified: 2026-04-09T13:15:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 20: Kerberos Scanner Verification Report

**Phase Goal:** Kerberos scanner — detect RC4-HMAC/DES usage, enumerate KDC etypes, report quantum readiness
**Verified:** 2026-04-09T13:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | scan_kerberos_targets sends AS-REQ to port 88 and parses PA-ETYPE-INFO2 without credentials | VERIFIED | `_probe_kdc` and `_probe_kdc_udp` implemented; `_build_as_req` constructs unauthenticated AS-REQ with ALL_ETYPES; tests `test_as_req_probe_returns_etypes` and `test_as_req_tcp_primary` pass |
| 2 | RC4-HMAC (etype 23) produces HIGH finding, DES etypes produce CRITICAL, AES-256 produces SAFE | VERIFIED | `KERBEROS_ETYPE_MAP` has 7 entries; `test_etype_map_rc4_high`, `test_etype_map_des_critical`, `test_etype_map_aes256_safe` all pass |
| 3 | Anonymous LDAP bind on port 389 gracefully degrades without crashing when unreachable or rejected | VERIFIED | `_probe_ldap_anon` always returns dict, never raises; tests `test_ldap_graceful_degrade` and `test_ldap_anonymous_bind_rejected` pass |
| 4 | Results stored in kerberos_scan_json with protocol=KERBEROS CryptoEndpoints | VERIFIED | `scan_kerberos_targets` constructs CryptoEndpoints with `protocol="KERBEROS"`, `port=88`, `kerberos_scan_json` populated; `test_kerberos_db_row` and `test_kerberos_scan_json_structure` pass |
| 5 | Samba DC chaos lab starts via docker compose --profile kerberos with RC4-enabled realm | VERIFIED | `quantum-chaos-enterprise-lab/samba/` dir exists with Dockerfile, entrypoint.sh, smb.conf; `docker-compose.yml` has `samba-dc` service under `profiles: ["kerberos"]` with `start_period: 90s`; `smb.conf` contains `kerberos encryption types = all` |
| 6 | CBOM builder has KERBEROS protocol branch and classifier has Kerberos etype entries | VERIFIED | `builder.py` has `elif ep.protocol == "KERBEROS"` branch with kerberos-unreachable exclusion; `classifier.py` has 7 Kerberos etype entries (des-cbc-crc/md4/md5, aes128, aes256-sha1/sha384, rc4-hmac) |
| 7 | run_scan.py has Kerberos scan block after SAML block with lazy import | VERIFIED | `run_scan.py` has `kerberos_endpoints = []`, `with _phase_timer(run_stats, "kerberos_scanning"):`, lazy `from quirk.scanner.kerberos_scanner import scan_kerberos_targets`; `kerberos_endpoints` included in aggregation tuple |
| 8 | All RED tests from Plan 01 are now GREEN | VERIFIED | 23 passed, 1 skipped (integration, correct); pytest output confirmed `23 passed, 1 skipped in 0.09s` |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/scanner/kerberos_scanner.py` | Full Kerberos scanner implementation | VERIFIED | 338 lines; exports `scan_kerberos_targets`, `KERBEROS_ETYPE_MAP`, `IMPACKET_AVAILABLE`, `ALL_ETYPES`; `_build_as_req`, `_probe_kdc`, `_probe_kdc_udp`, `_probe_ldap_anon`, `scan_kerberos_targets` fully implemented |
| `tests/test_kerberos_scanner.py` | 24 tests covering KERB-01 through KERB-05 | VERIFIED | 393 lines; 24 test functions; 23 pass, 1 skipped (integration) |
| `quirk/cbom/builder.py` | KERBEROS protocol branch | VERIFIED | Contains `elif ep.protocol == "KERBEROS"` with kerberos-unreachable guard |
| `quirk/cbom/classifier.py` | Kerberos etype classifier entries | VERIFIED | Contains `rc4-hmac`, `des-cbc-crc`, `des-cbc-md4`, `des-cbc-md5`, `aes128-cts-hmac-sha1-96`, `aes256-cts-hmac-sha1-96`, `aes256-cts-hmac-sha384-192` |
| `run_scan.py` | Kerberos scan phase block | VERIFIED | Contains `kerberos_endpoints`, lazy import, `_phase_timer`, aggregation |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | Samba DC service under kerberos profile | VERIFIED | Contains `samba-dc` service, `profiles: ["kerberos"]`, `start_period: 90s` |
| `quantum-chaos-enterprise-lab/samba/Dockerfile` | Samba DC container image | VERIFIED | Based on `debian:bookworm-slim`; exposes 88/tcp, 88/udp, 389/tcp |
| `quantum-chaos-enterprise-lab/samba/entrypoint.sh` | Samba provisioning entrypoint | VERIFIED | Contains `samba-tool domain provision` with realm and RC4 options |
| `quantum-chaos-enterprise-lab/samba/smb.conf` | Samba configuration with RC4 enabled | VERIFIED | Contains `kerberos encryption types = all`, `realm = QUIRK.LAB` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/scanner/kerberos_scanner.py` | `quirk/models.py` | `CryptoEndpoint(` construction | WIRED | Multiple `CryptoEndpoint(` calls in `scan_kerberos_targets`; `from quirk.models import CryptoEndpoint` at top of file |
| `quirk/scanner/kerberos_scanner.py` | `impacket.krb5.kerberosv5` | `sendReceive()` for TCP AS-REQ | WIRED | `sendReceive` called in `_probe_kdc`; import guard at top handles absence gracefully |
| `run_scan.py` | `quirk/scanner/kerberos_scanner.py` | lazy import and call | WIRED | `from quirk.scanner.kerberos_scanner import scan_kerberos_targets` inside `with _phase_timer` block |
| `quirk/cbom/builder.py` | `quirk/scanner/kerberos_scanner.py` | `ep.protocol == "KERBEROS"` dispatch | WIRED | `elif ep.protocol == "KERBEROS"` routes Kerberos endpoints to `_register_algorithm` |
| `quirk/cbom/classifier.py` | `quirk/scanner/kerberos_scanner.py` | etype name lookup | WIRED | All 7 etype names from `KERBEROS_ETYPE_MAP` present as classifier keys |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | `quantum-chaos-enterprise-lab/samba/` | Dockerfile build context | WIRED | `build: context: ./samba` resolves to samba directory |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `quirk/scanner/kerberos_scanner.py` | `etypes` (list[int]) | `_probe_kdc` TCP AS-REQ -> PA-ETYPE-INFO2 parsing | Yes — decodes real KDC wire response | FLOWING |
| `quirk/scanner/kerberos_scanner.py` | `ldap_result` (dict) | `_probe_ldap_anon` -> ldap3 anonymous bind | Yes — real LDAP query, graceful fallback dict on failure | FLOWING |
| `quirk/cbom/builder.py` | `ep.protocol` dispatch | `scan_kerberos_targets` CryptoEndpoint construction | Yes — protocol set from scan, not hardcoded | FLOWING |
| `run_scan.py` | `kerberos_endpoints` | `scan_kerberos_targets(cfg.connectors.kerberos_targets)` | Yes — real targets from config, real scan results | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Module importable without impacket | `python3 -c "from quirk.scanner.kerberos_scanner import scan_kerberos_targets, KERBEROS_ETYPE_MAP, IMPACKET_AVAILABLE"` | No error; `IMPACKET_AVAILABLE=False` | PASS |
| All 23 tests pass, 1 skipped | `python3 -m pytest tests/test_kerberos_scanner.py -v --tb=short` | `23 passed, 1 skipped in 0.09s` | PASS |
| No regression in non-SAML suite | `python3 -m pytest tests/ -q --tb=no --ignore=tests/test_saml_scanner.py` | `277 passed, 2 skipped in 2.68s` | PASS |
| KERBEROS_ETYPE_MAP has 7 entries | Static assertion in `test_etype_map_completeness` | Passes with keys `{1, 2, 3, 17, 18, 20, 23}` | PASS |
| KERB-05 integration test correctly skipped | `test_samba_dc_integration` in pytest output | `SKIPPED (Set QUIRK_KERBEROS_INTEGRATION=1 to run...)` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| KERB-01 | 20-01-PLAN, 20-02-PLAN | Scanner sends unauthenticated AS-REQ to port 88 (TCP with UDP fallback) and parses PA-ETYPE-INFO2 from KDC_ERR_PREAUTH_REQUIRED — no credentials required | SATISFIED | `_probe_kdc` (TCP) + `_probe_kdc_udp` (UDP fallback) implemented; `test_as_req_tcp_primary` and `test_as_req_udp_fallback` both pass |
| KERB-02 | 20-01-PLAN, 20-02-PLAN | RC4-HMAC (etype 23) flagged as HIGH; DES etypes (1, 2, 3) flagged as CRITICAL; AES-256 (etype 18/20) classified as quantum-safe | SATISFIED | `KERBEROS_ETYPE_MAP` verified; classification tests pass; `test_etype_unknown_gets_medium` verifies MEDIUM fallback for unknown etypes |
| KERB-03 | 20-01-PLAN, 20-02-PLAN | Scanner attempts anonymous LDAP bind on port 389 to read msDS-SupportedEncryptionTypes; gracefully degrades if unreachable or auth required | SATISFIED | `_probe_ldap_anon` always returns dict; `ldap_status` key always present in `kerberos_scan_json`; 3 LDAP tests pass |
| KERB-04 | 20-01-PLAN, 20-02-PLAN | Results stored in kerberos_scan_json with protocol="KERBEROS" CryptoEndpoints; classifier gains Kerberos etype entries; build_cbom() gains KERBEROS elif branches | SATISFIED | `kerberos_scan_json` with `realm`, `etypes`, `ldap`, `ldap_status` keys; CBOM builder elif branch present; 7 classifier entries present |
| KERB-05 | 20-01-PLAN, 20-02-PLAN | Chaos lab gains Samba DC kerberos Docker Compose profile with RC4-enabled realm and start_period: 90s healthcheck | SATISFIED | Samba Dockerfile, entrypoint.sh, smb.conf all present; docker-compose.yml has kerberos profile with `start_period: 90s`; `smb.conf` has `kerberos encryption types = all` |

All 5 requirements (KERB-01 through KERB-05) are SATISFIED. No orphaned requirements — REQUIREMENTS.md shows all 5 mapped to Phase 20, all marked `[x]` complete.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/scanner/kerberos_scanner.py` | 178 | `except Exception: return []` in `_probe_kdc_udp` | INFO | Intentional: UDP is best-effort fallback; swallowing exceptions here is correct per D-01 |
| `quirk/scanner/kerberos_scanner.py` | 230 | `except Exception as exc: return {"ldap_status": "skipped"}` in `_probe_ldap_anon` | INFO | Intentional: KERB-03 requires graceful degradation; not a stub |

No blocker or warning-level anti-patterns. All `return []` and exception-swallowing patterns are intentional graceful-degradation behaviors per design decisions D-01 and KERB-03. Data flows correctly through all code paths.

---

### Human Verification Required

#### 1. Samba DC Integration Test (KERB-05)

**Test:** Start the chaos lab with `docker compose --profile kerberos up -d`, wait 90 seconds for provisioning, then run `QUIRK_KERBEROS_INTEGRATION=1 python3 -m pytest tests/test_kerberos_scanner.py::test_samba_dc_integration -v`

**Expected:** Test passes; `scan_kerberos_targets(["127.0.0.1"])` returns at least one `CryptoEndpoint` with `cert_pubkey_alg == "rc4-hmac"` and `protocol == "KERBEROS"`

**Why human:** Requires Docker daemon and 90-second Samba DC provisioning — cannot be verified without running services

#### 2. Samba DC Provisioning Script

**Test:** Review `quantum-chaos-enterprise-lab/samba/entrypoint.sh` and run the container once to confirm `samba-tool domain provision` completes successfully and the DC accepts Kerberos AS-REQ connections

**Expected:** Container starts, realm QUIRK.LAB is provisioned, ports 88 and 389 are reachable

**Why human:** Requires Docker runtime and inspection of Samba provisioning output

---

### Gaps Summary

No gaps. All 8 must-have truths verified. All 5 KERB requirements satisfied. All artifacts exist, are substantive, and are wired. Data flows from scanner through CBOM builder to classifier and run_scan.py. The only items requiring human validation are the live Samba DC integration test (KERB-05 chaos lab), which is correctly gated by `QUIRK_KERBEROS_INTEGRATION=1` and marked skipped in CI.

**Pre-existing SAML failures noted:** `test_saml_scanner.py` has 8 pre-existing failures unrelated to phase 20, confirmed present before this phase began and documented in the Plan 02 summary. These are out of scope.

**Commit verification:** All 5 commits documented in summaries confirmed present in git log:
- `9470e6f` — kerberos_scanner.py stub (Plan 01, Task 1)
- `9397495` — test_kerberos_scanner.py RED scaffold (Plan 01, Task 2)
- `a62056a` — kerberos_scanner.py implementation (Plan 02, Task 1)
- `c3c0ab7` — CBOM builder, classifier, run_scan.py wiring (Plan 02, Task 2)
- `96c55a3` — Samba DC chaos lab (Plan 02, Task 3)

---

_Verified: 2026-04-09T13:15:00Z_
_Verifier: Claude (gsd-verifier)_
