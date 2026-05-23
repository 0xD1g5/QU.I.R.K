# Feature Research — v5.1 Authenticated Scanning + API Surface Depth

**Domain:** Consulting-grade cryptographic inventory scanner — capability milestone adding authenticated scanning and deeper API surface analysis.
**Researched:** 2026-05-22
**Confidence:** HIGH — all findings derived from direct code inspection of `quirk/scanner/jwt_scanner.py`, `quirk/intelligence/scoring.py`, `quirk/cbom/classifier.py`, `quirk/util/targets.py`, `run_scan.py`, `.planning/ROADMAP.md` BACK items, and `.planning/HORIZON.md`. Web research corroborates industry norms for authenticated scanning and OpenAPI analysis.

---

## Context: What Already Exists (Do Not Re-Build)

These exist and serve as integration seams for v5.1:

- **JWT/JWKS scanner (`quirk/scanner/jwt_scanner.py`):** Passive. Probes `/.well-known/jwks.json`, `/oauth/jwks`, OIDC discovery. Extracts `kty`, `alg`, RSA modulus bits, EC curve bits. Stores raw key entry in `jwt_scan_json` column. Emits one `CryptoEndpoint` per key. Already wired into `run_scan.py` via `_wrapped_phase`, config at `cfg.connectors.enable_jwt` + `cfg.connectors.jwt_targets`. No credential support.
- **CBOM classifier (`quirk/cbom/classifier.py`):** Master `_ALGORITHM_TABLE` maps normalized algorithm names to `(CryptoPrimitive, nist_quantum_security_level, classical_security_level)`. Already covers JWT algorithms (`RS256`, `ES256`, `HS256`, etc.) where they match TLS/SSH naming conventions; JWT-specific alg names (`RS256`, `RS384`, `RS512`, `ES256`, `ES384`, `PS256`, `HS256`, `HS384`, `HS512`) need explicit entries if not already present.
- **Probe-budget guard (`quirk/util/targets.py:maybe_confirm_probe_budget`):** TTY-aware y/N gate with 10,000-probe threshold, auto-proceed on non-TTY. Active fuzzing must mirror this exact pattern.
- **`safe_str()` scrubbing (`quirk/util/safe_exc.py`):** Must wrap any exception that might carry credential material. Already enforced via AST gate (`tests/test_leak_safe_str_gate.py`).
- **`_wrapped_phase()` in `run_scan.py`:** Uniform error capture for all scanner phases. Any new scanner phase must use it.
- **SCORE_WEIGHTS invariant test (`tests/test_score_weights_invariant.py`):** Any new scoring weight must update this test. CI fails on sum mismatch.

---

## Feature Landscape

### Table Stakes (Consultants Expect These)

Features a security tool in this class must provide. Missing any of these makes the milestone feel half-finished against its own stated goal.

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| Ephemeral credential injection — Bearer/OAuth2, API key, HTTP Basic | Authenticated scanning is the milestone's stated purpose. Without a credential model, nothing else in this milestone unlocks. Consultants pass tokens per-engagement; the tool must accept them at run time without storing them. | MEDIUM | Foundational; all other features depend on it. Config-layer + CLI flag + env-var injection. Must use `safe_str()` on all exc paths. |
| OpenAPI/Swagger spec parsing — securitySchemes, oauth flows, JWT bearer formats | Security consultants routinely receive spec files from clients as part of an engagement. Parsing a spec to extract `securitySchemes` (type, scheme, bearerFormat, oauth2 flows, scopes) is the lowest-risk way to enumerate API crypto surface without sending any traffic. Industry-standard entry point for API security assessment tools (Veracode, StackHawk, Acunetix all support this). | LOW–MEDIUM | Depends on: no live-scan credential injection. Pure static analysis; works offline. CBOM builder needs spec-origin algorithm components (new `source_type="spec"` origin label). |
| Bearer token decode and classify — alg, key size, expiry, quantum-safety label | When an authenticated scan returns a token (or the consultant provides a captured token), classifying its `alg` claim against the NIST PQC quantum-safety table is the primary consulting deliverable. RS256/ES256 tokens are quantum-vulnerable. No expiry (`exp` absent) is a HIGH finding regardless of algorithm. This is what "Bearer token interception & analysis" (BACK-11) means in practice — token decode from the Authorization header seen on responses, or from a provided sample. | LOW | Depends on: JWT/JWKS classifier already in `_ALGORITHM_TABLE` (verify entries exist for `RS256`, `RS384`, `RS512`, `ES256`, `ES384`, `PS256`, `HS256`, `HS384`, `HS512`). CBOM builder needs a `JWT-TOKEN` protocol entry distinct from `JWT` (JWKS key). |
| CBOM integration for new protocol sources | A consulting deliverable CBOM that omits authenticated-endpoint findings or spec-declared algorithms is an incomplete bill of materials. All new findings must emit `CryptoPrimitive` components through the existing `Pass-1/2/3` pipeline. | MEDIUM | Depends on: existing `builder.py` pass structure. New protocol labels need skip-list entries if they emit non-algorithm components. |
| Findings surface in scoring (agility/api sub-pillar) | Authenticated-scan findings that do not affect the score are invisible to the client's score interpretation. JWT algorithm weakness already feeds `agility_high_impact_ratio` via `finding_severity_counts`. New authenticated-scan findings must flow through the same path or a new `api_*` evidence counter set. | MEDIUM | Depends on: `SCORE_WEIGHTS` invariant test must be updated. If adding new `api_*` weights, sum changes. |

