import ipaddress
import itertools
from typing import Iterator, List, Optional, Tuple

# Phase 71 / D-01 / WR-14 (relaxed Phase 144 / D-01/D-02/D-05): this constant
# was originally a hard per-CIDR reject ceiling for expand_targets() — a
# misconfigured /8 (16M addresses) would burn memory before any failure
# surfaced. Phase 144 removes that reject behavior entirely (no total-range
# ceiling — see CONTEXT.md D-02) and repurposes this same constant, value
# unchanged, as the per-batch CHUNK SIZE the nmap discovery batch loop
# (run_scan.py, Plan 144-02) consumes via `_chunked()` below.
_MAX_HOSTS_PER_CIDR = 1024  # /22 in IPv4 — now a chunk size, not a reject cap


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

    # Phase 141 OTICS-01/D-04: inject 502 (Modbus/TCP) into the candidate
    # port list when --enable-modbus is set, so hardware_scanner.py Step 4's
    # port-502 open-port gate has an endpoint to actually check. This mirrors
    # the equivalent injection in run_scan.py's nmap-discovery path — that
    # injection only affects the optional nmap pre-scan; expand_targets() is
    # the port list used whenever nmap discovery is skipped (the default),
    # so without this, Modbus fingerprinting never activates in that mode.
    ports = list(cfg.scan.ports_tls)
    if getattr(getattr(cfg, "connectors", None), "enable_modbus", False) and 502 not in ports:
        ports.append(502)

    # FQDNs
    for fqdn in (cfg.targets.fqdns or []):
        for p in ports:
            targets.append((fqdn, p))

    # IPs from CIDRs. Phase 144 / D-05: the reject-on-oversized-CIDR check
    # that used to live here has been removed — expand_targets() now expands
    # any CIDR size without a ceiling. No batch-loop machinery is added here:
    # this builtin path has no subprocess and no wall-clock timeout, so it has
    # no "one bad batch kills the job" failure mode to fix (D-05) — only the
    # reject needed removing, in lockstep with the nmap-discovery path (D-02).
    for cidr in (cfg.targets.cidrs or []):
        net = ipaddress.ip_network(cidr, strict=False)
        for ip in net.hosts():
            ip_str = _norm_ip(ip)
            if ip_str in exclude_set:
                continue
            for p in ports:
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
        for p in ports:
            targets.append((ip_str, p))

    # Stable dedup — preserve first-seen order (D-14). dict.fromkeys()
    # relies on Python 3.7+ guaranteed insertion-order semantics. Do NOT
    # swap in a set-then-list pattern; that loses order and produces
    # report drift across runs.
    return list(dict.fromkeys(targets))


def _chunked(iterable, size: int) -> Iterator[List]:
    """Yield successive `size`-length lists from `iterable` (Phase 144 / D-01
    / D-03). The final list may be shorter than `size`. Empty iterables yield
    nothing.

    Deliberately hand-rolled via `itertools.islice` rather than
    `itertools.batched` — the project floor is Python 3.11 per CLAUDE.md and
    `batched` is 3.12+ (RESEARCH Assumption A3).
    """
    it = iter(iterable)
    while True:
        batch = list(itertools.islice(it, size))
        if not batch:
            return
        yield batch


def _expand_and_dedup_hosts(
    tokens: List[str], exclude_ips: Optional[List[str]] = None
) -> Iterator[str]:
    """Lazily yield unique host strings (first-seen order) from raw
    CIDR/FQDN/IP tokens (Phase 144 / D-06).

    Mirrors expand_targets()'s CIDR-expansion loop MINUS the removed
    cap-check `raise` — but never materializes a full `.hosts()` list, since
    D-02 removes the total-range ceiling entirely (a /8 is ~16.7M hosts).
    Output is a flat sequence of host STRINGS, never (host, port) tuples.
    """
    exclude_set = set()
    for x in (exclude_ips or []):
        try:
            exclude_set.add(_norm_ip(x))
        except ValueError:
            # Preserve original string for non-IP entries (e.g. hostnames the
            # caller may have stuffed into exclude_ips) — mirrors
            # expand_targets()'s exclude-set normalization (lines 26-36).
            exclude_set.add(str(x))

    seen: set = set()

    for token in tokens:
        try:
            net = ipaddress.ip_network(token, strict=False)
        except ValueError:
            net = None

        if net is not None and net.num_addresses > 1:
            # CIDR — expand lazily, never fully materialize net.hosts() into
            # a list (Pitfall 4 / T-144-01: the seen-set memory growth for
            # very large ranges is the accepted DoS tradeoff the user
            # locked; no size ceiling).
            for ip in net.hosts():
                ip_str = _norm_ip(ip)
                if ip_str in exclude_set or ip_str in seen:
                    continue
                seen.add(ip_str)
                yield ip_str
        else:
            # Single host — FQDN or bare IP, passed through unchanged.
            try:
                host_str = _norm_ip(token)
            except ValueError:
                host_str = str(token)
            if host_str in exclude_set or host_str in seen:
                continue
            seen.add(host_str)
            yield host_str
