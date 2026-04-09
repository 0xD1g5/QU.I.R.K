# Phase 19: SAML/OIDC Scanner - Research

**Researched:** 2026-04-08
**Domain:** SAML IdP metadata parsing (lxml + defusedxml), OIDC discovery enumeration, X.509 cert extraction, SimpleSAMLphp chaos lab
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**OIDC Target Configuration**
- D-01: OIDC discovery endpoints share the `saml_targets` list — no new config field. Scanner attempts to parse each URL as SAML metadata XML first; if the response is JSON (or the URL path contains `.well-known`), it treats it as an OIDC discovery document. No `enable_oidc` or `oidc_targets` field additions to `ConnectorsCfg`. Phase 17's schema is final for this phase.

**SAML CryptoEndpoint Schema**
- D-02: One `CryptoEndpoint` row per cert per use-type (signing or encryption). `service_detail` format: `{entity_id}|use=signing|serial={serial_hex}` or `|use=encryption|serial={serial_hex}`. Cert serial extracted from DER bytes via `cryptography.x509.load_der_x509_certificate()` — already in core deps via TLS scanner.
- D-03: For OIDC algorithm declaration findings: one `CryptoEndpoint` per algorithm string from `id_token_signing_alg_values_supported` (and `request_object_signing_alg_values_supported` if present). `service_detail` = `oidc-discovery|id_token_signing_alg`. `cert_pubkey_alg` = the alg string (e.g., `RS256`, `RS384`). `cert_pubkey_size` = key size derived from alg string where deterministic (RS256 → 2048 assumed min; only RSA algs produce a size finding).
- D-04: SHA-1 algorithm URI findings: one `CryptoEndpoint` per URI occurrence found. `service_detail` = `{entity_id}|algo_uri={full_uri}|source={SignatureMethod|SigningMethod}`. `cert_pubkey_alg` = shortened form (e.g., `SHA1`). Severity = HIGH per SAML-04.

**SHA-1 Algorithm URI Detection Scope**
- D-05: Parse two XML locations for SHA-1 algorithm URIs:
  1. `<ds:SignatureMethod Algorithm="...">` — in the signed metadata wrapper
  2. `<alg:SigningMethod Algorithm="...">` — in metadata extensions declaring preferred signing algorithms
  Any URI containing `sha1` or `sha-1` (case-insensitive) in the local fragment is flagged. Cert signature hash algorithm is NOT separately flagged — captured via cert key-size finding.

**SAML_NS and XML Namespaces**
- D-06: Declare a module-level `SAML_NS` dict constant in `saml_scanner.py`. Minimum required namespaces:
  ```python
  SAML_NS = {
      "md":  "urn:oasis:names:tc:SAML:2.0:metadata",
      "ds":  "http://www.w3.org/2000/09/xmldsig#",
      "alg": "urn:oasis:names:tc:SAML:metadata:algsupport",
      "mdui": "urn:oasis:names:tc:SAML:metadata:ui",
  }
  ```
  lxml XPath calls always use explicit `namespaces=SAML_NS` argument — no namespace stripping.

**Severity Classification**
- D-07: RSA key size severity:
  - CRITICAL: key_bits < 2048
  - HIGH: key_bits == 2048 (quantum-vulnerable RSA)
  - SAFE (no finding): ECDSA P-256, P-384, Ed25519 certs
- D-08: SHA-1 algorithm URI severity = HIGH regardless of source.
- D-09: OIDC alg severity: RS256/RS384/RS512 = HIGH; ES256/ES384/ES512 = informational (no finding); HS256/HS384 = informational (symmetric); Unknown alg strings = LOW with note.

**Scanner Structure**
- D-10: Function signature: `scan_saml_targets(targets: list, timeout: int = 10, logger=None) -> list[CryptoEndpoint]`
- D-11: Import guard at top of `saml_scanner.py`:
  ```python
  try:
      import lxml.etree as ET
      import defusedxml.lxml as defused_ET
      LXML_AVAILABLE = True
  except ImportError:
      LXML_AVAILABLE = False
  ```
  Use `defusedxml.lxml.fromstring()` for all XML parsing to prevent XXE attacks. Fall back gracefully if lxml not installed.
- D-12: Sequential target processing — one target at a time, no threading.
- D-13: SSL verification disabled on metadata fetch (`verify=False`) — IdP metadata endpoints frequently use self-signed certs.
- D-14: Follow redirects (up to 3 hops).
- D-15: On error: log warning, skip target, continue. Store error detail in `saml_scan_json` under an `"errors"` key.

**run_scan.py Integration**
- D-16: SAML scan phase block added after dnssec_endpoints section, before final endpoint aggregation. Guarded by `cfg.connectors.enable_saml and cfg.connectors.saml_targets`. Wrapped in `_phase_timer(run_stats, "saml_scanning")`.

**saml_scan_json Structure**
- D-17: Flat per-target dict stored as JSON array in `saml_scan_json` (see CONTEXT.md for full schema).

**Chaos Lab — SimpleSAMLphp**
- D-18: Docker image: `kenchan0130/simplesamlphp`
- D-19: RSA-1024 signing cert pre-generated with `openssl genrsa 1024` + `openssl req -x509`, committed to repo under `quantum-chaos-enterprise-lab/simplesamlphp/cert/server.crt` and `server.key`.
- D-20: Docker Compose `saml` profile — not grouped under `identity` profile.
- D-21: SimpleSAMLphp metadata URL: `http://localhost:8080/simplesaml/saml2/idp/metadata.php`

