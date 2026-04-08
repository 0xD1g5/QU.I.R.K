# Stack Research: v4.2 Identity Crypto Scanners

**Domain:** Identity protocol cryptographic inventory (Kerberos, SAML/OAuth, DNSSEC)
**Researched:** 2026-04-08
**Confidence:** HIGH (core libraries verified via PyPI and official docs; chaos lab images MEDIUM via Docker Hub)

---

## Scope

This research covers ONLY the new capabilities needed for v4.2. The existing stack
(sslyze, cyclonedx-python-lib, httpx, cryptography, boto3, azure-sdk, PyJWT, etc.) is
validated and does not need new research. See `pyproject.toml` for existing pinned versions.

---

## Recommended Stack

### New Python Dependencies

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| `dnspython[dnssec]` | `>=2.8.0` | DNSSEC scanner — DNSKEY/DS record queries, Algorithm enum, RFC 8624 policy | Only production-grade Python DNS library with full DNSSEC record type support and Algorithm enum covering RSASHA1/RSASHA256/ECDSA/Ed25519. The `[dnssec]` extra pulls in `cryptography` (already in stack) for signature validation. Pure Python, no binary deps. |
| `impacket` | `>=0.13.0,<0.14` | Kerberos scanner — AS-REQ construction, ETYPE_INFO2 parsing from KDC_ERR_PREAUTH_REQUIRED | The only maintained Python library implementing raw Kerberos ASN.1 wire protocol. The `kerberosv5.py` module exposes the exact ETYPE_INFO2 probe pattern needed: send unauthenticated AS-REQ, read `PA_ETYPE_INFO2` from the `KDC_ERR_PREAUTH_REQUIRED` error response. Constants for RC4 (etype 23), AES128 (17), AES256 (18), DES variants (1-3) are already enumerated in `impacket.krb5.constants.EncryptionTypes`. |
| `lxml` | `>=6.0` | SAML metadata XML parsing — parse EntityDescriptor, extract KeyDescriptor/X509Certificate and `ds:SignatureMethod`/`ds:DigestMethod` nodes | Required by signxml and provides the fastest, most secure XML parser in the Python ecosystem. Already the recommended parser for any SAML/XMLDSig work. |
| `defusedxml` | `>=0.7.1` | XXE/XML bomb guard when parsing untrusted SAML metadata from remote endpoints | Drop-in replacement for stdlib XML modules. Prevents billion-laughs / external entity injection when parsing metadata fetched from client IdP endpoints. REQUIRED for any remote XML parsing in a consulting tool. |
| `signxml` | `>=4.4.0` | SAML metadata certificate extraction and XMLDSig algorithm inspection | Pure-Python (no `xmlsec1` binary). Uses `lxml` + `cryptography` (both already in stack). Extracts the certificate from `ds:X509Certificate`, reads the `Algorithm` URI from `ds:SignatureMethod`, and supports SHA1-deprecation detection. Version 4.4.0 (March 2026) is the latest release. |

### No New Libraries Needed (covered by existing stack)

| Capability | Handled By | Notes |
|------------|-----------|-------|
| OIDC `.well-known/openid-configuration` fetch | `httpx` (already in stack) | Simple GET + JSON parse; `jwks_uri` → `kty`/`alg`/key-size extraction already demonstrated in `jwt_scanner.py` |
| JWT JWKS algorithm inspection | `PyJWT` + `cryptography` (already in stack) | Existing `jwt_scanner.py` already handles JWKS fetching and algorithm classification |
| X.509 certificate key-size analysis (SAML signing cert) | `cryptography` (already in stack) | `load_pem_x509_certificate()` + `.public_key().key_size` gives RSA/EC key size after base64-decoding the `X509Certificate` text node |
| CBOM integration for new findings | `cyclonedx-python-lib` (already in stack) | No new CBOM library needed; new scanners emit the same finding dicts as TLS/SSH scanners |

---

## Integration Analysis

### Dependency Conflict Risk: impacket

**Risk level: MEDIUM — requires version pinning.**

impacket pulls in `pyOpenSSL` as a transitive dependency. Recent impacket 0.13.0 "relaxed the
pyOpenSSL pin" (from an exact == constraint to >=), which reduces conflicts. However:

