# Architecture Research — v5.1 Authenticated Scanning + API Surface Depth

**Domain:** Integration architecture for ephemeral credential model + API crypto analysis
**Researched:** 2026-05-22
**Confidence:** HIGH (direct codebase inspection; all integration points verified against live source)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           run_scan.py (orchestrator)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  _wrapped_   │  │  _wrapped_   │  │  _wrapped_   │  │  _wrapped_   │    │
│  │  phase(...)  │  │  phase(...)  │  │  phase(...)  │  │  phase(...)  │    │
│  │  jwt_scanner │  │  openapi_    │  │  codesign_   │  │  rest_fuzzer │    │
│  │  (extended)  │  │  scanner     │  │  scanner     │  │  (gated)     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                  │                  │            │
│  ┌──────┴─────────────────┴──────────────────┴──────────────────┴────────┐  │
│  │         CredentialContext (in-memory only, never persisted)            │  │
│  │         captured in lambda closure at each _wrapped_phase call site    │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │  List[CryptoEndpoint]
          ┌────────────▼──────────────────────────┐
          │         evidence.py / scoring.py        │
          │  _PROTOCOL_KEYS extended               │
          │  api_weak_alg_count, codesign_weak_count│
          │  agility_signals subscore extended      │
          └────────────┬──────────────────────────┘
                       │
          ┌────────────▼──────────────────────────┐
          │         cbom/builder.py                 │
          │  Pass-1: OPENAPI/CODE_SIGN/REST_FUZZ   │
          │  Pass-2/3: no skip-list changes needed  │
          └────────────┬──────────────────────────┘
                       │
          ┌────────────▼──────────────────────────┐
          │         SQLite (quirk.db)               │
          │  openapi_scan_json, codesign_scan_json  │
          │  NO credential data ever written        │
          └───────────────────────────────────────┘
```

---

## Q1 — Ephemeral Credential Model: Where It Lives and How It Flows

### Design Decision: `CredentialContext` Dataclass in `quirk/util/credentials.py`

The cleanest abstraction is a single module-level dataclass that is constructed
once at scan startup from CLI flags / environment variables / a one-time TTY prompt,
then threaded through `run_scan.py` as a plain object — never serialised, never
persisted, never written to SQLite, logs, CBOM, or error strings.

**New file:** `quirk/util/credentials.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CredentialContext:
    """In-memory-only credential holder for authenticated scan mode.

    Lifecycle:
      - Constructed once in run_scan.py from CLI args / env / prompt.
      - Passed as a parameter to every scanner phase that needs it.
      - Dropped at scan completion; never serialised.

    Supported schemes (BACK-64):
      bearer  -- Authorization: Bearer <token>
      api_key -- header/query param injection (header_name + value)
      basic   -- HTTP Basic (username + password)

    mTLS client certs deferred to a future milestone.
    """
    scheme: str = "none"               # "bearer" | "api_key" | "basic" | "none"
    bearer_token: Optional[str] = None
    api_key_header: Optional[str] = None   # e.g. "X-API-Key"
    api_key_query: Optional[str] = None    # e.g. "api_key"
    api_key_value: Optional[str] = None
    basic_username: Optional[str] = None
    basic_password: Optional[str] = None

    def as_headers(self) -> dict[str, str]:
        """Return a dict of headers for injection into authenticated requests."""
        if self.scheme == "bearer" and self.bearer_token:
            return {"Authorization": f"Bearer {self.bearer_token}"}
        if self.scheme == "api_key" and self.api_key_header and self.api_key_value:
            return {self.api_key_header: self.api_key_value}
        if self.scheme == "basic" and self.basic_username and self.basic_password:
            import base64
            encoded = base64.b64encode(
                f"{self.basic_username}:{self.basic_password}".encode()
            ).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {}

    def as_query_params(self) -> dict[str, str]:
        if self.scheme == "api_key" and self.api_key_query and self.api_key_value:
            return {self.api_key_query: self.api_key_value}
        return {}

    @property
    def is_active(self) -> bool:
        return self.scheme != "none"
