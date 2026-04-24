# Phase 25: Identity Findings Accuracy — Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 25 delivers two surgical bug fixes carried over from the v4.2 audit (2026-04-24). No new
scanners, no new schema columns, no new API routes.

**Fix 1 — NEW-ISSUE-1:** OIDC RS256/RS384/RS512 endpoints are missing from the RS-family branch
in `_derive_identity_findings()`. They fall through the SAML branch silently, then get caught by
the quantum-vulnerable block in `_derive_findings()`, producing a `FindingItem(source="tls")`.
Result: RS256 endpoints appear in the Findings tab as TLS-sourced instead of the Identity tab.

**Fix 2 — ISSUE-2:** `ldap3` is absent from `[identity]` extras in `pyproject.toml`. The
Kerberos scanner's LDAP enumeration path always degrades gracefully (no exception), so the
missing dep is silent — but KERB-03 is inert until ldap3 is installable.

**Also in scope (NEW-ISSUE-3):** Update `quantum-chaos-enterprise-lab/expected_results_v3.md`
with identity chaos lab entries for DNSSEC, SAML/OIDC, and Kerberos profiles. Doc-only, no
code change. Closes the deferred carry-over from STATE.md.

</domain>

<decisions>
## Implementation Decisions

### RS-family detection in `_derive_identity_findings()`

- **D-01:** Import `OIDC_ALG_SEVERITY` from `quirk.scanner.saml_scanner` into
  `quirk/dashboard/api/routes/scan.py`. Use it as the single detection signal for OIDC
  RS-family endpoints inside the SAML branch of `_derive_identity_findings()`.
  - Detection: `severity = OIDC_ALG_SEVERITY.get(alg)` — if non-None, emit
    `IdentityFinding(source="saml")` using that severity.
  - This check runs FIRST inside the SAML branch, before the existing SHA-1 and
    weak-RSA-key-size checks. SHA-1 (`"SHA1"`) is not in `OIDC_ALG_SEVERITY`, so it
    naturally falls through to the existing handler. No service_detail check required.

- **D-02:** `IdentityFinding` for RS-family OIDC must use:
  - `source="saml"` (per SAML-04 requirement — OIDC lives under the SAML/OIDC scanner)
  - `severity` from `OIDC_ALG_SEVERITY.get(alg)` (RS256/RS384/RS512 → `"HIGH"`)
  - `algorithm=alg` (the raw alg string, e.g., `"RS256"`)
  - `protocol="SAML"` (per existing IdentityFinding protocol field usage)

### TLS-bleed guard in `_derive_findings()`

- **D-03:** Add a broad protocol guard at the top of the `_derive_findings()` loop body:
  ```python
  proto = (ep.protocol or "").upper()
  if proto in {"KERBEROS", "SAML", "DNSSEC"}:
      continue  # handled exclusively by _derive_identity_findings()
  ```
  This prevents all identity protocol endpoints from generating any `source="tls"`
  `FindingItem` — not just the quantum-vulnerable block. Rationale: none of the TLS
  checks (tls_version, cert_not_after, tls_weak_ciphers_present, HTTP plaintext) are
  populated on identity endpoints; only the quantum-vulnerable alg block fires today.
  Broad guard future-proofs against any new TLS check additions.

### ldap3 dependency

- **D-04:** Add `"ldap3>=2.9.1"` to the `[identity]` extras group in `pyproject.toml`.
  Version follows REQUIREMENTS.md KERB-03 (`>=2.9.1`). pip resolves to the latest
  compatible version. No upper-bound pin needed (no known conflict risk with impacket).

### NEW-ISSUE-3 documentation scope

- **D-05:** Update `quantum-chaos-enterprise-lab/expected_results_v3.md` with identity
  chaos lab expected results for the three v4.2 profiles:
  - DNSSEC chaos lab (bind9 profile) — 4 zones with expected classification outcomes
  - SAML/OIDC chaos lab (simpla-samlphp profile) — RSA-1024 signing cert expected results
  - Kerberos chaos lab (samba-dc profile) — RC4 etype expected results
  Doc-only change. No code, no test changes required for this item.