### Differentiators (Competitive Advantage)

Features that distinguish QU.I.R.K. in a consulting context against generic API scanners.

| Feature | Value Proposition | Complexity | Dependencies |
|---------|-------------------|------------|--------------|
| OpenAPI spec analysis produces CBOM components without live traffic | No other lightweight CLI tool emits a CycloneDX CBOM from an OpenAPI spec file. A consultant can run `quirk scan --spec ./openapi.json` against a client's spec before the live scan and have a partial CBOM and finding list to review. "Spec-origin" components in the CBOM carry a clear provenance label. | MEDIUM | `pyyaml` or `jsonschema` parsing; `openapi-spec-validator` (pip-installable) for optional schema validation. No new major dependency needed — httpx already present for live fetching of `/openapi.json`. |
| Active REST fuzzing for crypto posture — TLS downgrade + header crypto checks — gated by opt-in flag | Sending crafted TLS ClientHello messages to an API endpoint to detect whether it accepts SSLv3/TLS 1.0 is something passive scanning does not catch (TLS scanner already does this for port 443, but API endpoints on non-standard ports or behind load balancers with different TLS termination may have different posture). The key differentiator is the integration: fuzzing results feed the same CBOM + score pipeline, not a separate tool report. | HIGH | Depends on: opt-in `--enable-fuzzing` CLI flag + explicit `--authorize-active-probing` confirmation (mirrors nmap pattern in `maybe_confirm_probe_budget`). sslyze already handles TLS downgrade; the new work is applying it to `cfg.connectors.jwt_targets` (the API endpoint set) with a bounded request budget. |
| Code signing certificate discovery — CI/CD artifact signing posture | Supply chain crypto posture is an emerging consulting ask (post-SolarWinds, post-Log4Shell). Discovering that a client's artifacts are signed with RSA-1024 or SHA-1 is a HIGH finding that feeds the CBOM and score. Sigstore/cosign (ECDSA P-256) is currently the best practice; ML-DSA hybrid signing is emerging (Trail of Bits / Sigstore cryptographic agility work, published 2026-01). Classifying what a client's pipeline actually uses vs. what NIST recommends is a clear deliverable. | HIGH | Depends on: no single pip-installable library covers all signing formats (Authenticode, GPG, macOS notarization, Sigstore transparency log). Feasibility gate needed per signing format. |
| Captured bearer token analysis — decode from `Authorization: Bearer` on observed responses | When a consultant runs an authenticated scan and the scanner captures the token sent in the request headers (or extracts it from a provided sample), decoding it (without verification — inventory only) exposes `alg`, `kid`, `iss`, `exp`, `nbf` claims. This is distinct from JWKS (which shows *available* signing keys) — this shows which algorithm was *actually used* for a token in the current session. Quantum-vulnerable algorithm on a live production token is a higher-urgency finding than a JWKS entry for an unused key. | LOW | Depends on: `PyJWT` (already a common transitive dep) or manual base64 decode (no verification needed). Credential must be scrubbed from `CryptoEndpoint.service_detail` via `safe_str()`. |

### Anti-Features (Avoid These)

