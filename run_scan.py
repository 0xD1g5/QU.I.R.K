import argparse
import time
from datetime import datetime, timezone
from collections import Counter
from typing import List, Tuple, Dict, Any, Optional

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

from qcscan.engine.profiles import apply_profile
from qcscan.engine.cache import scope_hash, load_cache, save_cache, targets_to_serial, serial_to_targets
from qcscan.engine.rate_limiter import TokenBucket


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


def _get_scan_int(cfg, attr: str, fallback: int) -> int:
    v = getattr(cfg.scan, attr, None)
    if v is None:
        return fallback
    try:
        return int(v)
    except Exception:
        return fallback


def _phase_timer(run_stats: Dict[str, Any], name: str):
    class _T:
        def __enter__(self_t):
            self_t.start = time.perf_counter()
            return self_t
        def __exit__(self_t, exc_type, exc, tb):
            dur = time.perf_counter() - self_t.start
            run_stats["timings_sec"][name] = round(dur, 3)
    return _T()


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

    # v3.7: profiles + caching + safety
    parser.add_argument("--profile", choices=["quick", "standard", "deep"], default="standard", help="Scan profile")
    parser.add_argument("--score-profile",
        choices=["lenient", "balanced", "strict"],
        default=None,
        help="Scoring calibration profile (lenient|balanced|strict). Does NOT affect scan behavior.",)
    parser.add_argument("--safe-mode", action="store_true", help="Reduce concurrency and increase timeouts")
    parser.add_argument("--rate-limit", type=float, default=0.0, help="Targets/sec limiter (0 = off)")

    parser.add_argument("--cache", action="store_true", help="Enable cache for discovery/fingerprint (recommended)")
    parser.add_argument("--cache-ttl-hours", type=int, default=24, help="Cache TTL in hours")
    parser.add_argument("--resume", action="store_true", help="Reuse cache if valid")
    parser.add_argument("--force-discovery", action="store_true", help="Ignore discovery cache and re-run")

    args = parser.parse_args()

    tqdm = None
    if args.progress:
        from tqdm import tqdm as _tqdm  # type: ignore
        tqdm = _tqdm

    logger = Logger(verbose=args.verbose, use_tqdm=bool(args.progress))

    run_stats: Dict[str, Any] = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "timings_sec": {},
        "profile": args.profile,
        "score_profile": args.score_profile or "balanced",
        "discovery_mode": args.discovery,
        "cache_enabled": bool(args.cache),
        "safe_mode": bool(args.safe_mode),
        "rate_limit": args.rate_limit,
    }

    used_config_file = False
    if args.config:
        logger.info(f"🧾 Loading config from: {args.config}")
        cfg = load_config(args.config)
        used_config_file = True
    else:
        cfg = interactive_config()

    # Apply profile defaults (v3.7)
    apply_profile(cfg, args.profile, safe_mode=args.safe_mode)
    # Score profile (calibration) — independent from scan profile
    if getattr(args, "score_profile", None):
        if getattr(cfg, "intelligence", None) is None:
            try:
                from qcscan.config import IntelligenceCfg
                cfg.intelligence = IntelligenceCfg()  # type: ignore[attr-defined]
            except Exception:
                pass
        if getattr(cfg, "intelligence", None) is not None:
            cfg.intelligence.profile = args.score_profile  # type: ignore[attr-defined]

    # v3.5.1 context prompts (only in interactive mode)
    if not used_config_file:
        ctx = prompt_for_context()
        attach_context(cfg, ctx)

    init_db(cfg.output.db_path)

    limiter = TokenBucket(args.rate_limit, capacity=max(1.0, args.rate_limit)) if args.rate_limit and args.rate_limit > 0 else None

    # ==============================
    # Discovery targets
    # ==============================
    targets: List[Tuple[str, int]] = []

    if args.discovery == "nmap":
        nmap_targets = _build_nmap_target_list(cfg)
        if not nmap_targets:
            logger.info("⚠️ No CIDRs/FQDNs/IPs provided for Nmap discovery. Add targets and re-run.")
            return

        ports_for_nmap = sorted(set((cfg.scan.ports_tls or []) + [22, 80, 8080, 8000]))
        extra_args = args.nmap_extra_args.strip()

        d_key = f"discovery-{scope_hash(cfg, 'nmap', nmap_extra_args=extra_args, ports=ports_for_nmap)}"
        cached = load_cache(cfg.output.directory, d_key, args.cache_ttl_hours) if args.cache and args.resume and not args.force_discovery else None

        with _phase_timer(run_stats, "discovery"):
            if cached:
                logger.stamp(f"♻️ Using cached discovery results ({d_key})")
                targets = serial_to_targets(cached.get("targets", []))
            else:
                open_ports = run_nmap_discovery(
                    targets=nmap_targets,
                    ports=ports_for_nmap,
                    output_dir=cfg.output.directory,
                    logger=logger,
                    nmap_path=args.nmap_path,
                    extra_args=extra_args.split() if extra_args else None,
                    timeout_seconds=args.nmap_timeout,
                )
                targets = nmap_to_targets(open_ports, tcp_only=True)
                targets = _filter_excludes(targets, cfg.targets.exclude_ips or [])
                if args.cache:
                    save_cache(cfg.output.directory, d_key, {"targets": targets_to_serial(targets), "ports": ports_for_nmap, "mode": "nmap"})

        if not targets:
            logger.info("⚠️ Nmap discovery found no open ports in scope. Nothing to scan.")
            return

        logger.stamp(f"Using Nmap-discovered targets only: {len(targets)} endpoint(s)")

    else:
        with _phase_timer(run_stats, "discovery"):
            targets = expand_targets(cfg)
        if not targets:
            logger.info("⚠️ No targets provided. Add CIDRs/FQDNs/IPs and re-run.")
            return

    # ==============================
    # Fingerprinting (with cache)
    # ==============================
    fp_timeout = _get_scan_int(cfg, "fingerprint_timeout_seconds", cfg.scan.timeout_seconds)
    fp_conc = _get_scan_int(cfg, "fingerprint_concurrency", cfg.scan.concurrency)

    fp_key = f"fingerprint-{scope_hash(cfg, args.discovery, nmap_extra_args=args.nmap_extra_args, ports=sorted(set([p for _, p in targets])))}"
    fp_cached = load_cache(cfg.output.directory, fp_key, args.cache_ttl_hours) if args.cache and args.resume else None

    inventory_endpoints: List[CryptoEndpoint] = []
    tls_targets: List[Tuple[str, int]] = []
    ssh_targets: List[Tuple[str, int]] = []
    classified_details: Dict[Tuple[str, int], str] = {}

    def _fp_task(host: str, port: int) -> Dict[str, Any]:
        if limiter:
            limiter.acquire(1.0)
        fp = fingerprint_service(host, port, timeout=fp_timeout)
        return {"host": host, "port": port, "is_open": fp.is_open, "proto": fp.proto, "detail": fp.detail}

    with _phase_timer(run_stats, "fingerprinting"):
        fp_results: List[Dict[str, Any]] = []
        if fp_cached:
            logger.stamp(f"♻️ Using cached fingerprint results ({fp_key})")
            fp_results = fp_cached.get("fingerprints", [])
        else:
            logger.stamp(f"Fingerprinting {len(targets)} targets... (workers={fp_conc}, timeout={fp_timeout}s)")
            if tqdm:
                bar = tqdm(total=len(targets), desc="Fingerprinting", unit="target")
            else:
                bar = None

            from concurrent.futures import ThreadPoolExecutor, as_completed

            with ThreadPoolExecutor(max_workers=fp_conc) as ex:
                futs = [ex.submit(_fp_task, h, p) for h, p in targets]
                for f in as_completed(futs):
                    fp_results.append(f.result())
                    if bar:
                        bar.update(1)
            if bar:
                bar.close()

            if args.cache:
                save_cache(cfg.output.directory, fp_key, {"fingerprints": fp_results, "timeout": fp_timeout, "workers": fp_conc})

    # Build endpoint inventory lists
    for r in fp_results:
        host = r["host"]
        port = int(r["port"])
        proto = r.get("proto")
        detail = r.get("detail")
        is_open = bool(r.get("is_open"))
        key = (host, port)
        classified_details[key] = detail or ""

        ep = CryptoEndpoint(
            host=host,
            port=port,
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
            sni_used=bool(cfg.scan.include_sni),
        )

        if not is_open:
            ep.protocol = "CLOSED"
            ep.service_detail = detail
            ep.scan_error = f"{proto}: {detail}"
            inventory_endpoints.append(ep)
            logger.v(f"⛔ CLOSED {host}:{port} ({detail})")
            continue

        if proto == "SSH":
            ssh_targets.append((host, port))
            logger.v(f"🔑 SSH {host}:{port} ({detail})")
            continue

        if proto == "HTTP":
            ep.protocol = "HTTP"
            ep.service_detail = detail
            ep.tls_version = detail
            inventory_endpoints.append(ep)
            logger.v(f"🌐 HTTP {host}:{port} ({detail})")
            continue

        if proto == "TLS":
            tls_targets.append((host, port))
            logger.v(f"🔐 TLS candidate {host}:{port}")
            continue

        ep.protocol = "UNKNOWN"
        ep.service_detail = detail
        ep.tls_version = detail
        inventory_endpoints.append(ep)
        logger.v(f"❓ UNKNOWN {host}:{port} ({detail})")

    run_stats["counts"] = {
        "targets_total": len(targets),
        "tls_candidates": len(tls_targets),
        "ssh_candidates": len(ssh_targets),
        "inventory_other": len(inventory_endpoints),
    }

    logger.stamp(f"TLS candidates: {len(tls_targets)} | SSH candidates: {len(ssh_targets)} | Other inventory: {len(inventory_endpoints)}")

    # ==============================
    # TLS scan phase (phase-tuned)
    # ==============================
    tls_timeout = _get_scan_int(cfg, "tls_timeout_seconds", cfg.scan.timeout_seconds)
    tls_conc = _get_scan_int(cfg, "tls_concurrency", cfg.scan.concurrency)

    # Temporarily override shared cfg.scan controls (minimal diff)
    base_timeout = cfg.scan.timeout_seconds
    base_conc = cfg.scan.concurrency
    cfg.scan.timeout_seconds = tls_timeout
    cfg.scan.concurrency = tls_conc

    tls_endpoints = []
    with _phase_timer(run_stats, "tls_scanning"):
        if tls_targets:
            tls_endpoints = scan_tls_targets(
                cfg,
                tls_targets,
                logger=logger,
                progress_cb=None
            )
            for ep in tls_endpoints:
                key = (getattr(ep, "host", ""), int(getattr(ep, "port", 0)))
                ep.service_detail = classified_details.get(key, "")

    cfg.scan.timeout_seconds = base_timeout
    cfg.scan.concurrency = base_conc

    # ==============================
    # SSH scan phase (phase-tuned)
    # ==============================
    ssh_timeout = _get_scan_int(cfg, "ssh_timeout_seconds", cfg.scan.timeout_seconds)
    ssh_conc = _get_scan_int(cfg, "ssh_concurrency", cfg.scan.concurrency)

    cfg.scan.timeout_seconds = ssh_timeout
    cfg.scan.concurrency = ssh_conc

    ssh_endpoints = []
    with _phase_timer(run_stats, "ssh_scanning"):
        if ssh_targets:
            ssh_endpoints = scan_ssh_targets(
                cfg,
                ssh_targets,
                logger=logger,
                progress_cb=None
            )
            for ep in ssh_endpoints:
                key = (getattr(ep, "host", ""), int(getattr(ep, "port", 0)))
                ep.service_detail = classified_details.get(key, "")

    cfg.scan.timeout_seconds = base_timeout
    cfg.scan.concurrency = base_conc

    endpoints = inventory_endpoints + tls_endpoints + ssh_endpoints

    # ==============================
    # Findings + persistence + reports
    # ==============================
    with _phase_timer(run_stats, "risk_engine"):
        findings = evaluate_endpoints(cfg, endpoints)

    with _phase_timer(run_stats, "db_persist"):
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

    run_stats["ended_utc"] = datetime.now(timezone.utc).isoformat()
    run_stats["protocol_counts"] = dict(proto_counts)
    run_stats["error_categories"] = dict(err_counts)

    with _phase_timer(run_stats, "reporting"):
        write_reports(cfg, endpoints, findings, run_stats=run_stats)


if __name__ == "__main__":
    main()
