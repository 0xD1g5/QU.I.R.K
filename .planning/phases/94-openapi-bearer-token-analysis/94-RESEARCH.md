# Phase 94: OpenAPI & Bearer Token Analysis — Research

**Researched:** 2026-05-23
**Domain:** JWT/bearer-token analysis, OpenAPI spec parsing, SSRF hardening, CBOM classification, scoring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### `--analyze-token` command UX
- Input forms: positional token arg + `@file` reference + stdin (reuses Phase 93 `@file` model).
- Output: human-readable by default; `--json` flag for machine-readable output.
- DB persistence: standalone analyzer writes nothing to the scan DB — token is never persisted.
- `alg:none` (case-insensitive: none/None/NONE/NonE) flagged CRITICAL; command exits non-zero on a CRITICAL finding to gate CI.

#### OpenAPI spec analysis
- Spec source: `--openapi-spec <file|url>` CLI flag AND an `openapi:` config block.
- URL fetch only when the URL is within configured scan-target scope (SPEC-02); out-of-scope URL rejected before any network request.
- Findings mapping: emit as `CryptoEndpoint` rows (protocol `OpenAPI`) into the existing findings table — no new findings surface.
- Size gate: 10 MB hard cap checked BEFORE parse; oversized → `SpecParsingError`.
- `$ref` resolution is local-only; an internal-network `$ref` raises `SpecParsingError` rather than making an outbound request (SPEC-03 SSRF; CI fixture test).
- Validator: lenient parse-what-we-can with graceful degradation; validate structure, not strict spec compliance.

#### Bearer-token CBOM classification (TOKEN-02)
- Token source: only the operator-supplied `--auth-bearer` credential from Phase 93 (passive; no sniffing).
- CBOM label: exactly `declared_algorithm (unverified)` — never treated as enforced.
- Quantum-safety classification reuses existing JWT / `quirk/util/weak_crypto.py` alg-classification tables.

#### Scoring & packaging
- API spec + token findings feed `agility_signals` subscore; SCORE_WEIGHTS walks +10.0 → 293.0.
- `[api]` extras contains `openapi-spec-validator` only; `schemathesis` added in Phase 96 (excluded from `[all]`).
- New CI guard test mirrors `tests/test_install_all_excludes_impacket.py`, asserting `pip install quirk[all]` does not pull `schemathesis`.

### Claude's Discretion
- Module placement, exact report layout, and internal helper structure.

### Deferred Ideas (OUT OF SCOPE)
- Active REST fuzzing (`schemathesis`) → Phase 96.
- Sniffing/classifying bearer tokens observed in scan responses.
- mTLS client-cert analysis → v5.2.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SPEC-01 | Analyze an OpenAPI/Swagger spec from a local file to inventory declared API crypto posture (security schemes, plaintext `servers`, unauthenticated endpoints) | `openapi-spec-validator` 0.9.0 parses YAML/JSON; YAML via PyYAML (already a core dep); security-scheme extraction from spec dict |
| SPEC-02 | Analyze a spec fetched from a URL only when that URL is within configured scan-target scope | `validate_external_url()` already handles this pattern; scope-check against `cfg.targets` before any request |
| SPEC-03 | Spec parsing hardened against `$ref` SSRF and oversized-spec DoS | Pre-scan `$ref` values before calling `validate()`; size-gate on raw bytes before `yaml.safe_load` |
| TOKEN-01 | Decode and classify a bearer/JWT token via standalone `--analyze-token` command | `jwt.get_unverified_header()` + `jwt.decode(options={"verify_signature": False, "verify_exp": False})` — both confirmed working in PyJWT 2.12.1 already installed |
| TOKEN-02 | Bearer tokens from authenticated scan classified into CBOM with `declared_algorithm (unverified)` label | New `CryptoEndpoint(protocol="BEARER_TOKEN", cert_pubkey_alg=alg, service_detail="declared_algorithm (unverified)")` row fed to `build_cbom()` Pass 1 |
| TOKEN-03 | `alg:none` (any case variant) flagged CRITICAL | `header["alg"].lower() == "none"` check; `severity="CRITICAL"` on endpoint + non-zero exit |
| SCORE-01 (partial) | API/token findings contribute to `agility_signals` subscore; SCORE_WEIGHTS +10.0 → 293.0 | Add 2 new weight entries to `SCORE_WEIGHTS`; update invariant test expected sum 283.0 → 293.0 |
| PKG-01 | `[api]` extras group created; schemathesis excluded from `[all]`; CI guard test | Mirror `test_install_all_excludes_impacket.py` pattern; add `api = ["openapi-spec-validator>=0.9.0"]` to `pyproject.toml` |
</phase_requirements>

---

## Summary

Phase 94 adds two passive-analysis capabilities onto the credential infrastructure from Phase 93: (1) a standalone `quirk analyze-token` subcommand that decodes any JWT/bearer token and reports its algorithm, key-size, expiry, quantum-safety, and `alg:none` status; and (2) an `--openapi-spec` flag that parses a local-file (or scope-gated-URL) OpenAPI/Swagger spec to inventory declared crypto posture (security schemes, plaintext server URLs, unauthenticated endpoints). Bearer tokens supplied via `--auth-bearer` during an authenticated scan are also classified into the CBOM with a `declared_algorithm (unverified)` label.

