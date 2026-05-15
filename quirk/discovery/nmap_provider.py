from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from quirk.logging_util import Logger
from quirk.discovery.nmap_parser import parse_nmap_xml, NmapOpenPort

# D-04 / WR-05 — defense-in-depth allowlist for nmap extra_args tokens.
# Mirrors the Phase 70 `_SAFE_COL_TYPE_RE` pattern (quirk/db.py:34).
_SAFE_NMAP_ARG_RE = re.compile(r"^[A-Za-z0-9._:/=,-]+$")

# D-03 / WR-04 — fixed consulting-grade port set (SSH, HTTP, motion email,
# Kerberos, LDAP/LDAPS, RDP, AMQPS, Kafka). The dynamic TLS half comes from
# `cfg.scan.ports_tls`; see `default_nmap_ports_csv` below.
_FIXED_NMAP_PORTS: tuple = (
    22, 25, 80, 88, 389, 465, 587, 636, 993, 995, 3389, 5671, 8080, 9092,
)


def default_nmap_ports_csv(ports_tls: Iterable[int]) -> str:
    """
    Compose the consulting-grade default nmap port CSV (D-03 / WR-04).

    Union of `cfg.scan.ports_tls` (so the default tracks TLS port changes)
    and the fixed protocol set in `_FIXED_NMAP_PORTS`. Sorted, deduped.
    """
    ports = sorted(set(int(p) for p in ports_tls) | set(_FIXED_NMAP_PORTS))
    return ",".join(str(p) for p in ports)


def _default_nmap_args(ports_csv: str) -> List[str]:
    """
    Defaults chosen to be:
    - Non-admin friendly: -sT (TCP connect scan)
    - No DNS: -n
    - Treat hosts as up: -Pn (works better in segmented environments)
    - Only show open ports: --open
    - Conservative retry/timeouts to keep scans fast
    """
    return [
        "-sT",
        "-n",
        "-Pn",
        "--open",
        "-p", ports_csv,
        "--max-retries", "1",
        "--host-timeout", "10s",
        "--max-parallelism", "100",  # D-07: hard-coded; not configurable in Phase 47.
    ]


def run_nmap_discovery(
    targets: List[str],
    ports: List[int],
    output_dir: str,
    logger: Optional[Logger] = None,
    nmap_path: str = "nmap",
    extra_args: Optional[List[str]] = None,
    timeout_seconds: int = 1800,
) -> List[NmapOpenPort]:
    """
    Run nmap discovery scan and parse XML output for open ports.

    Returns a list of NmapOpenPort items.
    """
    if not targets:
        return []

    os.makedirs(output_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    xml_path = os.path.join(output_dir, f"nmap-discovery-{stamp}.xml")

    # D-03 / WR-04 — when caller passes no explicit port list, fall back to
    # the consulting-grade union (cfg.scan.ports_tls + fixed protocol set).
    # The default here hardcodes the canonical TLS list (Phase 47 consulting
    # set: 443, 8443, 9443, 10443, 5001) since this fallback runs without a
    # cfg handle; callers with a cfg should pass `ports` explicitly.
    if ports:
        ports_csv = ",".join(str(p) for p in sorted(set(ports)))
    else:
        ports_csv = default_nmap_ports_csv((443, 8443, 9443, 10443, 5001))

    args = [nmap_path] + _default_nmap_args(ports_csv)

    if extra_args:
        # D-04 / WR-05 — validate every extra_args token against the allowlist
        # BEFORE subprocess. Mirrors `_SAFE_COL_TYPE_RE` defense-in-depth
        # pattern from Phase 70. Reject loudly — no quoting / escaping.
        for token in extra_args:
            # Use fullmatch (not match) so the trailing `$` cannot match before
            # a final `\n` — a token like "foo\n-O" would otherwise slip the
            # allowlist (re audit WR-1, Phase 71 review).
            if not _SAFE_NMAP_ARG_RE.fullmatch(token):
                raise ValueError(f"Unsafe nmap extra arg: {token!r}")
        # allow user overrides like: ["-sS"] if running admin/root
        args.extend(extra_args)

    args.extend(["-oX", xml_path])
    args.extend(targets)

    if logger:
        logger.stamp(f"Running Nmap discovery on {len(targets)} target(s) (ports={ports_csv})")
        logger.v(f"🧾 Nmap cmd: {' '.join(args)}")

    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "Nmap not found. Install Nmap and ensure 'nmap' is in PATH, or pass --nmap-path."
        ) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"Nmap discovery timed out after {timeout_seconds}s. Consider reducing scope or increasing --nmap-timeout."
        ) from e

    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"Nmap discovery failed (exit {proc.returncode}). Output:\n{msg}")

    if logger:
        logger.stamp(f"Nmap discovery complete. Parsing XML: {xml_path}")

    open_ports = parse_nmap_xml(xml_path)

    if logger:
        logger.stamp(f"Nmap discovered {len(open_ports)} open port(s).")

    return open_ports

