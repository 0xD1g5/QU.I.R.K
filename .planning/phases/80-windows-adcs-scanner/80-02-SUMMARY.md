---
phase: 80
plan: 02
subsystem: identity-scanner
tags: [adcs, ldap, esc, cbom, scanner]
requirements: [ADCS-01, ADCS-02, ADCS-05, ADCS-06, ADCS-09]
dependency_graph:
  requires: [80-01]
  provides: [adcs-scanner-runtime, cbom-adcs-emit, run_scan-adcs-dispatch]
  affects: [quirk/scanner, quirk/cbom/builder, quirk/models, run_scan]
tech_stack:
  added: [ldap3 (existing identity extra), cryptography.x509.load_der_x509_certificate]
  patterns: [smime_scanner template, paged_search SUBTREE, SIMPLE-or-ANONYMOUS bind, ADCS-UNREACH coverage gap]
key_files:
  created:
    - quirk/scanner/adcs_scanner.py
  modified:
    - quirk/models.py
    - quirk/cbom/builder.py
    - run_scan.py
decisions:
  - "ESC1/2/3/6 emit deterministic HIGH findings from LDAP attribute-only logic"
  - "ESC4/5/7/8 emit one LOW ADCS-COVERAGE-GAP per ESC class per target (D-80-R8)"
  - "ESC6 emitted as HIGH (not MEDIUM as RESEARCH Pattern 2 sketch) — REQUIREMENTS ADCS-02 lists ESC6 alongside ESC1/2/3 as HIGH-class observable misconfig"
  - "ESC2 fires on either NO_SECURITY_EXTENSION (0x80000) or any-purpose EKU — broader than RESEARCH which only listed any-purpose"
  - "ESC3 requires both cert-request-agent EKU AND missing manager approval (ra_sig == 0) per plan instructions"
metrics:
  duration: ~12 min
  tasks_complete: 3
  files_touched: 4
  completed: 2026-05-16
---

# Phase 80 Plan 02: Scanner module + CBOM Pass-1 emit + orchestrator wiring Summary

Read-only AD CS LDAP scanner landed, wired through CBOM Pass-1 / Pass-2 / Pass-3 skip-tuples and run_scan.py data_at_rest stage.

## What Was Built

### `quirk/scanner/adcs_scanner.py` (NEW — 495 lines)

- ADCS-09 module header invariant verbatim (read-only, no enrollment / no template creation / no CSR / no writes).
- Imports: `ldap3` (gated by `LDAP3_AVAILABLE`), `cryptography.x509.load_der_x509_certificate`, `rsa`/`ec` for key classification, `quirk.util.weak_crypto.is_weak_cipher`, `quirk.util.safe_exc.safe_str`. **No `certipy`, no `certipy_ad`, no `CertificateSigningRequestBuilder`.**
- Constants: `CT_FLAG_*`, `EKU_*` (RESEARCH Pattern 2 verbatim); `_COVERAGE_GAP_ESCS = ("ESC4", "ESC5", "ESC7", "ESC8")`.
- Helpers:
  - `_realm_to_base_dn` — round-trips QUIRK.LAB ↔ DC=quirk,DC=lab; empty → "".
  - `_parse_target` — accepts URL strings, bare host[:port], or SimpleNamespace-style objects.
  - `_parse_ca_cert(der_bytes)` — DER-only (no PEM fallback per MS-CRTD §2.21); returns key_alg/key_bits/sig_hash/serial/not_after/expired or None.
  - `_decode_attr_list` / `_scalar` — Pitfall 3 (`int(... or 0)`) and Pitfall 7 (bytes→str OID decode) safety.
  - `_classify_template_escs` — emits ESC1/2/3/6 with reasons.
  - `_bind_and_query` — SIMPLE bind if creds supplied, ANONYMOUS otherwise; raises `LDAPBindError` on failure so caller converts to ADCS-UNREACH.
