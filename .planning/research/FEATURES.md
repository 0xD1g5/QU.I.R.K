# Feature Research: Identity Protocol Crypto Scanners

**Domain:** Identity protocol cryptographic inventory (Kerberos, SAML/OAuth, DNSSEC)
**Milestone:** v4.2 Identity Crypto
**Researched:** 2026-04-08
**Confidence:** HIGH (authoritative RFCs + official docs verified; implementation patterns confirmed via impacket/dnspython/python-saml sources)

---

## Context: What Already Exists

QU.I.R.K. v4.1 ships the following scanner infrastructure that new modules must plug into:

- `CryptoEndpoint` SQLite model with additive JSON blob columns (`_scan_json`) per scanner
- `build_cbom()` in `quirk/cbom/builder.py` dispatches on `ep.protocol` — new protocol strings need handling in Pass 1 (algorithms) and Pass 3 (protocols)
- `classify_algorithm()` in `quirk/cbom/classifier.py` is the single lookup table; new etypes/algorithms must be added here
- `ProtocolPropertiesType` enum allows: `TLS`, `SSH`, `IPSEC`, `IKE`, `SSTP`, `WPA`, `OTHER`, `UNKNOWN` — Kerberos/DNSSEC/SAML map to `OTHER`
- Existing pattern: each scanner returns `List[CryptoEndpoint]` with `protocol=` set to a new protocol string constant

---

## Scanner 1: Kerberos Etype Enumeration

### What It Does

Sends an unauthenticated AS-REQ probe to port 88 (KDC) advertising a set of known etypes. The KDC's error response (`KRB5KDC_ERR_PREAUTH_REQUIRED`, error code 25) includes the `etype-info2` pre-authentication data, which lists the etypes the KDC actually supports for the target principal. This is a passive read of KDC capability — no credentials required, no actual authentication.

**Probe mechanics:**
1. Open TCP/UDP socket to host:88
2. Craft AS-REQ ASN.1 DER packet offering all known etypes (1-26, 23, 17, 18)
3. Parse AS-REP or error response for `etype-info2` or `etype-info` PA data
4. Extract the etype integer list from PA data — these are the KDC-supported etypes
5. Map each integer to algorithm name + quantum classification

**Key insight on quantum classification:** Kerberos uses symmetric encryption for session keys, not public-key cryptography. RC4 and DES are classically weak (brute-forceable, collision attacks) but not vulnerable to Shor's algorithm. The quantum threat is classical weakness, not post-quantum relevance. AES-128+ with sufficiently large key sizes is resistant to Grover's algorithm (provides ~64-bit quantum security at AES-128; AES-256 provides ~128-bit quantum security). The classification used by QUIRK should reflect classical risk for RC4/DES, and note AES-256 as quantum-adequate.

### Etype Number Reference Table

| etype | Algorithm Name | Strength Class | QUIRK Classification | Notes |
|-------|---------------|---------------|---------------------|-------|
| 1 | des-cbc-crc | WEAK | quantum-vulnerable (classically broken) | Deprecated RFC 6649 |
| 2 | des-cbc-md4 | WEAK | quantum-vulnerable (classically broken) | Deprecated RFC 6649 |
| 3 | des-cbc-md5 | WEAK | quantum-vulnerable (classically broken) | Deprecated RFC 6649 |
| 7 | des3-cbc-sha1 | DEPRECATED | quantum-vulnerable | Deprecated MIT krb5 >=1.18 |
| 17 | aes128-cts-hmac-sha1-96 | STRONG | quantum-adequate (64-bit QS) | AES-128 safe vs Grover |
| 18 | aes256-cts-hmac-sha1-96 | STRONG | quantum-safe | AES-256 primary recommendation |
| 19 | aes128-cts-hmac-sha256-128 | STRONG | quantum-adequate (64-bit QS) | RFC 8009, SHA-256 PRF |
| 20 | aes256-cts-hmac-sha384-192 | STRONG | quantum-safe | RFC 8009, preferred |
| 23 | rc4-hmac (arcfour-hmac) | WEAK | quantum-vulnerable (classically broken) | RC4 stream cipher; Windows default pre-2019 |
| 24 | rc4-hmac-exp | WEAK | quantum-vulnerable (classically broken) | Export-grade RC4; effectively banned |
| 25 | camellia128-cts-cmac | STRONG | quantum-adequate | RFC 6803 |
| 26 | camellia256-cts-cmac | STRONG | quantum-safe | RFC 6803 |