```

### Where Construction Happens

`run_scan.py` resolves credentials immediately after config loading, before any
scanner phase runs. Priority order (highest wins):

1. CLI flags: `--auth-bearer`, `--auth-api-key-header`, `--auth-api-key-value`,
   `--auth-api-key-query`, `--auth-basic`, `--auth-prompt`
2. Env vars: `QUIRK_AUTH_BEARER`, `QUIRK_AUTH_API_KEY_VALUE`, etc.
3. Interactive TTY prompt (only when `--auth-prompt` flag given)
4. None (default — unauthenticated mode)

The result is a `CredentialContext` instance. If no credential input is present,
`ctx.is_active == False` and no authenticated scanner phase runs. This is the
zero-impact path — existing unauthenticated scans are completely unaffected.

### How It Threads Through `_wrapped_phase()`

The current `_wrapped_phase` signature:

```python
def _wrapped_phase(run_stats, phase_name, scanner_label, fn, error_endpoints, logger)
```

The `fn` argument is already a zero-argument callable (a lambda or `functools.partial`
created at the call site). Credentials are captured into the closure at that point:

```python
# run_scan.py call site — credentials captured in closure, NOT passed to _wrapped_phase
cred_ctx = _build_credential_context(args)   # constructed once above main scan loop

api_endpoints = _wrapped_phase(
    run_stats, "api_authenticated", "api-scanner",
    lambda: scan_api_authenticated(
        targets=cfg.connectors.api_targets,
        cred_ctx=cred_ctx,          # captured in closure
        timeout=cfg.scan.timeouts.jwt_seconds,
        logger=logger,
    ),
    error_endpoints, logger,
)
```

This design means:
- `_wrapped_phase()` never sees credential data — its existing signature is unchanged.
- The `safe_str()` scrubbing helper in `_wrapped_phase`'s exception handler never
  touches credential values (they are only in the inner `fn` closure).
- `scan_error` written to SQLite is the output of `safe_str(exc)` — which already
  strips Authorization headers via `_SENSITIVE_PATTERNS` in `quirk/util/safe_exc.py`.
  The existing pattern covers bearer and basic schemes. The api_key scheme needs a
  corresponding pattern added (keyed on the header-value shape, not the header name,
  since the header name is configurable).

### Memory Lifetime and Leak Surface

| Surface | Risk | Mitigation |
|---------|------|-----------|
| SQLite `scan_error` column | Exception message could include cred | `safe_str()` strips; extend pattern for api_key value shapes |
| CBOM `service_detail` / component names | Scanner emits these | `service_detail` contract is algorithm/protocol label only; scanners never interpolate cred data |
| Log messages | URL + algorithm are fine; cred must not appear | Convention: log target URLs and algorithm IDs, never headers or tokens |
| Run stats JSON | Persisted as `run_stats_json` | Credential context never enters `run_stats`; it is local to the lambda |
| Scheduled scan re-execution | Authenticated runs must not be schedulable | `quirk schedule add` rejects configs where `enable_authenticated_mode: true` with `QRK-SCHED-AUTH-001` error |

---

## Q2 — Authenticated Mode: Extend Existing JWT Scanner vs. New Module

**Decision: Extend the existing scanner for token-layer work; new sibling modules for OpenAPI/REST/codesign.**

### What `jwt_scanner.py` Currently Does

`scan_jwt_endpoint()` probes `/.well-known/jwks.json`, `/oauth/jwks`, and
`/.well-known/openid-configuration` without credentials, returns one
`CryptoEndpoint(protocol="JWT")` per public key found. Passive discovery.

### Module Boundary Map

| Work | Module | Status |
|------|--------|--------|
| JWKS passive discovery | `quirk/scanner/jwt_scanner.py` | Existing — no change |
| Bearer token decode/classify | `quirk/scanner/jwt_scanner.py` | Extend — add `scan_bearer_token()` |
| OpenAPI spec analysis | `quirk/scanner/openapi_scanner.py` | New |
| Authenticated REST calls | Both scanners consume `CredentialContext` via closure | Context injected in closure |
| Active REST fuzzing | `quirk/scanner/rest_fuzzer.py` | New — gated separately |
| Code-signing cert inventory | `quirk/scanner/codesign_scanner.py` | New |

### Extended `jwt_scanner.py` Surface

Add one new public function alongside `scan_jwt_targets()`:

```python
def scan_bearer_token(
    token: str,
    *,
    logger=None,
) -> CryptoEndpoint:
    """Decode and classify a bearer JWT without network I/O.

    Returns one CryptoEndpoint(protocol="JWT") with:
      - cert_pubkey_alg = header["alg"] (e.g. "RS256", "ES256")
      - cert_pubkey_size derived from alg
      - service_detail = "bearer-token-analysis"
      - jwt_scan_json = JSON with {alg, exp, iat, is_expired, key_size}
    """
