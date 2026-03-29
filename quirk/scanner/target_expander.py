import ipaddress
from typing import List, Tuple

def expand_targets(cfg) -> List[Tuple[str, int]]:
    targets: List[Tuple[str, int]] = []

    # FQDNs
    for fqdn in cfg.targets.fqdns:
        for p in cfg.scan.ports_tls:
            targets.append((fqdn, p))

    # IPs from CIDRs
    exclude = set(cfg.targets.exclude_ips or [])
    for cidr in cfg.targets.cidrs:
        net = ipaddress.ip_network(cidr, strict=False)
        for ip in net.hosts():
            ip_str = str(ip)
            if ip_str in exclude:
                continue
            for p in cfg.scan.ports_tls:
                targets.append((ip_str, p))

    # Explicit IPs
    for ip in cfg.targets.include_ips:
        if ip in exclude:
            continue
        for p in cfg.scan.ports_tls:
            targets.append((ip, p))

    return targets
