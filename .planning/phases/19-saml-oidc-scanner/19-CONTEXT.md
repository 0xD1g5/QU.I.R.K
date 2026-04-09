# Phase 19: SAML/OIDC Scanner - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. fetches SAML IdP metadata XML and OIDC discovery endpoints, extracts signing and
encryption certificates (with key size and algorithm) plus algorithm URI declarations, classifies
weak crypto (RSA < 2048 = CRITICAL, SHA-1 URI = HIGH), and stores results in the CBOM via
`protocol="SAML"` CryptoEndpoints and `saml_scan_json` in the database.

Scanner module, classifier extension, CBOM builder integration, and SimpleSAMLphp chaos lab
profile with RSA-1024 weak signing cert. OIDC scanning is scoped to algorithm declaration
enumeration from discovery endpoints — not full OIDC flow.

</domain>

<decisions>
## Implementation Decisions

### OIDC Target Configuration
- **D-01:** OIDC discovery endpoints share the `saml_targets` list — no new config field. Scanner
  attempts to parse each URL as SAML metadata XML first; if the response is JSON (or the URL
  path contains `.well-known`), it treats it as an OIDC discovery document. No `enable_oidc` or
  `oidc_targets` field additions to `ConnectorsCfg`. Phase 17's schema is final for this phase.

### SAML CryptoEndpoint Schema
- **D-02:** One `CryptoEndpoint` row per cert per use-type (signing or encryption). `service_detail`
  format: `{entity_id}|use=signing|serial={serial_hex}` or `|use=encryption|serial={serial_hex}`.
  Cert serial extracted from DER bytes via `cryptography.x509.load_der_x509_certificate()` —
  already in core deps via TLS scanner.
- **D-03:** For OIDC algorithm declaration findings: one `CryptoEndpoint` per algorithm string
  from `id_token_signing_alg_values_supported` (and `request_object_signing_alg_values_supported`
  if present). `service_detail` = `oidc-discovery|id_token_signing_alg`.
  `cert_pubkey_alg` = the alg string (e.g., `RS256`, `RS384`). `cert_pubkey_size` = key size
  derived from alg string where deterministic (RS256 → 2048 assumed min; only RSA algs produce
  a size finding).
- **D-04:** SHA-1 algorithm URI findings: one `CryptoEndpoint` per URI occurrence found.
  `service_detail` = `{entity_id}|algo_uri={full_uri}|source={SignatureMethod|SigningMethod}`.
  `cert_pubkey_alg` = shortened form (e.g., `SHA1`). Severity = HIGH per SAML-04.