```

This carries zero credential-leak risk — the token is the subject of analysis,
not a secret to protect; the caller owns any scrubbing needed before passing it.

---

## Q3 — CBOM Pass-1/2/3 Integration and Scoring Touch-Points

### New Protocol Labels

| Protocol Label | Scanner | CBOM Pass-1 Action |
|---------------|---------|-------------------|
| `JWT` | jwt_scanner (existing) | Already registered |
| `OPENAPI` | openapi_scanner | AlgorithmProperties per security scheme/operation |
| `CODE_SIGN` | codesign_scanner | CertificateProperties per cert |
| `REST_FUZZ` | rest_fuzzer | AlgorithmProperties per observed cipher |

### CBOM Pass-1 Extension

The builder's Pass-1 loop iterates `endpoint_list` and calls `classify_algorithm()`
on `cert_pubkey_alg`. This path already handles `JWT` correctly. New protocols:

- `OPENAPI` endpoints: `cert_pubkey_alg` carries the extracted security scheme alg.
  A helper `_extract_openapi_alg(ep)` mirrors the existing
  `_extract_algo_from_rule_id()` for semgrep. Alg strings like `RS256`, `ES256`
  pass directly to `classify_algorithm()`.
- `CODE_SIGN` endpoints: `cert_pubkey_alg` carries the cert's public key algorithm.
  Same classifier path. Subject/issuer populate `CertificateProperties` in Pass-2.
- `REST_FUZZ` endpoints: cipher suite from the probed TLS response goes in
  `cipher_suite`; existing `_KEX_MAP` / `_ENC_MAP` / `_AUTH_MAP` decomposition
  already handles it.

### CBOM Pass-2/3 Skip-List Extension

`MOTION_PLAINTEXT_PROTOCOLS` and `DAR_SKIP_PROTOCOLS` in `builder.py` do not
need changes. `OPENAPI`, `CODE_SIGN`, and `REST_FUZZ` all carry genuine algorithm
data and participate in Pass-1 normally.

### New SQLite Columns (Additive Only)

```
openapi_scan_json   TEXT   -- OpenAPI spec analysis result per endpoint
codesign_scan_json  TEXT   -- Code-signing cert details
```

`jwt_scan_json` already exists and handles bearer token analysis output
(the `scan_bearer_token()` result stores there). No new column for `REST_FUZZ` —
the TLS cipher/version data from fuzzing probes goes into the existing
`tls_version`, `cipher_suite`, and `tls_capabilities_json` fields.

### Scoring: Extend `agility_signals` Subscore, Not a New Subscore

**Decision: Augment the existing `agility_signals` subscore. Do NOT add a 7th subscore.**

The 6-pillar formula is `total_score = int(round(sum_of_six / 1.5))`, mapping
0–150 to 0–100. A 7th subscore changes the denominator and breaks the Phase 86
fix math, the `SCORE_WEIGHTS` invariant test, all report renderers, and all six
dashboard `ScoreGauge` components. The API surface features are fundamentally
agility signals — algorithm choices in tokens, specs, and code-signing certs.
They belong in `agility_signals`.

**New evidence counters in `evidence.py`:**

```python
api_weak_alg_count = 0              # JWT/OpenAPI endpoints with SHA-1 or RSA<2048
api_no_expiry_count = 0             # bearer tokens with no exp claim
api_fuzzing_weak_cipher_count = 0   # REST fuzzing: weak cipher in TLS response
codesign_weak_count = 0             # code-signing certs with RSA<2048 or SHA-1
```

**New `_PROTOCOL_KEYS` entries:** `"OPENAPI"`, `"CODE_SIGN"`, `"REST_FUZZ"` appended
to the existing tuple (mirrors Phase 77 D-10 pattern that added `CONTAINER`,
`SOURCE`, `AWS`, `AZURE`, `GCP`, `CLOUD_SQL`).

**New SCORE_WEIGHTS entries (additive; invariant test updated per phase):**

```python
"agility_api_weak_alg_ratio":       6.0,
"agility_api_no_expiry_ratio":      4.0,
"agility_codesign_weak_ratio":      6.0,
"agility_fuzz_weak_cipher_ratio":   4.0,
```

New sum: `283.0 + 6.0 + 4.0 + 6.0 + 4.0 = 303.0`.

The `agility_` prefix means `PROFILE_MULTIPLIERS` applies automatically — no
changes to the multiplier dict needed.

**Backward compatibility:** All four new evidence keys default to 0 when absent.
Historical scans re-rendered through the new scorer receive no impact from these
counters. This is the same pattern as `data_in_motion` D-12 backward compat.

---

## Q4 — Active REST Fuzzing Gate: Where It Sits

### Pattern: Mirror the nmap Probe-Budget Gate, With One Tightening

The nmap gate (Phase 47) in `run_scan.py`:

1. CLI opt-in: `--discovery nmap`
2. Config flag: `connectors.enable_nmap: true`
3. Budget: `maybe_confirm_probe_budget(targets, ports, threshold=10_000)`
   - TTY: print projection + require y/N
   - non-TTY: warn stderr + auto-proceed

The REST fuzzing gate mirrors this exactly except at step 3:

1. CLI opt-in: `--enable-fuzzing`
2. Config flag: `connectors.enable_rest_fuzzing: bool = False`
3. Budget: `maybe_confirm_fuzz_budget(targets, endpoint_count, threshold=500)`
   - TTY: display endpoint count + explicit authorization prompt
     ("I confirm I am authorized to send crafted traffic to these targets")
     requires literal `yes` (not `y`) to proceed
   - **non-TTY: HARD ABORT** — fuzzing is never auto-approved in headless mode

The non-TTY hard abort is a deliberate tightening relative to nmap. Fuzzing crafts
active traffic that could trigger IDS alerts or cause state mutations — it must
never run silently in CI or scheduled contexts.

**New function in `quirk/util/targets.py`:**

```python
def maybe_confirm_fuzz_budget(
    targets: list,
    endpoint_count: int,
    threshold: int = 500,
    is_tty: Optional[bool] = None,
    prompt_fn: Callable = input,
) -> bool:
    """Active-fuzzing authorization gate.

    Returns True only if endpoint_count <= threshold AND explicit 'yes' confirmed.
    endpoint_count > threshold: always False (too large a surface).
    Non-TTY mode always returns False — fuzzing must not run headless.
    """
