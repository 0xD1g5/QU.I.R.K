# Requirements — QU.I.R.K. v5.1 Authenticated Scanning + API Surface Depth

**Milestone:** v5.1
**Goal:** Add an optional, ephemeral credential model that unlocks deeper crypto findings across the API surface — without QU.I.R.K. ever becoming a secret store.
**Selected from:** HORIZON Candidate A (Authenticated Scanning + API Surface Depth).
**Research:** `.planning/research/SUMMARY.md` (HIGH confidence; 4-agent sweep 2026-05-22).
**Last updated:** 2026-05-22

---

## Scope Decisions (locked at milestone open)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Credential storage | **Ephemeral / in-memory only** | Lowest blast radius; QU.I.R.K. never a stored-secret surface. Consequence: no authenticated *scheduled* scans. |
| Auth schemes | **Bearer/OAuth2, API key (header/query), HTTP Basic** | The three common HTTP auth shapes. mTLS client certs deferred. |
| Code-signing scope | **LDAP `userCertificate` + TLS EKU check only** | Zero new deps, offline-safe, reuses existing cert pipelines. Sigstore/npm/Authenticode → v5.2. |
| Scoring | **Fold into existing `agility_signals` subscore** | No 7th pillar; preserves the v4.10.1 `÷1.5` rollup denominator and all report/dashboard renderers. |
| Alg-confusion probe | **In-scope, dedicated `--fuzz-jwt-alg-confusion` sub-flag** | Detects a real CVE-class JWT vuln; sub-flag prevents unintended firing. |
| OpenAPI input | **Local file + scoped URL fetch** | Air-gapped-safe default; URL fetch only when URL ∈ scan targets. `$ref` SSRF restriction required regardless. |

---

## v5.1 Requirements

### Authenticated Scanning — Credential Model (BACK-64)

- [x] **AUTH-01**: User can supply Bearer/OAuth2 token, API key (header or query), or HTTP Basic credentials for an authenticated scan via CLI flag, env var, or interactive prompt.
- [x] **AUTH-02**: Credentials are never persisted — absent from SQLite, CBOM output, logs, error messages, and dashboard API responses (ephemeral / in-memory only).
- [x] **AUTH-03**: Scheduled scans reject authenticated-mode configs with a clear error code, since credentials cannot be persisted for later runs.
- [x] **AUTH-04**: A security-review gate deliverable audits every credential-leakage surface and documents the best-effort (not provable) nature of in-memory zeroization in Python.
- [x] **AUTH-05**: Credential scrubbing (`safe_str()` + AST CI gate) is extended to API-key / token field shapes so leaks cannot regress silently.

### OpenAPI / Swagger Spec Analysis (BACK-10)

- [ ] **SPEC-01**: User can analyze an OpenAPI/Swagger spec from a local file to inventory declared API crypto posture (security schemes, plaintext `servers`, unauthenticated endpoints).
- [ ] **SPEC-02**: User can analyze a spec fetched from a URL, but only when that URL is within the configured scan-target scope.
- [ ] **SPEC-03**: Spec parsing is hardened against `$ref` SSRF (local-only ref resolution) and oversized-spec DoS (size gate before parse).

### Bearer Token Analysis (BACK-11)

- [ ] **TOKEN-01**: User can decode and classify a bearer/JWT token (algorithm, key size, expiry, quantum-safety) via a standalone `--analyze-token` command.
- [ ] **TOKEN-02**: Bearer tokens captured during an authenticated scan are classified into the CBOM with a `declared_algorithm (unverified)` label — never treated as enforced.
- [ ] **TOKEN-03**: `alg:none` tokens (any case variant) are flagged CRITICAL.

### Active REST Fuzzing (BACK-09)

