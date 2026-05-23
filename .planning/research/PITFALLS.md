# Pitfalls Research

**Domain:** Authenticated scanning + active fuzzing + API surface depth additions to an agentless live-network crypto-inventory scanner (v5.1)
**Researched:** 2026-05-22
**Confidence:** HIGH for credential-leakage and JWT/alg-confusion vectors (multiple authoritative sources + codebase read); MEDIUM for fuzzing guardrails and spec-parsing SSRF (WebSearch + official advisories); MEDIUM for code-signing classification scope (real-incident evidence, no formal academic source)

---

## Critical Pitfalls

### Pitfall 1: Python string immutability makes credential zeroization a false promise

**What goes wrong:**
A developer stores a captured bearer token or Basic-auth password in a Python `str`, uses it for the authenticated scan call, then sets the variable to `None` or deletes it, believing the secret is gone. It is not. Python strings are immutable and interned; the runtime may hold multiple copies at unpredictable addresses. The garbage collector frees the *reference* but does not zero the backing memory. The raw bytes survive in the process heap until that page happens to be reused — which may never occur during the process lifetime on a long-running dashboard session. A memory dump (core dump, swap, `/proc/<pid>/mem` read) recovers the credential verbatim.

The `bytearray` type is mutable and can be overwritten in-place, but the moment a credential arrives as a CLI argument or environment variable it is already a `str` (Python's `sys.argv`, `os.environ`, and `argparse` all return immutable strings). Converting to `bytearray` copies the bytes, leaving the original `str` still in memory alongside the mutable copy. The `mlock()` syscall prevents the page from swapping but does nothing about the original immutable copy at a different address.

**Why it happens:**
Developers familiar with C/Rust credential handling apply the same mental model to Python. The language semantics do not support it. Python's string interning optimization may additionally create copies inside the interpreter for frequently-used strings.

**How to avoid:**
1. **Accept credentials only as `bytearray` or Pydantic `SecretStr` from the point of entry.** If the credential arrives as a CLI flag, use `getpass.getpass()` (which never passes through `sys.argv`) or read from stdin into `bytearray` immediately.
2. **Overwrite the `bytearray` in a `finally` block** after use: `cred_bytes[:] = b'\x00' * len(cred_bytes)`.
3. **Never convert a credential `bytearray` to `str` for any reason** — not for logging, not for HTTP headers (use `bytes` or encode inline at the callsite). All HTTP client libraries (`requests`, `httpx`) accept `bytes` for auth headers.
4. **Document explicitly that Python in-memory-only is best-effort, not provable.** The security-review gate deliverable must state this honestly: the implementation minimises credential lifetime and prevents persistence, but cannot guarantee the Python heap is zeroed.
5. **Environment variable path:** `os.environ` entries are `str`. If the user passes a credential via env var, read it into a `bytearray`, then delete the env var key (`del os.environ['QUIRK_API_KEY']`) immediately so subprocess forks do not inherit it.
6. **No `mlock` dependency required** for the v5.1 consulting use case — ephemeral interactive sessions on a local machine have a narrower threat model than a server daemon. The meaningful wins are (a) never logging the credential and (b) never writing it to SQLite.

**Warning signs:**
- Any function that accepts a credential and has parameter type `str` rather than `bytearray` or `SecretStr`.
- Any `except` block that catches a broad exception after a credential has been used — the `safe_str()` helper (Phase 59) already scrubs `exc` bodies, but a new code path that re-raises or logs `repr(locals())` could expose the credential from the frame.
- `credential` appearing as a key in any dict that gets JSON-serialised for the CBOM or dashboard API response.

**Phase to address:**
Phase 93 (credential model foundation) — define the credential container type, the `bytearray` zeroing pattern in `finally`, and the env-var deletion. The security-review gate (likely Phase 95 or 96) must audit every callsite.

---

### Pitfall 2: Credential leakage into the eleven stored/rendered surfaces

**What goes wrong:**
Even with correct in-memory handling, a credential escapes in one of many stored or rendered surfaces. The existing `safe_str()` scrubber (Phase 59, LEAK-01/02/03) was designed for exception messages from the existing unauthenticated scanners. The credential subsystem creates entirely new leakage vectors that are not covered by the current AST gate.

Exhaustive leakage surface map for v5.1:

| Surface | Vector | Risk |
|---------|--------|------|
| SQLite `scan_error` column | `_wrapped_phase()` writes `safe_str(exc)` — but if the exception message *contains* the credential string, `safe_str()` only strips stack frames, not the value itself | HIGH |
| SQLite `api_scan_json` / `cbom_json` columns | Builder serialises the auth context for audit trail; if auth headers end up in the captured request dict they persist forever | HIGH |
| CBOM JSON/XML output files | Any `evidence` or `service_detail` field populated from authenticated request context | HIGH |
| Dashboard `/api/scan/latest` JSON response | `api_scan_json` deserialised and forwarded; includes any fields set during authenticated scan | HIGH |
| Dashboard PDF export | HTML report rendered from the same JSON; PDF renderer has no additional scrubbing | MEDIUM |
| CLI HTML report | Same data path as PDF | MEDIUM |
| Structured logs / `logging.debug()` calls | `httpx`/`requests` debug logging emits full request headers including `Authorization:` | HIGH |
| Python traceback printed to stderr | An unhandled exception in the auth flow prints `locals()` in some debug modes | MEDIUM |
| `quirk.db` WAL file | SQLite write-ahead log is a separate file; a crash mid-write leaves partial rows in the WAL | LOW |
| Process swap / core dump | Covered in Pitfall 1 above | LOW (consulting threat model) |
| Scheduler `scheduled_scans` table | Scheduled scans deliberately do not accept credentials (v5.1 decision); but if a developer adds a `credential_hint` column "just to show context" it becomes a persistent secret store | HIGH (future regression risk) |

**Why it happens:**
Each surface was hardened independently during v4.8. Adding a new data type (credential) to an existing data pipeline does not automatically inherit the existing scrubbing — the scrubber must be explicitly extended to know what credential field names look like.

**How to avoid:**
1. **Extend `safe_str()` with a credential-pattern scrubber.** After the credential object is created, register its value (or a hash prefix) in a thread-local or call-local scrub set. Any string routed through `safe_str()` is filtered against this set. Clear the scrub set in the `finally` block alongside the `bytearray` zeroing.
2. **Add credential field names to the AST gate's deny list.** The existing gate (Phase 59 LEAK-03) blocks raw exception writes to `scan_error`. Extend it to fail CI on any `json.dumps()` or `model_dump()` call in a scan module that includes a field named `api_key`, `token`, `password`, `authorization`, `bearer`, or `credential`.
3. **Set `logging.disable(logging.DEBUG)` or strip `Authorization` headers from `httpx`/`requests` event hooks** during authenticated scans. Passing `event_hooks={'request': [_strip_auth_header]}` to the `httpx.Client` prevents the library's own debug logging from writing the header to stdout/stderr.
4. **CBOM builder: add a `NEVER_SERIALISE` field-name set** checked before any field is written to a component's `properties` list.
5. **Enforce that no authenticated scan writes the auth context to `api_scan_json`.** The column stores discovered-API metadata (endpoints, algorithms), not scanner configuration. A code review checklist item for the security gate: does `api_scan_json` in any branch contain a field from the auth context?

**Warning signs:**
- `httpx` or `requests` log level set to `DEBUG` anywhere in the scan pipeline.
- A new ORM column added whose name contains `credential`, `key`, `token`, `password`, or `secret`.
- `model_dump()` called on the credential object without a `exclude=` filter.
- Test fixtures that use real-looking tokens (e.g., `eyJ...`) — these should be synthetic garbage strings to prevent accidental real-token commits.

**Phase to address:**
Phase 93 (credential model) owns the `safe_str()` extension and AST gate extension. Phase 95 or the dedicated security-review gate phase audits all eleven surfaces against a checklist derived from this table.

---

### Pitfall 3: Active REST fuzzing causes a client outage or IDS lockout — without exceeding the opt-in flag

**What goes wrong:**
The fuzzer is gated behind `--fuzz` opt-in (mirroring nmap's `--discover` flag). The consultant enables it on a client's *staging* environment. The staging environment shares a WAF with production (common CDN/reverse-proxy topology). The WAF detects the scan signatures and blocks the consulting firm's IP. Production traffic through the same WAF begins failing. Alternatively: the fuzzer sends a `DELETE /users/1` request that the staging API forwards to a shared database with production data — staging is thin-shell only.

Separate failure mode: a `POST` request body crafted with a boundary-value integer (`-1`, `2^31`) triggers a server-side exception that cascades to a shared queue, causing a partial production outage.

**Why it happens:**
The opt-in flag establishes authorization. It does not establish safety. Developers conflate "the user said yes" with "it is safe to do". Active fuzzing against live systems is inherently risky regardless of explicit opt-in.

**How to avoid:**
The following guardrails are all mandatory — the opt-in flag is a prerequisite, not a substitute:

1. **Method allowlist, not blocklist.** Default to `GET` only. Add `POST` only with a second explicit flag: `--fuzz-write-methods`. Never send `DELETE`, `PUT` (full replace), or `PATCH` without a third explicit flag: `--fuzz-destructive`. The burden of enabling destructive methods must be higher than enabling fuzzing itself.
2. **Request budget cap with hard ceiling.** Mirror the nmap probe-budget pattern: `--fuzz-max-requests N` (default 50, hard ceiling 500). Enforce in the fuzzer core, not as a suggestion. Once the budget is exhausted, the fuzzer stops and reports "budget exhausted" in the findings — it does not prompt to continue.
3. **Rate limit at the fuzzer level.** Default: 2 requests/second. The WAF rate-limit is typically 10–100 req/s; staying well below prevents lockout. Configurable via `--fuzz-rate-limit`.
4. **Authorization confirmation prompt.** Before the first fuzz request is sent, print a summary of: target host, method set, estimated request count, rate, and a warning that this will generate active traffic. Require the user to type `CONFIRM` (not just press Enter). Log the confirmation with timestamp to the scan record.
5. **Scope enforcement via target allowlist.** The fuzzer must only send requests to hosts/IPs in the configured `targets` list. If `$ref` resolution (Pitfall 5) discovers a `server` URL in the OpenAPI spec that is *not* in the target list, it must not be fuzzed without explicit user override.
6. **Idempotency-first endpoint selection.** Parse the OpenAPI spec's `x-idempotency` extension or infer from method: prefer `GET` > `HEAD` > `OPTIONS`. Only escalate to `POST` if explicitly enabled.
7. **Response monitoring for cascading failure signals.** If more than 3 consecutive requests return 5xx, pause and alert. If a request returns 429 (Too Many Requests), respect `Retry-After` and reduce rate automatically.

**Warning signs:**
- Fuzzer logic that sends `DELETE` or `PUT` on first pass without a method allowlist check.
- A single `--fuzz` flag that enables all methods and all request depths simultaneously.
- No request counter or budget enforcement in the fuzzer core.
- Fuzzer ignores HTTP 429 responses.

**Phase to address:**
The fuzzer phase (likely Phase 96 or 97) must implement all seven guardrails before any integration test against the chaos lab. The security-review gate must include a checklist item for each guardrail. The chaos lab fuzzing profile must NOT be a production-replica topology — use an isolated container with no shared state.

---

### Pitfall 4: OpenAPI `$ref` external URL resolution is an SSRF vector against the scanner host

**What goes wrong:**
A client hands QU.I.R.K. an OpenAPI spec file (or a URL to one). The spec contains:

```yaml
components:
  schemas:
    Token:
      $ref: 'http://169.254.169.254/latest/meta-data/iam/security-credentials/role'
```

If the spec parser resolves external `$ref` URLs by fetching them (the default behaviour of most OpenAPI resolver libraries), the scanner's own host makes an HTTP request to the cloud metadata endpoint. If the scanner is running inside an EC2 instance or GCP VM (e.g., a consultant running QU.I.R.K. on a cloud bastion), this leaks the instance's IAM credentials to the spec file author.

Separately: a spec with deeply nested `$ref` cycles (`A -> B -> C -> A`) causes infinite recursion in the resolver, consuming unbounded memory or stack depth — a denial-of-service against the scanner process.

**Why it happens:**
OpenAPI spec parsers (`prance`, `openapi-spec-validator`, `jsonschema-ref-parser`) resolve `$ref` by default. The feature is legitimate for bundling multi-file specs. The danger is that "resolve" means "fetch" for remote refs. No standard parser ships with SSRF protection enabled by default.

**How to avoid:**
1. **Resolve only local (same-file) `$ref` entries.** When loading a spec, disable all HTTP/HTTPS and `file://` ref resolution. For `prance` (the most capable Python OpenAPI parser): use `ResolvingParser` with a custom `resolve_types={}` that excludes `RESOLVE_HTTP` and `RESOLVE_FILES`. For `openapi-spec-validator` (v0.7+): pass `resolver_manager` with restricted resolvers.
2. **Implement a depth limit on `$ref` resolution.** Even local refs can cycle. Set `max_depth=10` and raise `SpecParsingError` if exceeded.
3. **Size-gate the spec before parsing.** Reject specs larger than 10 MB before any parsing begins. A legitimate OpenAPI spec for even the most complex enterprise API rarely exceeds 2 MB.
4. **Validate the spec source URL against the target allowlist** before fetching if the user passes a URL rather than a local file. Only fetch from hosts in the configured `targets` list.
5. **Parse in a separate thread with a timeout.** Even with the above, a pathological spec may cause slow parse. Wrap in `concurrent.futures.ThreadPoolExecutor` with a 30-second timeout and terminate on expiry.

**Warning signs:**
- `prance.ResolvingParser(spec_url)` called with no custom resolver options.
- No file size check before spec parsing.
- Parser library version below `prance>=23.6` or `openapi-spec-validator>=0.7` (older versions have fewer resolver controls).
- Tests that pass spec fixtures via HTTP URLs (implies the parser is fetching by default in tests).

**Phase to address:**
OpenAPI spec analysis phase (likely Phase 94). The restricted resolver must be implemented on day 1 of the spec parser, not retrofitted. The security-review gate must include a test fixture containing a `$ref` pointing to `http://169.254.169.254/` and assert it raises `SpecParsingError` rather than making a network request.

---

### Pitfall 5: Treating the JWT `alg` header as the actual algorithm — enabling alg-confusion misclassification

**What goes wrong:**
QU.I.R.K. intercepts a bearer token during an authenticated scan call and reports it in the CBOM with its algorithm. The algorithm classification logic reads `token_header['alg']` and uses that value to determine quantum-safety, key size, and severity. An attacker (or misconfigured server) has set `"alg": "HS256"` on a token that is actually validated server-side with RS256. QU.I.R.K. reports `HMAC-SHA256 — symmetric, not quantum-vulnerable` when the actual cryptographic posture is `RSA-2048 — quantum-vulnerable`. The CBOM is wrong; the client gets a false pass on their API layer.

Worse: `"alg": "none"` is a valid JWT header value that some older servers accept. QU.I.R.K. would classify this as a CRITICAL finding (unsigned token) — but only if it checks the `alg` field, which is the header as *declared*, not as *enforced*. The CBOM should reflect what is declared (which is itself a finding if `none`) but must not conflate declared algorithm with enforced algorithm.

**Why it happens:**
JWT analysis tools universally read the header because it is the only programmatically accessible signal without server-side access. The conceptual error is treating "declared algorithm" as "enforced algorithm" in the CBOM component description.

**How to avoid:**
1. **Label CBOM components with `declared_alg` and a note that enforcement is unverifiable without server-side access.** Never write `algorithm: HS256` as if it is an established fact — write `declared_algorithm: HS256 (unverified)`.
2. **Flag `alg: none` and `alg: None` (case variants) as CRITICAL regardless of other claims.** These values indicate either a broken server or an attacker-modified token.
3. **For the fuzzing phase: attempt sending a token with `alg: none` (signature stripped) to the target and observe whether the server accepts it.** If it does, that is a CRITICAL finding `JWT-ALG-NONE-ACCEPTED`. This is active probing — gate it behind `--fuzz`.
4. **Flag RS256/RS512 tokens as potentially misclassified if the JWKS endpoint is not reachable or returns a symmetric key.** Cross-reference JWKS where available (the existing JWKS scanner already fetches `/jwks.json`).
5. **For algorithm confusion detection (active, `--fuzz` only):** craft a token with `alg` changed from RS256 to HS256, signed with the server's public key as the HMAC secret, and send it. If the server accepts it, emit `JWT-ALG-CONFUSION` CRITICAL. This is a known attack (Portswigger Web Security Academy documented vector); performing it against a client's live system requires explicit authorization — put it behind a dedicated `--fuzz-jwt-alg-confusion` flag.

**Warning signs:**
- Any code path that constructs a CBOM `AlgorithmComponent` from `token['header']['alg']` without adding a `(declared, unverified)` qualifier.
- A CBOM component for a JWT that has `quantum_safe: true` derived solely from `alg: EdDSA` in the header — EdDSA declared does not mean EdDSA enforced.
- Test fixtures for JWT analysis that use tokens with `alg: HS256` but are tested against a server that uses RS256 (this mismatch should be a test case, not an oversight).

**Phase to address:**
Bearer token interception phase (likely Phase 94 or 95). The `declared_alg` labelling convention must be established at the data model level before any CBOM components are built from JWT analysis. The security-review gate must test the `alg: none` detection and confirm the CBOM field accurately reflects declarative vs. enforced status.

---

### Pitfall 6: Captured bearer tokens logged or stored verbatim during interception

**What goes wrong:**
The bearer token interception feature captures the `Authorization: Bearer <token>` header from an authenticated scan call to analyse it. A developer adds `logger.debug(f"Captured token: {token}")` to aid debugging during development. This line ships to production. Every authenticated scan now writes the client's bearer token to the debug log, which may be forwarded to a SIEM, stored in Splunk, or included in a support bundle sent to QU.I.R.K.'s developers. This is a credential breach affecting the client's production API.

Separate risk: the token is stored in `api_scan_json` as part of the "request evidence" for the CBOM. The CBOM is exported and handed to the client. The client's CBOM deliverable now contains their own bearer token in cleartext — which may then be emailed, uploaded to a ticketing system, or printed.

**Why it happens:**
During development of the interception feature, logging the full token is the easiest way to verify capture. The log line is not removed before shipping. Storing the token in `api_scan_json` seems like "evidence" — matching the pattern of other scanners that store raw probe data.

**How to avoid:**
1. **Log only a scrubbed form: first 8 characters + `...` + last 4 characters.** `safe_token_repr(token)` — add this as a named function to the existing `safe_str()` module so it is reusable and searchable.
2. **Never store the raw token value in any SQLite column, CBOM field, or API response.** Store the *analysis result*: algorithm, key size, expiry, claims structure — not the token string itself.
3. **Extend the AST CI gate (Phase 59 LEAK-03)** to also flag any string variable named `token`, `bearer`, or `jwt` being passed to `logger.debug()`, `logger.info()`, `json.dumps()`, or `scan_error` write paths.
4. **Add the token to the in-call scrub set** (see Pitfall 2) so even if it escapes into an exception message it is redacted before `safe_str()` writes it to the DB.
5. **CBOM output test:** add a pytest assertion that no exported CBOM (JSON or XML) from a test authenticated scan contains a string matching the JWT regex `eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*`. This is a regression gate — if a CBOM ever contains a raw token, CI fails.

**Warning signs:**
- `logger.debug()` calls anywhere in the token interception or bearer analysis code path that reference the raw token variable.
- `api_scan_json` containing the substring `Authorization` or `Bearer` in a test output fixture.
- CBOM fixtures in `examples/cbom/` that contain JWT-shaped strings.

**Phase to address:**
Bearer token interception phase. The `safe_token_repr()` helper and AST gate extension must be implemented as the first task of that phase, before any token capture logic is written. The security-review gate verifies the CBOM JWT-regex assertion is in CI.

---

## Moderate Pitfalls

### Pitfall 7: Code-signing certificate discovery scope creep and false classification

**What goes wrong:**
The code-signing cert inventory feature discovers `extendedKeyUsage: codeSigning` OIDs in certificates. Two failure modes:

**Scope creep:** The scanner, given a broad target list, starts inspecting certificate stores on network file shares, CI/CD artifact servers, and package registries that were not in scope for the engagement. The client's scope-of-work covers their public API endpoints; the scanner reaches into their internal build infrastructure.

**False classification:** A certificate with `extendedKeyUsage: codeSigning, emailProtection` is classified as a code-signing cert and scored against quantum-readiness criteria. It is actually a developer S/MIME cert that happens to also carry the code-signing OID. The CBOM emits `RSA-2048 code-signing: QUANTUM-VULNERABLE` for what is a low-risk personal email cert, inflating the finding severity.

Additionally: a CI/CD server may present a code-signing cert over TLS for its web UI. The TLS scanner already captures the leaf cert. Emitting a *second* CBOM component for the same cert (once from TLS scanner, once from code-signing scanner) creates duplicates in the CBOM and inflates the finding count.

**How to avoid:**
1. **Scope enforcement: only inspect certs encountered during the normal scan flow** (TLS handshakes, JWKS endpoints, SAML metadata). Do not add new network probe targets specifically to find code-signing certs.
2. **De-duplicate CBOM components by cert fingerprint.** Before adding a code-signing cert component, check whether a component with the same SHA-256 fingerprint was already emitted by the TLS or SAML scanner. Reuse the existing component and add `code_signing: true` as a property rather than creating a duplicate.
3. **Classify by primary OID, not presence of OID.** A cert whose `extendedKeyUsage` lists `codeSigning` as the *first* OID is a code-signing cert. A cert that lists `emailProtection` first and `codeSigning` second is an email cert that can also sign code — classify it as email-class, note the secondary usage.
4. **Restrict to endpoints in the configured target list.** The code-signing scanner must not discover and scan hosts outside `cfg.targets`.

**Warning signs:**
- Code-signing scanner that opens new TCP connections to hosts not in the original scan target list.
- CBOM output with duplicate `serialNumber` values across components.
- Finding count that jumps dramatically after enabling code-signing inventory (suggests duplicate counting).

**Phase to address:**
Code-signing inventory phase. De-duplication logic and scope enforcement must be in the initial design; retrofitting de-duplication to the CBOM builder after the fact is difficult (Phase 42 OBS-1 was exactly this problem — 5 profiles emitting zero algo components because skip-lists were built post-hoc).

---

### Pitfall 8: Over-trusting OpenAPI-declared security schemes vs. actual enforcement

**What goes wrong:**
The spec analysis phase reads an OpenAPI spec and reports `securitySchemes: BearerAuth (JWT, HS256)`. QU.I.R.K. emits a CBOM component: `API authentication: JWT HS256 — symmetric, not quantum-vulnerable`. The actual server enforces no authentication on that endpoint (the `security:` field is empty in the path-level override, which the spec scanner missed). Or the server enforces OAuth2 PKCE, not a raw JWT, and the `bearerFormat: JWT` hint in the spec is aspirational documentation written before the implementation was changed.

**How to avoid:**
1. **Distinguish spec-declared vs. observed security in all CBOM fields.** A component derived from static spec analysis carries `evidence_source: openapi_spec_declared`. A component derived from an actual authenticated scan call carries `evidence_source: observed_request`. Never merge these without noting the discrepancy.
2. **Cross-reference spec-declared schemes with the bearer token interception results.** If the spec declares `HS256` but the intercepted token header shows `RS256`, emit a finding: `API-SCHEME-MISMATCH` — the spec is out of date.
3. **Empty path-level `security: []` overrides the top-level scheme.** The spec parser must check both the global `security` field and the per-path/per-operation `security` override. Flag unprotected paths as a finding even if the top-level scheme looks correct.

**Phase to address:**
OpenAPI spec analysis phase. Build the `evidence_source` field into the data model from day one.

---

### Pitfall 9: Authenticated scan accidentally persists credentials via the scheduler

**What goes wrong:**
The scheduler feature (Phase 63) stores `scheduled_scans` rows with target configuration. A developer adds "convenience" fields to store the last-used credential so the scheduled scan can re-authenticate on the next run — reasoning that the user already opted in. This converts QU.I.R.K. from an ephemeral credential handler into a stored-secret surface. The v5.1 design decision explicitly prohibits this.

A subtler variant: the `scan_checkpoints` table (Phase 67 resumable scans) stores mid-scan state. If a resumable authenticated scan stores the credential in the checkpoint row, it persists to disk until the checkpoint is cleaned up.

**How to avoid:**
1. **Add a CI test that asserts no `scheduled_scans` or `scan_checkpoints` column name contains `key`, `token`, `password`, `secret`, or `credential`.** This is a schema-level gate, not a runtime check.
2. **In the dashboard `ScanJob` model, explicitly exclude credential fields from serialisation.** If the form ever grows a credential input, ensure `model_config = ConfigDict(exclude={'api_key', 'token', 'password'})` is set before any ORM write.
3. **Document the decision in the code.** Add a `# v5.1: ephemeral-only — credentials are NEVER stored` comment at the top of the credential module and reference it in the scheduler module's docstring.

**Phase to address:**
Phase 93 (credential model foundation). The schema-level CI gate must be part of the first phase, not deferred. The security-review gate must verify the assertion is green.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Accept credential as `str` for simplicity | Faster to wire into existing HTTP client code | Credential lives in Python heap indefinitely; cannot be zeroed | Never — use `bytearray` or `SecretStr` from the point of entry |
| Log full bearer token during development | Easy debugging of token capture logic | Credential breach if log line ships to production | Never in any code path that touches production output |
| Resolve all `$ref` in OpenAPI spec by default | Handles multi-file specs without custom configuration | SSRF vector against scanner host; DoS via recursive refs | Never — always use a restricted resolver |
| Single `--fuzz` flag enables all HTTP methods | Simpler UX | Accidental `DELETE` or `PUT` against client production data | Never — must be a layered flag system |
| Store "analysis context" including raw token in `api_scan_json` | Preserves full evidence for audit | Raw credential in SQLite, CBOM, and API responses | Never — store analysis results only, not the credential itself |
| Re-use the nmap probe-budget pattern for fuzzing without adapting it | Familiar pattern | Nmap budget is per-host probe count; fuzzing budget is per-endpoint request count — different semantics, different defaults needed | Only if the semantics are explicitly adapted for REST context |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `httpx` authenticated requests | Default `httpx` debug logging emits `Authorization:` header at DEBUG level | Pass `event_hooks={'request': [_strip_auth_header]}` and keep log level at INFO or above during scans |
| OpenAPI `prance` parser | `prance.ResolvingParser(url)` fetches remote `$ref` by default | Use `prance.ResolvingParser(url, resolve_types={})` with all remote resolution disabled |
| JWT `PyJWT` library | `jwt.decode(token, key, algorithms=["HS256", "RS256"])` allows algorithm confusion if both are in the list | For classification only (no verification), use `jwt.decode(token, options={"verify_signature": False})` and separately classify the `alg` header — but label the result as `declared_alg` |
| `getpass.getpass()` | Returns a `str` — the zeroization problem applies immediately | Transfer to `bytearray` before use: `cred = bytearray(getpass.getpass().encode('utf-8'))` |
| HTTP Basic auth in `httpx` | `httpx.BasicAuth(user, password)` accepts `str` — copies made internally by httpx | Use `httpx.BasicAuth(user, bytes(cred_bytearray))` and zero `cred_bytearray` after the request; accept that httpx's internal copy is outside your control |
| OpenAPI spec size validation | Checking `len(spec_str)` after reading the file into memory | Gate on `os.path.getsize()` *before* opening the file; never read a file larger than 10 MB into a Python string |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Classifying JWT `alg` header as enforced algorithm | False-pass finding for an API that is actually using a weaker algorithm than declared | Label all JWT analysis results as `declared_alg (unverified)`; cross-reference JWKS |
| Fuzz requests sent to spec-declared `servers` URLs without scope check | Active traffic sent to out-of-scope hosts (legal exposure, client outage) | Intersect spec `servers` list with configured `targets` before any fuzz request |
| Bearer token stored in CBOM `properties` | Client's production API credential in a deliverable file | CBOM JWT-regex CI regression gate; store analysis metadata only |
| Unauthenticated scheduled scan accidentally inherits credential from prior interactive scan via shared process state | Credential lives beyond its intended lifetime | Ensure credential is zeroed and removed from all thread-locals before the scan function returns |
| `alg: none` classified as "unauthenticated" rather than CRITICAL | Severity underreported | Hardcode `alg: none` (all case variants) as CRITICAL `JWT-UNSIGNED` finding regardless of other spec context |
| Code-signing cert scanner adding targets beyond the configured scope | Scope creep; legal exposure | Restrict all new connection attempts to `cfg.targets`; no speculative host discovery in code-signing phase |

---

## "Looks Done But Isn't" Checklist

- [ ] **Credential zeroing:** `bytearray` is overwritten in a `finally` block — verify the finally runs even on `KeyboardInterrupt` (`BaseException`, not `Exception`)
- [ ] **CBOM JWT regex gate:** CI assertion that no CBOM fixture contains a JWT-shaped string — verify the regex covers both compact (`eyJ...`) and URL-safe base64 variants
- [ ] **Fuzzer budget enforcement:** request counter is decremented *before* the request is sent, not after — verify a mid-scan kill signal does not allow more than `max_requests + 1` requests
- [ ] **Spec parser SSRF gate:** test fixture with `$ref: 'http://169.254.169.254/latest/meta-data/'` asserts `SpecParsingError`, not a network timeout — verify by running with network access blocked
- [ ] **Scheduler schema gate:** CI assertion on column names — verify it runs on schema migration, not just at test time
- [ ] **AST gate coverage:** extended deny list includes `bearer`, `api_key`, `authorization`, `token` variable names — verify with a synthetic failing test case in the test suite
- [ ] **Authorization confirmation prompt:** requires typing `CONFIRM` — verify it is not bypassable by stdin redirection (e.g., `echo CONFIRM | quirk scan --fuzz`)
- [ ] **`alg: none` detection:** case-insensitive check — verify `None`, `NonE`, `NONE` all trigger CRITICAL
- [ ] **Code-signing de-duplication:** CBOM component count does not increase when running with and without `--inventory-code-signing` on the same target that already has TLS certs captured

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Credential found in SQLite scan record | HIGH | Delete the scan record row; vacuum the SQLite file; rotate the credential immediately; notify client |
| Credential found in exported CBOM file | HIGH | Recall the deliverable; rotate the credential; audit where the file was sent (email, upload) |
| Fuzzer causes client WAF lockout | MEDIUM | Immediately stop the scanner; contact client WAF team with timestamp and source IP; provide request logs for WAF rule whitelisting |
| Fuzzer sends DELETE to a live endpoint | HIGH | Immediately stop; assess whether the DELETE affected production data; escalate to client incident response |
| SSRF via spec `$ref` against scanner host | MEDIUM | If scanner runs on a cloud instance: rotate the instance IAM role credentials immediately; audit CloudTrail for the metadata endpoint calls; patch the resolver before next use |
| Alg-confusion misclassification in CBOM deliverable | LOW | Issue a corrected CBOM; add `declared_alg` label to all JWT components; re-score the API pillar |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Python string zeroization limits | Phase 93 — credential model definition | Security-review gate: code review of `finally` blocks + documentation of best-effort guarantee |
| Credential leakage across 11 surfaces | Phase 93 + security-review gate | AST gate extended to cover new field names; manual checklist review at security gate |
| Active fuzzing outage / scope | Fuzzing phase (est. Phase 96–97) | Chaos lab test with WAF-rate-limit simulation; method allowlist unit tests |
| OpenAPI `$ref` SSRF | Spec analysis phase (est. Phase 94) | pytest fixture with internal `$ref` URL asserting `SpecParsingError` |
| JWT alg-confusion misclassification | Bearer token phase (est. Phase 94–95) | pytest with RS256 token re-declared as HS256; assert `declared_alg (unverified)` label |
| Bearer token in logs/CBOM | Bearer token phase | CBOM JWT-regex CI gate; AST gate covering `token` variable logging |
| Code-signing scope creep + duplicates | Code-signing phase (est. Phase 95) | CBOM de-duplication test; scan target scope assertion |
| Spec-declared vs. observed security mismatch | Spec analysis phase | `API-SCHEME-MISMATCH` finding test with mismatched spec vs. intercepted token |
| Credential in scheduler/checkpoint tables | Phase 93 | Schema-level CI assertion on column names |

---

## Sources

- [Clearing Memory in Python — Sjoerd Langkemper](https://www.sjoerdlangkemper.nl/2016/06/09/clearing-memory-in-python/) — definitive explanation of why Python string zeroization is fundamentally limited
- [zeroize-python — radumarias/zeroize-python](https://github.com/radumarias/zeroize-python) — `bytearray` + mlock approach; confirms mlock works on pages (two vars may share a page)
- [JWT Algorithm Confusion Attacks — PortSwigger Web Security Academy](https://portswigger.net/web-security/jwt/algorithm-confusion) — authoritative mechanics of RS256→HS256 swap attack
- [JWT Attacks — PortSwigger Web Security Academy](https://portswigger.net/web-security/jwt) — `alg: none` variants (None, NonE, NONE) documented
- [SSRF via OpenAPI `$ref` — mcp-from-openapi DailyCVE](https://dailycve.com/mcp-from-openapi-ssrf-and-local-file-read-via-dereferencing-no-cve-critical/) — real-world `$ref` SSRF via `json-schema-ref-parser` with no resolver restrictions
- [SSRF in swagger-ui — CVE-2018-25031 (Snyk)](https://security.snyk.io/vuln/SNYK-JS-SWAGGERUI-2314885) — established SSRF vector in OpenAPI tooling
- [SSRF + Path Traversal in FastMCP OpenAPI Provider — GHSA-vv7q-7jx5-f767](https://github.com/PrefectHQ/fastmcp/security/advisories/GHSA-vv7q-7jx5-f767) — 2026 advisory confirming the vector is current
- [Pydantic SecretStr — Python secrets leakage prevention](https://blog.gitguardian.com/how-to-handle-secrets-in-python/) — `SecretStr` pattern and `safe_str`-equivalent approaches
- [RESTler stateful REST fuzzer — Microsoft](https://github.com/microsoft/restler-fuzzer) — "Fuzz mode may cause outages if poorly implemented"; confirms aggressive mode risk
- [Scope creep in pentesting — nflo.tech](https://nflo.tech/knowledge-base/scope-creep-in-pentesting-projects/) — authorization scope enforcement practices
- [DigiCert code-signing false-positive incident — AirlockDigital](https://www.airlockdigital.com/airlock-blog/digicert-incident-and-microsoft-defender-false-positive-what-happened-and-what-it-means/) — real-world code-signing cert classification false-positive at scale
- [Certified evil: signed malicious binaries — Red Canary](https://redcanary.com/blog/threat-detection/code-signing-certificates/) — signing cert classification heuristics and pitfalls
- v4.8 Phase 59 codebase audit (LEAK-01/02/03) — existing `safe_str()` implementation and AST gate pattern; this research extends those patterns to the v5.1 credential and token surfaces

---
*Pitfalls research for: authenticated scanning + active fuzzing + API surface depth (v5.1 additions to QU.I.R.K.)*
*Researched: 2026-05-22*
