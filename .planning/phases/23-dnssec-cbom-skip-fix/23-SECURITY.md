---
phase: 23
slug: dnssec-cbom-skip-fix
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-24
---

# Phase 23 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| None | Internal transform filter — `build_cbom()` operates on already-persisted `CryptoEndpoint` rows from the local SQLite database. No external input crosses any trust boundary. | N/A |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-23-01 | Information Disclosure | build_cbom Pass 2 | accept | Hollow cert components were a data quality bug, not a security issue. They contained no secrets (`subject_name=None`, `issuer_name=None`). Fix in `de32d01` eliminates them for correctness. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-23-01 | T-23-01 | Hollow `CertificateProperties` components contained no secrets and were a data quality issue, not a security vulnerability. No ASVS L1 controls applicable — phase modifies an internal data transform producing CycloneDX output from already-validated scan results. | gsd-secure-phase | 2026-04-24 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-24 | 1 | 1 | 0 | gsd-secure-phase |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-24
