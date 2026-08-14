#!/usr/bin/env python3
"""
Phase 152 / DISC-10 — chunked-vs-direct nmap discovery comparison.

Empirically settles the Phase 144 nmap adaptive RTT/timing-engine artifact
(an accepted VERIFICATION override from v5.11 — real open ports possibly
suppressed on a mostly-silent host batch) against the DISC-09
`segmented-network` chaos lab profile built in Plan 152-01.

Run INSIDE the lab network (macOS Docker Desktop cannot route host traffic
into custom bridge networks — see docs/chaos-lab.md 3.24):

    docker compose --profile segmented-network up -d
    docker compose exec segnet-prober python \
        /quirk/quantum-chaos-enterprise-lab/segmented-network/compare_discovery.py

Topology (see 152-01-SUMMARY.md "Deviations" for the exact routing fix):
  - segnet-live (10.70.0.0/24): segnet-live-tls (10.70.0.10:443),
    segnet-live-ssh (10.70.0.11:2222), segnet-prober (10.70.0.20).
  - segnet-dead (10.71.0.0/24): no containers — segnet-gateway (10.70.0.2 /
    10.71.0.2) REJECTs all FORWARD-chain traffic into this subnet with
    TCP RST / ICMP-host-unreachable.
  - segnet-prober is a member of segnet-live ONLY and reaches segnet-dead by
    routing through segnet-gateway's live-side IP (10.70.0.2) — it is NOT
    dual-homed on both subnets (that bypasses the gateway's FORWARD chain
    entirely; see 152-01-SUMMARY.md Deviation 1).

Strict reproduction definition (152-CONTEXT.md, quoted verbatim): "real open
ports on live hosts missed/suppressed by adaptive RTT/timing throttling
during chunked discovery, confirmed by diffing chunked-discovery output
against a direct nmap run of the same segment. Any other kind of missed port
does not count as reproduction." The diff below is restricted to
`segnet-live` hosts only (10.70.0.0/24) — dead-subnet non-findings are
expected/correct, never suppressions (152-CONTEXT.md Pitfall 4).
"""

from __future__ import annotations

import ipaddress
import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Set, Tuple

# Allow running this script directly (python compare_discovery.py) from
# inside the container without requiring `pip install -e .` — the image
# already installs the package in site-packages (sensor.Dockerfile), so this
# is a defensive fallback only, not the primary import path.
sys.path.insert(0, "/quirk")

from quirk.logging_util import Logger  # noqa: E402
from quirk.discovery.nmap_provider import (  # noqa: E402
    run_nmap_discovery,
    run_nmap_liveness_check,
    discovery_timing_template_for_batch,
    discovery_timeout_for_batch,
)

# --- DISC-09 lab topology (docker-compose.yml, PHASE 152 / DISC-09 block) ---

# segnet-live hosts (10.70.0.0/24) — the ONLY hosts eligible to count as a
# "reproduction candidate" in the diff below (152-CONTEXT.md strict
# definition: live-subnet-only).
SEGNET_LIVE_HOSTS: Tuple[str, ...] = ("10.70.0.10", "10.70.0.11")
SEGNET_LIVE_CIDR = "10.70.0.0/24"  # used only for the grep-visible filter marker below

# Representative dead range verified live in Plan 152-01 (63-address /26
# REJECT-rule sweep, 100% RST/closed, 0 filtered/silent — 10.71.0.2 the
# gateway's own dead-side IP is excluded below, see _build_target_list) —
# a scaled reproduction of the original ~1024-host batch, not a 1:1
# replica (152-CONTEXT.md).
SEGNET_DEAD_CIDR = "10.71.0.0/26"

# The gateway's own IP on segnet-dead. A probe to this address is handled by
# the container's own INPUT chain (ordinary "no listener" TCP RST), not the
# FORWARD-chain REJECT rule this lab exists to verify — so it must be
# excluded from the REJECT-rule sweep (WR-01, 152-REVIEW.md).
SEGNET_DEAD_GATEWAY_IP = "10.71.0.2"

# Real open ports on the live subnet (segnet-live-tls:443, segnet-live-ssh:2222).
PORTS: List[int] = [443, 2222]

RUNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")


def _build_target_list() -> List[str]:
    """Full target list: segnet-live static IPs + the segnet-dead /26 range."""
    gateway_dead_ip = ipaddress.ip_address(SEGNET_DEAD_GATEWAY_IP)
    dead_hosts = [
        str(ip)
        for ip in ipaddress.ip_network(SEGNET_DEAD_CIDR).hosts()
        if ip != gateway_dead_ip
    ]
    # `.hosts()` on a /26 excludes the network (.0) and broadcast (.63)
    # addresses (62 usable addresses), and the comprehension above further
    # excludes 10.71.0.2 (the gateway's own dead-side IP — WR-01), leaving
    # 61 addresses genuinely exercising the FORWARD-chain REJECT rule. The
    # live-fire transcript in expected_results_segmented_network.md swept
    # the raw /26 CIDR directly via nmap (64 addresses incl. .0/.63/.2) and
    # found 63/64 REJECT-verified (10.71.0.2 excluded as gateway-self) — see
    # that file's "Dead-Range Sweep" section for the exact count reasoning.
    return list(SEGNET_LIVE_HOSTS) + dead_hosts