**Critical etype for findings:** etype 23 (RC4-HMAC) is the primary finding. Windows domains that still support RC4 are vulnerable to credential relay, Kerberoasting, and Pass-the-Hash attacks. Microsoft disabled RC4 by default in Windows Server 2025 but it persists in legacy environments.

**Etype bitmap note:** Active Directory uses an `msDS-SupportedEncryptionTypes` attribute bitmask:
- Bit 1 = DES-CBC-CRC
- Bit 2 = DES-CBC-MD5
- Bit 4 = RC4-HMAC
- Bit 8 = AES128-CTS-HMAC-SHA1-96
- Bit 16 = AES256-CTS-HMAC-SHA1-96

### Table Stakes: Kerberos

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| AS-REQ probe to port 88 (TCP+UDP) | Core mechanism for etype discovery | MEDIUM | Requires raw socket or impacket/minikerberos; no auth needed |
| Parse etype-info2 PA data from error response | The only unauthenticated etype read path | MEDIUM | AS error code 25 (PREAUTH_REQUIRED) contains PA data |
| Etype integer → algorithm name mapping | Without this the finding is unreadable | LOW | Static lookup table; 12 entries covers full range |
| RC4-HMAC (etype 23) flagged as CRITICAL finding | RC4 is the primary finding consultants need | LOW | High-value, fast to implement |
| DES etypes (1,2,3) flagged as CRITICAL | Legacy detection | LOW | Rare but catastrophic when found |
| AES-only classification as PASS | Show green state; not just red findings | LOW | AES-128 = adequate, AES-256 = safe |
| Store raw etype list in `kerberos_scan_json` | Preserves full detail for CBOM/reporting | LOW | Follow JWT/SSH pattern |
| CryptoEndpoint with `protocol="KERBEROS"` | Required for CBOM dispatch | LOW | Add to builder.py switch |
| CBOM algorithm entries per etype found | Each supported etype = CBOM algorithm component | MEDIUM | Map etype → CryptoPrimitive.BLOCK_CIPHER or HASH |
| Chaos lab: Samba DC with RC4 enabled | Scanner validation requires a real KDC target | HIGH | Docker Samba 4 DC with known etype config |

### Differentiators: Kerberos

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Etype bitmap decode from `msDS-SupportedEncryptionTypes` | Shows what AD attribute value produced the etype set | MEDIUM | Requires LDAP query (separate from AS-REQ probe); LDAP 389/636 |
| Report etype 23 vs etype 18/20 ratio across targets | Shows scope of RC4 exposure across domain | LOW | Aggregate from multi-target scan |
| Distinguish KDC-supports-RC4 vs AD-account-enforces-AES | Subtlety: KDC may support RC4 but AES-only account prevents use | HIGH | Requires per-account probe with dummy SPN; complex |
| Detect Kerberoastable SPN accounts | Unauthenticated SPN enumeration via AS-REQ | HIGH | Significant pentest overlap; scope creep risk |

### Anti-Features: Kerberos

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full Kerberos authentication / TGT retrieval | Seems comprehensive | Requires credentials; out of agentless model; pentest territory | Stick to unauthenticated AS-REQ probe only |
| User enumeration via KRB5KDC_ERR_C_PRINCIPAL_UNKNOWN | Pentest capability | Not a crypto audit; scope creep; may trigger IDS | Probe against known principal (e.g. `krbtgt`) or dummy name |
| TGS-REQ etype probing | Shows service-level etype | Requires TGT; auth dependency | AS-REQ probe covers KDC-wide etype support sufficiently |
| LDAP msDS-SupportedEncryptionTypes connector | More accurate etype bitmap | Separate auth model; adds LDAP dependency; scope creep | Phase differentiator at most; not v4.2 MVP |

---

## Scanner 2: SAML/OAuth Metadata Scanning

### What It Does

Fetches SAML IdP/SP metadata XML documents and/or OIDC discovery endpoints, extracts all cryptographic declarations, and produces findings. No SAML authentication is performed — this is pure metadata document fetch and parse.

**Two sub-modes:**

**SAML metadata mode:**
- Fetch URL (e.g., `https://idp.example.com/saml/metadata`) or read local XML file
- Parse `<md:KeyDescriptor>` elements for signing/encryption certificates
- Extract X.509 certificate → parse `cert_pubkey_alg`, `cert_pubkey_size`, `cert_not_after`
- Parse `<md:Extensions>` / `<alg:SigningMethod>` / `<alg:DigestMethod>` for declared algorithm support (SAML Metadata Algorithm Support profile)
- Extract `<ds:SignatureMethod Algorithm="...">` from any signed metadata
- Flag weak algorithms: SHA-1 (`xmldsig#sha1`), MD5, RSA < 2048-bit

