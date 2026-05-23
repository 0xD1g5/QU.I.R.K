# Stack Research — v5.1 Authenticated Scanning + API Surface Depth (ADDITIONS ONLY)

**Domain:** Ephemeral credential model, OpenAPI spec analysis, bearer token interception, active REST fuzzing, code-signing cert inventory — additive to an existing mature Python 3.11+ crypto scanner
**Researched:** 2026-05-22
**Confidence:** HIGH (all versions verified against live PyPI index; existing core deps confirmed from pyproject.toml; integration points confirmed from source files)

> This file covers ONLY stack additions/changes for v5.1. The full existing stack
> (sslyze, httpx, PyJWT, python-jose, cryptography, PyYAML, lxml, cyclonedx-python-lib,
> FastAPI, React + shadcn/ui, SQLite, dnspython, signxml, nh3, impacket, etc.) is
> documented in PROJECT.md Key Decisions and is NOT repeated here.

---

## Existing Core Deps Already Available for v5.1 (Zero Additional Cost)

These are already in `pyproject.toml` core and cover most of the v5.1 feature surface.
Verify before adding anything — the correct answer is often "use what is already there."

| Library | Version Pinned | Latest on PyPI | Relevant v5.1 Use |
|---------|---------------|---------------|-------------------|
| `httpx` | `>=0.28.0` | 0.28.1 | HTTP client for authenticated API calls; inject auth headers |
| `PyJWT` | `>=2.12.0` | 2.13.0 | JWT decode/inspect (alg, exp, kid) for bearer token analysis |
| `python-jose` | `>=3.5.0` | 3.5.0 | JWE / non-standard alg values that PyJWT refuses to decode |
| `cryptography` | `>=44.0` | 48.0.0 | X.509 EKU OID extraction for code-signing cert classification |
| `PyYAML` | `>=6.0` | 6.0.3 | OpenAPI YAML spec loading (use `safe_load`, never `load`) |
| `lxml` | `>=6.0` | 6.1.1 | XML-based code-signing manifests; already XXE-hardened |
| `asn1crypto` | transitive via `cryptography` | 1.5.1 | ASN.1 cert field decoding (already available at zero cost) |
| `rich` | `>=13.0.0` | 15.0.0 | Credential prompt UX (`quirk doctor` already uses it) |

**Implication:** Zero new core dependencies are needed for Features 1, 3, and 5. Only Features 2 and 4 require new pip packages, and those belong in a new `[api]` extras group only.

---

## Feature 1 — Ephemeral Credential Model

### Decision: No new pip dependency

Use stdlib `getpass.getpass()` + `os.environ` + a plain `dataclass` in a new `quirk/auth/credentials.py` module. The `safe_exc.py` helper (v4.8 Phase 59 / LEAK-01) already scrubs `Authorization: Bearer` from exception strings — extend its `_SENSITIVE_PATTERNS` with API-key header variants.

**Why no new lib:**

`keyring` (25.7.0) persists credentials to OS Keychain/GNOME Wallet/Windows Credential Manager. That directly contradicts the milestone's "never persisted" invariant stated in PROJECT.md. Adding it would make the ephemeral guarantee impossible to enforce via tests. Do NOT add.

`requests-oauthlib` (2.0.0) handles OAuth2 client-credentials token acquisition (network round-trip, `client_secret` in memory). v5.1 scope is to USE a pre-acquired token — not to acquire one. OAuth2 flow is deferred per PROJECT.md (mTLS + OAuth2 client_credentials). Do NOT add.

`python-dotenv` (1.2.1) loads credentials from `.env` files — a persistence mechanism in disguise. Any tool that reads credentials from a file on disk defeats the ephemeral model. Do NOT add.

### Implementation pattern