**CBOM Integration**
- D-22: `build_cbom()` gains `elif ep.protocol == "SAML":` branch calling `_register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)`.
- D-23: `classifier.py` gains `SAML_ALG_MAP` for algorithm URI strings and alg name classification.

### Claude's Discretion

- Internal helper function naming (`_fetch_metadata`, `_parse_signing_certs`, `_parse_oidc_discovery`, etc.)
- Exact XPath expressions for each field extracted
- Whether `SAML_NS` lives in `saml_scanner.py` or a shared `quirk/scanner/xml_utils.py`
- SimpleSAMLphp authsource configuration
- Exact SimpleSAMLphp docker-compose.yml env vars and volume mount paths

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAML-01 | Scanner fetches and parses SAML IdP metadata XML for signing and encryption cert key type, size, and expiry using lxml with explicit `SAML_NS` namespace constant | `defusedxml.lxml.fromstring()` + XPath with `namespaces=SAML_NS`; `cryptography.x509.load_der_x509_certificate()` for serial/expiry extraction from base64 DER |
| SAML-02 | Scanner parses `<KeyDescriptor use="encryption">` certs separately from signing certs, extracting key size findings for each | XPath `//md:KeyDescriptor[@use="encryption"]/ds:KeyInfo/ds:X509Data/ds:X509Certificate` with `namespaces=SAML_NS`; parallel to signing cert XPath |
| SAML-03 | Scanner parses OIDC discovery endpoint for `id_token_signing_alg_values_supported` and `request_object_signing_alg_values_supported` | JSON fetch on `.well-known/openid-configuration` URL; D-01 routing: JSON response or `.well-known` URL path → OIDC branch |
| SAML-04 | RSA < 2048-bit signing keys flagged CRITICAL; SHA-1 algorithm URIs flagged HIGH | D-07 severity map for key bits; D-05 XPath locations for SHA-1 URI detection; uri.lower() fragment check for `sha1` / `sha-1` |
| SAML-05 | Results stored in `saml_scan_json` with `protocol="SAML"` CryptoEndpoints; classifier updated with SAML algorithm URI strings; `build_cbom()` gains SAML `elif` branches | `_ALGORITHM_TABLE` extension with SAML-specific alg strings; builder `elif ep.protocol == "SAML"` dispatch — directly follows DNSSEC pattern |
| SAML-06 | Chaos lab gains SimpleSAMLphp `saml` Docker Compose profile with RSA-1024 weak signing cert for scanner validation | `kenchan0130/simplesamlphp` image; pre-generated RSA-1024 cert committed to repo; `SIMPLESAMLPHP_SP_ENTITY_ID` + volume mount env vars; `saml` profile in docker-compose.yml |
</phase_requirements>

---

## Summary

Phase 19 adds a SAML/OIDC scanner to QU.I.R.K. that fetches IdP metadata XML and OIDC discovery endpoints, extracts X.509 signing and encryption certificates, parses algorithm URI declarations, classifies weak crypto (RSA < 2048 = CRITICAL, SHA-1 URI = HIGH), and stores results in the CBOM via `protocol="SAML"` CryptoEndpoints and `saml_scan_json`.

The implementation follows the exact structural pattern established by the DNSSEC scanner (Phase 18): import guard (`LXML_AVAILABLE`), sequential target processing, one-CryptoEndpoint-per-finding, `_phase_timer` integration in `run_scan.py`, and a `elif ep.protocol == "SAML"` dispatch in `build_cbom()`. The primary new technical domain is lxml XPath over namespaced SAML XML — the namespace pitfall (silent empty results without explicit `namespaces=` arg) is the most common implementation error.

The chaos lab uses `kenchan0130/simplesamlphp` with a pre-generated RSA-1024 cert baked in, matching the DNSSEC pre-signed zone approach for deterministic TDD validation. lxml is declared in `[identity]` extras but not installed in the core virtualenv — the import guard is mandatory and tests must mock the XML layer rather than require lxml at test time.

**Primary recommendation:** Follow the DNSSEC scanner pattern precisely. The only genuine novelty is (1) lxml XPath with `SAML_NS` namespaces, (2) base64→DER→X.509 cert parsing already available in `cryptography` lib, and (3) the OIDC routing branch (JSON vs XML detection).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lxml | >=6.0 (identity extras) | SAML XML parsing and XPath | Industry-standard C-backed XML library; handles complex namespaced SAML metadata reliably |
| defusedxml | 0.7.1 (installed) | XXE-safe XML parsing wrapper | Mandatory for enterprise security scanner — XXE in a security tool is a critical vulnerability |
| httpx | 0.28.1 (installed) | HTTP fetch for metadata and OIDC endpoints | Already used in jwt_scanner.py; consistent with project pattern |
| cryptography | (installed, core dep) | X.509 cert parsing from DER bytes | Already used in TLS scanner; `load_der_x509_certificate()` extracts serial, key size, expiry |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| defusedxml.lxml | (via defusedxml) | `defusedxml.lxml.fromstring()` — the safe parse entry point | Use for ALL XML ingestion; never `lxml.etree.fromstring()` directly |
| json (stdlib) | — | OIDC discovery document parsing | JSON branch when URL is OIDC discovery |
| base64 (stdlib) | — | Decode `<ds:X509Certificate>` text content to DER bytes | SAML embeds certs as base64-encoded DER |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| lxml + defusedxml | pysaml2, python3-saml | Both require `xmlsec1` system binary — violates pip-only constraint; explicitly out of scope in REQUIREMENTS.md |
| lxml + defusedxml | stdlib xml.etree.ElementTree | No XXE protection by default; namespace handling is inferior; lxml already declared in [identity] extras |
| httpx | requests | httpx already in project; avoid adding requests dependency |

