# Project Research Summary

**Project:** QU.I.R.K. v4.2 — Identity Crypto Milestone
**Domain:** Identity protocol cryptographic inventory (Kerberos, SAML/OAuth, DNSSEC)
**Researched:** 2026-04-08
**Confidence:** HIGH (stack + architecture verified from source; MEDIUM on chaos lab container specifics)

---

## Executive Summary

The v4.2 Identity Crypto milestone extends QU.I.R.K.'s agentless scanning model to three new
protocol families: Kerberos etype enumeration, SAML/OIDC metadata parsing, and DNSSEC algorithm
auditing. All three scanners follow the same CryptoEndpoint → SQLite → CBOM pipeline that governs
TLS/SSH/JWT scanners in v4.1. The correct integration pattern is well-understood from codebase
inspection: write a JSON blob column per scanner, set a new `protocol=` string constant, add
elif branches in `build_cbom()`, and register new algorithm entries in `classifier.py`. Because
this pattern is additive and proven, the core architectural risk is low — but there are
significant protocol-specific implementation traps that must be addressed at design time, not
discovered during testing.

The most important resolved conflict in this synthesis concerns library choice and build order.
**impacket** (not pyasn1) is the correct Kerberos library: its `kerberosv5.py` handles
`KDC_ERR_PREAUTH_REQUIRED` without raising, giving clean access to `PA-ETYPE-INFO2` without
credential material. However, impacket's pyOpenSSL transitive dependency creates a version
conflict risk that must be contained by installing impacket in a new `[identity]` optional extras
group, separate from core deps. On **build order**, PITFALLS research overrides ARCHITECTURE's
suggested Kerberos-first order: DNSSEC should come before Kerberos because it validates the
classifier extension pattern cheaply (pure DNS queries, no socket work, no ASN.1) before the
project commits to the raw Kerberos TCP/UDP probe path. SAML sits between them in complexity.

The key consulting finding this milestone enables is stark: **all current DNSSEC signing
algorithms are quantum-vulnerable** via Shor's algorithm, and RC4-HMAC Kerberos etypes remain
common in legacy Windows domains. These findings are high-value, have no equivalent in the
existing TLS/SSH/JWT scanners, and map directly to billable remediation work. The implementation
work is bounded and well-specified; the chaos lab infrastructure is the highest-complexity
deliverable due to container startup timing and DNSSEC zone signing configuration requirements.

---

## Key Findings

### Recommended Stack

The existing QU.I.R.K. stack (sslyze, cyclonedx-python-lib, httpx, cryptography, PyJWT) needs
only five new dependencies, all pip-installable with no system binaries required. These are
grouped into a single `[identity]` optional extras group to isolate impacket's pyOpenSSL
transitive pull from core deps.

**New dependencies in `[identity]` extras:**
- `impacket>=0.13.0,<0.14` — raw Kerberos AS-REQ/ETYPE-INFO2 wire protocol; the only Python
  library that implements this without requiring a host krb5 installation; pin `<0.14` to avoid
  surprise breaking changes
- `dnspython[dnssec]>=2.8.0` — DNSKEY/DS record queries with Algorithm enum; zero new
  transitive deps because `cryptography` is already in the core stack
- `lxml>=6.0` — SAML metadata XML parsing with correct namespace support; ships binary wheels
  for Python 3.10-3.14 on all target platforms
- `defusedxml>=0.7.1` — XXE/XML bomb guard for untrusted SAML metadata; already transitively
  present in the venv but must be declared explicitly for a security tool
- `signxml>=4.4.0` — XMLDSig algorithm inspection; pure Python (no xmlsec1 binary); latest
  release March 2026

**Conflict resolution — impacket:** impacket 0.13.0 relaxed its pyOpenSSL pin (was `==`, now
`>=`). The conflict risk is MEDIUM, not LOW, because pyOpenSSL>=25.0.0 requires
cryptography>=46.0.0 while the existing stack requires only >=44.0. The `[identity]` extras
group isolates this. If a future upgrade requires `cryptography>=46.0` in core deps anyway, the
conflict disappears — the cryptography project maintains backward API compatibility.

