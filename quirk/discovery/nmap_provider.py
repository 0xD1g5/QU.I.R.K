from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from typing import List, Optional

from quirk.logging_util import Logger
from quirk.discovery.nmap_parser import parse_nmap_xml, NmapOpenPort


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

    ports_csv = ",".join(str(p) for p in sorted(set(ports))) if ports else "22,80,443,8443,9443,10443,5001"

    args = [nmap_path] + _default_nmap_args(ports_csv)

    if extra_args:
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

