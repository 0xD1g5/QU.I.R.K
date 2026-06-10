import argparse
import json
import multiprocessing
import os
import sys
import time
from datetime import datetime, timezone
from collections import Counter
from typing import List, Tuple, Dict, Any, Optional

# Windows consoles default to the cp1252 codec, which cannot encode the Unicode
# glyphs QUIRK emits (e.g. the "→" arrow in --help, score gauges, roadmap output).
# Reconfigure stdout/stderr to UTF-8 on Windows so the frozen sensor binary and
# the CLI render correctly instead of raising UnicodeEncodeError. No-op on
# POSIX, where stdout is already UTF-8.
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):  # stream replaced or not a TextIOWrapper
            pass

from quirk.config import load_config
from quirk.util.safe_exc import safe_str
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
from quirk.engine.findings_evaluator import evaluate_endpoints, evaluate_email_endpoints, evaluate_broker_endpoints, evaluate_codesign_endpoints
from quirk.reports.writer import write_reports
from quirk.reports.content_model import ReportCongruenceError  # D-06: fail-closed report halt

from quirk.engine.profiles import apply_profile
from quirk.engine.cache import scope_hash, load_cache, save_cache, targets_to_serial, serial_to_targets
from quirk.engine.rate_limiter import TokenBucket

from quirk import __version__
from quirk.cli.banner import print_banner
from quirk.errors import format_error
from quirk.util.targets import apply_targets_file_override  # D-03
from quirk.util.optional_extra import is_extra_available, select_nmap_port_list  # D-08/D-09
from quirk.cli.job_progress import (  # Phase 65 — best-effort job progress updates
    update_job_stage,
    mark_job_completed,
    mark_job_failed,
    write_scan_checkpoint,   # Phase 67 RESUME-01
)


def apply_security_cli_overrides(cfg, args) -> None:
    """Phase 57 / D-04: CLI flags can only flip cfg.security.* False -> True.

    An absent CLI flag (default=False) MUST NOT override a True value already
    loaded from YAML. This is an opt-in-only pattern: CLI flags escalate
    permissions, never revoke them.
    """
    if getattr(args, "allow_internal_targets", False):
        cfg.security.allow_internal_targets = True
    if getattr(args, "allow_cleartext_broker_probe", False):
        cfg.security.allow_cleartext_broker_probe = True
    if getattr(args, "allow_insecure_jwks", False):
        cfg.security.allow_insecure_jwks = True


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


def _wrapped_phase(run_stats, phase_name, scanner_label, fn, error_endpoints, logger):
    """Phase 41 / D-14: run a scanner phase under BaseException protection.

    Returns the scanner's return value, or [] when a non-fatal exception is
    captured. Re-raises only KeyboardInterrupt and SystemExit so the user can
    abort cleanly. All other exceptions (BaseException subclasses) are turned
    into a CryptoEndpoint row with scan_error_category='exception' so the rest
    of the scan can continue and the failure is visible in the report / DB.
    """
    try:
        with _phase_timer(run_stats, phase_name):
            return fn()
    except (KeyboardInterrupt, SystemExit):
        # D-14: never swallow user-abort or interpreter-exit signals.
        raise
    except BaseException as exc:  # noqa: BLE001 — D-14 wrapper by design
        try:
            logger.error(f"{phase_name}: unhandled exception: {exc!r}")
        except Exception:
            # Logger contract is best-effort; do not let logger failure mask the original error.
            pass
        error_endpoints.append(CryptoEndpoint(
            host=scanner_label,
            port=0,
            protocol="ERROR",
            scan_error=str(exc) or exc.__class__.__name__,
            scan_error_category="exception",
        ))
        return []


def _emit_missing_extra_advisory(scanner_name: str, extra_group: str, error_endpoints) -> None:
    """Phase 41 / D-12 — Phase 68 UX-02: emit QRK-INSTALL-001 stderr advisory + record CryptoEndpoint row.

    Invoked when an optional-extra-gated scanner is enabled but its underlying
    package is not installed. Emits format_error("INSTALL-001") to stderr and
    appends a CryptoEndpoint with scan_error_category='missing_extra' so
    trends.py can exclude it from regression counts (D-15).
    """
    print(format_error("INSTALL-001"), file=sys.stderr)
    error_endpoints.append(CryptoEndpoint(
        host=scanner_name,
        port=0,
        protocol="ADVISORY",
        scan_error=f"optional extra [{extra_group}] not installed",
        scan_error_category="missing_extra",
    ))


def _flush_stage_endpoints(db_path: str, endpoints: list) -> None:
    """Phase 67 RESUME-01: flush a stage's CryptoEndpoint rows to SQLite immediately.

    Called after each scanner stage so a crash between stages leaves results
    for completed stages persisted. Silent no-op on failure — the scan's
    bulk persist at the end is the safety net.
    """
    if not endpoints or not db_path:
        return
    try:
        with get_session(db_path) as session:
            for ep in endpoints:
                session.merge(ep)   # merge: safe if row already exists
            session.commit()
    except Exception:
        pass


def _collect_stage_partial_failures(
    run_stats: dict,
    stage: str,
    error_endpoints: list,
    previous_error_count: int,
) -> list:
    """Phase 67 RESUME-02: build partial_failures entries from new error_endpoints.

    Compares error_endpoints length before vs after a stage to find new errors.
    Returns the list of new partial_failure dicts (also appended to run_stats).
    """
    new_errors = error_endpoints[previous_error_count:]
    stage_failures = []
    for ep in new_errors:
        stage_failures.append({
            "stage": stage,
            "scanner": getattr(ep, "host", "unknown"),
            "error_category": getattr(ep, "scan_error_category", "exception"),
            "error_message": getattr(ep, "scan_error", "") or "",
            "endpoint_count": 0,
        })
    run_stats.setdefault("partial_failures", []).extend(stage_failures)
    return stage_failures


def _resolve_db_path(args) -> str | None:
    """Phase 67 RESUME-01: resolve db_path for pre-scan commands (list-resumable)."""
    if getattr(args, "db_path", None):
        return args.db_path
    config_path = getattr(args, "config", None)
    if config_path:
        try:
            from quirk.config import load_config
            cfg = load_config(config_path)
            return cfg.output.db_path
        except Exception:
            pass
    # Fall back to default path used by config wizard
    return "./quirk.db"