**Installation (identity extras group):**
```bash
pip install "quirk[identity]"
# Installs: impacket, dnspython[dnssec], lxml>=6.0, defusedxml>=0.7.1, signxml>=4.4.0
```

**Note:** lxml is NOT installed in the core venv. `pip install quirk` does not include it. The import guard (`LXML_AVAILABLE`) is mandatory. Tests must mock the XML layer at the `defusedxml.lxml` / `lxml.etree` module level.

**Version note (verified 2026-04-08):** defusedxml 0.7.1 is installed in project venv. lxml >=6.0 is declared in pyproject.toml [identity] extras. httpx 0.28.1 installed. cryptography installed (version: in core deps, confirmed working via `from cryptography.x509 import load_der_x509_certificate`).

## Architecture Patterns

### Recommended Project Structure
```
quirk/scanner/
├── saml_scanner.py          # New: SAML/OIDC scanner module

quantum-chaos-enterprise-lab/
├── docker-compose.yml       # Add: saml profile with simplesamlphp service
└── simplesamlphp/
    ├── cert/
    │   ├── server.crt       # Pre-generated RSA-1024 X.509 cert (weak, deterministic)
    │   └── server.key       # RSA-1024 private key
    └── config/              # Optional: custom authsources.php if needed

quirk/cbom/
├── builder.py               # Modify: add elif ep.protocol == "SAML" branch
└── classifier.py            # Modify: add SAML_ALG_MAP to _ALGORITHM_TABLE

run_scan.py                  # Modify: add saml scan block after dnssec block

tests/
└── test_saml_scanner.py     # New: RED scaffold (Plan 01), GREEN (Plan 02)
```

### Pattern 1: Import Guard (mirrors DNSSEC scanner exactly)
**What:** Try-import block that sets `LXML_AVAILABLE = True/False`, allowing the module to import without lxml installed.
**When to use:** Always — lxml is an optional identity extra.
**Example:**
```python
# Source: Established pattern from quirk/scanner/dnssec_scanner.py (DNSSEC_AVAILABLE → LXML_AVAILABLE)
try:
    import lxml.etree as ET
    import defusedxml.lxml as defused_ET
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False
```

### Pattern 2: SAML_NS Namespace Constant
**What:** Module-level dict mapping namespace prefixes used in XPath calls.
**When to use:** Every single lxml XPath call — omitting this causes silent empty results (XPath matches nothing).
**Example:**
```python
# Source: CONTEXT.md D-06 / SAML 2.0 specification namespace URIs
SAML_NS = {
    "md":   "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds":   "http://www.w3.org/2000/09/xmldsig#",
    "alg":  "urn:oasis:names:tc:SAML:metadata:algsupport",
    "mdui": "urn:oasis:names:tc:SAML:metadata:ui",
}

# Correct XPath usage:
signing_certs = root.findall(
    ".//md:KeyDescriptor[@use='signing']/ds:KeyInfo/ds:X509Data/ds:X509Certificate",
    namespaces=SAML_NS
)
# Note: lxml uses `findall(..., namespaces=)` or `.xpath(..., namespaces=)`
```

### Pattern 3: Base64-DER to X.509 Certificate Extraction
**What:** SAML XML embeds certificates as base64-encoded DER. Strip whitespace, decode, parse via cryptography library.
**When to use:** For every `<ds:X509Certificate>` element found.
**Example:**
```python
# Source: cryptography library docs; same approach as TLS scanner cert parsing
import base64
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.primitives.asymmetric import rsa, ec

def _parse_cert_element(cert_b64_text: str) -> dict:
    """Parse base64-encoded DER cert from SAML XML. Returns dict with key_alg, key_bits, serial, not_after."""
    der = base64.b64decode(cert_b64_text.replace(" ", "").replace("\n", ""))
    cert = load_der_x509_certificate(der)
    pub_key = cert.public_key()

    key_alg = "UNKNOWN"
    key_bits = None
    if isinstance(pub_key, rsa.RSAPublicKey):
        key_alg = "RSA"
        key_bits = pub_key.key_size
    elif isinstance(pub_key, ec.EllipticCurvePublicKey):
        key_alg = "ECDSA"
        key_bits = pub_key.key_size

    return {
        "key_alg": key_alg,
        "key_bits": key_bits,
        "serial": format(cert.serial_number, 'x'),
        "not_after": cert.not_valid_after_utc.isoformat(),
    }
```

### Pattern 4: OIDC/SAML URL Routing (D-01)
**What:** Determine at fetch time whether target is SAML XML or OIDC JSON.
**When to use:** In the main `scan_saml_targets` loop for each target.
**Example:**
```python
# Source: CONTEXT.md D-01
def _classify_target(url: str, resp_content_type: str, resp_bytes: bytes) -> str:
    """Returns 'saml' or 'oidc'."""
    if ".well-known" in url:
        return "oidc"
    # Attempt JSON parse — OIDC discovery documents are JSON
    try:
        json.loads(resp_bytes)
        return "oidc"
    except (json.JSONDecodeError, ValueError):
        return "saml"
```