All required building blocks are already present in the codebase. `PyJWT 2.12.1` (already a core dep) provides `jwt.get_unverified_header()` and signature-skip decode. `quirk/cbom/classifier.py` already maps every standard JWT algorithm (RS256, ES256, HS256, PS256, EdDSA, `none`) to quantum-safety levels. `quirk/util/url_allowlist.py::validate_external_url()` already blocks metadata-IPs and private ranges. The critical new external dependency is `openapi-spec-validator>=0.9.0` (pip-confirmed `[OK]` by slopcheck), but its default behavior resolves remote `$ref` values via network requests — the SSRF guard MUST pre-scan all `$ref` values in the raw spec dict and raise `SpecParsingError` on any non-`#`-prefixed ref before calling `validate()`.

The scoring +10.0 increment requires adding 2 new agility-subscore weight entries to `SCORE_WEIGHTS` (e.g. `agility_weak_jwt_alg_ratio` and `agility_openapi_plaintext_ratio`) and bumping the invariant test expected sum from 283.0 to 293.0 with count 37 → 39.

**Primary recommendation:** Implement in 3 waves: (1) token analyzer + CBOM classification + SCORE_WEIGHTS bump; (2) OpenAPI spec parser with SSRF/DoS hardening; (3) `[api]` extras + CI guard test.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| JWT decode and classification | CLI / `quirk/cli/analyze_token_cmd.py` | `quirk/cbom/classifier.py` (algorithm lookup) | Passive analysis — no network, no DB; belongs in a dedicated cli module |
| Bearer-token CBOM classification | CBOM builder (`quirk/cbom/builder.py` Pass 1) | `quirk/auth/credentials.py` (token source) | Build-time classification of an already-collected credential; existing Pass-1 pattern |
| OpenAPI spec loading + SSRF guard | `quirk/scanner/openapi_scanner.py` | `quirk/util/url_allowlist.py` (scope gate + $ref guard) | Scanner tier owns network-fetch decisions; url_allowlist is the shared guard |
| OpenAPI crypto-posture inventory | `quirk/scanner/openapi_scanner.py` | `quirk/models.py::CryptoEndpoint` (row shape) | Findings surface via existing protocol-tagged CryptoEndpoint rows |
| `analyze-token` subcommand routing | `run_scan.py` (subcommand intercept pattern) | `quirk/cli/analyze_token_cmd.py` | Consistent with `init`, `serve`, `compliance`, `db`, `errors` intercepts |
| SCORE_WEIGHTS +10.0 | `quirk/intelligence/scoring.py` | `tests/test_score_weights_invariant.py` | agility_signals subscore owns API posture signals |
| `[api]` extras + schemathesis CI guard | `pyproject.toml` | `tests/test_install_all_excludes_schemathesis.py` | Mirrors impacket exclusion pattern |

---

## Standard Stack

### Core (no new deps for token analysis)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyJWT | `>=2.12.0` (already installed, 2.12.1 confirmed) | Unverified JWT header decode + claims decode | Core dep; `get_unverified_header()` + `decode(options={"verify_signature": False})` confirmed working |
| `quirk/cbom/classifier.py` | project code | JWT algorithm → quantum-safety mapping | Already maps RS256/ES256/HS256/PS256/EdDSA/`none` — no additions needed |
| `quirk/util/url_allowlist.py` | project code | Scope gate (SPEC-02) + $ref SSRF guard (SPEC-03) | Existing validator: blocks metadata IPs always, blocks private/loopback unless allow_internal |

[VERIFIED: codebase inspection]

### New External Dependency

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `openapi-spec-validator` | `>=0.9.0` (0.9.0 latest, confirmed via pip) | OpenAPI 2.0/3.0/3.1 spec structural validation | Official validator from OpenAPI Initiative ecosystem; slopcheck `[OK]` |

[VERIFIED: pip index versions]

### Transitive Deps Introduced by `openapi-spec-validator` 0.9.0

| Package | Already Present? | Note |
|---------|-----------------|------|
| `jsonschema` | Yes (4.26.0 in venv after install; was 4.25.1 per STATE.md) | Upgraded minor version — `pip check` reports no conflicts |
| `jsonschema-path` 0.5.0 | No — new | Introduces `SchemaPath`, `UrllibHandler` |
| `openapi-schema-validator` 0.9.0 | No — new | Structural schema validation |
| `lazy-object-proxy` 1.12.0 | No — new | Proxy library |
| `pydantic-settings` 2.14.1 | No — new | Settings management (required by openapi-spec-validator) |
| `pathable` 0.6.0 | No — new | Path-like object library |

[VERIFIED: `pip show openapi-spec-validator` in project .venv after install]

**Key concern resolved:** `schemathesis` is NOT a transitive dep of `openapi-spec-validator`. [VERIFIED: `pip show schemathesis` returns "not found" in .venv after install]

**jsonschema version note:** `openapi-spec-validator` 0.9.0 caused `jsonschema` to upgrade from 4.25.1 → 4.26.0 in the venv. STATE.md noted "verify jsonschema-path transitive dep installs cleanly alongside existing jsonschema 4.25.1" — the minor bump to 4.26.0 is forward-compatible and `pip check` reports no conflicts. Pin as `jsonschema-path>=0.5.0` and let pip resolve. [VERIFIED: `pip check` output]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `openapi-spec-validator` | `prance` (another ref-resolver) | prance has complex bundling behavior and is less actively maintained; `openapi-spec-validator` is the de facto standard |
| Pre-scan $refs + call `validate()` | Subclass `SpecValidator` with local-only handler | Subclassing does NOT work — the `referencing` library used internally still resolves external refs regardless of `resolver_handlers` override (confirmed by live test: timeout on 169.254.169.254) |

