---
phase: 46-tls-finding-gaps
type: discussion-log
status: complete
source: /gsd-discuss-phase 46
updated: 2026-05-03
---

# Phase 46 — Discussion Log

> Human-readable audit of the discussion. Not consumed by downstream agents
> (researcher / planner / executor read CONTEXT.md instead).

## Setup

**Phase goal (from ROADMAP.md):** Users receive actionable security findings for
expired certificates, self-signed certificates, untrusted-CA certificates, and weak
RSA/EC keys — certificate defects that previously produced zero findings.

**Requirements:** TLS-FIND-01..07 (7 requirements).

**Pre-discussion codebase scan revealed:**
- Risk engine `quirk/engine/risk_engine.py:343–423` already implements all five
  finding branches; phase is mostly a wiring problem, not greenfield.
- `chain_verified` is computed at `tls_scanner.py:208` but never assigned to the
  `CryptoEndpoint` returned by the scanner — so `risk_engine.py:375`'s `cv is False`
  check is structurally dead today.
- Chaos lab already has `tls-expired` (port 9443) and `tls-selfsigned` (port 10443)
  profiles. TLS-FIND-07 calls for a NEW `tls-cert-defects` profile — design choice
  about whether to combine, replace, or add alongside.

## Gray areas presented

User selected all four:
- Cert metadata flow fix
- Combined defects
- tls-cert-defects design
- Untrusted-CA detection

## Discussion

### Area 1 — Cert metadata flow fix (TLS-FIND-06)

**Question:** Which fallback strategy when sslyze CERTIFICATE_INFO returns ERROR?

**Options presented:**
1. Result-validation gate (Recommended) — re-run via basic-ssl when `cert_not_after`
   is None or `cert_subject` is empty; both paths set `ep.chain_verified` explicitly.
2. Try/except + return-None fallback — smallest diff, but relies on exception/None
   signaling rather than explicit field validation.
3. Always run both, merge — most robust but doubles network cost.

**User chose:** Result-validation gate.

**Recorded as D-01.** Both paths populate `ep.chain_verified`. No silent
partial-population. No double-scan in the happy path.

### Area 2 — Combined defects on one cert

**Question:** When one cert has multiple defects (e.g., expired + self-signed +
RSA-1024), how should findings render?

**Options presented:**
1. All defects, separate findings (Recommended) — 1:1 mapping to TLS-FIND-01..05.
2. Worst severity only — less noise but loses information.
3. Single "cert defects" rollup finding — cleaner UI but new finding shape.

**User chose:** Separate findings per defect class.

**Recorded as D-02.** Risk-engine branches stay orthogonal. Each branch inspects
the same `ep` and emits independently.

### Area 3 — `tls-cert-defects` chaos lab profile design (TLS-FIND-07)

**Question:** How to design the new chaos lab profile, given existing `tls-expired`
and `tls-selfsigned` already exist?

**Options presented:**
1. New combined profile, 4 endpoints, new ports (Recommended) — single profile,
   ports 13443–13446, existing profiles stay unchanged.
2. Meta-profile pulling existing + new — Compose profile-of-profiles pattern not
   currently used in the lab.
3. Replace existing profiles — simpler long-term but breaks doc references.

**User chose:** New combined profile, 4 endpoints, dedicated ports.

**Recorded as D-03.** Proposed services: tls-cert-expired (13443),
tls-cert-selfsigned (13444), tls-cert-untrusted-ca (13445), tls-cert-rsa1024
(13446). Final port allocation confirmed in PLAN.md.

### Area 4 — Self-signed vs untrusted-CA exclusivity

**Question:** A self-signed cert is technically also an untrusted CA (chain
verification fails). Should they emit overlapping findings?

**Options presented:**
1. Mutually exclusive (Recommended) — self-signed branch fires only when
   `issuer==subject`; untrusted-CA branch fires only when `issuer!=subject AND
   chain_verified is False`. At most one finding per cert.
2. Both fire independently — most paranoid but creates redundant noise.
3. Severity-floor only — single finding with conditional severity; arguably violates
   TLS-FIND-02/03 which are written as distinct findings.

**User chose:** Mutually exclusive.

**Recorded as D-04.** The existing risk_engine branch at line 375 is currently a
single OR-branch (`(issuer==subject) or cv is False`); plan must split it into two
distinct branches with explicit exclusivity.

## Deferred ideas (captured, not acted on)

- Severity calibration profile for cert defects — lenient could downgrade self-signed
  to MEDIUM in dev. Future scoring-profile phase.
- Hostname mismatch as a separate cert finding type. Backlog.
- Auto-remediation hints with platform-specific commands. Future docs/UX phase.

## Outcome

CONTEXT.md written to `.planning/phases/46-tls-finding-gaps/46-CONTEXT.md` with
4 locked decisions (D-01..D-04), 10 canonical refs, and explicit boundaries.

Ready for `/gsd-plan-phase 46`.