### Pattern 5: CryptoEndpoint Construction (SAML certs)
**What:** One CryptoEndpoint per cert per use-type. `saml_scan_json` populated on each endpoint.
**When to use:** For every signing and encryption cert found.
**Example:**
```python
# Source: CONTEXT.md D-02, modeled on dnssec_scanner.py CryptoEndpoint construction
from quirk.models import CryptoEndpoint
from datetime import datetime, timezone

ep = CryptoEndpoint(
    host=target_url,
    port=443,  # or 80 for http metadata endpoints
    protocol="SAML",
    cert_pubkey_alg=cert_info["key_alg"],        # "RSA" or "ECDSA"
    cert_pubkey_size=cert_info["key_bits"],       # e.g., 1024
    service_detail=f"{entity_id}|use=signing|serial={cert_info['serial']}",
    saml_scan_json=json.dumps(scan_dict),
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
```

### Pattern 6: CBOM Builder Integration (mirrors DNSSEC branch exactly)
**What:** `elif ep.protocol == "SAML"` branch in `build_cbom()` Pass 1.
**When to use:** In `quirk/cbom/builder.py` after the existing DNSSEC branch.
**Example:**
```python
# Source: quirk/cbom/builder.py lines 351-355 (DNSSEC branch to follow)
elif ep.protocol == "SAML":
    # SAML: cert_pubkey_alg holds algorithm name (RSA, ECDSA) or SHA1 for URI findings
    # Exclude structural finding types that are not real crypto algorithms
    if ep.cert_pubkey_alg and ep.cert_pubkey_alg not in ("NONE",):
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

### Pattern 7: run_scan.py Integration Block (mirrors DNSSEC block)
**What:** Insert SAML scan block after `dnssec_endpoints`, before final aggregation.
**When to use:** Modify `run_scan.py` lines ~472-474 to add `saml_endpoints`.
**Example:**
```python
# Source: run_scan.py lines 460-474 (DNSSEC block to follow)
# ── SAML/OIDC scanning ──────────────────────────────────────
saml_endpoints = []
with _phase_timer(run_stats, "saml_scanning"):
    if cfg.connectors.enable_saml and cfg.connectors.saml_targets:
        saml_endpoints = scan_saml_targets(
            targets=cfg.connectors.saml_targets,
            timeout=getattr(cfg.connectors, "saml_timeout", 10),
            logger=main_logger,
        )
        main_logger.info("SAML scan: %d endpoints from %d targets",
                         len(saml_endpoints), len(cfg.connectors.saml_targets))

endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints
             + jwt_endpoints + container_endpoints + source_endpoints
             + aws_endpoints + azure_endpoints + dnssec_endpoints + saml_endpoints)
```

### Anti-Patterns to Avoid
- **Namespace stripping:** Never call `lxml.etree.fromstring(xml_bytes)` then strip namespaces. Always use `SAML_NS` in XPath. Silent empty result is the failure mode.
- **Direct lxml.etree.fromstring():** Always use `defusedxml.lxml.fromstring()` — the security scanner must not be vulnerable to XXE.
- **Importing pysaml2 or python3-saml:** Both require the `xmlsec1` system binary. Explicitly out of scope (REQUIREMENTS.md Out of Scope table).
- **Hardcoded HTTP port 443:** SimpleSAMLphp chaos lab runs on port 8080. Scanner must parse port from URL, not default to 443.
- **Calling `defusedxml.lxml.fromstring()` without checking LXML_AVAILABLE:** Will raise `NameError` if lxml is not installed and guard was bypassed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Safe XML parsing | Custom XXE mitigation | `defusedxml.lxml.fromstring()` | XXE via ENTITY expansion, billion laughs, external DTD attacks all handled by defusedxml |
| X.509 cert parsing from DER | Custom ASN.1 parser | `cryptography.x509.load_der_x509_certificate()` | Already in core deps; handles all cert formats, key types, extension parsing |
| RSA key size from cert | Byte-counting modulus manually | `cert.public_key().key_size` (cryptography lib) | RSAPublicKey.key_size is the authoritative way; byte-counting has endianness edge cases |
| OIDC algorithm enumeration | Full OIDC token verification flow | JSON GET on `.well-known/openid-configuration` | Scope is algorithm enumeration only — agentless model does not need a valid OIDC client |
| SAML metadata schema validation | Custom XSD validation | Skip validation, parse defensively | Consulting scanner; invalid metadata still needs partial results; schema validation errors would break scan |

**Key insight:** The complexity in this phase is XML namespace handling and DER cert parsing — both solved by lxml+defusedxml+cryptography. The scanner logic itself (iterate certs, classify sizes) is straightforward once those are working.

## Common Pitfalls

### Pitfall 1: Silent Empty XPath Results (Namespace Trap)
**What goes wrong:** XPath returns `[]` even though the XML clearly contains the elements.
**Why it happens:** SAML XML uses namespaces (e.g., `urn:oasis:names:tc:SAML:2.0:metadata`). Without `namespaces=SAML_NS` argument, lxml matches against the literal prefix text, which is absent in the serialized element name.
**How to avoid:** Always pass `namespaces=SAML_NS` to every `.findall()`, `.find()`, and `.xpath()` call. Test with a real SAML metadata sample in TDD.
**Warning signs:** Scanner runs without error, returns 0 CryptoEndpoints for a known-good IdP metadata URL.

### Pitfall 2: defusedxml.lxml Import Requires lxml
**What goes wrong:** `import defusedxml.lxml` raises `ModuleNotFoundError: No module named 'lxml'` even though defusedxml is installed (confirmed: defusedxml 0.7.1 is in venv but lxml is not).
**Why it happens:** `defusedxml.lxml` module imports from `lxml` at module level — it is a wrapper, not a standalone parser.
**How to avoid:** The import guard must cover BOTH `import lxml.etree as ET` and `import defusedxml.lxml as defused_ET` in the same try block. If lxml is absent, both fail.
**Warning signs:** `from defusedxml import lxml as defused_ET` raises ImportError in the test environment.

### Pitfall 3: SimpleSAMLphp Startup Latency
**What goes wrong:** Integration test hits `http://localhost:8080/simplesaml/saml2/idp/metadata.php` immediately after `docker compose --profile saml up`, gets a 503 or connection refused.
**Why it happens:** SimpleSAMLphp is a PHP application. Container starts fast but PHP-FPM and nginx/apache take 5-15 seconds to become ready.
**How to avoid:** Add `healthcheck` to the Docker Compose service testing the metadata URL, and `start_period: 20s`. Integration test should use `@pytest.mark.skipif` and retry logic or a sleep.
**Warning signs:** Integration test flaky — passes when run manually after wait, fails in automated suite.