- `cryptography>=44.0` is already required by the existing quirk stack.
- `pyOpenSSL>=25.0.0` requires `cryptography>=46.0.0`.
- `sslyze` (not pinned to an upper bound in pyproject.toml) works with `cryptography>=43`.

**Recommended mitigation:** Install impacket in the `[identity]` optional extras group (like
`[dashboard]`) rather than core dependencies. This isolates the pyOpenSSL transitive pull to
users who opt into the identity scanners.

```toml
[project.optional-dependencies]
identity = [
    "impacket>=0.13.0,<0.14",
    "dnspython[dnssec]>=2.8.0",
    "lxml>=6.0",
    "defusedxml>=0.7.1",
    "signxml>=4.4.0",
]
```

If pip reports a conflict on `cryptography`, the fix is to upgrade to `cryptography>=46.0` in
the core deps, which is safe — the `cryptography` project maintains backward API compatibility.

### lxml on macOS/Linux

lxml 6.x ships binary wheels for Python 3.10-3.14 on macOS arm64/x86_64 and Linux x86_64.
No compilation needed. No conflict with anything in the existing stack.

### defusedxml note

defusedxml 0.7.1 was released in March 2021 and has been stable since. It is already installed
as a transitive dependency of several packages in the quirk venv (visible in `.venv/lib/` dist-info).
Adding it as an explicit dependency is belt-and-suspenders.

---

## Kerberos Scanner: Integration Pattern

The etype probe is done WITHOUT valid credentials. Pattern:

1. Use `impacket.krb5.kerberosv5.getKerberosTGT()` with a synthetic username and a junk password.
2. The KDC responds with `KDC_ERR_PREAUTH_REQUIRED` containing `PA_ETYPE_INFO2`.
3. The `sendReceive()` call does NOT raise on `KDC_ERR_PREAUTH_REQUIRED` — it returns the raw
   error response for parsing.
4. Iterate `padata` from the KRB_ERROR, find `PA_ETYPE_INFO2`, decode it, extract etype values.
5. Map etype integers to names using `impacket.krb5.constants.EncryptionTypes`.

**Quantum-safety classification for Kerberos etypes:**

| Etype int | Name | Quantum classification |
|-----------|------|----------------------|
| 1-3 | DES variants | CRITICAL (broken classically) |
| 5, 7, 16 | 3DES variants | CRITICAL (56-bit effective key) |
| 17 | AES128-CTS-HMAC-SHA1-96 | SAFE (symmetric, 128-bit) |
| 18 | AES256-CTS-HMAC-SHA1-96 | SAFE (symmetric, 256-bit) |
| 23 | RC4-HMAC | HIGH (MD4/RC4 — classically weak) |
| 24 | RC4-HMAC-exp | CRITICAL (40-bit export key) |

**If the KDC is unreachable / not Kerberos:** The scanner should return a timeout finding
with severity=INFO, not crash. impacket's `sendReceive()` raises `socket.timeout` — wrap it.

---

## SAML/OAuth Scanner: Integration Pattern

**SAML metadata fetch + parse:**

1. Fetch the metadata URL (configurable, e.g. `/saml/metadata`, `/FederationMetadata/2007-06/FederationMetadata.xml`) via `httpx` (already in stack).
2. Parse with `lxml.etree.fromstring(defusedxml.lxml.RestrictedElement(...))` or use
   `defusedxml.lxml.fromstring()` directly.
3. Navigate `{urn:oasis:names:tc:SAML:2.0:metadata}EntityDescriptor` →
   `KeyDescriptor` → `{http://www.w3.org/2000/09/xmldsig#}X509Certificate` text node.
4. Base64-decode the cert, load with `cryptography.x509.load_der_x509_certificate()`.
5. Extract: algorithm (`cert.signature_algorithm_oid.dotted_string`), key type, key size.
6. Read `ds:SignatureMethod Algorithm` URI from metadata XML for signing algorithm declaration.

**OIDC discovery + JWKS:**

This is already handled by the existing `jwt_scanner.py` path. The identity scanner needs only
to add a probe for `/.well-known/openid-configuration` and extract `id_token_signing_alg_values_supported`.
No new libraries — pure `httpx` + `json`.

**Quantum-safety for SAML signing:**