**Installation:**
```bash
pip install "openapi-spec-validator>=0.9.0"
```

---

## Package Legitimacy Audit

| Package | Registry | Age | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|
| `openapi-spec-validator` | PyPI | ~8 years (0.0.2 in 2016) | `[OK]` | Approved |

[VERIFIED: slopcheck install openapi-spec-validator — returned `[OK]`; pip index versions confirmed 0.9.0 is latest]

**Packages removed due to slopcheck `[SLOP]` verdict:** none
**Packages flagged as suspicious `[SUS]`:** none

---

## Architecture Patterns

### System Architecture Diagram

```
quirk analyze-token <token|@file|->
  │
  ├─► parse_token_ref()          # @file / stdin / positional — reuses Phase 93 ref model
  │        │
  │        ▼
  │   jwt.get_unverified_header() + jwt.decode(verify_signature=False)
  │        │
  │        ├─► alg.lower() == "none" ?  ──► CRITICAL finding + exit 1
  │        │
  │        ▼
  │   classify_algorithm(alg) from quirk/cbom/classifier.py
  │        │
  │        ▼
  │   format report (human-readable | --json)
  │
quirk scan ... --auth-bearer @token_file --openapi-spec ./api.yaml
  │
  ├─► Phase 93: CredentialContext.from_cli(bearer="@token_file")
  │        │
  │        └─► TOKEN-02: classify alg → CryptoEndpoint(protocol="BEARER_TOKEN")
  │
  ├─► OpenAPI phase:
  │      │
  │      ├─► size_gate(path_or_url, max_bytes=10*1024*1024)  # BEFORE parse
  │      │
  │      ├─► [URL input] validate_external_url(url) + scope_check(url, cfg.targets)
  │      │
  │      ├─► yaml.safe_load(content)  ──► collect_all_refs(spec_dict)
  │      │         │
  │      │         └─► any non-'#' ref?  ──► SpecParsingError  (SSRF guard)
  │      │
  │      ├─► openapi_spec_validator.validate(spec_dict)  # structural check (lenient)
  │      │
  │      └─► extract_crypto_posture(spec_dict)
  │               ├─► security schemes → CryptoEndpoint(protocol="OpenAPI", ...)
  │               ├─► plaintext servers (http://) → finding
  │               └─► unauthenticated paths → finding
  │
  └─► reports/CBOM: all CryptoEndpoint rows including BEARER_TOKEN + OpenAPI rows
```

### Recommended Project Structure

```
quirk/
├── cli/
│   └── analyze_token_cmd.py     # NEW: --analyze-token subcommand handler
├── scanner/
│   └── openapi_scanner.py       # NEW: OpenAPI spec parser + crypto-posture extractor
└── cbom/
    └── builder.py               # EDIT: add "OpenAPI" + "BEARER_TOKEN" to Pass 1
quirk/intelligence/
    └── scoring.py               # EDIT: +2 agility weights (+10.0)
tests/
├── test_analyze_token.py        # NEW: TOKEN-01/02/03 unit tests
├── test_openapi_scanner.py      # NEW: SPEC-01/02/03 unit tests (mock httpx)
└── test_install_all_excludes_schemathesis.py  # NEW: PKG-01 CI guard
```

### Pattern 1: JWT Unverified Decode (TOKEN-01)

```python
# Source: PyJWT 2.12.1 confirmed in project .venv
import jwt

def analyze_jwt_token(raw_token: str) -> dict:
    """Decode JWT without signature verification for crypto posture analysis.
    
    Never validates the signature — this is intentional (passive analysis).
    options={"verify_signature": False, "verify_exp": False} prevents
    PyJWT from raising on expired or unsigned tokens.
    """
    header = jwt.get_unverified_header(raw_token)
    claims = jwt.decode(
        raw_token,
        options={"verify_signature": False, "verify_exp": False},
        algorithms=list(header.get("alg", "none") if header.get("alg") else ["none"])
        # algorithms must be passed to suppress AlgorithmNotAllowed on non-standard algs
    )
    return {"header": header, "claims": claims}
```

**Important:** `jwt.decode()` with `verify_signature=False` still requires the `algorithms` parameter in PyJWT ≥2.4.0 (changed to prevent algorithm confusion attacks). Pass `algorithms=["<alg_from_header>"]` or `algorithms=jwt.algorithms.get_default_algorithms()`. [VERIFIED: PyJWT 2.12.1 behavior confirmed by live test in project .venv]

### Pattern 2: `alg:none` Detection (TOKEN-03)

```python
# Must handle all case variants: none / None / NONE / NonE etc.
# Source: CONTEXT.md decision — case-insensitive check

alg = header.get("alg", "")
if alg.lower() == "none":
    # CRITICAL severity; command exits 1
    finding = CryptoEndpoint(
        host="<token-source>",
        port=0,
        protocol="BEARER_TOKEN",
        cert_pubkey_alg="none",
        severity="CRITICAL",
        service_detail="alg:none — unsigned JWT, trivially forgeable",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
```

### Pattern 3: SSRF Guard — Pre-Scan `$ref` Values (SPEC-03)