```python
# quirk/auth/credentials.py — pure stdlib, no new deps
from __future__ import annotations
import base64, getpass, os, sys
from dataclasses import dataclass
from typing import Literal, Optional

CredKind = Literal["bearer", "api_key_header", "api_key_query", "basic"]

@dataclass(frozen=True)
class EphemeralCredential:
    kind: CredKind
    value: str           # bearer token, api key, or "user:pass" for Basic
    header_name: str = "Authorization"   # override for api_key_header
    query_param: str = ""                # populated for api_key_query only

    def apply_to_headers(self) -> dict[str, str]:
        if self.kind == "bearer":
            return {"Authorization": f"Bearer {self.value}"}
        if self.kind == "api_key_header":
            return {self.header_name: self.value}
        if self.kind == "basic":
            enc = base64.b64encode(self.value.encode()).decode()
            return {"Authorization": f"Basic {enc}"}
        return {}   # api_key_query: applied via URL params, not headers

def credential_from_env_or_prompt(kind: CredKind = "bearer") -> Optional[EphemeralCredential]:
    """Flag > env > TTY prompt. Never reads from file. Never persists."""
    token = (
        os.environ.get("QUIRK_AUTH_TOKEN")
        or os.environ.get("QUIRK_AUTH_KEY")
        or os.environ.get("QUIRK_AUTH_BASIC")
    )
    if not token and sys.stdin.isatty():
        token = getpass.getpass("Auth credential (Enter to skip): ").strip() or None
    return EphemeralCredential(kind=kind, value=token) if token else None
```

### `safe_exc.py` extension (one-line addition, no new dep)

Extend `_SENSITIVE_PATTERNS` in `quirk/util/safe_exc.py` to cover API-key variants not currently scraped:

```python
# Add to _SENSITIVE_PATTERNS tuple:
re.compile(r"\bX-Api-Key:\s*\S+", re.IGNORECASE),
re.compile(r"\bX-Auth-Token:\s*\S+", re.IGNORECASE),
re.compile(r"[?&]api[_-]?key=[^&\s]+", re.IGNORECASE),  # query param leakage
```

---

## Feature 2 — OpenAPI / Swagger Spec Analysis

### Decision: Add `openapi-spec-validator>=0.7.2` to `[api]` extras

| Library | Version | Extras Group | Why |
|---------|---------|-------------|-----|
| `openapi-spec-validator` | `>=0.7.2` | `[api]` | Validates and resolves both OAS2 (Swagger) and OAS3 specs. Pure-Python, pip-installable, offline-capable. Handles `$ref` resolution internally via `jsonschema-path`. The canonical validation layer used by the OpenAPI community. Deps: `jsonschema` (already installed at 4.25.1 in env), `referencing` (0.36.2 also present). No new transitive conflicts. |

**`openapi-core` (0.22.0): Do NOT add.** It layers full HTTP request/response validation middleware on top of spec parsing — heavyweight (`werkzeug`, `isodate`, `lazy-object-proxy` in transitive tree). QUIRK needs passive spec analysis for crypto inventory, not a request validator. Brings `werkzeug` which has no scanner role.

**`prance` (23.6.21.0): Do NOT add.** Primary value is resolving external `$ref` URLs via network. QUIRK's offline constraint makes remote `$ref` resolution a liability; a spec file with external `$ref` to `https://example.com/schemas/…` would fail on an air-gapped engagement. `openapi-spec-validator` handles local `$ref` correctly.

**`jsonref` (1.1.0): Do NOT add separately.** `openapi-spec-validator` handles `$ref` resolution already. No independent value.

### What the OpenAPI scanner extracts (passive — no auth needed)

Walk `paths` → `operations` → security declarations. Extract:
- `components/securitySchemes`: type, scheme, `bearerFormat`, OAuth2 flows, API key param name/location
- Per-operation `security` overrides (some ops may be public, some require auth)
- Parameters or schema fields using `format: "password"` or `format: "byte"` (base64 creds in request bodies)
- `x-` extensions advertising JWT `alg` or key ID hints
- Crypto-weak patterns: HTTP (not HTTPS) `servers` entries, `securitySchemes` with no scheme declared

All extraction is plain dict-walking after `openapi-spec-validator` loads and resolves. No additional library beyond the validator.

### YAML loading safety

`PyYAML` is already in core. Use `yaml.safe_load()` exclusively — never `yaml.load()`. YAML 1.1 booleans (`on`/`off`, `yes`/`no`) can corrupt boolean OpenAPI field values. Enforce via the existing semgrep ruleset (add a rule targeting `yaml.load\(` without `Loader=yaml.SafeLoader` if not already present).

---

## Feature 3 — Bearer Token Interception and Cryptographic Analysis

### Decision: No new dependency — use existing PyJWT + python-jose (both in core)

`PyJWT 2.x` decodes a JWT header/payload without verification:

```python
import jwt
header = jwt.get_unverified_header(token)   # {"alg": "RS256", "kid": "abc", "typ": "JWT"}
payload = jwt.decode(token, options={"verify_signature": False})  # {"exp": 1748000000, ...}
```