```

**`ConnectorsCfg` additions (additive fields):**

```python
enable_rest_fuzzing: bool = False
rest_fuzzing_budget: int = 500
rest_fuzzing_targets: list = field(default_factory=list)
```

**`TimeoutsCfg` addition:**

```python
rest_fuzzing_seconds: int = 15
```

**`run_scan.py` call site:**

```python
if getattr(cfg.connectors, "enable_rest_fuzzing", False):
    from quirk.util.targets import maybe_confirm_fuzz_budget
    if not maybe_confirm_fuzz_budget(
        targets=fuzz_targets,
        endpoint_count=len(fuzz_targets),
        threshold=cfg.connectors.rest_fuzzing_budget,
    ):
        logger.warning("REST fuzzing aborted — authorization not confirmed.")
    else:
        fuzz_endpoints = _wrapped_phase(
            run_stats, "rest_fuzzing", "rest-fuzzer",
            lambda: fuzz_rest_targets(
                targets=fuzz_targets,
                cred_ctx=cred_ctx,
                timeout=cfg.scan.timeouts.rest_fuzzing_seconds,
                logger=logger,
            ),
            error_endpoints, logger,
        )
```

**Optional extras:** `[api] = ["httpx>=0.27"]`. OpenAPI parsing uses stdlib
json/yaml (PyYAML is already a transitive dep). No new pip dependencies for
OpenAPI analysis or bearer token decode.

---

## Q5 — Dependency-Ordered Build Sequence

### Phase 93 — Credential Infrastructure (Foundational)

Must ship first. Every other phase consumes it.

- `quirk/util/credentials.py`: `CredentialContext` dataclass + `build_credential_context(args, env)` factory.
- `run_scan.py`: credential construction at startup; all `--auth-*` CLI flags; `QUIRK_AUTH_*` env vars.
- `ConnectorsCfg`: `enable_authenticated_mode: bool = False`.
- `safe_exc.py`: extend `_SENSITIVE_PATTERNS` to cover api_key header value shapes.
- `quirk schedule add`: reject configs where `enable_authenticated_mode: true`
  with `QRK-SCHED-AUTH-001` error code.
- Security review gate: credential lifetime in memory + leak surface audit
  (this is the HORIZON-required security review for the credential subsystem).
- Tests: credential construction from flags/env; scrubbing patterns; schedule
  rejection; `as_headers()` for all three schemes; `is_active` predicate.

### Phase 94 — Bearer Token Interception + OpenAPI Analysis (BACK-11, BACK-10)

Depends on Phase 93.

- `jwt_scanner.py`: `scan_bearer_token()` (decode-only, no network I/O).
- `quirk/scanner/openapi_scanner.py`: new; reads local spec or authenticated URL
  from `cfg.connectors.openapi_spec_path`; emits `CryptoEndpoint(protocol="OPENAPI")`
  per security scheme; uses `cred_ctx` for authenticated spec fetch if URL.
- `evidence.py`: `"OPENAPI"` in `_PROTOCOL_KEYS`; `api_weak_alg_count`,
  `api_no_expiry_count` counters.
- `scoring.py`: `agility_api_weak_alg_ratio`, `agility_api_no_expiry_ratio` in
  `SCORE_WEIGHTS`; new entries in `agility_impacts` list.
- `models.py`: `openapi_scan_json TEXT` column (additive).
- `builder.py`: Pass-1 handling for `OPENAPI` protocol; `_extract_openapi_alg(ep)` helper.
- `pyproject.toml`: `[api]` extras group with `httpx>=0.27`.
- `tests/test_score_weights_invariant.py`: update expected sum (283.0 + 10.0 = 293.0 after Phase 94).
- Chaos lab: extend existing jwt chaos lab profile with an OpenAPI spec endpoint.

### Phase 95 — Code-Signing Certificate Inventory (BACK-24)

Depends on Phase 93. Independent of Phase 94 (can run in parallel if agent capacity allows).

- `quirk/scanner/codesign_scanner.py`: new; discovers code-signing certs from
  LDAP `userCertificate` with CodeSigning EKU, or configured PEM/DER paths;
  emits `CryptoEndpoint(protocol="CODE_SIGN")`.
- `evidence.py`: `"CODE_SIGN"` in `_PROTOCOL_KEYS`; `codesign_weak_count` counter.
- `scoring.py`: `agility_codesign_weak_ratio` weight; `agility_impacts` extended.
- `models.py`: `codesign_scan_json TEXT` column (additive).
- `builder.py`: Pass-1 handling for `CODE_SIGN` (CertificateProperties path).
- `ConnectorsCfg`: `enable_codesign: bool = False`, `codesign_targets: list`.
- `pyproject.toml`: reuses `[api]` extras (httpx already there); Sigstore client deferred.
- `tests/test_score_weights_invariant.py`: update expected sum again (+6.0).

### Phase 96 — Active REST Fuzzing Gate (BACK-09)

Depends on Phase 93 (credentials) and Phase 94 (OpenAPI — for endpoint discovery).
Fuzzing probes endpoints discovered by OpenAPI analysis; ship Phase 94 first.

- `quirk/scanner/rest_fuzzer.py`: new; takes endpoint URLs, injects `CredentialContext`
  headers, sends crafted requests with weak-cipher preference headers, records
  `tls_version` + `cipher_suite` from response.
- `quirk/util/targets.py`: `maybe_confirm_fuzz_budget()` (TTY-hard-only gate).
- `ConnectorsCfg`: `enable_rest_fuzzing`, `rest_fuzzing_budget`, `rest_fuzzing_targets`.
- `TimeoutsCfg`: `rest_fuzzing_seconds`.
- `evidence.py`: `"REST_FUZZ"` in `_PROTOCOL_KEYS`; `api_fuzzing_weak_cipher_count`.
- `scoring.py`: `agility_fuzz_weak_cipher_ratio` weight; `agility_impacts` extended.
- `run_scan.py`: gate call site (opt-in flag + `maybe_confirm_fuzz_budget` + hard
  non-TTY abort + `_wrapped_phase` wrapper).
- `tests/test_score_weights_invariant.py`: final update (sum = 303.0).
- Chaos lab: extend an existing profile (e.g., jwt) to respond to crafted
  cipher-preference requests for fuzzing validation.

---

## Component Responsibilities

| Component | Responsibility | New vs Modified |
|-----------|---------------|----------------|
| `quirk/util/credentials.py` | In-memory credential holder + factory + header injection | New |
| `quirk/scanner/jwt_scanner.py` | JWKS passive + bearer token decode | Modified (add `scan_bearer_token`) |
| `quirk/scanner/openapi_scanner.py` | OpenAPI spec parsing, security scheme extraction | New |
| `quirk/scanner/codesign_scanner.py` | Code-signing cert discovery and classification | New |
| `quirk/scanner/rest_fuzzer.py` | Active REST fuzzing behind confirmation gate | New |
| `quirk/util/targets.py` | `maybe_confirm_fuzz_budget()` guard | Modified (add function) |
| `quirk/util/safe_exc.py` | `_SENSITIVE_PATTERNS` extended for api_key value shapes | Modified |
| `quirk/config.py` (ConnectorsCfg) | `enable_authenticated_mode`, fuzzing flags, codesign flags | Modified (additive fields) |
| `quirk/config.py` (TimeoutsCfg) | `rest_fuzzing_seconds` | Modified (additive field) |
| `quirk/models.py` | `openapi_scan_json`, `codesign_scan_json` columns | Modified (additive) |
| `quirk/intelligence/evidence.py` | New protocol keys + api/codesign counters | Modified (additive) |
| `quirk/intelligence/scoring.py` | New `agility_*` weights + impacts | Modified (additive) |
| `quirk/cbom/builder.py` | Pass-1 for OPENAPI/CODE_SIGN/REST_FUZZ protocols | Modified (additive) |
| `run_scan.py` | Credential construction; scanner call sites; fuzzing gate | Modified |
| `quirk/dashboard/api/schemas.py` | `api_findings`, `codesign_findings` on response model | Modified |

---

## Data Flow: Authenticated Scan

```
CLI args / env vars / TTY prompt
    |