**CRITICAL FINDING:** `openapi-spec-validator` 0.9.0 with `jsonschema-path` 0.5.0 WILL make real network requests for external `$ref` values during `validate()`. This was confirmed by live test: passing a spec with `$ref: "http://169.254.169.254/metadata"` caused the library to attempt a TCP connection to 169.254.169.254:80 with a timeout (no exception raised immediately). Subclassing `SpecValidator` with custom `resolver_handlers` does NOT block this — the `referencing` library used internally bypasses the override.

**The correct guard: pre-scan ALL `$ref` values in the raw dict BEFORE calling `validate()`.**

```python
# Source: codebase investigation + live test confirmation

def _collect_refs(obj: Any, refs: list | None = None) -> list[str]:
    """Recursively collect all $ref string values from a parsed spec dict."""
    if refs is None:
        refs = []
    if isinstance(obj, dict):
        ref = obj.get("$ref")
        if ref is not None:
            refs.append(str(ref))
        for v in obj.values():
            _collect_refs(v, refs)
    elif isinstance(obj, list):
        for item in obj:
            _collect_refs(item, refs)
    return refs


def _assert_no_external_refs(spec_dict: dict) -> None:
    """Raise SpecParsingError if any $ref is external (not starting with '#').
    
    This MUST be called BEFORE openapi_spec_validator.validate() to prevent
    SSRF — the validator follows external $refs via urllib during validation.
    
    External refs include: http://, https://, ./relative-file, ../parent-file
    Local (intra-document) refs start with '#' and are safe.
    """
    refs = _collect_refs(spec_dict)
    external = [r for r in refs if not r.startswith("#")]
    if external:
        raise SpecParsingError(
            f"Spec contains {len(external)} external $ref(s) — blocked (SSRF guard). "
            f"Only intra-document refs (#/...) are permitted. "
            f"First rejected: {external[0][:64]!r}"
        )
```

### Pattern 4: Size Gate (SPEC-03 DoS guard)

```python
# Check BEFORE yaml.safe_load — prevents decompression bomb + parser exhaustion
MAX_SPEC_BYTES = 10 * 1024 * 1024  # 10 MB

def load_spec_from_file(path: str) -> dict:
    import os
    size = os.path.getsize(path)
    if size > MAX_SPEC_BYTES:
        raise SpecParsingError(
            f"Spec file exceeds 10 MB limit ({size} bytes) — refused to parse."
        )
    with open(path, "rb") as f:
        content = f.read(MAX_SPEC_BYTES + 1)
    if len(content) > MAX_SPEC_BYTES:
        raise SpecParsingError("Spec content exceeds 10 MB limit.")
    import yaml
    return yaml.safe_load(content)
```

### Pattern 5: CBOM Bearer-Token Component (TOKEN-02)

The bearer-token classification hooks into the existing `build_cbom()` Pass 1 — simply emit a `CryptoEndpoint(protocol="BEARER_TOKEN", ...)` row and add it to the endpoint list passed to `build_cbom()`. Pass 1 already handles "JWT" protocol; "BEARER_TOKEN" needs an `elif` branch.

```python
# In quirk/cbom/builder.py Pass 1 — add after elif ep.protocol == "JWT":
elif ep.protocol == "BEARER_TOKEN":
    # TOKEN-02: operator-supplied bearer credential, classified passively
    # service_detail carries "declared_algorithm (unverified)" label per CONTEXT D
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

The CBOM component will carry a `quirk:coverage-note` property via `_emit_coverage_note()` with value `"bearer-token-declared-algorithm"` to distinguish it from enforced-TLS algorithm components.

Also add `"BEARER_TOKEN"` to the Pass 3 skip list alongside "JWT" (no ProtocolProperties component).

### Pattern 6: SCORE_WEIGHTS +10.0 (SCORE-01)

Add 2 new entries to the `SCORE_WEIGHTS` dict in `quirk/intelligence/scoring.py`:

```python
"agility_weak_jwt_alg_ratio": 6.0,      # Phase 94 SCORE-01 — alg:none / RS256 in bearer token
"agility_openapi_plaintext_ratio": 4.0, # Phase 94 SCORE-01 — OpenAPI spec declares http:// servers
```

This adds +10.0 (283.0 → 293.0) and increases count 37 → 39. Update the invariant test:

```python
# tests/test_score_weights_invariant.py
assert abs(sum(SCORE_WEIGHTS.values()) - 293.0) < 1e-9  # was 283.0
assert len(SCORE_WEIGHTS) == 39  # was 37
```

The evidence keys that feed these new weights need to be computed in `build_evidence_summary()` in `quirk/intelligence/evidence.py` by inspecting `BEARER_TOKEN` and `OpenAPI` protocol rows.

### Pattern 7: Subcommand Registration (TOKEN-01)

The `analyze-token` subcommand follows the same intercept-before-argparse pattern as every other subcommand:

```python
# run_scan.py — add BEFORE the compliance block
if len(_sys.argv) > 1 and _sys.argv[1] == "analyze-token":
    from quirk.cli.analyze_token_cmd import run_analyze_token
    run_analyze_token(_sys.argv[2:])
    return
