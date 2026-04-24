# Phase 25: Identity Findings Accuracy — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 25-identity-findings-accuracy
**Areas discussed:** RS-family detection, TLS-bleed guard scope, ldap3 version pin, NEW-ISSUE-3 scope

---

## RS-family detection

| Option | Description | Selected |
|--------|-------------|----------|
| OIDC_ALG_SEVERITY lookup only | Import from saml_scanner, check alg in OIDC_ALG_SEVERITY — single source of truth; RS256→HIGH, ES256→None (skipped); no service_detail check | ✓ |
| service_detail + severity lookup | Check both "oidc-discovery" in service_detail AND alg in OIDC_ALG_SEVERITY — more explicit, but brittle to service_detail format changes | |
| alg.startswith(RS/PS) check | Check alg prefix — avoids import but duplicates logic already in severity table | |

**User's choice:** OIDC_ALG_SEVERITY lookup only
**Notes:** The severity table is the single source of truth — same table the scanner uses to decide whether to emit an endpoint. SHA1 is not in that table, so it naturally falls through to the existing handler. No service_detail coupling.

---

## TLS-bleed guard scope

*(User asked for clarification before answering — explained that _derive_findings() runs for all endpoints including SAML/OIDC, and the quantum-vulnerable algorithm block (line 150) fires on RS256 since "RS256" doesn't start with "RSA", producing a source="tls" FindingItem.)*

| Option | Description | Selected |
|--------|-------------|----------|
| Broad: skip KERBEROS/SAML/DNSSEC | One continue guard at top of _derive_findings() loop; all TLS checks skipped for identity endpoints | ✓ |
| Narrow: guard only quantum-vuln block | Only add skip inside the quantum-vulnerable algorithm block | |

**User's choice:** Broad guard
**Notes:** None of the TLS checks are meaningful for identity endpoints anyway. Broad guard future-proofs against new check additions.

---

## ldap3 version pin

| Option | Description | Selected |
|--------|-------------|----------|
| ldap3>=2.9.1 (REQUIREMENTS.md) | Matches KERB-03 as written; more permissive; pip resolves to latest | ✓ |
| ldap3>=3.4 (roadmap success criteria) | Pins to newer major version; matches roadmap wording | |

**User's choice:** ldap3>=2.9.1
**Notes:** REQUIREMENTS.md is the source for the version string; more permissive constraint avoids locking to a specific major unnecessarily.

---

## NEW-ISSUE-3 scope

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — fold it in | Doc-only update; same identity domain; closes the deferred carry-over | ✓ |
| No — keep deferred | Keep phase tightly scoped to the two code bug fixes in success criteria | |

**User's choice:** Fold in
**Notes:** No code change required — only expected_results_v3.md. Closes the STATE.md carry-over cleanly.

---

## Claude's Discretion

- Exact wording of RS-family IdentityFinding title/description/remediation — follow existing style in _derive_identity_findings()
- Whether IDENTITY_PROTOCOLS set is module-level constant or inline — either acceptable