**Library choice overruled — Kerberos:** FEATURES.md suggested pyasn1 for AS-REQ construction.
STACK.md wins: impacket's `kerberosv5.py` already encodes the correct PDU, handles TCP framing,
and parses ETYPE-INFO2. Building AS-REQ from scratch with pyasn1 is 200+ lines of fragile ASN.1
work for zero gain.

**What NOT to use:**
- `pysaml2` or `python3-saml` — both require the `xmlsec1` system binary, violating QU.I.R.K.'s
  pip-only constraint
- `python-gssapi` or `krb5` C bindings — require a working host Kerberos installation
  (krb5.conf, realm config); impacket speaks raw Kerberos over TCP with no host krb5 required
- `impacket` in core deps — must stay in `[identity]` extras to contain pyOpenSSL conflict risk

**Chaos lab Docker images (confirmed available):**
- Kerberos KDC: `smblds/smblds` (purpose-built CI image, KDC on port 88, minimal footprint)
- SAML IdP: `kenchan0130/simplesamlphp` (PHP8 Apache, SAML 2.0 IdP, metadata at
  `/simplesaml/saml2/idp/metadata.php`)
- DNSSEC authoritative: `internetsystemsconsortium/bind9:9.20` (official ISC image, supports
  `dnssec-policy` for inline zone signing with configurable algorithms)

---

### Expected Features

All three scanners operate in read-only agentless mode — no credentials, no agents, no active
exploitation. Each scanner targets a distinct network port and protocol family.

**Must have (table stakes for v4.2):**
- Kerberos: AS-REQ probe to port 88 (TCP + UDP fallback), parse PA-ETYPE-INFO2 from
  `KDC_ERR_PREAUTH_REQUIRED`, classify RC4-HMAC (etype 23) as HIGH and DES etypes (1,2,3) as
  CRITICAL, store `kerberos_scan_json`, emit `protocol="KERBEROS"` CryptoEndpoints
- SAML: HTTP fetch of IdP metadata XML, lxml parse of `<md:KeyDescriptor>` (signing and
  both-use certs), extract X.509 cert key type/size/expiry via DER decode, parse
  `<alg:SigningMethod>` URI, flag SHA-1 signing as HIGH, flag RSA < 2048-bit as CRITICAL, store
  `saml_scan_json`
- OIDC: parse `id_token_signing_alg_values_supported` from `/.well-known/openid-configuration`
  (complement to existing `jwt_scanner.py`, not a replacement)
- DNSSEC: `dns.resolver.resolve(domain, 'DNSKEY')` + `resolve(domain, 'DS')` via dnspython with
  DO bit, classify algorithms per RFC 8624 / RFC 9905 (2025), flag RSASHA1 (alg 5) and
  RSASHA1-NSEC3-SHA1 (alg 7) as CRITICAL MUST NOT, flag missing DNSSEC as HIGH, store
  `dnssec_scan_json`
- CBOM pipeline: new `_ALGORITHM_TABLE` entries for all 11 new algorithm keys; KERBEROS/SAML/
  DNSSEC elif branches in `build_cbom()` Pass 1 (algorithms) and Pass 3 (protocol components)
- Chaos lab: Samba DC with RC4-only etype config, SimpleSAMLphp with weak RSA-1024 signing cert,
  BIND9 with RSASHA1-signed zone and clean ECDSAP256SHA256 zone
- Dashboard: Identity tab with per-protocol summary cards and findings list

**Should have (adds consulting differentiation, targeted for v4.2.x post-validation):**
- SAML encryption `<KeyDescriptor use="encryption">` cert extraction
- DNSSEC NSEC vs NSEC3 detection (zone enumeration exposure surface)
- DS broken chain detection (mismatched key tags between DS and DNSKEY records)
- OIDC `request_object_signing_alg_values_supported` parsing

**Defer to v5+:**
- Post-quantum DNSSEC algorithm support (ML-DSA IANA numbers not yet registered; IETF draft as
  of 2026)
- SAML assertion signature validation (requires SP context; SaaS model)
- Kerberos account-level etype probing via LDAP `msDS-SupportedEncryptionTypes` (requires LDAP
  auth dependency; breaks agentless constraint)
- DNSKEY rollover monitoring (continuous monitoring; SaaS feature)

