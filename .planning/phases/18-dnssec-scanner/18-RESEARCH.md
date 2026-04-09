# Phase 18: DNSSEC Scanner - Research

**Researched:** 2026-04-08
**Domain:** DNSSEC auditing via dnspython, RFC 8624/9905 algorithm classification, BIND9 chaos lab
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Finding Granularity**
- D-01: One CryptoEndpoint per DNSKEY record — each DNSKEY produces its own row with algorithm, key size, and flags (ZSK/KSK role + key_tag in `service_detail`). Matches JWT scanner pattern (one per key).
- D-02: Unsigned zones, NSEC exposure, and DS chain breaks also produce CryptoEndpoint rows — every finding is a CBOM entry. Unsigned zone uses `algorithm="NONE"`, `service_detail="unsigned-zone"`. NSEC exposure uses `service_detail="nsec-exposure"`. DS chain break uses `service_detail="ds-chain-broken"`.
- D-03: `dnssec_scan_json` stores a flat per-domain dict: `domain`, `ns_queried`, `signed` boolean, `dnskeys[]` array (flags, alg, tag, key_size, role), `ds_records[]` array (key_tag, algorithm, digest_type), `nsec_type`, `chain_valid`.

**Severity Classification**
- D-04: 3-tier DNSSEC algorithm severity map per RFC 8624/9905:
  - CRITICAL: RSAMD5 (alg 1), DSA/SHA1 (alg 3), RSASHA1 (alg 5), DSA-NSEC3 (alg 6), RSASHA1-NSEC3 (alg 7)
  - HIGH: RSASHA256 (alg 8), RSASHA512 (alg 10) — quantum-vulnerable RSA
  - Safe (no finding): ECDSAP256SHA256 (alg 13), ECDSAP384SHA384 (alg 14), ED25519 (alg 15), ED448 (alg 16)
- D-05: NSEC zone-enumeration exposure = MEDIUM severity.
- D-06: SHA-1 DS digest type (type 1) = MEDIUM severity. SHA-256 (type 2) and SHA-384 (type 4) are acceptable.
- D-07: Unsigned zone = HIGH severity. Broken DS chain = HIGH severity.

**Chaos Lab**
- D-08: 4 BIND9 zones: `weak.chaos.local` (RSASHA1+NSEC), `safe.chaos.local` (ECDSAP256SHA256+NSEC3), `broken.chaos.local` (valid DNSKEY, DS key_tag mismatch), `unsigned.chaos.local` (no DNSSEC).
- D-09: Pre-signed zone files baked into Docker image — deterministic. No runtime key generation. Zone files generated with `dnssec-keygen` + `dnssec-signzone`, committed under `quantum-chaos-enterprise-lab/bind9/zones/`.
- D-10: Dedicated `dnssec` Docker Compose profile, not grouped under `identity`. Activated via `docker compose --profile dnssec up`.

**Scan Error Handling**
- D-11: On unreachable NS or SERVFAIL: retry once, then skip domain with warning log. Error details optionally in `dnssec_scan_json`.
- D-12: Auto-resolve authoritative NS from domain name — scanner resolves NS records first, then queries DNSKEY/DS against those NS directly.
- D-13: UDP first, TCP fallback — dnspython's `udp_with_fallback()` handles this natively.

**run_scan.py Integration**
- D-14: DNSSEC scan phase block added after Azure connector, before endpoint aggregation. Guarded by `cfg.connectors.enable_dnssec and cfg.connectors.dnssec_targets`. Wrapped in `_phase_timer(run_stats, "dnssec_scanning")`.
- D-15: Function signature: `scan_dnssec_targets(targets: list, timeout: int = 10, logger=None) -> list[CryptoEndpoint]`. Matches JWT scanner pattern exactly.

**CBOM Builder Mapping**
- D-16: DNSSEC algorithm stored in `cert_pubkey_alg` field. Key size in `cert_pubkey_size` for RSA algorithms. Builder branch: `elif ep.protocol == "DNSSEC": _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)`.

**Scan Timeout + Concurrency**
- D-17: Sequential domain scanning — no threading.
- D-18: 5-second per-query timeout for DNS UDP/TCP calls.

### Claude's Discretion

- BIND9 Dockerfile specifics and base image version
- Internal helper function naming (`_scan_domain`, `_resolve_ns`, `_parse_dnskeys`, etc.)
- Exact BIND9 named.conf structure for the 4 zones
- How to construct the broken DS chain scenario (e.g., wrong key_tag in parent zone file)
- `DNSSEC_ALG_MAP` constant placement (in `dnssec_scanner.py` or `cbom/classifier.py`)
- Whether to add `DNSSEC_AVAILABLE` import guard (matching `HTTPX_AVAILABLE` in jwt_scanner.py)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DNSSEC-01 | Scanner queries DNSKEY and DS records via dnspython with DO bit set against authoritative nameservers directly (not system resolver) | `dns.message.make_query(want_dnssec=True)` + `dns.query.udp_with_fallback()` against NS-resolved addresses |
| DNSSEC-02 | Algorithm classification per RFC 8624/RFC 9905 — RSASHA1 (alg 5) and RSASHA1-NSEC3-SHA1 (alg 7) flagged as CRITICAL | `DNSSEC_ALG_MAP` dict keyed by int alg number; RFC 9905 confirms alg 5/7 MUST NOT status |
| DNSSEC-03 | Unsigned zone detected and flagged as HIGH severity | Missing DNSKEY rrset in answer → `algorithm="NONE"`, `service_detail="unsigned-zone"` |
| DNSSEC-04 | Results in `dnssec_scan_json`, `protocol="DNSSEC"` CryptoEndpoints, `DNSSEC_ALG_MAP` in classifier, `build_cbom()` DNSSEC elif branch | Follows JWT scanner and builder patterns exactly; classifier entry format confirmed |
| DNSSEC-05 | NSEC vs NSEC3 detected; NSEC flagged as zone-enumerable exposure | `dns.rdatatype.NSEC = 47`, `dns.rdatatype.NSEC3 = 50`; query SOA to trigger NSEC/NSEC3 in authority section |
| DNSSEC-06 | DS broken chain detection — mismatched key tags between DS and DNSKEY records flagged as HIGH | `dns.dnssec.key_id(dnskey_rdata)` returns int; compare against DS record `key_tag` attribute |
| DNSSEC-07 | Chaos lab gains BIND9 `dnssec` Docker Compose profile with RSASHA1-signed zone and ECDSAP256SHA256 zone | `internetsystemsconsortium/bind9:9.18`; pre-signed zone files baked into custom Dockerfile |
</phase_requirements>

