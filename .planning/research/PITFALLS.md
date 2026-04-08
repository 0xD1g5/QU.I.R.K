# Pitfalls Research

**Domain:** Identity protocol crypto scanners — Kerberos etype enumeration, SAML/OAuth metadata parsing, DNSSEC algorithm auditing — added to an existing Python CBOM pipeline
**Researched:** 2026-04-08
**Confidence:** HIGH (Kerberos protocol behavior, DNSSEC algorithm numbers, SQLite migration), MEDIUM (SAML namespace edge cases, chaos lab container specifics)

---

## Critical Pitfalls

### Pitfall 1: Kerberos AS-REQ Sends Credentials to Enumerate Etypes

**What goes wrong:**
Developers copy impacket's `getKerberosTGT()` or `GetNPUsers.py` flow without realizing it performs credential-based authentication, not agentless probing. The function sends real NT hashes or Kerberos keys. If a dummy principal is used with fake credentials, the KDC will either return `KDC_ERR_C_PRINCIPAL_UNKNOWN` (unknown user) before etype information is transmitted, or `KDC_ERR_PREAUTH_REQUIRED` with a PA-ETYPE-INFO2 padata field that contains the supported etypes. Only the second error response actually carries etype data.

**Why it happens:**
Impacket is designed for active exploitation tooling, not passive crypto auditing. Its `getKerberosTGT()` falls back to RC4-HMAC when AES is not supported, and its AS-REQ construction is oriented around obtaining usable tickets. The etype advertisement behavior (PA-ETYPE-INFO2) is a KDC response to a PREAUTH_REQUIRED error, not to a successful TGT request. Developers who follow impacket's normal flow miss this distinction.

**How to avoid:**
Send a bare AS-REQ with no preauthentication data, using a known-valid or dummy username with `ENC_TIMESTAMP` padata absent. The KDC will return `KDC_ERR_PREAUTH_REQUIRED` (error code 25) with PA-ETYPE-INFO2 pre-authentication data that lists the KDC-supported etypes (RC4=23, AES128=17, AES256=18, DES3=16). Alternatively, send a request with only `RC4_HMAC` etype in the etype list; if it succeeds, RC4 is supported. Parse the `PA-ETYPE-INFO2` element from the error response, not from a successful AS-REP. Use raw `impacket.krb5.asn1` construction rather than the high-level `getKerberosTGT()` wrapper. The scanner must never authenticate; it must only observe what the KDC advertises.

**Warning signs:**
- Code calls `getKerberosTGT()` or `getKerberosTGS()` in the etype scanner
- Unit tests pass only when given valid credentials
- Scan logs show `KDC_ERR_C_PRINCIPAL_UNKNOWN` rather than `KDC_ERR_PREAUTH_REQUIRED`
- Test fixtures require a real AD user account

**Phase to address:** Kerberos scanner implementation phase (first Kerberos phase). Must be in design requirements for the scanner, not discovered during chaos lab testing.

---

### Pitfall 2: Kerberos Etype Enumeration Blocked by UDP 88 Silently Returns No Result

**What goes wrong:**
Kerberos defaults to UDP port 88. Many enterprise firewalls block UDP/88 specifically to force TCP Kerberos (which is harder to intercept). A UDP-only scanner silently times out and reports "no Kerberos service" rather than "Kerberos service present but UDP blocked." The finding disappears from the CBOM entirely rather than appearing as an error endpoint.

**Why it happens:**
UDP sockets do not receive an ICMP port-unreachable response in many enterprise environments. The scanner socket simply blocks until timeout, indistinguishable from a host that has no KDC. TCP/88 fallback is part of the MIT Kerberos RFC but not implemented by scanners that only use `socket.SOCK_DGRAM`.

**How to avoid:**
Implement a TCP/88 fallback. Attempt UDP first with a short timeout (3–5 seconds); on timeout, retry via TCP/88 with a fresh connection. Use `socket.SOCK_STREAM` for TCP. Store both the transport used and the result in `service_detail`. If both UDP and TCP time out, record a `scan_error` with a specific "kerberos-unreachable" message rather than silently emitting an empty result.

**Warning signs:**
- Kerberos scanner returns empty results against a known-running Samba DC
- No `scan_error` column populated when KDC is unreachable
- Scanner only constructs UDP sockets

**Phase to address:** Kerberos scanner implementation phase.

---

### Pitfall 3: SAML Metadata XML Namespace Handling Breaks with Bare lxml XPath

**What goes wrong:**
SAML metadata uses multiple XML namespaces simultaneously: `urn:oasis:names:tc:SAML:2.0:metadata`, `http://www.w3.org/2000/09/xmldsig#` for the signature namespace, and `urn:oasis:names:tc:SAML:2.0:assertion`. XPath queries written without namespace mappings (e.g., `//KeyDescriptor` instead of `//md:KeyDescriptor`) silently return empty results rather than raising errors. The scanner reports no signing algorithms found when the metadata is valid.