def _is_segnet_live(host: str) -> bool:
    """
    Restrict the diff to `segnet-live` hosts only (152-CONTEXT.md Pitfall 4
    — dead-subnet non-findings are expected/correct, never suppressions).

    Applied BEFORE the diff runs (filter open-port sets first, diff second)
    — never applied as a post-hoc filter on an already-computed diff.
    """
    try:
        return ipaddress.ip_address(host) in ipaddress.ip_network(SEGNET_LIVE_CIDR)
    except ValueError:
        return False


def _run_chunked(targets: List[str], logger: Logger, output_dir: str) -> Set[Tuple[str, int]]:
    """
    Mirror run_scan.py's chunked discovery batch loop (run_scan.py:1464-1537)
    honestly: liveness pre-pass narrows the batch to responsive hosts, then
    the timing template/timeout selected by
    discovery_timing_template_for_batch()/discovery_timeout_for_batch() for
    THIS batch's size drives the real sweep — exactly as production does.
    Since the DISC-09 lab's ~66-host target list is far below
    `_MAX_HOSTS_PER_CIDR` (1024), it forms a single batch, matching how any
    real-world scan smaller than 1024 hosts already runs in production
    today (not an invented batch size — RESEARCH.md "Don't Hand-Roll").
    """
    batch = targets
    batch_timeout = discovery_timeout_for_batch(len(batch))
    batch_timing_template = discovery_timing_template_for_batch(len(batch))

    logger.stamp(
        f"[chunked] batch of {len(batch)} host(s): timing={batch_timing_template}, "
        f"timeout={batch_timeout}s"
    )

    statuses = run_nmap_liveness_check(
        targets=batch,
        ports=PORTS,
        output_dir=output_dir,
        logger=logger,
        timeout_seconds=batch_timeout,
    )
    down_hosts = {s.host for s in statuses if not s.up}
    sweep_targets = [h for h in batch if h not in down_hosts]
    logger.stamp(
        f"[chunked] liveness pre-pass: {len(sweep_targets)} responsive, "
        f"{len(down_hosts)} skipped"
    )

    if not sweep_targets:
        return set()

    open_ports = run_nmap_discovery(
        targets=sweep_targets,
        ports=PORTS,
        output_dir=output_dir,
        logger=logger,
        extra_args=[batch_timing_template],
        timeout_seconds=batch_timeout,
    )
    return {(p.host, p.port) for p in open_ports}


def _run_direct(targets: List[str], logger: Logger, output_dir: str) -> Set[Tuple[str, int]]:
    """
    Single non-chunked, non-timing-throttled run against the SAME full
    target list (live + dead) — no liveness pre-pass narrowing, no
    `-T4`/`-T3` template injected via `extra_args`, just nmap's own default
    timing (`-T3`, nmap's built-in default when no `-T` flag is passed).
    This is the "ground truth" side of the comparison.
    """
    logger.stamp(f"[direct] single sweep of {len(targets)} host(s), no timing template")
    open_ports = run_nmap_discovery(
        targets=targets,
        ports=PORTS,
        output_dir=output_dir,
        logger=logger,
        extra_args=None,
        timeout_seconds=1800,
    )
    return {(p.host, p.port) for p in open_ports}


def main() -> int:
    os.makedirs(RUNS_DIR, exist_ok=True)
    logger = Logger(verbose=True)

    targets = _build_target_list()
    live_count = len(SEGNET_LIVE_HOSTS)
    dead_count = len(targets) - live_count
    logger.stamp(
        f"DISC-10 comparison: {len(targets)} total target(s) "
        f"({live_count} segnet-live, {dead_count} segnet-dead)"
    )

    chunked_open = _run_chunked(targets, logger, RUNS_DIR)
    direct_open = _run_direct(targets, logger, RUNS_DIR)

    # Restrict to segnet-live hosts BEFORE diffing (152-CONTEXT.md Pitfall 4)
    # — dead-subnet results are never part of the reproduction check.
    chunked_live = {(h, p) for (h, p) in chunked_open if _is_segnet_live(h)}
    direct_live = {(h, p) for (h, p) in direct_open if _is_segnet_live(h)}

    # A "reproduction candidate" is a (host, port) the direct run found open
    # on segnet-live that the chunked run's sweep did not — i.e. genuinely
    # suppressed by throttling, not a closed port or unrelated gap.
    reproduction_candidates = sorted(direct_live - chunked_live)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report = {
        "run_timestamp_utc": stamp,
        "target_counts": {
            "total": len(targets),
            "segnet_live": live_count,
            "segnet_dead": dead_count,
        },
        "chunked_open_ports": sorted(f"{h}:{p}" for h, p in chunked_open),
        "direct_open_ports": sorted(f"{h}:{p}" for h, p in direct_open),
        "chunked_open_ports_segnet_live_only": sorted(f"{h}:{p}" for h, p in chunked_live),
        "direct_open_ports_segnet_live_only": sorted(f"{h}:{p}" for h, p in direct_live),
        "reproduction_candidates": sorted(f"{h}:{p}" for h, p in reproduction_candidates),
    }

    report_path = os.path.join(RUNS_DIR, f"compare-{stamp}.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print("\n=== DISC-10 chunked-vs-direct comparison report ===")
    print(json.dumps(report, indent=2))
    print(f"\nReport written to: {report_path}")

    if reproduction_candidates:
        print(
            f"\n{len(reproduction_candidates)} reproduction candidate(s) found: "
            f"{report['reproduction_candidates']}"
        )
    else:
        print("\n0 reproduction candidates — chunked and direct segnet-live open-port sets match.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
