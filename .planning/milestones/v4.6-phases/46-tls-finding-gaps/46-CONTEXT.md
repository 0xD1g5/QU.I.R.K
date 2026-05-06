---
phase: 46-tls-finding-gaps
type: context
status: active
source: /gsd-discuss-phase 46
updated: 2026-05-03
milestone: v4.6 Enterprise Readiness
requirements: [TLS-FIND-01, TLS-FIND-02, TLS-FIND-03, TLS-FIND-04, TLS-FIND-05, TLS-FIND-06, TLS-FIND-07]
---

# Phase 46 — TLS Finding Gaps — Context

## Domain

Wire actionable security findings into the report for cert-level defects (expired,
self-signed, untrusted-CA) and weak public keys (RSA<2048, EC<256). Add a chaos lab
profile that exercises all four defect classes end-to-end.

**Key insight:** This phase is largely a **wiring problem, not greenfield**. The risk
engine (`quirk/engine/risk_engine.py:343–423`) already implements all five finding
branches today. Findings don't fire because:
1. `chain_verified` is computed locally inside `tls_scanner.py:208` but never assigned
   to the `CryptoEndpoint` instance returned to the engine — so the untrusted-CA
   branch (`cv is False`) is structurally dead.
2. When sslyze `CERTIFICATE_INFO` returns ERROR, the basic-ssl fallback path
   (`tls_scanner.py:348+`) populates `cert_subject` / `cert_issuer` / `cert_pubkey_size`
   / `cert_not_after` but does NOT compute `chain_verified` either — a half-populated
   `CryptoEndpoint` reaches the database, missing the chain attribute the engine needs.
3. There is no chaos lab profile that exercises self-signed / untrusted-CA / RSA-1024
   in one place, so the test loop is broken — historical evidence of "no findings"
   has been ambiguous (genuine bug vs. wrong test target).

## Canonical Refs

> **MANDATORY for downstream agents.** Every researcher and planner MUST read these
> before producing RESEARCH.md or PLAN.md. Paths are repo-relative.

### Roadmap & requirements
- `.planning/ROADMAP.md` — Phase 46 entry (lines 901+)
- `.planning/REQUIREMENTS.md` — TLS-FIND-01..07 (lines 13–19, traceability 105–112)
- `CLAUDE.md` — "Chaos Lab Maintenance" rule (lab.sh + README + expected_results sync)

### Code under modification
- `quirk/scanner/tls_scanner.py` — primary scanner; sslyze path lines 130–220, basic-ssl
  fallback ~line 348+. **Critical:** line 208 computes `chain_verified` but never assigns
  it to `ep`. Fallback path doesn't compute it at all.
- `quirk/discovery/tls_scanner.py` — simpler discovery-time TLS probe; populates
  `cert_pubkey_size` and `cert_not_after` but no chain check.
- `quirk/engine/risk_engine.py:343–423` — existing finding logic for all five classes:
  - lines 343–366: cert expired (CRITICAL)
  - lines 372–389: self-signed / untrusted-CA combined branch (will be split per D-04)
  - lines 391–398: RSA < 2048 (HIGH)
  - lines 416–423: EC < 256 (HIGH)
- `quirk/models.py` — `CryptoEndpoint` definition; check whether `chain_verified` is
  already a declared field (if not, add it; otherwise wire to existing field).

### Chaos lab artifacts
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing TLS profiles:
  `tls-modern` (443), `tls-legacy` (8443), `tls-expired` (9443), `tls-selfsigned` (10443),
  `tls-mtls-required` (11443). New `tls-cert-defects` profile lands here.
- `quantum-chaos-enterprise-lab/lab.sh` — `ALL_PROFILES` list must gain the new profile.
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — oracle file; gains a section
  documenting expected findings for each `tls-cert-defects` endpoint.
