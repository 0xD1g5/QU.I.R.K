# Project Research Summary

**Project:** QU.I.R.K. — Quantum Infrastructure Readiness Kit
**Milestone:** v5.1 Authenticated Scanning + API Surface Depth
**Domain:** Ephemeral credential model + OpenAPI/JWT surface analysis + gated active fuzzing + code-signing inventory
**Researched:** 2026-05-22
**Confidence:** HIGH (all four research files derived from direct codebase inspection + live PyPI verification + authoritative security sources)

---

## Executive Summary

v5.1 adds five tightly-coupled capabilities to an already-mature consulting-grade crypto scanner. The build order is not arbitrary — it is a hard dependency graph. The credential model (BACK-64) is the foundation without which three of the remaining four features cannot be tested end-to-end; however, OpenAPI spec analysis (BACK-10) and the standalone `--analyze-token` path of bearer token decode (BACK-11) are genuinely independent and can begin while Phase 93 credential work is in review. Code-signing cert inventory (BACK-24) reuses existing `cryptography` EKU APIs with zero new core dependencies and attaches to existing TLS and S/MIME scanner output, making it low-risk despite appearing complex. Active REST fuzzing (BACK-09) is the sharpest edge and must ship last — it requires the credential model, benefits from OpenAPI endpoint discovery, and carries the most significant guardrail burden before it can touch any live client network.

The stack picture is deliberately minimal. Zero new core dependencies are required for Features 1, 3, and 5. Only two new pip packages are needed at all — `openapi-spec-validator>=0.7.2` and `schemathesis>=4.4.4` — and both live exclusively in a new `[api]` extras group that is explicitly excluded from `[all]`. The `[all]` exclusion of `schemathesis` must be enforced by a CI test mirroring the existing `test_install_all_excludes_impacket.py` pattern. The single most important anti-addition is `keyring`: it would persist credentials to the OS keychain, directly violating the milestone's foundational ephemeral-only invariant.

The milestone's security posture requires honest accounting of one Python-specific limitation: credential zeroization is best-effort, not provably complete. Python strings are immutable and heap-resident; the `bytearray`-plus-`finally` pattern minimizes lifetime but cannot guarantee the original `str` (from `sys.argv`, `os.environ`, or `getpass`) is overwritten. The security-review gate deliverable must state this explicitly. Beyond this inherent constraint, the 11 leakage surfaces catalogued in PITFALLS.md (SQLite columns, CBOM fields, dashboard API, PDF export, debug logs, WAL file, etc.) must each be audited against a formal checklist, and the `safe_str()` scrubber in `quirk/util/safe_exc.py` must be extended with API-key header patterns before any authenticated scan code ships.

---

## Key Findings

### Recommended Stack

All four research files converge on the same conclusion: the existing stack already covers most of the v5.1 surface. `httpx` (HTTP client), `PyJWT` + `python-jose` (JWT decode), `cryptography>=44.0` (EKU OID extraction), `PyYAML` (spec loading), and `lxml` (XML manifests) are all in core and require no additions. The only new packages are `openapi-spec-validator>=0.7.2` (OpenAPI parsing, offline `$ref` resolution, OAS2+OAS3) and `schemathesis>=4.4.4` (spec-aware HTTP fuzzing that wraps `hypothesis`), both in `[api]` extras only.

Three explicit anti-additions emerged from research with strong rationale: `keyring` (persists credentials — defeats the ephemeral model), `prance` (resolves external `$ref` URLs — SSRF vector in air-gapped environments), and `python-dotenv` (reads `.env` files — persistence mechanism in disguise). The `schemathesis`-vs-`[all]` exclusion is the single highest-risk packaging decision and must be verified by CI on every PR.

**Core technologies (additions only — see PROJECT.md for full existing stack):**