---

## Summary

Phase 18 implements a DNSSEC posture scanner that audits domains for signing algorithm weaknesses, unsigned zones, NSEC zone-enumeration exposure, and broken DS chains. All findings feed into the CBOM as `protocol="DNSSEC"` CryptoEndpoint rows, consistent with the established JWT/SSH scanner patterns.

The technical implementation has three parts: (1) a `dnspython`-based scanner module in `quirk/scanner/dnssec_scanner.py` that resolves authoritative NS, sends DO-bit queries, and classifies findings; (2) classifier and CBOM builder extensions; and (3) a BIND9 Docker service in the chaos lab with four pre-signed zones covering all test scenarios.

All architectural decisions are locked in CONTEXT.md. The key open question is the BIND9 image variant and Dockerfile structure for embedding pre-signed zone files — both are within Claude's discretion and are addressed in this research.

**Primary recommendation:** Use `dns.query.udp_with_fallback()` with `want_dnssec=True` for all DNSKEY/DS queries; resolve authoritative NS first via a plain NS query; use `dns.dnssec.key_id()` for key tag computation; and build the BIND9 chaos lab on `internetsystemsconsortium/bind9:9.18` with pre-signed zone files baked into a custom Dockerfile.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dnspython | 2.8.0 | DNS record queries with DNSSEC support (DO bit, DNSKEY, DS, NSEC, NSEC3) | Already declared in `pyproject.toml` `[identity]` extras; current pip-available version |
| cryptography | >=45 (already installed) | Required by `dnspython[dnssec]` for RRSIG validation | Transitive dep; already in venv |

**Version verification:** `pip index versions dnspython` confirmed 2.8.0 is the current release (2026-04-08).

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| internetsystemsconsortium/bind9 | 9.18 | BIND9 DNS server for chaos lab | Docker chaos lab only; LTS branch, supported through ~2026 |
| json (stdlib) | — | Serialize `dnssec_scan_json` | Always (no extra dep needed) |

**Installation (already in pyproject.toml):**
```bash
pip install "dnspython[dnssec]>=2.8.0"
```

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dnspython | scapy | Scapy needs raw socket privileges; dnspython is pure Python, pip-only, fits pip-only constraint |
| internetsystemsconsortium/bind9:9.18 | ubuntu/bind9 | ubuntu/bind9 is Canonical-maintained but thinner docs; ISC image is authoritative source |

---

## Architecture Patterns

### Recommended Project Structure

```
quirk/scanner/dnssec_scanner.py      # New scanner module
quantum-chaos-enterprise-lab/
└── bind9/
    ├── Dockerfile                    # Custom image baking in pre-signed zones
    ├── named.conf                    # Main BIND9 config (include zones.conf)
    ├── named.conf.options            # Listen-on any, allow-query any
    ├── zones.conf                    # Zone declarations for all 4 zones
    └── zones/
        ├── weak.chaos.local.zone    # RSASHA1 signed zone file
        ├── safe.chaos.local.zone    # ECDSAP256SHA256 signed zone file
        ├── broken.chaos.local.zone  # Zone with DS key_tag mismatch
        └── unsigned.chaos.local.zone # Unsigned zone file
```

### Pattern 1: dnspython Query with DO Bit (Authoritative NS)

**What:** Send DNSKEY/DS queries directly to authoritative nameservers with the DNSSEC OK flag, using UDP with automatic TCP fallback for truncated responses.

**When to use:** All DNSSEC record queries in the scanner.

```python
# Source: https://github.com/rthalley/dnspython/issues/621 (verified pattern)
import dns.message
import dns.query
import dns.rdatatype
import dns.resolver

def _resolve_ns(domain: str, timeout: int) -> list[str]:
    """Return IP addresses of authoritative nameservers for domain."""
    try:
        # Use system resolver for NS lookup — only DNSKEY/DS need auth NS
        answers = dns.resolver.resolve(domain, "NS", lifetime=timeout)
        ns_names = [str(rdata.target) for rdata in answers]
        ns_ips = []
        for ns_name in ns_names:
            try:
                a_answers = dns.resolver.resolve(ns_name, "A", lifetime=timeout)
                ns_ips.extend([str(r) for r in a_answers])
            except Exception:
                pass
        return ns_ips
    except Exception:
        return []

def _query_rrset(domain: str, rdtype: int, ns_ip: str, timeout: int):
    """Query an rrset from a specific nameserver with DO bit set."""
    request = dns.message.make_query(domain, rdtype, want_dnssec=True)
    # Flags: RD is cleared for authoritative queries; want_dnssec sets DO in EDNS
    request.flags &= ~dns.flags.RD
    response, _tcp_used = dns.query.udp_with_fallback(
        request, ns_ip, timeout=timeout
    )
    return response
```

