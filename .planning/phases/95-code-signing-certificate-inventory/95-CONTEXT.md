# Phase 95: Code-Signing Certificate Inventory - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Inventory code-signing certificates from two passive sources and surface weak-algorithm
findings, with fingerprint-based CBOM de-duplication:
1. **LDAP `userCertificate`** entries that carry the CodeSigning EKU (1.3.6.1.5.5.7.3.3).
2. **Already-captured TLS certificates** checked in-process for the CodeSigning EKU
   (no new network fetch).

Scope is LOCKED to Option A (v5.1-D-07): LDAP `userCertificate` + TLS EKU check only.
Sigstore / npm / Authenticode are explicitly deferred to v5.2.

Advances SCORE_WEIGHTS +6.0 → 299.0 via the existing `agility_signals` subscore
(no 7th pillar). Adds chaos-lab validation coverage (LAB-01, partial).

Requirements: CSIGN-01, CSIGN-02, CSIGN-03, SCORE-01 (partial), LAB-01 (partial).
</domain>

<decisions>
## Implementation Decisions

### Discovery & invocation
- `--inventory-code-signing` CLI flag gates the whole feature (opt-in).
- LDAP source reuses `quirk/scanner/smime_scanner.py`'s LDAP `userCertificate` connection
  pattern, filtered to certs carrying the CodeSigning EKU.
- TLS-EKU source checks **already-captured** TLS certs in-process for the CodeSigning EKU
  (1.3.6.1.5.5.7.3.3) — no new network fetch.
- New module `quirk/scanner/codesign_scanner.py`, reusing smime LDAP helpers and
  `adcs_scanner.py` EKU-parsing helpers.

### Findings & weak-algorithm (CSIGN-02)
- Finding category: `CODE-SIGN/weak-algorithm`.
- Weak thresholds → HIGH severity: RSA < 2048 bits, EC < 256 bits, SHA-1 signature hash.
  Reuse `quirk/util/weak_crypto.py` rather than new threshold logic.
- CryptoEndpoint protocol label: `CODE_SIGNING` (UPPERCASE — per the Phase 94 casing
  lesson, all CBOM/evidence/resume consumers key on uppercase protocol values).

### CBOM de-duplication (CSIGN-03)
- Dedup key: SHA-256 certificate fingerprint, deduped against existing TLS-derived
  CBOM components.
- Precedence: the TLS-derived component WINS; code-signing adds an EKU/usage annotation
  to the existing component rather than emitting a duplicate.
- Automated test asserts a stable CBOM component count when the same cert is seen via
  both TLS capture and code-signing inventory.

### Chaos lab (LAB-01) + scoring
- Reuse the existing `ldaps` chaos-lab profile — add a code-signing cert fixture
  (`userCertificate` with CodeSigning EKU). No new profile.
- Per CLAUDE.md: update `expected_results_*.md` oracle + `quantum-chaos-enterprise-lab/lab.sh`
  + chaos-lab README in the SAME change as any lab modification.
- Scoring: code-signing signal feeds `agility_signals`; SCORE_WEIGHTS +6.0 → 299.0.
  BOTH the sum AND the count invariant in `tests/test_score_weights_invariant.py` must
  update together (Phase 94 lesson: 293.0/39 → 299.0/4N).

### Claude's Discretion
- Exact evidence counter key name(s) for the code-signing agility signal, the precise
  agility weight split, helper structure, and report layout are at Claude's discretion,
  following codebase conventions.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/scanner/smime_scanner.py` — LDAP `userCertificate` discovery pattern (v4.10 S/MIME).
- `quirk/scanner/adcs_scanner.py` — EKU / extended-key-usage parsing (ldap3, no impacket).
- `quirk/util/weak_crypto.py` — weak-algorithm classification (SHA-1 family, cipher/version helpers).
- `quirk/cbom/builder.py` / `quirk/cbom/classifier.py` — CBOM component construction +
  fingerprint handling; the BEARER_TOKEN branch (Phase 94) is the most recent protocol-add analog.
- `quirk/intelligence/evidence.py` / `scoring.py` — `_PROTOCOL_KEYS`, agility counters,
  SCORE_WEIGHTS (currently 293.0 / 39 entries after Phase 94).
- Existing `ldaps` chaos-lab profile in `quantum-chaos-enterprise-lab/docker-compose.yml`.

### Established Patterns
- Scanner enable flags live in `ConnectorsCfg` (quirk/config.py); CLI flags wired in run_scan.py.
- Protocol values are UPPERCASE (JWT, SSH, BEARER_TOKEN, OPENAPI) — consumers key on exact match.
- New CBOM protocol branch: add to builder.py Pass-1 elif chain + Pass-3 skip tuples +
  evidence.py `_PROTOCOL_KEYS`.
- SCORE_WEIGHTS invariant test pins BOTH sum and count — bump both.

### Integration Points
- run_scan.py — `--inventory-code-signing` flag + a code-signing scan phase feeding `endpoints`.
- CBOM dedup — fingerprint reconciliation against TLS-derived components.
- Chaos lab — `ldaps` profile fixture + `lab.sh` ALL_PROFILES (already includes ldaps) +
  `expected_results_*.md` + README.
</code_context>

<specifics>
## Specific Ideas

- De-dup must be proven by an automated test asserting a STABLE component count (not just
  "no obvious duplicate") — the success criterion is explicit about this.
- Reuse the SHA-256 fingerprint already computed for TLS certs; do not invent a second
  fingerprinting path.
- EKU OID for code signing is 1.3.6.1.5.5.7.3.3.
</specifics>

<deferred>
## Deferred Ideas

- Sigstore / npm / Authenticode code-signing verification → v5.2 (v5.1-D-07).
- Active fetching of certs solely for EKU inspection → out of scope (passive: reuse captures).
- A dedicated `codesign` chaos-lab profile → not now; reuse `ldaps`.
</deferred>
