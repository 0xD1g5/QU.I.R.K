---
phase: 25
slug: identity-findings-accuracy
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-24
---

# Phase 25 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| test code → production module | `tests/test_identity_findings_accuracy.py` imports `_derive_findings` / `_derive_identity_findings` from `quirk.dashboard.api.routes.scan` — read-only function import, no I/O, no secrets | Function references only |
| scan.py import → saml_scanner | Module-level import of `OIDC_ALG_SEVERITY` dict — read-only constant, no I/O, no external input | Python dict constant |
| pyproject.toml → pip resolver | `ldap3>=2.9.1` pulled from PyPI on `pip install .[identity]` — standard supply chain trust boundary | Package metadata + wheel |
| documentation → developer/QA | `expected_results_v3.md` is a plain Markdown file documenting internal chaos lab port/profile configuration | Chaos lab port numbers, profile names (non-production) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-25-01 | Tampering | `tests/test_identity_findings_accuracy.py` | accept | Test file only — no production attack surface added. Tampering mitigated by git history and CI gate. | closed |
| T-25-02 | Spoofing | `OIDC_ALG_SEVERITY` import (`scan.py:29`) | accept | Dict is a first-party module constant under version control; no external input source. No spoofing vector. | closed |
| T-25-03 | Information Disclosure | TLS-bleed guard — `_derive_findings()` (`scan.py:55`) | mitigate | Guard (`proto in {"KERBEROS", "SAML", "DNSSEC"}: continue`) prevents identity endpoints from leaking into TLS findings list, eliminating false-positive disclosure in API responses. Mitigation IS the fix. | closed |
| T-25-04 | Tampering | `pyproject.toml` `ldap3>=2.9.1` addition | accept | `ldap3` is a well-maintained LDAP client library (active PyPI, MIT license). No upper-bound conflict risk at `>=2.9.1`. Transitive conflict with impacket assessed as low risk. | closed |
| T-25-05 | Information Disclosure | `expected_results_v3.md` chaos lab port/profile details | accept | File documents internal chaos lab configuration for QA use. No production credentials or secrets. Port numbers are chaos lab ports (non-standard, non-production). Appropriate for version-controlled test oracle. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-25-01 | T-25-01 | Test file manipulation is mitigated by git history integrity and CI enforcement — no production attack surface introduced. Acceptance is consistent with standard test-code security posture. | gsd-security-auditor | 2026-04-24 |
| AR-25-02 | T-25-02 | `OIDC_ALG_SEVERITY` is a first-party constant dict with no external inputs. Spoofing would require compromising the source repository itself, which is beyond the threat scope of this phase. | gsd-security-auditor | 2026-04-24 |
| AR-25-04 | T-25-04 | `ldap3>=2.9.1` has no known critical CVEs at the time of acceptance. MIT license. Open lower-bound pin accepted per project dependency policy (consistent with impacket pin pattern). | gsd-security-auditor | 2026-04-24 |
| AR-25-05 | T-25-05 | Chaos lab port numbers and profile names are internal QA configuration, not production endpoints. Disclosure risk is informational only — no credentials, keys, or exploitable topology details included. | gsd-security-auditor | 2026-04-24 |

---

## Verification Evidence

### T-25-03 Code Evidence (mitigate — verified)

**TLS-bleed guard at `quirk/dashboard/api/routes/scan.py:55`:**
```python
for ep in endpoints:
    # D-03: skip identity protocol endpoints — handled exclusively by
    # _derive_identity_findings(); none of the TLS checks apply to them.
    proto = (ep.protocol or "").upper()
    if proto in {"KERBEROS", "SAML", "DNSSEC"}:
        continue
```

**OIDC_ALG_SEVERITY import at `quirk/dashboard/api/routes/scan.py:29`:**
```python
from quirk.scanner.saml_scanner import OIDC_ALG_SEVERITY
```

**Test verification (GREEN gate, all 4 passed):**
- `test_saml_endpoint_absent_from_tls_findings` — PASSED (T-25-03 directly exercised)
- `test_rs256_oidc_produces_identity_finding` — PASSED (T-25-02 import verified)
- `test_rs384_oidc_produces_identity_finding` — PASSED
- `test_pyproject_ldap3_in_identity_extras` — PASSED (T-25-04 verified)

Source: `25-02-SUMMARY.md` — 363 passed, 0 new regressions.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-24 | 5 | 5 | 0 | gsd-security-auditor (automated, State B) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-24