- `openapi-spec-validator>=0.7.2`: Validates + resolves OAS2/OAS3 specs; pure-Python; handles local `$ref` without network calls. In `[api]` extras only.
- `schemathesis>=4.4.4`: Spec-aware HTTP fuzzer for crypto-posture probes; wraps `hypothesis`; `Case.as_transport_kwargs()` keeps `httpx` as the single HTTP client. In `[api]` extras only, excluded from `[all]` with CI gate.
- `cryptography>=44.0` (existing): `ExtendedKeyUsageOID.CODE_SIGNING` + `get_extension_for_class(x509.ExtendedKeyUsage)` covers code-signing cert classification with zero new deps.
- `PyJWT>=2.12.0` + `python-jose>=3.5.0` (existing): Bearer token decode without verification; `python-jose` as fallback for JWE and non-standard alg values PyJWT refuses.
- `getpass` + `os.environ` (stdlib): Credential prompt and env injection — `keyring` is the explicit avoid.

### Expected Features

**Must have (table stakes for the milestone to close):**

- BACK-64: Ephemeral credential model — Bearer/OAuth2, API key (header + query), HTTP Basic. No persistence, no `keyring`, no `.env`. `CredentialContext` dataclass constructed once at scan startup and threaded via lambda closure into `_wrapped_phase`. `safe_str()` extended to scrub `X-Api-Key`, `X-Auth-Token`, and query-param API key shapes.
- BACK-10: OpenAPI/Swagger spec analysis — `securitySchemes` extraction, `servers[]` HTTP detection, unauthenticated endpoint flagging, `source_type="spec"` CBOM provenance label. Local file path + well-known URL auto-fetch. Restricted `$ref` resolver (local-only; 10 MB size gate before parsing).
- BACK-11: Bearer token decode and classify — `alg` + `exp` + quantum-safety label. Two input paths: captured during authenticated scan, and standalone `--analyze-token`. CBOM components carry `declared_algorithm (unverified)` label — never treated as enforced. `JWT-TOKEN` protocol distinct from `JWT` (JWKS keys).

**Should have (v5.1 differentiators):**

- BACK-09: Active REST fuzzing — crypto-specific probes only (TLS downgrade, cipher acceptance, HSTS, HTTP-only credential transmission, `alg: none` injection). Six mandatory guardrails: GET-only default, hard budget ceiling (50 default / 500 max), rate cap (2 req/s default), `CONFIRM` prompt (not just Enter), scope enforcement against `cfg.targets`, 5xx pause. `--fuzz-jwt-alg-confusion` as a sub-flag for the alg-confusion attack probe.
- BACK-24: Code-signing cert inventory — LDAP `userCertificate` with CodeSigning EKU only for v5.1 (S/MIME pattern, reuses `smime_scanner.py`); EKU check on TLS scanner cert output (free pass). `CODE-SIGN/weak-algorithm` finding for RSA<2048, EC<256, SHA-1. De-duplicate CBOM components by cert SHA-256 fingerprint against existing TLS-derived components.

**Defer (v5.2+):**

- Sigstore/cosign transparency log queries (requires network; `sigstore` dep; v5.2)
- npm + PyPI + Maven + Authenticode code-signing surfaces (higher complexity, lower v5.1 consulting value)
- OAuth2 client credentials token acquisition (conflicts with ephemeral-only model)
- mTLS client cert injection (explicitly deferred in PROJECT.md)
- Authenticated scheduled scans (credential persistence — architecture prohibits it)

### Architecture Approach

The architecture is additive throughout — no existing modules are restructured. The `CredentialContext` dataclass (new `quirk/auth/credentials.py`) is constructed once in `run_scan.py` after config loading and captured into lambda closures at each `_wrapped_phase` call site. The `_wrapped_phase` signature is unchanged — credentials never enter the generic error handler. New scanner modules (`openapi_scanner.py`, `codesign_scanner.py`, `rest_fuzzer.py`) each emit `List[CryptoEndpoint]` through the same existing pipeline. Scoring stays at 6 pillars; new API/codesign signals fold into the existing `agility_signals` subscore via 4 new `agility_*` SCORE_WEIGHTS entries (sum moves from 283.0 to 303.0 across three phases). CBOM builder gets Pass-1 handlers for `OPENAPI`, `CODE_SIGN`, and `REST_FUZZ` protocol labels. Two new additive SQLite columns: `openapi_scan_json` and `codesign_scan_json`.

**Major components:**

