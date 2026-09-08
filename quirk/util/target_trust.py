"""Phase 143 / TAIL-02: server-enforced trusted-targets scan-consent allowlist.

Single chokepoint (D-04) for both scan entry points — the CLI (``run_scan.py::main``)
and the dashboard (``quirk/dashboard/api/routes/jobs.py::create_job``). Neither entry
point re-implements matching; both call ``is_target_trusted`` / ``enforce_trusted_targets``
from this module.

Matching (D-06): exact host/IP string membership, or CIDR containment for entries that
contain a "/". No wildcard-subdomain matching. An empty ``trusted_targets`` list means
allow-all (D-03) — backward compatible with every existing scan config.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Final

RC_NOT_IN_ALLOWLIST: Final[str] = "not_in_trusted_targets"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str
    redacted_preview: str


def is_target_trusted(host_or_ip: str, trusted_targets: list) -> ValidationResult:
    """D-03: empty trusted_targets means allow-all (backward compatible).
    D-06: exact host/IP match OR CIDR containment — no wildcard subdomains.
    """
    if not trusted_targets:
        return ValidationResult(True, "", "")

    if host_or_ip in trusted_targets:
        return ValidationResult(True, "", "")

    try:
        candidate_ip = ipaddress.ip_address(host_or_ip)
    except ValueError:
        try:
            results = socket.getaddrinfo(host_or_ip, None, family=socket.AF_UNSPEC)
            candidate_ips = [ipaddress.ip_address(r[4][0]) for r in results if r[4]]
        except (socket.gaierror, OSError, UnicodeError, ValueError):
            return ValidationResult(False, RC_NOT_IN_ALLOWLIST, host_or_ip[:32])
    else:
        candidate_ips = [candidate_ip]

    for entry in trusted_targets:
        if "/" not in entry:
            continue
        try:
            network = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            continue
        if any(ip in network for ip in candidate_ips):
            return ValidationResult(True, "", "")

    return ValidationResult(False, RC_NOT_IN_ALLOWLIST, host_or_ip[:32])


def _broker_target_hosts(cfg) -> list:
    """Phase 190 / T-190-01: extract the HOST component of every
    connectors.broker_targets entry, tolerant of malformed entries (config
    load-time validation in quirk/config.py already rejects those before this
    is ever called; this stays defensive rather than importing quirk.config's
    _parse_host_port, to avoid a circular import — quirk/config.py does not
    import this module, but keeping this module dependency-free of quirk.config
    keeps the import direction simple and one-way).
    """
    connectors = getattr(cfg, "connectors", None)
    raw_targets = list(getattr(connectors, "broker_targets", None) or [])
    hosts = []
    for entry in raw_targets:
        if not isinstance(entry, str):
            continue
        candidate = entry.strip()
        if not candidate:
            continue
        if candidate.startswith("["):
            rbracket_idx = candidate.find("]")
            host = candidate[1:rbracket_idx].strip() if rbracket_idx != -1 else candidate
        elif candidate.count(":") == 1:
            host = candidate.split(":", 1)[0].strip()
        else:
            # Bare hostname, or a bare (unbracketed) IPv6 literal with no
            # port — either way the whole string is the host.
            host = candidate
        if host:
            hosts.append(host)
    return hosts


def enforce_trusted_targets(cfg) -> None:
    """Single chokepoint (D-04) — raise ValueError on the first untrusted target.
    Called from BOTH run_scan.py::main and jobs.py::create_job.
    """
    trusted = list(getattr(cfg.security, "trusted_targets", None) or [])
    if not trusted:
        return  # D-03: allow-all when empty
    all_targets = (
        list(cfg.targets.fqdns or [])
        + list(cfg.targets.cidrs or [])
        + _broker_target_hosts(cfg)
    )
    for target in all_targets:
        result = is_target_trusted(target, trusted)
        if not result.ok:
            raise ValueError(
                f"Target {result.redacted_preview!r} is not in the trusted-targets "
                f"allowlist (security.trusted_targets in config.yaml)."
            )