```

`run_analyze_token()` builds its own `argparse.ArgumentParser(prog="quirk analyze-token")` with a positional `token` arg (nargs="?") and a `--json` flag.

### Pattern 8: CI Guard Test — Schemathesis Exclusion (PKG-01)

Mirror `tests/test_install_all_excludes_impacket.py` exactly, replacing "impacket" with "schemathesis":

```python
# tests/test_install_all_excludes_schemathesis.py
assert "schemathesis" not in installed, (
    "REGRESSION: schemathesis is present in the resolved set for quirk[all]. "
    "Phase 94 PKG-01: schemathesis is in [api] extras only — never in [all]. "
    ...
)
```

Add a sanity-check for the presence of `openapi-spec-validator` in the `[api]` extra (verify the extra was created). This prevents a vacuous pass if `[api]` was silently omitted from `[all]` but also not present in the resolved set.

### Anti-Patterns to Avoid

- **Never call `openapi_spec_validator.validate()` before running `_assert_no_external_refs()`** — the validator will attempt network requests for `$ref: "http://..."` values. This is confirmed behavior in 0.9.0 (see live test results above).
- **Never pass `algorithms=None` to `jwt.decode()`** — PyJWT ≥2.4.0 requires an explicit algorithms list even when `verify_signature=False`; passing `None` raises `DecodeError`.
- **Never log or persist the raw token string** — even in `analyze-token`, the token is passed as a reference (`@file` / stdin / positional). If positional, document the argv-leakage caveat in `--help`.
- **Never add `quirk[api]` to `[all]`** — schemathesis ships in `[api]` in Phase 96; adding `[api]` to `[all]` would pull it in transitively before the CI guard is in place.
- **Never treat `declared_algorithm (unverified)` as enforced** — the CBOM label MUST include this caveat string exactly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT header decode | Custom base64url split + JSON parse | `jwt.get_unverified_header()` | Handles base64url padding edge cases, malformed headers, binary input |
| JWT claims decode | Manual base64url decode | `jwt.decode(verify_signature=False)` | Handles compressed claims, binary payloads, encoding variants |
| OpenAPI structural validation | Custom JSON Schema walk | `openapi_spec_validator.validate()` | Covers OAS 2.0/3.0/3.1 schema rules, security scheme shapes, server object formats |
| YAML parse | `json.loads()` fallback | `yaml.safe_load()` | Most OpenAPI specs are YAML; PyYAML already a core dep; `safe_load` prevents code execution |
| URL scope check | IP-range comparison | `validate_external_url()` in `quirk/util/url_allowlist.py` | Handles DNS resolution, metadata IPs, IPv6, link-local — already battle-tested |
| Quantum-safety classification | New alg table | `classify_algorithm()` in `quirk/cbom/classifier.py` | RS256/ES256/HS256/PS256/EdDSA/none already mapped with correct NIST levels |

---

## Common Pitfalls

### Pitfall 1: `jwt.decode()` requires `algorithms` parameter even with `verify_signature=False`
**What goes wrong:** `jwt.decode(token, options={"verify_signature": False})` without `algorithms` raises `jwt.exceptions.DecodeError: It is required that you pass in a value for the "algorithms" argument when calling decode()` in PyJWT ≥2.4.0.
**Why it happens:** PyJWT hardened against algorithm confusion attacks; even unverified decode needs to know which algorithm to expect for claim parsing.
**How to avoid:** Extract `alg` from `jwt.get_unverified_header()` first, then pass `algorithms=[alg]` (or a broad list) to `decode()`.
**Warning signs:** `DecodeError` in tests with `alg:none` tokens (where the header itself is valid).

### Pitfall 2: `openapi-spec-validator` follows external `$ref` during `validate()` — SSRF
**What goes wrong:** A spec containing `$ref: "http://169.254.169.254/latest/meta-data/"` will cause `openapi_spec_validator.validate()` to make a real network request to the metadata service. Confirmed by live test — the library uses `urllib` (via `requests`) to fetch `http://` refs during schema path resolution in `jsonschema_path`.
**Why it happens:** `jsonschema-path` 0.5.0 uses `UrllibHandler("http", "https", "file")` as the default `all_urls_handler`. The `referencing` library then calls this handler lazily when a `$ref` node is traversed during validation keyword processing.
**How to avoid:** Call `_assert_no_external_refs(spec_dict)` BEFORE `validate()`. Reject any ref that does not start with `#`.
**Warning signs:** Long pauses or connection timeouts on tests that pass specs with external refs.

### Pitfall 3: YAML decompression bomb before size gate
**What goes wrong:** `yaml.safe_load(open(huge_file))` can consume gigabytes of memory before returning if the YAML anchors cause exponential expansion (billion-laughs variant).
**Why it happens:** YAML anchors (`&anchor`) + aliases (`*alias`) can multiply content exponentially.
**How to avoid:** Read the raw bytes first, check `len(content) > 10MB`, THEN call `yaml.safe_load`. `PyYAML` does NOT have a built-in anchor-expansion limit; the byte-count gate provides partial mitigation.
**Warning signs:** OOM or very long parse times on crafted YAML specs.

### Pitfall 4: pydantic-settings is a NEW transitive dep
**What goes wrong:** `openapi-spec-validator` 0.9.0 requires `pydantic-settings` which was not previously installed in the project venv. If tests run in an environment that only has base `[dashboard]` extras installed, `import openapi_spec_validator` will fail with ImportError.
**Why it happens:** `pydantic-settings` is listed as a required dep of `openapi-spec-validator` but is not transitively pulled by any existing extras. [VERIFIED: `pip show pydantic-settings` — Required-by only lists `openapi-schema-validator` and `openapi-spec-validator`]
**How to avoid:** The `[api]` extras group in `pyproject.toml` pins `openapi-spec-validator>=0.9.0`, which will pull `pydantic-settings` transitively. Use graceful degradation guard: `try: from openapi_spec_validator import validate; OPENAPI_AVAILABLE = True; except ImportError: OPENAPI_AVAILABLE = False`.
**Warning signs:** `ImportError: No module named 'pydantic_settings'` in the openapi scanner when `[api]` extras are not installed.