**Why it happens:**
lxml's `xpath()` method ignores namespace prefixes in queries unless you pass an `nsmap` argument with the correct namespace bindings. Developers test against metadata fetched from a known IdP that happens to use no prefix, then break on real-world metadata from Okta, Azure AD, or ADFS which all use `md:` and `ds:` prefixes. The behavior is silent (empty list returned) not explosive (exception raised).

**How to avoid:**
Always pass an explicit `namespaces` dict to `findall()` or `xpath()`. Define the canonical SAML namespace map as a module-level constant:

```python
SAML_NS = {
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
}
```

Use `tree.findall(".//md:KeyDescriptor[@use='signing']", SAML_NS)`. Test against at least three distinct IdP metadata formats: SimpleSAMLphp (chaos lab), Keycloak (chaos lab), and a static file fixture representing ADFS-style metadata with full namespace prefixes.

**Warning signs:**
- `cert_pubkey_alg` is `None` for endpoints that clearly have SAML metadata
- Scanner works against Keycloak but not against static ADFS fixture
- No namespace dict in the SAML parsing code

**Phase to address:** SAML scanner implementation phase.

---

### Pitfall 4: SAML KeyDescriptor `use` Attribute Is Optional — All Keys Parsed as Signing

**What goes wrong:**
SAML metadata allows KeyDescriptor elements with `use="signing"`, `use="encryption"`, or no `use` attribute at all. A KeyDescriptor with no `use` attribute means it applies to both signing and encryption. Scanners that only query `[@use='signing']` miss dual-purpose keys entirely. Scanners that pull all KeyDescriptor certificates without filtering collect encryption-only keys and misclassify them as signing keys, producing misleading findings.

**Why it happens:**
The SAML metadata spec (OASIS) makes `use` optional. Real-world Azure AD and Okta metadata frequently omits `use` on the primary signing key, relying on the "no attribute = both" rule. Developers read examples with explicit `use="signing"` and hard-code the XPath filter.

**How to avoid:**
Parse three categories: `[@use='signing']`, `[@use='encryption']`, and `[not(@use)]` (both). Report all three in `service_detail` with their role. When computing quantum-readiness findings, treat "signing" and "both" as relevant to the signing crypto surface; "encryption-only" keys are lower priority but should still appear in the CBOM. Do not silently discard keys lacking a `use` attribute.

**Warning signs:**
- SAML scan against a real IdP (Keycloak chaos lab) finds zero signing keys even though the metadata is valid
- Scanner XPath filter includes `[@use='signing']` with no fallback for missing attribute
- test fixtures all have explicit `use="signing"` attributes

**Phase to address:** SAML scanner implementation phase.

---

### Pitfall 5: DNSSEC Requires `dnspython[dnssec]` Extra — Silent ImportError at Runtime

**What goes wrong:**
`pip install dnspython` without the extras gives you the base library. The DNSSEC-specific module `dns.dnssec` imports cleanly at the top level, but calling `dns.dnssec.make_ds()` or signature validation functions raises `ImportError: No module named 'cryptography'` at runtime. The scanner appears to load successfully but all DNSSEC analysis paths silently fail.

**Why it happens:**
dnspython separates its cryptography dependency into an optional extra (`pip install dnspython[dnssec]`). The base package installs without `cryptography`. The import-time failure happens inside `dns.dnssec` function bodies, not at module import time, so the error only surfaces when a function is called.

**How to avoid:**
Add `dnspython[dnssec]` (not `dnspython`) to `pyproject.toml` dependencies. In the scanner module, add a guard at load time:

```python
try:
    import dns.dnssec
    import dns.resolver
    DNSPYTHON_AVAILABLE = True
except ImportError:
    DNSPYTHON_AVAILABLE = False
```

Follow the same pattern used in `jwt_scanner.py` for `httpx`. Include a test that verifies `DNSPYTHON_AVAILABLE` is `True` in the CI environment so it fails loudly if the extra is missing from the package manifest.

**Warning signs:**
- `dnspython` is in `pyproject.toml` without `[dnssec]`
- DNSSEC scan returns empty results against a known-signed zone
- No `DNSPYTHON_AVAILABLE` guard in the scanner module

**Phase to address:** Dependency declaration phase, before DNSSEC scanner implementation.

---

### Pitfall 6: DNSSEC Querying Requires a Validating Resolver — System Resolver May Return Cached or Unsigned Results

**What goes wrong:**
The system resolver (`/etc/resolv.conf`) may be a caching forwarder that strips DNSSEC RRs (DNSKEY, RRSIG, DS) from responses. Querying via `dns.resolver.resolve("example.com", "DNSKEY")` against a forwarder that strips DO-bit responses returns `NXRRSET` or an empty rrset, causing the scanner to report "not signed" for a fully DNSSEC-signed zone.