### Claude's Discretion

- Exact title/description/remediation wording in the new `IdentityFinding` for RS-family
  OIDC endpoints — follow the existing KERBEROS and DNSSEC finding text style in
  `_derive_identity_findings()`.
- Whether to extract `{"KERBEROS", "SAML", "DNSSEC"}` as a module-level constant or
  keep it inline in `_derive_findings()` — either is fine.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core files being modified
- `quirk/dashboard/api/routes/scan.py` — Contains both `_derive_findings()` and
  `_derive_identity_findings()`; both functions need changes (D-01 through D-03)
- `quirk/scanner/saml_scanner.py` — Source of `OIDC_ALG_SEVERITY` dict (D-01); read to
  understand the alg → severity mapping and how OIDC endpoints are stored (protocol="SAML",
  service_detail="oidc-discovery|...")
- `pyproject.toml` — `[identity]` extras group currently has only impacket; D-04 adds ldap3

### Documentation
- `quantum-chaos-enterprise-lab/expected_results_v3.md` — Target file for NEW-ISSUE-3
  identity chaos lab entries (D-05)

### Requirements
- `.planning/REQUIREMENTS.md` §Phase 25 Carry-Over — SAML-04, IDENT-02, IDENT-03,
  KERB-03, INFRA-03; these are the acceptance criteria for the two bug fixes

### Prior phase context
- `.planning/phases/21-identity-surface/21-CONTEXT.md` — D-06 and D-07 from Phase 21
  define the `_derive_identity_findings()` contract and the "derive once, expose twice"
  pattern; this phase extends D-06's SAML branch

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OIDC_ALG_SEVERITY` in `quirk/scanner/saml_scanner.py:44` — module-level dict mapping
  OIDC alg strings to severity strings or None. Already the authority for which OIDC algs
  produce findings at scan time; importing it into `routes/scan.py` for derivation keeps
  the two functions in sync automatically.
- `IdentityFinding` schema in `quirk/dashboard/api/schemas.py:79` — existing Pydantic model
  with `source`, `algorithm`, `protocol`, `severity`, `quantum_risk` fields; no changes needed.

### Established Patterns
- **SAML branch ordering:** The existing SAML branch in `_derive_identity_findings()` checks
  `alg == "SHA1"` then `size < 2048`. The new RS-family check runs first (highest specificity),
  with SHA-1 and weak-key checks as fallthrough cases.
- **Identity protocol skipping:** The `_derive_findings()` broad guard pattern mirrors how
  `_derive_identity_findings()` itself uses `proto in {"KERBEROS","SAML","DNSSEC"}` to
  route — consistent language.
- **TDD is the established phase pattern** — RED test scaffold plan first, then GREEN
  implementation plan. Phase 25 will follow the same two-plan structure as Phases 22–24.

### Integration Points
- `_derive_findings()` and `_derive_identity_findings()` are both called in the
  `GET /api/scan/latest` handler at `scan.py:502`. No route changes needed — only the
  two helper functions are modified.
- The D-07 "expose twice" pattern (identity_findings + FindingItem conversion) is already
  wired; Phase 25 additions will flow through it automatically once `_derive_identity_findings()`
  returns the RS-family `IdentityFinding`.

</code_context>

<specifics>
## Specific Ideas

- The broad guard in `_derive_findings()` should be added as the very first statement in
  the `for ep in endpoints:` loop body — before the HTTP, TLS version, cipher, and cert
  checks — so it's visually obvious and not buried.
- For the RS-family `IdentityFinding`, use language consistent with the DNSSEC and
  Kerberos finding descriptions: state the algorithm, state why it's a risk
  (RSA is quantum-vulnerable), and give an actionable remediation (migrate to ECDSA/EdDSA).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 25-identity-findings-accuracy*
*Context gathered: 2026-04-24*