| Feature | Why Requested | Why Problematic | What to Do Instead |
|---------|---------------|-----------------|-------------------|
| Persisted credential store (encrypted vault for scheduled authenticated scans) | Operators want to schedule authenticated scans the same way they schedule unauthenticated ones | QU.I.R.K. is a CLI tool, not a secrets manager. Storing credentials at rest introduces a new attack surface and a security-review scope larger than the entire authenticated-scan feature. PROJECT.md decision: "QU.I.R.K. is never a stored-secret surface to defend." Scheduled authenticated scans are explicitly out of scope for v5.1. | Ephemeral-only: per-run injection via `--bearer-token`, `QUIRK_BEARER_TOKEN` env var, or interactive prompt. Document that scheduled scans remain unauthenticated. |
| mTLS client certificate injection | Enterprise APIs increasingly require mTLS | mTLS involves managing client key material on disk; same attack-surface objection as persisted credentials. Security review scope expands significantly. | PROJECT.md explicitly defers mTLS to post-v5.1. Accept graceful degradation finding ("mTLS required — unauthenticated path blocked") as a valid inventory result. |
| Full DAST (dynamic application security testing) mode | Fuzzing is a short hop from "probe cipher suites" to "probe OWASP Top-10 injection vectors" | Scope drift into a full DAST tool changes the product's identity and liability surface. The `--enable-fuzzing` flag must be bounded to *crypto posture* probes only: TLS version negotiation, cipher acceptance, header crypto checks (`Strict-Transport-Security`, `Expect-CT`). Not injection, not auth bypass. | Hard-code the fuzzing probe list. No plugin API. No generic request injection. |
| Traffic MITM / passive capture mode for token interception | Wireshark-style capture would surface more tokens | Requires elevated OS privileges (raw socket / libpcap), breaks the agentless model, and is scope-equivalent to Zeek — already listed as out of scope in PROJECT.md under "Network traffic capture." | Token interception from `Authorization: Bearer` header on requests *QU.I.R.K. itself sends* (during authenticated scan) is the correct model. Consultant can also provide a captured token via `--analyze-token`. |
| OpenAPI spec *fuzzing* — generating test inputs from spec to find injection bugs | A logical extension of spec analysis | Moves from crypto-posture inventory into full API security testing. Different scope, different liability. Not the QU.I.R.K. product identity. | OpenAPI analysis scope: securitySchemes extraction, declared algorithm classification, endpoint count per scheme, missing-auth endpoint flagging. No request generation. |
| OAuth2 client credentials flow (full token acquisition) | Deeper authenticated scanning if scanner can fetch its own tokens | Requires storing `client_secret`; conflicts with the ephemeral-only credential decision. Full OAuth2 flow also means the scanner becomes an OAuth client — adds complexity and security review scope. | Accept Bearer tokens the operator provides (already acquired outside QU.I.R.K.). Emit a finding if the JWKS endpoint's algorithm is quantum-vulnerable. |

---

## Feature Dependencies

```
BACK-64: Authenticated credential model (ephemeral)
    └──enables──> BACK-11: Bearer token capture & classify
                      └──feeds──> CBOM Pass-1 (JWT-TOKEN protocol components)
                      └──feeds──> agility subscore (via finding_severity_counts)
    └──enables──> BACK-09: Active REST fuzzing (crypto probes only)
                      └──requires──> maybe_confirm_probe_budget gate (existing)
                      └──requires──> --enable-fuzzing opt-in flag
                      └──feeds──> CBOM + score (same pipeline)
    └──enables──> (future) Deeper Kerberos LDAP bind, SSH sshd_config inspect

BACK-10: OpenAPI/Swagger spec analysis
    └──independent of BACK-64 (passive, no credentials needed)
    └──feeds──> CBOM Pass-1 (spec-origin algorithm components)
    └──feeds──> agility subscore
    └──enhances──> BACK-11 (spec declares expected alg; token analysis validates actual alg matches)

BACK-24: Code signing cert inventory
    └──partially independent of BACK-64 (some formats are public: Sigstore transparency log, npm registry sigs)
    └──partially depends on BACK-64 (CI/CD API auth to fetch signing metadata from private registries)
    └──feeds──> CBOM Pass-1 (new CODESIGN protocol family)
    └──feeds──> agility subscore
```

### Dependency Notes

