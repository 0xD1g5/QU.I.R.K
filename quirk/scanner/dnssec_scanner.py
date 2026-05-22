"""DNSSEC scanner module — queries DNSKEY/DS records and classifies algorithms per RFC 8624/9905."""

import json
import logging
from datetime import datetime, timezone

try:
    import dns.message
    import dns.query
    import dns.rdatatype
    import dns.resolver
    import dns.dnssec
    import dns.flags
    DNSPYTHON_AVAILABLE = True
except ImportError:
    DNSPYTHON_AVAILABLE = False

from quirk.models import CryptoEndpoint

# Module-level logger (Phase 71 WR-07)
logger = logging.getLogger(__name__)

# DNSKEY algorithm minimum public-key byte lengths per RFC 4034/6605/8080 (Phase 71 WR-07 / D-11).
# RSA family (5, 7, 8, 10) require at least the encoding header (exp-len byte + 1-byte exp + 1 modulus byte) = 3
# practical floor 5 to guard against truncation in the multi-byte exp-len form.
# Fixed-size algorithms come straight from their RFCs.
_DNSKEY_MIN_BYTES: dict = {
    1:  5,    # RSAMD5 (RFC 4034 §2.1.5 — same RFC 3110 encoding floor as RSA-SHA1)
    5:  5,    # RSASHA1
    7:  5,    # RSASHA1-NSEC3-SHA1
    8:  5,    # RSASHA256
    10: 5,    # RSASHA512
    13: 64,   # ECDSA P-256 / SHA-256 (RFC 6605 §4 — uncompressed X||Y, 32+32 bytes)
    14: 96,   # ECDSA P-384 / SHA-384 (RFC 6605 §4 — uncompressed X||Y, 48+48 bytes)
    15: 32,   # Ed25519 (RFC 8080 §3)
    16: 57,   # Ed448   (RFC 8080 §3)
}

# DNSSEC algorithm severity map per RFC 8624/9905 (D-04)
# Maps algorithm number -> (name, severity)
# CRITICAL: SHA-1 / MD5 / DSA / GOST based algorithms
# HIGH: RSA-only algorithms (quantum-vulnerable)
# SAFE: ECDSA / EdDSA algorithms
DNSSEC_ALG_MAP: dict = {
    1:  ("RSAMD5",              "CRITICAL"),
    3:  ("DSA",                 "CRITICAL"),
    5:  ("RSASHA1",             "CRITICAL"),
    6:  ("DSA-NSEC3-SHA1",      "CRITICAL"),
    7:  ("RSASHA1-NSEC3-SHA1",  "CRITICAL"),
    8:  ("RSASHA256",           "HIGH"),
    9:  ("Reserved",            "HIGH"),       # IANA Reserved per RFC 8624 — closes scanners-protocol/IN-02 (Phase 77 D-02)
    10: ("RSASHA512",           "HIGH"),
    11: ("Reserved",            "HIGH"),       # IANA Reserved per RFC 8624
    12: ("ECC-GOST",            "CRITICAL"),
    13: ("ECDSAP256SHA256",     "SAFE"),
    14: ("ECDSAP384SHA384",     "SAFE"),
    15: ("ED25519",             "SAFE"),
    16: ("ED448",               "SAFE"),
}


def _parse_resolver(resolver: str):
    """Parse a ``host:port`` resolver string into a ``(host, port)`` tuple.

    Returns ``(host, 53)`` if *resolver* is ``None`` or empty, and
    ``(host, int(port))`` otherwise.  Supports IPv4 addresses and plain
    hostnames only (no IPv6 bracket notation required for lab use).
    """
    if not resolver:
        return None, 53
    if ":" in resolver:
        host, port_str = resolver.rsplit(":", 1)
        try:
            return host, int(port_str)
        except ValueError:
            return resolver, 53
    return resolver, 53