### Pitfall 4: SimpleSAMLphp kenchan0130 Image Certificate Config
**What goes wrong:** The container starts but serves its own default self-signed cert instead of the pre-generated RSA-1024 weak cert.
**Why it happens:** `kenchan0130/simplesamlphp` requires specific environment variables (`SIMPLESAMLPHP_SP_ENTITY_ID`, etc.) AND the cert files must be mounted at the expected paths inside the container.
**How to avoid:** Volume-mount the pre-generated cert files. The standard SimpleSAMLphp cert path is `/var/www/simplesamlphp/cert/`. Set `SIMPLESAMLPHP_IDP_ENABLE=true`. Verify the metadata URL returns XML containing `<KeyDescriptor use="signing">` before committing.
**Warning signs:** Container running, metadata URL returns XML, but cert extracted is RSA-2048 (default) not RSA-1024.

### Pitfall 5: SHA-1 URI Fragment Detection — Case and Encoding Variants
**What goes wrong:** Scanner misses a SHA-1 URI because the XML uses `SHA1` instead of `sha1` or uses a variant URI (`xmldsig-more#rsa-sha1` vs `xmldsig#rsa-sha1`).
**Why it happens:** SAML metadata from different vendors uses slightly different URI strings for the same algorithm.
**How to avoid:** The detection logic per D-05 is: check if `"sha1"` or `"sha-1"` appears (case-insensitive) anywhere in the URI string — not just in the fragment. Use `uri.lower()` and check `.find("sha1") != -1 or .find("sha-1") != -1`.
**Warning signs:** Test with the URI `http://www.w3.org/2001/04/xmldsig-more#rsa-sha1` (note `xmldsig-more`) — scanner must flag it even though the primary SHA-1 URI uses `xmldsig#`.

### Pitfall 6: OIDC Discovery Field Absence
**What goes wrong:** Scanner raises `KeyError` or `TypeError` when OIDC provider omits `request_object_signing_alg_values_supported` (this field is optional per RFC 8414).
**Why it happens:** Code written against a full-featured IdP assumes both fields are present.
**How to avoid:** Use `data.get("id_token_signing_alg_values_supported", [])` and `data.get("request_object_signing_alg_values_supported", [])` — both default to empty list.
**Warning signs:** Scanner crashes on Keycloak or Okta endpoints that omit the optional field.

### Pitfall 7: X.509 DER base64 Whitespace
**What goes wrong:** `base64.b64decode()` fails with `binascii.Error: Invalid base64-encoded string`.
**Why it happens:** SAML metadata cert text contains newlines and spaces (PEM-style line wrapping embedded in XML). Standard `b64decode()` rejects whitespace by default.
**How to avoid:** Strip all whitespace before decoding: `der = base64.b64decode(cert_text.replace(" ", "").replace("\n", "").replace("\r", "").strip())`.
**Warning signs:** Test with a cert element that has embedded newlines (most real SAML metadata does).

## Code Examples

Verified patterns from official sources and existing project code:

### SAML Namespace XPath (correct form)
```python
# Source: lxml XPath documentation + SAML 2.0 spec namespace URIs
SAML_NS = {
    "md":  "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds":  "http://www.w3.org/2000/09/xmldsig#",
    "alg": "urn:oasis:names:tc:SAML:metadata:algsupport",
}

root = defused_ET.fromstring(xml_bytes)

# Signing certs
signing_certs_b64 = root.findall(
    ".//md:KeyDescriptor[@use='signing']/ds:KeyInfo/ds:X509Data/ds:X509Certificate",
    namespaces=SAML_NS
)
# Each element's .text is base64-encoded DER

# Encryption certs
encryption_certs_b64 = root.findall(
    ".//md:KeyDescriptor[@use='encryption']/ds:KeyInfo/ds:X509Data/ds:X509Certificate",
    namespaces=SAML_NS
)
```