| Algorithm URI | Assessment |
|--------------|-----------|
| `...rsa-sha1` | CRITICAL — SHA1 is broken; also quantum-unsafe RSA key sizes <3072 |
| `...rsa-sha256` | WARN if RSA key < 3072; OK for classical, quantum-unsafe |
| `...rsa-sha384/sha512` | WARN if RSA key < 3072; stronger hash, still RSA-vulnerable |
| `...ecdsa-sha256` + P-256 | WARN — quantum-unsafe ECDSA |
| `...ecdsa-sha384` + P-384 | WARN — quantum-unsafe ECDSA |

---

## DNSSEC Scanner: Integration Pattern

1. Use `dns.resolver.resolve(domain, 'DNSKEY')` for the zone's public keys.
2. Use `dns.resolver.resolve(domain, 'DS')` to enumerate digest/algorithm entries.
3. Read `rdata.algorithm` (a `dns.dnssec.Algorithm` enum member) from each DNSKEY record.
4. Map algorithms to quantum/classical safety:

| Algorithm enum | Int | Assessment |
|---------------|-----|-----------|
| `RSAMD5` | 1 | CRITICAL — MD5-based, deprecated RFC 8624 MUST NOT |
| `RSASHA1` | 5 | HIGH — SHA1-based, deprecated RFC 8624 MUST NOT |
| `RSASHA1NSEC3SHA1` | 7 | HIGH — same as RSASHA1 for signing |
| `RSASHA256` | 8 | WARN — classical RSA, quantum-unsafe |
| `RSASHA512` | 10 | WARN — classical RSA, quantum-unsafe |
| `ECDSAP256SHA256` | 13 | WARN — quantum-unsafe ECDSA |
| `ECDSAP384SHA384` | 14 | WARN — quantum-unsafe ECDSA |
| `ED25519` | 15 | WARN — quantum-unsafe (EdDSA on Curve25519) |
| `ED448` | 16 | WARN — quantum-unsafe (EdDSA on Curve448) |

5. Check DS record hash algorithm: SHA1 (1) = HIGH; SHA256 (2) = WARN; SHA384 (4) = WARN.
6. If `dns.resolver.NoAnswer` or `dns.resolver.NXDOMAIN`: domain is unsigned — emit a DNSSEC_MISSING finding.

**Important:** `dnspython[dnssec]` requires the `cryptography` package for RRSIG validation.
Since `cryptography>=44.0` is already in core deps, the `[dnssec]` extra adds zero new transitive
dependencies.

---

## Chaos Lab Docker Images

### Kerberos: Samba AD DC

| Image | Recommendation | Notes |
|-------|---------------|-------|
| `smblds/smblds` | **USE THIS** — MEDIUM confidence | "Samba Lightweight Directory Services" — purpose-built for CI/dev testing. Minimal footprint. Exposes KDC on port 88. Available on Docker Hub. |
| `itherz/samba-ad-dc` | Fallback option | Full Samba4 AD DC. Heavier (~600MB), requires `--privileged` flag and specific hostname setup. More realistic but harder to run in chaos lab profile. |
| `rsippl/samba-ad-dc` | Fallback option | Similar to itherz; both verified on Docker Hub. |

**Recommendation:** Use `smblds/smblds` for the chaos lab profile. It is the purpose-built CI
image with KDC enabled and minimal configuration overhead. Add a custom entrypoint script to
pre-provision a test realm with RC4-only etypes (to exercise the weak-etype detection path) and
a second config with AES-only etypes (to verify clean scans).

**Port:** 88/tcp (Kerberos standard). Bind to `127.0.0.1:88:88` in docker-compose profile.

### SAML IdP

| Image | Recommendation | Notes |
|-------|---------------|-------|
| `kenchan0130/simplesamlphp` | **USE THIS** — HIGH confidence | PHP8 Apache base; SAML 2.0 IdP. Metadata endpoint at `/simplesaml/saml2/idp/metadata.php`. Actively maintained, widely used for dev/test. Configure with a custom signing cert (RSA-1024 for weak-etype lab, RSA-2048 SHA1 for algorithm-weakness lab). |
| `kristophjunge/test-saml-idp` | Not recommended | Unmaintained, PHP7-based, last update 2020. Use kenchan0130 instead. |