Combined with the existing `_rsa_key_bits_from_n()` helper already in `jwt_scanner.py`, all needed crypto fields are extractable without a new dep.

`python-jose` (already in core) covers JWE (encrypted tokens with `"alg": "RSA-OAEP"` in the outer header) and non-standard `alg` values that `PyJWT` refuses to decode (e.g., deprecated `"alg": "none"`). The `python-jose` path is a fallback for tokens PyJWT rejects.

Token expiry classification uses stdlib: `datetime.fromtimestamp(exp, tz=timezone.utc)`. No new dep.

**`joserfc` (1.6.5): Do NOT add.** More modern library but adds a dependency for capabilities already covered by `python-jose` which is already in core. Redundant.

### Integration point with jwt_scanner.py

Extend `scan_jwt_targets()` with an optional `credential: Optional[EphemeralCredential]` parameter:

1. If credential provided: inject `credential.apply_to_headers()` into the `httpx` request for JWKS fetch (enables fetching protected JWKS endpoints).
2. After JWKS fetch, also decode the credential's bearer token itself (if `kind == "bearer"` and token is a JWT): extract `alg`, `exp`, `kid`, `iat` and emit an additional `CryptoEndpoint` record for the token's own crypto posture.
3. Cross-reference decoded `kid` with fetched JWKS keys where available.

Return path is the same `List[CryptoEndpoint]` — no output model changes.

---

## Feature 4 — Active REST Fuzzing for Crypto Posture

### Decision: Add `schemathesis>=4.4.4` to `[api]` extras; NEVER in `[all]`

| Library | Version | Extras Group | In `[all]`? | Why |
|---------|---------|-------------|-------------|-----|
| `schemathesis` | `>=4.4.4` | `[api]` | **No** (explicit CI gate) | Spec-aware HTTP fuzzer — generates requests from OAS2/3 specs. Supports `stateful=False` mode for single-shot request generation. The `Case.as_transport_kwargs()` API lets QUIRK control dispatch via its existing `httpx` client. `max_examples` maps directly to the probe-budget constraint. Wraps `hypothesis` — no need to add `hypothesis` directly. |

**Why NOT `hypothesis` directly (6.141.1):** `schemathesis` wraps `hypothesis` with OpenAPI-aware strategies. Using `hypothesis` raw requires writing auth-downgrade strategies manually — that is the work `schemathesis` already did. Wrong abstraction level.

**Why NOT a custom fuzzer:** The budget-guard pattern (mirrors Phase 47 nmap probe budget) needs `max_examples` tracking. `schemathesis` provides this built-in. A custom fuzzer produces the same result with more unvetted surface for the security review gate.

### Critical design constraints (non-negotiable)

1. **Off by default.** Active fuzzing requires `--fuzz` flag + `--fuzz-confirm-authorization` acknowledgement flag + `--fuzz-budget N` (max requests, default 50). Mirrors the nmap `--probe-budget` pattern from Phase 47.
2. **Lazy import.** `schemathesis` must only be imported inside the fuzzing branch. `pip install quirk-scanner` (without `[api]`) must never crash on import.
3. **`[api]` not in `[all]`.** Active fuzzing sends crafted traffic. Including it in `[all]` would silently add active-scanning capability to the default install. Gate explicitly. A CI test (`tests/test_install_all_excludes_schemathesis.py`) guards this invariant — mirrors `tests/test_install_all_excludes_impacket.py`.

```python
# quirk/scanner/fuzz_scanner.py
try:
    import schemathesis
    SCHEMATHESIS_AVAILABLE = True
except ImportError:
    SCHEMATHESIS_AVAILABLE = False

def scan_api_fuzz(spec_path: str, credential, budget: int = 50):
    if not SCHEMATHESIS_AVAILABLE:
        raise MissingExtraError("api", "active REST fuzzing")
    ...
```

### Fuzzing target: crypto-specific attack payloads only

The fuzzer is not general-purpose — it generates specific crypto-attack probes:

1. `alg: "none"` JWT header injection (no-signature bypass)
2. `alg: "HS256"` with RSA public key as HMAC secret (algorithm confusion attack — CVE class)
3. Downgraded `alg` value in `Authorization: Bearer` header
4. Missing `Authorization` header (verify 401 is returned — confirms auth is enforced)
5. API key in wrong location (header vs query param — tests parameter binding)
6. HTTP (not HTTPS) downgrade attempt via `http://` prefix substitution in base URL

