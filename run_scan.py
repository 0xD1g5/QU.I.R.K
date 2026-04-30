import argparse
import json
import os
import time
from datetime import datetime, timezone
from collections import Counter
from typing import List, Tuple, Dict, Any, Optional

from quirk.config import load_config
from quirk.interactive import interactive_config
from quirk.db import init_db, get_session
from quirk.models import CryptoEndpoint

from quirk.logging_util import Logger
from quirk.scanner.target_expander import expand_targets
from quirk.scanner.fingerprint import fingerprint_service
from quirk.scanner.tls_scanner import scan_tls_targets
from quirk.scanner.ssh_scanner import scan_ssh_targets
from quirk.scanner.jwt_scanner import scan_jwt_targets
from quirk.scanner.container_scanner import scan_container_targets
from quirk.scanner.source_scanner import scan_source_targets
from quirk.scanner.aws_connector import scan_aws_targets
from quirk.scanner.azure_connector import scan_azure_targets
from quirk.scanner.gcp_connector import scan_gcp_targets
from quirk.scanner.dnssec_scanner import scan_dnssec_targets
from quirk.scanner.email_scanner import scan_email_targets
from quirk.scanner.broker_scanner import (
    scan_kafka_targets, scan_rabbitmq_targets, scan_redis_targets,
)

from quirk.discovery.nmap_provider import run_nmap_discovery
from quirk.discovery.nmap_parser import to_targets as nmap_to_targets

from quirk.assessment.operator_context import attach_context
from quirk.engine.risk_engine import evaluate_endpoints, evaluate_email_endpoints, evaluate_broker_endpoints
from quirk.reports.writer import write_reports

from quirk.engine.profiles import apply_profile
from quirk.engine.cache import scope_hash, load_cache, save_cache, targets_to_serial, serial_to_targets
from quirk.engine.rate_limiter import TokenBucket

from quirk import __version__
from quirk.cli.banner import print_banner


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


def _process_gcs_storage_encryption(gcp_endpoints: list, logger=None) -> list:
    """Read gcs_scan_json from the GCS-SUMMARY sentinel produced by Phase 26 (STOR-03).

    STOR-03 invariant: this function makes ZERO new GCS API calls. Phase 26 already wrote
    per-bucket CryptoEndpoint rows into gcp_endpoints; this helper only consumes the
    sentinel's gcs_scan_json blob to confirm the data hand-off works. No new endpoints are
    created here — the per-bucket rows are already present.

    Returns [] always. Future phases may extend this to derive additional findings from the
    sentinel JSON without making new API calls.
    """
    import json as _json
    sentinel = next(
        (ep for ep in (gcp_endpoints or []) if getattr(ep, "cert_pubkey_alg", "") == "GCS-SUMMARY"),
        None,
    )
    if sentinel is None:
        return []
    raw = getattr(sentinel, "gcs_scan_json", None)
    if not raw:
        return []
    try:
        _json.loads(raw)  # validate JSON (informational; result not used)
    except (ValueError, TypeError):
        return []
    # STOR-03 satisfied: Phase 26's per-bucket rows already in gcp_endpoints; no API call here.
    return []