- **BACK-64 is foundational but BACK-10 is independent:** OpenAPI spec analysis (passive, static) can be implemented and tested entirely without credentials. This means BACK-10 can be a standalone earlier phase while BACK-64 is being designed and security-reviewed.
- **BACK-11 depends on BACK-64 for the "authenticated call captures token" path** but has a second independent input path: `--analyze-token <token>` (analyst provides a captured token directly). This second path also does not require BACK-64.
- **BACK-09 (active fuzzing) is the hardest dependency:** it requires BACK-64 (to test authenticated endpoints) and the probe-budget gate. It also requires a security-review gate on what probes are in scope (crypto-only, no injection).
- **BACK-24 (code signing) has the fewest integration dependencies** of any of the five features — it reads X.509 certificate properties from signing artifacts and classifies them through the existing classifier. The complexity is surface discovery (what signing formats to support), not integration.

---

## Per-Feature Expected Behavior

### BACK-64: Authenticated Scan Mode — Ephemeral Credential Handling

**How it works in comparable tools:** Veracode API scanning, Acunetix, StackHawk all support per-scan credential injection via Authorization header or API key header. Credentials are provided at scan launch, held in memory for the scan's duration, and not persisted. All three tools mask credentials in logs.

**Credential types for v5.1:**

| Type | Injection method | HTTP wire format | Scanner use |
|------|-----------------|-----------------|-------------|
| Bearer / OAuth2 access token | `--bearer-token TOKEN` or `QUIRK_BEARER_TOKEN` env var or interactive prompt | `Authorization: Bearer <token>` | JWT scanner authenticated path; REST fuzzing; spec validation |
| API key (header) | `--api-key-header "X-Api-Key: <val>"` or env var | Custom header name:value | REST fuzzing; spec validation |
| API key (query param) | `--api-key-query "api_key=<val>"` or env var | URL query string (TLS only) | REST fuzzing |
| HTTP Basic | `--basic-auth user:pass` or env var | `Authorization: Basic <b64>` | REST fuzzing; some identity endpoints |

**What deeper findings authentication unlocks vs. unauthenticated:**

| Finding | Unauthenticated | Authenticated |
|---------|----------------|---------------|
| JWKS key algorithm | Available (passive JWKS fetch) | Same, plus token-in-use validation |
| Actual token algorithm (`alg` claim) | Not available | Available via `Authorization: Bearer` capture on authenticated responses |
| Token expiry policy (`exp` absent) | Not available | Available via token decode |
| OpenAPI declared algorithm vs. actual | Spec analysis only (no validation) | Spec + live token comparison |
| Endpoints requiring auth (403 vs. 200) | Not classified | Authenticated: reachable, unauthenticated: access-denied finding |
| TLS posture of authenticated API endpoints | Partially available (TLS scanner covers the host, but may not cover the specific API port) | Confirmed for the exact endpoint URL under test |

**Security invariants (non-negotiable for the security-review gate):**

1. Credentials MUST NOT appear in `CryptoEndpoint.service_detail`, `scan_error_category`, or log output. `safe_str()` wraps every exception on credentialed code paths.
2. Credentials MUST NOT be written to the SQLite database (the `jwt_scan_json` column stores key material from JWKS, not operator-provided credentials).
3. Credentials MUST NOT appear in the HTML/PDF/CBOM report. The report may reference "authenticated scan" but never the credential value.
4. `safe_str()` AST gate already enforces (1) for scan_error writes. The v5.1 security-review gate should extend this to `service_detail` writes in the JWT scanner and any new authenticated scanner.
5. Credentials exist in Python process memory only for the duration of `_wrapped_phase()`. No pickling, no serialization.

### BACK-10: OpenAPI/Swagger Spec Analysis — Crypto Signal

**What crypto-relevant signal lives in a spec:**

| Signal | Location in spec | Finding to emit |
|--------|-----------------|-----------------|
| `securitySchemes[].type = "http", scheme = "bearer", bearerFormat = "JWT"` | `components/securitySchemes` | CBOM component for JWT algorithm if bearerFormat specifies one (e.g., `bearerFormat: RS256`). No finding if bearerFormat is absent (informational note only). |
| `securitySchemes[].type = "oauth2", flows.*.tokenUrl` | `components/securitySchemes` | OAuth2 flow declared; token endpoint URL captured for follow-up live probe. No crypto finding without token algorithm data. |
| `securitySchemes[].type = "apiKey"` | `components/securitySchemes` | API key scheme declared; HIGH finding if `in: query` (credentials in URL, logged by proxy/CDN). |
| `securitySchemes[].type = "http", scheme = "basic"` | `components/securitySchemes` | MEDIUM finding — Basic auth is quantum-irrelevant but transmits credentials base64-only; flagged as weak authentication scheme if TLS is not confirmed. |
| Endpoints with no `security` declaration and no global `security` | `paths[*][method].security = []` | MEDIUM finding "Unauthenticated endpoint declared in spec" — quantum-irrelevant but API surface hygiene. |
| Declared TLS servers (`servers[].url` scheme = `https` vs `http`) | `servers[]` | HIGH finding if any server URL uses `http://`. |
| `securitySchemes` that reference deprecated OIDC parameters | `components/securitySchemes` | LOW/MEDIUM if discoverable, but usually too API-specific to classify without live scanning. |