All probes are crafted as `httpx.Request` objects via `schemathesis`'s `Case` API. No subprocess, no curl.

---

## Feature 5 — Code Signing Certificate Inventory

### Decision: No new dependency — use existing `cryptography>=44.0`

Code-signing certificates are X.509 certs with Extended Key Usage (EKU) OIDs. The `cryptography` library (core, `>=44.0`) exposes them via:

```python
from cryptography.x509.oid import ExtendedKeyUsageOID
from cryptography import x509

CODE_SIGNING_OIDS = frozenset({
    ExtendedKeyUsageOID.CODE_SIGNING,                          # 1.3.6.1.5.5.7.3.3 (standard)
    x509.ObjectIdentifier("1.2.840.113635.100.4.1"),           # Apple Developer ID Application
    x509.ObjectIdentifier("1.3.6.1.4.1.311.10.3.3"),           # Microsoft Authenticode
    x509.ObjectIdentifier("1.3.6.1.4.1.311.10.3.6"),           # Microsoft Windows System Component
})

def is_code_signing_cert(cert: x509.Certificate) -> bool:
    try:
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        return bool(CODE_SIGNING_OIDS & set(eku.value))
    except x509.ExtensionNotFound:
        return False
```

No subprocess, no OS keystore access, no new dependency.

**Discovery sources (agentless, no new deps):**

1. **TLS scanner output** — certs already extracted during `tls_scanner.py`; EKU check is a free pass through existing cert objects.
2. **SMIME scanner output** — `smime_scanner.py` already retrieves `userCertificate` / `userSMIMECertificate` attributes via LDAP. Apply the same EKU check.
3. OS certificate stores — out of scope (requires agent on target, violates agentless constraint).
4. JAR/APK files — out of scope (requires file system access on target).
5. Sigstore transparency log — deferred to v5.2 (see "What NOT to Add" below).

**New finding type:** `CODE-SIGN/weak-algorithm` — emitted when a code-signing cert uses RSA<2048, EC<256, or SHA-1. Severity: HIGH (same tier as `CERT/weak-key`). Routes through existing `_build_finding()` chokepoint in `risk_engine.py`. Adds to CBOM Pass-1 algorithm components.

**`sigstore` (4.1.0): Do NOT add.** Sigstore verifies Sigstore-format signatures via Rekor transparency log (network-required). v5.1 inventories traditional X.509 code-signing certs already discovered by existing scanners. Sigstore integration is a v5.2 extension.

**`pyhanko` (0.33.0): Do NOT add.** PDF digital signatures, not code-signing cert inventory.

**`oscrypto` (1.3.0): Do NOT add.** Superseded by `cryptography` for everything QUIRK needs.

**`certipy-ad` (4.8.2): Out of scope per PROJECT.md.** Live AD CS connectivity + pyOpenSSL conflict.

---

## New Extras Group: `[api]`

```toml
[project.optional-dependencies]
api = [
    "openapi-spec-validator>=0.7.2",
    "schemathesis>=4.4.4",
]
```

**`[all]` must NOT include `[api]`.** Guard with `tests/test_install_all_excludes_schemathesis.py`. Rationale: schemathesis sends active crafted traffic; this must never be a silent transitive of `pip install quirk-scanner[all]`.

### Lazy-import pattern (mandatory for both libs)

```python
# quirk/scanner/openapi_scanner.py
try:
    from openapi_spec_validator import validate as _validate_spec
    OPENAPI_SPEC_VALIDATOR_AVAILABLE = True
except ImportError:
    OPENAPI_SPEC_VALIDATOR_AVAILABLE = False

# quirk/scanner/fuzz_scanner.py
try:
    import schemathesis as _schemathesis
    SCHEMATHESIS_AVAILABLE = True
except ImportError:
    SCHEMATHESIS_AVAILABLE = False
```

Mirrors the `HTTPX_AVAILABLE` pattern in `jwt_scanner.py` and the `optional_extra.py` probe registry from Phase 45. Coverage-gap advisory findings must be emitted when `[api]` is absent and these features are requested.

---

## Dependency Impact Summary