def _resolve_ns(domain: str, timeout: int, resolver: str = None) -> list:
    """Resolve authoritative nameserver IPs for a domain.

    When *resolver* is set (``host:port`` string), queries that specific
    resolver directly instead of the system resolver — required for lab
    bind9 instances that listen on a non-standard port (e.g. 15353).

    Returns list of NS IP strings.  Returns [] on any failure.
    """
    resolver_host, resolver_port = _parse_resolver(resolver)
    try:
        if resolver_host:
            # Query the custom resolver directly for NS records
            request = dns.message.make_query(domain, dns.rdatatype.NS)
            result = dns.query.udp_with_fallback(
                request, resolver_host, port=resolver_port, timeout=timeout,
            )
            if isinstance(result, tuple):
                result = result[0]
            ns_names = []
            for rrset in result.answer:
                if rrset.rdtype == dns.rdatatype.NS:
                    for rdata in rrset:
                        ns_names.append(str(rdata.target))
            # Resolve each NS name via the same custom resolver
            ips = []
            for ns_name in ns_names:
                try:
                    a_request = dns.message.make_query(ns_name, dns.rdatatype.A)
                    a_result = dns.query.udp_with_fallback(
                        a_request, resolver_host, port=resolver_port, timeout=timeout,
                    )
                    if isinstance(a_result, tuple):
                        a_result = a_result[0]
                    for rrset in a_result.answer:
                        if rrset.rdtype == dns.rdatatype.A:
                            for a_rdata in rrset:
                                ips.append(a_rdata.address)
                except Exception:
                    pass
            # Fall back to using the resolver host itself as the NS IP
            # if no A records were found — lab bind9 is authoritative for
            # the zone, so direct queries to it work even without A glue.
            if not ips and resolver_host:
                ips = [resolver_host]
            return ips
        else:
            ns_answer = dns.resolver.resolve(domain, "NS", lifetime=timeout)
            ips = []
            for rdata in ns_answer:
                ns_name = str(rdata.target)
                try:
                    a_answer = dns.resolver.resolve(ns_name, "A", lifetime=timeout)
                    for a_rdata in a_answer:
                        ips.append(a_rdata.address)
                except Exception:
                    pass
            return ips
    except Exception:
        return []


def _query_rrset(domain: str, rdtype, ns_ip: str, timeout: int, ns_port: int = 53):
    """Query a specific RR type from an authoritative nameserver.

    Creates a query with DO bit (want_dnssec=True) and clears RD flag so
    authoritative servers respond without recursion refusal.

    *ns_port* defaults to 53 but can be overridden for lab resolvers on
    non-standard ports (e.g. bind9-dnssec on 15353).

    Returns the DNS response message, or None on failure.
    """
    try:
        request = dns.message.make_query(domain, rdtype, want_dnssec=True)
        request.flags &= ~dns.flags.RD
        result = dns.query.udp_with_fallback(
            request, ns_ip, port=ns_port, timeout=timeout,
        )
        # Real dnspython returns (response, used_tcp) tuple; mocks may return response directly
        if isinstance(result, tuple):
            return result[0]
        return result
    except Exception:
        return None


def _parse_dnskeys(dnskey_rrset) -> list:
    """Parse DNSKEY rrset into a list of dicts with flags, alg, tag, key_size, role.

    Each dict: {"flags": int, "alg": int, "tag": int, "key_size": int|None, "role": str}
    """
    keys = []
    for rdata in dnskey_rrset:
        alg_num = int(rdata.algorithm)
        key_tag = dns.dnssec.key_id(rdata)
        role = "KSK" if (rdata.flags & 0x0001) else "ZSK"

        # Phase 71 WR-07 (D-11): bound key_bytes length against the algorithm-specific
        # minimum BEFORE any subscript access. Malformed/truncated records log a WARNING
        # and are skipped so DNSSEC scans degrade gracefully rather than aborting.
        key_bytes = rdata.key
        min_len = _DNSKEY_MIN_BYTES.get(alg_num, 1)
        if len(key_bytes) < min_len:
            logger.warning(
                "DNSKEY (alg %d) too short: %d bytes < %d; skipping",
                alg_num, len(key_bytes), min_len,
            )
            continue

        # RSA algorithms: parse RFC 3110 format to extract modulus length
        key_size = None
        if alg_num in (1, 5, 7, 8, 10):
            try:
                if key_bytes[0] == 0:
                    if len(key_bytes) < 3:
                        raise ValueError("RSA multi-byte exponent length header truncated")
                    exp_len = (key_bytes[1] << 8) | key_bytes[2]
                    modulus_start = 3 + exp_len
                else:
                    exp_len = key_bytes[0]
                    modulus_start = 1 + exp_len
                if modulus_start >= len(key_bytes):
                    raise ValueError("RSA modulus offset past key_bytes end")
                key_size = (len(key_bytes) - modulus_start) * 8
            except Exception as exc:
                logger.warning(
                    "DNSKEY RSA (alg %d) modulus parse failed: %s",
                    alg_num, exc,
                )
                key_size = None

        keys.append({
            "flags": int(rdata.flags),
            "alg": alg_num,
            "tag": key_tag,
            "key_size": key_size,
            "role": role,
        })
    return keys