**Spec sources to support:**
1. Local file path (`--spec ./openapi.yaml` or `--spec ./swagger.json`)
2. Well-known URL auto-fetch: `/openapi.json`, `/openapi.yaml`, `/swagger.json`, `/swagger/v1/swagger.json`, `/v2/api-docs` (Spring Boot)
3. No authentication required for spec fetch path (specs should be publicly accessible; authenticated spec fetch is a v5.2+ concern)

**CBOM integration:** Spec-declared algorithms emit `CryptoPrimitive` components with `source_type="spec"` provenance. These are marked clearly in the CBOM as "spec-declared, not live-verified" to distinguish from scanner-observed components.

### BACK-11: Bearer Token Interception and Analysis

**Two input paths:**

1. **Captured from authenticated scan:** During an authenticated REST scan (`--bearer-token TOKEN`), QU.I.R.K. sends the token in the Authorization header. The scanner inspects the token it is about to send (decode-only, no verification) and emits a finding for the decoded `alg`.
2. **Analyst-provided sample:** `--analyze-token <base64url_or_raw_jwt>` decodes and classifies a token the analyst captured externally. This path has zero dependencies on BACK-64.

**What to extract and classify:**

| Claim | Extraction | Finding |
|-------|-----------|---------|
| `alg` header | `header.alg` (JOSE header, base64url decode part 0) | Classify against `_ALGORITHM_TABLE`. RS256/RS384/RS512/ES256/ES384/PS256 → quantum-vulnerable HIGH. HS256/HS384/HS512 → quantum-vulnerable MEDIUM (symmetric, Grover halves strength, but 256-bit HS256 key retains 128-bit quantum security — note complexity). `none` alg → CRITICAL. Unknown alg → MEDIUM (quantum-unknown). |
| `exp` payload claim | `payload.exp` (Unix timestamp) | Absent `exp` → HIGH "No expiry policy declared." Expired token → MEDIUM "Token used past expiry." Far-future `exp` (> 30 days) → LOW "Long-lived token." |
| `iss` payload claim | `payload.iss` | Informational only — identifies the issuing authority for the CBOM component. |
| `kid` header claim | `header.kid` | Cross-reference with JWKS scan: does the `kid` appear in the JWKS? Informational. |
| Key size | Not available from token alone (key size comes from JWKS `n` modulus) | If JWKS scanner has already run, join on `kid` to get key size. |

**CBOM integration:** Token-observed algorithms emit `CryptoPrimitive` components with `protocol="JWT-TOKEN"` (distinct from `protocol="JWT"` used for JWKS keys). This preserves the distinction between "algorithm available in JWKS" and "algorithm observed in a live token."

**Quantum-safety classification:**
- RS256 (RSA-2048 signature): NIST level 0 (quantum-vulnerable). Current `_ALGORITHM_TABLE` may not have `rs256` as a key — needs addition.
- ES256 (ECDSA P-256): NIST level 0 (quantum-vulnerable). Shor's algorithm breaks discrete log on elliptic curves.
- HS256 (HMAC-SHA256): NIST level 0 by convention in the table (symmetric Grover), but pragmatically 128-bit post-quantum with a 256-bit key. Emit MEDIUM not HIGH for HS256.
- `none`: CRITICAL (no signature).
- ML-DSA-44/65/87 (FIPS 204): NIST level 2/3/5 — quantum-safe. Not yet common in JWT but appears in emerging JOSE proposals.

### BACK-09: Active REST Fuzzing for Crypto Posture

**What "crypto fuzzing" means in this context (bounded scope):**

This is NOT generic API fuzzing (no injection, no parameter mutation). It is *crypto posture probing* — sending crafted requests to determine the API endpoint's cryptographic configuration. Specifically:

| Probe type | What it checks | Risk level |
|-----------|---------------|-----------|
| TLS downgrade probe | Send ClientHello advertising only SSLv3/TLS1.0/TLS1.1 to the API endpoint's host:port. Does the server accept? | LOW — same traffic sslyze already sends to port 443. New: applies to API endpoint URLs. |
| Weak cipher acceptance | Offer only RC4/3DES/EXPORT cipher suites. Does the server negotiate? | LOW — same as TLS scanner. New: targeted at JWT endpoint URLs. |
| `Strict-Transport-Security` header check | Is HSTS present on authenticated API responses? Max-age sufficient (>=31536000)? | ZERO traffic — header inspection on responses already received. |
| `Expect-CT` / `Public-Key-Pins` (deprecated check) | Informational only — flag if HPKP present (deprecated, conflict risk). | ZERO traffic — header inspection. |
| HTTP vs HTTPS credential transmission | Does the endpoint accept `Authorization: Bearer <token>` over plaintext HTTP? | LOW — single probe request, token is test-only or operator-provided. |
| Algorithm downgrade (JWT `alg: none` acceptance) | Send a request with a crafted JWT where `alg` is `none`. Does the API accept it? | MEDIUM — this is an active exploit probe, not passive. Must be explicitly opt-in. |

**Gate structure (mirrors nmap probe budget):**

```
--enable-fuzzing flag required (default: off)
    --> on first use: TTY prompt "Fuzzing sends crafted traffic to target systems.
        Confirm you have authorization to test [targets]? [y/N]:"
    --> non-TTY: stderr warning + auto-proceed (mirrors maybe_confirm_probe_budget)
--> per-target probe budget cap: default 50 probes (TLS + header checks per endpoint)
    --> --max-fuzzing-probes N override (CLI only, not in config)
```

**The `alg: none` probe is the sharpest edge:** It sends a crafted request that bypasses signature verification if the server is vulnerable. It is technically an exploit attempt. Recommendation: gate this probe behind a separate `--enable-none-alg-probe` flag in addition to `--enable-fuzzing`. Emit a CRITICAL finding if the server accepts it.

**Findings emitted by fuzzing:**

| Finding | Severity | Category |
|---------|---------|---------|
| API endpoint accepts SSLv3/TLS1.0 | HIGH | TLS-version weakness |
| API endpoint accepts RC4/3DES/EXPORT cipher | HIGH | Weak cipher |
| HSTS absent on authenticated API endpoint | MEDIUM | Transport security header |
| Bearer token transmitted over plaintext HTTP | CRITICAL | Credential exposure |
| API accepts `alg: none` JWT | CRITICAL | Auth bypass (opt-in probe only) |

**Safety expectations for consulting use against client networks:**
- Default off. Consultant must explicitly opt in per-run.
- Authorization check is the consultant's responsibility; QUIRK cannot verify it. The TTY prompt records that the operator confirmed.
- Probe budget cap prevents runaway scanning.
- Fuzzing findings carry a `source="active-fuzzing"` tag in the CBOM to distinguish them from passive findings — client CBOM must clearly show which components were confirmed by active probing.

### BACK-24: Code Signing Certificate Inventory

**What code-signing certs to discover:**

| Source | Discovery method | Availability |
|--------|-----------------|-------------|
| Sigstore/Cosign transparency log (Rekor) | Query `rekor.sigstore.dev` API for entries by artifact hash or repo name | PUBLIC API — no auth required |
| npm package signatures | Registry API `registry.npmjs.org/<pkg>` — `dist.signatures[]` field | PUBLIC — no auth |
| PyPI PGP signatures | `pypi.org/simple/<pkg>/` — `.asc` files (deprecated) or attestation API (PEP 740) | PUBLIC — no auth |
| GitHub release assets (`.sig`, `.asc`, `.pem` attachments) | GitHub API `repos/{owner}/{repo}/releases` | PUBLIC repos — no auth; private repos need BACK-64 |
| macOS notarization | Apple notarization service (requires Apple ID) | NOT agentless — skip |
| Windows Authenticode | PE binary inspection locally or via NuGet/Chocolatey API | MEDIUM complexity — requires binary download |
| Maven Central artifact signing | Maven Central API search | PUBLIC — no auth |

**Classification of code-signing certs:**