### SHA-1 Algorithm URI Detection
```python
# Source: CONTEXT.md D-05; SAML metadata algorithm URI conventions
SHA1_INDICATORS = ("sha1", "sha-1")

def _is_sha1_uri(uri: str) -> bool:
    lower = uri.lower()
    return any(ind in lower for ind in SHA1_INDICATORS)

# DS SignatureMethod (in signed metadata wrapper)
sig_methods = root.findall(".//ds:SignatureMethod", namespaces=SAML_NS)
for sm in sig_methods:
    uri = sm.get("Algorithm", "")
    if _is_sha1_uri(uri):
        # flag: source="SignatureMethod"

# AlgSupport SigningMethod (in metadata extensions)
signing_methods = root.findall(".//alg:SigningMethod", namespaces=SAML_NS)
for sm in signing_methods:
    uri = sm.get("Algorithm", "")
    if _is_sha1_uri(uri):
        # flag: source="SigningMethod"
```

### EntityID Extraction
```python
# Source: SAML 2.0 metadata spec — EntityDescriptor is the root element
entity_id = root.get("entityID", "")
# OR for federation metadata with EntitiesDescriptor wrapper:
entity_descriptor = root.find("md:EntityDescriptor", namespaces=SAML_NS)
if entity_descriptor is not None:
    entity_id = entity_descriptor.get("entityID", "")
```

### X.509 DER Parsing from SAML XML
```python
# Source: cryptography library; matches TLS scanner cert-parsing approach in quirk
import base64
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.primitives.asymmetric import rsa, ec

def _parse_cert_der(cert_text: str) -> dict | None:
    """Parse base64 DER cert from SAML XML element text."""
    try:
        der = base64.b64decode(
            cert_text.replace(" ", "").replace("\n", "").replace("\r", "").strip()
        )
        cert = load_der_x509_certificate(der)
        pub = cert.public_key()
        key_alg, key_bits = "UNKNOWN", None
        if isinstance(pub, rsa.RSAPublicKey):
            key_alg, key_bits = "RSA", pub.key_size
        elif isinstance(pub, ec.EllipticCurvePublicKey):
            key_alg, key_bits = "ECDSA", pub.key_size
        return {
            "key_alg": key_alg,
            "key_bits": key_bits,
            "serial": format(cert.serial_number, 'x'),
            "not_after": cert.not_valid_after_utc.isoformat(),
        }
    except Exception:
        return None
```

### OIDC Discovery Parsing
```python
# Source: RFC 8414 (OAuth 2.0 Authorization Server Metadata), OIDC Core spec
def _parse_oidc_discovery(data: dict, url: str, timeout: int) -> list[dict]:
    """Extract algorithm declarations from OIDC discovery document."""
    results = []
    issuer = data.get("issuer", url)
    for field in ("id_token_signing_alg_values_supported",
                  "request_object_signing_alg_values_supported"):
        algs = data.get(field, [])
        for alg in algs:
            results.append({
                "alg": alg,
                "source_field": field,
                "issuer": issuer,
            })
    return results
```

### CLASSIFIER: SAML_ALG_MAP Entries for _ALGORITHM_TABLE
```python
# Source: Existing classifier.py pattern (DNSSEC section lines 149-159)
# Add to _ALGORITHM_TABLE in quirk/cbom/classifier.py:
# SAML algorithm URI short names and OIDC alg strings
"rsa":   (CryptoPrimitive.PKE, 0, 112),       # Already present — RSA in general
"sha1":  (CryptoPrimitive.HASH, 0, 80),        # SHA-1 URI finding
"rs256": (CryptoPrimitive.SIGNATURE, 0, 112),  # Already present — OIDC alg
"rs384": (CryptoPrimitive.SIGNATURE, 0, 112),  # Already present
"rs512": (CryptoPrimitive.SIGNATURE, 0, 112),  # Already present
"es256": (CryptoPrimitive.SIGNATURE, 0, 128),  # Already present
```

Note: Most OIDC alg strings (RS256, ES256, HS256, etc.) are ALREADY in `_ALGORITHM_TABLE` from the JWT section. The SAML-specific additions are only for algorithm URI short names not currently present.

### TDD Mock Structure for lxml (avoids requiring lxml in test env)
```python
# Source: Pattern from test_dnssec_scanner.py mock approach; adapted for lxml
from unittest.mock import patch, MagicMock

def test_saml_signing_cert_rsa1024_critical():
    """Mock httpx response + defusedxml.lxml.fromstring to return structured XML."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner.defused_ET") as mock_et, \
         patch("quirk.scanner.saml_scanner.httpx") as mock_httpx:

        # Mock HTTP response returning SAML XML
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"<EntityDescriptor...>"
        mock_httpx.get.return_value = mock_resp

        # Mock parsed XML tree — return real lxml-like mock
        mock_root = MagicMock()
        mock_et.fromstring.return_value = mock_root

        # Set up findall to return cert elements
        cert_elem = MagicMock()
        cert_elem.text = "<base64-encoded-rsa1024-cert>"
        mock_root.findall.return_value = [cert_elem]
        mock_root.get.return_value = "https://idp.example.com/"

        # Patch cert parsing to return known RSA-1024 result
        with patch("quirk.scanner.saml_scanner._parse_cert_der") as mock_parse:
            mock_parse.return_value = {"key_alg": "RSA", "key_bits": 1024,
                                       "serial": "deadbeef", "not_after": "2030-01-01T00:00:00+00:00"}
            endpoints = scan_saml_targets(["http://localhost:8080"])

        assert any(ep.cert_pubkey_size == 1024 and ep.cert_pubkey_alg == "RSA"
                   for ep in endpoints)
```

