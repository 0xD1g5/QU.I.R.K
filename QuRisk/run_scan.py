import argparse
from datetime import datetime, timezone
from collections import Counter
from typing import List, Tuple

from qcscan.config import load_config
from qcscan.interactive import interactive_config
from qcscan.db import init_db, get_session
from qcscan.models import CryptoEndpoint

from qcscan.logging_util import Logger
from qcscan.scanner.target_expander import expand_targets
from qcscan.scanner.fingerprint import fingerprint_service
from qcscan.scanner.tls_scanner import scan_tls_targets
from qcscan.scanner.ssh_scanner import scan_ssh_targets

from qcscan.discovery.nmap_provider import run_nmap_discovery
from qcscan.discovery.nmap_parser import to_targets as nmap_to_targets

from qcscan.assessment.operator_context import prompt_for_context, attach_context

from qcscan.engine.risk_engine import evaluate_endpoints
from qcscan.reports.writer import write_reports


def _error_category(desc: str) -> str:
    if not desc:
        return "UNKNOWN"
    if ":" in desc:
        return desc.split(":", 1)[0].strip()
    return "UNCLASSIFIED"


def _build_nmap_target_list(cfg) -> List[str]:
    targets: List[str] = []
    targets.extend(cfg.targets.cidrs or [])
    targets.extend(cfg.targets.fqdns or [])
    targets.extend(cfg.targets.include_ips or [])
    return [t for t in targets if t]


def _filter_excludes(targets: List[Tuple[str, int]], exclude_ips: List[str]) -> List[Tuple[str, int]]:
    if not exclude_ips:
        return targets
    ex = set(exclude_ips)
    return [(h, p) for (h, p) in targets if h not in ex]


