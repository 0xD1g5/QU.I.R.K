# Phase 90: OQS-nginx PQC-Hybrid - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 90-oqs-nginx-pqc-hybrid
**Areas discussed:** Phase 91 disposition, PQC-02 detection strategy (empirical spike), agility bonus shape, image/port/group specifics, demo/oracle framing, advisory scoping

---

## Phase 91 disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Keep as-is | 91-CONTEXT.md already complete (CLEAN-01..04, Ready for planning) from the earlier parallel run | ✓ |
| Revise it | Re-open Phase 91 discussion before planning | |

**User's choice:** Keep as-is.
**Notes:** This session focuses solely on Phase 90; Phase 91 goes straight to `/gsd-plan-phase 91` when ready.

---

## PQC-02 — Detection strategy (pre-locked empirical decision)

| Option | Description | Selected |
|--------|-------------|----------|
| Run the live spike first | Pin a digest, bring up the endpoint, observe what sslyze + a raw probe actually report, then decide | ✓ |
| Decide by reasoning now | Lock the strategy from research notes without live observation | |

**User's choice:** Run the live spike first.
**Notes:** Spike executed against the pinned digest. Findings: sslyze/nassl → `ERROR_NO_CONNECTIVITY` (bundled OpenSSL too old); host OpenSSL 3.6.2 `s_client -groups X25519MLKEM768` → negotiates `X25519MLKEM768` (NamedGroup 4588) with an `mldsa65` peer cert; hybrid-only probe FAILS against a classical server (clean discriminator); Python stdlib `ssl.set_ecdh_curve` rejects the group name. → Decision: genuine raw `openssl s_client` probe, capability-gated, with advisory fallback (D-01). Not sslyze-based.

---

## Remaining gray areas (agility bonus / image-port-group / demo-oracle / advisory scoping)

| Option | Description | Selected |
|--------|-------------|----------|
| Discuss selected subset | User picks which to lock | |
| Move forward with recommended actions | Claude proceeds with grounded recommendations on all | ✓ |

**User's choice:** "please move forward with recommended actions."
**Notes:** All remaining areas resolved with spike-grounded recommendations — D-02 (pin digest `sha256:6ca18ac6…`, target standardized `X25519MLKEM768`, classifier alias to existing `mlkem768x25519-sha256`), D-03 (new `pqc_hybrid_endpoint_count` + agility bonus ≈ +8, clamped at 25, update invariant test sum 275→ and count 36→37), D-04 (oqs-nginx oracle section + demoable agility uplift, CLAUDE.md lab-sync), D-05 (counter increments under both genuine + advisory surfaces).

---

## Claude's Discretion

- Exact lab port (collision-checked; candidate 25443 or a 39xxx-range port).
- Capability-probe mechanism for "OpenSSL ≥3.5".
- Exact agility bonus value within the D-03 guidance.
- Whether to pin `ssl_ecdh_curve` explicitly in nginx.conf.
- Where the raw-probe helper lives (kept out of the sslyze flow per D-01).

## Deferred Ideas

- PQC certificate-signature (ML-DSA-65 / Dilithium) scoring — separate signal, future phase.
- Native OQS-compiled sslyze/nassl detection — documented non-goal, v5.1.
- Additional hybrid groups (MLKEM1024, P-384 hybrids) — future breadth work.