Use the existing `cryptography` library (already a core dep via sslyze/paramiko):
- Extract `cert.signature_hash_algorithm.name` → map to `_ALGORITHM_TABLE`
- Extract `cert.public_key()` type and size (RSA key size, EC curve)
- Check `not_valid_after` — expired signing cert is a MEDIUM finding (historical artifacts signed with it may be unverifiable)
- Check extended key usage — must include `codeSigning` OID (`1.3.6.1.5.5.7.3.3`)

**Findings:**

| Finding | Severity |
|---------|---------|
| Code signing cert uses RSA < 2048 bits | HIGH |
| Code signing cert uses SHA-1 signature hash | HIGH |
| Code signing cert uses RSA (any size) — quantum-vulnerable | MEDIUM (informational: all RSA is quantum-vulnerable, not an immediate risk) |
| Code signing cert expired | MEDIUM |
| No code signing evidence found for target repo/package | LOW (coverage gap advisory) |
| Sigstore/Cosign used with ECDSA P-256 | SAFE — informational, no finding |

**CBOM integration:** Emit `CryptoPrimitive.SIGNATURE` components with `protocol="CODESIGN"`, `service_detail` indicating the source (Sigstore/npm/PyPI/GitHub). This is a new protocol family requiring `classifier.py` entries and `builder.py` Pass-1 handling.

**Complexity note:** Supporting all signing surfaces is HIGH complexity. Recommend phasing: (1) Sigstore transparency log + npm signatures (public, low-effort) in v5.1; (2) Authenticode + Maven in v5.2 or backlog.

---

## Feature Prioritization Matrix