build_credential_context(args, env)  -->  CredentialContext (in-memory only)
    |
run_scan.py scan loop
    |-- _wrapped_phase("jwt_bearer", lambda: scan_bearer_token(token=cred_ctx.bearer_token))
    |-- _wrapped_phase("openapi", lambda: scan_openapi_targets(..., cred_ctx=cred_ctx))
    |-- _wrapped_phase("codesign", lambda: scan_codesign_targets(..., cred_ctx=cred_ctx))
    `-- [if enable_rest_fuzzing AND confirmed]
        _wrapped_phase("rest_fuzzing", lambda: fuzz_rest_targets(..., cred_ctx=cred_ctx))
    |
List[CryptoEndpoint]  (no credential data in any field)
    |
evidence.build_evidence_summary()  -->  api_weak_alg_count, codesign_weak_count, ...
    |
scoring.compute_readiness_score()  -->  agility_signals subscore (extended)
    |
cbom.build_cbom()  -->  OPENAPI/CODE_SIGN algorithm components in CycloneDX CBOM
    |
SQLite persist  (openapi_scan_json, codesign_scan_json additive columns)
    |
FastAPI /api/scan/latest  -->  React dashboard (api_findings, codesign_findings)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Credential Fields on `ConnectorsCfg`

**What people do:** Add `bearer_token`, `api_key` fields to `ConnectorsCfg` so
they load from the YAML config file.

**Why it's wrong:** Config files are typically committed to version control or
stored on disk. `ConnectorsCfg` is serialized to run stats JSON. This is a hard
constraint violation for the ephemeral model.

**Do this instead:** Credentials live only in `CredentialContext`, constructed at
runtime from CLI flags / env vars / TTY prompt. `ConnectorsCfg` carries only
`enable_authenticated_mode: bool` — no secret data.

### Anti-Pattern 2: Passing `CredentialContext` Through `_wrapped_phase`

**What people do:** Add a `cred_ctx` parameter to `_wrapped_phase()`.

**Why it's wrong:** This puts credential material inside `_wrapped_phase()`'s
exception handler scope, which calls `safe_str(exc)`. Even with scrubbing, the
call stack carries credentials through a generic error-handling path.

**Do this instead:** Capture `cred_ctx` in the lambda closure at the call site.
`_wrapped_phase()` never sees credential data; its signature is unchanged.

### Anti-Pattern 3: Writing Credential Contents to `scan_error` or `service_detail`

**What people do:** Log `f"Authenticated request to {url} with token {token} failed: {exc}"`.

**Why it's wrong:** `scan_error` is written to SQLite. `service_detail` appears in
CBOM component names and reports. Both are long-lived.

**Do this instead:** Log only the URL and the exception class name via `safe_str(exc)`.
Token values are never interpolated into any logged or persisted string.

### Anti-Pattern 4: Scheduling Authenticated Scans

**What people do:** Add authenticated credentials to `scheduled_scans` config so
they run on a cron.

**Why it's wrong:** Scheduled scans persist their configuration to the `scheduled_scans`
SQLite table. Credentials stored there become a stored-secret surface QUIRK deliberately
avoids becoming.

**Do this instead:** `quirk schedule add` rejects any config where
`enable_authenticated_mode: true` with `QRK-SCHED-AUTH-001` error code.
Authenticated runs are explicitly interactive / per-invocation.

### Anti-Pattern 5: A New 7th Subscore for API/OpenAPI/CodeSign

**What people do:** Add `api_surface` as a 7th subscore alongside the existing six.

**Why it's wrong:** The formula `total_score = int(round(sum_of_six / 1.5))` assumes
a 0–150 maximum. A 7th subscore changes this to 0–175 and requires updating the
denominator, the `SCORE_WEIGHTS` invariant test, all report renderers, all dashboard
`ScoreGauge` components, and the Phase 86 fix math. High blast radius, no user-facing
benefit (API signals are agility signals).

**Do this instead:** Fold new API/codesign signals into the existing `agility_signals`
subscore via the `agility_` SCORE_WEIGHTS prefix. Profile multipliers apply
automatically; no renderer changes needed.

---

## Integration Points Summary

### Schema Touch-Points (Additive Only)

| Column | Table | Phase |
|--------|-------|-------|
| `openapi_scan_json TEXT` | `crypto_endpoints` | 94 |
| `codesign_scan_json TEXT` | `crypto_endpoints` | 95 |

No existing column is modified.

### SCORE_WEIGHTS Invariant

Current sum: **283.0** (post-v5.0 PQC-03 agility bonus).
After Phase 94: `283.0 + 6.0 + 4.0 = 293.0`
After Phase 95: `293.0 + 6.0 = 299.0`
After Phase 96: `299.0 + 4.0 = 303.0`

`tests/test_score_weights_invariant.py` must be updated once per phase that adds
weights. CI fails loudly on mismatch.

### `_PROTOCOL_KEYS` in `evidence.py`

Current tuple ends with `"CLOUD_SQL"`. Append: `"OPENAPI"`, `"CODE_SIGN"`, `"REST_FUZZ"`.
Pattern established by Phase 77 D-10 (which added `CONTAINER`, `SOURCE`, `AWS`,
`AZURE`, `GCP`, `CLOUD_SQL`).

### CBOM `DAR_SKIP_PROTOCOLS` / `MOTION_PLAINTEXT_PROTOCOLS`

No changes. `OPENAPI`, `CODE_SIGN`, `REST_FUZZ` are not in either skip-list.

### FastAPI `/api/scan/latest` Response

New optional fields on the Pydantic schema:

```python
api_findings: List[ApiFinding] = []
codesign_findings: List[CodeSignFinding] = []
```

Mirrors the existing `identity_findings`, `motion_findings`, `dar_findings` pattern.

---

## Sources

- Direct inspection: `quirk/scanner/jwt_scanner.py`, `run_scan.py`, `quirk/models.py`,
  `quirk/config.py`, `quirk/intelligence/evidence.py`, `quirk/intelligence/scoring.py`,
  `quirk/cbom/builder.py`, `quirk/util/targets.py`, `quirk/util/safe_exc.py`
  (verified 2026-05-22 against live codebase)
- Key Decisions in `.planning/PROJECT.md`: `safe_str()` pattern (Phase 59),
  `_wrapped_phase` pattern (Phase 41), `maybe_confirm_probe_budget` pattern (Phase 47),
  additive-only schema constraint, 6-pillar scoring formula (Phase 86 D-01)
- v5.0 milestone context: SCORE_WEIGHTS sum 283.0; `pqc_hybrid_endpoint_count` as
  precedent for new agility-bonus counter; Phase 77 D-10 as precedent for
  `_PROTOCOL_KEYS` extension

---

*Architecture research for: QU.I.R.K. v5.1 Authenticated Scanning + API Surface Depth*
*Researched: 2026-05-22*