def _parse_ds_records(ds_rrset) -> list:
    """Parse DS rrset into a list of dicts with key_tag, algorithm, digest_type.

    Each dict: {"key_tag": int, "algorithm": int, "digest_type": int}
    """
    return [
        {
            "key_tag": rdata.key_tag,
            "algorithm": int(rdata.algorithm),
            "digest_type": rdata.digest_type,
        }
        for rdata in ds_rrset
    ]


def _check_chain(dnskeys: list, ds_records: list) -> bool:
    """Check whether any DS record matches a DNSKEY by key_tag.

    Returns True if chain is valid (at least one matching key_tag found).
    Returns False if chain is broken (no DS matches any DNSKEY).
    """
    dnskey_tags = {d["tag"] for d in dnskeys}
    ds_tags = {ds["key_tag"] for ds in ds_records}
    return bool(dnskey_tags & ds_tags)


def _detect_nsec_type(domain: str, ns_ip: str, timeout: int, ns_port: int = 53):
    """Detect NSEC vs NSEC3 by sending NXDOMAIN probe query and inspecting authority section.

    Returns "NSEC", "NSEC3", or None if neither found.
    """
    try:
        probe_domain = f"_quirk_probe_.{domain}"
        response = _query_rrset(probe_domain, dns.rdatatype.A, ns_ip, timeout, ns_port=ns_port)
        if response is None:
            return None
        for rrset in response.authority:
            if rrset.rdtype == dns.rdatatype.NSEC:   # 47
                return "NSEC"
            if rrset.rdtype == dns.rdatatype.NSEC3:  # 50
                return "NSEC3"
        return None
    except Exception:
        return None