**Why it happens:**
Many corporate and containerized environments use a local caching resolver (systemd-resolved, dnsmasq) that does not forward the DNSSEC OK (DO) bit and may strip or not forward DNSKEY/RRSIG records. The scanner developer tests against `8.8.8.8` which works, but the CI/CD or client environment uses a stripping forwarder.

**How to avoid:**
Query authoritative nameservers directly rather than through the system resolver. Use `dns.resolver.Resolver()` with `resolver.nameservers` set to the zone's actual authoritative NS records (queried first via `dns.resolver.resolve(zone, "NS")`). Set `resolver.use_edns(edns=0, ednsflags=dns.flags.DO)` to request DNSSEC records. In offline/air-gapped environments, document that DNSSEC scanning requires at least UDP/53 connectivity to the target nameserver (this is inherently a network operation; it is not fully offline-capable). In the chaos lab, point the BIND9 container directly using `nameservers=["127.0.0.1"]` with the configured port.

**Warning signs:**
- DNSSEC scan returns "not signed" for `cloudflare.com` or `google.com`
- Resolver configuration uses system default (`/etc/resolv.conf`)
- No explicit DO-bit configuration in resolver setup

**Phase to address:** DNSSEC scanner design phase.

---

### Pitfall 7: DNSSEC Algorithm 5 (RSASHA1) / Algorithm 7 (RSASHA1-NSEC3-SHA1) Not Classified as Quantum-Vulnerable in Classifier

**What goes wrong:**
DNSSEC algorithm numbers are integers (5, 7, 13, 15) not algorithm name strings. The existing `_ALGORITHM_TABLE` in `classifier.py` uses string keys (`"rsa"`, `"ecdsa"`, etc.). If the DNSSEC scanner passes raw algorithm integers or their short names without mapping to the classifier's canonical key format, `classify_algorithm()` returns `(UNKNOWN, None, None)` for all DNSSEC algorithms. DNSKEY records signed with SHA-1-based algorithms are the most critical finding (RFC 8624 status: MUST NOT use), but they silently become "unknown" in the CBOM.

**Why it happens:**
DNSSEC algorithm numbers are defined in IANA's registry with specific integer IDs. dnspython exposes them as `dns.dnssec.RSASHA1 = 5`. The scanner developer may pass the integer (5) or the IANA name ("RSASHA1") to the classifier, neither of which matches `"rsa"` or `"sha-1"` in `_ALGORITHM_TABLE`. The mapping between DNSSEC IANA algorithm numbers and CBOM classifier keys must be built explicitly.

**How to avoid:**
Add a DNSSEC-specific algorithm mapping table to `classifier.py` (or the DNSSEC scanner module) before calling `classify_algorithm()`:

```python
DNSSEC_ALG_MAP = {
    1:  "RSA",       # RSAMD5 — MUST NOT (RFC 8624)
    3:  "DSA",       # DSA — MUST NOT
    5:  "RSA",       # RSASHA1 — MUST NOT for signing
    6:  "DSA",       # DSA-NSEC3-SHA1 — MUST NOT
    7:  "RSA",       # RSASHA1-NSEC3-SHA1 — MUST NOT
    8:  "RSA",       # RSASHA256 — recommended
    10: "RSA",       # RSASHA512
    13: "ECDSA",     # ECDSAP256SHA256 — recommended
    14: "ECDSA",     # ECDSAP384SHA384
    15: "Ed25519",   # ED25519 — recommended
    16: "Ed448",     # ED448
}
```

Include additional context (algorithm number, IANA name, RFC 8624 status) in `service_detail` so the risk engine can issue MUST-NOT-USE findings separate from quantum-readiness findings.

**Warning signs:**
- DNSKEY records produce `(UNKNOWN, None, None)` from classifier
- CBOM has no DNSSEC algorithm components after a signed zone scan
- No DNSSEC algorithm map in classifier or scanner module

**Phase to address:** DNSSEC scanner implementation phase, during classifier extension.

---

### Pitfall 8: SAML Signing Certificate Extraction Loses PEM Headers — `cryptography` Library Parsing Fails