### Pitfall 5: SCORE_WEIGHTS count invariant must also be updated
**What goes wrong:** Updating the sum test (283.0 → 293.0) without also updating the count test (37 → 39) will fail the count invariant CI check.
**Why it happens:** `test_score_weights_invariant.py` has TWO tests: `test_score_weights_sum_invariant` (sum = 283.0) AND `test_score_weights_count_invariant` (len = 37).
**How to avoid:** Update both assertions in the same commit as the SCORE_WEIGHTS dict change. New counts: sum = 293.0, count = 39.

### Pitfall 6: `alg:none` in headers is a dict key — not the JWT literal string "none"
**What goes wrong:** Checking `raw_token.lower().contains("none")` will false-positive on legitimate tokens that mention "none" in the payload or target URLs.
**Why it happens:** Naive string search on the raw JWT.
**How to avoid:** Decode the header via `jwt.get_unverified_header()` first, then check `header.get("alg", "").lower() == "none"`.

### Pitfall 7: `validate()` is not lenient by default for Swagger 2.0 specs
**What goes wrong:** `openapi_spec_validator.validate()` raises `ValidationError` on non-conformant specs, breaking the scan for legitimate but partially-invalid specs.
**Why it happens:** The library enforces the schema strictly. Some real-world Swagger 2.0 specs have minor violations.
**How to avoid:** Wrap `validate()` in a try-except; log the validation warning but continue with the raw spec dict for crypto-posture extraction. The CONTEXT specifies "lenient parse-what-we-can with graceful degradation" — structural validation errors should produce a warning, not block the entire analysis.

---

## Code Examples

### Full JWT Analysis Flow (TOKEN-01)

```python
# Source: PyJWT 2.12.1 behavior confirmed in project .venv
import jwt
from datetime import datetime, timezone
from quirk.cbom.classifier import classify_algorithm, quantum_safety_label

def analyze_bearer_token(raw_token: str) -> dict:
    """Decode and classify a JWT/bearer token. Never verifies signature."""
    header = jwt.get_unverified_header(raw_token)
    alg = header.get("alg", "UNKNOWN")
    
    # Decode claims without signature verification
    try:
        claims = jwt.decode(
            raw_token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=[alg] if alg else ["none"],
        )
    except jwt.exceptions.DecodeError:
        claims = {}
    
    # alg:none check — case-insensitive (TOKEN-03)
    is_alg_none = alg.lower() == "none"
    
    # Expiry check
    exp = claims.get("exp")
    expired = False
    if exp is not None:
        expired = datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc)
    
    # Quantum-safety via existing classifier
    primitive, nist_level, classical_level = classify_algorithm(alg.lower())
    qs_label = quantum_safety_label(nist_level)
    
    return {
        "alg": alg,
        "is_alg_none": is_alg_none,
        "expired": expired,
        "exp": exp,
        "nist_level": nist_level,
        "quantum_safety": qs_label,
        "claims": claims,
    }
```

### OpenAPI Spec Load + Guard Flow (SPEC-01/02/03)