def _handle_list_resumable(args) -> None:
    """Phase 67 RESUME-01: print rich table of incomplete scan runs.

    A scan run is "resumable" if it has scan_checkpoints rows but does NOT
    have a 'reports' stage with status='completed'. Joins scan_jobs to
    recover the original target if available.

    Output columns: Scan ID | Last Stage | Status | Age | Target
    Age > 72h: row highlighted yellow.
    Empty result: plain text 'No resumable scans found.'
    """
    from rich.table import Table
    from rich.console import Console
    from quirk.models import ScanCheckpoint, ScanJob
    from quirk.db import get_session, init_db
    from datetime import datetime, timezone

    db_path = getattr(args, "db_path", None) or _resolve_db_path(args)
    if not db_path:
        print(format_error("INSTALL-003"), file=sys.stderr)
        return

    try:
        init_db(db_path)
    except Exception:
        print(format_error("INSTALL-003"), file=sys.stderr)
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    STALE_HOURS = 72

    try:
        with get_session(db_path) as db:
            # Find scan_run_ids with checkpoints but no completed 'reports' stage
            all_run_ids = [r[0] for r in db.query(ScanCheckpoint.scan_run_id).distinct().all()]
            # scan_run_ids with a completed reports stage
            completed_ids = {
                r[0] for r in db.query(ScanCheckpoint.scan_run_id)
                .filter(ScanCheckpoint.stage == "reports", ScanCheckpoint.status == "completed")
                .all()
            }
            resumable_ids = [rid for rid in all_run_ids if rid not in completed_ids]

            if not resumable_ids:
                print("No resumable scans found.")
                return

            # Build table rows
            table = Table(title="Resumable Scans", show_header=True, header_style="bold")
            table.add_column("Scan ID", style="cyan", no_wrap=True)
            table.add_column("Last Stage", style="white")
            table.add_column("Status", style="white")
            table.add_column("Age", style="white")
            table.add_column("Target", style="dim")

            for run_id in sorted(resumable_ids, reverse=True):
                # Last checkpoint for this run
                last_cp = (
                    db.query(ScanCheckpoint)
                    .filter(ScanCheckpoint.scan_run_id == run_id)
                    .order_by(ScanCheckpoint.checkpoint_id.desc())
                    .first()
                )
                if last_cp is None:
                    continue

                # Age calculation
                completed_at = last_cp.completed_at  # tz-naive UTC
                if completed_at:
                    diff = now - completed_at
                    total_hours = int(diff.total_seconds() // 3600)
                    mins = int((diff.total_seconds() % 3600) // 60)
                    if total_hours >= 24:
                        age_str = f"{total_hours // 24}d {total_hours % 24}h"
                    else:
                        age_str = f"{total_hours}h {mins}m"
                else:
                    age_str = "unknown"
                    total_hours = 0

                # Target from scan_jobs (best-effort)
                job_row = (
                    db.query(ScanJob)
                    .filter(ScanJob.scan_run_id == run_id)
                    .first()
                )
                target_str = getattr(job_row, "target", "—") if job_row else "—"

                row_style = "yellow" if total_hours >= STALE_HOURS else ""
                table.add_row(
                    run_id,
                    last_cp.stage,
                    last_cp.status,
                    age_str,
                    target_str,
                    style=row_style,
                )

            Console().print(table)

    except Exception as exc:
        print(f"[error] list-resumable failed: {exc}", file=sys.stderr)


def _stage_completed(completed_stages: set, stage: str) -> bool:
    """Phase 67 RESUME-01: True if this stage was completed in a prior run."""
    return stage in completed_stages


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
        serve_parser.add_argument(
            "--insecure",
            action="store_true",
            default=False,
            help=(
                "Allow binding a network-reachable interface with no "
                "QUIRK_API_TOKEN set. Off by default; the server refuses such a "
                "bind so a public console cannot be left auth-disabled by "
                "accident. Use only on trusted, firewalled segments."
            ),
        )
        serve_args = serve_parser.parse_args(_sys.argv[2:])
        print_banner(__version__, quiet=False)
        from quirk.dashboard.server import serve as _serve
        _serve(
            port=serve_args.port,
            host=serve_args.host,
            no_open=serve_args.no_open,
            insecure=serve_args.insecure,
        )
        return

    # --- compliance subcommand: intercept before scan argparse (Phase 49 D-05) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "compliance":
        comp_parser = argparse.ArgumentParser(
            prog="quirk compliance",
            description="Inspect QUIRK's compliance mapping data (PCI-DSS / HIPAA / FIPS 140-3)",
        )
        comp_sub = comp_parser.add_subparsers(dest="action", required=True)
        status_parser = comp_sub.add_parser(
            "status",
            help="Print per-framework version, last_verified date, and source URL",
        )
        status_parser.add_argument(
            "--format",
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)",
        )
        # --- Phase 81 CMVP-03/05: compliance cmvp refresh|status ---
        cmvp_parser = comp_sub.add_parser(
            "cmvp",
            help="Inspect / refresh CMVP attestation cache",
        )
        cmvp_sub = cmvp_parser.add_subparsers(dest="cmvp_action", required=True)
        cmvp_refresh = cmvp_sub.add_parser(
            "refresh", help="Refresh CMVP cache from NIST"
        )
        cmvp_refresh.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing the cache",
        )
        cmvp_status = cmvp_sub.add_parser(
            "status", help="Print CMVP cache freshness"
        )
        cmvp_status.add_argument(
            "--format", choices=["text", "json"], default="text"
        )
        comp_args = comp_parser.parse_args(_sys.argv[2:])
        if comp_args.action == "status":
            from quirk.compliance import status_report
            status_report(format=comp_args.format)
            return
        if comp_args.action == "cmvp":
            from quirk.cli.cmvp_cmd import run_cmvp
            run_cmvp(comp_args)
            return
        return

    # --- doctor subcommand: intercept before scan argparse (Phase 52 DOCS-05 / D-10) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "doctor":
        from quirk.cli.doctor_cmd import run_doctor
        run_doctor()
        return

    # --- schedule subcommand: intercept before scan argparse (Phase 63 SCHED-01) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "schedule":
        from quirk.cli.schedule_cmd import run_schedule
        run_schedule(_sys.argv[2:])
        return

    # --- scheduler subcommand: intercept before scan argparse (Phase 63 SCHED-02) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "scheduler":
        from quirk.cli.scheduler_cmd import run_scheduler
        run_scheduler(_sys.argv[2:])
        return

    # --- qramm subcommand: intercept before scan argparse (Phase 55 QRAMM-07) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "qramm":
        if len(_sys.argv) > 2 and _sys.argv[2] == "status":
            from quirk.cli.qramm_cmd import run_qramm_status
            run_qramm_status()
            return
        # Future: other `quirk qramm <action>` subcommands route here.

    # --- analyze-token subcommand: intercept before scan argparse (Phase 94 TOKEN-01) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "analyze-token":
        from quirk.cli.analyze_token_cmd import run_analyze_token
        run_analyze_token(_sys.argv[2:])
        return

    # --- token subcommand: intercept before scan argparse (Phase 102 AUTH-01) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "token":
        from quirk.cli.token_cmd import run_token
        run_token(_sys.argv[2:])
        return

    # --- export subcommand: intercept before scan argparse (Phase 103 SIEM-01/02) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "export":
        from quirk.cli.export_cmd import run_export
        run_export(_sys.argv[2:])
        return

    # --- ticket subcommand: intercept before scan argparse (Phase 104 TICKET-01) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "ticket":
        from quirk.cli.ticket_cmd import run_ticket
        run_ticket(_sys.argv[2:])
        return

    # --- sensor subcommand: intercept before scan argparse (Phase 108 SENSOR-01/02/03/04) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "sensor":
        from quirk.cli.sensor_cmd import run_sensor
        run_sensor(_sys.argv[2:])
        return

    # --- console subcommand: intercept before scan argparse (Phase 108 SENSOR-04) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "console":
        from quirk.cli.console_cmd import run_console
        run_console(_sys.argv[2:])
        return

    # --- errors subcommand: intercept before scan argparse (Phase 68 UX-01) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "errors":
        from quirk.cli.errors_cmd import run_errors
        run_errors(_sys.argv[2:])
        return

    # --- db subcommand: intercept before scan argparse (Phase 85-01 LAUNCH-04) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "db":
        db_parser = argparse.ArgumentParser(
            prog="quirk db",
            description="Database maintenance subcommands",
        )
        db_sub = db_parser.add_subparsers(dest="action", required=True)
        migrate_parser = db_sub.add_parser(
            "migrate",
            help="Additive-only schema migration: brings an existing quirk.db current",
            description=(
                "Idempotent, additive-only schema migration. Reports each "
                "additive column as 'added' or 'already-present'. Never drops, "
                "renames, or retypes columns. Exits 0 on success."
            ),
        )
        migrate_parser.add_argument(
            "--db",
            dest="db_path",
            default=None,
            help=(
                "Path to quirk.db. Defaults to cfg.output.db_path from --config "
                "if provided, otherwise ./quirk.db."
            ),
        )
        migrate_parser.add_argument(
            "--config",
            default=None,
            help="Path to quirk.yaml (used to resolve --db default).",
        )
        migrate_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be added without writing.",
        )
        db_args = db_parser.parse_args(_sys.argv[2:])
        if db_args.action == "migrate":
            from quirk.db import get_engine, run_additive_migration

            db_path = db_args.db_path or _resolve_db_path(db_args)
            if not db_args.dry_run:
                # Ensure file + base tables exist before introspecting —
                # init_db is itself idempotent and only adds (never destroys).
                init_db(db_path)
            elif not os.path.exists(db_path):
                # Dry-run against a non-existent DB has no schema to report on.
                print(
                    f"error: --dry-run requires an existing database at {db_path}",
                    file=_sys.stderr,
                )
                _sys.exit(2)
            engine = get_engine(db_path)
            results = run_additive_migration(engine, dry_run=db_args.dry_run)
            for r in results:
                print(f"{r.table}.{r.column}: {r.status}")
            added = sum(1 for r in results if r.status == "added")
            present = sum(1 for r in results if r.status == "already-present")
            footer = f"Summary: {added} added, {present} already-present, {len(results)} total"
            if db_args.dry_run:
                footer += " (dry-run; no changes written)"
            print(footer)
            return

    parser = argparse.ArgumentParser(description="QU.I.R.K. -- Quantum Infrastructure Readiness Kit")
    parser.add_argument("--version", action="version", version=f"QU.I.R.K. v{__version__}")
    parser.add_argument("--quiet", action="store_true", default=False, help="Suppress banner and decorative output")
    parser.add_argument("--config", help="Path to config.yaml (skip prompts)")
    parser.add_argument(
        "--targets-file",
        help=(
            "Path to file of targets (one per line, '#' comments). "
            "Replaces config targets entirely (does NOT merge). Phase 47 / D-03."
        ),
    )  # D-03
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

    # Phase 67 RESUME-01: checkpoint resume flags
    parser.add_argument(
        "--resume-scan-id",
        default=None,
        metavar="SCAN_RUN_ID",
        help="Resume an interrupted scan from its last completed stage. "
             "Use --list-resumable to find valid SCAN_RUN_IDs.",
    )
    parser.add_argument(
        "--list-resumable",
        action="store_true",
        default=False,
        help="List interrupted scans that can be resumed with --resume-scan-id.",
    )

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

    # Phase 57 / D-04: security hardening opt-outs.
    # These flags can only flip cfg.security.* False -> True; an absent flag
    # never overrides a True value loaded from YAML.
    parser.add_argument(
        "--allow-internal-targets",
        action="store_true", default=False,
        help=(
            "Permit SAML/broker fetches to RFC1918, loopback, and link-local IPs. "
            "Cloud metadata IPs (169.254.169.254, fd00:ec2::254) remain blocked. "
            "Emits HIGH advisory per affected target. Phase 57 / CR-04."
        ),
    )
    parser.add_argument(
        "--allow-cleartext-broker-probe",
        action="store_true", default=False,
        help=(
            "Permit broker management API probes over HTTP (no TLS) and Redis "
            "ssl_cert_reqs=none. Emits HIGH advisory per affected target. "
            "Phase 57 / CR-06."
        ),
    )
    parser.add_argument(
        "--allow-insecure-jwks",
        action="store_true", default=False,
        help=(
            "Disable TLS certificate verification for JWKS fetches. "
            "Emits HIGH advisory per affected target. Phase 57 / CR-01."
        ),
    )
    parser.add_argument(
        "--job-id",
        default=None,
        help="Dashboard job ID for progress reporting (Phase 65). No-op if absent.",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Explicit SQLite path for job progress writes (Phase 65). Required when --job-id is set.",
    )

    # Phase 93 / AUTH-01: authenticated scan flags.
    # SECURITY MODEL — never pass secrets directly on the command line (avoids argv/ps/history leakage).
    # Instead, pass a REFERENCE to the secret:
    #   Bare flag (no value):  triggers an interactive getpass prompt (recommended)
    #   ENVVAR_NAME:           reads the named env var and deletes it (prevents subprocess inheritance)
    #   @/path/to/file:        reads the first line of the file (path-traversal guard applied)
    #
    # Only one --auth-* flag may be active per run (first provided wins).
    _auth_group = parser.add_argument_group(
        "Authenticated scanning (Phase 93 / AUTH-01)",
        description=(
            "Attach credentials to JWT/API scanner requests. "
            "Always supply a REFERENCE (env var name / @file / bare flag for prompt) "
            "— never the secret value itself (avoids argv/ps/history leakage). "
            "Credentials are ephemeral: buffer is zeroed in a finally block covering "
            "the full scan body. Authenticated scans cannot be scheduled (QRK-SCHED-AUTH-001)."
        ),
    )
    _auth_group.add_argument(
        "--auth-bearer",
        dest="auth_bearer",
        nargs="?",
        const="PROMPT",
        default=None,
        metavar="REF",
        help=(
            "Bearer token for JWT/API scanner. "
            "Bare flag triggers getpass prompt; or supply ENVVAR_NAME or @/path/to/token."
        ),
    )
    _auth_group.add_argument(
        "--auth-api-key",
        dest="auth_api_key",
        nargs="?",
        const="PROMPT",
        default=None,
        metavar="REF",
        help=(
            "API key sent as X-Api-Key header. "
            "Bare flag triggers getpass prompt; or supply ENVVAR_NAME or @/path/to/key."
        ),
    )
    _auth_group.add_argument(
        "--auth-api-key-query",
        dest="auth_api_key_query",
        nargs="?",
        const="PROMPT",
        default=None,
        metavar="REF",
        help=(
            "API key appended to the JWKS/endpoint fetch URL as a query parameter "
            "(default param name: api_key). Never sent as a header (D-03). "
            "Bare flag triggers getpass prompt; or supply ENVVAR_NAME or @/path/to/key."
        ),
    )
    _auth_group.add_argument(
        "--auth-basic",
        dest="auth_basic",
        nargs="?",
        const="PROMPT",
        default=None,
        metavar="REF",
        help=(
            "HTTP Basic credentials (base64-encoded user:pass). "
            "Bare flag triggers getpass prompt; or supply ENVVAR_NAME or @/path/to/creds."
        ),
    )

    # Phase 94 SPEC-01/02: OpenAPI spec source flag (local file path or scope-gated URL)
    parser.add_argument(
        "--openapi-spec",
        dest="openapi_spec",
        default=None,
        metavar="FILE_OR_URL",
        help=(
            "Path to a local OpenAPI/Swagger spec file, or an HTTP(S) URL within the "
            "configured scan targets (SPEC-02 scope gate enforced before any fetch). "
            "Emits OpenAPI CryptoEndpoint rows for security schemes, plaintext servers, "
            "and unauthenticated endpoints. Phase 94 SPEC-01/02/03."
        ),
    )
    # Phase 95 CSIGN-01: code-signing certificate inventory flag
    parser.add_argument(
        "--inventory-code-signing",
        dest="inventory_code_signing",
        action="store_true",
        default=False,
        help=(
            "Inventory code-signing certificates from LDAP userCertificate attributes "
            "and TLS endpoint EKU checks (CSIGN-01). Requires codesign_targets in "
            "connectors config for LDAP discovery."
        ),
    )

    # Phase 96 FUZZ-01/02/03/04: active REST crypto-posture fuzzing flags
    parser.add_argument(
        "--fuzz",
        dest="fuzz",
        action="store_true",
        default=False,
        help=(
            "Enable active REST crypto-posture fuzzing of discovered OpenAPI endpoints "
            "(FUZZ-01). Requires --openapi-spec. Presents an interactive CONFIRM gate "
            "before any request is sent; hard-aborts in non-TTY/CI environments (FUZZ-03). "
            "Schemathesis [api] extra must be installed."
        ),
    )
    parser.add_argument(
        "--fuzz-jwt-alg-confusion",
        dest="fuzz_jwt_alg_confusion",
        action="store_true",
        default=False,
        help=(
            "Enable JWT RS256→HS256 alg-confusion probe during REST fuzzing (FUZZ-04). "
            "Requires --fuzz. Attempts to forge a HS256 token using the target's RS256 "
            "public key and reports CRITICAL if the server accepts it."
        ),
    )
    parser.add_argument(
        "--fuzz-budget",
        dest="fuzz_budget",
        type=int,
        default=50,
        metavar="N",
        help=(
            "Maximum number of HTTP requests dispatched during REST fuzzing "
            "(FUZZ-02). Default: 50. Hard maximum: 500."
        ),
    )

    args = parser.parse_args()

    # Phase 67 RESUME-01: --list-resumable exits after printing table
    if args.list_resumable:
        _handle_list_resumable(args)
        sys.exit(0)

    # Phase 65: populate module-level job report dict so _run_main_with_job_guard
    # can write mark_job_failed on uncaught exceptions after argparse completes.
    if args.job_id and args.db_path:
        _job_report["job_id"] = args.job_id
        _job_report["db_path"] = args.db_path

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

    # Phase 47 / D-03: --targets-file REPLACES cfg.targets.fqdns + cidrs (does NOT merge)
    if getattr(args, "targets_file", None):
        apply_targets_file_override(cfg, args.targets_file)  # D-03

    # Phase 57 / D-04: CLI flags override YAML security block per-run (opt-in only, never opt-out).
    apply_security_cli_overrides(cfg, args)

    # Phase 47 / D-09: reflect --discovery flag onto cfg.connectors.enable_nmap for
    # --config / CLI mode. In interactive mode the wizard already set enable_nmap via
    # interactive_config(); overwriting here would silently discard the user's y/N answer.
    if used_config_file:
        setattr(cfg.connectors, "enable_nmap", args.discovery == "nmap")  # D-09

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

    # Phase 94 SPEC-01/02: --openapi-spec CLI flag overrides cfg.scan.openapi_spec_path
    if getattr(args, "openapi_spec", None):
        if hasattr(cfg, "scan") and cfg.scan is not None:
            cfg.scan.openapi_spec_path = args.openapi_spec

    # Phase 93 / AUTH-01: build CredentialContext after config load + security overrides.
    # Lazy import prevents circular deps (D-14: credentials.py has zero scanner imports).
    # cred_ctx is built when either enable_authenticated_mode is set in config OR when
    # at least one --auth-* CLI flag is present.
    _any_auth_flag = any([
        getattr(args, "auth_bearer", None) is not None,
        getattr(args, "auth_api_key", None) is not None,
        getattr(args, "auth_api_key_query", None) is not None,
        getattr(args, "auth_basic", None) is not None,
    ])
    cred_ctx = None
    if cfg.connectors.enable_authenticated_mode or _any_auth_flag:
        from quirk.auth.credentials import CredentialContext
        cred_ctx = CredentialContext.from_cli(
            bearer=getattr(args, "auth_bearer", None),
            api_key=getattr(args, "auth_api_key", None),
            api_key_query=getattr(args, "auth_api_key_query", None),
            basic=getattr(args, "auth_basic", None),
        )
    # Phase 93 / AUTH-01: store cred_ctx in module-level _job_report so
    # _run_main_with_job_guard's finally block can zero the buffer on BaseException paths.
    _job_report["cred_ctx"] = cred_ctx

    init_db(cfg.output.db_path)

    # Phase 65: scan_run_id is the started_utc timestamp (unique per scan invocation).
    # Used by mark_job_completed to associate the completed ScanJob with this scan run.
    scan_run_id: Optional[str] = run_stats["started_utc"]

    # Phase 67 RESUME-01: resume from checkpoint if --resume-scan-id provided
    _resume_scan_id = getattr(args, "resume_scan_id", None)
    _completed_stages: set = set()
    _resumed_endpoints: list = []

    if _resume_scan_id:
        # T-67-04-01: validate ISO timestamp format before using as DB filter value.
        # fromisoformat() raises ValueError on invalid input; caught below → start fresh.
        try:
            from datetime import datetime as _dt_validate
            _dt_validate.fromisoformat(_resume_scan_id)
        except ValueError:
            logger.error(f"--resume-scan-id '{_resume_scan_id}' is not a valid ISO timestamp. Starting fresh scan.")
            _resume_scan_id = None

    if _resume_scan_id:
        scan_run_id = _resume_scan_id  # override: use the original scan's run_id
        run_stats["started_utc"] = scan_run_id  # keep consistent

        try:
            with get_session(cfg.output.db_path) as _db:
                from quirk.models import ScanCheckpoint as _SC, CryptoEndpoint as _CE
                from datetime import datetime as _dt, timezone as _tz, timedelta as _td

                # Load completed stages
                _cps = (
                    _db.query(_SC)
                    .filter(
                        _SC.scan_run_id == scan_run_id,
                        _SC.status.in_(["completed", "partial"]),
                    )
                    .all()
                )
                _completed_stages = {cp.stage for cp in _cps}

                # Stale checkpoint warning (72h threshold)
                if _cps:
                    _last_cp = max(_cps, key=lambda c: c.completed_at or _dt.min)
                    if _last_cp.completed_at:
                        _age = _dt.now(_tz.utc).replace(tzinfo=None) - _last_cp.completed_at
                        _age_hours = int(_age.total_seconds() // 3600)
                        if _age_hours > 72:
                            print(
                                f"[warn] scan checkpoint for {scan_run_id} is {_age_hours}h old"
                                " — verify targets are still valid before resuming.",
                                file=sys.stderr,
                            )

                # Load existing endpoints for this scan_run_id (best-effort; used to
                # populate stage endpoint lists when skipping completed stages).
                # CR-01: strip tz offset so the filter matches tz-naive scanned_at
                # values stored in SQLite (stored via .replace(tzinfo=None) at
                # persist time — tz-aware strings fail SQLite string comparison).
                _target_ts = _dt.fromisoformat(scan_run_id).replace(tzinfo=None)
                _resumed_endpoints = (
                    _db.query(_CE)
                    .filter(
                        _CE.scanned_at >= _target_ts,
                        _CE.scanned_at < _target_ts + _td(seconds=1),
                    )
                    .all()
                )
                logger.info(
                    f"Resuming scan {scan_run_id}: {len(_completed_stages)} stages complete, "
                    f"{len(_resumed_endpoints)} endpoints loaded"
                )
        except Exception as exc:
            logger.error(f"Failed to load resume state: {exc!r}. Starting fresh.")
            _completed_stages = set()
            _resumed_endpoints = []

    limiter = TokenBucket(args.rate_limit, capacity=max(1.0, args.rate_limit)) if args.rate_limit and args.rate_limit > 0 else None

    # ==============================
    # Discovery targets
    # ==============================
    if args.job_id and args.db_path:
        update_job_stage(args.db_path, args.job_id, "discovery")
    targets: List[Tuple[str, int]] = []

    if getattr(cfg.connectors, "enable_nmap", False):
        nmap_targets = _build_nmap_target_list(cfg)
        if not nmap_targets:
            logger.info("⚠️ No CIDRs/FQDNs/IPs provided for Nmap discovery. Add targets and re-run.")
            mark_job_completed(args.db_path, args.job_id, scan_run_id)
            return

        # D-08: check if nmap binary is available; fall back to CONSULTING_TLS_PORTS if not.
        nmap_binary_available = is_extra_available("nmap")
        # D-11: use post-config resolved port list; select_nmap_port_list handles fallback.
        ports_for_nmap = sorted(set(select_nmap_port_list(cfg, nmap_binary_available) + [22, 80, 8080, 8000]))  # D-08/D-11
        extra_args = args.nmap_extra_args.strip()

        # D-10/D-11/D-12: TTY-aware probe-budget guard (inserted Task 3)
        from quirk.util.targets import maybe_confirm_probe_budget
        if not maybe_confirm_probe_budget(
            targets=nmap_targets,
            ports=ports_for_nmap,
            threshold=10_000,  # D-12: threshold locked to 10,000 by roadmap success criterion #5; not configurable
            is_tty=sys.stdin.isatty(),  # stdin.isatty(): correct check for "can user provide input"
        ):
            logger.info("Aborted by user — projected probe count exceeded threshold.")
            mark_job_failed(args.db_path, args.job_id, "Scan aborted: projected probe count exceeded the 10,000 limit. Reduce scope and try again.")
            return

        d_key = f"discovery-{scope_hash(cfg, 'nmap', nmap_extra_args=extra_args, ports=ports_for_nmap)}"
        cached = load_cache(cfg.output.directory, d_key, args.cache_ttl_hours) if args.cache and args.resume and not args.force_discovery else None

        with _phase_timer(run_stats, "discovery"):
            if cached:
                logger.stamp(f"♻️ Using cached discovery results ({d_key})")
                targets = serial_to_targets(cached.get("targets", []))
            elif not nmap_binary_available:
                # D-08: nmap binary absent — advisory already emitted by probe_missing_extras;
                # fall back to builtin discovery using CONSULTING_TLS_PORTS.
                logger.info(
                    "⚠️ nmap binary not found — falling back to builtin discovery "
                    "(consulting-tls port list). Install nmap and ensure it is in PATH."
                )
                targets = expand_targets(cfg)
                targets = _filter_excludes(targets, cfg.targets.exclude_ips or [])
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
            mark_job_completed(args.db_path, args.job_id, scan_run_id)
            return

        logger.stamp(f"Using Nmap-discovered targets only: {len(targets)} endpoint(s)")

    else:
        with _phase_timer(run_stats, "discovery"):
            targets = expand_targets(cfg)
        if not targets:
            logger.info("⚠️ No targets provided. Add CIDRs/FQDNs/IPs and re-run.")
            mark_job_completed(args.db_path, args.job_id, scan_run_id)
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
    # Phase 41 / D-12 + D-14: scanner-phase failure surface — both missing-extra
    # advisory rows (category='missing_extra') and BaseException-captured rows
    # (category='exception') flow through this list and merge into the main
    # endpoints list before risk_engine / db_persist / write_reports.
    error_endpoints: List[CryptoEndpoint] = []
    # Phase 45 / D-08: centralized optional-extra probe. For each enabled scanner
    # whose optional extra is unavailable, emit one ADVISORY CryptoEndpoint into
    # error_endpoints. Phase 41 inline calls at lines ~782 (email) and ~827 (broker)
    # are LEFT IN PLACE per D-11 — the registry intentionally omits motion to avoid
    # double-emitting for those two scanners. See .planning/phases/45-install-day-ux/.
    from quirk.util.optional_extra import probe_missing_extras
    probe_missing_extras(cfg, error_endpoints)

    # Phase 96 FUZZ-01: emit advisory when --fuzz is set but schemathesis [api] extra is absent.
    if getattr(args, "fuzz", False) and not is_extra_available("schemathesis"):
        _emit_missing_extra_advisory("rest_fuzzer", "api", error_endpoints)

    tls_targets: List[Tuple[str, int]] = []
    ssh_targets: List[Tuple[str, int]] = []
    classified_details: Dict[Tuple[str, int], str] = {}

    # Phase 67 RESUME-01: if inventory stage was completed in a prior run, restore
    # inventory_endpoints, tls_targets, and ssh_targets from the DB snapshot.
    if _stage_completed(_completed_stages, "inventory"):
        _inv_protocols = ("CLOSED", "HTTP", "UNKNOWN", "TCP", "UDP", "FINGERPRINT", "NMAP", "HOST")
        inventory_endpoints = [
            e for e in _resumed_endpoints
            if getattr(e, "protocol", "") in _inv_protocols
        ]
        # Reconstruct tls_targets and ssh_targets from resumed endpoints (best-effort)
        tls_targets = [
            (getattr(e, "host", ""), int(getattr(e, "port", 0) or 0))
            for e in _resumed_endpoints
            if (getattr(e, "protocol", "") or "").startswith("TLS")
               or (getattr(e, "protocol", "") or "") == "HTTPS"
        ]
        ssh_targets = [
            (getattr(e, "host", ""), int(getattr(e, "port", 0) or 0))
            for e in _resumed_endpoints
            if getattr(e, "protocol", "") == "SSH"
        ]
        logger.info(
            f"Resuming: skipping inventory/fingerprint stage "
            f"({len(inventory_endpoints)} inventory, {len(tls_targets)} tls, {len(ssh_targets)} ssh from DB)"
        )
    else:
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
    run_stats.setdefault("partial_failures", [])   # Phase 67 RESUME-02

    logger.stamp(f"TLS candidates: {len(tls_targets)} | SSH candidates: {len(ssh_targets)} | Other inventory: {len(inventory_endpoints)}")

    # Phase 67 RESUME-01: persist inventory before first scanner stage
    _flush_stage_endpoints(cfg.output.db_path, inventory_endpoints)
    if args.db_path:
        write_scan_checkpoint(
            args.db_path, scan_run_id, "inventory", "completed",
            endpoint_count=len(inventory_endpoints),
        )

    # ==============================
    # TLS scan phase (phase-tuned)
    # ==============================
    _err_before_tls = len(error_endpoints)  # Phase 67 RESUME-02
    if args.job_id and args.db_path:
        update_job_stage(args.db_path, args.job_id, "tls")
    # Phase 41 / D-08: BACK-45 dissolved. The TLS scanner now reads
    # cfg.scan.timeouts.tls_seconds and cfg.scan.tls_concurrency directly — no
    # more cfg.scan mutate-and-restore pattern around the scan call.
    # Phase 41 / D-14: TLS phase runs under _wrapped_phase BaseException protection.
    # Phase 67 RESUME-01: skip if already completed in a prior run.
    if _stage_completed(_completed_stages, "tls"):
        tls_endpoints = [
            e for e in _resumed_endpoints
            if (getattr(e, "protocol", "") or "").startswith("TLS")
               or getattr(e, "protocol", "") in ("HTTPS",)
        ]
        logger.info(f"Resuming: skipping tls stage ({len(tls_endpoints)} endpoints from DB)")
    else:
        def _run_tls_phase():
            if not tls_targets:
                return []
            eps = scan_tls_targets(
                cfg,
                tls_targets,
                logger=logger,
                progress_cb=None,
            )
            for ep in eps:
                key = (getattr(ep, "host", ""), int(getattr(ep, "port", 0)))
                ep.service_detail = classified_details.get(key, "")
            return eps
        tls_endpoints = _wrapped_phase(
            run_stats, "tls_scanning", "tls_scanner",
            _run_tls_phase, error_endpoints, logger,
        ) or []
        _flush_stage_endpoints(cfg.output.db_path, tls_endpoints)   # Phase 67 RESUME-01
        _tls_pf = _collect_stage_partial_failures(run_stats, "tls", error_endpoints, _err_before_tls)
        if args.db_path:
            write_scan_checkpoint(args.db_path, scan_run_id, "tls",
                status="partial" if _tls_pf else "completed",
                endpoint_count=len(tls_endpoints), partial_failure=bool(_tls_pf),
                error_summary=_tls_pf or None)

    # ==============================
    # SSH scan phase (phase-tuned)
    # ==============================
    _err_before_ssh = len(error_endpoints)  # Phase 67 RESUME-02
    if args.job_id and args.db_path:
        update_job_stage(args.db_path, args.job_id, "ssh")
    # Phase 41 / D-08: BACK-45 dissolved for SSH as well. The SSH scanner reads
    # cfg.scan.timeouts.ssh_seconds and cfg.scan.ssh_concurrency directly.
    # Phase 41 / D-14: SSH phase runs under _wrapped_phase BaseException protection.
    # Phase 67 RESUME-01: skip if already completed in a prior run.
    if _stage_completed(_completed_stages, "ssh"):
        ssh_endpoints = [
            e for e in _resumed_endpoints
            if getattr(e, "protocol", "") == "SSH"
        ]
        logger.info(f"Resuming: skipping ssh stage ({len(ssh_endpoints)} endpoints from DB)")
    else:
        def _run_ssh_phase():
            if not ssh_targets:
                return []
            eps = scan_ssh_targets(
                cfg,
                ssh_targets,
                logger=logger,
                progress_cb=None,
            )
            for ep in eps:
                key = (getattr(ep, "host", ""), int(getattr(ep, "port", 0)))
                ep.service_detail = classified_details.get(key, "")
            return eps
        ssh_endpoints = _wrapped_phase(
            run_stats, "ssh_scanning", "ssh_scanner",
            _run_ssh_phase, error_endpoints, logger,
        ) or []
        _flush_stage_endpoints(cfg.output.db_path, ssh_endpoints)   # Phase 67 RESUME-01
        _ssh_pf = _collect_stage_partial_failures(run_stats, "ssh", error_endpoints, _err_before_ssh)
        if args.db_path:
            write_scan_checkpoint(args.db_path, scan_run_id, "ssh",
                status="partial" if _ssh_pf else "completed",
                endpoint_count=len(ssh_endpoints), partial_failure=bool(_ssh_pf),
                error_summary=_ssh_pf or None)

    # ==============================
    # PQC-hybrid probe phase (Phase 90 PQC-02, D-01)
    # Runs as a dedicated phase — explicitly NOT inside _run_tls_phase.
    # sslyze's bundled OpenSSL cannot handshake against the hybrid endpoint;
    # a raw openssl s_client subprocess probe is the only viable path (D-01).
    # ==============================
    def _run_pqc_phase():
        from quirk.scanner.pqc_probe import probe_pqc_hybrid, host_supports_mlkem
        if not tls_targets:
            return []
        pqc_eps = []
        capability_ok = host_supports_mlkem()
        for _host, _port in tls_targets:
            result = probe_pqc_hybrid(_host, _port, timeout=8)
            if result["detected"]:
                # Genuine component path: TLS endpoint with the negotiated PQC group.
                # The service_detail sentinel "pqc-hybrid-detected" triggers D-05 counter
                # in build_evidence_summary; the negotiated group drives CBOM classification.
                ep = CryptoEndpoint(
                    host=_host,
                    port=int(_port),
                    protocol="TLS",
                    service_detail=f"pqc-hybrid-detected|group=X25519MLKEM768",
                    tls_version="TLSv1.3",
                    cipher_suite="X25519MLKEM768",
                )
                pqc_eps.append(ep)
                logger.info(
                    "PQC probe: X25519MLKEM768 detected on %s:%s (genuine component)",
                    _host, _port,
                )
            elif not capability_ok:
                # Advisory-fallback path: host OpenSSL lacks ML-KEM support (D-01 graceful
                # degradation).  Emit a scoped ADVISORY documenting the limitation.  The
                # "pqc-hybrid-detected" sentinel still increments pqc_hybrid_endpoint_count
                # (D-05) so PQC-03 scoring works on old-OpenSSL hosts.
                ep = CryptoEndpoint(
                    host=_host,
                    port=int(_port),
                    protocol="ADVISORY",
                    scan_error=(
                        "PQC-hybrid detection requires host OpenSSL >= 3.5 / OQS-compiled "
                        "tooling (X25519MLKEM768 / NamedGroup 4588). "
                        "The target may be a PQC-hybrid server but confirmation is unavailable "
                        "on this host. Upgrade to OpenSSL >= 3.5 for genuine detection."
                    ),
                    scan_error_category="coverage_gap",
                    service_detail="pqc-hybrid-detected|advisory=openssl-too-old",
                )
                pqc_eps.append(ep)
                logger.info(
                    "PQC probe: advisory fallback for %s:%s (host OpenSSL lacks ML-KEM)",
                    _host, _port,
                )
        return pqc_eps

    pqc_endpoints = _wrapped_phase(
        run_stats, "pqc_probe", "pqc_probe",
        _run_pqc_phase, error_endpoints, logger,
    ) or []

    # ==============================
    # JWT scan phase
    # ==============================
    _err_before_api = len(error_endpoints)  # Phase 67 RESUME-02
    if args.job_id and args.db_path:
        update_job_stage(args.db_path, args.job_id, "api")
    # Phase 67 RESUME-01: skip api stage if already completed in a prior run.
    _api_protocols = ("JWT", "CONTAINER", "SOURCE", "ADVISORY", "OPENAPI")
    if _stage_completed(_completed_stages, "api"):
        jwt_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "JWT"]
        container_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "CONTAINER"]
        source_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "SOURCE"]
        openapi_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "OPENAPI"]
        logger.info(
            f"Resuming: skipping api stage "
            f"({len(jwt_endpoints)} jwt, {len(container_endpoints)} container, "
            f"{len(source_endpoints)} source, {len(openapi_endpoints)} openapi from DB)"
        )
    else:
        def _run_jwt_phase():
            if not (cfg.connectors.enable_jwt and cfg.connectors.jwt_targets):
                return []
            return scan_jwt_targets(
                cfg.connectors.jwt_targets,
                timeout=cfg.scan.timeouts.jwt_seconds,
                logger=logger,
                allow_insecure_jwks=cfg.security.allow_insecure_jwks,
                cred_ctx=cred_ctx,          # Phase 93 / AUTH-01: None when unauthenticated (D-14 closure capture)
            )
        jwt_endpoints = _wrapped_phase(
            run_stats, "jwt_scanning", "jwt_scanner",
            _run_jwt_phase, error_endpoints, logger,
        ) or []

        # ==============================
        # Container scan phase
        # ==============================
        def _run_container_phase():
            if not (cfg.connectors.enable_container and cfg.connectors.container_targets):
                return []
            return scan_container_targets(
                cfg.connectors.container_targets,
                timeout=cfg.scan.timeouts.container_seconds,
                logger=logger,
            )
        container_endpoints = _wrapped_phase(
            run_stats, "container_scanning", "container_scanner",
            _run_container_phase, error_endpoints, logger,
        ) or []

        # ==============================
        # Source code scan phase
        # ==============================
        def _run_source_phase():
            if not (cfg.connectors.enable_source and cfg.connectors.source_targets):
                return []
            return scan_source_targets(
                cfg.connectors.source_targets,
                timeout=cfg.scan.timeouts.source_seconds,
                logger=logger,
            )
        source_endpoints = _wrapped_phase(
            run_stats, "source_scanning", "source_scanner",
            _run_source_phase, error_endpoints, logger,
        ) or []

        # ==============================
        # OpenAPI spec scan phase (Phase 94 SPEC-01/02/03)
        # ==============================
        def _run_openapi_phase():
            _spec_path = getattr(getattr(cfg, "scan", None), "openapi_spec_path", None)
            if not _spec_path:
                return []
            from quirk.scanner.openapi_scanner import scan_openapi_spec, SpecParsingError
            _target_list = []
            if hasattr(cfg, "targets") and cfg.targets is not None:
                _target_list = list(getattr(cfg.targets, "fqdns", []) or [])
            try:
                return scan_openapi_spec(
                    _spec_path,
                    cfg_targets=_target_list,
                    allow_internal=cfg.security.allow_internal_targets,
                )
            except SpecParsingError as exc:
                logger.error(f"OpenAPI spec parse error: {safe_str(exc)}")
                return []
        openapi_endpoints = _wrapped_phase(
            run_stats, "openapi_scanning", "openapi_scanner",
            _run_openapi_phase, error_endpoints, logger,
        ) or []

        # ==============================
        # REST fuzz scan phase (Phase 96 FUZZ-01/02/03/04)
        # ==============================
        def _run_fuzz_phase():
            # Guard: --fuzz must be set and openapi_endpoints must exist (no spec → no fuzz)
            if not getattr(args, "fuzz", False):
                return []
            if not openapi_endpoints:
                return []
            _spec_path = getattr(getattr(cfg, "scan", None), "openapi_spec_path", None)
            if not _spec_path:
                return []
            # Derive base_url from the first configured FQDN (prefer https://)
            _fqdns = []
            if hasattr(cfg, "targets") and cfg.targets is not None:
                _fqdns = list(getattr(cfg.targets, "fqdns", []) or [])
            _base_url = (f"https://{_fqdns[0]}" if _fqdns else "https://localhost")
            # Re-parse spec dict for the fuzzer (same spec already security-validated above)
            from quirk.scanner.openapi_scanner import (
                _load_spec_bytes_from_file,
                _parse_spec_dict,
                SpecParsingError,
            )
            try:
                _raw = _load_spec_bytes_from_file(_spec_path)
                _spec_dict = _parse_spec_dict(_raw)
            except (SpecParsingError, Exception) as exc:
                logger.error(f"REST fuzz: spec re-parse error: {safe_str(exc)}")
                return []
            from quirk.scanner.rest_fuzzer import run_fuzz_scan
            # Single gate call: run_fuzz_scan owns confirm_fuzz_gate internally.
            # The CLI passes prompt_fn=input and is_tty=sys.stdin.isatty() so the
            # user is prompted EXACTLY ONCE (T-96-09 / DOUBLE-PROMPT RESOLUTION).
            return run_fuzz_scan(
                spec_dict=_spec_dict,
                base_url=_base_url,
                cfg=cfg,
                cred_ctx=cred_ctx,
                budget=getattr(args, "fuzz_budget", 50),
                prompt_fn=input,
                is_tty=sys.stdin.isatty(),
                run_alg_confusion=getattr(args, "fuzz_jwt_alg_confusion", False),
            )
        fuzz_endpoints = _wrapped_phase(
            run_stats, "fuzz_scanning", "rest_fuzzer",
            _run_fuzz_phase, error_endpoints, logger,
        ) or []

        _flush_stage_endpoints(cfg.output.db_path, jwt_endpoints + container_endpoints + source_endpoints + openapi_endpoints + fuzz_endpoints)  # Phase 67 RESUME-01
        _api_pf = _collect_stage_partial_failures(run_stats, "api", error_endpoints, _err_before_api)
        if args.db_path:
            write_scan_checkpoint(args.db_path, scan_run_id, "api",
                status="partial" if _api_pf else "completed",
                endpoint_count=len(jwt_endpoints + container_endpoints + source_endpoints + openapi_endpoints + fuzz_endpoints),
                partial_failure=bool(_api_pf), error_summary=_api_pf or None)

    # ==============================
    # AWS cloud connector phase
    # ==============================
    _err_before_identity = len(error_endpoints)  # Phase 67 RESUME-02
    if args.job_id and args.db_path:
        update_job_stage(args.db_path, args.job_id, "identity")
    # ── Shared identity-scan session timestamp (ISSUE-3 fix) ──
    session_start = datetime.now(timezone.utc)
    # Phase 67 RESUME-01: skip identity stage if already completed in a prior run.
    _identity_protocols = ("AWS-KMS", "AZURE-KV", "GCP-KMS", "DB", "DNSSEC", "SAML", "KERBEROS")
    if _stage_completed(_completed_stages, "identity"):
        aws_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "AWS-KMS"]
        azure_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "AZURE-KV"]
        gcp_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "GCP-KMS"]
        db_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "DB"]
        logger.info(
            f"Resuming: skipping identity stage "
            f"({len(aws_endpoints)} aws, {len(azure_endpoints)} azure, "
            f"{len(gcp_endpoints)} gcp, {len(db_endpoints)} db from DB)"
        )
    else:
        def _run_aws_phase():
            if not cfg.connectors.enable_aws:
                return []
            return scan_aws_targets(
                region=cfg.connectors.aws_region,
                profile=cfg.connectors.aws_profile,
                logger=logger,
            )
        aws_endpoints = _wrapped_phase(
            run_stats, "aws_scanning", "aws_connector",
            _run_aws_phase, error_endpoints, logger,
        ) or []

        # ==============================
        # Azure cloud connector phase
        # ==============================
        def _run_azure_phase():
            if not cfg.connectors.enable_azure:
                return []
            return scan_azure_targets(
                subscription_id=cfg.connectors.azure_subscription_id or "",
                keyvault_urls=cfg.connectors.azure_keyvault_urls,
                logger=logger,
            )
        azure_endpoints = _wrapped_phase(
            run_stats, "azure_scanning", "azure_connector",
            _run_azure_phase, error_endpoints, logger,
        ) or []

        # ==============================
        # GCP cloud connector phase
        # ==============================
        def _run_gcp_phase():
            if not cfg.connectors.enable_gcp:
                return []
            return scan_gcp_targets(
                project_id=cfg.connectors.gcp_project_id or "",
                logger=logger,
            )
        gcp_endpoints = _wrapped_phase(
            run_stats, "gcp_scanning", "gcp_connector",
            _run_gcp_phase, error_endpoints, logger,
        ) or []

        # ==============================
        # DB connector phase (PostgreSQL / MySQL) — Phase 27
        # ==============================
        def _run_db_phase():
            if not cfg.connectors.enable_db:
                return []
            from quirk.scanner.db_connector import scan_pg_targets, scan_mysql_targets
            result = []
            if cfg.connectors.pg_targets:
                result.extend(scan_pg_targets(
                    targets=cfg.connectors.pg_targets,
                    user=cfg.connectors.pg_scanner_user,
                    password=cfg.connectors.pg_scanner_password,
                    logger=logger,
                    session_start=session_start,
                    cfg=cfg,
                ))
            if cfg.connectors.mysql_targets:
                result.extend(scan_mysql_targets(
                    targets=cfg.connectors.mysql_targets,
                    user=cfg.connectors.mysql_scanner_user,
                    password=cfg.connectors.mysql_scanner_password,
                    logger=logger,
                    session_start=session_start,
                    cfg=cfg,
                ))
            return result
        db_endpoints = _wrapped_phase(
            run_stats, "db_scanning", "db_connector",
            _run_db_phase, error_endpoints, logger,
        ) or []

        # Phase 67 RESUME-01: flush identity stage endpoints before data_at_rest begins
        # identity = aws + azure + gcp + db (dnssec/saml/kerberos run after data_at_rest in this codebase)
        _identity_eps = aws_endpoints + azure_endpoints + gcp_endpoints + db_endpoints
        _flush_stage_endpoints(cfg.output.db_path, _identity_eps)
        _identity_pf = _collect_stage_partial_failures(run_stats, "identity", error_endpoints, _err_before_identity)
        if args.db_path:
            write_scan_checkpoint(args.db_path, scan_run_id, "identity",
                status="partial" if _identity_pf else "completed",
                endpoint_count=len(_identity_eps), partial_failure=bool(_identity_pf),
                error_summary=_identity_pf or None)

    # ==============================
    # Data-at-rest stage (S3, Blob, K8S, GCS, DNSSEC, SAML, Kerberos, Vault)
    # ==============================
    _err_before_dar = len(error_endpoints)  # Phase 67 RESUME-02
    if args.job_id and args.db_path:
        update_job_stage(args.db_path, args.job_id, "data_at_rest")
    # Phase 67 RESUME-01: skip data_at_rest stage if already completed in a prior run.
    _dar_protocols = ("S3", "AZURE-BLOB", "K8S", "GCS", "VAULT", "DNSSEC", "SAML",
                     "KERBEROS", "SMIME", "ADCS", "CODE_SIGNING")  # Phase 95 CSIGN-01
    if _stage_completed(_completed_stages, "data_at_rest"):
        s3_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "S3"]
        blob_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "AZURE-BLOB"]
        k8s_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "K8S"]
        gcs_storage_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "GCS"]
        dnssec_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "DNSSEC"]
        saml_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "SAML"]
        kerberos_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "KERBEROS"]
        smime_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "SMIME"]
        adcs_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "ADCS"]
        codesign_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "CODE_SIGNING"]  # Phase 95 CSIGN-01
        vault_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "VAULT"]
        logger.info(
            f"Resuming: skipping data_at_rest stage "
            f"({len(s3_endpoints)} s3, {len(blob_endpoints)} blob, {len(k8s_endpoints)} k8s, "
            f"{len(gcs_storage_endpoints)} gcs, {len(dnssec_endpoints)} dnssec, "
            f"{len(saml_endpoints)} saml, {len(kerberos_endpoints)} kerberos, "
            f"{len(smime_endpoints)} smime, {len(adcs_endpoints)} adcs, "
            f"{len(codesign_endpoints)} codesign, "
            f"{len(vault_endpoints)} vault from DB)"
        )
    else:
        # ==============================
        # S3 object storage encryption (Phase 28, STOR-01)
        # ==============================
        def _run_s3_phase():
            if not cfg.connectors.enable_s3:
                return []
            from quirk.scanner.aws_connector import _scan_s3_encryption, BOTO3_AVAILABLE
            if not BOTO3_AVAILABLE:
                logger.v("boto3 not installed — S3 scanning skipped")
                return []
            import boto3
            s3_session = boto3.Session(
                region_name=cfg.connectors.aws_region,
                profile_name=cfg.connectors.aws_profile,
            )
            eps = _scan_s3_encryption(
                session=s3_session,
                logger=logger,
                session_start=session_start,
                endpoint_url=cfg.connectors.aws_endpoint_url or None,
            )
            logger.info(f"S3 scan: {len(eps)} bucket endpoints")
            return eps
        s3_endpoints = _wrapped_phase(
            run_stats, "s3_scanning", "s3_connector",
            _run_s3_phase, error_endpoints, logger,
        ) or []

        # ==============================
        # Azure Blob container encryption (Phase 28, STOR-02)
        # ==============================
        def _run_blob_phase():
            if not cfg.connectors.enable_blob:
                return []
            from quirk.scanner.azure_connector import _scan_blob_encryption, AZURE_AVAILABLE, DefaultAzureCredential
            if not AZURE_AVAILABLE:
                logger.v("azure SDK not installed — Azure Blob scanning skipped")
                return []
            if not (cfg.connectors.azure_subscription_id or "").strip():
                logger.v("azure_subscription_id not set — Azure Blob scanning skipped")
                return []
            eps = _scan_blob_encryption(
                credential=DefaultAzureCredential(),
                subscription_id=cfg.connectors.azure_subscription_id,
                logger=logger,
                session_start=session_start,
            )
            logger.info(f"Azure Blob scan: {len(eps)} container endpoints")
            return eps
        blob_endpoints = _wrapped_phase(
            run_stats, "blob_scanning", "azure_blob_connector",
            _run_blob_phase, error_endpoints, logger,
        ) or []

        # ==============================
        # K8S secrets inspection (Phase 29, K8S-01 / K8S-02 / K8S-03)
        # ==============================
        def _run_k8s_phase():
            if not cfg.connectors.enable_k8s:
                return []
            from quirk.scanner.k8s_connector import scan_k8s_targets
            eps = scan_k8s_targets(
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
                        eps.extend(_scan_eks_encryption(
                            _eks_session, logger, session_start=session_start,
                        ))
                except Exception as exc:
                    logger.v(f"EKS encryption scan unavailable: {exc}")
            logger.info(f"K8S scan: {len(eps)} cluster endpoints")
            return eps
        k8s_endpoints = _wrapped_phase(
            run_stats, "k8s_scanning", "k8s_connector",
            _run_k8s_phase, error_endpoints, logger,
        ) or []

        # ==============================
        # GCS bucket encryption re-use (Phase 28, STOR-03 — zero API call invariant)
        # ==============================
        gcs_storage_endpoints = []
        with _phase_timer(run_stats, "gcs_storage_reuse"):
            gcs_storage_endpoints = _process_gcs_storage_encryption(gcp_endpoints, logger=logger)
            if gcs_storage_endpoints:
                logger.info(f"GCS storage re-use: {len(gcs_storage_endpoints)} derived endpoints")

        # ── DNSSEC scanning ─────────────────────────────────────
        def _run_dnssec_phase():
            if not (cfg.connectors.enable_dnssec and cfg.connectors.dnssec_targets):
                return []
            eps = scan_dnssec_targets(
                targets=cfg.connectors.dnssec_targets,
                timeout=getattr(cfg.connectors, "dnssec_timeout", 10),
                logger=logger,
                session_start=session_start,
                resolver=getattr(cfg.connectors, "dnssec_resolver", None),
            )
            logger.info("DNSSEC scan: %d endpoints from %d targets",
                        len(eps), len(cfg.connectors.dnssec_targets))
            return eps
        dnssec_endpoints = _wrapped_phase(
            run_stats, "dnssec_scanning", "dnssec_scanner",
            _run_dnssec_phase, error_endpoints, logger,
        ) or []

        # ── SAML/OIDC scanning ────────────────────────────────────
        def _run_saml_phase():
            if not (cfg.connectors.enable_saml and cfg.connectors.saml_targets):
                return []
            from quirk.scanner.saml_scanner import scan_saml_targets
            eps = scan_saml_targets(
                targets=cfg.connectors.saml_targets,
                timeout=getattr(cfg.connectors, "saml_timeout", 10),
                logger=logger,
                session_start=session_start,
                allow_internal_targets=cfg.security.allow_internal_targets,
            )
            logger.info("SAML scan: %d endpoints from %d targets",
                        len(eps), len(cfg.connectors.saml_targets))
            return eps
        saml_endpoints = _wrapped_phase(
            run_stats, "saml_scanning", "saml_scanner",
            _run_saml_phase, error_endpoints, logger,
        ) or []

        # ── Kerberos scanning ────────────────────────────────────
        def _run_kerberos_phase():
            if not (cfg.connectors.enable_kerberos and cfg.connectors.kerberos_targets):
                return []
            from quirk.scanner.kerberos_scanner import scan_kerberos_targets
            eps = scan_kerberos_targets(
                targets=cfg.connectors.kerberos_targets,
                timeout=getattr(cfg.connectors, "kerberos_timeout", 10),
                logger=logger,
                session_start=session_start,
            )
            logger.info("Kerberos scan: %d endpoints from %d targets",
                        len(eps), len(cfg.connectors.kerberos_targets))
            return eps
        kerberos_endpoints = _wrapped_phase(
            run_stats, "kerberos_scanning", "kerberos_scanner",
            _run_kerberos_phase, error_endpoints, logger,
        ) or []

        # ── S/MIME LDAP scanning (Phase 79 SMIME-01) ──────────────────
        def _run_smime_phase():
            if not (getattr(cfg.connectors, "enable_smime", False)
                    and getattr(cfg.connectors, "smime_targets", None)):
                return []
            from quirk.scanner.smime_scanner import scan_smime_targets
            eps = scan_smime_targets(
                targets=cfg.connectors.smime_targets,
                timeout=getattr(cfg.connectors, "smime_timeout", 10),
                logger=logger,
                session_start=session_start,
                search_base=getattr(cfg.connectors, "smime_search_base", None),
            )
            logger.info("SMIME scan: %d endpoints from %d targets",
                        len(eps), len(cfg.connectors.smime_targets))
            return eps
        smime_endpoints = _wrapped_phase(
            run_stats, "smime_scanning", "smime_scanner",
            _run_smime_phase, error_endpoints, logger,
        ) or []

        # ── AD CS LDAP scanning (Phase 80 ADCS-01) ────────────────────
        def _run_adcs_phase():
            if not (getattr(cfg.connectors, "enable_adcs", False)
                    and getattr(cfg.connectors, "adcs_targets", None)):
                return []
            from quirk.scanner.adcs_scanner import scan_adcs_targets
            eps = scan_adcs_targets(
                targets=cfg.connectors.adcs_targets,
                timeout=getattr(cfg.connectors, "adcs_timeout", 10),
                logger=logger,
                session_start=session_start,
                search_base=getattr(cfg.connectors, "adcs_search_base", None),
                user=getattr(cfg.connectors, "adcs_user", None),
                password=getattr(cfg.connectors, "adcs_password", None),
            )
            logger.info("ADCS scan: %d endpoints from %d targets",
                        len(eps), len(cfg.connectors.adcs_targets))
            return eps
        adcs_endpoints = _wrapped_phase(
            run_stats, "adcs_scanning", "adcs_scanner",
            _run_adcs_phase, error_endpoints, logger,
        ) or []

        # ── Code-signing certificate inventory (Phase 95 CSIGN-01) ───────────────
        # IMPORTANT: runs AFTER tls_endpoints is populated so the TLS EKU path
        # (scan_codesign_from_tls_endpoints) can operate on already-captured certs.
        def _run_codesign_phase():
            if not getattr(args, "inventory_code_signing", False):
                return []
            from quirk.scanner.codesign_scanner import (
                scan_codesign_from_ldap,
                scan_codesign_from_tls_endpoints,
            )
            ldap_eps = []
            if getattr(cfg.connectors, "codesign_targets", None):
                ldap_eps = scan_codesign_from_ldap(
                    targets=cfg.connectors.codesign_targets,
                    timeout=getattr(cfg.connectors, "codesign_timeout", 10),
                    logger=logger,
                    session_start=session_start,
                    search_base=getattr(cfg.connectors, "codesign_search_base", None),
                )
                logger.info("CODE_SIGNING LDAP scan: %d endpoints from %d targets",
                            len(ldap_eps), len(cfg.connectors.codesign_targets))
            # In-process TLS EKU check — no new network I/O (CSIGN-01 TLS source)
            tls_eps = scan_codesign_from_tls_endpoints(
                tls_endpoints,
                session_start=session_start,
                logger=logger,
            )
            logger.info("CODE_SIGNING TLS-EKU check: %d CODE_SIGNING endpoints from %d TLS endpoints",
                        len(tls_eps), len(tls_endpoints))
            return ldap_eps + tls_eps
        codesign_endpoints = _wrapped_phase(
            run_stats, "codesign_scanning", "codesign_scanner",
            _run_codesign_phase, error_endpoints, logger,
        ) or []

        # ── Vault scanning (Phase 30, VAULT-01/02/03) ─────────────────────────────
        def _run_vault_phase():
            if not cfg.connectors.enable_vault:
                return []
            from quirk.scanner.vault_connector import (
                scan_vault_targets,
                HVAC_AVAILABLE,
            )
            if not HVAC_AVAILABLE:
                logger.v("hvac not installed -- Vault scanning skipped")
                return []
            if not (cfg.connectors.vault_addr or os.environ.get("VAULT_ADDR")):
                logger.v("vault_addr not set -- Vault scanning skipped")
                return []
            # Phase 72 D-22 / WR-09: connector requires explicit token now (no implicit
            # env fallback inside vault_connector). Source the token here at the caller
            # boundary — config takes precedence; VAULT_TOKEN env is the operator override.
            _vault_token = cfg.connectors.vault_token or os.environ.get("VAULT_TOKEN", "")
            eps = scan_vault_targets(
                vault_addr=(cfg.connectors.vault_addr
                            or os.environ.get("VAULT_ADDR", "")),
                token=_vault_token,
                transit_mount=cfg.connectors.vault_transit_mount or "transit",
                tls_verify=cfg.connectors.vault_tls_verify,
                logger=logger,
                session_start=session_start,
                cfg=cfg,
            )
            logger.info("Vault scan: %d endpoints", len(eps))
            return eps
        vault_endpoints = _wrapped_phase(
            run_stats, "vault_scanning", "vault_connector",
            _run_vault_phase, error_endpoints, logger,
        ) or []

        # Phase 67 RESUME-01: flush data_at_rest stage endpoints before broker_email begins
        _dar_eps = s3_endpoints + blob_endpoints + k8s_endpoints + gcs_storage_endpoints + dnssec_endpoints + saml_endpoints + kerberos_endpoints + smime_endpoints + adcs_endpoints + vault_endpoints
        _flush_stage_endpoints(cfg.output.db_path, _dar_eps)
        _dar_pf = _collect_stage_partial_failures(run_stats, "data_at_rest", error_endpoints, _err_before_dar)
        if args.db_path:
            write_scan_checkpoint(args.db_path, scan_run_id, "data_at_rest",
                status="partial" if _dar_pf else "completed",
                endpoint_count=len(_dar_eps), partial_failure=bool(_dar_pf),
                error_summary=_dar_pf or None)

    # ── Email + Broker stage (Phase 32 + 33) ─────────────────────
    _err_before_broker = len(error_endpoints)  # Phase 67 RESUME-02
    # Phase 67 RESUME-01: skip broker_email stage if already completed in a prior run.
    _broker_email_protocols = ("KAFKA", "AMQP", "AMQPS", "REDIS", "SMTP", "SMTPS",
                                "AMQPS/Azure-ServiceBus", "HTTPS/AWS-SQS", "EMAIL")
    if _stage_completed(_completed_stages, "broker_email"):
        email_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") in ("SMTP", "SMTPS", "EMAIL")]
        kafka_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "KAFKA"]
        rabbit_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") in ("AMQP", "AMQPS", "AMQPS/Azure-ServiceBus", "HTTPS/AWS-SQS")]
        redis_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "REDIS"]
        all_broker_eps = kafka_endpoints + rabbit_endpoints + redis_endpoints
        logger.info(
            f"Resuming: skipping broker_email stage "
            f"({len(email_endpoints)} email, {len(kafka_endpoints)} kafka, "
            f"{len(rabbit_endpoints)} rabbit, {len(redis_endpoints)} redis from DB)"
        )
    else:
        email_endpoints = []
        # Phase 41 / D-12: probe optional-extra availability and emit advisory if missing.
        if cfg.connectors.enable_email:
            from quirk.scanner import email_scanner as _email_mod
            if not getattr(_email_mod, "SSLYZE_AVAILABLE", True):
                _emit_missing_extra_advisory("email_scanner", "motion", error_endpoints)
                cfg_email_skip = True
            else:
                cfg_email_skip = False
        else:
            cfg_email_skip = True

        # Phase 67 / D-04: email phase now uses _wrapped_phase for uniform error capture.
        # cfg_email_skip and _emit_missing_extra_advisory() call above remain before the
        # _run_email_phase def — correct ordering preserved.
        def _run_email_phase():
            if cfg_email_skip or not cfg.connectors.enable_email:
                return []
            email_hosts = list(dict.fromkeys(h for h, _ in tls_targets))
            if not email_hosts:
                return []
            eps = scan_email_targets(
                hosts=email_hosts,
                timeout=cfg.scan.timeouts.email_seconds,
                logger=logger,
                session_start=session_start,
                motion_concurrency=cfg.scan.motion_concurrency,
            )
            logger.info(f"Email scan: {len(eps)} endpoints from {len(email_hosts)} hosts")
            return eps
        email_endpoints = _wrapped_phase(
            run_stats, "email_scanning", "email_scanner",
            _run_email_phase, error_endpoints, logger,
        ) or []

        # ── Broker TLS scanning (Phase 33) ────────────────────────
        kafka_endpoints = []
        rabbit_endpoints = []
        redis_endpoints = []
        # Phase 41 / D-12: probe optional-extra availability — broker depends on the
        # [motion] extra (sslyze + kafka-python + redis). If sslyze is absent, emit
        # the canonical advisory and skip the phase rather than crashing on import.
        if cfg.connectors.enable_broker:
            from quirk.scanner import broker_scanner as _broker_mod
            if not getattr(_broker_mod, "SSLYZE_AVAILABLE", True):
                _emit_missing_extra_advisory("broker_scanner", "motion", error_endpoints)
                cfg_broker_skip = True
            else:
                cfg_broker_skip = False
        else:
            cfg_broker_skip = True

        def _run_broker_phase():
            if cfg_broker_skip or not cfg.connectors.enable_broker:
                return ([], [], [])
            broker_hosts = list(dict.fromkeys(h for h, _ in tls_targets))
            if not broker_hosts:
                return ([], [], [])
            k = scan_kafka_targets(
                hosts=broker_hosts,
                timeout=cfg.scan.timeouts.broker_seconds,
                profile=scan_profile,
                logger=logger,
                session_start=session_start,
                motion_concurrency=cfg.scan.motion_concurrency,
            )
            r = scan_rabbitmq_targets(
                hosts=broker_hosts,
                azure_namespaces=cfg.connectors.broker_azure_namespaces,
                sqs_regions=cfg.connectors.broker_sqs_regions,
                timeout=cfg.scan.timeouts.broker_seconds,
                logger=logger,
                session_start=session_start,
                security=cfg.security,
                broker_credentials=cfg.broker_credentials,
                motion_concurrency=cfg.scan.motion_concurrency,
            )
            rd = scan_redis_targets(
                hosts=broker_hosts,
                timeout=cfg.scan.timeouts.broker_seconds,
                logger=logger,
                session_start=session_start,
                motion_concurrency=cfg.scan.motion_concurrency,
            )
            logger.info(
                f"Broker scan: kafka={len(k)} rabbit={len(r)} redis={len(rd)}"
            )
            return (k, r, rd)
        _broker_result = _wrapped_phase(
            run_stats, "broker_scanning", "broker_scanner",
            _run_broker_phase, error_endpoints, logger,
        )
        if isinstance(_broker_result, tuple) and len(_broker_result) == 3:
            kafka_endpoints, rabbit_endpoints, redis_endpoints = _broker_result
        # else: BaseException captured — error_endpoints already records the failure.

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

        # Phase 67 RESUME-01: flush broker_email stage endpoints
        _broker_email_eps = email_endpoints + kafka_endpoints + rabbit_endpoints + redis_endpoints
        _flush_stage_endpoints(cfg.output.db_path, _broker_email_eps)
        _broker_pf = _collect_stage_partial_failures(run_stats, "broker_email", error_endpoints, _err_before_broker)
        if args.db_path:
            write_scan_checkpoint(args.db_path, scan_run_id, "broker_email",
                status="partial" if _broker_pf else "completed",
                endpoint_count=len(_broker_email_eps), partial_failure=bool(_broker_pf),
                error_summary=_broker_pf or None)

    # Phase 94 / TOKEN-02: classify the operator-supplied bearer credential into the CBOM.
    # Passive — the JWT header is decoded UNVERIFIED for its declared algorithm only; the
    # raw token never reaches a CryptoEndpoint, the DB, or the CBOM (only the alg string).
    bearer_token_endpoints = []
    if cred_ctx is not None and getattr(cred_ctx, "scheme", None) == "bearer":
        _declared_alg = cred_ctx.bearer_declared_alg()
        if _declared_alg:
            _bt_host = (cfg.targets.fqdns[0] if getattr(cfg, "targets", None)
                        and getattr(cfg.targets, "fqdns", None) else "authenticated-scan")
            bearer_token_endpoints.append(CryptoEndpoint(
                host=_bt_host,
                port=443,
                protocol="BEARER_TOKEN",
                cert_pubkey_alg=_declared_alg,
                service_detail="declared_algorithm (unverified)",
                severity="INFO",
            ))

    endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints
                 + pqc_endpoints                                    # Phase 90 PQC-02
                 + jwt_endpoints + container_endpoints + source_endpoints
                 + openapi_endpoints                                # Phase 94 SPEC-01
                 + bearer_token_endpoints                           # Phase 94 TOKEN-02
                 + aws_endpoints + azure_endpoints + gcp_endpoints
                 + db_endpoints
                 + s3_endpoints + blob_endpoints + gcs_storage_endpoints
                 + k8s_endpoints
                 + dnssec_endpoints + saml_endpoints + kerberos_endpoints
                 + smime_endpoints
                 + adcs_endpoints
                 + codesign_endpoints                              # Phase 95 CSIGN-01
                 + vault_endpoints
                 + email_endpoints
                 + kafka_endpoints + rabbit_endpoints + redis_endpoints
                 # Phase 41 / D-12 + D-14: missing-extra advisory rows and
                 # BaseException-captured rows flow into reports / DB persist.
                 + error_endpoints)

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
        broker_findings = evaluate_broker_endpoints(all_broker_eps)
        if broker_findings:
            findings = (findings or []) + broker_findings
        # Phase 99 CTX-03: code-signing expiry/weak-algo findings (ZERO findings
        # previously — codesign endpoints were collected but never evaluated).
        codesign_findings = evaluate_codesign_endpoints(codesign_endpoints)
        if codesign_findings:
            findings = (findings or []) + codesign_findings

    with _phase_timer(run_stats, "db_persist"):
        with get_session(cfg.output.db_path) as session:
            for ep in endpoints:
                # CR-03: use merge() instead of add() so that detached resumed
                # endpoints (which already have a PK from a prior flush) are
                # UPDATE'd rather than INSERT'd, avoiding IntegrityError on resume.
                session.merge(ep)
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

    if args.job_id and args.db_path:
        update_job_stage(args.db_path, args.job_id, "reports")
    # Phase 67 RESUME-01: if reports stage was completed in a prior run, re-run anyway
    # (reports are cheap and the user wants fresh output files).
    if _stage_completed(_completed_stages, "reports"):
        logger.info("Resuming: reports stage was completed — re-running to regenerate output files.")
    with _phase_timer(run_stats, "reporting"):
        try:
            write_reports(cfg, endpoints, findings, run_stats=run_stats, error_endpoints=error_endpoints)
        except ReportCongruenceError as exc:
            # D-06 fail-closed halt: the executive headline contradicts the findings
            # (e.g. a healthy band alongside a CRITICAL). Surface a clean, actionable
            # message and a non-zero exit instead of an opaque traceback.
            if args.job_id and args.db_path:
                mark_job_failed(args.db_path, args.job_id, f"ReportCongruenceError: {safe_str(exc)}")
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(2)

    # Phase 67 RESUME-01: checkpoint after reports written
    if args.db_path:
        write_scan_checkpoint(args.db_path, scan_run_id, "reports", "completed",
            endpoint_count=len(endpoints))

    # Phase 65: mark scan job completed after all phases succeed.
    if args.job_id and args.db_path:
        mark_job_completed(args.db_path, args.job_id, scan_run_id)

    # Phase 93 / AUTH-01: zeroize credential buffer on normal exit path (best-effort).
    # The BaseException path is covered by _run_main_with_job_guard's finally block,
    # which reads _job_report["cred_ctx"] set below.
    if cred_ctx is not None:
        cred_ctx.close()
        _job_report["cred_ctx"] = None


