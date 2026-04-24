---
phase: 25-identity-findings-accuracy
verified: 2026-04-24T23:06:41Z
status: human_needed
score: 8/8 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run quirk scan against the simpla-samlphp chaos lab profile and confirm findings appear in the Identity tab (source='saml'), not the Findings tab"
    expected: "1 CRITICAL finding for RSA-1024 signing cert and optionally 1 HIGH finding for SHA-1 algorithm URI; zero findings in the TLS Findings tab for this target"
    why_human: "Requires Docker chaos lab environment running; cannot verify tab routing in the dashboard UI programmatically"
  - test: "Run quirk scan against the samba-dc chaos lab profile and confirm RC4-HMAC and AES128-SHA1 Kerberos findings appear in the Identity tab (source='kerberos')"
    expected: ">= 1 HIGH finding for rc4-hmac (etype 23); findings visible in Identity tab only, not TLS Findings tab"
    why_human: "Requires Docker chaos lab environment and live Kerberos AS-REQ exchange; cannot verify without running containers"
---

# Phase 25: Identity Findings Accuracy Verification Report

**Phase Goal:** Fix identity findings accuracy — route RS-family OIDC endpoints to _derive_identity_findings(), prevent TLS-bleed in _derive_findings(), add ldap3 dependency, and document chaos lab expected results.
**Verified:** 2026-04-24T23:06:41Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | RS256/RS384/RS512 OIDC endpoints produce IdentityFinding(source='saml', severity='HIGH') from _derive_identity_findings() | VERIFIED | scan.py line 230: `severity = OIDC_ALG_SEVERITY.get(alg)`; line 247: `source="saml"`; test_rs256 and test_rs384 both PASS |
| 2 | SAML/KERBEROS/DNSSEC endpoints produce zero FindingItem entries from _derive_findings() | VERIFIED | scan.py lines 54-56: guard `if proto in {"KERBEROS", "SAML", "DNSSEC"}: continue`; test_saml_endpoint_absent_from_tls_findings PASSES |
| 3 | pyproject.toml [identity] extras contains 'ldap3>=2.9.1' alongside impacket | VERIFIED | pyproject.toml line 42: `"ldap3>=2.9.1"` present in identity block; test_pyproject_ldap3_in_identity_extras PASSES |
| 4 | All 4 Phase 25 RED tests pass GREEN | VERIFIED | pytest output: 4 passed in 0.16s — test_rs256, test_rs384, test_saml_tls_bleed, test_pyproject_ldap3 all PASSED |
| 5 | Zero new regressions in the full test suite | VERIFIED | Full suite: 363 passed, 3 failed (same 3 pre-existing failures), 3 skipped — 0 new failures introduced |
| 6 | expected_results_v3.md contains three new identity chaos lab sections for DNSSEC, SAML/OIDC, and Kerberos | VERIFIED | grep confirms exactly 3 headings: "Phase 25 — DNSSEC Profile", "Phase 25 — SAML/OIDC Profile", "Phase 25 — Kerberos Profile" at lines 224, 241, 256 |
| 7 | Each section follows the existing Phase 4 profile table format (heading, table, validation command, expected outcome) | VERIFIED | All 3 sections contain: Markdown table, **Scanner validation command:** block referencing --profile bind9/simpla-samlphp/samba-dc, **Expected:** summary sentence |
| 8 | OIDC_ALG_SEVERITY is imported from saml_scanner into scan.py as a module-level import | VERIFIED | scan.py line 29: `from quirk.scanner.saml_scanner import OIDC_ALG_SEVERITY` — not in a try/except or function body |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_identity_findings_accuracy.py` | RED scaffold with 4 failing tests (Plan 01), then GREEN after Plan 02 | VERIFIED | 153 lines; 4 test methods in TestIdentityFindingsAccuracy; all 4 PASS; imports resolve cleanly |
| `quirk/dashboard/api/routes/scan.py` | RS-family OIDC check in _derive_identity_findings + TLS-bleed guard in _derive_findings | VERIFIED | Line 29: OIDC_ALG_SEVERITY import; lines 53-56: D-03 TLS-bleed guard; lines 229-248: RS-family IdentityFinding block |
| `pyproject.toml` | ldap3>=2.9.1 in [identity] extras | VERIFIED | Line 42: `"ldap3>=2.9.1"` present alongside impacket>=0.13.0,<0.14 |
| `quantum-chaos-enterprise-lab/expected_results_v3.md` | Identity chaos lab expected results for all three v4.2 scanner profiles | VERIFIED | 3 new Phase 25 sections appended (lines 224-267); original Phase 4 sections intact |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| tests/test_identity_findings_accuracy.py | quirk.dashboard.api.routes.scan._derive_identity_findings | direct import | WIRED | Line 6: `from quirk.dashboard.api.routes.scan import _derive_findings, _derive_identity_findings` — import resolves; tests exercise both functions |
| quirk/dashboard/api/routes/scan.py::_derive_identity_findings | quirk/scanner/saml_scanner.OIDC_ALG_SEVERITY | module-level import | WIRED | scan.py line 29 imports at module level; used at line 230 in SAML branch |
| quirk/dashboard/api/routes/scan.py::_derive_findings | identity protocol skip guard | proto in set check | WIRED | Lines 53-56 guard fires before any TLS check in the loop body |
| quantum-chaos-enterprise-lab/expected_results_v3.md | docker-compose.yml profile names | validation commands reference --profile | WIRED | bind9, simpla-samlphp, samba-dc profile names appear in scanner validation commands at lines 235, 250, 265 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| scan.py::_derive_identity_findings | results (IdentityFinding list) | ep.cert_pubkey_alg via OIDC_ALG_SEVERITY.get(alg) | Yes — dict lookup on live endpoint data | FLOWING |
| scan.py::_derive_findings | findings (FindingItem list) | ep.protocol guard filters real endpoint protocol field | Yes — guard uses real ep.protocol from DB | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| RS256 OIDC → IdentityFinding(HIGH, saml) | pytest tests/test_identity_findings_accuracy.py::TestIdentityFindingsAccuracy::test_rs256_oidc_produces_identity_finding | PASSED | PASS |
| RS384 OIDC → IdentityFinding(HIGH) | pytest test_rs384_oidc_produces_identity_finding | PASSED | PASS |
| SAML endpoint → zero TLS FindingItems | pytest test_saml_endpoint_absent_from_tls_findings | PASSED | PASS |
| pyproject.toml contains ldap3>=2.9.1 | pytest test_pyproject_ldap3_in_identity_extras | PASSED | PASS |
| Full regression suite | python -m pytest tests/ -q | 363 passed, 3 pre-existing failed, 0 new failures | PASS |
| Compile check | python -m compileall quirk/dashboard/api/routes/scan.py | No output (exit 0) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| SAML-04 | 25-01, 25-02 | OIDC RS256 endpoints produce IdentityFinding(source="saml"), not TLS-sourced findings | SATISFIED | RS-family check at scan.py line 229-248 emits source="saml"; TLS-bleed guard at lines 53-56 prevents TLS bleed |
| IDENT-02 | 25-01, 25-02 | Identity findings from OIDC RS256 appear in the Identity tab, not the Findings tab | NEEDS HUMAN | Backend routing is correct (source="saml" flows to identity findings, not TLS findings); UI tab routing requires chaos lab visual verification |
| IDENT-03 | 25-01, 25-02 | OIDC RS-family algorithms (RS256, RS384, RS512) classified via OIDC_ALG_SEVERITY lookup | SATISFIED | OIDC_ALG_SEVERITY imported at line 29; .get(alg) used at line 230; RS256 and RS384 confirmed via passing tests |
| KERB-03 | 25-01, 25-02 | ldap3>=2.9.1 included in [identity] extras and resolves without conflicts | SATISFIED | pyproject.toml line 42 confirmed; test passes; no conflict reported in test suite (363 passing) |
| INFRA-03 | 25-02, 25-03 | pip install quirk[identity] installs ldap3; Kerberos LDAP enumeration is no longer always-inert | NEEDS HUMAN | ldap3 entry confirmed in pyproject.toml; actual pip install and Kerberos LDAP enumeration behavior requires live environment test |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|---------|--------|
| None | — | — | — | — |

No TODO, FIXME, PLACEHOLDER, empty implementations, or stub indicators found in any modified file.

### Human Verification Required

#### 1. IDENT-02: UI tab routing — Identity tab vs Findings tab

**Test:** Start the QUIRK dashboard, run a scan against the simpla-samlphp chaos lab profile (`docker compose --profile simpla-samlphp up -d`), then navigate to the dashboard and verify the RS256/RSA-1024 SAML findings appear in the Identity tab and are absent from the TLS Findings tab.
**Expected:** SAML/OIDC findings with source="saml" visible only in the Identity tab; Findings tab shows zero entries for that target.
**Why human:** The backend routing is verified programmatically (source="saml" is set correctly and the TLS-bleed guard is in place), but confirming the dashboard UI correctly routes by source field requires a running application with a real scan result.

#### 2. INFRA-03: Live ldap3 install and Kerberos LDAP enumeration

**Test:** In a clean virtualenv, run `pip install -e ".[identity]"` and verify ldap3 is installed. Then run a scan against the samba-dc chaos lab profile and confirm Kerberos findings appear (not the always-inert placeholder behavior from before ldap3 was present).
**Expected:** `pip install quirk[identity]` completes with ldap3>=2.9.1 installed; Kerberos scanner returns RC4-HMAC and/or AES128-SHA1 etype findings in the Identity tab.
**Why human:** Cannot run pip install in the verification environment without side effects; live Kerberos AS-REQ enumeration requires the samba-dc container running and network access to localhost:88.

### Gaps Summary

No blocking gaps found. All 8 must-have truths are verified against the actual codebase. The two human verification items (IDENT-02 UI tab routing, INFRA-03 live install + Kerberos enumeration) represent behaviors that are correctly implemented at the backend/config layer but require a running environment and visual/functional confirmation to close fully.

All commits are present in git history: efd08fa (Plan 01 RED scaffold), 5afb834 (Plan 02 scan.py edits), ec91d4b (Plan 02 pyproject.toml), 8cb1ffe (Plan 03 expected results).

---

_Verified: 2026-04-24T23:06:41Z_
_Verifier: Claude (gsd-verifier)_