### Pattern 2: DNSKEY Record Parsing

**What:** Extract algorithm number, flags (KSK vs ZSK via SEP bit), key tag, and RSA key size from DNSKEY rdata objects.

**When to use:** After receiving DNSKEY rrset from authoritative NS.

```python
# Source: dnspython DNSKEY rdata attributes (flags, protocol, algorithm, key)
# KSK: flags = 257 (bit 8=ZONE + bit 0=SEP); ZSK: flags = 256 (ZONE only)
import dns.dnssec
import math

def _parse_dnskeys(dnskey_rrset) -> list[dict]:
    results = []
    for rdata in dnskey_rrset:
        alg_num = int(rdata.algorithm)
        key_tag = dns.dnssec.key_id(rdata)
        role = "KSK" if (rdata.flags & 0x0001) else "ZSK"  # SEP bit
        # RSA key size from key material length (modulus is the bulk of RSA key bytes)
        key_size = None
        if alg_num in (1, 5, 7, 8, 10):  # RSA family
            key_size = (len(rdata.key) - 3) * 8  # approximate; more precise: parse modulus
        results.append({
            "flags": rdata.flags,
            "alg": alg_num,
            "tag": key_tag,
            "key_size": key_size,
            "role": role,
        })
    return results
```

**RSA key size note:** For RSA algorithms, the key material format is: 1-byte exponent length, exponent bytes, then modulus bytes. To get exact modulus bit length, parse the first byte to find exponent length, then count remaining bytes. A simpler approximation is `(len(rdata.key) - 3) * 8` for typical 65537 exponent cases. For production precision, use modulus byte count directly.

### Pattern 3: DS Record Parsing and Chain Validation

**What:** Fetch DS records, extract key_tag/algorithm/digest_type, compare against DNSKEY key tags to detect broken chains.

**When to use:** Chain validation for DNSSEC-06.

```python
# Source: dns.rdatatype.DS — attributes: key_tag, algorithm, digest_type, digest
def _parse_ds_records(ds_rrset) -> list[dict]:
    return [
        {
            "key_tag": rdata.key_tag,
            "algorithm": int(rdata.algorithm),
            "digest_type": rdata.digest_type,
        }
        for rdata in ds_rrset
    ]

def _check_chain(dnskeys: list[dict], ds_records: list[dict]) -> bool:
    """Returns True if at least one DS key_tag matches a DNSKEY key_tag."""
    dnskey_tags = {d["tag"] for d in dnskeys}
    ds_tags = {ds["key_tag"] for ds in ds_records}
    return bool(dnskey_tags & ds_tags)  # intersection non-empty = valid chain
```

### Pattern 4: NSEC/NSEC3 Detection

**What:** Detect which denial-of-existence record type the zone uses by sending a query for a non-existent name and examining the authority section.

**When to use:** NSEC exposure detection (DNSSEC-05).

```python
# dns.rdatatype.NSEC = 47, dns.rdatatype.NSEC3 = 50
import dns.rdatatype

def _detect_nsec_type(domain: str, ns_ip: str, timeout: int) -> str | None:
    """Returns 'NSEC', 'NSEC3', or None if unsigned/unreachable."""
    # Query for a guaranteed non-existent name to trigger NSEC/NSEC3 in authority
    nxdomain_name = f"_quirk_probe_.{domain}"
    try:
        request = dns.message.make_query(nxdomain_name, dns.rdatatype.A, want_dnssec=True)
        request.flags &= ~dns.flags.RD
        response, _ = dns.query.udp_with_fallback(request, ns_ip, timeout=timeout)
        for rrset in response.authority:
            if rrset.rdtype == dns.rdatatype.NSEC:
                return "NSEC"
            if rrset.rdtype == dns.rdatatype.NSEC3:
                return "NSEC3"
    except Exception:
        pass
    return None
```

### Pattern 5: CryptoEndpoint Construction for DNSSEC

**What:** Build CryptoEndpoint rows matching the JWT scanner pattern — one row per DNSKEY, plus synthetic rows for unsigned/NSEC/chain-broken findings.

**When to use:** Constructing all output from `scan_dnssec_targets()`.

```python
# Source: jwt_scanner.py pattern (confirmed working in project)
from quirk.models import CryptoEndpoint
import json
from datetime import datetime, timezone

# DNSKEY finding
ep = CryptoEndpoint(
    host=domain,
    port=53,
    protocol="DNSSEC",
    cert_pubkey_alg="RSASHA1",       # human-readable alg name
    cert_pubkey_size=2048,            # RSA key size or None for EC
    dnssec_scan_json=json.dumps(scan_dict),
    service_detail=f"dnskey:tag={key_tag}:role={role}",
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)

# Unsigned zone synthetic finding
ep = CryptoEndpoint(
    host=domain,
    port=53,
    protocol="DNSSEC",
    cert_pubkey_alg="NONE",
    cert_pubkey_size=None,
    dnssec_scan_json=json.dumps(scan_dict),
    service_detail="unsigned-zone",
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)

# NSEC exposure finding
ep = CryptoEndpoint(
    host=domain, port=53, protocol="DNSSEC",
    cert_pubkey_alg="NSEC",
    cert_pubkey_size=None,
    dnssec_scan_json=json.dumps(scan_dict),
    service_detail="nsec-exposure",
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)

# DS chain broken finding
ep = CryptoEndpoint(
    host=domain, port=53, protocol="DNSSEC",
    cert_pubkey_alg="DS-MISMATCH",
    cert_pubkey_size=None,
    dnssec_scan_json=json.dumps(scan_dict),
    service_detail="ds-chain-broken",
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
```