| Feature (BACK#) | Consulting Value | Implementation Cost | Priority | Phase order |
|----------------|-----------------|--------------------|---------|-----------| 
| BACK-64: Authenticated credential model | HIGH — nothing else works without it | MEDIUM — but security-review gated | P1 | Phase 93 — first |
| BACK-10: OpenAPI spec analysis | HIGH — passive, works on any engagement | LOW–MEDIUM — no credential dependency | P1 | Phase 94 — can parallel BACK-64 |
| BACK-11: Bearer token classify | HIGH — closes gap between JWKS and live token | LOW — BACK-64 enhances it but `--analyze-token` path is standalone | P1 | Phase 95 — after BACK-64 |
| BACK-09: Active fuzzing | HIGH for engagements where client authorizes active probing | HIGH — opt-in gating, probe budget, security review | P2 | Phase 96 — after BACK-64 and security review |
| BACK-24: Code signing (Sigstore + npm slice only) | MEDIUM — supply chain ask is growing but niche for current user base | HIGH — multiple source formats, new protocol family | P2 | Phase 97 — partially independent |

---

## MVP Definition for v5.1

### Build First (Required for Milestone)

- BACK-64: Ephemeral credential model — Bearer token, API key (header), HTTP Basic. `safe_str()` on all exception paths. Security-review gate as a Phase 93 deliverable.
- BACK-10: OpenAPI spec analysis — `securitySchemes` extraction, `servers[]` HTTP detection, unauthenticated endpoint flagging, CBOM `spec-origin` components. Local file + well-known URL auto-fetch.
- BACK-11: Bearer token decode and classify — `--analyze-token` path (standalone) + authenticated-scan capture path. `alg` + `exp` + quantum-safety. CBOM `JWT-TOKEN` components.

### Add After Core Works

- BACK-09: Active REST fuzzing — TLS downgrade + cipher acceptance + HSTS check. Gate: `--enable-fuzzing` + TTY confirm. `alg: none` probe behind separate sub-flag.
- BACK-24: Code signing inventory — Sigstore + npm slice only. Defer Authenticode/Maven.

### Defer to Backlog

- BACK-24 full surface (Authenticode, Maven, macOS notarization): complexity exceeds consulting value in v5.1 timeframe.
- OAuth2 client credentials token acquisition: conflicts with ephemeral-only credential decision.
- mTLS client cert injection: explicitly deferred in PROJECT.md.
- Authenticated scheduled scans: explicitly excluded from ephemeral credential model.

---

## Existing Integration Seams (Where New Code Attaches)

| New capability | Attaches to | How |
|---------------|-------------|-----|
| Credential injection | `quirk/config.py` — new `[credentials]` config section; `quirk/cli/` — new CLI flags parsed before `_run_jwt_phase` | Pass `credentials: CredentialsCfg` into `_run_jwt_phase` and new scanner phases |
| OpenAPI spec analysis | New `quirk/scanner/openapi_scanner.py` → `_wrapped_phase` in `run_scan.py` | Emits `CryptoEndpoint` with `protocol="OPENAPI-SPEC"` |
| Bearer token classify | `quirk/scanner/jwt_scanner.py` — extend `scan_jwt_endpoint` with `auth_token=` kwarg OR new `quirk/scanner/token_analyzer.py` | Emits `CryptoEndpoint` with `protocol="JWT-TOKEN"` |
| Active fuzzing | New `quirk/scanner/api_fuzzer.py` → `_wrapped_phase` in `run_scan.py` | Emits `CryptoEndpoint` with `protocol="API-FUZZ"`, `source="active-fuzzing"` |
| Code signing | New `quirk/scanner/codesign_scanner.py` → `_wrapped_phase` in `run_scan.py` | Emits `CryptoEndpoint` with `protocol="CODESIGN"` |
| CBOM Pass-1 | `quirk/cbom/builder.py` — add protocol handling for `OPENAPI-SPEC`, `JWT-TOKEN`, `API-FUZZ`, `CODESIGN` | Follows same `if ep.protocol == "X": ...` pattern as existing passes |
| CBOM Pass-2/3 skip-lists | `quirk/cbom/builder.py` — `MOTION_PLAINTEXT_PROTOCOLS` / `DAR_SKIP_PROTOCOLS` pattern | Add `API_SKIP_PROTOCOLS` frozenset for non-algorithm endpoint types |
| Scoring | `quirk/intelligence/scoring.py` — new `api_*` evidence counters or reuse `agility_high_impact_ratio` via `finding_severity_counts` | Simplest path: HIGH/CRITICAL API findings flow through existing `agility_high_impact_ratio`; new `api_weak_jwt_ratio` weight if a separate pillar is desired |
| Dashboard | `quirk/dashboard/api/routes/scan.py` + React — new `api_findings` field on `/api/scan/latest` Pydantic model | Mirrors `identity_findings`, `motion_findings` pattern |

---

## Chaos Lab Requirements

Each new scanner family needs a chaos lab profile for CI validation:

| Profile name | What it exercises |
|-------------|-----------------|
| `openapi-spec` | Flask/FastAPI container serving `/openapi.json` with `securitySchemes` declaring RS256 bearer + HTTP apiKey; one endpoint with no `security` |
| `jwt-weak` | Token endpoint returning JWTs signed with RS256/ES256; JWKS at `/.well-known/jwks.json` (already partially covered by existing `jwt` profile — verify coverage) |
| `api-fuzz` | TLS server accepting TLS 1.0, weak ciphers; HSTS absent; for fuzzing probe validation |
| `codesign` | Not a Docker service — use fixture files (sample X.509 certs with RSA-1024, SHA-1, and ECDSA P-256 extended key usage `codeSigning`) |

---

## Sources

- Direct code inspection: `quirk/scanner/jwt_scanner.py`, `quirk/intelligence/scoring.py`, `quirk/cbom/classifier.py`, `quirk/util/targets.py`, `run_scan.py`, `quirk/config.py`
- `.planning/ROADMAP.md` BACK-09, BACK-10, BACK-11, BACK-24, BACK-64 descriptions
- `.planning/HORIZON.md` Candidate A rationale
- `.planning/PROJECT.md` v5.1 milestone scoping and key decisions
- [Veracode API Scanning Authentication Methods](https://docs.veracode.com/r/API_Scanning_Authentication_Methods) — MEDIUM confidence (industry norm confirmation)
- [Swagger Bearer Authentication docs](https://swagger.io/docs/specification/v3_0/authentication/bearer-authentication/) — HIGH confidence (spec)
- [OpenAPI Security specification](https://learn.openapis.org/specification/security.html) — HIGH confidence (spec)
- [Trail of Bits: Building cryptographic agility into Sigstore](https://blog.trailofbits.com/2026/01/29/building-cryptographic-agility-into-sigstore/) — HIGH confidence (authoritative, 2026-01)
- [Venari Security: Post-Quantum JWT](https://www.venarisecurity.com/post-quantum-jwt-security/) — MEDIUM confidence (current analysis)
- [WuppieFuzz: REST API Fuzzing](https://arxiv.org/pdf/2512.15554) — MEDIUM confidence (academic, fuzzing scope reference)

---
*Feature research for: QU.I.R.K. v5.1 Authenticated Scanning + API Surface Depth*
*Researched: 2026-05-22*