**OIDC/OAuth discovery mode:**
- Fetch `/.well-known/openid-configuration`
- Extract `id_token_signing_alg_values_supported`, `token_endpoint_auth_signing_alg_values_supported`, `request_object_signing_alg_values_supported`
- Extract `jwks_uri` → fetch JWKS → already handled by `jwt_scanner.py` (reuse)
- Flag `RS256` with short RSA keys, `HS256` (symmetric, shared secret), `none` (critical)

**Note:** The existing `jwt_scanner.py` already handles OIDC JWKS discovery (the `/.well-known/openid-configuration` path). The SAML scanner adds the SAML metadata XML path and the algorithm declarations from discovery documents (separate from the JWKS key material).

### SAML Algorithm URI Reference Table

| Algorithm URI | Algorithm | Strength Class | QUIRK Classification |
|--------------|-----------|---------------|---------------------|
| `http://www.w3.org/2000/09/xmldsig#rsa-sha1` | RSA + SHA-1 | WEAK | quantum-vulnerable |
| `http://www.w3.org/2000/09/xmldsig#dsa-sha1` | DSA + SHA-1 | WEAK | quantum-vulnerable |
| `http://www.w3.org/2000/09/xmldsig#sha1` (digest) | SHA-1 | WEAK | quantum-vulnerable |
| `http://www.w3.org/2001/04/xmldsig-more#rsa-sha256` | RSA-2048 + SHA-256 | ADEQUATE | quantum-vulnerable (RSA) |
| `http://www.w3.org/2001/04/xmldsig-more#rsa-sha384` | RSA + SHA-384 | ADEQUATE | quantum-vulnerable (RSA) |
| `http://www.w3.org/2001/04/xmldsig-more#rsa-sha512` | RSA + SHA-512 | ADEQUATE | quantum-vulnerable (RSA) |
| `http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256` | ECDSA P-256 + SHA-256 | STRONG | quantum-vulnerable (ECC) |
| `http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha384` | ECDSA P-384 + SHA-384 | STRONG | quantum-vulnerable (ECC) |
| `http://www.w3.org/2001/04/xmlenc#aes128-cbc` (encryption) | AES-128-CBC | ADEQUATE | quantum-adequate |
| `http://www.w3.org/2001/04/xmlenc#aes256-cbc` (encryption) | AES-256-CBC | STRONG | quantum-safe |

**Note on quantum classification:** RSA and ECDSA in SAML ARE quantum-vulnerable via Shor's algorithm (they protect public-key operations used to sign assertions). SHA-1-based algorithms are classically weak and quantum-vulnerable (SHA-1 provides ~80-bit classical security, further weakened by chosen-prefix collisions).

**Signing cert key type:** The X.509 certificate in `<KeyDescriptor use="signing">` is the primary finding surface. RSA-1024 signing certs are critical; RSA-2048 is adequate but quantum-vulnerable; self-signed is a secondary risk finding.

### Table Stakes: SAML/OAuth

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Fetch SAML metadata XML from URL (HTTP/HTTPS) | Standard metadata exchange mechanism | LOW | httpx GET, no auth, parse XML |
| Parse `<KeyDescriptor use="signing">` certificates | Primary crypto finding surface | MEDIUM | lxml XPath; extract base64 cert → cryptography.x509 |
| Extract cert key type + size from signing cert | Core field: RSA-1024 vs RSA-2048 vs ECDSA | LOW | Use `cryptography` lib already in stack |
| Extract cert expiry from signing cert | Operational finding; expired signing certs break federation | LOW | `cert_not_after` column reuse |
| Parse `<alg:SigningMethod>` URI declarations | Shows declared algorithm support | MEDIUM | SAML Metadata Algorithm Support profile (OASIS) |
| Parse OIDC `id_token_signing_alg_values_supported` | Standard OAuth discovery field | LOW | JSON parse; map to existing JWT classifier |
| Flag SHA-1 signing methods as HIGH severity | SHA-1 is the primary SAML weakness in the field | LOW | Simple URI substring match |
| Flag RSA key < 2048-bit as CRITICAL | Below NIST minimum | LOW | Check cert_pubkey_size |
| Store full metadata in `saml_scan_json` | Full detail preservation | LOW | Follow jwt_scan_json pattern |
| `protocol="SAML"` or `protocol="OIDC"` in CryptoEndpoint | CBOM dispatch | LOW | Add to builder.py |
| Chaos lab: mock IdP serving weak-algorithm metadata | Scanner validation | MEDIUM | nginx or simple Flask serving static XML |