**Key quantum-safety insight:** Kerberos etype findings are primarily classical-risk findings
(RC4/DES are brute-forceable), not PQC-migration findings — AES-128/AES-256 session keys are
Grover-resistant. DNSSEC and SAML findings are true PQC-migration findings — all current DNSSEC
signing algorithms and all RSA/ECDSA SAML signing algorithms are Shor-vulnerable. This
distinction is important for the dashboard severity framing and report copy.

---

### Architecture Approach

The v4.2 identity scanners are purely additive changes to the existing architecture. The data
flow is identical to every scanner in v4.1: scanner module writes CryptoEndpoint rows with a
unique `protocol=` string and a `*_scan_json` blob column; `build_cbom()` dispatches on
`ep.protocol` to extract algorithm components; `compute_readiness_score()` consumes the evidence
dict; the dashboard API serializes `identity_findings` in the scan response. No structural
changes to the pipeline are required — only extensions.

**Major components and modification types:**

1. `quirk/scanner/kerberos_scanner.py` — NEW; AS-REQ probe via impacket.krb5.asn1, ETYPE-INFO2
   parse, TCP/UDP fallback logic
2. `quirk/scanner/saml_scanner.py` — NEW; httpx fetch + lxml/defusedxml parse + DER cert
   extraction; OIDC discovery JSON path separate from SAML XML path
3. `quirk/scanner/dnssec_scanner.py` — NEW; dnspython with DO bit, direct authoritative NS
   query, DNSKEY/DS classification per RFC 8624
4. `quirk/models.py` — MODIFY; three new nullable Text columns with additive migration guard
5. `quirk/config.py` — MODIFY; `enable_kerberos/saml/dnssec` flags + target lists in
   `ConnectorsCfg`
6. `quirk/cbom/classifier.py` — MODIFY; Kerberos etype strings + DNSSEC IANA algorithm number
   mapping table (`DNSSEC_ALG_MAP`)
7. `quirk/cbom/builder.py` — MODIFY; KERBEROS/SAML/DNSSEC elif branches in Pass 1 + Pass 3
8. `quirk/intelligence/evidence.py` + `scoring.py` — MODIFY; identity protocol counters and
   optional sub-score weights
9. `quirk/dashboard/api/routes/scan.py` + `schemas.py` — MODIFY; `IdentityFinding` model +
   `identity_findings` in `ScanLatestResponse`
10. `quantum-chaos-enterprise-lab/docker-compose.yml` — MODIFY; three new profiles

**Protocol string convention (new values):** `KERBEROS`, `SAML`, `DNSSEC` — these map to
`ProtocolPropertiesType.OTHER` in CycloneDX 1.6 (no native identity protocol type defined).

**One CryptoEndpoint row per target** (not per algorithm) — the SSH scanner is the canonical
model. Algorithm detail lives in the `*_scan_json` blob.

---

### Critical Pitfalls

1. **Kerberos probe sends credential material** — calling `getKerberosTGT()` without credentials
   returns `KDC_ERR_C_PRINCIPAL_UNKNOWN` before etype data is transmitted. Use raw
   `impacket.krb5.asn1` AS-REQ construction with no preauthentication data; the correct response
   is `KDC_ERR_PREAUTH_REQUIRED` (error code 25) containing `PA-ETYPE-INFO2`. This must be a
   design requirement, not discovered during chaos lab testing.

2. **Kerberos UDP/88 silently blocked** — enterprise firewalls block UDP/88 to force TCP. A
   UDP-only scanner returns empty results indistinguishable from "no KDC present." Implement
   TCP/88 fallback with explicit timeout; record `kerberos-unreachable` in `scan_error` when
   both transports fail.

3. **SAML namespace XPath silently returns empty** — lxml's `xpath()` / `findall()` ignores
   namespace prefixes without an explicit `nsmap` argument. Define `SAML_NS` as a module
   constant and pass it to every query. Real-world Azure AD and Okta metadata use `md:` and
   `ds:` prefixes; test fixtures that work with SimpleSAMLphp often break on these.

4. **SAML `<KeyDescriptor>` without `use` attribute** — Azure AD and Okta frequently omit `use`
   on the primary signing key (means "both signing and encryption"). Hard-coding
   `[@use='signing']` in XPath misses these entirely. Parse three categories: signing,
   encryption, and no-use (both).