def main():
    # --- init subcommand: intercept before scan argparse ---
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "init":
        init_parser = argparse.ArgumentParser(
            prog="quirk init",
            description="Generate a starter config.yaml",
        )
        init_parser.add_argument(
            "--output",
            default="config.yaml",
            help="Output path for generated config.yaml (default: ./config.yaml)",
        )
        init_args = init_parser.parse_args(_sys.argv[2:])
        from quirk.cli.init_cmd import run_init
        run_init(init_args.output)
        return

    # --- serve subcommand: intercept before scan argparse to avoid conflicts ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "serve":
        serve_parser = argparse.ArgumentParser(
            prog="quirk serve",
            description="Start the QU.I.R.K. web dashboard",
        )
        serve_parser.add_argument(
            "--port",
            type=int,
            default=8512,
            help="Port to serve on (default: 8512)",
        )
        serve_parser.add_argument(
            "--host",
            default="127.0.0.1",
            help="Host to bind (default: 127.0.0.1)",
        )
        serve_parser.add_argument(
            "--no-open",
            action="store_true",
            default=False,
            help="Do not automatically open the browser",
        )
        serve_args = serve_parser.parse_args(_sys.argv[2:])
        print_banner(__version__, quiet=False)
        from quirk.dashboard.server import serve as _serve
        _serve(port=serve_args.port, host=serve_args.host, no_open=serve_args.no_open)
        return

    parser = argparse.ArgumentParser(description="QU.I.R.K. -- Quantum Infrastructure Readiness Kit")
    parser.add_argument("--version", action="version", version=f"QU.I.R.K. v{__version__}")
    parser.add_argument("--quiet", action="store_true", default=False, help="Suppress banner and decorative output")
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

    # Phase 33 / D-01: cloud broker target flags (repeatable)
    parser.add_argument(
        "--azure-servicebus-namespace",
        action="append", default=[], dest="azure_servicebus_namespaces",
        help="Azure Service Bus namespace to probe (repeatable). Phase 33 / D-01.",
    )
    parser.add_argument(
        "--aws-sqs-region",
        action="append", default=[], dest="aws_sqs_regions",
        help="AWS SQS region to probe (repeatable). Phase 33 / D-01.",
    )

    args = parser.parse_args()

    quiet = getattr(args, "quiet", False)
    print_banner(__version__, quiet=quiet)

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
    scan_profile = args.profile
    if args.config:
        logger.info(f"🧾 Loading config from: {args.config}")
        cfg = load_config(args.config)
        used_config_file = True
    else:
        cfg, scan_profile = interactive_config()

    # Apply profile defaults (v3.7)
    apply_profile(cfg, scan_profile, safe_mode=args.safe_mode)

    # Phase 33 / D-01: cloud broker target plumbing — CLI extends config-supplied lists
    if getattr(args, "azure_servicebus_namespaces", None):
        cfg.connectors.broker_azure_namespaces = (
            list(cfg.connectors.broker_azure_namespaces or []) + list(args.azure_servicebus_namespaces)
        )
    if getattr(args, "aws_sqs_regions", None):
        cfg.connectors.broker_sqs_regions = (
            list(cfg.connectors.broker_sqs_regions or []) + list(args.aws_sqs_regions)
        )

    # Score profile (calibration) — independent from scan profile
    if getattr(args, "score_profile", None):
        if getattr(cfg, "intelligence", None) is None:
            try:
                from quirk.config import IntelligenceCfg
                cfg.intelligence = IntelligenceCfg()  # type: ignore[attr-defined]
            except Exception:
                pass
        if getattr(cfg, "intelligence", None) is not None:
            cfg.intelligence.profile = args.score_profile  # type: ignore[attr-defined]

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
    # Phase 41 / D-08: read fingerprint timeout from canonical TimeoutsCfg sub-table.
    fp_timeout = getattr(cfg.scan.timeouts, "fingerprint_seconds", cfg.scan.timeout_seconds)
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

            from concurrent.futures import ThreadPoolExecutor, as_completed

            with ThreadPoolExecutor(max_workers=fp_conc) as ex:
                futs = [ex.submit(_fp_task, h, p) for h, p in targets]
                for f in as_completed(futs):
                    fp_results.append(f.result())

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
        "hosts_scanned": sorted({h for h, _ in targets}),
        "ports_scanned": sorted({p for _, p in targets}),
    }

    logger.stamp(f"TLS candidates: {len(tls_targets)} | SSH candidates: {len(ssh_targets)} | Other inventory: {len(inventory_endpoints)}")

    # ==============================
    # TLS scan phase (phase-tuned)
    # ==============================
    # Phase 41 / D-08: BACK-45 dissolved. The TLS scanner now reads
    # cfg.scan.timeouts.tls_seconds and cfg.scan.tls_concurrency directly — no
    # more cfg.scan mutate-and-restore pattern around the scan call.
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

    # ==============================
    # SSH scan phase (phase-tuned)
    # ==============================
    # Phase 41 / D-08: BACK-45 dissolved for SSH as well. The SSH scanner reads
    # cfg.scan.timeouts.ssh_seconds and cfg.scan.ssh_concurrency directly.
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

    # ==============================
    # JWT scan phase
    # ==============================
    jwt_endpoints = []
    with _phase_timer(run_stats, "jwt_scanning"):
        if cfg.connectors.enable_jwt and cfg.connectors.jwt_targets:
            jwt_endpoints = scan_jwt_targets(
                cfg.connectors.jwt_targets,
                timeout=cfg.scan.timeouts.jwt_seconds,
                logger=logger,
            )

    # ==============================
    # Container scan phase
    # ==============================
    container_endpoints = []
    with _phase_timer(run_stats, "container_scanning"):
        if cfg.connectors.enable_container and cfg.connectors.container_targets:
            container_endpoints = scan_container_targets(
                cfg.connectors.container_targets,
                timeout=cfg.scan.timeouts.container_seconds,
                logger=logger,
            )

    # ==============================
    # Source code scan phase
    # ==============================
    source_endpoints = []
    with _phase_timer(run_stats, "source_scanning"):
        if cfg.connectors.enable_source and cfg.connectors.source_targets:
            source_endpoints = scan_source_targets(
                cfg.connectors.source_targets,
                timeout=cfg.scan.timeouts.source_seconds,
                logger=logger,
            )

    # ==============================
    # AWS cloud connector phase
    # ==============================
    aws_endpoints = []
    with _phase_timer(run_stats, "aws_scanning"):
        if cfg.connectors.enable_aws:
            aws_endpoints = scan_aws_targets(
                region=cfg.connectors.aws_region,
                profile=cfg.connectors.aws_profile,
                logger=logger,
            )

    # ==============================
    # Azure cloud connector phase
    # ==============================
    azure_endpoints = []
    with _phase_timer(run_stats, "azure_scanning"):
        if cfg.connectors.enable_azure:
            azure_endpoints = scan_azure_targets(
                subscription_id=cfg.connectors.azure_subscription_id or "",
                keyvault_urls=cfg.connectors.azure_keyvault_urls,
                logger=logger,
            )

    # ==============================
    # GCP cloud connector phase
    # ==============================
    gcp_endpoints = []
    with _phase_timer(run_stats, "gcp_scanning"):
        if cfg.connectors.enable_gcp:
            gcp_endpoints = scan_gcp_targets(
                project_id=cfg.connectors.gcp_project_id or "",
                logger=logger,
            )

    # ── Shared identity-scan session timestamp (ISSUE-3 fix) ──
    session_start = datetime.now(timezone.utc)

    # ==============================
    # DB connector phase (PostgreSQL / MySQL) — Phase 27
    # ==============================
    db_endpoints = []
    with _phase_timer(run_stats, "db_scanning"):
        if cfg.connectors.enable_db:
            from quirk.scanner.db_connector import scan_pg_targets, scan_mysql_targets
            if cfg.connectors.pg_targets:
                db_endpoints.extend(scan_pg_targets(
                    targets=cfg.connectors.pg_targets,
                    user=cfg.connectors.pg_scanner_user,
                    password=cfg.connectors.pg_scanner_password,
                    logger=logger,
                    session_start=session_start,
                    cfg=cfg,
                ))
            if cfg.connectors.mysql_targets:
                db_endpoints.extend(scan_mysql_targets(
                    targets=cfg.connectors.mysql_targets,
                    user=cfg.connectors.mysql_scanner_user,
                    password=cfg.connectors.mysql_scanner_password,
                    logger=logger,
                    session_start=session_start,
                    cfg=cfg,
                ))

    # ==============================
    # S3 object storage encryption (Phase 28, STOR-01)
    # ==============================
    s3_endpoints = []
    with _phase_timer(run_stats, "s3_scanning"):
        if cfg.connectors.enable_s3:
            from quirk.scanner.aws_connector import _scan_s3_encryption, BOTO3_AVAILABLE
            if not BOTO3_AVAILABLE:
                logger.v("boto3 not installed — S3 scanning skipped")
            else:
                import boto3
                s3_session = boto3.Session(
                    region_name=cfg.connectors.aws_region,
                    profile_name=cfg.connectors.aws_profile,
                )
                s3_endpoints = _scan_s3_encryption(
                    session=s3_session,
                    logger=logger,
                    session_start=session_start,
                    endpoint_url=cfg.connectors.aws_endpoint_url or None,
                )
                logger.info(f"S3 scan: {len(s3_endpoints)} bucket endpoints")

    # ==============================
    # Azure Blob container encryption (Phase 28, STOR-02)
    # ==============================
    blob_endpoints = []
    with _phase_timer(run_stats, "blob_scanning"):
        if cfg.connectors.enable_blob:
            from quirk.scanner.azure_connector import _scan_blob_encryption, AZURE_AVAILABLE, DefaultAzureCredential
            if not AZURE_AVAILABLE:
                logger.v("azure SDK not installed — Azure Blob scanning skipped")
            elif not (cfg.connectors.azure_subscription_id or "").strip():
                logger.v("azure_subscription_id not set — Azure Blob scanning skipped")
            else:
                blob_endpoints = _scan_blob_encryption(
                    credential=DefaultAzureCredential(),
                    subscription_id=cfg.connectors.azure_subscription_id,
                    logger=logger,
                    session_start=session_start,
                )
                logger.info(f"Azure Blob scan: {len(blob_endpoints)} container endpoints")

    # ==============================
    # K8S secrets inspection (Phase 29, K8S-01 / K8S-02 / K8S-03)
    # ==============================
    k8s_endpoints = []
    with _phase_timer(run_stats, "k8s_scanning"):
        if cfg.connectors.enable_k8s:
            from quirk.scanner.k8s_connector import scan_k8s_targets
            k8s_endpoints = scan_k8s_targets(
                provider=cfg.connectors.k8s_provider or "",
                cluster_name=cfg.connectors.k8s_cluster_name or "",
                namespace=cfg.connectors.k8s_namespace or "default",
                kubeconfig=cfg.connectors.k8s_kubeconfig or None,
                context=cfg.connectors.k8s_context or None,
                gcp_project_id=cfg.connectors.gcp_project_id or "",
                gke_clusters=cfg.connectors.gke_clusters or [],
                azure_subscription_id=cfg.connectors.azure_subscription_id or "",
                aks_clusters=cfg.connectors.aks_clusters or [],
                logger=logger,
                session_start=session_start,
            )
            # EKS path uses boto3 (NOT kubernetes Python client). Run alongside
            # GKE/AKS/secret enumeration when k8s_provider == "eks".
            if (cfg.connectors.k8s_provider or "").lower() == "eks":
                try:
                    from quirk.scanner.aws_connector import (
                        BOTO3_AVAILABLE,
                        _scan_eks_encryption,
                    )
                    if BOTO3_AVAILABLE:
                        import boto3 as _boto3_eks
                        _eks_session = _boto3_eks.Session(
                            region_name=getattr(cfg.connectors, "aws_region", None) or None,
                            profile_name=getattr(cfg.connectors, "aws_profile", None) or None,
                        )
                        k8s_endpoints.extend(_scan_eks_encryption(
                            _eks_session, logger, session_start=session_start,
                        ))
                except Exception as exc:
                    logger.v(f"EKS encryption scan unavailable: {exc}")
            logger.info(f"K8S scan: {len(k8s_endpoints)} cluster endpoints")

    # ==============================
    # GCS bucket encryption re-use (Phase 28, STOR-03 — zero API call invariant)
    # ==============================
    gcs_storage_endpoints = []
    with _phase_timer(run_stats, "gcs_storage_reuse"):
        gcs_storage_endpoints = _process_gcs_storage_encryption(gcp_endpoints, logger=logger)
        if gcs_storage_endpoints:
            logger.info(f"GCS storage re-use: {len(gcs_storage_endpoints)} derived endpoints")

    # ── DNSSEC scanning ─────────────────────────────────────
    dnssec_endpoints = []
    with _phase_timer(run_stats, "dnssec_scanning"):
        if cfg.connectors.enable_dnssec and cfg.connectors.dnssec_targets:
            dnssec_endpoints = scan_dnssec_targets(
                targets=cfg.connectors.dnssec_targets,
                timeout=getattr(cfg.connectors, "dnssec_timeout", 10),
                logger=logger,
                session_start=session_start,
            )
            logger.info("DNSSEC scan: %d endpoints from %d targets",
                        len(dnssec_endpoints), len(cfg.connectors.dnssec_targets))

    # ── SAML/OIDC scanning ────────────────────────────────────
    saml_endpoints = []
    with _phase_timer(run_stats, "saml_scanning"):
        if cfg.connectors.enable_saml and cfg.connectors.saml_targets:
            from quirk.scanner.saml_scanner import scan_saml_targets
            saml_endpoints = scan_saml_targets(
                targets=cfg.connectors.saml_targets,
                timeout=getattr(cfg.connectors, "saml_timeout", 10),
                logger=logger,
                session_start=session_start,
            )
            logger.info("SAML scan: %d endpoints from %d targets",
                        len(saml_endpoints), len(cfg.connectors.saml_targets))

    # ── Kerberos scanning ────────────────────────────────────
    kerberos_endpoints = []
    with _phase_timer(run_stats, "kerberos_scanning"):
        if cfg.connectors.enable_kerberos and cfg.connectors.kerberos_targets:
            from quirk.scanner.kerberos_scanner import scan_kerberos_targets
            kerberos_endpoints = scan_kerberos_targets(
                targets=cfg.connectors.kerberos_targets,
                timeout=getattr(cfg.connectors, "kerberos_timeout", 10),
                logger=logger,
                session_start=session_start,
            )
            logger.info("Kerberos scan: %d endpoints from %d targets",
                        len(kerberos_endpoints), len(cfg.connectors.kerberos_targets))

    # ── Vault scanning (Phase 30, VAULT-01/02/03) ─────────────────────────────
    vault_endpoints = []
    with _phase_timer(run_stats, "vault_scanning"):
        if cfg.connectors.enable_vault:
            from quirk.scanner.vault_connector import (
                scan_vault_targets,
                HVAC_AVAILABLE,
            )
            if not HVAC_AVAILABLE:
                logger.v("hvac not installed -- Vault scanning skipped")
            elif not (cfg.connectors.vault_addr or os.environ.get("VAULT_ADDR")):
                logger.v("vault_addr not set -- Vault scanning skipped")
            else:
                vault_endpoints = scan_vault_targets(
                    vault_addr=(cfg.connectors.vault_addr
                                or os.environ.get("VAULT_ADDR", "")),
                    token=cfg.connectors.vault_token,
                    transit_mount=cfg.connectors.vault_transit_mount or "transit",
                    tls_verify=cfg.connectors.vault_tls_verify,
                    logger=logger,
                    session_start=session_start,
                    cfg=cfg,
                )
                logger.info("Vault scan: %d endpoints", len(vault_endpoints))

    # ── Email TLS scanning (Phase 32 — v4.4 Data in Motion) ────
    email_endpoints = []
    with _phase_timer(run_stats, "email_scanning"):
        if cfg.connectors.enable_email:
            # D-01/D-02: reuse the existing TLS target list verbatim (deduplicated by host)
            email_hosts = list(dict.fromkeys(h for h, _ in tls_targets))
            if email_hosts:
                email_endpoints = scan_email_targets(
                    hosts=email_hosts,
                    timeout=cfg.scan.timeouts.email_seconds,
                    logger=logger,
                    session_start=session_start,
                )
                logger.info(f"Email scan: {len(email_endpoints)} endpoints from {len(email_hosts)} hosts")

    # ── Broker TLS scanning (Phase 33) ────────────────────────
    kafka_endpoints = []
    rabbit_endpoints = []
    redis_endpoints = []
    with _phase_timer(run_stats, "broker_scanning"):
        if cfg.connectors.enable_broker:
            broker_hosts = list(dict.fromkeys(h for h, _ in tls_targets))
            if broker_hosts:
                kafka_endpoints = scan_kafka_targets(
                    hosts=broker_hosts,
                    timeout=cfg.scan.timeouts.broker_seconds,
                    profile=scan_profile,
                    logger=logger,
                    session_start=session_start,
                )
                rabbit_endpoints = scan_rabbitmq_targets(
                    hosts=broker_hosts,
                    azure_namespaces=cfg.connectors.broker_azure_namespaces,
                    sqs_regions=cfg.connectors.broker_sqs_regions,
                    timeout=cfg.scan.timeouts.broker_seconds,
                    logger=logger,
                    session_start=session_start,
                )
                redis_endpoints = scan_redis_targets(
                    hosts=broker_hosts,
                    timeout=cfg.scan.timeouts.broker_seconds,
                    logger=logger,
                    session_start=session_start,
                )
                logger.info(
                    f"Broker scan: kafka={len(kafka_endpoints)} "
                    f"rabbit={len(rabbit_endpoints)} redis={len(redis_endpoints)}"
                )

    # broker_scan_json aggregation (Phase 33 / D-12, D-14)
    all_broker_eps = kafka_endpoints + rabbit_endpoints + redis_endpoints
    if all_broker_eps:
        def _ep_dict(ep):
            return {
                "host": getattr(ep, "host", None),
                "port": getattr(ep, "port", None),
                "protocol": getattr(ep, "protocol", None),
                "tls_version": getattr(ep, "tls_version", None),
                "cipher_suite": getattr(ep, "cipher_suite", None),
                "cert_pubkey_alg": getattr(ep, "cert_pubkey_alg", None),
                "cert_subject": getattr(ep, "cert_subject", None),
                "scan_error": getattr(ep, "scan_error", None),
            }
        azure_eps = [e for e in rabbit_endpoints if getattr(e, "protocol", "") == "AMQPS/Azure-ServiceBus"]
        sqs_eps   = [e for e in rabbit_endpoints if getattr(e, "protocol", "") == "HTTPS/AWS-SQS"]
        rabbit_self = [e for e in rabbit_endpoints if e not in azure_eps and e not in sqs_eps]
        payload = {
            "kafka":            [_ep_dict(e) for e in kafka_endpoints],
            "rabbitmq":         [_ep_dict(e) for e in rabbit_self],
            "redis":            [_ep_dict(e) for e in redis_endpoints],
            "azure_servicebus": [_ep_dict(e) for e in azure_eps],
            "aws_sqs":          [_ep_dict(e) for e in sqs_eps],
            "session_start":    session_start.isoformat() if session_start else None,
        }
        setattr(all_broker_eps[0], "broker_scan_json", json.dumps(payload, default=str))

    endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints
                 + jwt_endpoints + container_endpoints + source_endpoints
                 + aws_endpoints + azure_endpoints + gcp_endpoints
                 + db_endpoints
                 + s3_endpoints + blob_endpoints + gcs_storage_endpoints
                 + k8s_endpoints
                 + dnssec_endpoints + saml_endpoints + kerberos_endpoints
                 + vault_endpoints
                 + email_endpoints
                 + kafka_endpoints + rabbit_endpoints + redis_endpoints)

    # ==============================
    # Findings + persistence + reports
    # ==============================
    with _phase_timer(run_stats, "risk_engine"):
        findings = evaluate_endpoints(cfg, endpoints)
        # Phase 32: email-specific findings (EMAIL-08, EMAIL-09).
        # Titles are unique strings not produced elsewhere, so the (host, port,
        # title, recommendation) dedup key in evaluate_endpoints will not collide
        # with these. D-11 layered findings (port 25 + weak cipher) survive.
        email_findings = evaluate_email_endpoints(email_endpoints)
        if email_findings:
            findings = (findings or []) + email_findings
        # Phase 33: broker-specific findings (layered findings survive _dedupe_findings
        # because titles differ per protocol; D-11/D-12 carry-forward from Phase 32).
        broker_findings = evaluate_broker_endpoints(all_broker_eps if 'all_broker_eps' in dir() else [])
        if broker_findings:
            findings = (findings or []) + broker_findings

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