### Differentiators: SAML/OAuth

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Parse `<KeyDescriptor use="encryption">` certs too | Encryption key in SAML is separate from signing key | LOW | Same extraction path; use="encryption" |
| Multi-IdP metadata aggregate support (federation) | Enterprise federations (InCommon, eduGAIN) publish aggregate XML | HIGH | Large XML files; streaming parse needed |
| SAML metadata signature validation (self-signed check) | Flag unsigned or weakly-signed metadata documents | MEDIUM | `<Signature>` on EntityDescriptor; check presence + alg |
| Detect `<NameIDFormat>` transient vs persistent (privacy finding) | Not crypto but identity hygiene | LOW | Out of scope for CBOM; skip |
| Compare IdP-declared vs SP-declared algorithm support | Mismatch = potential downgrade | HIGH | Requires both IdP and SP metadata; complex |
| OIDC `request_object_signing_alg_values_supported` | Additional alg declaration field | LOW | Add to discovery parse |

### Anti-Features: SAML/OAuth

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| SAML authentication / SP-initiated flow | Seems more complete | Requires SP credentials/config; breaks agentless model; pentest-adjacent | Metadata fetch is the right scope |
| Validate SAML assertion signatures in captured traffic | Deep inspection | Requires network tap or proxy; passive capture model; out of scope | Document limitation; recommend federation audit |
| OAuth token introspection endpoint | Shows live token algorithms | Requires client_id/secret; auth dependency | JWKS already handled by jwt_scanner |
| Check all transitive federation IdPs | Comprehensive coverage | Combinatorial explosion; rate limits; scope creep | Scan top-level metadata only |

---

## Scanner 3: DNSSEC Algorithm Audit

### What It Does

Queries DNSKEY and DS records for a target domain using dnspython, classifies the signing algorithm numbers, and produces findings for deprecated or quantum-vulnerable algorithms.

**Query sequence:**
1. Query `DNSKEY` RRset for the target domain (zone apex)
2. Query `DS` RRset at the parent zone (one label up) — shows what hash algorithm the parent uses to delegate trust
3. For each DNSKEY: extract algorithm number, key size (RSA modulus length), key tag, flags (KSK=257 vs ZSK=256)
4. For each DS: extract digest type (1=SHA-1, 2=SHA-256, 4=SHA-384), key tag, algorithm number
5. Classify algorithm against RFC 8624 / RFC 9905 table
6. Detect: unsigned (no DNSKEY returned), deprecated algorithms, SHA-1 DS records

**DNS resolver note:** Scanner must use a validating resolver (or a specified nameserver) with `DO` (DNSSEC OK) bit set. `dnspython` supports this natively via `dns.resolver.Resolver` with `use_dnssec=True` or manual `dns.message` construction.

### DNSSEC Algorithm Number Reference Table