5. **SAML certificate DER vs PEM** — `ds:X509Certificate` stores raw base64 (no PEM headers).
   Never construct PEM by string concatenation; use `x509.load_der_x509_certificate(
   base64.b64decode(raw_b64))` — DER parsing avoids line-break format issues entirely.

6. **DNSSEC `[dnssec]` extra not installed** — `pip install dnspython` without the extras gives
   base library that imports cleanly but raises `ImportError` at runtime inside `dns.dnssec`
   function bodies. Declare `dnspython[dnssec]` (not `dnspython`) in pyproject.toml; add an
   `DNSPYTHON_AVAILABLE` guard with a CI test that verifies it is True.

7. **DNSSEC system resolver strips DO bit** — corporate and containerized resolvers often strip
   DNSKEY/RRSIG records. Query authoritative NS records directly: resolve the zone's NS records
   first, then set `resolver.nameservers` to those IPs and `resolver.use_edns(edns=0,
   ednsflags=dns.flags.DO)`. Never use the system resolver for DNSKEY queries.

8. **DNSSEC algorithm numbers not in `_ALGORITHM_TABLE`** — DNSSEC uses IANA integer keys (5, 7,
   8, 13); the existing classifier uses string keys. Add `DNSSEC_ALG_MAP` integer → canonical
   name translation in the scanner (or classifier) before calling `classify_algorithm()`.

9. **SQLite additive column migration** — `create_all()` does not add columns to existing
   tables. New `*_scan_json` columns must be declared `nullable=True` and added via an
   idempotent `ALTER TABLE ADD COLUMN` guard in `db.py` startup (check `PRAGMA table_info`
   first). Test against a `quirk.db` created by v4.1.

10. **CBOM builder `else` treats unknown protocols as TLS** — if `build_cbom()` is not updated,
    KERBEROS/SAML/DNSSEC endpoints enter the TLS branch and produce garbage cipher-suite
    decomposition. Add explicit elif branches in the same phase as each scanner. Log a warning on
    unrecognized protocol values rather than silently falling through.

11. **Samba DC container takes 60–90 seconds to provision** — `samba-tool domain provision` runs
    after container start; the chaos lab test runner hits port 88 before KDC is ready. Add a
    healthcheck with `start_period: 90s` and require `depends_on: condition: service_healthy`.

12. **BIND9 chaos lab serves unsigned zone by default** — DNSSEC is not automatic in BIND9.
    Use `dnssec-policy` block in `named.conf` (BIND 9.16+) with an RSASHA1 policy for the weak
    test zone. Verify with `dig @localhost DNSKEY chaos.local` before claiming chaos lab is ready.

---

## Implications for Roadmap

Based on combined research, the recommended build order is **DNSSEC first, SAML second,
Kerberos third**, with a shared infrastructure phase before all scanners and a shared surface
phase after all scanners. PITFALLS research overrides ARCHITECTURE's suggested Kerberos-first
order: DNSSEC is the simplest scanner (pure DNS queries, no custom socket work), validating the
classifier extension pattern and CBOM pipeline integration cheaply before the project commits to
Kerberos raw socket / ASN.1 work.

### Phase 1: Infrastructure — Schema, Config, Migration Guard

**Rationale:** All three scanners depend on models.py columns and config.py flags. This phase
unblocks all downstream work and is low-risk, with no new libraries needed.

**Delivers:** Three new nullable Text columns (`kerberos_scan_json`, `saml_scan_json`,
`dnssec_scan_json`) with idempotent `ALTER TABLE ADD COLUMN` guard in `db.py`; `enable_kerberos/
saml/dnssec` flags and target list fields in `ConnectorsCfg`; `[identity]` extras group in
`pyproject.toml` with all five new dependencies declared.

**Pitfall addressed:** SQLite additive migration (Pitfall 9) — must be tested against a v4.1
`quirk.db` fixture before any scanner work begins.

**Research flag:** Standard pattern — no per-phase research needed.

---

### Phase 2: DNSSEC Scanner + Classifier + CBOM Integration

**Rationale:** DNSSEC is the simplest scanner: pure DNS queries over UDP/TCP using dnspython,
no custom socket construction, no ASN.1, no XML parsing. It validates the full
scanner → CryptoEndpoint → CBOM pipeline for identity protocols before tackling harder
scanners. The DNSSEC_ALG_MAP integer → classifier key translation establishes the pattern that
Kerberos etype mapping will follow.