- Top-level `scan_adcs_targets(targets, timeout=10, logger=None, session_start=None, *, search_base=None, user=None, password=None)` — three phases per target: (A) CA enumeration → weak-signing-alg / weak-rsa-key HIGH findings, (B) template enumeration → ESC1/2/3/6 HIGH findings, (C) coverage-gap emission → 4 LOW findings (ESC4/5/7/8).
- All exception paths convert to LOW `adcs-unreachable` CryptoEndpoint with `scan_error_category="exception"`; no exception propagates.

### `quirk/models.py`

Appended `adcs_scan_json = Column(Text, nullable=True)` immediately after `smime_scan_json` (Pydantic-via-SQLAlchemy surface counterpart to the DB column from Plan 80-01).

### `quirk/cbom/builder.py`

- **Pass-1 emit** at line 464: `elif ep.protocol == "ADCS"` registers `cert_pubkey_alg` (CA signing alg or template key alg) via `_register_algorithm`.
- **Pass-2 skip-tuple at line 538** — appended `"ADCS"` to inline tuple `("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC", "SMIME", "ADCS", ...)`.
- **Pass-3 skip-tuple at line 623** — appended `"ADCS"` to inline tuple `("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "DNSSEC", "SAML", "KERBEROS", "SMIME", "ADCS", ...)`.
- Pass-2 line landed at 538 as predicted; Pass-3 landed at 623 (one line below the predicted 622, because the Pass-1 ADCS branch added 9 lines above). Non-comment `"ADCS"` occurrences = 3 (Pass-1 + Pass-2 + Pass-3).

### `run_scan.py`

- `_dar_protocols` (line 1210) — append `"ADCS"`.
- Resume bucket (line ~1220) — `adcs_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "ADCS"]`.
- Resume-count log — includes `{len(adcs_endpoints)} adcs`.
- `_run_adcs_phase()` defined at line ~1419 immediately after `_run_smime_phase`; dispatched via `_wrapped_phase` into `adcs_endpoints` (data_at_rest stage). Passes `adcs_user`/`adcs_password` from config.
- `_dar_eps` sum (line ~1454) and final endpoints concat (line ~1620) both include `adcs_endpoints`.

## ESC Mappings Verified (against `quantum-chaos-enterprise-lab/adcs/ldif/20-templates.ldif`)

| Fixture template | Classifier output | Reason chain |
|------------------|-------------------|--------------|
| `BadTemplate-ESC1` (NameFlag=1, RA-Sig=0, EKU=client-auth) | 1 HIGH ESC1 | enrollee-supplies-subject + client-auth-eku + no-ra-signature |
| `BadTemplate-ESC4` (NameFlag=0, RA-Sig=1, nTSecurityDescriptor present) | 0 findings (caller emits ESC4 coverage-gap LOW) | n/a |
| `SafeTemplate` (NameFlag=0, RA-Sig=1, EKU=email-protection) | 0 findings | n/a |
| Fake CA (RSA-1024) | 1 HIGH (weak-rsa-key) | weak-rsa-key |

**Per-target output total against the chaos lab** (after Plan 80-04 wires the full smoke test): 1 HIGH weak-CA + 1 HIGH ESC1 + 4 LOW COVERAGE-GAP (ESC4/5/7/8) = **6 findings**, exactly matching `expected_results_v4.md` §profile-adcs.

## Verification

- `python -m compileall quirk/scanner/adcs_scanner.py quirk/models.py quirk/cbom/builder.py run_scan.py quirk/` — clean.
- `python -c "from quirk.scanner.adcs_scanner import scan_adcs_targets, _realm_to_base_dn, _classify_template_escs"` — imports succeed; `_realm_to_base_dn` round-trips.
- Forbidden imports absent: `grep -E 'import +certipy|from +certipy|CertificateSigningRequestBuilder' quirk/scanner/adcs_scanner.py` → no matches.
- `grep -c '"ADCS"' quirk/cbom/builder.py` (non-comment) = 3.
- `grep -c 'adcs_endpoints' run_scan.py` = 5.
- Mock-based classifier test against the three lab fixtures returned the expected (1 ESC1 HIGH, 0, 0) tuple set.
- DER-cert parsing path validated against a freshly-generated RSA-1024 SHA-256 cert — `weak-rsa-key` reason fires correctly.
- Existing test suite: `tests/test_cbom_builder.py`, `test_cbom_classifier.py`, `test_cbom_skip_lists.py`, `test_smime_scanner.py`, `test_smime_ast_gate.py`, `test_smime_no_envelope_leak.py` — **88/88 passing** (Phase 79 work stays green).
- Pre-existing test failures observed (NOT caused by this plan, not in scope):
  - `tests/test_cbom_integration.py::test_write_reports_creates_cbom_files` — `quirk.reports.writer` attribute issue.
  - `tests/test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles` — pre-existing `RSA-kex` / `ssh-dss` classifier gap.