# Phase 65: module-level dict allows the __main__ exception handler to
# write mark_job_failed without access to main()'s local `args`.
_job_report: Dict[str, Any] = {}


def _run_main_with_job_guard() -> None:
    """Phase 65: run main(); on exception write mark_job_failed if --job-id was set.
    Phase 93 / AUTH-01: finally block ensures credential buffer is zeroed on any
    BaseException path (KeyboardInterrupt, SystemExit, unhandled exceptions).
    """
    try:
        main()
    except Exception as exc:
        job_id = _job_report.get("job_id")
        db_path = _job_report.get("db_path")
        if job_id and db_path:
            # CR-04: scrub before persisting — a credential-bearing exception (e.g. an
            # httpx error carrying ?api_key=<secret>) must not be written to the job row.
            mark_job_failed(db_path, job_id, f"{type(exc).__name__}: {safe_str(exc)}")
        raise
    finally:
        # Phase 93 / AUTH-01: BaseException-safe zeroization.
        # main() already calls cred_ctx.close() on normal exit and sets
        # _job_report["cred_ctx"] = None; this finally handles interrupt/exception paths.
        # D-05: best-effort — Python GC may retain heap copies of the original str.
        _ctx = _job_report.get("cred_ctx")
        if _ctx is not None:
            try:
                _ctx.close()
            except Exception:
                pass
            _job_report["cred_ctx"] = None


if __name__ == "__main__":
    multiprocessing.freeze_support()
    _run_main_with_job_guard()