1. `quirk/auth/credentials.py` (new) — `CredentialContext` dataclass; `build_credential_context(args, env)` factory; `as_headers()` / `as_query_params()` injection; `is_active` predicate. Zero imports from scanner modules (prevents circular deps).
2. `quirk/scanner/openapi_scanner.py` (new) — Passive spec analysis; restricted local-only `$ref` resolver; 10 MB size gate; emits `CryptoEndpoint(protocol="OPENAPI")`.
3. `quirk/scanner/codesign_scanner.py` (new) — EKU OID check on TLS + SMIME cert output; `CODE_SIGN` protocol; de-duplication by SHA-256 fingerprint.
4. `quirk/scanner/rest_fuzzer.py` (new) — `maybe_confirm_fuzz_budget()` gate (TTY-hard-only, `CONFIRM` required, non-TTY hard aborts); crypto-specific probes only; `REST_FUZZ` protocol.
5. `quirk/scanner/jwt_scanner.py` (modified) — Add `scan_bearer_token()` alongside existing `scan_jwt_targets()`.
6. `quirk/intelligence/scoring.py` + `evidence.py` (modified, additive) — 4 new `agility_*` weights; 3 new `_PROTOCOL_KEYS` entries.
7. `quirk/cbom/builder.py` (modified, additive) — Pass-1 handling for 3 new protocol labels.

### Critical Pitfalls

All 6 critical pitfalls identified in PITFALLS.md are directly relevant to Phase 93. They are not "nice to know" — each maps to a specific deliverable that must exist before authenticated scan code ships.

1. **Python string zeroization is best-effort, not provable** — Credentials arrive as `str` from `getpass`, `sys.argv`, and `os.environ`; Python's immutable string and GC semantics prevent true zeroing. Use `bytearray`; overwrite in `finally` (`BaseException`, not `Exception`); delete env var key after reading; document the limitation honestly in the security-review gate deliverable.

2. **Credential leakage across 11 stored/rendered surfaces** — Extend `_SENSITIVE_PATTERNS` for API-key header shapes; add token value to a call-local scrub set cleared in `finally`; extend AST gate deny-list to flag `api_key`, `token`, `password`, `authorization`, `bearer`, `credential` in `json.dumps()` / `model_dump()`; disable `httpx` debug logging; CBOM JWT-regex CI regression gate (`eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*`).

3. **OpenAPI `$ref` external URL resolution is an SSRF vector** — Restrict `$ref` resolution to local (same-file) only; `max_depth=10`; reject specs >10 MB before any parsing; CI test fixture with internal metadata URL (`http://169.254.169.254/`) asserts `SpecParsingError`.

4. **Active REST fuzzing causes client outage or WAF lockout** — All 6 guardrails are mandatory (GET-only default, hard budget ceiling, rate cap, `CONFIRM` prompt, scope enforcement, 5xx pause); non-TTY hard aborts (unlike nmap which auto-proceeds); chaos lab profile must be isolated with no shared state.

5. **JWT `alg` header is declared, not enforced** — All CBOM JWT components carry `declared_algorithm (unverified)` qualifier; `alg: none` (case-insensitive: None, NonE, NONE) hardcoded CRITICAL; alg-confusion active probe (`--fuzz-jwt-alg-confusion`) gated separately from general fuzzing.

6. **Bearer token logged or stored verbatim** — `safe_token_repr()` helper (first 8 + `...` + last 4 chars); AST gate flags `token`, `bearer`, `jwt` variable names passed to `logger.debug()` or `json.dumps()`; store analysis results only, never raw token.

---

## Open Decisions for Roadmapper to Resolve

These are genuine open questions. Each needs an explicit decision recorded in the relevant phase CONTEXT.md.

### Decision 1: Code-Signing Scope for v5.1

| Option | Coverage | New deps | Complexity |
|--------|----------|----------|-----------|
| A (recommended) | LDAP `userCertificate` CodeSigning-EKU + EKU check on existing TLS certs | Zero | LOW |
| B | Option A + Sigstore + npm registry signatures | `sigstore>=4.1.0`, network required | MEDIUM |
| C | Option A + B + Authenticode + Maven Central | Multiple, platform-specific | HIGH |

Architecture and STACK research both recommend Option A for v5.1. Sigstore requires network access, conflicts with the offline/air-gapped constraint, and adds a dep excluded from `[all]`. Confirm Option A; document Sigstore as v5.2 backlog.