def _scan_domain(domain: str, timeout: int, logger, session_start=None, resolver: str = None) -> list:
    """Scan a single domain for DNSSEC posture.

    *resolver* is an optional ``host:port`` string.  When set, all DNS
    queries (NS resolution + RR queries) are sent to that specific resolver
    instead of the system resolver.  Required for lab bind9 instances on
    non-standard ports (e.g. 127.0.0.1:15353).

    Returns list of CryptoEndpoint objects for this domain.
    """
    resolver_host, resolver_port = _parse_resolver(resolver)
    ns_ips = _resolve_ns(domain, timeout, resolver=resolver)
    if not ns_ips:
        if logger:
            logger.warning("DNSSEC: could not resolve NS for %s", domain)
        return []

    ns_ip = ns_ips[0]

    # Query DNSKEY (use resolver_port when a custom resolver is configured)
    dnskey_response = _query_rrset(domain, dns.rdatatype.DNSKEY, ns_ip, timeout, ns_port=resolver_port)

    # Find DNSKEY rrset in answer section
    dnskey_rrset = None
    if dnskey_response:
        for rrset in dnskey_response.answer:
            if rrset.rdtype == dns.rdatatype.DNSKEY:
                dnskey_rrset = rrset
                break

    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)

    # Unsigned zone — no DNSKEY
    if dnskey_rrset is None:
        scan_dict = {
            "domain": domain,
            "ns_queried": ns_ip,
            "signed": False,
            "dnskeys": [],
            "ds_records": [],
            "nsec_type": None,
            "chain_valid": None,
        }
        return [CryptoEndpoint(
            host=domain,
            port=resolver_port,
            protocol="DNSSEC",
            cert_pubkey_alg="NONE",
            cert_pubkey_size=None,
            dnssec_scan_json=json.dumps(scan_dict),
            service_detail="unsigned-zone",
            scanned_at=now,
        )]

    # Signed zone — parse keys
    dnskeys = _parse_dnskeys(dnskey_rrset)

    # Detect NSEC type
    nsec_type = _detect_nsec_type(domain, ns_ip, timeout, ns_port=resolver_port)

    # Query DS records — may be in the same response or separate
    ds_records = []
    if dnskey_response:
        for rrset in dnskey_response.answer:
            if rrset.rdtype == dns.rdatatype.DS:
                ds_records = _parse_ds_records(rrset)
                break

    if not ds_records:
        ds_response = _query_rrset(domain, dns.rdatatype.DS, ns_ip, timeout, ns_port=resolver_port)
        if ds_response:
            for rrset in ds_response.answer:
                if rrset.rdtype == dns.rdatatype.DS:
                    ds_records = _parse_ds_records(rrset)
                    break

    chain_valid = _check_chain(dnskeys, ds_records) if ds_records else None

    scan_dict = {
        "domain": domain,
        "ns_queried": ns_ip,
        "signed": True,
        "dnskeys": dnskeys,
        "ds_records": ds_records,
        "nsec_type": nsec_type,
        "chain_valid": chain_valid,
    }

    endpoints = []

    # One CryptoEndpoint per DNSKEY
    for key in dnskeys:
        alg_name, _severity = DNSSEC_ALG_MAP.get(key["alg"], (f"UNKNOWN-{key['alg']}", "HIGH"))
        endpoints.append(CryptoEndpoint(
            host=domain,
            port=resolver_port,
            protocol="DNSSEC",
            cert_pubkey_alg=alg_name,
            cert_pubkey_size=key["key_size"],
            service_detail=f"dnskey:tag={key['tag']}:role={key['role']}",
            dnssec_scan_json=json.dumps(scan_dict),
            scanned_at=now,
        ))

    # NSEC exposure finding
    if nsec_type == "NSEC":
        endpoints.append(CryptoEndpoint(
            host=domain,
            port=resolver_port,
            protocol="DNSSEC",
            cert_pubkey_alg="NSEC",
            cert_pubkey_size=None,
            service_detail="nsec-exposure",
            dnssec_scan_json=json.dumps(scan_dict),
            scanned_at=now,
        ))

    # DS chain broken finding
    if chain_valid is False:
        endpoints.append(CryptoEndpoint(
            host=domain,
            port=resolver_port,
            protocol="DNSSEC",
            cert_pubkey_alg="DS-MISMATCH",
            cert_pubkey_size=None,
            service_detail="ds-chain-broken",
            dnssec_scan_json=json.dumps(scan_dict),
            scanned_at=now,
        ))

    # DS SHA-1 digest finding
    for ds in ds_records:
        if ds["digest_type"] == 1:
            endpoints.append(CryptoEndpoint(
                host=domain,
                port=resolver_port,
                protocol="DNSSEC",
                cert_pubkey_alg="SHA1-DS",
                cert_pubkey_size=None,
                service_detail="sha1-ds-digest",
                dnssec_scan_json=json.dumps(scan_dict),
                scanned_at=now,
            ))

    return endpoints


def scan_dnssec_targets(
    targets: list,
    timeout: int = 10,
    logger=None,
    session_start=None,
    resolver: str = None,
) -> list:
    """Scan DNSSEC posture for a list of domain targets.

    *resolver* is an optional ``host:port`` string.  When set, all DNS
    queries bypass the system resolver and go directly to the specified
    host and port.  This is required for lab bind9 instances that listen
    on non-standard ports (e.g. ``127.0.0.1:15353``).

    Returns list of CryptoEndpoint objects — one per DNSKEY record found, plus
    additional entries for unsigned zones, NSEC exposure, and DS chain breaks.

    Degrades gracefully if dnspython is not installed (returns empty list).
    """
    if not DNSPYTHON_AVAILABLE:
        if logger:
            logger.warning("dnspython not installed — DNSSEC scanning disabled")
        return []

    results = []
    for domain in targets:
        try:
            results.extend(
                _scan_domain(domain, timeout, logger, session_start=session_start, resolver=resolver)
            )
        except Exception as exc:
            if logger:
                logger.warning("DNSSEC scan failed for %s: %s", domain, exc)
    return results