**Port:** 8080/tcp (HTTP, no TLS needed for chaos lab).
**OIDC:** SimpleSAMLphp does not expose an OIDC discovery endpoint natively. For OAuth/OIDC
testing, use the existing `jwt` chaos lab profile (already present) — it already exercises
JWKS endpoint scanning. No new OIDC container needed.

### DNSSEC: BIND9

| Image | Recommendation | Notes |
|-------|---------------|-------|
| `internetsystemsconsortium/bind9:9.20` | **USE THIS** — HIGH confidence | Official ISC BIND9 image, actively maintained, latest stable is 9.20. Add a custom zone file with `dnssec-keygen`-generated keys covering: (a) RSASHA1-signed zone (weak), (b) ECDSAP256SHA256-signed zone (current), (c) unsigned zone (DNSSEC_MISSING path). |
| `coredns/coredns` with `sign` plugin | Alternative | CoreDNS `sign` plugin does on-the-fly DNSSEC signing but limited algorithm control. BIND9 gives better control over key algorithm for chaos scenarios. |

**Port:** 5353/udp (or 53/udp — remap to 5353 to avoid host conflict).
**Zone setup:** Use a custom `named.conf` and zone files checked into the chaos lab directory.
Pre-generate DNSSEC keys with `dnssec-keygen -a RSASHA1 -b 1024` for the weak-algorithm test case.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `impacket>=0.13.0` | Raw socket + pyasn1 Kerberos ASN.1 construction | Would require implementing full AS-REQ/AS-REP ASN.1 encoding from scratch. impacket's `kerberosv5.py` already encodes the correct PDU, handles TCP framing, and parses ETYPE_INFO2. Re-implementing this is 200+ lines of fragile ASN.1 work for zero benefit. |
| `impacket>=0.13.0` | `python-gssapi` / `krb5` C binding | These libraries require a working Kerberos installation on the scanner host (krb5.conf, realm config). QU.I.R.K.'s constraint is agentless, minimal host deps. impacket speaks raw Kerberos over TCP with no host krb5 required. |
| `signxml>=4.4.0` + `lxml` | `pysaml2` | pysaml2 7.5.x requires `xmlsec1` binary at runtime (a non-Python system dependency). QU.I.R.K.'s constraint is pip-installable with no system binaries. signxml + lxml is pure Python and covers all the metadata inspection use cases needed. |
| `signxml>=4.4.0` + `lxml` | `python3-saml` (OneLogin) | Also requires `xmlsec1` binary AND `dm.xmlsec.binding` Cython extension. Same problem as pysaml2. |
| `defusedxml>=0.7.1` (explicit dep) | Rely on lxml's built-in security | lxml alone does not prevent all XXE scenarios by default. defusedxml ensures parser config is correct regardless of lxml version. Belt-and-suspenders for a security tool. |
| `dnspython[dnssec]>=2.8.0` | `ldns` Python bindings | ldns is a C library requiring separate install, not pip-installable on all platforms. dnspython is pure Python with C extensions only for performance (not required for correctness). |
| `kenchan0130/simplesamlphp` (chaos lab) | `Keycloak` | Keycloak requires >512MB RAM and JVM startup time. Too heavy for a chaos lab profile. SimpleSAMLphp is ~50MB and starts in <3 seconds. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pysaml2` as a dep | Requires `xmlsec1` binary — violates pip-only constraint | `lxml` + `defusedxml` + `signxml` |
| `python3-saml` (OneLogin) | Same `xmlsec1` binary requirement | `lxml` + `signxml` |
| `python-gssapi` | Requires host Kerberos installation (krb5.conf, realm) | `impacket` (raw Kerberos TCP) |
| `kristophjunge/test-saml-idp` | Unmaintained since 2020, PHP7 | `kenchan0130/simplesamlphp` |
| `hardware/nsd-dnssec` | Explicitly marked UNMAINTAINED on GitHub/Docker Hub | `internetsystemsconsortium/bind9:9.20` |
| `impacket` in core deps | pyOpenSSL transitive dep may conflict with future cryptography upgrades | Move to `[identity]` optional extras group |
| Full pysaml2 SAML flow | Scanning does not require SP-side authentication — just metadata inspection | Parse metadata XML directly with lxml + extract cert/alg |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `dnspython[dnssec]>=2.8.0` | `cryptography>=44.0` (already in stack) | The `[dnssec]` extra uses `cryptography` for RRSIG validation — no new cryptography pull. Zero conflict. |
| `impacket>=0.13.0,<0.14` | `cryptography>=44.0`, `pyOpenSSL>=24.0` | 0.13.0 relaxed pyOpenSSL pin. If cryptography is upgraded to >=46 for other reasons, impacket is compatible. Pin `<0.14` to avoid surprise breaking changes. |
| `lxml>=6.0` | `cryptography>=44.0`, Python 3.10-3.14 | No shared dependencies with the rest of the stack. Ships binary wheels. |
| `signxml>=4.4.0` | `lxml>=6.0`, `cryptography>=44.0` | All three deps already in stack or being added. Latest release March 2026. |
| `defusedxml>=0.7.1` | Any Python >=3.6 | No compiled extensions, pure Python. Already transitively present in venv. |

---

## Installation

```bash
# Add to pyproject.toml optional extras
# [project.optional-dependencies]
# identity = [...]