## Deviations from Plan

**1. [Rule 2 — missing critical functionality] ESC6 severity HIGH instead of MEDIUM.** RESEARCH Pattern 2 sketched ESC6 as MEDIUM, but REQUIREMENTS ADCS-02 + the plan's hard-constraint list explicitly lists ESC6 alongside ESC1/2/3 as HIGH. Followed the binding constraint (HIGH) over the RESEARCH sketch.

**2. [Rule 2 — broader coverage] ESC2 fires on NO_SECURITY_EXTENSION enrollment bit (0x80000) in addition to any-purpose EKU.** Plan instructions ("ESC2 → msPKI-Enrollment-Flag has NO_SECURITY_EXTENSION bit 0x80000 → HIGH") supersede RESEARCH Pattern 2 which only listed any-purpose. Both checks now emit ESC2 HIGH.

**3. [Rule 2 — tighter ESC3] ESC3 requires both cert-request-agent EKU AND `msPKI-RA-Signature == 0`.** Plan instructions ("ESC3 → ... + missing manager approval → HIGH"); RESEARCH Pattern 2 only checked the EKU. Adding the manager-approval clause prevents false positives on locked-down enrollment-agent templates.

**4. [Rule 3 — blocking input handling] `_decode_attr_list` / `_scalar` helpers added.** RESEARCH Pattern 2 assumed clean dict access; real `paged_search` `raw_attributes` returns bytes for OID lists (Pitfall 7) and either `[b"1"]` or `1` for scalars (Pitfall 3). Helpers normalize so the classifier remains deterministic across ldap3 versions.

**5. Line-drift note.** Plan instructions cite Pass-3 line 622; after the Pass-1 ADCS branch inserts 9 lines, the live Pass-3 skip-tuple landed at line 623. Append still correct — site identified by content (`"SMIME"` neighbor), not by absolute line number.

**6. Unbind safety.** Added a defensive `try/except: pass` around `conn.unbind()` at the end of each target loop — not in plan, but matches Rule 3 (avoid leaked LDAP connections poisoning subsequent targets). Pass per ADCS-04 SC#2 (no exception propagates).

Not touched (per plan):
- `quirk/intelligence/scoring.py` — Plan 80-03 owns.
- `quirk/intelligence/evidence.py` — Plan 80-03 owns.
- `tests/test_score_weights_invariant.py` — Phase 83 owns the SUM bump.

## Commit

- **SHA:** `73f92e0`
- **Message:** `feat(80-02): adcs scanner module + cbom pass-1 emit + skip-list extensions`
- **Files:** `quirk/scanner/adcs_scanner.py`, `quirk/models.py`, `quirk/cbom/builder.py`, `run_scan.py`.

## Self-Check: PASSED

- FOUND: `quirk/scanner/adcs_scanner.py` (495 lines)
- FOUND: commit `73f92e0` in git log
- FOUND: 3 non-comment `"ADCS"` occurrences in `quirk/cbom/builder.py`
- FOUND: 5 `adcs_endpoints` references in `run_scan.py`
- FOUND: `adcs_scan_json` column in `quirk/models.py`
- FOUND: ADCS-09 read-only invariant string in scanner module header
- NO forbidden `certipy` / `CertificateSigningRequestBuilder` references