### SimpleSAMLphp Docker Compose Service (saml profile)
```yaml
# Source: kenchan0130/simplesamlphp Docker Hub + CONTEXT.md D-18 through D-21
simplesamlphp:
  image: kenchan0130/simplesamlphp
  profiles: ["saml"]
  environment:
    SIMPLESAMLPHP_SP_ENTITY_ID: "http://localhost:8080/simplesaml/module.php/saml/sp/metadata.php/default-sp"
    SIMPLESAMLPHP_SP_ASSERTION_CONSUMER_SERVICE: "http://localhost:8080/simplesaml/module.php/saml/sp/saml2-acs.php/default-sp"
    SIMPLESAMLPHP_SP_SINGLE_LOGOUT_SERVICE: "http://localhost:8080/simplesaml/module.php/saml/sp/saml2-logout.php/default-sp"
    SIMPLESAMLPHP_IDP_ENABLE: "true"
  volumes:
    - ./simplesamlphp/cert/server.crt:/var/www/simplesamlphp/cert/server.crt:ro
    - ./simplesamlphp/cert/server.key:/var/www/simplesamlphp/cert/server.key:ro
  ports:
    - "8080:8080"
  healthcheck:
    test: ["CMD", "curl", "-sf", "http://localhost:8080/simplesaml/saml2/idp/metadata.php"]
    interval: 10s
    timeout: 5s
    retries: 6
    start_period: 20s
```

### RSA-1024 Cert Generation (one-time, committed to repo)
```bash
# Source: OpenSSL standard commands; matches DNSSEC pre-generated zone approach
# Run once, commit server.crt and server.key to repo
openssl genrsa -out server.key 1024
openssl req -new -x509 -key server.key -out server.crt -days 3650 \
    -subj "/CN=chaos-simplesamlphp-idp/O=ChaosLab/C=US"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pysaml2 for SAML parsing | lxml + defusedxml (pip-only) | REQUIREMENTS.md v4.2 | pysaml2 requires xmlsec1 system binary — excluded from pip-only constraint |
| Inline lxml.etree parsing | defusedxml.lxml wrapper | Security best practice | XXE prevention is mandatory for enterprise security scanner |
| Single cert per IdP | One CryptoEndpoint per cert per use-type | D-02 | Supports IdP key rotation scenarios (multiple active signing certs) |

**Deprecated/outdated:**
- python3-saml / onelogin-saml2: Requires xmlsec1 system binary. Out of scope.
- `lxml.etree.fromstring()` directly: Use `defusedxml.lxml.fromstring()` instead — direct parse is XXE-vulnerable.

## Open Questions

1. **Does SimpleSAMLphp emit `<alg:SigningMethod>` elements in metadata by default?**
   - What we know: D-05 documents two SHA-1 URI sources; the primary path is `<ds:SignatureMethod>` in signed metadata; `<alg:SigningMethod>` is in extensions.
   - What's unclear: SimpleSAMLphp 2.x may not include `alg:SigningMethod` extensions by default — cert key inspection may be the only reliable path for the chaos lab test.
   - Recommendation: Build the SHA-1 URI detection for both paths as specified, but design the chaos lab integration test to assert on the RSA-1024 cert finding (SAML-01 success criteria), which is definitive regardless of alg URI presence. The `alg:SigningMethod` path can be tested with synthetic XML in unit tests.

2. **kenchan0130/simplesamlphp exact cert mount path**
   - What we know: Standard SimpleSAMLphp cert path is `/var/www/simplesamlphp/cert/`; D-18 cites this image.
   - What's unclear: The specific image version's filesystem layout may differ from the standard — worth verifying at implementation time with `docker run ... ls /var/www/simplesamlphp/cert/`.
   - Recommendation: Plan 02 should include an implementation step that runs the container and verifies the metadata endpoint actually reflects the mounted cert before writing the test assertion. Docker daemon is available on the dev machine (Docker 29.3.1 installed) but not currently running.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| lxml | saml_scanner.py XML parsing | ✗ (not in core venv) | — (declared in [identity] extras) | Import guard returns [] if absent; install with `pip install quirk[identity]` |
| defusedxml | saml_scanner.py XXE-safe parse | ✓ | 0.7.1 | — (no fallback; required with lxml) |
| httpx | metadata/OIDC HTTP fetch | ✓ | 0.28.1 | — |
| cryptography | X.509 DER cert parsing | ✓ | core dep | — |
| Docker | SimpleSAMLphp chaos lab | ✓ (installed, not running) | 29.3.1 | Start daemon before chaos lab tests |
| kenchan0130/simplesamlphp | SAML-06 chaos lab | Not verified (daemon not running) | latest | — (integration tests skip without daemon) |
| pytest | Test framework | ✓ | in venv | — |

**Missing dependencies with no fallback:**
- lxml: Required for actual XML parsing. Scanner degrades gracefully (returns []) but tests of XML-parsing logic require either lxml installed or full mocking of the defusedxml.lxml.fromstring call chain.

**Missing dependencies with fallback:**
- Docker daemon not currently running: Start with `open -a Docker` on macOS before running chaos lab integration tests. Integration tests use `@pytest.mark.skipif` with `QUIRK_INTEGRATION_TESTS` env var — safe to skip in normal CI.

**Pre-existing test failure:** `tests/test_pdf_export.py::test_pdf_export_endpoint` fails with HTTP 500 (pre-existing, unrelated to Phase 19). All other 238 tests pass.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (in project venv) |
| Config file | pytest.ini or pyproject.toml [tool.pytest] |
| Quick run command | `.venv/bin/python -m pytest tests/test_saml_scanner.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAML-01 | Fetch SAML XML + extract signing cert key type/size via lxml+SAML_NS | unit (mocked) | `pytest tests/test_saml_scanner.py -k "signing_cert" -x` | ❌ Wave 0 |
| SAML-02 | Parse encryption certs separately from signing certs | unit (mocked) | `pytest tests/test_saml_scanner.py -k "encryption_cert" -x` | ❌ Wave 0 |
| SAML-03 | OIDC discovery → alg enumeration from `id_token_signing_alg_values_supported` | unit (mocked) | `pytest tests/test_saml_scanner.py -k "oidc" -x` | ❌ Wave 0 |
| SAML-04 | RSA <2048 → CRITICAL; SHA-1 URI → HIGH severity classification | unit (pure) | `pytest tests/test_saml_scanner.py -k "severity or sha1" -x` | ❌ Wave 0 |
| SAML-05 | protocol="SAML" CryptoEndpoints; saml_scan_json populated; CBOM builder branch | unit (mocked) | `pytest tests/test_saml_scanner.py -k "cbom or protocol or json" -x` | ❌ Wave 0 |
| SAML-06 | SimpleSAMLphp chaos lab returns CRITICAL for RSA-1024 cert | integration (skipif) | `QUIRK_INTEGRATION_TESTS=1 pytest tests/test_saml_scanner.py -k "chaos_lab" -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/test_saml_scanner.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -q`
- **Phase gate:** Full suite green (minus pre-existing PDF export failure) before `/gsd:verify-work`