```python
# Source: codebase investigation + live test confirmation of SSRF behavior

import os
import yaml
from quirk.util.url_allowlist import validate_external_url

MAX_SPEC_BYTES = 10 * 1024 * 1024  # 10 MB


class SpecParsingError(Exception):
    """Raised for SSRF attempts, oversized specs, or parse failures."""


def load_openapi_spec(path: str) -> dict:
    """Load OpenAPI spec from local file with size gate. SPEC-01 + SPEC-03."""
    if not os.path.isfile(path):
        raise SpecParsingError(f"Spec file not found: {path!r}")
    raw = open(path, "rb").read(MAX_SPEC_BYTES + 1)
    if len(raw) > MAX_SPEC_BYTES:
        raise SpecParsingError(
            f"Spec file exceeds 10 MB limit ({os.path.getsize(path)} bytes)."
        )
    return yaml.safe_load(raw)


def fetch_openapi_spec_url(url: str, cfg_targets: list[str]) -> dict:
    """Fetch OpenAPI spec from URL — ONLY when URL is in configured scan targets. SPEC-02."""
    # Scope gate: URL must be within configured targets
    # (cfg_targets is the list from AppConfig.targets)
    if not any(url.startswith(t.rstrip("/")) for t in cfg_targets):
        raise SpecParsingError(
            f"OpenAPI spec URL {url!r} is outside configured scan-target scope. "
            "URL fetch is only permitted for URLs within the targets list."
        )
    # SSRF gate: validate_external_url blocks metadata IPs always
    vr = validate_external_url(url)
    if not vr.ok:
        raise SpecParsingError(
            f"OpenAPI spec URL rejected ({vr.reason}): {vr.redacted_preview!r}"
        )
    import httpx
    resp = httpx.get(url, timeout=15, follow_redirects=True)
    resp.raise_for_status()
    content = resp.content
    if len(content) > MAX_SPEC_BYTES:
        raise SpecParsingError("Fetched spec content exceeds 10 MB limit.")
    return yaml.safe_load(content)


def assert_no_external_refs(spec_dict: dict) -> None:
    """Raise SpecParsingError on any external $ref. SPEC-03 SSRF guard.
    
    MUST be called before openapi_spec_validator.validate() — the validator
    follows external $refs via urllib (confirmed live behavior in 0.9.0).
    """
    refs = _collect_refs(spec_dict)
    external = [r for r in refs if not str(r).startswith("#")]
    if external:
        from quirk.util.url_allowlist import _redact_preview
        first = _redact_preview(str(external[0]))
        raise SpecParsingError(
            f"Spec contains {len(external)} external $ref(s) — blocked to prevent "
            f"SSRF. Only intra-document refs (#/...) are allowed. "
            f"First rejected: {first!r}"
        )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `jwt.decode(key="", algorithms=["RS256"])` fails without key | `jwt.decode(options={"verify_signature": False})` + explicit `algorithms` list | PyJWT 2.4.0 (2022) | Must pass algorithms param even for unverified decode |
| `openapi-spec-validator` < 0.5 had sync resolve | 0.9.0 uses `jsonschema-path` + `referencing` for lazy resolution | 0.9.0 (2025) | External $refs are resolved lazily during `validate()` iteration — not at load time; pre-scan guard is required |
| OpenAPI 2.0 only parsers | `openapi-spec-validator` 0.9.0 covers OAS 2.0 + 3.0 + 3.1 | 0.7.x (2023) | Single library covers all spec versions |

**Deprecated/outdated:**
- `prance`: Had widespread use as an OpenAPI bundler/resolver; now less maintained; NOT recommended for QUIRK (ref-resolution model conflicts with SSRF requirements).
- `connexion`: Framework-level validator, too heavy; not a candidate.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `agility_weak_jwt_alg_ratio` (6.0) and `agility_openapi_plaintext_ratio` (4.0) are reasonable weight names/values for the +10.0 increment | Standard Stack / Code Examples | If planner chooses different weight names or splits, test expected-sum still holds — only count changes |
| A2 | The `BEARER_TOKEN` protocol string does not collide with any existing protocol in evidence.py `_PROTOCOL_KEYS` | Architecture Patterns | No existing usage found by grep; would need to add "BEARER_TOKEN" to `_PROTOCOL_KEYS` in evidence.py |
| A3 | `yaml.safe_load` on a 10 MB spec will complete in reasonable time without OOM | Common Pitfalls | YAML anchor-explosion is possible but unlikely for real-world specs; 10 MB byte-gate provides partial mitigation |
| A4 | The `openapi:` config block will be added as a new section in `ConnectorsCfg` or `ScanCfg` | Architecture Patterns | Either location works; ConnectorsCfg is more semantically correct (external source) |

---

## Open Questions

1. **Evidence keys for new agility weights**
   - What we know: `agility_weak_jwt_alg_ratio` and `agility_openapi_plaintext_ratio` need corresponding evidence keys read from `build_evidence_summary()`.
   - What's unclear: The exact counter variable names to add to `evidence.py` and how to count "weak JWT alg" from `BEARER_TOKEN` protocol rows vs OpenAPI `http://` server URLs from `OpenAPI` protocol rows.
   - Recommendation: Add `bearer_token_weak_alg_count` (RS256/HS256/etc — all currently quantum-vulnerable) and `openapi_plaintext_server_count` counters to `build_evidence_summary()`. The scoring function reads these the same way as `dar_db_plaintext_count`.

2. **OpenAPI config block location in AppConfig**
   - What we know: CONTEXT says `openapi:` config block; `AppConfig` has `assessment`, `scan`, `targets`, `connectors`, `output`, `intelligence`, `security`.
   - What's unclear: Whether `openapi_spec` goes in `ScanCfg` (scan-time option) or `ConnectorsCfg` (external source).
   - Recommendation: `ScanCfg` as `openapi_spec_path: Optional[str] = None` — it's a per-scan input like targets, not a persistent connector.

3. **`--analyze-token` with bearer tokens that are NOT JWTs (opaque tokens)**
   - What we know: `jwt.get_unverified_header()` will raise `jwt.exceptions.DecodeError` for opaque bearer tokens that are not Base64url-encoded JWTs.
   - What's unclear: Should the command report "not a JWT — cannot analyze" gracefully, or hard-error?
   - Recommendation: Catch `DecodeError`, report "token does not appear to be a JWT (opaque token)" with INFO severity and exit 0 (non-CRITICAL). Only JWT-shaped tokens are classified.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All | ✓ | 3.14.x (.venv) | — |