- `quantum-chaos-enterprise-lab/README.md` — profile docs.
- `quantum-chaos-enterprise-lab/certs/` — existing CA + cert generators; we will need
  new `untrusted-ca` (cert signed by an off-trust-store CA) and `rsa1024` cert variants.

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONVENTIONS.md`

## Decisions

### D-01 — sslyze fallback: result-validation gate
**Decision:** After sslyze runs, validate `ep.cert_not_after is None OR ep.cert_subject is empty`.
If the gate trips, re-run via the basic-ssl fallback path and merge results. Both paths
**must** assign `ep.chain_verified` explicitly.

- sslyze path (success): `ep.chain_verified = (deployment.verified_certificate_chain is not None)`
- basic-ssl fallback: separate validating context with `ctx.verify_mode = ssl.CERT_REQUIRED`
  and `ctx.check_hostname = True` against the system trust store; on `SSLCertVerificationError`,
  set `ep.chain_verified = False` while still extracting cert metadata via a second
  `verify_mode = ssl.CERT_NONE` pass.

**Why:** Explicit field validation > exception/None signaling. No silent partial-population.
No double-scan in the happy path. Closes TLS-FIND-06 directly.

**How to apply:** Researcher should examine the existing fallback structure at
`tls_scanner.py:348+` and identify the smallest delta to add the validation gate +
`chain_verified` plumbing. Planner should split this into one plan task per layer
(scanner fix → CryptoEndpoint field → engine consumption).

### D-02 — Combined defects: separate findings per class
**Decision:** A cert with multiple defects (e.g., expired + self-signed + RSA-1024)
emits one finding **per defect class**, not a rollup or worst-severity-only.

**Why:** 1:1 mapping to TLS-FIND-01..05 keeps verification and traceability clean.
Risk-engine branches stay orthogonal. Aligns with how Phase 41 handles multi-issue
endpoints. An operator fixing the expired cert sees they ALSO need to swap to RSA-2048.

**How to apply:** Each of the five risk_engine branches at lines 343–423 must be
independent (no early-return / no else-if chains across classes). All five branches
inspect the same `ep` and emit findings independently.

### D-03 — Chaos lab: new combined profile, dedicated ports
**Decision:** Create a single new profile `tls-cert-defects` with **4 nginx services**
on dedicated ports. Existing `tls-expired` and `tls-selfsigned` profiles **stay
unchanged** for back-compat with prior expected_results docs.

**Proposed services (final ports decided in PLAN.md):**
- `tls-cert-expired` — port `13443` — uses existing expired cert fixtures
- `tls-cert-selfsigned` — port `13444` — uses existing self-signed fixtures
- `tls-cert-untrusted-ca` — port `13445` — NEW: cert signed by an off-trust-store CA
- `tls-cert-rsa1024` — port `13446` — NEW: cert with RSA-1024 key

**Why:** Single new profile = one new section in `expected_results_v4.md`, one new
entry in `lab.sh ALL_PROFILES`, no Compose profile-of-profiles pattern (which the lab
doesn't currently use). Keeping old profiles unchanged means no doc rewrites for
historical UAT runs.

**How to apply:** Planner allocates one plan task to chaos lab additions; researcher
verifies port availability and confirms the existing cert generation scripts can be
extended to produce the two new variants.

### D-04 — Self-signed vs untrusted-CA: mutually exclusive
**Decision:** The two cert-trust findings have mutually exclusive trigger conditions.

| Finding | Severity | Trigger |
|---|---|---|
| Self-signed (TLS-FIND-02) | HIGH | `cert_issuer == cert_subject` |
| Untrusted-CA (TLS-FIND-03) | MEDIUM | `cert_issuer != cert_subject AND chain_verified is False` |

A given cert produces at most ONE of these two findings. (Combined with D-02, a
self-signed cert that is also expired and uses RSA-1024 produces 3 findings:
CRITICAL expired + HIGH self-signed + HIGH RSA-1024 — but never an additional
MEDIUM untrusted-CA.)

**Why:** Matches the literal wording of TLS-FIND-02 vs TLS-FIND-03. Self-signed is a
stricter subset of "chain didn't verify" — surfacing both is redundant noise. The
existing risk_engine branch at line 375 (`(issuer==subject) or cv is False`) is a
single OR-branch; this decision splits it into two mutually exclusive branches.

**How to apply:** Planner targets `risk_engine.py:372-389` for refactor — split into
two distinct branches with explicit `if issuer==subject: ... elif issuer!=subject and cv is False: ...`
structure. Test fixtures must include one cert per branch to verify exclusivity.

## Code Context

### Reusable assets
- **risk_engine.py:343–423** already implements all five finding bodies (titles,
  descriptions, severity, recommendations). Reuse verbatim — only the trigger
  conditions need adjustment (D-02 split + D-04 exclusivity).
- **tls_scanner.py:130–220** sslyze CERTIFICATE_INFO populator works correctly when
  sslyze succeeds — only `chain_verified` plumbing missing.
- **chaos lab cert fixtures** (`quantum-chaos-enterprise-lab/certs/`) — existing
  expired and self-signed fixtures can be reused at the new ports without regeneration.

### New code surface
- `CryptoEndpoint.chain_verified: Optional[bool]` field (if not present in models.py).
- Two new cert variants in `quantum-chaos-enterprise-lab/certs/`: untrusted-CA + RSA-1024.
- Two new nginx confs in `quantum-chaos-enterprise-lab/nginx/`: cert-untrusted-ca + cert-rsa1024.
- `tls-cert-defects` profile entries in docker-compose.yml + lab.sh.
- Section in `expected_results_v4.md` listing the four endpoints + expected findings.

### Carrying forward from prior phases
- Phase 45 D-07: severity counts and intelligence-score evidence already filter
  `category=='coverage_gap'`. New findings here have `category=None`, so they count
  normally — no D-07 interaction.
- CLAUDE.md "Chaos Lab Maintenance": every chaos lab change must update lab.sh
  ALL_PROFILES + README.md + expected_results_v4.md in the same change. Plan must
  enforce this gate.

## Boundaries (Out of Scope)

- **Cipher-suite findings** — covered by `tls_supported_versions` / `tls_weak_ciphers_present`
  fields and existing risk_engine logic. Not part of Phase 46.
- **Hostname mismatch findings** — distinct from chain verification; deferred to backlog.
- **OCSP/CRL revocation checks** — out of scope (large-surface project of its own).
- **Rich finding context (BACK-79)** — separate roadmap item already tracked.
- **EC curve weakness beyond key size** (e.g., disallowing brainpool, secp192r1 specifically)
  — TLS-FIND-05 is bit-size only; deeper curve analysis is future work.

## Deferred Ideas

- **Severity calibration profile for cert defects** — could lenient profile downgrade
  self-signed to MEDIUM in dev environments? Punt to a future scoring-profile phase.
- **Hostname mismatch as a separate cert finding type** — captured for the backlog.
- **Auto-remediation hints with platform-specific commands** (nginx vs. apache vs. AWS
  ACM) — could enrich the recommendation field in a future docs/UX phase.

## Next Steps

`/clear` then:

`/gsd-plan-phase 46`

Or `/gsd-plan-phase 46 --skip-research` if you want to skip the research step.