| Algorithm | Name | RFC 8624 Signing | RFC 9905 Update | QUIRK Classification | Quantum Status |
|-----------|------|-----------------|-----------------|---------------------|----------------|
| 1 | RSAMD5 | MUST NOT | MUST NOT | critical-weak | quantum-vulnerable + classically broken |
| 3 | DSA | MUST NOT | MUST NOT | critical-weak | quantum-vulnerable |
| 5 | RSASHA1 | MUST NOT | MUST NOT (RFC 9905) | critical-weak | quantum-vulnerable |
| 6 | DSA-NSEC3-SHA1 | MUST NOT | MUST NOT | critical-weak | quantum-vulnerable |
| 7 | RSASHA1-NSEC3-SHA1 | MUST NOT | MUST NOT (RFC 9905) | critical-weak | quantum-vulnerable |
| 8 | RSASHA256 | MUST | - | adequate | quantum-vulnerable (RSA; Shor's) |
| 10 | RSASHA512 | NOT RECOMMENDED | - | adequate | quantum-vulnerable (RSA; Shor's) |
| 12 | ECC-GOST | MUST NOT | - | critical-weak | quantum-vulnerable |
| 13 | ECDSAP256SHA256 | MUST | - | strong | quantum-vulnerable (ECC; Shor's) |
| 14 | ECDSAP384SHA384 | MAY | - | strong | quantum-vulnerable (ECC; Shor's) |
| 15 | ED25519 | RECOMMENDED | - | strong | quantum-vulnerable (ECC; Shor's) |
| 16 | ED448 | MAY | - | strong | quantum-vulnerable (ECC; Shor's) |

**All current DNSSEC algorithms are quantum-vulnerable** via Shor's algorithm because all use public-key cryptography (RSA, ECDSA, EdDSA). This is the key CBOM finding: DNSSEC provides no post-quantum protection for DNS authenticity. RSASHA1/SHA-1-based algorithms additionally fail classical security requirements (RFC 9905, published 2025).

**DS digest type table:**
| Digest Type | Name | Status |
|-------------|------|--------|
| 1 | SHA-1 | DEPRECATED (RFC 8624); flag as finding |
| 2 | SHA-256 | RECOMMENDED |
| 4 | SHA-384 | ACCEPTABLE |

### Table Stakes: DNSSEC

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Query DNSKEY RRset via dnspython | Core mechanism | LOW | `dns.resolver.resolve(domain, 'DNSKEY')` with DO bit |
| Query DS RRset at parent zone | Chain of trust check | LOW | Strip first label: `example.com` → DS at `com` |
| Algorithm number → name + classification | Without this the number is opaque | LOW | Static lookup table; 12 entries |
| Flag algorithms 1,3,5,6,7,12 as CRITICAL | Deprecated per RFC 8624 / RFC 9905 | LOW | Simple integer lookup |
| Flag RSASHA1 (5) and RSASHA1-NSEC3-SHA1 (7) as MUST NOT | RFC 9905 published 2025 | LOW | Highest priority finding |
| Detect unsigned zone (no DNSKEY, NXDOMAIN or empty) | Zone with no DNSSEC = finding | LOW | Empty result = "not signed" |
| Flag SHA-1 DS digest type (1) | SHA-1 in parent delegation is weak | LOW | DS.digest_type == 1 |
| Distinguish KSK vs ZSK by flags (257 vs 256) | KSK is higher value finding | LOW | DNSKEY.flags field |
| Extract RSA key size from DNSKEY for RSA algorithms | RSA key length is a primary finding field | MEDIUM | Parse DNSKEY RDATA public key bytes |
| Store `dnskey_scan_json` / `dnssec_scan_json` blob | Full detail preservation | LOW | Follow jwt_scan_json pattern |
| `protocol="DNSSEC"` in CryptoEndpoint | CBOM dispatch | LOW | port=53, host=domain |
| Chaos lab: BIND/Knot DNS zone with RSASHA1 signing | Scanner validation | HIGH | Docker BIND 9 with deliberately weak zone |

### Differentiators: DNSSEC

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| NSEC vs NSEC3 detection (zone walking exposure) | NSEC enables zone enumeration; NSEC3 mitigates | LOW | Check `NSEC`/`NSEC3PARAM` record presence |
| DS record at parent present/absent check (broken chain) | DS without matching DNSKEY = validation failure | MEDIUM | Cross-correlate DS key tag with DNSKEY key tags |
| Check DNSKEY algorithm vs DS algorithm consistency | Algorithm mismatch = misconfiguration | MEDIUM | DS algorithm number must match DNSKEY algorithm |
| DNSKEY RRSIG signature expiry check | Zone signing roll-over failure = validation failure | MEDIUM | Query RRSIG, check expiry timestamp |
| Report "all DNSSEC algorithms are quantum-vulnerable" in summary | High-value PQC talking point for consultants | LOW | Single aggregate finding; key differentiator for QUIRK |
| Multi-zone batch scan | Efficiency for clients with many domains | LOW | Already supported by multi-target scan architecture |

### Anti-Features: DNSSEC

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full DNSSEC chain validation (validate signatures) | Completeness | Requires recursive resolver + all parent chain queries; complex; dnspython does this but it's slow | Audit algorithm numbers only; note chain validation is out of scope |
| Zone transfer (AXFR) for full zone audit | Comprehensive inventory | Requires DNS server allow-transfer; almost never permitted externally; scope creep | Single-domain DNSKEY query is correct approach |
| DNSKEY signing oracle / timing tests | Deep validation | Requires active probing beyond passive inventory; pentest territory | Not crypto inventory; exclude |
| Monitor DNSSEC rollover over time | Continuous monitoring | Requires persistent agent; SaaS milestone feature | Note as future capability |

---

## Feature Dependencies

```
[Kerberos Scanner]
    └──requires──> port 88 TCP/UDP reachable
    └──requires──> quirk/cbom/classifier.py (new etype entries)
    └──requires──> quirk/cbom/builder.py (KERBEROS protocol dispatch)
    └──uses──> CryptoEndpoint.kerberos_scan_json (new column)

[SAML Scanner]
    └──requires──> httpx (already in stack from jwt_scanner)
    └──requires──> cryptography lib (already in stack from TLS scanner)
    └──requires──> lxml (new dependency for XML parse)
    └──partly-reuses──> jwt_scanner.py (OIDC discovery + JWKS already handled)
    └──uses──> CryptoEndpoint.saml_scan_json (new column)

[DNSSEC Scanner]
    └──requires──> dnspython (new dependency; pip-installable)
    └──requires──> quirk/cbom/classifier.py (DNSSEC algorithm entries)
    └──uses──> CryptoEndpoint.dnssec_scan_json (new column)

[Identity Dashboard Tab]
    └──requires──> all 3 scanners producing data
    └──requires──> FastAPI route exposing identity findings
    └──enhances──> existing findings table (add protocol filter for KERBEROS/SAML/OIDC/DNSSEC)
```

### Dependency Notes

- **SAML scanner requires lxml:** lxml is the standard for safe XML parsing in Python; `xml.etree.ElementTree` is insufficient for XML namespace handling in SAML. Add to `pyproject.toml` optional `[identity]` extras group.
- **DNSSEC scanner requires dnspython:** Pure Python DNS library. Already used in some Python security tooling. Pip-installable; no system dependency. Add to optional extras.
- **Kerberos scanner dependency choice:** Two options — `impacket` (heavyweight, offensive tooling, 40+ transitive deps) vs `minikerberos` (pure Python, lighter) vs raw socket with `pyasn1` for ASN.1 encoding. Recommendation: raw socket + `pyasn1` for AS-REQ construction. `pyasn1` is pip-installable, lightweight, and avoids the impacket security association. Adds `pyasn1` dependency only.
- **SAML scanner overlaps with JWT scanner:** For OIDC targets, `jwt_scanner.py` already fetches `/.well-known/openid-configuration` and the JWKS. SAML scanner should not re-fetch JWKS — it should parse the discovery document's `*_signing_alg_values_supported` fields only, then hand off JWKS to the existing JWT scanner.

---

## CBOM Integration Points

### New CryptoPrimitive Mappings Needed

Add to `quirk/cbom/classifier.py`:

| Algorithm Key | CryptoPrimitive | NIST Level | Classical Level | Notes |
|--------------|----------------|-----------|----------------|-------|
| `kerberos-rc4-hmac` | BLOCK_CIPHER | 0 | 40 | RC4 stream; 40-bit effective |
| `kerberos-des-cbc-crc` | BLOCK_CIPHER | 0 | 56 | DES 56-bit |
| `kerberos-aes128-cts` | BLOCK_CIPHER | 1 | 128 | AES-128; quantum-adequate |
| `kerberos-aes256-cts` | BLOCK_CIPHER | 1 | 256 | AES-256; quantum-safe |
| `dnssec-rsasha256` | SIGNATURE | 0 | 112 | RSA-2048; quantum-vulnerable |
| `dnssec-rsasha1` | SIGNATURE | 0 | 80 | SHA-1; classically weak |
| `dnssec-ecdsap256sha256` | SIGNATURE | 0 | 128 | ECDSA P-256; quantum-vulnerable |
| `dnssec-ed25519` | SIGNATURE | 0 | 128 | Ed25519; quantum-vulnerable |
| `saml-rsa-sha1` | SIGNATURE | 0 | 80 | RSA+SHA-1; weak |
| `saml-rsa-sha256` | SIGNATURE | 0 | 112 | RSA+SHA-256; adequate |
| `saml-ecdsa-sha256` | SIGNATURE | 0 | 128 | ECDSA+SHA-256; adequate |

### CryptoEndpoint Schema Additions

New columns (additive, no migration required):

| Column | Type | Scanner | Purpose |
|--------|------|---------|---------|
| `kerberos_scan_json` | Text | Kerberos | Full etype list + KDC response details |
| `saml_scan_json` | Text | SAML | Full metadata parse: certs, alg URIs, endpoints |
| `dnssec_scan_json` | Text | DNSSEC | DNSKEY/DS records, algorithm numbers, flags |

### CBOM Builder Protocol Dispatch

In `build_cbom()`, add to the `ep.protocol` dispatch:
- `"KERBEROS"` → algorithm components per etype; protocol component with `ProtocolPropertiesType.OTHER`
- `"SAML"` / `"OIDC"` → algorithm + certificate components; protocol `OTHER`
- `"DNSSEC"` → algorithm components per DNSKEY; protocol `OTHER`

**Existing CertificateProperties reuse:** For SAML signing certs extracted from `<KeyDescriptor>`, the existing Pass 2 certificate component logic applies without modification — populate `cert_pubkey_alg`, `cert_pubkey_size`, `cert_not_before`, `cert_not_after`, `cert_subject`, `cert_issuer` on the CryptoEndpoint.

---

## Dashboard: Identity Tab Considerations

### Data Shape

The Identity tab surfaces findings from three new protocol types. The minimum viable display mirrors the existing Findings table filtered to `protocol IN ('KERBEROS', 'SAML', 'OIDC', 'DNSSEC')`.

| UI Element | Content | Source |
|------------|---------|--------|
| Summary cards | Count of weak etypes found, count of SHA-1 SAML certs, count of deprecated DNSSEC algos | Aggregated query |
| Findings list | Per-endpoint findings with severity, protocol badge, algorithm detail | `crypto_endpoints` table |
| Kerberos section | Host → supported etypes → RC4/AES status per KDC | kerberos_scan_json parsed |
| SAML/OIDC section | IdP URL → signing cert key type/expiry → declared alg methods | saml_scan_json parsed |
| DNSSEC section | Domain → DNSKEY algorithm → DS digest → signed/unsigned status | dnssec_scan_json parsed |

### Display Considerations

- Protocol badge colors: KERBEROS (orange), SAML/OIDC (purple), DNSSEC (teal) — distinct from existing TLS (blue) and SSH (green)
- "Not signed" DNSSEC zone: display as HIGH finding with distinct icon (not an algorithm finding, a presence finding)
- SAML cert expiry: reuse existing cert inventory display logic; just add protocol filter
- Kerberos RC4 finding: highest visual priority; RC4 on a KDC affects the entire Windows domain

---

## MVP Definition

### Launch With (v4.2)

These are the minimum features to ship v4.2 Identity Crypto milestone:

- [ ] Kerberos: AS-REQ probe (TCP+UDP port 88), etype-info2 parse, RC4/DES/AES classification, `kerberos_scan_json` storage
- [ ] SAML: URL fetch, `<KeyDescriptor>` cert extraction, `<SigningMethod>` URI parse, cert key type/size/expiry
- [ ] OIDC: `id_token_signing_alg_values_supported` from discovery doc (complement to existing jwt_scanner, not replace it)
- [ ] DNSSEC: DNSKEY + DS query via dnspython, algorithm classification per RFC 8624/RFC 9905, SHA-1 DS detection, unsigned zone detection
- [ ] classifier.py: new etype/DNSSEC/SAML algorithm entries
- [ ] builder.py: KERBEROS/SAML/DNSSEC protocol dispatch (Pass 1 + Pass 3)
- [ ] Chaos lab: Docker containers for all 3 (Samba DC with RC4, mock SAML IdP, BIND with RSASHA1)
- [ ] Identity tab in dashboard (findings table filtered + summary cards)

### Add After Validation (v4.2.x)

- [ ] LDAP `msDS-SupportedEncryptionTypes` bitmap decode — trigger: consultant feedback that domain-level attribute is needed
- [ ] DNSSEC NSEC vs NSEC3 detection — trigger: client asks about zone enumeration exposure
- [ ] DS broken chain detection — trigger: consultant UAT identifies false-clean report on misconfigured zone
- [ ] SAML encryption `<KeyDescriptor>` — trigger: client has encrypted assertions

### Future Consideration (v5+)

- [ ] Post-quantum DNSSEC algorithm support (ML-DSA algorithm numbers not yet registered in IANA; IETF draft stage as of 2026) — defer to when standard is finalized
- [ ] SAML assertion signature validation (requires SP context; SaaS model)
- [ ] Kerberos account-level etype probing (requires credentials; out of agentless model)
- [ ] DNSKEY rollover monitoring (SaaS continuous monitoring feature)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Kerberos RC4 etype detection | HIGH | MEDIUM | P1 |
| DNSSEC RSASHA1/unsigned detection | HIGH | LOW | P1 |
| SAML SHA-1 cert/alg detection | HIGH | MEDIUM | P1 |
| CBOM integration (all 3 scanners) | HIGH | MEDIUM | P1 |
| Chaos lab (all 3) | HIGH | HIGH | P1 |
| Identity dashboard tab | HIGH | MEDIUM | P1 |
| DNSSEC DS SHA-1 digest detection | MEDIUM | LOW | P1 |
| OIDC alg_values_supported parse | MEDIUM | LOW | P1 |
| SAML encryption cert extraction | MEDIUM | LOW | P2 |
| DNSSEC NSEC/NSEC3 detection | MEDIUM | LOW | P2 |
| LDAP etype bitmap decode | MEDIUM | MEDIUM | P2 |
| DS broken chain check | LOW | MEDIUM | P3 |
| DNSKEY RRSIG expiry check | LOW | MEDIUM | P3 |

---

## Dependency Library Summary

| Library | Scanner | Status | Install |
|---------|---------|--------|---------|
| `httpx` | SAML (URL fetch) | Already in stack (jwt_scanner) | No change |
| `cryptography` | SAML (cert parse) | Already in stack (TLS scanner) | No change |
| `lxml` | SAML (XML parse) | New dependency | `pip install lxml` |
| `dnspython` | DNSSEC | New dependency | `pip install dnspython` |
| `pyasn1` | Kerberos AS-REQ | New dependency | `pip install pyasn1` |

All new dependencies are pure Python, pip-installable, and have no system-level requirements. They are compatible with the "offline capable" constraint as long as the packages are pre-installed.

---

## Sources

- [Encrypt: Kerberos encryption types — MIT Kerberos Documentation](https://web.mit.edu/kerberos/krb5-latest/doc/admin/enctypes.html)
- [IANA Kerberos Encryption Type Numbers](https://www.iana.org/assignments/kerberos-parameters/kerberos-parameters.xhtml)
- [Microsoft: Detect and Remediate RC4 Usage in Kerberos](https://learn.microsoft.com/en-us/windows-server/security/kerberos/detect-remediate-rc4-kerberos)
- [Microsoft: Decrypting the Selection of Supported Kerberos Encryption Types](https://techcommunity.microsoft.com/blog/coreinfrastructureandsecurityblog/decrypting-the-selection-of-supported-kerberos-encryption-types/1628797)
- [RFC 9905: Deprecating the Use of SHA-1 in DNSSEC Signature Algorithms](https://www.rfc-editor.org/rfc/rfc9905.html)
- [RFC 8624 bis: Algorithm Implementation Requirements and Usage Guidance for DNSSEC](https://datatracker.ietf.org/doc/html/draft-hardaker-dnsop-rfc8624-bis-01)
- [dnspython DNSSEC documentation](https://dnspython.readthedocs.io/en/latest/dnssec.html)
- [OASIS: SAML v2.0 Metadata Profile for Algorithm Support](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-algsupport-v1.0-cs01.html)
- [OpenID Connect Discovery 1.0 Specification](https://openid.net/specs/openid-connect-discovery-1_0.html)
- [CycloneDX Cryptographic Protocol Use Case](https://cyclonedx.org/use-cases/cryptographic-protocol/)
- [cyclonedx-python-lib CryptoPrimitive/ProtocolPropertiesType docs](https://cyclonedx-python-library.readthedocs.io/en/v10.4.0/autoapi/cyclonedx/model/crypto/index.html)
- [Post-Quantum Cryptography for Authentication: Enterprise Migration Guide 2026](https://securityboulevard.com/2026/03/post-quantum-cryptography-for-authentication-the-enterprise-migration-guide-2026/)
- [SIDN: EdDSA-based algorithms for DNSSEC under development](https://www.sidn.nl/en/news-and-blogs/eddsa-based-algorithms-for-dnssec-under-development)
- [minikerberos: pure Python Kerberos library](https://github.com/skelsec/minikerberos)
- [IETF: Quantum Relief with TLS and Kerberos (symmetric key quantum resistance)](https://www.ietf.org/archive/id/draft-vanrein-tls-kdh-08.html)

---

*Feature research for: QU.I.R.K. v4.2 Identity Crypto milestone — Kerberos, SAML/OAuth, DNSSEC scanners*
*Researched: 2026-04-08*