| PyJWT | TOKEN-01/02/03 | ✓ | 2.12.1 (core dep) | — |
| `openapi-spec-validator` | SPEC-01/02/03 | ✓ (installed in .venv) | 0.9.0 | Scanner degrades gracefully when `[api]` not installed |
| PyYAML | SPEC-01/02/03 | ✓ (core dep) | 6.0.x | — |
| `quirk/cbom/classifier.py` | TOKEN-02 | ✓ | project code | — |
| `quirk/util/url_allowlist.py` | SPEC-02/03 | ✓ | project code | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** `openapi-spec-validator` — when `[api]` extras not installed, `OPENAPI_AVAILABLE = False` and the scanner emits a `scan_error_category="missing_extra"` endpoint (same pattern as `HTTPX_AVAILABLE` in jwt_scanner.py).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `pytest tests/test_analyze_token.py tests/test_openapi_scanner.py tests/test_score_weights_invariant.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOKEN-01 | Decode JWT header/claims without signature verification | unit | `pytest tests/test_analyze_token.py::test_decode_rs256_token -x` | ❌ Wave 0 |
| TOKEN-01 | Handle opaque (non-JWT) token gracefully | unit | `pytest tests/test_analyze_token.py::test_opaque_token_graceful -x` | ❌ Wave 0 |
| TOKEN-02 | CBOM component emitted for bearer token with `declared_algorithm (unverified)` label | unit | `pytest tests/test_analyze_token.py::test_cbom_bearer_classification -x` | ❌ Wave 0 |
| TOKEN-03 | `alg:none` (all case variants) flagged CRITICAL + exit 1 | unit | `pytest tests/test_analyze_token.py::test_alg_none_critical -x` | ❌ Wave 0 |
| SPEC-01 | Local file parsed; security schemes extracted | unit | `pytest tests/test_openapi_scanner.py::test_local_file_parse -x` | ❌ Wave 0 |
| SPEC-02 | URL outside targets rejected before network | unit | `pytest tests/test_openapi_scanner.py::test_url_scope_rejected -x` | ❌ Wave 0 |
| SPEC-03 | File > 10 MB raises SpecParsingError | unit | `pytest tests/test_openapi_scanner.py::test_oversize_rejected -x` | ❌ Wave 0 |
| SPEC-03 | External `$ref` raises SpecParsingError (no network call) | unit | `pytest tests/test_openapi_scanner.py::test_external_ref_ssrf_guard -x` | ❌ Wave 0 |
| SCORE-01 | SCORE_WEIGHTS sum = 293.0 | unit | `pytest tests/test_score_weights_invariant.py -x` | ✅ exists (must update) |
| SCORE-01 | SCORE_WEIGHTS count = 39 | unit | `pytest tests/test_score_weights_invariant.py -x` | ✅ exists (must update) |
| PKG-01 | `quirk[all]` does not pull schemathesis | slow | `pytest tests/test_install_all_excludes_schemathesis.py -m slow` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_analyze_token.py tests/test_openapi_scanner.py tests/test_score_weights_invariant.py -x`
- **Per wave merge:** `pytest` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_analyze_token.py` — covers TOKEN-01/02/03
- [ ] `tests/test_openapi_scanner.py` — covers SPEC-01/02/03
- [ ] `tests/test_install_all_excludes_schemathesis.py` — covers PKG-01

*(No new framework install needed — pytest already configured)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase 93 delivered this |
| V3 Session Management | No | Standalone analyzer has no session |
| V4 Access Control | No | `--analyze-token` is local operator tool |
| V5 Input Validation | Yes | Size gate (10 MB), SSRF pre-scan of $refs, `alg:none` case-insensitive check, opaque-token graceful handling |
| V6 Cryptography | Yes | JWT alg classification via `classify_algorithm()` — never hand-roll |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via OpenAPI `$ref: "http://169.254.169.254/..."` | Spoofing, Information Disclosure | Pre-scan all `$ref` values; reject any non-`#` ref before calling `validate()` |
| Decompression bomb via YAML anchors | Denial of Service | 10 MB byte-gate BEFORE `yaml.safe_load()` |
| Algorithm confusion via `alg:none` JWT | Spoofing | Case-insensitive `header["alg"].lower() == "none"` check → CRITICAL + exit 1 |
| Opaque token treated as JWT | Information Disclosure | `jwt.DecodeError` caught; report "opaque token" with INFO severity, no classification |
| Token value in error messages (LEAK-03) | Information Disclosure | Any exception wrapping token analysis wrapped in `safe_str()` before logging; token bytes never logged |

---

## Sources

### Primary (HIGH confidence)
- Project codebase (`quirk/scanner/jwt_scanner.py`, `quirk/util/url_allowlist.py`, `quirk/cbom/builder.py`, `quirk/intelligence/scoring.py`, `tests/test_score_weights_invariant.py`, `tests/test_install_all_excludes_impacket.py`) — direct code inspection
- `PyJWT 2.12.1` live test in project `.venv` — confirmed `get_unverified_header()` + `decode(verify_signature=False)` behavior
- `openapi-spec-validator` 0.9.0 live test — confirmed external `$ref` SSRF behavior (TCP connection attempt to 169.254.169.254:80 during `validate()`)

### Secondary (MEDIUM confidence)
- `pip index versions openapi-spec-validator` — confirmed 0.9.0 latest on PyPI
- `slopcheck install openapi-spec-validator` — confirmed `[OK]` verdict
- `pip check` in project `.venv` after installing `openapi-spec-validator` — confirmed no dependency conflicts

### Tertiary (LOW confidence)
- None — all critical claims verified via live tooling

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps verified in project .venv; slopcheck run
- Architecture: HIGH — all patterns derived from existing codebase code inspection
- SSRF pitfall: HIGH — confirmed by live test (actual TCP connection attempt observed)
- Scoring: HIGH — SCORE_WEIGHTS structure verified by direct code read; invariant test verified
- Pitfalls: HIGH — confirmed by live PyJWT + openapi-spec-validator experiments

**Research date:** 2026-05-23
**Valid until:** 2026-07-23 (stable ecosystem; 60-day window before `openapi-spec-validator` minor bump check advisable)