### Pattern 6: DNSSEC_ALG_MAP for Classifier

**What:** Map integer DNSSEC algorithm numbers to severity labels. The existing `classifier.py` uses `_ALGORITHM_TABLE` keyed by lowercase string names; DNSSEC scanner needs its own lookup by integer alg number.

**When to use:** When deciding which CryptoEndpoints to create and their severity-relevant algorithm names.

```python
# Placement: at top of dnssec_scanner.py (Claude's discretion per CONTEXT.md)
# Per D-04 decisions
DNSSEC_ALG_MAP: dict[int, tuple[str, str]] = {
    # alg_num: (human_name, severity)
    1:  ("RSAMD5",              "CRITICAL"),  # RFC 8624: MUST NOT
    3:  ("DSA",                 "CRITICAL"),  # RFC 8624: MUST NOT
    5:  ("RSASHA1",             "CRITICAL"),  # RFC 9905: MUST NOT
    6:  ("DSA-NSEC3-SHA1",      "CRITICAL"),  # RFC 8624: MUST NOT
    7:  ("RSASHA1-NSEC3-SHA1",  "CRITICAL"),  # RFC 9905: MUST NOT
    8:  ("RSASHA256",           "HIGH"),      # quantum-vulnerable RSA
    10: ("RSASHA512",           "HIGH"),      # quantum-vulnerable RSA
    12: ("ECC-GOST",            "CRITICAL"),  # RFC 8624: MUST NOT
    13: ("ECDSAP256SHA256",     "SAFE"),
    14: ("ECDSAP384SHA384",     "SAFE"),
    15: ("ED25519",             "SAFE"),
    16: ("ED448",               "SAFE"),
}
```

The classifier `_ALGORITHM_TABLE` should also receive entries for the DNSSEC algorithm name strings (e.g., `"rsasha1"`, `"rsasha256"`, `"ecdsap256sha256"`) mapped to the appropriate CryptoPrimitive and NIST level. This is needed for `build_cbom()` to resolve algorithm primitives.

### Pattern 7: BIND9 Chaos Lab Docker Structure

**What:** Custom Dockerfile from `internetsystemsconsortium/bind9:9.18` that bakes in pre-signed zone files.

**When to use:** DNSSEC-07 requirement.

```dockerfile
# quantum-chaos-enterprise-lab/bind9/Dockerfile
FROM internetsystemsconsortium/bind9:9.18

COPY named.conf /etc/bind/named.conf
COPY named.conf.options /etc/bind/named.conf.options
COPY zones.conf /etc/bind/zones.conf
COPY zones/ /etc/bind/zones/
```

```
# named.conf.options
options {
    directory "/var/cache/bind";
    listen-on { any; };
    listen-on-v6 { any; };
    allow-query { any; };
    recursion no;         # authoritative-only
    dnssec-validation no; # we're the authority, not a validator
};
```

```
# zones.conf (included from named.conf)
zone "weak.chaos.local" { type master; file "/etc/bind/zones/weak.chaos.local.zone"; };
zone "safe.chaos.local" { type master; file "/etc/bind/zones/safe.chaos.local.zone"; };
zone "broken.chaos.local" { type master; file "/etc/bind/zones/broken.chaos.local.zone"; };
zone "unsigned.chaos.local" { type master; file "/etc/bind/zones/unsigned.chaos.local.zone"; };
```

```yaml
# docker-compose.yml addition (dnssec profile)
bind9-dnssec:
  build:
    context: ./bind9
    dockerfile: Dockerfile
  profiles: ["dnssec"]
  ports:
    - "15353:53/udp"
    - "15353:53/tcp"
  healthcheck:
    test: ["CMD", "dig", "@127.0.0.1", "weak.chaos.local", "SOA"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 15s
```

### Pattern 8: Broken DS Chain Construction

**What:** Create `broken.chaos.local` with a valid signed DNSKEY but a DS record in its parent zone using a deliberately wrong key_tag.