- [ ] **FUZZ-01**: User can run opt-in active REST crypto-posture fuzzing (TLS downgrade, cipher acceptance, HSTS, HTTP-only credential transmission), gated behind an explicit flag + authorization confirmation + bounded request budget.
- [ ] **FUZZ-02**: Fuzzing enforces six safety guardrails: GET-only default, hard budget ceiling, rate cap, `CONFIRM` prompt, target-scope enforcement, and 5xx-cascade pause.
- [ ] **FUZZ-03**: Fuzzing hard-aborts in non-interactive (non-TTY) contexts — it never runs headless.
- [ ] **FUZZ-04**: User can enable a JWT alg-confusion probe (RS256→HS256) behind a dedicated `--fuzz-jwt-alg-confusion` sub-flag.

### Code-Signing Certificate Inventory (BACK-24)

- [ ] **CSIGN-01**: User can inventory code-signing certificates discovered via LDAP `userCertificate` and EKU checks on already-captured TLS certs.
- [ ] **CSIGN-02**: Code-signing certs with weak algorithms (RSA<2048, EC<256, SHA-1) raise a HIGH finding.
- [ ] **CSIGN-03**: Code-signing CBOM components are de-duplicated by SHA-256 fingerprint against existing TLS-derived components.

### Scoring, Packaging & Lab (cross-cutting)

- [ ] **SCORE-01**: New API / code-signing / fuzzing signals contribute to the readiness score via the existing `agility_signals` subscore — no 7th pillar, no rollup-denominator change.
- [ ] **PKG-01**: A new `[api]` extras group is introduced; `schemathesis` is excluded from `[all]` and enforced by a CI guard test (impacket exclusion pattern).
- [ ] **LAB-01**: The chaos lab gains validation coverage for the new surfaces (OpenAPI spec endpoint, code-signing cert fixtures, isolated fuzzing target) with `expected_results_*.md` oracle updates.

---

## Future Requirements (deferred)

- Sigstore / cosign transparency-log queries (requires network + `sigstore` dep) — v5.2.
- npm / PyPI / Maven / Authenticode code-signing surfaces — v5.2+.
- OAuth2 client-credentials token *acquisition* (vs. accepting a supplied token) — conflicts with ephemeral-only model unless revisited.
- Authenticated *scheduled* scans — architecturally prohibited while credentials are ephemeral-only.

## Out of Scope (v5.1)

| Feature | Reason |
|---------|--------|
| Persisted credential store (`keyring` / `.env`) | Directly violates the ephemeral-only invariant; would make QU.I.R.K. a secret store to defend. |
| mTLS client-certificate auth | Higher effort; deferred per milestone-open decision. |
| A 7th readiness subscore for API surface | Would change the `÷1.5` rollup denominator and force edits to all renderers/gauges; API findings fold into `agility_signals` instead. |
| Provable credential zeroization | Python string immutability makes true zeroing impossible; "ephemeral" means *never persisted*, documented as best-effort in the security-review gate. |
| Full DAST behavior (destructive method fuzzing by default) | QU.I.R.K. is a crypto-posture inventory tool, not a DAST scanner; write/destructive methods are off by default behind layered flags. |

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| AUTH-01 | Phase 93 | Complete |
| AUTH-02 | Phase 93 | Complete |
| AUTH-03 | Phase 93 | Complete |
| AUTH-04 | Phase 93 | Complete |
| AUTH-05 | Phase 93 | Complete |
| SPEC-01 | Phase 94 | Pending |
| SPEC-02 | Phase 94 | Pending |
| SPEC-03 | Phase 94 | Pending |
| TOKEN-01 | Phase 94 | Pending |
| TOKEN-02 | Phase 94 | Pending |
| TOKEN-03 | Phase 94 | Pending |
| SCORE-01 | Phase 94 (partial), Phase 95 (partial), Phase 96 (final) | Pending |
| PKG-01 | Phase 94 | Pending |
| CSIGN-01 | Phase 95 | Pending |
| CSIGN-02 | Phase 95 | Pending |
| CSIGN-03 | Phase 95 | Pending |
| LAB-01 | Phase 95 (partial), Phase 96 (final) | Pending |
| FUZZ-01 | Phase 96 | Pending |
| FUZZ-02 | Phase 96 | Pending |
| FUZZ-03 | Phase 96 | Pending |
| FUZZ-04 | Phase 96 | Pending |