| Feature | New Pip Deps | Extras Group | In `[all]`? | Confidence |
|---------|-------------|-------------|-------------|------------|
| 1. Ephemeral credential model | None (pure stdlib + existing `rich` + `safe_exc.py` extension) | — | — | HIGH |
| 2. OpenAPI spec analysis | `openapi-spec-validator>=0.7.2` | `[api]` | No | HIGH |
| 3. Bearer token interception | None (existing `PyJWT` + `python-jose` in core) | — | — | HIGH |
| 4. Active REST fuzzing | `schemathesis>=4.4.4` | `[api]` | No (CI gate) | HIGH |
| 5. Code-signing cert inventory | None (existing `cryptography` EKU API in core) | — | — | HIGH |

**Net new pip dependencies: 2** (`openapi-spec-validator`, `schemathesis`), both in `[api]` extras only. Zero core dependency additions.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `keyring` | Persists credentials to OS keychain — directly contradicts ephemeral-only invariant | stdlib `getpass.getpass()` + `os.environ` |
| `requests-oauthlib` | OAuth2 token acquisition (mTLS + client_credentials flow) is deferred; v5.1 uses pre-acquired tokens | Pass token via `--auth-bearer` / env |
| `python-dotenv` | Reads creds from `.env` on disk — a persistence mechanism; defeats ephemeral model | `os.environ` direct access |
| `openapi-core` | Full HTTP middleware (`werkzeug`, `isodate`, `lazy-object-proxy`); overkill for passive spec analysis | `openapi-spec-validator` |
| `prance` | Resolves external `$ref` via network — breaks offline/air-gapped constraint | `openapi-spec-validator` (handles local `$ref`) |
| `jsonref` | Redundant with `openapi-spec-validator`'s built-in `$ref` resolution | `openapi-spec-validator` |
| `joserfc` | Duplicates `python-jose` already in core | Existing `python-jose>=3.5.0` |
| `hypothesis` (direct) | `schemathesis` wraps it with OpenAPI-aware strategies; don't add both | `schemathesis` (pulls hypothesis as dep) |
| `sigstore` | Sigstore transparency log verification; needs network; not X.509 inventory | `cryptography` EKU OID check (in-process) |
| `pyhanko` | PDF digital signatures, not code-signing cert inventory | Not applicable in v5.1 scope |
| `oscrypto` | Superseded by `cryptography` | Existing `cryptography>=44.0` |
| `certipy-ad` | Live AD CS + pyOpenSSL conflict; explicitly deferred in PROJECT.md | Out of scope v5.1 |
| `getpass2` / `maskpass` | Third-party wrappers around stdlib `getpass`; no meaningful improvement | stdlib `getpass.getpass()` |

---

## Integration Points With Existing API/JWT Scanner

1. **`quirk/scanner/jwt_scanner.py`** — Add optional `credential: Optional[EphemeralCredential]` parameter to `scan_jwt_targets()`. If provided: (a) inject `credential.apply_to_headers()` into the JWKS `httpx` fetch, (b) decode the credential's bearer token itself for direct `alg`/`exp` classification. Return path unchanged: `List[CryptoEndpoint]`.

2. **`quirk/scanner/tls_scanner.py`** — After cert extraction loop, add `cert_code_signing: bool` flag derived from `is_code_signing_cert(cert)` (EKU OID check, no new import). Feed into `_build_finding()` for `CODE-SIGN/weak-algorithm` findings.

3. **`quirk/scanner/smime_scanner.py`** — After `userCertificate` LDAP retrieval, apply `is_code_signing_cert()` check. Code-signing certs co-reside in directory services (e.g., `Developer ID` certs sometimes stored in LDAP).

4. **`quirk/scanner/openapi_scanner.py`** (new module) — Passive spec analysis. Input: spec file path (local) or URL (fetched via existing `httpx`). Output: `List[CryptoEndpoint]` representing API security surface. Lazy-imports `openapi_spec_validator`. Never requires auth for passive mode.

5. **`quirk/scanner/fuzz_scanner.py`** (new module) — Active fuzzing. Requires `EphemeralCredential` + explicit `--fuzz` + `--fuzz-confirm-authorization` + `--fuzz-budget N`. Emits `Finding` records (server behavior observations), not `CryptoEndpoint` records. Lazy-imports `schemathesis`. Budget tracked in a simple counter; abort on `budget_remaining == 0` before dispatching additional requests.

6. **`quirk/auth/credentials.py`** (new module) — `EphemeralCredential` dataclass + `credential_from_env_or_prompt()`. Zero imports from scanner modules (prevents circular deps). Called from `run_scan.py` to build credential and thread it into scanner calls via kwarg.

