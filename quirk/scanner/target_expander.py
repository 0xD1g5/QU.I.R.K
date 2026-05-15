import ipaddress
from typing import List, Tuple

# Phase 71 / D-01 / WR-14: per-CIDR host-count cap. A misconfigured /8
# (16M addresses) would burn memory before any failure surfaced — fail
# loud BEFORE iterating .hosts(). Cap is num_addresses > 1024 (/22 IPv4).
_MAX_HOSTS_PER_CIDR = 1024  # /22 in IPv4


def _norm_ip(x) -> str:
    """Normalize an IP entry (str or ipaddress.IPv4/IPv6Address) to its
    canonical str form so membership comparisons work regardless of the
    caller's input type (Phase 71 / D-14 / WR-14).
    """
    return str(ipaddress.ip_address(x))


def expand_targets(cfg) -> List[Tuple[str, int]]:
    targets: List[Tuple[str, int]] = []

    # Build normalized include/exclude sets up front (D-14 type-confusion fix):
    # both `cfg.targets.exclude_ips` and `cfg.targets.include_ips` may contain
    # raw strings OR ipaddress.IPv4Address instances depending on caller.
    exclude_set = set()
    for x in (cfg.targets.exclude_ips or []):
        try:
            exclude_set.add(_norm_ip(x))
        except ValueError:
            # Preserve original string for non-IP entries (e.g. hostnames the
            # caller may have stuffed into exclude_ips).
            exclude_set.add(str(x))

    # FQDNs
    for fqdn in (cfg.targets.fqdns or []):
        for p in cfg.scan.ports_tls:
            targets.append((fqdn, p))

    # IPs from CIDRs — validate size BEFORE enumeration (D-01).
    for cidr in (cfg.targets.cidrs or []):
        net = ipaddress.ip_network(cidr, strict=False)
        if net.num_addresses > _MAX_HOSTS_PER_CIDR:
            raise ValueError(
                f"CIDR {cidr} expands to {net.num_addresses} hosts; "
                f"refusing to scan more than {_MAX_HOSTS_PER_CIDR} hosts per CIDR "
                f"(split it or use --include-ips)"
            )
        for ip in net.hosts():
            ip_str = _norm_ip(ip)
            if ip_str in exclude_set:
                continue
            for p in cfg.scan.ports_tls:
                targets.append((ip_str, p))

    # Explicit IPs — normalize each entry so exclude filters match
    # regardless of caller input type (str vs IPv4Address).
    for ip in (cfg.targets.include_ips or []):
        try:
            ip_str = _norm_ip(ip)
        except ValueError:
            # Caller passed something non-IP (hostname-like); leave untouched.
            ip_str = str(ip)
        if ip_str in exclude_set:
            continue
        for p in cfg.scan.ports_tls:
            targets.append((ip_str, p))

    # Stable dedup — preserve first-seen order (D-14). dict.fromkeys()
    # relies on Python 3.7+ guaranteed insertion-order semantics. Do NOT
    # swap in a set-then-list pattern; that loses order and produces
    # report drift across runs.
    return list(dict.fromkeys(targets))