# Install for development with identity scanners enabled
pip install -e ".[identity]"

# Core libs (no impacket for conflict isolation)
pip install "dnspython[dnssec]>=2.8.0" lxml>=6.0 defusedxml>=0.7.1 signxml>=4.4.0

# Identity etype scanner (separate due to pyOpenSSL transitive dep)
pip install "impacket>=0.13.0,<0.14"
```

---

## Sources

- [dnspython PyPI](https://pypi.org/project/dnspython/) — version 2.8.0 confirmed (September 2025)
- [dnspython DNSSEC docs (readthedocs)](https://dnspython.readthedocs.io/en/stable/dnssec.html) — Algorithm enum, DNSKEY/DS support confirmed (403 on direct fetch; verified via GitHub source search)
- [dnspython GitHub dns/dnssec.py](https://github.com/rthalley/dnspython/blob/main/dns/dnssec.py) — Algorithm enum values verified (RSASHA1=5, ECDSAP256SHA256=13, ED25519=15, etc.)
- [impacket PyPI](https://pypi.org/project/impacket/) — version 0.13.0 confirmed (October 2025); Python 3.9-3.13 support confirmed
- [impacket fortra/impacket kerberosv5.py](https://github.com/fortra/impacket/blob/master/impacket/krb5/kerberosv5.py) — ETYPE_INFO2 extraction from KDC_ERR_PREAUTH_REQUIRED confirmed; sendReceive pattern verified
- [impacket fortra/impacket constants.py](https://github.com/fortra/impacket/blob/master/impacket/krb5/constants.py) — EncryptionTypes enum values verified (RC4=23, AES128=17, AES256=18)
- [lxml PyPI](https://pypi.org/project/lxml/) — version 6.0.2 confirmed (September 2025); Python 3.8-3.14 wheel support confirmed
- [defusedxml PyPI](https://pypi.org/project/defusedxml/) — version 0.7.1 confirmed; stable since 2021
- [signxml PyPI](https://pypi.org/project/signxml/) — version 4.4.0 confirmed (March 2026); pure Python (no xmlsec1 binary), lxml + cryptography deps confirmed
- [kenchan0130/simplesamlphp Docker Hub](https://hub.docker.com/r/kenchan0130/simplesamlphp/) — SAML IdP image verified, metadata endpoint at /simplesaml/saml2/idp/metadata.php
- [internetsystemsconsortium/bind9 Docker Hub](https://hub.docker.com/r/internetsystemsconsortium/bind9) — official ISC BIND9 image confirmed, version 9.20 available
- [smblds/smblds Docker Hub](https://hub.docker.com/r/smblds/smblds) — Samba lightweight DS image for Kerberos KDC testing confirmed
- [impacket pyOpenSSL conflict issues](https://github.com/fortra/impacket/issues/1716) — pyOpenSSL/cryptography conflict history reviewed; 0.13.0 relaxed pin confirmed via [PR #1939](https://github.com/fortra/impacket/pull/1939)
- WebSearch: pysaml2 xmlsec1 dependency confirmed via IdentityPython/pysaml2 docs and known issues

---

*Stack research for: QU.I.R.K. v4.2 Identity Crypto — Kerberos/SAML/DNSSEC scanners*
*Researched: 2026-04-08*
