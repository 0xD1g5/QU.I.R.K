"""DNSSEC scanner module — queries DNSKEY/DS records and classifies algorithms per RFC 8624/9905."""

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
    10: ("RSASHA512",           "HIGH"),
    12: ("ECC-GOST",            "CRITICAL"),
    13: ("ECDSAP256SHA256",     "SAFE"),
    14: ("ECDSAP384SHA384",     "SAFE"),
    15: ("ED25519",             "SAFE"),
    16: ("ED448",               "SAFE"),
}


def scan_dnssec_targets(targets: list, timeout: int = 10, logger=None) -> list:
    """Scan DNSSEC posture for a list of domain targets.

    Returns list of CryptoEndpoint objects — one per DNSKEY record found, plus
    additional entries for unsigned zones, NSEC exposure, and DS chain breaks.

    Degrades gracefully if dnspython is not installed (returns empty list).
    """
    if not DNSPYTHON_AVAILABLE:
        return []
    raise NotImplementedError("Plan 02 implements")


def _resolve_ns(domain: str, timeout: int) -> list:
    """Resolve authoritative nameserver IPs for a domain.

    Returns list of NS IP strings.
    """
    raise NotImplementedError("Plan 02 implements")


def _query_rrset(domain: str, rdtype, ns_ip: str, timeout: int):
    """Query a specific RR type from a nameserver.

    Returns the DNS response message, or None on failure.
    """
    raise NotImplementedError("Plan 02 implements")


def _parse_dnskeys(dnskey_rrset) -> list:
    """Parse DNSKEY rrset into a list of dicts with flags, algorithm, key_tag, key_size, role.

    Each dict: {flags, algorithm, alg_name, key_tag, key_size, role}
    """
    raise NotImplementedError("Plan 02 implements")


def _parse_ds_records(ds_rrset) -> list:
    """Parse DS rrset into a list of dicts with key_tag, algorithm, digest_type.

    Each dict: {key_tag, algorithm, digest_type}
    """
    raise NotImplementedError("Plan 02 implements")


def _check_chain(dnskeys: list, ds_records: list) -> bool:
    """Check whether any DS record matches a DNSKEY by key_tag.

    Returns True if chain is valid (at least one matching key_tag found).
    Returns False if chain is broken (no DS matches any DNSKEY).
    """
    raise NotImplementedError("Plan 02 implements")


def _detect_nsec_type(domain: str, ns_ip: str, timeout: int):
    """Detect NSEC vs NSEC3 by sending NXDOMAIN query and inspecting authority section.

    Returns "nsec", "nsec3", or None if neither found.
    """
    raise NotImplementedError("Plan 02 implements")


def _scan_domain(domain: str, timeout: int, logger) -> list:
    """Scan a single domain for DNSSEC posture.

    Returns list of CryptoEndpoint objects for this domain.
    """
    raise NotImplementedError("Plan 02 implements")