### SHA-1 Algorithm URI Detection Scope
- **D-05:** Parse two XML locations for SHA-1 algorithm URIs:
  1. `<ds:SignatureMethod Algorithm="...">` — in the signed metadata wrapper (metadata was
     signed with a weak algorithm)
  2. `<alg:SigningMethod Algorithm="...">` — in metadata extensions declaring preferred
     signing algorithms for the IdP
  Both sources use `http://www.w3.org/2000/09/xmldsig#rsa-sha1` (and variants) as the SHA-1
  indicator. Any URI containing `sha1` or `sha-1` (case-insensitive) in the local fragment
  is flagged. Cert signature hash algorithm (the cert's own `signature_hash_algorithm`) is NOT
  separately flagged as a URI finding — it is captured via the cert key-size finding (SAML-01).

### SAML_NS and XML Namespaces
- **D-06:** Declare a module-level `SAML_NS` dict constant in `saml_scanner.py` per SAML-01.
  Minimum required namespaces:
  ```python
  SAML_NS = {
      "md":  "urn:oasis:names:tc:SAML:2.0:metadata",
      "ds":  "http://www.w3.org/2000/09/xmldsig#",
      "alg": "urn:oasis:names:tc:SAML:metadata:algsupport",
      "mdui": "urn:oasis:names:tc:SAML:metadata:ui",
  }
  ```
  lxml XPath calls always use explicit `namespaces=SAML_NS` argument — no namespace stripping.

### Severity Classification
- **D-07:** RSA key size severity (for both signing and encryption certs):
  - CRITICAL: key_bits < 2048
  - HIGH: key_bits == 2048 (quantum-vulnerable RSA, still commonly required)
  - SAFE (no finding): ECDSA P-256, P-384, Ed25519 certs
- **D-08:** SHA-1 algorithm URI severity = HIGH regardless of source (SignatureMethod or
  SigningMethod extension). Matches SAML-04 text exactly.
- **D-09:** OIDC alg severity: RS256/RS384/RS512 = HIGH (RSA, quantum-vulnerable at typical
  sizes); ES256/ES384/ES512 = informational only (no finding); HS256/HS384 = informational
  (symmetric, out of scope for PKI posture). Unknown alg strings = LOW with note.

### Scanner Structure
- **D-10:** Function signature: `scan_saml_targets(targets: list, timeout: int = 10, logger=None) -> list[CryptoEndpoint]`
  Matches DNSSEC and JWT scanner signatures exactly.
- **D-11:** Import guard at top of `saml_scanner.py`:
  ```python
  try:
      import lxml.etree as ET
      import defusedxml.lxml as defused_ET
      LXML_AVAILABLE = True
  except ImportError:
      LXML_AVAILABLE = False
  ```
  Use `defusedxml.lxml.fromstring()` for all XML parsing to prevent XXE attacks. Fall back
  gracefully if lxml not installed (log warning, return []).
- **D-12:** Sequential target processing — one target at a time, no threading. HTTP fetches
  are fast enough for typical consultant target lists (5-20 IdP metadata URLs).
- **D-13:** SSL verification disabled on metadata fetch (`verify=False`) — IdP metadata
  endpoints frequently use self-signed certs in enterprise environments. Matches JWT scanner
  behavior exactly.
- **D-14:** Follow redirects (up to 3 hops) — some IdPs redirect their metadata URL to an
  internal CDN or load balancer.
- **D-15:** On error (unreachable, non-XML response, parse failure): log warning, skip target,
  continue. Store error detail in `saml_scan_json` under an `"errors"` key for forensics.

### run_scan.py Integration
- **D-16:** SAML scan phase block added after dnssec_endpoints section, before final endpoint
  aggregation. Guarded by `cfg.connectors.enable_saml and cfg.connectors.saml_targets`.
  Wrapped in `_phase_timer(run_stats, "saml_scanning")`.

### saml_scan_json Structure
- **D-17:** Flat per-target dict stored as JSON array in `saml_scan_json`:
  ```json
  [
    {
      "url": "https://idp.example.com/metadata.xml",
      "type": "saml",
      "entity_id": "https://idp.example.com/",
      "signing_certs": [{"serial": "...", "key_alg": "RSA", "key_bits": 1024, "not_after": "..."}],
      "encryption_certs": [{"serial": "...", "key_alg": "RSA", "key_bits": 2048, "not_after": "..."}],
      "sha1_uris": [{"source": "SignatureMethod", "uri": "http://..."}],
      "errors": []
    },
    {
      "url": "https://auth.example.com/.well-known/openid-configuration",
      "type": "oidc",
      "issuer": "https://auth.example.com",
      "id_token_signing_alg_values_supported": ["RS256", "ES256"],
      "request_object_signing_alg_values_supported": ["RS256"],
      "errors": []
    }
  ]
  ```

### Chaos Lab — SimpleSAMLphp
- **D-18:** Docker image: `kenchan0130/simplesamlphp` — official SimpleSAMLphp image, PHP 8+,
  supports custom certs via environment variables and volume mounts.
- **D-19:** RSA-1024 signing cert and key: pre-generated with `openssl genrsa 1024` and
  `openssl req -x509`, committed to repo under
  `quantum-chaos-enterprise-lab/simplesamlphp/cert/server.crt` and `server.key`.
  Deterministic cert (same fingerprint/serial every run). Matches DNSSEC pre-signed zone
  approach.
- **D-20:** Docker Compose `saml` profile — starts only the SimpleSAMLphp container. Not
  grouped under `identity` profile. `docker compose --profile saml up` per success criteria 5.
- **D-21:** SimpleSAMLphp metadata URL exposed at `http://localhost:8080/simplesaml/saml2/idp/metadata.php`
  by default (standard SimpleSAMLphp URL path). Scanner test target: `http://localhost:8080`.

### CBOM Integration
- **D-22:** `build_cbom()` gains `elif ep.protocol == "SAML":` branch, calling
  `_register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)`.
- **D-23:** `classifier.py` gains `SAML_ALG_MAP` for algorithm URI strings and alg name
  classification. At minimum: RSA (various sizes) → QUANTUM_VULNERABLE; SHA-1 URI →
  DEPRECATED; ECDSA/EdDSA → SAFE.

### Claude's Discretion
- Internal helper function naming (`_fetch_metadata`, `_parse_signing_certs`, `_parse_oidc_discovery`, etc.)
- Exact XPath expressions for each field extracted
- Whether `SAML_NS` lives in `saml_scanner.py` or a shared `quirk/scanner/xml_utils.py`
- SimpleSAMLphp authsource configuration (the default demo authsource is sufficient for metadata-only scanning)
- Exact SimpleSAMLphp docker-compose.yml env vars and volume mount paths

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §SAML — SAML-01 through SAML-06 full requirement text
- `.planning/ROADMAP.md` §Phase 19 — success criteria, plan structure (2 plans), dependencies

### Phase 17 infrastructure (already implemented)
- `quirk/config.py` — `ConnectorsCfg.enable_saml`, `ConnectorsCfg.saml_targets` fields
- `quirk/models.py` — `ScanResult.saml_scan_json = Column(Text, nullable=True)`
- `quirk/db.py` — migration helper; `saml_scan_json` already in column list (line ~40)

### Scanner patterns to follow
- `quirk/scanner/jwt_scanner.py` — HTTP-based scanner reference: import guard, httpx fetch
  with `verify=False`, one `CryptoEndpoint` per key, error handling
- `quirk/scanner/dnssec_scanner.py` — closest structural reference (same milestone pattern):
  sequential scanning, `_phase_timer` integration, `saml_scan_json` JSON structure pattern

### CBOM integration
- `quirk/cbom/builder.py` — `build_cbom()` protocol dispatch (`elif ep.protocol == ...`),
  `_register_algorithm()` usage and signature
- `quirk/cbom/classifier.py` — `classify_algorithm()` function, existing algorithm maps
  (extend with `SAML_ALG_MAP`)

### Scan orchestration
- `run_scan.py` — dnssec_endpoints block (lines ~461-474) — SAML block follows same pattern

### Chaos lab
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing profile structure (`saml` profile
  added here, following `dnssec` profile pattern)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CryptoEndpoint` model fields: `cert_pubkey_alg`, `cert_pubkey_size`, `service_detail`,
  `protocol` — all reused for SAML findings
- `cryptography.x509.load_der_x509_certificate()` — already used in TLS scanner for cert
  parsing; reuse for cert serial extraction from SAML XML `<ds:X509Certificate>` DER bytes
- `_register_algorithm()` in `cbom/builder.py` — handles algorithm registration with key size
- `_phase_timer` context manager in `run_scan.py` — wraps scan phases for timing
- `httpx` already imported in jwt_scanner.py — same library for SAML metadata fetch

### Established Patterns
- Scanner module in `quirk/scanner/` with `scan_<type>_targets()` returning `List[CryptoEndpoint]`
- Import guard: `try: import X; X_AVAILABLE = True except ImportError: X_AVAILABLE = False`
- Error handling: log warning, skip target, continue — no exceptions raised to caller
- `verify=False` on all HTTP fetches — enterprise environments frequently use internal CAs
- CBOM builder: `elif ep.protocol == "TYPE":` dispatch for algorithm registration

### Integration Points
- `run_scan.py` lines ~461-474 (after dnssec block) — insert SAML scan phase here
- `quirk/cbom/builder.py` — add `elif ep.protocol == "SAML"` branch after DNSSEC branch
- `quirk/cbom/classifier.py` — add `SAML_ALG_MAP` constant
- `quantum-chaos-enterprise-lab/docker-compose.yml` — add `saml` profile with SimpleSAMLphp

</code_context>

<specifics>
## Specific Ideas

- Federation multi-cert support: `service_detail` includes cert serial (`entity_id|use=signing|serial={hex}`)
  so organizations with multiple active signing certs (rotation windows) produce distinct findings per cert
- defusedxml.lxml must be used for XML parsing to prevent XXE attacks — this is non-negotiable
  for an enterprise security scanner (XXE in a security tool would be a serious vulnerability)
- SimpleSAMLphp pre-baked cert approach matches DNSSEC pattern — deterministic chaos lab is
  critical for TDD (tests can assert on known cert fingerprint/serial)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 19-saml-oidc-scanner*
*Context gathered: 2026-04-08*