### Decision 2: New 7th Subscore vs. Folding into `agility_signals`

Architecture research is explicit: **fold into `agility_signals`, do not add a 7th subscore.** The formula `total_score = int(round(sum_of_six / 1.5))` assumes a 0–150 ceiling; a 7th subscore changes it to 0–175 and requires updating the denominator, `SCORE_WEIGHTS` invariant test, all report renderers, and all six dashboard `ScoreGauge` components. API and code-signing findings are agility signals. Net addition: 4 new `agility_*` weights, SCORE_WEIGHTS sum 283.0 → 303.0 across three phases (Phase 94: +10.0 → 293.0; Phase 95: +6.0 → 299.0; Phase 96: +4.0 → 303.0).

### Decision 3: `alg: none` / Alg-Confusion Active Probe — In-Scope or Deferred

Features research recommends gating behind `--fuzz-jwt-alg-confusion` (in addition to `--fuzz`). This is a CVE-class attack probe (RS256→HS256 with server's public key as HMAC secret). The recommendation is in-scope in Phase 96 with a dedicated sub-flag and security-review gate checklist item.

### Decision 4: OpenAPI Spec Input — Local File Only vs. Authenticated URL Fetch

Local file path is the air-gapped-safe default. URL fetch is possible via existing `httpx` + `CredentialContext` but adds a second SSRF surface. Recommended: local file as default; URL fetch enabled only when the URL is in `cfg.targets`. The roadmapper should decide whether to implement both paths in Phase 94 or defer URL fetch.

---

## Implications for Roadmap

### Phase 93: Credential Infrastructure (BACK-64) — Foundational

**Rationale:** Every other phase requires or is enhanced by a credential model. The credential subsystem introduces the most significant security surface in the milestone and must be security-reviewed before anything authenticates against live targets.

**Delivers:**
- `quirk/auth/credentials.py`: `CredentialContext` dataclass + factory
- All `--auth-*` CLI flags and `QUIRK_AUTH_*` env vars in `run_scan.py`
- `ConnectorsCfg.enable_authenticated_mode: bool = False`
- `safe_exc.py` extended with API-key header patterns
- `quirk schedule add` rejects configs with `enable_authenticated_mode: true` (QRK-SCHED-AUTH-001)
- Schema-level CI assertion: no `scheduled_scans` or `scan_checkpoints` column named `key`, `token`, `password`, `secret`, `credential`
- AST gate extended with `bearer`, `api_key`, `authorization`, `token` deny-list
- Committed security-review gate deliverable: credential lifetime audit + 11-surface leakage checklist + best-effort zeroization documentation
- Tests: construction from flags/env; scrubbing patterns; schedule rejection; `as_headers()` for all three schemes

**Features from FEATURES.md:** BACK-64 core
**Pitfalls to avoid:** Pitfall 1 (zeroization), Pitfall 2 (11-surface leakage), Pitfall 9 (scheduler persistence)
**Research flag:** Standard pattern — architecture fully specified; no research phase needed

### Phase 94: Bearer Token Analysis + OpenAPI Spec Analysis (BACK-11, BACK-10)

**Rationale:** Bearer token decode's standalone `--analyze-token` path has zero credential dependency and is the lowest-risk post-Phase-93 feature. OpenAPI spec analysis is fully passive. Both feed the `OPENAPI` and `JWT-TOKEN` CBOM protocol families and share `agility_api_*` evidence counters. Coupling them in one phase is efficient given shared evidence/scoring touch-points.

**Delivers:**
- `jwt_scanner.py`: `scan_bearer_token()` (decode-only, no network I/O, `declared_algorithm (unverified)` label, `alg: none` CRITICAL detection case-insensitive)
- `quirk/scanner/openapi_scanner.py`: local file parsing + restricted `$ref` resolver + 10 MB size gate + well-known URL auto-fetch
- `evidence.py`: `OPENAPI` in `_PROTOCOL_KEYS`; `api_weak_alg_count`, `api_no_expiry_count`
- `scoring.py`: `agility_api_weak_alg_ratio` (6.0) + `agility_api_no_expiry_ratio` (4.0); SCORE_WEIGHTS sum → 293.0
- `models.py`: `openapi_scan_json TEXT` column (additive)
- `builder.py`: Pass-1 handling for `OPENAPI` protocol
- `pyproject.toml`: `[api]` extras group with `openapi-spec-validator>=0.7.2`
- `quirk/util/optional_extra.py`: register `openapi-spec-validator` under `api` group
- CBOM JWT-regex CI regression gate
- Chaos lab: extend existing jwt profile with an OpenAPI spec endpoint
- `tests/test_score_weights_invariant.py`: update expected sum to 293.0

**Uses:** `openapi-spec-validator>=0.7.2` (new), `PyJWT>=2.12.0` (existing)
**Features from FEATURES.md:** BACK-10, BACK-11
**Pitfalls to avoid:** Pitfall 4 (`$ref` SSRF — critical Day 1 task), Pitfall 5 (alg-confusion misclassification), Pitfall 6 (token logging/storage), Pitfall 8 (spec-declared vs. observed mismatch)
**Research flag:** Standard pattern — no research phase needed

### Phase 95: Code-Signing Certificate Inventory (BACK-24)

**Rationale:** Independent of Phase 94; can run in parallel if agent capacity allows. Reuses existing `cryptography` EKU API and attaches to existing TLS and SMIME scanner cert pipelines — no new network probe targets. De-duplication requirement (fingerprint-based) must be in the initial design, not retrofitted (Phase 42 OBS-1 lesson).

**Delivers:**
- `quirk/scanner/codesign_scanner.py`: EKU OID check on TLS + SMIME cert objects; de-duplication by SHA-256 fingerprint; `CryptoEndpoint(protocol="CODE_SIGN")`
- `CODE-SIGN/weak-algorithm` finding (RSA<2048, EC<256, SHA-1); severity HIGH
- `evidence.py`: `CODE_SIGN` in `_PROTOCOL_KEYS`; `codesign_weak_count`
- `scoring.py`: `agility_codesign_weak_ratio` (6.0); SCORE_WEIGHTS sum → 299.0
- `models.py`: `codesign_scan_json TEXT` column (additive)
- `builder.py`: Pass-1 handling for `CODE_SIGN` (CertificateProperties path)
- `ConnectorsCfg`: `enable_codesign: bool = False`, `codesign_targets: list`
- De-duplication test: component count does not increase when running with/without `--inventory-code-signing` on a target that already has TLS certs captured
- Chaos lab: fixture files (sample X.509 certs with RSA-1024, SHA-1, ECDSA P-256 codeSigning EKU)
- `tests/test_score_weights_invariant.py`: update expected sum to 299.0

**Uses:** `cryptography>=44.0` (existing, zero new deps)
**Features from FEATURES.md:** BACK-24 (Option A scope: LDAP + TLS EKU check only)
**Pitfalls to avoid:** Pitfall 7 (scope creep + false classification — primary EKU ordering rule, fingerprint de-duplication)
**Research flag:** Standard pattern — no research phase needed

### Phase 96: Active REST Fuzzing Gate (BACK-09) — Ships Last

**Rationale:** Depends on Phase 93 (credentials) and benefits from Phase 94 (OpenAPI-discovered endpoints). Ships last because all guardrails must be complete and security-reviewed before the first fuzz request goes to a live target. The non-TTY hard abort differentiates this from the nmap gate (which auto-proceeds). `schemathesis` excluded from `[all]` with CI gate from day one.

**Delivers:**
- `quirk/scanner/rest_fuzzer.py`: crypto-specific probes only; `maybe_confirm_fuzz_budget()` gate (TTY-hard, `CONFIRM` required, non-TTY hard aborts)
- `schemathesis>=4.4.4` added to `[api]` extras; `tests/test_install_all_excludes_schemathesis.py` CI gate
- All 6 mandatory guardrails: GET-only default (`--fuzz-write-methods` to add POST), hard budget ceiling (default 50, max 500), rate cap (2 req/s, configurable), `CONFIRM` prompt, scope enforcement via `cfg.targets` intersection, 5xx pause (>3 consecutive → halt and alert)
- `--fuzz-jwt-alg-confusion` sub-flag for RS256→HS256 confusion attack probe
- `ConnectorsCfg`: `enable_rest_fuzzing: bool = False`, `rest_fuzzing_budget: int = 500`, `rest_fuzzing_targets: list`
- `TimeoutsCfg`: `rest_fuzzing_seconds: int = 15`
- `evidence.py`: `REST_FUZZ` in `_PROTOCOL_KEYS`; `api_fuzzing_weak_cipher_count`
- `scoring.py`: `agility_fuzz_weak_cipher_ratio` (4.0); SCORE_WEIGHTS sum → 303.0
- `run_scan.py`: gate call site with `maybe_confirm_fuzz_budget` + hard non-TTY abort + `_wrapped_phase`
- Chaos lab: isolated container (no shared state) responding to crafted cipher-preference requests
- Security-review gate: all 6 guardrails enforced; alg-confusion probe properly sub-flagged; CONFIRM not bypassable via stdin redirect
- `tests/test_score_weights_invariant.py`: final update to 303.0

**Uses:** `schemathesis>=4.4.4` (new, `[api]` only, CI-excluded from `[all]`)
**Features from FEATURES.md:** BACK-09
**Pitfalls to avoid:** Pitfall 3 (client outage / WAF lockout — all 6 guardrails mandatory), Pitfall 5 (alg-confusion probe gated separately)
**Research flag:** Standard pattern — guardrails fully specified; risk is in implementation completeness

### Phase Ordering Rationale

The dependency graph is strict and must be respected:
- Phase 93 before everything (credential model is foundational)
- Phase 94 before Phase 96 (OpenAPI discovers endpoints; fuzzer targets them)
- Phase 95 can run parallel to Phase 94 (no shared integration touch-points beyond Phase 93)
- Phase 96 last (requires 93 for credentials, 94 for endpoint discovery, and the Phase 93 security-review gate must be complete before sending crafted traffic to any live target)

The passive/active split is intentional: Phases 93–95 are all passive or read-only analysis. Phase 96 introduces active traffic generation and must demonstrate all guardrails are functional against the chaos lab before any engagement use.

### Research Flags

All four phases have standard patterns — no dedicated research sub-phase is needed for any of them. The four research agents provided implementation-ready specificity throughout.

- **Phase 93:** Architecture fully specified down to field names and `finally` block pattern; all integration seams verified in live source.
- **Phase 94:** SSRF gate and `$ref` restriction approach fully specified; token decode path uses existing library calls.
- **Phase 95:** EKU OID list and `cryptography` API calls verified against live library; de-duplication approach established from Phase 42 OBS-1 lessons.
- **Phase 96:** Guardrail list exhaustive and fully specified; `schemathesis` `Case.as_transport_kwargs()` API verified.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All version numbers verified against live PyPI index 2026-05-22; all integration points confirmed from direct codebase inspection; anti-additions have clear documented rationale |
| Features | HIGH | Direct code inspection of `jwt_scanner.py`, `scoring.py`, `classifier.py`, `targets.py`, `run_scan.py`; BACK items verified in ROADMAP.md; industry norms confirmed from Veracode, StackHawk, OpenAPI spec docs |
| Architecture | HIGH | All integration seams verified against live source (models.py, config.py, evidence.py, scoring.py, builder.py, safe_exc.py); SCORE_WEIGHTS sum 283.0 and invariant test pattern verified; Phase 86 math confirmed |
| Pitfalls | HIGH (credential/JWT vectors); MEDIUM (fuzzing guardrails, SSRF) | Credential leakage and JWT alg-confusion: authoritative security sources (PortSwigger, Langkemper, GHSA advisories). Fuzzing outage risk: Microsoft RESTler docs + pentesting scope literature. SSRF via `$ref`: current 2026 CVE. |

**Overall confidence:** HIGH

### Gaps to Address During Planning

1. **`schemathesis` httpx dispatch integration (MEDIUM risk):** `schemathesis` uses `requests` transport by default; QUIRK uses `httpx`. The `Case.as_transport_kwargs()` API enables httpx dispatch but needs integration testing before the fuzzing phase begins. Assign as Day 1 task in Phase 96.

2. **`openapi-spec-validator` + `jsonschema-path` transitive dep (LOW risk):** `openapi-spec-validator>=0.7.2` requires `jsonschema-path` (distinct from `jsonschema`). `jsonschema 4.25.1` and `referencing 0.36.2` are already installed; verify `jsonschema-path` installs cleanly without conflicts at Phase 94 start.

3. **Authenticated URL fetch for OpenAPI specs — scope decision pending (LOW risk):** Both local-file-only and URL-with-scope-restriction approaches are viable. The roadmapper must decide whether Phase 94 implements URL fetch or defers it. This does not change the SSRF mitigation — the `$ref` resolver restriction is required regardless.

4. **Chaos lab coverage for new protocols:** Three new chaos lab requirements emerge (openapi-spec endpoint, codesign fixture files, fuzzing isolated container). These must be part of the respective phase plans and validated via `expected_results_*.md` oracle files per CLAUDE.md maintenance rules.

5. **`quirk/auth/credentials.py` vs. `quirk/util/credentials.py` module path:** STACK.md proposes `quirk/auth/credentials.py`; ARCHITECTURE.md proposes `quirk/util/credentials.py`. Both are functionally equivalent. Recommendation: `quirk/auth/` as a new subdirectory signals a distinct concern boundary and is more discoverable. The roadmapper should confirm and document in Phase 93 CONTEXT.md.

---

## Sources

### Primary (HIGH confidence)

- `quirk/scanner/jwt_scanner.py` — Integration point for bearer token decode; `scan_jwt_targets()` signature; `_rsa_key_bits_from_n()` helper; `HTTPX_AVAILABLE` pattern
- `quirk/intelligence/scoring.py` — SCORE_WEIGHTS sum 283.0; `agility_` prefix behavior; 6-pillar formula
- `quirk/cbom/classifier.py` — `_ALGORITHM_TABLE` for JWT alg entries; classifier path
- `quirk/util/targets.py` — `maybe_confirm_probe_budget` pattern; nmap gate design
- `quirk/util/safe_exc.py` — `_SENSITIVE_PATTERNS` tuple; `Authorization: Bearer` pattern present; API-key variants absent
- `pyproject.toml` — Core deps and extras groups; `[all]` exclusion of `impacket` as pattern precedent
- `.planning/PROJECT.md` — v5.1 milestone scope; key decisions; certipy-ad deferral; ephemeral-only invariant
- PyPI live index 2026-05-22 — All version numbers for `openapi-spec-validator`, `schemathesis`, `cryptography`, `PyJWT`, `python-jose`
- [JWT Algorithm Confusion Attacks — PortSwigger](https://portswigger.net/web-security/jwt/algorithm-confusion) — RS256→HS256 swap attack mechanics
- [JWT Attacks — PortSwigger](https://portswigger.net/web-security/jwt) — `alg: none` case variants
- [SSRF via OpenAPI `$ref` — GHSA-vv7q-7jx5-f767](https://github.com/PrefectHQ/fastmcp/security/advisories/GHSA-vv7q-7jx5-f767) — 2026 advisory confirming `$ref` SSRF is current

### Secondary (MEDIUM confidence)

- `openapi-spec-validator` PyPI page + README — OAS2/OAS3 support, `jsonschema-path` dep, offline `$ref` resolution
- `schemathesis` PyPI / GitHub README — `stateful=False` mode, `max_examples`, `Case.as_transport_kwargs()` API
- [Clearing Memory in Python — Sjoerd Langkemper](https://www.sjoerdlangkemper.nl/2016/06/09/clearing-memory-in-python/) — Python string zeroization fundamental limits
- [Trail of Bits: Building cryptographic agility into Sigstore](https://blog.trailofbits.com/2026/01/29/building-cryptographic-agility-into-sigstore/) — Code-signing agility context
- [WuppieFuzz: REST API Fuzzing (arXiv 2512.15554)](https://arxiv.org/pdf/2512.15554) — Fuzzing scope reference

### Tertiary (LOW confidence)

- [Venari Security: Post-Quantum JWT](https://www.venarisecurity.com/post-quantum-jwt-security/) — PQC JWT classification norms; single source, consistent with NIST guidance
- [nflo.tech: Scope creep in pentesting](https://nflo.tech/knowledge-base/scope-creep-in-pentesting-projects/) — Code-signing scope enforcement practices

---

*Research completed: 2026-05-22*
*Ready for roadmap: yes*