def main():
    parser = argparse.ArgumentParser(description="Quantum Crypto Scanner (qcscan)")
    parser.add_argument("--config", help="Path to config.yaml (skip prompts)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output during scan")
    parser.add_argument("--progress", action="store_true", help="Show progress bars during scan")

    parser.add_argument("--discovery", choices=["builtin", "nmap"], default="builtin",
                        help="Discovery mode: builtin fingerprinting or nmap pre-scan")
    parser.add_argument("--nmap-path", default="nmap", help="Path to nmap executable (default: nmap)")
    parser.add_argument("--nmap-timeout", type=int, default=1800, help="Nmap discovery timeout seconds")
    parser.add_argument("--nmap-extra-args", default="", help='Extra nmap args (quoted), e.g. "-sS" if admin')

    args = parser.parse_args()

    tqdm = None
    if args.progress:
        from tqdm import tqdm as _tqdm  # type: ignore
        tqdm = _tqdm

    logger = Logger(verbose=args.verbose, use_tqdm=bool(args.progress))

    used_config_file = False
    if args.config:
        logger.info(f"🧾 Loading config from: {args.config}")
        cfg = load_config(args.config)
        used_config_file = True
    else:
        cfg = interactive_config()

    # v3.5.1 context prompts (only in interactive mode)
    if not used_config_file:
        ctx = prompt_for_context()
        attach_context(cfg, ctx)

    init_db(cfg.output.db_path)

    # ==============================
    # Discovery: builtin vs nmap
    # ==============================
    if args.discovery == "nmap":
        nmap_targets = _build_nmap_target_list(cfg)
        if not nmap_targets:
            logger.info("⚠️ No CIDRs/FQDNs/IPs provided for Nmap discovery. Add targets and re-run.")
            return

        ports_for_nmap = sorted(set((cfg.scan.ports_tls or []) + [22, 80, 8080, 8000]))
        extra_args = args.nmap_extra_args.strip().split() if args.nmap_extra_args.strip() else None

        open_ports = run_nmap_discovery(
            targets=nmap_targets,
            ports=ports_for_nmap,
            output_dir=cfg.output.directory,
            logger=logger,
            nmap_path=args.nmap_path,
            extra_args=extra_args,
            timeout_seconds=args.nmap_timeout,
        )

        targets = nmap_to_targets(open_ports, tcp_only=True)
        targets = _filter_excludes(targets, cfg.targets.exclude_ips or [])

        if not targets:
            logger.info("⚠️ Nmap discovery found no open ports in scope. Nothing to scan.")
            return

        logger.stamp(f"Using Nmap-discovered targets only: {len(targets)} endpoint(s)")

    else:
        targets = expand_targets(cfg)
        if not targets:
            logger.info("⚠️ No targets provided. Add CIDRs/FQDNs/IPs and re-run.")
            return

    # ------------------------------
    # Fingerprinting with progress
    # ------------------------------
    tls_targets = []
    ssh_targets = []
    inventory_endpoints = []

    if tqdm:
        fp_iter = tqdm(targets, desc="Fingerprinting", unit="target")
    else:
        fp_iter = targets
        logger.stamp(f"Fingerprinting {len(targets)} targets...")

    for host, port in fp_iter:
        fp = fingerprint_service(host, port, timeout=cfg.scan.timeout_seconds)

        ep = CryptoEndpoint(
            host=host,
            port=port,
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
            sni_used=bool(cfg.scan.include_sni),
        )

        if not fp.is_open:
            ep.protocol = "CLOSED"
            ep.scan_error = f"{fp.proto}: {fp.detail}"
            inventory_endpoints.append(ep)
            logger.v(f"⛔ CLOSED {host}:{port} ({fp.detail})")
            continue

        if fp.proto == "SSH":
            ssh_targets.append((host, port))
            ep.protocol = "SSH"
            ep.tls_version = fp.detail
            inventory_endpoints.append(ep)
            logger.v(f"🔑 SSH {host}:{port} ({fp.detail})")
            continue

        if fp.proto == "HTTP":
            ep.protocol = "HTTP"
            ep.tls_version = fp.detail
            inventory_endpoints.append(ep)
            logger.v(f"🌐 HTTP {host}:{port} ({fp.detail})")
            continue

        if fp.proto == "TLS":
            tls_targets.append((host, port))
            logger.v(f"🔐 TLS candidate {host}:{port}")
            continue

        ep.protocol = "UNKNOWN"
        ep.tls_version = fp.detail
        inventory_endpoints.append(ep)
        logger.v(f"❓ UNKNOWN {host}:{port} ({fp.detail})")

    logger.stamp(f"TLS candidates: {len(tls_targets)} | SSH candidates: {len(ssh_targets)} | Other inventory: {len(inventory_endpoints)}")

    # ------------------------------
    # TLS scans with progress
    # ------------------------------
    tls_bar = None
    if tqdm and tls_targets:
        tls_bar = tqdm(total=len(tls_targets), desc="TLS Scanning", unit="endpoint")

    tls_endpoints = scan_tls_targets(
        cfg,
        tls_targets,
        logger=logger,
        progress_cb=(tls_bar.update if tls_bar else None),
    ) if tls_targets else []

    if tls_bar:
        tls_bar.close()

    # ------------------------------
    # SSH scans with progress
    # ------------------------------
    ssh_bar = None
    if tqdm and ssh_targets:
        ssh_bar = tqdm(total=len(ssh_targets), desc="SSH Scanning", unit="endpoint")

    ssh_endpoints = scan_ssh_targets(
        cfg,
        ssh_targets,
        logger=logger,
        progress_cb=(ssh_bar.update if ssh_bar else None),
    ) if ssh_targets else []

    if ssh_bar:
        ssh_bar.close()

    endpoints = inventory_endpoints + tls_endpoints + ssh_endpoints
    findings = evaluate_endpoints(cfg, endpoints)

    with get_session(cfg.output.db_path) as session:
        for ep in endpoints:
            session.add(ep)
        session.commit()

    proto_counts = Counter([getattr(e, "protocol", "UNKNOWN") for e in endpoints])
    err_counts = Counter([_error_category(getattr(e, "scan_error", "")) for e in endpoints if getattr(e, "scan_error", None)])

    logger.stamp("Scan Summary")
    for k, v in proto_counts.most_common():
        logger.info(f"  - {k}: {v}")
    if err_counts:
        logger.info("  - Error categories (top):")
        for k, v in err_counts.most_common(10):
            logger.info(f"      {k}: {v}")

    write_reports(cfg, endpoints, findings)


if __name__ == "__main__":
    main()