**Delivers:** `quirk/scanner/dnssec_scanner.py` with DO-bit resolver, DNSKEY/DS classification
per RFC 8624/RFC 9905, unsigned-zone detection; `DNSSEC_ALG_MAP` in classifier; DNSSEC elif
branches in `build_cbom()` Pass 1 and Pass 3; BIND9 chaos lab profile (`dnssec` Docker Compose
profile) with RSASHA1-signed zone and clean ECDSAP256SHA256 zone.

**Features addressed:** All DNSSEC table stakes; RFC 9905 RSASHA1 MUST-NOT finding; SHA-1 DS
digest detection; unsigned zone HIGH finding.

**Pitfalls addressed:** Pitfalls 5 (dnssec extra), 6 (DO-bit resolver), 7 (algorithm number
mapping), 10 (CBOM builder elif), 12 (BIND9 unsigned zone default).

**Research flag:** Standard patterns — RFC 8624/RFC 9905 tables are authoritative, dnspython
API is well-documented. No per-phase research needed.

---

### Phase 3: SAML/OIDC Scanner + CBOM Integration

**Rationale:** SAML sits at medium complexity: XML namespace handling adds implementation risk
but the underlying technology (httpx + lxml + cryptography) is already in the stack. OIDC
discovery piggybacks on existing `jwt_scanner.py` infrastructure. Building SAML after DNSSEC
means the classifier extension pattern and CBOM pipeline are already proven.

**Delivers:** `quirk/scanner/saml_scanner.py` with SAML XML path (lxml + defusedxml, SAML_NS
constant, DER cert extraction) and OIDC JSON path (separate code paths); SAML elif in
`build_cbom()` Pass 1 + Pass 2 (certificate components reuse existing cert logic) + Pass 3;
SimpleSAMLphp chaos lab profile (`saml` Docker Compose profile) with RSA-1024 weak signing cert.

**Features addressed:** All SAML/OIDC table stakes; SHA-1 algorithm detection; RSA key size
classification; OIDC `id_token_signing_alg_values_supported` parsing.

**Pitfalls addressed:** Pitfalls 3 (namespace XPath), 4 (missing use= attribute), 8 (DER cert
parsing), 13 (Keycloak/SimpleSAMLphp startup timing).

**Research flag:** The SAML `<alg:SigningMethod>` declaration parsing and SAML Metadata
Algorithm Support profile (OASIS) is moderately niche — may benefit from a brief targeted
research pass to confirm edge cases for `<md:Extensions>` attribute variant handling.

---

### Phase 4: Kerberos Scanner + CBOM Integration

**Rationale:** Kerberos is the most complex scanner because it requires raw TCP/UDP socket work,
impacket ASN.1 construction, and careful handling of the KDC error response path. Building it
last means the CBOM pipeline integration is proven on two simpler scanners first, and the
`[identity]` extras group is already installed and tested.

**Delivers:** `quirk/scanner/kerberos_scanner.py` using `impacket.krb5.asn1` for bare AS-REQ
with no preauthentication, TCP/88 fallback when UDP/88 times out, ETYPE-INFO2 extraction from
`KDC_ERR_PREAUTH_REQUIRED` error response, RC4/DES/AES classification; KERBEROS elif in
`build_cbom()` Pass 1 and Pass 3; Samba DC chaos lab profile (`kerberos` Docker Compose profile)
with RC4-enabled etype config and healthcheck with `start_period: 90s`.

**Features addressed:** All Kerberos table stakes; RC4-HMAC CRITICAL finding; DES etype
detection; AES-only PASS state.

**Pitfalls addressed:** Pitfalls 1 (AS-REQ must not use credentials), 2 (UDP/88 fallback), 10
(CBOM builder elif for KERBEROS), 11 (Samba DC startup race).

**Research flag:** impacket's `kerberosv5.py` wire protocol behavior for bare AS-REQ
construction should be verified against the actual source before implementation begins. The
STACK.md research covers this but the specific ASN.1 field sequence for a no-preauth AS-REQ is
worth a targeted code review to avoid Pitfall 1.

---

### Phase 5: Intelligence Layer + Dashboard Identity Tab