**What goes wrong:**
SAML metadata stores X.509 certificates as raw base64 strings inside `<ds:X509Certificate>` elements — no PEM headers. When extracting the signing key type and size, developers must reconstruct the PEM format before passing to `cryptography.x509.load_pem_x509_certificate()`. If the PEM header/footer lines are concatenated with the base64 data without newlines (e.g., `"-----BEGIN CERTIFICATE-----" + raw_b64 + "-----END CERTIFICATE-----"`), the `cryptography` library raises a `ValueError: Could not deserialize key data`. This is a documented SimpleSAMLphp issue (#999).

**Why it happens:**
`ds:X509Certificate` content is raw base64 (no header, no line breaks). The `cryptography` library requires PEM format with exactly `-----BEGIN CERTIFICATE-----\n`, base64 content split into 64-character lines, and `\n-----END CERTIFICATE-----\n`. Missing the `\n` after the header or between data lines causes silent parsing failure in some versions and explicit errors in others.

**How to avoid:**
Always wrap the base64 content before parsing:

```python
import textwrap
from cryptography import x509

raw_b64 = key_descriptor_text.strip()
pem = "-----BEGIN CERTIFICATE-----\n" + textwrap.fill(raw_b64, 64) + "\n-----END CERTIFICATE-----\n"
cert = x509.load_pem_x509_certificate(pem.encode())
```

Use `textwrap.fill(raw_b64, 64)` not a raw concatenation. Test against certificates of various lengths (short test cert vs real 4096-bit RSA cert). The `cryptography` library also accepts DER format via `load_der_x509_certificate(base64.b64decode(raw_b64))` which avoids the PEM wrapping issue entirely — prefer DER parsing.

**Warning signs:**
- `ValueError: Could not deserialize key data` in scanner logs
- PEM construction uses `"-----BEGIN CERTIFICATE-----" + raw_b64` without newline
- No `textwrap.fill` or DER parsing in certificate extraction code

**Phase to address:** SAML scanner implementation phase.

---

### Pitfall 9: New `identity_scan_json` Column Added Without `nullable=True` Breaks Existing Rows

**What goes wrong:**
Adding a new column like `identity_scan_json = Column(Text)` to `CryptoEndpoint` in models.py without `nullable=True` causes SQLAlchemy to attempt to set `NOT NULL` on a column in an existing SQLite table. SQLite's `ALTER TABLE ... ADD COLUMN` only allows NOT NULL columns if a `DEFAULT` expression is provided. Without it, SQLAlchemy's `Base.metadata.create_all()` succeeds on fresh databases but fails on existing databases in-place, or silently creates inconsistent schema.

**Why it happens:**
`Column(Text)` in SQLAlchemy defaults to `nullable=True` in Python, but in SQLite the behavior depends on whether the table already exists and whether Alembic migrations are used. The project uses `create_all()` at startup (no Alembic). If a user upgrades QUIRK on an existing `quirk.db`, `create_all()` does not run `ALTER TABLE` at all — new columns are simply absent. The scanner then fails with `OperationalError: table crypto_endpoints has no column named identity_scan_json`.

**How to avoid:**
All new columns must be: (1) `nullable=True` (no DEFAULT needed), (2) explicitly added in the codebase's startup migration path. Since QUIRK uses `create_all()` without Alembic, add a lightweight `_apply_additive_migrations()` function in `db.py` that runs `ALTER TABLE crypto_endpoints ADD COLUMN <name> TEXT` if the column does not exist. The function should be idempotent (check `PRAGMA table_info(crypto_endpoints)` first). Document this pattern in `CLAUDE.md` as the required approach for any v4.x column addition.

**Warning signs:**
- New column declaration lacks `nullable=True`
- No `ALTER TABLE` logic in `db.py` or `migrate.py`
- Scanner tests only create fresh test databases (never test against a pre-existing schema)

**Phase to address:** Database/models phase — the first thing done when adding identity scanner columns.

---

### Pitfall 10: CBOM Builder `else` Branch Handles New Identity Protocols as TLS — Produces Garbage Components

**What goes wrong:**
The `build_cbom()` function in `builder.py` has an `else` branch (lines 351–366) that treats any endpoint with an unrecognized `protocol` value as TLS. If a new Kerberos scanner stores endpoints with `protocol="KERBEROS"` or `protocol="SAML"` and `build_cbom()` is not updated, those endpoints enter the TLS branch: `_decompose_cipher_suite(ep.cipher_suite)` is called on etype or signing algorithm data, producing nonsensical cipher suite decomposition results or silently skipping them entirely.

**Why it happens:**
The builder's protocol dispatch is a long `if/elif/else` chain. The `else` is a safety net for the original codebase where all non-SSH endpoints were TLS. As new protocols are added, developers add scanner code and models but forget to update the CBOM builder dispatch. The new endpoints appear in the scan results table but produce malformed or missing CBOM components. This is exactly the pattern that caused the `protocol in ("JWT", "CONTAINER", ...)` elif block to grow in v4.0.

**How to avoid:**
Add explicit `elif ep.protocol == "KERBEROS":`, `elif ep.protocol == "SAML":`, and `elif ep.protocol == "DNSSEC":` branches to `build_cbom()` in Pass 1 (algorithm extraction) and Pass 3 (protocol components). The new branches must be added in the same phase as the scanner implementation, with tests that explicitly verify CBOM components are generated for identity protocol endpoints. The `else` branch should log a warning for unrecognized protocol values rather than silently treating them as TLS.

**Warning signs:**
- CBOM output contains `protocol:tls:` components for Kerberos/SAML/DNSSEC endpoints
- `build_cbom()` has no `KERBEROS`, `SAML`, or `DNSSEC` branch
- CBOM builder tests do not cover identity protocol endpoint types

**Phase to address:** CBOM integration phase — concurrent with each scanner's implementation phase.

---

### Pitfall 11: Samba DC Container Takes 60–90 Seconds to Provision — Chaos Lab Tests Fail on Startup Race

**What goes wrong:**
`samba-tool domain provision` inside a Samba AD DC container takes 60–90 seconds to complete on the first startup. If a chaos lab test runner or dependent service starts while Samba is still provisioning, it gets `KDC_ERR_NEVER_VALID` or connection refused on port 88, and the test is marked as a scanner failure rather than a container readiness failure. This is especially problematic in CI/CD pipelines where the compose profile starts fresh every run.

**Why it happens:**
Docker Compose's `depends_on: condition: service_healthy` requires an explicit `healthcheck:` to be defined. Samba DC images commonly have no built-in healthcheck. Without a healthcheck, Compose considers the container "started" as soon as the process runs, which is immediate — long before the domain provision completes.

**How to avoid:**
Add a healthcheck to the Samba DC service in `docker-compose.yml` that probes port 88 availability or `kinit` success:

```yaml
healthcheck:
  test: ["CMD-SHELL", "nc -z localhost 88 || exit 1"]
  interval: 5s
  timeout: 3s
  retries: 20
  start_period: 90s
```

Set `start_period: 90s` to give provisioning time before Docker starts counting failures. Any service that needs the KDC (the scanner test runner) must declare `depends_on: kerberos-dc: condition: service_healthy`. Avoid using the smblds/smblds image unless it includes a healthcheck — prefer images that have explicit provision-complete signaling.

**Warning signs:**
- Chaos lab Kerberos tests flake intermittently (pass on rerun)
- Samba DC service has no `healthcheck:` block in compose
- Scanner test starts without `service_healthy` wait

**Phase to address:** Chaos lab setup phase (Kerberos profile).

---

### Pitfall 12: DNSSEC Chaos Lab BIND9 Container Serves an Unsigned Zone by Default

**What goes wrong:**
BIND9 Docker images (e.g., `internetsystemsconsortium/bind9`) serve zones without DNSSEC signing unless `dnssec-policy` or `auto-dnssec maintain` is explicitly configured and keys are generated. A chaos lab test that queries a BIND9 container for `DNSKEY` records gets `NXRRSET` (no records of that type) because DNSSEC was never enabled on the zone. The scanner correctly reports "no DNSSEC" but the test purpose (verifying scanner detection of weak algorithms) is never exercised.

**Why it happens:**
DNSSEC zone signing is not automatic in BIND9. It requires either a `dnssec-policy` block in `named.conf` (BIND 9.16+) or manual `dnssec-keygen`/`dnssec-signzone` invocations. Developers familiar with serving zones often overlook this. Additionally, the signed zone requires the `$INCLUDE` directive pointing at the generated `.signed` file, and the keys must be present in the zone directory.

**How to avoid:**
Use BIND9's built-in `dnssec-policy` feature (9.16+) to auto-sign the chaos lab zone with a weak algorithm for testing:

```
zone "chaos.local" {
    type primary;
    file "chaos.local.zone";
    dnssec-policy "weak-test";
    inline-signing yes;
};

dnssec-policy "weak-test" {
    keys { ksk lifetime unlimited algorithm rsasha1; };
};
```

Alternatively, provide a pre-signed zone file with hand-crafted DNSKEY/RRSIG records using algorithm 5 (RSASHA1) generated with `dnssec-keygen -a RSASHA1`. Include both a weak-algorithm zone and a strong-algorithm zone (ECDSAP256SHA256) to test that the scanner correctly distinguishes both. Document the zone files as static fixtures checked into the chaos lab directory.

**Warning signs:**
- `dig @localhost DNSKEY chaos.local` returns no records
- No `dnssec-policy` or `auto-dnssec` in `named.conf`
- Chaos lab DNSSEC test always reports "not signed" regardless of scanner code

**Phase to address:** Chaos lab setup phase (DNSSEC profile).

---

### Pitfall 13: SimpleSAMLphp / Keycloak Container OIDC Discovery Endpoint Has Timing Dependency on DB Init

**What goes wrong:**
The existing chaos lab uses Keycloak with a Postgres dependency (`id-postgres`). Keycloak's first startup performs database schema initialization that takes 30–60 seconds. If the SAML scanner chaos lab test hits `/.well-known/openid-configuration` or `realms/master/protocol/saml/descriptor` before Keycloak finishes starting, it gets a 503 or connection refused. The scanner correctly returns `scan_error`, but the test marks the scanner as broken rather than the container as not ready.

**Why it happens:**
The existing `keycloak` service in `docker-compose.yml` depends on `id-postgres` (service started), not `id-postgres: condition: service_healthy`. Keycloak itself also needs time after Postgres is available. The SAML scanner test assumes the IdP is available and does not retry.

**How to avoid:**
Add a `service_healthy` condition to the Keycloak dependency: `depends_on: id-postgres: condition: service_healthy`. Add a Keycloak healthcheck:

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -sf http://localhost:8080/health/ready || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 12
  start_period: 60s
```

For SAML scanner chaos lab tests, add a retry loop (3 attempts, 5-second backoff) in the test fixture setup, as the SAML endpoint may be temporarily unavailable during realm initialization even after the container is "healthy". This is already needed for SimpleSAMLphp as well if it is used.

**Warning signs:**
- SAML chaos lab test fails intermittently on first run
- `keycloak` depends on `id-postgres` without `condition: service_healthy`
- No retry in chaos lab test setup for SAML endpoint

**Phase to address:** Chaos lab setup phase (SAML profile) and SAML scanner test design.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `impacket.krb5.kerberosv5.getKerberosTGT()` directly | Fast scanner skeleton | Requires credentials; can't probe without auth; potential legal/policy concern | Never — write a raw AS-REQ probe |
| Querying DNSSEC via system resolver only | No resolver config needed | Produces false "not signed" in environments with stripping resolvers | Never |
| Adding `identity_scan_json` without additive migration handler | Models work on fresh DB | Breaks existing `quirk.db` on upgrade | Never |
| Hardcoding `@use='signing'` XPath filter in SAML parser | Simple first pass | Misses dual-purpose keys and most Azure AD certs | Never |
| Skipping CBOM builder update when adding new protocol | Scanner works end-to-end | Identity endpoints silently enter TLS branch | Never |
| Using `lxml.etree.fromstring()` directly on raw SAML without namespace handling | Quick parse | Silent empty results on prefixed metadata | Never |
| Using `dns.resolver.resolve()` with default resolver for DNSSEC | Works in dev | Fails in corporate environments; strips DNSSEC records | Never in the scanner |
| Using `dnskey.flags == 256` alone to identify ZSK | Simple check | Bit 7 of flags is zone key bit; the KSK/ZSK distinction requires DNSKEY flags bitmask, not equality | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Kerberos / impacket | Calling `getKerberosTGT()` and treating the error as the etype list | Parse `PA-ETYPE-INFO2` from `KDC_ERR_PREAUTH_REQUIRED` error packet using `impacket.krb5.asn1` |
| Kerberos / models | Storing etypes as a Python list in `service_detail` | Store as JSON-encoded list in `identity_scan_json`; mirrors jwt_scan_json pattern |
| SAML / lxml | `root.findall("KeyDescriptor")` | `root.findall(".//md:KeyDescriptor", SAML_NS)` with explicit namespace dict |
| SAML / x509 | `load_pem_x509_certificate(raw_b64.encode())` | `load_der_x509_certificate(base64.b64decode(raw_b64))` — DER avoids PEM line-break issues |
| SAML / OIDC | Treating `/.well-known/openid-configuration` as SAML metadata | OIDC discovery is JSON; SAML metadata is XML at `realms/master/protocol/saml/descriptor` — separate code paths |
| DNSSEC / dnspython | `dns.resolver.resolve(zone, "DNSKEY")` without DO bit | `resolver.use_edns(edns=0, ednsflags=dns.flags.DO)` before querying |
| DNSSEC / classifier | Passing integer algorithm number to `classify_algorithm()` | Map IANA algorithm number to canonical name via `DNSSEC_ALG_MAP` before calling classifier |
| DNSSEC / DNSKEY flags | `record.flags == 257` to find KSK | `record.flags & 0x0100` (Zone Key bit) and `record.flags & 0x0001` (SEP bit) for KSK/ZSK distinction |
| CBOM builder | Forgetting to add identity protocol elif to builder | Add Kerberos/SAML/DNSSEC elif in all three passes (algorithm, certificate, protocol) |
| SQLite / additive migration | Relying on `create_all()` to add new columns | Use idempotent `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` in db.py startup |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| DNSSEC NS lookup before each DNSKEY query | Each domain takes 2 DNS round-trips (NS then DNSKEY) | Cache NS lookups; batch DNSKEY queries per nameserver | At 50+ domains in a scan |
| Sequential AS-REQ probes with 5s timeout | Kerberos scan of 20 KDCs takes 100 seconds | Use concurrency pattern from `ssh_scanner.py`; thread pool with configurable size | At 5+ Kerberos targets |
| SAML metadata fetched every scan run | Repeated 200KB+ XML downloads for same IdP | Cache metadata by URL in `identity_scan_json`; re-fetch only when TTL expired (use `validUntil` attribute from metadata if present) | Any repeat scan |
| dnspython SERVFAIL retry | Query hangs for 2x timeout on SERVFAIL | Set `resolver.retry_servfail = False` | Environments with broken DNSSEC validation chains |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Verifying SAML signing cert from untrusted metadata | Scanner itself becomes vulnerable to cert substitution; irrelevant for read-only scanning | Acceptable for read-only CBOM inventory — scanner is not an SP verifying assertions |
| Logging full AS-REQ packet bytes to debug output | Kerberos traffic captured in logs; could be used for offline attack replay | Log only etype numbers and realm name, not raw packet bytes |
| Storing SAML certificates with private key material | Private keys never appear in metadata; but log output must not include any `<EncryptedKey>` content | Confirm scanner only reads public certificates, not private material |
| Making DNSSEC queries against client's production nameserver during scan | Zone transfer / bulk query triggers rate-limiting or IDS alert | Query only for specific record types (DNSKEY, DS) with standard UDP; do not attempt zone enumeration |
| Using `RC4_HMAC` etype in Kerberos scan probe in production | Some IDS (e.g., Microsoft Defender Identity) alert on RC4-only AS-REQ as AS-REP Roasting attempt | Probe with AES256+AES128+RC4 in the supported_etypes field (normal client behavior) rather than RC4-only |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Reporting "algorithm 5" without name in findings | User cannot understand findings without IANA lookup | Always render "RSASHA1 (algorithm 5)" in human-readable output |
| Reporting "no DNSSEC" without distinguishing "not signed" vs "unreachable resolver" | User doesn't know if they fixed the wrong thing | Use distinct finding codes: `DNSSEC_NOT_SIGNED` vs `DNSSEC_QUERY_FAILED` |
| Showing Kerberos etype results without KSK/ZSK context | User confuses identity protocol etypes with TLS ciphers | Identity tab in dashboard must group by protocol type, not by host:port alone |
| Reporting SAML signing algorithms from `<alg>` attributes only | Many SAML metadata docs omit `<alg>` — scanner appears to find nothing | Extract algorithm from the signing certificate public key itself, not just the algorithm attribute |

---

## "Looks Done But Isn't" Checklist

- [ ] **Kerberos etype scanner:** Often missing TCP/88 fallback — verify scan still works when UDP/88 is blocked
- [ ] **Kerberos etype scanner:** Often missing `KDC_ERR_PREAUTH_REQUIRED` parsing — verify it reads `PA-ETYPE-INFO2` not just a TCP connection success
- [ ] **SAML scanner:** Often missing no-`use`-attribute KeyDescriptor handling — verify it finds certs from Azure AD and Okta metadata fixtures (not just SimpleSAMLphp)
- [ ] **SAML scanner:** Often missing OIDC vs SAML path separation — verify `/descriptor` (XML) and `/.well-known/openid-configuration` (JSON) are handled by different code paths
- [ ] **DNSSEC scanner:** Often missing `dnspython[dnssec]` extra in `pyproject.toml` — verify `pip install .` gives a working scanner with a fresh virtualenv
- [ ] **DNSSEC scanner:** Often missing DO-bit on resolver — verify scanner finds DNSKEY records for `cloudflare.com` against a direct nameserver query
- [ ] **CBOM builder:** Often missing identity protocol elif — verify `build_cbom()` produces CBOM components for KERBEROS/SAML/DNSSEC endpoint objects (not just TLS/SSH)
- [ ] **Classifier:** Often missing DNSSEC algorithm number mapping — verify `classify_algorithm()` returns non-UNKNOWN for algorithm numbers 5, 7, 8, 13, 15
- [ ] **SQLite schema:** Often missing additive migration handler — verify scanner works against a `quirk.db` created by v4.1.0 (no identity columns present)
- [ ] **Chaos lab Kerberos:** Often missing `start_period` on Samba DC healthcheck — verify test passes after cold Docker pull (not warm restart)
- [ ] **Chaos lab DNSSEC:** Often serving unsigned zone — verify `dig @localhost DNSKEY chaos.local` returns at least one record before claiming chaos lab is ready

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| AS-REQ uses credentials, not PA-ETYPE-INFO2 | MEDIUM | Rewrite AS-REQ construction using raw impacket.krb5.asn1 KerberosRequest; no credential material needed |
| SAML namespace XPath returns empty | LOW | Add SAML_NS dict, update all findall() calls; 1-hour fix |
| DNSSEC missing [dnssec] extra | LOW | Add to pyproject.toml; pip install triggers automatically |
| CBOM builder produces TLS components for identity endpoints | MEDIUM | Add 3 elif branches per protocol; rebuild CBOM for affected scans |
| SQLite missing identity columns in existing db | LOW | Run ALTER TABLE ADD COLUMN manually; add to db.py startup migration |
| Samba DC chaos lab flakes | MEDIUM | Add healthcheck with start_period=90s; add retry in test fixture |
| DNSSEC chaos lab serves unsigned zone | MEDIUM | Rebuild BIND9 config with dnssec-policy; regenerate signed zone file |
| SAML PEM construction crashes | LOW | Switch to DER parsing via load_der_x509_certificate(base64.b64decode(raw_b64)) |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Kerberos AS-REQ uses credentials | Kerberos scanner design | Unit test confirms scan_error or etype list returned with no credential input |
| Kerberos UDP/88 blocked silently | Kerberos scanner implementation | Test with mocked socket.sendto timeout verifies TCP fallback triggers |
| SAML namespace XPath silent empty | SAML scanner implementation | Test against 3 metadata fixtures: SimpleSAMLphp, Keycloak, ADFS-style |
| SAML KeyDescriptor use=missing | SAML scanner implementation | Test with metadata fixture that has no @use attribute on KeyDescriptor |
| dnspython[dnssec] extra missing | Dependency declaration | CI test verifies dns.dnssec function call succeeds |
| DNSSEC system resolver strips DO bit | DNSSEC scanner design | Integration test queries BIND9 chaos lab with direct nameserver config |
| DNSSEC algorithm number not in classifier | DNSSEC + CBOM implementation | Test classify_algorithm with alg numbers 5, 7, 8, 13, 15 |
| SAML PEM wrapping crash | SAML scanner implementation | Test with certificates of varying lengths including real 4096-bit cert |
| identity_scan_json NOT NULL | Models/schema phase | Test migrate against a pre-existing v4.1 quirk.db fixture |
| CBOM builder TLS fallback for identity | CBOM builder update phase | Test build_cbom() with KERBEROS, SAML, DNSSEC endpoint objects |
| Samba DC startup race | Chaos lab setup phase | CI must cold-start Samba DC and verify port 88 responds before test |
| BIND9 serves unsigned zone | Chaos lab setup phase | `dig @localhost DNSKEY chaos.local +dnssec` returns records |
| Keycloak SAML endpoint timing | Chaos lab setup + SAML test design | SAML scanner test uses retry fixture; Keycloak has service_healthy condition |

---

## Sources

- [MIT Kerberos documentation — encryption types and KDC_ERR_ETYPE_NOSUPP behavior](https://web.mit.edu/kerberos/krb5-latest/doc/admin/enctypes.html)
- [impacket kerberosv5.py — KDC_ERR_ETYPE_NOSUPP fallback logic](https://github.com/CoreSecurity/impacket/blob/master/impacket/krb5/kerberosv5.py)
- [RFC 8624 — Algorithm Implementation Requirements and Usage Guidance for DNSSEC](https://datatracker.ietf.org/doc/html/rfc8624)
- [IANA DNSSEC Algorithm Numbers registry](https://www.iana.org/assignments/dns-sec-alg-numbers/dns-sec-alg-numbers.xml)
- [dnspython documentation — DNSSEC module and extras](https://dnspython.readthedocs.io/en/stable/dnssec.html)
- [SignXML Python XML Signature library — PEM/DER handling notes](https://xml-security.github.io/signxml/)
- [SimpleSAMLphp issue #999 — X509Certificate PEM header crash](https://github.com/simplesamlphp/simplesamlphp/issues/999)
- [python-saml README — namespace handling and lxml/xmlsec compatibility](https://github.com/SAML-Toolkits/python-saml)
- [lxml bug #2052475 — floating point exception when using lxml >= 5 with xmlsec](https://bugs.launchpad.net/lxml/+bug/2052475)
- [Helge Klein — Samba AD DC in Docker installation guide (2025)](https://helgeklein.com/blog/samba-active-directory-in-a-docker-container-installation-guide/)
- [smblds/smblds Docker image — Samba AD DC for development](https://hub.docker.com/r/smblds/smblds)
- [Docker Compose healthcheck documentation — start_period behavior](https://docs.docker.com/compose/how-tos/startup-order/)
- [Kerberos firewall requirements — UDP and TCP port 88](https://web.mit.edu/kerberos/www/krb5-1.5/krb5-1.5.4/doc/krb5-admin/Configuring-Your-Firewall-to-Work-With-Kerberos-V5.html)
- [OASIS SAML Metadata specification v2.0 — KeyDescriptor use attribute](https://docs.oasis-open.org/security/saml/v2.0/saml-metadata-2.0-os.pdf)
- [Shibboleth SAML Keys and Certificates — signing vs encryption KeyDescriptor ambiguity](https://shibboleth.atlassian.net/wiki/spaces/CONCEPT/pages/948470554/SAMLKeysAndCertificates)
- [Alembic batch migrations — SQLite ALTER TABLE constraints](https://alembic.sqlalchemy.org/en/latest/batch.html)
- [BIND9 DNSSEC Guide — dnssec-policy configuration for auto-signing](https://bind9.readthedocs.io/en/latest/dnssec-guide.html)
- [kenchan0130/simplesamlphp Docker image — chaos lab SAML IdP reference](https://github.com/kenchan0130/docker-simplesamlphp)
- [kristophjunge/test-saml-idp — port configuration pitfall in SAML metadata](https://github.com/kristophjunge/docker-test-saml-idp)

---
*Pitfalls research for: Identity protocol crypto scanners (Kerberos/SAML/DNSSEC) added to QU.I.R.K. v4.2*
*Researched: 2026-04-08*