### Wave 0 Gaps (Plan 01 creates)
- [ ] `tests/test_saml_scanner.py` — covers SAML-01 through SAML-06 (RED scaffold)
- [ ] `quirk/scanner/saml_scanner.py` — stub module with `LXML_AVAILABLE` guard and function signatures

## Sources

### Primary (HIGH confidence)
- Existing codebase: `quirk/scanner/dnssec_scanner.py` — structural pattern to replicate exactly
- Existing codebase: `quirk/scanner/jwt_scanner.py` — HTTP fetch pattern, import guard, error handling
- Existing codebase: `quirk/cbom/builder.py` lines 351-355 — DNSSEC elif branch to mirror
- Existing codebase: `quirk/cbom/classifier.py` — `_ALGORITHM_TABLE` extension pattern
- Existing codebase: `run_scan.py` lines 460-474 — DNSSEC scan block to follow
- `.planning/phases/19-saml-oidc-scanner/19-CONTEXT.md` — all D-01 through D-23 decisions
- `.planning/REQUIREMENTS.md` §SAML — SAML-01 through SAML-06 requirement text

### Secondary (MEDIUM confidence)
- SAML 2.0 metadata specification: namespace URIs `urn:oasis:names:tc:SAML:2.0:metadata` and `http://www.w3.org/2000/09/xmldsig#` — well-established, no version uncertainty
- RFC 8414 (OAuth 2.0 Authorization Server Metadata): `id_token_signing_alg_values_supported` field name — stable RFC, not changing
- Python cryptography library: `RSAPublicKey.key_size`, `load_der_x509_certificate()` — confirmed present in project venv

### Tertiary (LOW confidence)
- kenchan0130/simplesamlphp exact cert mount path: `var/www/simplesamlphp/cert/` — based on standard SimpleSAMLphp layout; verify at implementation time
- Whether `<alg:SigningMethod>` elements appear in kenchan0130/simplesamlphp default metadata: MEDIUM confidence it does not by default; unit tests cover the code path with synthetic XML regardless

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 19 |
|-----------|-------------------|
| PEP 8 for all Python changes | saml_scanner.py, classifier.py, builder.py edits must be PEP 8 compliant |
| Keep diffs minimal — avoid unnecessary refactors | Do not restructure builder.py or classifier.py beyond adding the SAML branch/entries |
| After changes, run `python -m compileall` and relevant tests | Verification step after each plan |
| If detection logic changes, update `labs/*/expected_results.md` accordingly | N/A for Phase 19 (new scanner, not changing existing detection logic) |
| Obsidian phase notes: create draft at phase start | Execute-phase agent responsibility |
| Update docs/UAT-SERIES.md after phase | Execute-phase agent responsibility |

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — lxml/defusedxml/httpx/cryptography all confirmed in project deps; roles unambiguous
- Architecture: HIGH — DNSSEC scanner provides exact structural template; all decisions locked in CONTEXT.md
- Pitfalls: HIGH — namespace trap, defusedxml dependency on lxml, and DER whitespace are verified from codebase inspection; SimpleSAMLphp latency and cert mount from general Docker/PHP experience (MEDIUM for those two)
- Test patterns: HIGH — directly mirrors test_dnssec_scanner.py structure

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable domain — lxml/SAML specs don't change; SimpleSAMLphp image tags may update)