**Rationale:** Requires all three scanners to exist and produce data. The intelligence layer
additions (evidence counters, scoring weights) and the React Identity tab surface findings that
need real scanner output to validate.

**Delivers:** `identity_weak_etype_count`, `saml_weak_signing_count`, `dnssec_weak_algo_count`
counters in `evidence.py`; optional identity sub-score weights in `scoring.py`; `IdentityFinding`
Pydantic model in `schemas.py`; `identity_findings` section in `GET /api/scan/latest` response;
React `<IdentityTab>` with per-protocol summary cards and findings list (KERBEROS=orange,
SAML/OIDC=purple, DNSSEC=teal badge colors).

**Features addressed:** Identity dashboard tab; all severity findings surfaced in UI; protocol
filter in findings table.

**Research flag:** Standard patterns — mirrors existing TLS/SSH tab structure. No per-phase
research needed.

---

### Phase Ordering Rationale

- **DNSSEC first** validates the classifier integer-key extension pattern (DNSSEC_ALG_MAP) and
  the CBOM builder elif pattern cheaply, before any raw socket work
- **SAML second** adds XML parsing complexity while reusing proven stack components (httpx,
  cryptography); cert extraction uses the existing `cert_pubkey_alg`/`cert_pubkey_size` field
  path without new schema work
- **Kerberos third** isolates the highest-risk implementation (impacket AS-REQ wire construction,
  TCP/UDP fallback, pyOpenSSL conflict) to a phase where CBOM integration is already proven
- **Dashboard last** is the correct sequence because identity_findings data must exist before
  the tab can be validated; chaos lab profiles can be built in parallel with the dashboard phase
  (they are test infrastructure, not a production dependency)

---

### Research Flags

**Needs targeted research before implementation:**
- Phase 4 (Kerberos): Verify the specific impacket.krb5.asn1 field sequence for a bare AS-REQ
  (no ENC-TIMESTAMP padata, no preauth data present) — the STACK.md research covers the
  behavior but not the exact call sequence. A 30-minute code review of impacket's
  `GetNPUsers.py` vs `kerberosv5.py` will confirm the correct construction pattern.
- Phase 3 (SAML): The SAML Metadata Algorithm Support extension (`<alg:SigningMethod>` under
  `<md:Extensions>`) is used by some IdPs but not all; confirm whether the chaos lab
  SimpleSAMLphp image emits these elements or whether algorithm discovery must fall back to the
  signing certificate key inspection path.

**Standard patterns (skip research-phase):**
- Phase 1 (Infrastructure): additive SQLite column pattern already documented in codebase
- Phase 2 (DNSSEC): RFC 8624/RFC 9905 tables are static; dnspython API is stable
- Phase 5 (Dashboard): mirrors existing tab structure with well-established React + FastAPI
  patterns

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library versions confirmed via PyPI; impacket pyOpenSSL conflict history reviewed via GitHub issues; binary wheel availability confirmed for target platforms |
| Features | HIGH | Authoritative sources: RFC 6649 (DES), RFC 8429 (RC4), RFC 8624 / RFC 9905 (DNSSEC), OASIS SAML specs, IANA Kerberos/DNSSEC registries; MIT Kerberos docs |
| Architecture | HIGH | Based on direct codebase inspection of v4.1; all pattern references (SSH scanner, JWT scanner, build_cbom dispatch) verified against existing code |
| Pitfalls | HIGH (protocol behavior) / MEDIUM (chaos lab containers) | Protocol pitfalls verified against source code and RFC behavior; chaos lab container startup timing is empirical, MEDIUM confidence on exact `start_period` values |

**Overall confidence:** HIGH

### Gaps to Address

- **impacket bare AS-REQ exact call sequence:** STACK.md confirms behavioral correctness but
  the precise `impacket.krb5.asn1` API call for a no-preauth AS-REQ should be verified against
  the latest 0.13.0 source before writing the scanner. Gap is small; resolve during Phase 4
  design.

- **smblds/smblds etype configuration:** The chaos lab recommends `smblds/smblds` with a custom
  entrypoint to provision RC4-only and AES-only realms. The exact `samba-tool` commands and
  `smb.conf` options needed to restrict etypes to RC4 at provision time are MEDIUM confidence.
  Test during Phase 4 chaos lab setup; fallback image `itherz/samba-ad-dc` is documented.