7. **`quirk/util/safe_exc.py`** — Extend `_SENSITIVE_PATTERNS` with `X-Api-Key`, `X-Auth-Token`, and query-param API key patterns. One-time addition; existing AST CI gate (`LEAK-03`) enforces no-raw-exc in `scan_error` writes already.

8. **`quirk/util/optional_extra.py`** probe registry — Register `openapi-spec-validator` and `schemathesis` as optional extras under the `api` group. `quirk doctor` will surface advisory findings for missing `[api]` extras when fuzz/spec features are requested.

---

## Version Compatibility Notes

| Package Pair | Compatibility | Notes |
|-------------|---------------|-------|
| `schemathesis>=4.4.4` + `hypothesis` | No conflict — `schemathesis` pins `hypothesis>=6.x` as a dep; `hypothesis 6.141.1` is current. | LOW risk |
| `openapi-spec-validator>=0.7.2` + `jsonschema` | `jsonschema 4.25.1` already installed. `openapi-spec-validator 0.7.2` requires `jsonschema-path` (separate pkg from `jsonschema` — verify not to confuse); `referencing 0.36.2` already present. | LOW risk — verify `jsonschema-path` installs cleanly |
| `schemathesis>=4.4.4` + `httpx>=0.28` | `schemathesis` can dispatch via its own transport or yield `Case` objects. Use `Case.as_transport_kwargs()` path to keep `httpx` as the single HTTP client in the scanner. Avoid mixing `requests` transport (schemathesis default) with `httpx`. | MEDIUM — test dispatch integration |
| `cryptography>=44.0` + `ExtendedKeyUsageOID` | `ExtendedKeyUsageOID.CODE_SIGNING` available since `cryptography 2.5`. Floor of 44.0 is far above that. | LOW risk |
| `PyJWT>=2.12.0` + `options={"verify_signature": False}` | Stable since PyJWT 2.0. Latest 2.13.0 is compatible. | LOW risk |
| `[api]` exclusion from `[all]` + `impacket` exclusion pattern | Both guard the same `[all]` invariant. CI must have two separate tests: `test_install_all_excludes_impacket.py` (existing) AND `test_install_all_excludes_schemathesis.py` (new). | LOW risk if CI gate is added at phase start |

---

## Installation

```bash
# Passive analysis only (spec parsing, bearer token decode, code-signing inventory)
# All needed libs are already in core — no extra needed
pip install "quirk-scanner"

# Spec analysis + active fuzzing (opt-in)
pip install "quirk-scanner[api]"

# Full suite including identity scanners (impacket excluded from [all] by design)
pip install "quirk-scanner[all,api]"   # or [api,identity] if Kerberos needed

# Dev / testing
pip install "quirk-scanner[all,api,dev]"
```

---

## Sources

- PyPI live index, 2026-05-22 — all version numbers verified via `pip index versions <lib>` (HIGH confidence)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/pyproject.toml` — core deps and extras groups verified directly from repo (HIGH confidence)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/scanner/jwt_scanner.py` — `_rsa_key_bits_from_n()`, `HTTPX_AVAILABLE` pattern, `scan_jwt_targets()` signature confirmed (HIGH confidence)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/util/safe_exc.py` — `_SENSITIVE_PATTERNS` tuple confirmed; `Authorization: Bearer` pattern present; API-key variants absent (HIGH confidence)
- `openapi-spec-validator` PyPI page — OAS2/OAS3 support, `jsonschema-path` dep, offline `$ref` resolution confirmed (MEDIUM — PyPI description + README; no Context7 entry; training-data cross-check consistent)
- `schemathesis` PyPI / GitHub README — `stateful=False` mode, `max_examples`, `Case.as_transport_kwargs()` API confirmed across 3.x → 4.x series (MEDIUM — PyPI/GitHub; training-data consistent)
- `cryptography` official docs — `ExtendedKeyUsageOID`, `x509.Certificate.extensions.get_extension_for_class()` API confirmed; available since 2.5; current floor 44.0 (HIGH confidence)
- PROJECT.md Key Decisions — `certipy-ad` deferred, `[all]` impacket exclusion pattern, ephemeral credential design decision confirmed (HIGH confidence — authoritative source)

---

*Stack research for: QU.I.R.K. v5.1 Authenticated Scanning + API Surface Depth*
*Researched: 2026-05-22*