**Implementation approach** (Claude's discretion): The zone itself is normally signed with ECDSAP256SHA256. The parent zone's DS record references a `key_tag` that does not match any DNSKEY in the zone. In the chaos lab context where we are the authoritative authority for both parent and child, we construct the zone file with a valid `DNSKEY` record but craft the DS record manually in the parent zone using a fake key_tag (e.g., `12345` when real key_tag is `54321`). The scanner compares DNSKEY key_tags against DS key_tags and finds no intersection.

### Anti-Patterns to Avoid

- **Querying the system resolver for DNSKEY/DS:** System resolvers (including Docker's internal resolver) strip DNSSEC records and do not pass the DO bit. Always resolve directly to authoritative NS IPs.
- **Ignoring the TC bit:** Large DNSSEC responses (containing RRSIG, multiple DNSKEY) routinely exceed UDP 512-byte limit. Not using `udp_with_fallback()` causes silent data loss.
- **Forgetting to clear RD flag:** When querying an authoritative server directly, the Recursion Desired flag should be cleared (`request.flags &= ~dns.flags.RD`). Some authoritative servers refuse queries with RD set.
- **Treating SERVFAIL as unsigned:** SERVFAIL may mean broken delegation, not absence of DNSSEC. Log the error distinctly; do not emit an unsigned-zone finding on SERVFAIL.
- **Key size from algorithm number alone:** RSA key sizes vary (1024, 2048, 4096). Must parse actual key material to determine size; algorithm number only tells you it's RSA, not the modulus size.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TCP fallback on truncation | Custom UDP/TCP retry logic | `dns.query.udp_with_fallback()` | Handles TC bit detection, message assembly, socket lifecycle automatically |
| Key tag computation | Manual DNSKEY key_tag calculation (RFC 4034 §B.1 checksum algorithm) | `dns.dnssec.key_id(rdata)` | RFC 4034 key_tag algorithm is non-trivial (16-bit sum with 16-bit folding for alg 1); dnspython implements it correctly |
| DNSSEC algorithm names | String mapping table from scratch | `dns.dnssec.algorithm_to_text(int)` | Returns canonical IANA names; dnspython table is authoritative |
| NSEC3 hash computation | NSEC3 hashing (RFC 5155) | `dns.dnssec.nsec3_hash()` | NSEC3 uses iterated SHA-1 with salt — implementation-error-prone |
| DS record generation | Computing DS digest from DNSKEY | `dns.dnssec.make_ds()` | Handles SHA-1/SHA-256/SHA-384 digest computation correctly |

**Key insight:** dnspython's DNSSEC support handles the cryptographic and protocol-level details. The scanner's job is orchestration (resolve NS, fire queries, classify results, emit CryptoEndpoints) — not re-implementing RFC 4034/5155.

---

## Common Pitfalls

### Pitfall 1: System Resolver Strips DNSSEC Records
**What goes wrong:** Using `dns.resolver.resolve(domain, "DNSKEY")` returns no records or SERVFAIL because the default system resolver doesn't pass DO bit or discards DNSKEY rrsets.
**Why it happens:** Docker's internal resolver (`127.0.0.11`) and many ISP resolvers strip DNSSEC records even when DNSSEC is configured.
**How to avoid:** Always resolve authoritative NS first (plain NS query, system resolver is fine here), then send DNSKEY/DS queries directly to the authoritative NS IP using `dns.query.udp_with_fallback()`.
**Warning signs:** DNSKEY rrset is empty for a zone you know is signed; `dig @system-resolver example.com DNSKEY` returns nothing.

### Pitfall 2: DNSSEC Scanner Import Guard Pattern
**What goes wrong:** If `dnspython[dnssec]` is not installed (user didn't install identity extras), the module import crashes and the entire scan fails.
**Why it happens:** `dnspython[dnssec]` is an optional extras group, not a core dependency.
**How to avoid:** Use the same import guard pattern as `jwt_scanner.py`:
```python
try:
    import dns.message
    import dns.query
    import dns.rdatatype
    import dns.dnssec
    DNSPYTHON_AVAILABLE = True
except ImportError:
    DNSPYTHON_AVAILABLE = False
```
Return `[]` immediately from `scan_dnssec_targets()` if `DNSPYTHON_AVAILABLE` is False.
**Warning signs:** `ModuleNotFoundError: No module named 'dns'` during scan.

### Pitfall 3: Pre-signed Zone File Determinism
**What goes wrong:** BIND9 auto-DNSSEC management regenerates keys on container restart, producing different key_tags every boot. Test assertions that check specific key_tags break.
**Why it happens:** Modern BIND9 has `dnssec-policy` auto-signing that is active by default in some configurations.
**How to avoid:** Use `dnssec-policy "none"` in zone declarations (or omit dnssec-policy entirely) and bake in manually pre-signed zone files. Do NOT use `auto-dnssec maintain` or `inline-signing yes`.
**Warning signs:** Zone file changes after container restart; key_tag values vary between runs.

### Pitfall 4: NSEC3 False Negative for Unsigned Zone
**What goes wrong:** A domain that is DNSSEC-signed but uses NSEC3 returns no NSEC records for the probe query (by design — NSEC3 hashes names). The scanner incorrectly reports it as "no NSEC type found" (unsigned).
**Why it happens:** NSEC3 doesn't return plaintext next-name chains; it returns hashed NSEC3 records. Both NSEC and NSEC3 appear in the authority section of an NXDOMAIN response.
**How to avoid:** Check rdtype separately: `rrset.rdtype == dns.rdatatype.NSEC` vs `rrset.rdtype == dns.rdatatype.NSEC3`. Only NSEC (not NSEC3) is flagged as zone-enumerable exposure.
**Warning signs:** ECDSAP256SHA256+NSEC3 zone (`safe.chaos.local`) reports NSEC exposure.

### Pitfall 5: DS Records in Parent vs Child Zone
**What goes wrong:** Querying DS records against the child zone's authoritative NS returns NXDOMAIN — DS records live in the PARENT zone, not the child.
**Why it happens:** DS (Delegation Signer) records are published by the parent zone's NS. The child zone never holds its own DS records.
**How to avoid:** For the chaos lab, the "parent" zone is also one of our BIND9 zones (e.g., `chaos.local`). In real-world scanning, DS records must be queried from the parent's NS (the TLD nameserver for `example.com`'s DS). For simplicity in the scanner, query DS against the authoritative NS of the domain — BIND9 will serve the parent's DS records from the chaos lab because we control the whole hierarchy. For real domains, resolve the parent zone's NS separately.
**Warning signs:** DS rrset empty when querying the child's own authoritative NS.

### Pitfall 6: RSA Key Size Calculation Edge Cases
**What goes wrong:** `len(rdata.key) * 8` overestimates RSA key size because the key material starts with an exponent length byte, the exponent itself, then the modulus.
**Why it happens:** RFC 3110 format for RSA public keys: first byte = exponent length (if < 256) or `\x00` + 2-byte exponent length; then exponent bytes; then modulus bytes.
**How to avoid:** Parse the exponent length correctly:
```python
key_bytes = rdata.key
if key_bytes[0] == 0:
    exp_len = (key_bytes[1] << 8) | key_bytes[2]
    modulus_start = 3 + exp_len
else:
    exp_len = key_bytes[0]
    modulus_start = 1 + exp_len
key_size = (len(key_bytes) - modulus_start) * 8
```
**Warning signs:** RSA-2048 key reported as 2072 bits.

---

## Code Examples

Verified patterns from official sources and existing project code:

### Complete scan_dnssec_domain() skeleton
```python
# Source: Derived from dns.query.udp_with_fallback (github.com/rthalley/dnspython/issues/621)
# and jwt_scanner.py pattern in this project

def _scan_domain(domain: str, timeout: int, logger=None) -> dict:
    """Scan a single domain and return raw scan dict per D-03 schema."""
    result = {
        "domain": domain,
        "ns_queried": None,
        "signed": False,
        "dnskeys": [],
        "ds_records": [],
        "nsec_type": None,
        "chain_valid": None,
        "error": None,
    }

    # Step 1: Resolve authoritative NS
    ns_ips = _resolve_ns(domain, timeout)
    if not ns_ips:
        result["error"] = "ns-resolve-failed"
        return result

    ns_ip = ns_ips[0]
    result["ns_queried"] = ns_ip

    # Step 2: Query DNSKEY with DO bit
    try:
        resp = _query_rrset(domain, dns.rdatatype.DNSKEY, ns_ip, timeout)
        dnskey_rrsets = [r for r in resp.answer if r.rdtype == dns.rdatatype.DNSKEY]
        if not dnskey_rrsets:
            result["signed"] = False
            return result  # unsigned zone — return early
        result["signed"] = True
        result["dnskeys"] = _parse_dnskeys(dnskey_rrsets[0])
    except Exception as exc:
        result["error"] = f"dnskey-query-failed: {exc}"
        return result

    # Step 3: Query DS records
    try:
        resp = _query_rrset(domain, dns.rdatatype.DS, ns_ip, timeout)
        ds_rrsets = [r for r in resp.answer if r.rdtype == dns.rdatatype.DS]
        if ds_rrsets:
            result["ds_records"] = _parse_ds_records(ds_rrsets[0])
    except Exception:
        pass  # DS absence doesn't block other findings

    # Step 4: Detect NSEC type
    result["nsec_type"] = _detect_nsec_type(domain, ns_ip, timeout)

    # Step 5: Chain validation
    if result["dnskeys"] and result["ds_records"]:
        result["chain_valid"] = _check_chain(result["dnskeys"], result["ds_records"])
    elif result["dnskeys"]:
        result["chain_valid"] = None  # no DS to validate against

    return result
```

### run_scan.py integration block
```python
# Insert after azure scan block (~line 457), before endpoint aggregation
# Source: existing _phase_timer and scan_* patterns in run_scan.py

# ==============================
# DNSSEC scan phase
# ==============================
dnssec_endpoints = []
with _phase_timer(run_stats, "dnssec_scanning"):
    if cfg.connectors.enable_dnssec and cfg.connectors.dnssec_targets:
        dnssec_endpoints = scan_dnssec_targets(
            cfg.connectors.dnssec_targets,
            timeout=cfg.scan.timeout_seconds,
            logger=logger,
        )

# Update aggregation line:
endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints
             + jwt_endpoints + container_endpoints + source_endpoints
             + aws_endpoints + azure_endpoints + dnssec_endpoints)
```

### CBOM builder elif branch
```python
# Insert in build_cbom() algorithm registration loop (~line 338 in builder.py)
# After the elif ep.protocol == "AZURE": block

elif ep.protocol == "DNSSEC":
    # cert_pubkey_alg holds algorithm name (e.g., "RSASHA256", "NONE", "NSEC")
    if ep.cert_pubkey_alg and ep.cert_pubkey_alg not in ("NONE", "NSEC", "DS-MISMATCH"):
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

### classifier.py additions
```python
# Add to _ALGORITHM_TABLE in quirk/cbom/classifier.py
# DNSSEC signing algorithms (lowercase, matches classify_algorithm() normalization)
"rsasha1":           (CryptoPrimitive.SIGNATURE, 0, 80),   # SHA-1 broken; CRITICAL
"rsasha1-nsec3-sha1":(CryptoPrimitive.SIGNATURE, 0, 80),   # SHA-1 broken; CRITICAL
"rsasha256":         (CryptoPrimitive.SIGNATURE, 0, 112),  # RSA quantum-vulnerable; HIGH
"rsasha512":         (CryptoPrimitive.SIGNATURE, 0, 112),  # RSA quantum-vulnerable; HIGH
"ecdsap256sha256":   (CryptoPrimitive.SIGNATURE, 0, 128),  # ECDSA quantum-vulnerable; SAFE per D-04
"ecdsap384sha384":   (CryptoPrimitive.SIGNATURE, 0, 192),  # ECDSA quantum-vulnerable; SAFE per D-04
# ed25519 and ed448 already in table
"rsamd5":            (CryptoPrimitive.SIGNATURE, 0, 80),   # MD5 broken; CRITICAL
"dsa":               (CryptoPrimitive.SIGNATURE, 0, 112),  # DSA; CRITICAL
```

---

## Runtime State Inventory

> This section is omitted — Phase 18 is a greenfield scanner module addition. No rename, refactor, or migration is involved.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All code | ✓ | 3.14.3 | — |
| dnspython[dnssec] | Scanner module | ✗ (not in venv) | 2.8.0 installable | Scanner returns [] (import guard) |
| Docker | Chaos lab | ✓ (daemon not running in this session) | 29.3.1 | Run manually |
| BIND9 tools (dnssec-keygen, dnssec-signzone) | Zone file pre-signing | ✗ | — | Run in Docker container during build |
| cryptography (Python) | dnspython[dnssec] transitive dep | ✓ | 46.0.6 | — |

**Missing dependencies with no fallback:**
- `dnspython[dnssec]` must be installed in the project venv before the scanner runs: `pip install "dnspython[dnssec]>=2.8.0"`. Plan 02 must include this install step (or instruct user to `pip install -e ".[identity]"`).
- `dnssec-keygen` and `dnssec-signzone` (BIND9 tools) are required to pre-sign the chaos lab zones. These run inside a temporary BIND9 container during the build step — they do NOT need to be installed on the host. The Dockerfile's build stage or a helper script handles key generation.

**Missing dependencies with fallback:**
- Docker daemon not running: chaos lab tests cannot run without Docker. The unit tests mock DNS responses and do not require Docker. Only integration validation of DNSSEC-07 requires Docker.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| RSASHA1 (alg 5) for production zones | ECDSAP256SHA256 (alg 13) or ED25519 (alg 15) | RFC 9905 (2025) | RSASHA1 is MUST NOT per RFC 9905 |
| RSA-2048 DNSSEC (alg 8) | ECDSA or EdDSA | RFC 8624 (2019) updated | RSA still broadly deployed but flagged HIGH for quantum risk |
| NSEC for denial-of-existence | NSEC3 (with opt-out) | RFC 5155 (2008), now standard | NSEC allows zone enumeration; NSEC3 prevents it |
| `auto-dnssec maintain` + `inline-signing` | `dnssec-policy` (BIND 9.16+) | BIND 9.16 (2020) | auto-dnssec is deprecated in BIND 9.18+ |

**Deprecated/outdated:**
- `dns.query.udp()` without fallback: Still works but truncated responses silently lose DNSSEC data. Use `dns.query.udp_with_fallback()` instead.
- BIND9's `auto-dnssec maintain`: Removed/deprecated in BIND 9.18; use `dnssec-policy` or pre-signed zones.
- Algorithm 12 (ECC-GOST): Deprecated in RFC 8624 (MUST NOT). Not commonly seen but should be in the CRITICAL bucket.

---

## Open Questions

1. **DS record querying in the chaos lab**
   - What we know: In real-world DNS, DS records are published in the parent zone's NS. In the chaos lab, we control both the parent (`chaos.local`) and child zones (`weak.chaos.local`).
   - What's unclear: Whether to model a separate `chaos.local` parent zone in BIND9 that holds DS records for each child, or to embed DS records directly in the child zone file (non-standard but BIND9 will serve them).
   - Recommendation: Create a `chaos.local` parent zone file containing DS records for `weak.chaos.local` and `broken.chaos.local` (with wrong key_tag). The scanner queries DS from the parent's NS. This matches real-world DNS hierarchy. Alternatively — and more simply — query DS against the same authoritative NS as DNSKEY; BIND9 will answer from the parent zone if that NS is authoritative for it. This is Claude's discretion.

2. **DNSSEC_ALG_MAP placement**
   - What we know: Context.md marks this as Claude's discretion (in `dnssec_scanner.py` or `cbom/classifier.py`).
   - What's unclear: Keeping it in `dnssec_scanner.py` avoids touching the classifier for DNSSEC severity; keeping it in `classifier.py` centralizes all algorithm knowledge.
   - Recommendation: Place in `dnssec_scanner.py`. The existing classifier works on string algorithm names from TLS/SSH/JWT flows; DNSSEC algorithm numbers are integers and form a separate lookup path. This keeps the classifier's `_ALGORITHM_TABLE` clean. Add the human-readable string names (e.g., `"rsasha1"`) to `_ALGORITHM_TABLE` for CBOM builder resolution — this is a separate concern from severity classification.

3. **Pre-signed zone file generation workflow**
   - What we know: `dnssec-keygen` and `dnssec-signzone` are not available on the host (confirmed). Zone files must be pre-signed and committed.
   - What's unclear: Whether to include a `scripts/generate_zones.sh` helper that the implementer runs once inside a BIND9 container, or to include the already-generated signed zone files directly in the commit.
   - Recommendation: Include a `scripts/generate_zones.sh` that runs inside a `bind9:9.18` container to produce signed zone files, and commit the resulting `.zone` files. This makes the chaos lab deterministic (committed zone files) while documenting how they were produced.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_dnssec_scanner.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DNSSEC-01 | `scan_dnssec_targets()` queries DNSKEY with DO bit against authoritative NS | unit (mocked) | `pytest tests/test_dnssec_scanner.py::test_dnskey_query_do_bit -x` | ❌ Wave 0 |
| DNSSEC-02 | RSASHA1 (alg 5) → CRITICAL; ED25519 (alg 15) → no finding | unit | `pytest tests/test_dnssec_scanner.py::test_algorithm_classification -x` | ❌ Wave 0 |
| DNSSEC-03 | Domain with no DNSKEY rrset produces `protocol=DNSSEC, cert_pubkey_alg=NONE, service_detail=unsigned-zone` | unit (mocked) | `pytest tests/test_dnssec_scanner.py::test_unsigned_zone -x` | ❌ Wave 0 |
| DNSSEC-04 | CryptoEndpoint rows have `protocol="DNSSEC"`; `dnssec_scan_json` is valid JSON with required fields; CBOM builder processes DNSSEC endpoints | unit | `pytest tests/test_dnssec_scanner.py::test_cbom_integration -x` | ❌ Wave 0 |
| DNSSEC-05 | NSEC rrset in authority → `service_detail=nsec-exposure`; NSEC3 → no nsec finding | unit (mocked) | `pytest tests/test_dnssec_scanner.py::test_nsec_detection -x` | ❌ Wave 0 |
| DNSSEC-06 | DS key_tag mismatch → `service_detail=ds-chain-broken`; matching key_tag → no chain finding | unit | `pytest tests/test_dnssec_scanner.py::test_ds_chain_broken -x` | ❌ Wave 0 |
| DNSSEC-07 | `docker compose --profile dnssec up` starts BIND9; scanner validates against `weak.chaos.local` (CRITICAL), `safe.chaos.local` (clean), `unsigned.chaos.local` (HIGH) | integration (Docker) | manual / `pytest tests/test_dnssec_scanner.py::test_chaos_lab -x -m integration` | ❌ Wave 0 |

**Note on DNSSEC-07:** The chaos lab test requires Docker running and the `dnssec` profile started. Mark it with `@pytest.mark.integration` and skip if `QUIRK_INTEGRATION_TESTS` env var is not set, consistent with other integration tests in the project.

### Mocking Strategy for Unit Tests

Follow `test_jwt_scanner.py` pattern: mock the dnspython query functions rather than making real DNS calls.

```python
# Pattern: mock dns.query.udp_with_fallback return value
from unittest.mock import patch, MagicMock
import dns.message
import dns.rdatatype

with patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback") as mock_udp:
    # Build a fake response with DNSKEY rrset
    mock_response = MagicMock()
    mock_udp.return_value = (mock_response, False)
    # ... test assertions
```

### Sampling Rate
- **Per task commit:** `pytest tests/test_dnssec_scanner.py -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green (238 + new tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dnssec_scanner.py` — covers all 7 requirements (RED scaffold for Plan 01)
- [ ] `quirk/scanner/dnssec_scanner.py` — stub with `DNSPYTHON_AVAILABLE` guard (Plan 02 implements)

---

## Project Constraints (from CLAUDE.md)

- PEP 8 for all Python changes.
- Keep diffs minimal — avoid unnecessary refactors.
- After changes, run `python -m compileall` and relevant tests.
- Detection logic change: update `labs/*/expected_results.md` accordingly (the chaos lab has `expected_results_v3.md`; Phase 18 should update or create a DNSSEC section).
- Obsidian vault sync and UAT-SERIES.md update are required at phase end (mandatory completion steps in CLAUDE.md).

---

## Sources

### Primary (HIGH confidence)
- github.com/rthalley/dnspython issue #621 — confirmed `dns.query.udp_with_fallback()` + `want_dnssec=True` pattern for DNSKEY queries
- github.com/rthalley/dnspython blob/main/dns/dnssec.py — DNSKEY rdata attributes (flags, protocol, algorithm, key), `key_id()` function
- Project codebase — `quirk/scanner/jwt_scanner.py`, `quirk/cbom/builder.py`, `quirk/cbom/classifier.py`, `quirk/models.py` (all read directly)
- `pyproject.toml` — `dnspython[dnssec]>=2.8.0` in `[identity]` extras group (confirmed installed)
- `pip index versions dnspython` — confirmed 2.8.0 is current available release

### Secondary (MEDIUM confidence)
- rfc-editor.org/rfc/rfc9905 — RFC 9905 "Deprecating SHA-1 in DNSSEC": RSASHA1 (alg 5) and RSASHA1-NSEC3-SHA1 (alg 7) are MUST NOT for signing
- datatracker.ietf.org/doc/html/rfc8624 — RFC 8624 base algorithm table: RSAMD5, DSA, ECC-GOST = MUST NOT; RSASHA256/512 = SHOULD/MAY
- bind9.readthedocs.io — BIND9 zone file format, named.conf structure, dnssec-keygen usage
- hub.docker.com/r/internetsystemsconsortium/bind9 — `internetsystemsconsortium/bind9:9.18` image, configuration path `/etc/bind/`

### Tertiary (LOW confidence)
- WebSearch results on BIND9 Docker DNSSEC examples — general structure confirmed by multiple sources but specific named.conf syntax for pre-signed zones should be verified during implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — dnspython 2.8.0 confirmed installable, already in pyproject.toml extras
- Architecture: HIGH — scanner pattern confirmed from existing jwt_scanner.py; dnspython API patterns confirmed from primary sources
- DNSSEC algorithm map: HIGH — RFC 8624 + RFC 9905 confirmed algorithm status
- BIND9 chaos lab structure: MEDIUM — named.conf pattern confirmed from multiple sources; exact pre-signed zone file syntax requires BIND9 tools to generate (run inside container)
- Pitfalls: HIGH — NS/system-resolver trap and TC bit truncation confirmed from dnspython issue tracker

**Research date:** 2026-04-08
**Valid until:** 2026-07-08 (stable stack; RFC status unlikely to change; dnspython API stable)