- **SAML `<alg:SigningMethod>` presence in practice:** Some real-world IdPs (especially older
  ADFS deployments) do not include `<md:Extensions>` / `<alg:SigningMethod>` in metadata. The
  fallback path (extract algorithm from the signing cert's public key) must be primary, not a
  fallback. Confirm this during Phase 3 design.

- **Post-quantum DNSSEC:** IETF drafts for ML-DSA DNSSEC algorithm numbers exist but are not
  finalized as of 2026. The classifier correctly represents all current DNSSEC algorithms as
  quantum-vulnerable (nist_level=0). This is accurate; no action needed until IANA registers
  PQC algorithm numbers.

---

## Sources

### Primary (HIGH confidence)

- [impacket fortra/impacket kerberosv5.py](https://github.com/fortra/impacket/blob/master/impacket/krb5/kerberosv5.py) — ETYPE_INFO2 extraction from KDC_ERR_PREAUTH_REQUIRED; sendReceive non-raise behavior
- [impacket fortra/impacket constants.py](https://github.com/fortra/impacket/blob/master/impacket/krb5/constants.py) — EncryptionTypes enum values (RC4=23, AES128=17, AES256=18)
- [RFC 8624](https://datatracker.ietf.org/doc/html/rfc8624) — DNSSEC algorithm implementation requirements and MUST NOT use designations
- [RFC 9905](https://datatracker.ietf.org/doc/html/rfc9905) — 2025 update; RSASHA1 (alg 5) and RSASHA1-NSEC3-SHA1 (alg 7) elevated to MUST NOT
- [IANA DNSSEC Algorithm Numbers registry](https://www.iana.org/assignments/dns-sec-alg-numbers/dns-sec-alg-numbers.xml) — authoritative algorithm number table
- [IANA Kerberos Encryption Type Numbers](https://www.iana.org/assignments/kerberos-parameters/kerberos-parameters.xhtml) — etype integer table
- [MIT Kerberos docs — encryption types](https://web.mit.edu/kerberos/krb5-latest/doc/admin/enctypes.html) — etype deprecation and RFC references
- [dnspython GitHub dns/dnssec.py](https://github.com/rthalley/dnspython/blob/main/dns/dnssec.py) — Algorithm enum values confirmed (RSASHA1=5, ECDSAP256SHA256=13, ED25519=15)
- [dnspython PyPI](https://pypi.org/project/dnspython/) — version 2.8.0 confirmed September 2025
- [impacket PyPI](https://pypi.org/project/impacket/) — version 0.13.0 confirmed October 2025
- [signxml PyPI](https://pypi.org/project/signxml/) — version 4.4.0 confirmed March 2026
- [lxml PyPI](https://pypi.org/project/lxml/) — version 6.0.2 confirmed; Python 3.8-3.14 wheels
- [defusedxml PyPI](https://pypi.org/project/defusedxml/) — version 0.7.1 stable since 2021

### Secondary (MEDIUM confidence)

- [kenchan0130/simplesamlphp Docker Hub](https://hub.docker.com/r/kenchan0130/simplesamlphp/) — SAML IdP chaos lab image; metadata endpoint location confirmed
- [internetsystemsconsortium/bind9 Docker Hub](https://hub.docker.com/r/internetsystemsconsortium/bind9) — official ISC BIND9 9.20 image confirmed
- [smblds/smblds Docker Hub](https://hub.docker.com/r/smblds/smblds) — Samba lightweight DS image confirmed; etype provision commands not verified
- [impacket pyOpenSSL conflict PR #1939](https://github.com/fortra/impacket/pull/1939) — 0.13.0 relaxed pyOpenSSL pin confirmed
- [SimpleSAMLphp issue #999](https://github.com/simplesamlphp/simplesamlphp/issues/999) — PEM header crash from raw base64 without newlines confirmed

### Tertiary (LOW confidence)

- SAML `<alg:SigningMethod>` adoption in real-world ADFS/Azure AD metadata — assumed sparse;
  cert-based fallback should be primary extraction path (needs validation in Phase 3)
- smblds/smblds etype configuration via `samba-tool` and smb.conf for RC4-only realm — needs
  validation during Phase 4 chaos lab setup

---

*Research completed: 2026-04-08*
*Ready for roadmap: yes*
