"""Phase 65 — /api/jobs router (UI-SCAN-01/02/03).

Two routers:
  - read_router  : require_auth only         (GET)
  - write_router : require_auth + require_csrf (POST, DELETE)

Both are mounted under /api by app.py.

Subprocess dispatch follows the Phase 63 scheduler Popen pattern but
MUST NOT block (Pitfall 2): we return immediately after Popen and let
the spawned run_scan.py update scan_jobs progress via --job-id flag.
"""
from __future__ import annotations

import dataclasses
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from quirk.errors import format_error
from sqlalchemy.orm import Session

from quirk.dashboard.api._timestamp_utils import stamp_utc_iso
from quirk.dashboard.api.deps import get_db, _default_db_path
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf
from quirk.dashboard.api.schemas import ScanSubmitRequest, JobStatusResponse
from quirk.models import ScanJob

logger = logging.getLogger(__name__)

read_router = APIRouter(dependencies=[Depends(require_auth)])
write_router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])

_STAGE_ORDER = [
    "discovery", "tls", "ssh", "api", "identity", "data_at_rest", "reports",
]
_STAGE_TOTAL = 7


def _utcnow_naive() -> datetime:
    """Tz-naive UTC datetime — matches schedules.py convention (Pitfall 6)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def build_job_config_dict(
    output_dir: Path,
    targets: str,
    db_path: str,
    calibration: str,
    allow_internal_targets: bool = False,
    port_scope: str = "top1000",
    custom_ports: Optional[str] = None,
    *,
    connectors_overlay: Optional[Dict[str, bool]] = None,
) -> dict:
    """Build the dict a dashboard-dispatched scan's job config YAML is dumped from.

    run_scan.py has no --target CLI flag; all target/output config must live
    in a YAML file passed via --config. Targets are classified as cidrs (if
    they contain '/') or fqdns (hostnames and bare IPs).

    Phase 121: port_scope controls the scan.ports_tls (common/custom) or
    scan.nmap_port_scope (top1000/all) written to the job YAML. ValueError
    from parse_port_spec propagates to the caller (create_job wraps it as 422).

    Phase 121 follow-up: a Custom port spec means "scan exactly these ports".
    The email/broker connectors carry their own fixed service-port tables
    (email_scanner.EMAIL_PORTS etc.) that the standard/deep profiles auto-enable
    independently of ports_tls, so a custom scan leaks ~7 email ports the user
    never asked for. For custom scope only, write an explicit connectors block
    disabling them. Because config loading records these keys in
    ConnectorsCfg._user_set_fields, apply_profile() honors the explicit False
    and will NOT re-enable them under the deep profile (Phase 72 D-02/WR-11).
    Common scope is intentionally left alone — CONSULTING_TLS_PORTS already
    curates in the implicit-TLS email ports (993/995/465), so its connector
    coverage is by design, not a leak.

    Phase 192 / PARITY-01: extracted out of `_write_job_config` so
    `quirk/dashboard/api/config_preview.py`'s `resolve_effective_config` can
    build the exact same dict a real submission would dump, without writing a
    file itself.

    Phase 193 / PARITY-02 / D-13 / D-14: `connectors_overlay` is a delta-only
    keyword-only parameter — only the connector flags the operator explicitly
    touched are written into `config["connectors"]`. It is merged LAST, after
    the Phase 121 custom-port-scope suppression below, so an explicit operator
    toggle wins over that suppression (D-14). This is the only path connector
    selections may reach the job YAML through — never a post-load `setattr` on
    a loaded `ConnectorsCfg` (Phase 75 D-13's replaced anti-pattern).
    """
    from quirk.config import _KNOWN_CONNECTOR_KEYS  # single allowlist source of truth
    from quirk.interactive import CONSULTING_TLS_PORTS  # importable side-effect-free
    from quirk.util.port_spec import parse_port_spec

    target_list = [t.strip() for t in targets.split(",") if t.strip()]
    fqdns = [t for t in target_list if "/" not in t]
    cidrs = [t for t in target_list if "/" in t]

    # Phase 121: resolve scan block from port_scope. connectors_block stays None
    # for every scope except custom (explicit fixed-port-connector suppression).
    connectors_block: Optional[dict] = None
    if port_scope == "common":
        scan_block: dict = {
            "concurrency": 100,
            "ports_tls": list(CONSULTING_TLS_PORTS),
            "include_sni": True,
        }
    elif port_scope == "custom":
        scan_block = {
            "concurrency": 100,
            "ports_tls": parse_port_spec(custom_ports or ""),
            "include_sni": True,
        }
        connectors_block = {
            "enable_email": False,
            "enable_broker": False,
        }
    else:
        # top1000 or all — nmap-native scopes; write hint for run_scan.py
        scan_block = {
            "concurrency": 100,
            "ports_tls": list(CONSULTING_TLS_PORTS),
            "include_sni": True,
            "nmap_port_scope": port_scope,
        }

    config = {
        "assessment": {
            "name": "Dashboard Scan",
            "data_classification": "confidential",
            "report_owner": "Dashboard",
            "timezone": "UTC",
        },
        "scan": scan_block,
        "targets": {
            "fqdns": fqdns,
            "cidrs": cidrs,
            "include_ips": [],
            "exclude_ips": [],
        },
        "output": {
            "directory": str(output_dir),
            "db_path": db_path,
        },
        "intelligence": {
            "intelligence_version": "4.8.0",
            "profile": calibration,
        },
        "security": {
            "allow_internal_targets": allow_internal_targets,
        },
    }
    # D-14: an explicit operator toggle (connectors_overlay) beats the
    # custom-port-scope suppression above (enable_email/enable_broker=False),
    # so the overlay is merged LAST — {**suppression, **overlay}. D-13:
    # delta-only — only keys the operator actually touched are written, never
    # the full 25-key ConnectorsCfg surface.
    if connectors_overlay:
        filtered_overlay: Dict[str, bool] = {}
        for key, value in connectors_overlay.items():
            if key not in _KNOWN_CONNECTOR_KEYS or not key.startswith("enable_"):
                raise ValueError(
                    f"{key!r} is not a recognized connector toggle "
                    "(must be a known enable_* connector key)"
                )
            filtered_overlay[key] = value
        connectors_block = {**(connectors_block or {}), **filtered_overlay}
    if connectors_block is not None:
        config["connectors"] = connectors_block
    return config


def _write_job_config(
    output_dir: Path,
    targets: str,
    db_path: str,
    calibration: str,
    allow_internal_targets: bool = False,
    port_scope: str = "top1000",
    custom_ports: Optional[str] = None,
) -> str:
    """Write a minimal config YAML for a dashboard-dispatched scan.

    Dict construction lives in `build_job_config_dict` (Phase 192 / PARITY-01);
    this function's remaining job is to dump that dict to the job's config path.
    """
    config = build_job_config_dict(
        output_dir, targets, db_path, calibration,
        allow_internal_targets=allow_internal_targets,
        port_scope=port_scope,
        custom_ports=custom_ports,
    )
    config_path = str(output_dir / "config.yaml")
    with open(config_path, "w") as fh:
        yaml.dump(config, fh, default_flow_style=False)
    return config_path


# Phase 193 / PARITY-03 / D-09/D-10: sanitize a per-host key into the
# [A-Z0-9_] alphabet used for env-var names. Uppercases and replaces every
# other character with "_" — never drops characters, so two DISTINCT hosts
# can still collide (e.g. "a.b" and "a_b" both sanitize to "A_B"), which the
# caller below detects and rejects rather than silently overwriting one
# host's credential with another's (T-193-30).
_SANITIZE_NON_ENV_CHARS = re.compile(r"[^A-Z0-9_]")


def _sanitize_host_for_env(host: str) -> str:
    return _SANITIZE_NON_ENV_CHARS.sub("_", host.upper())


def _build_credential_env(
    credentials: Optional[Dict[str, str]],
) -> Tuple[Dict[str, str], Dict[str, dict]]:
    """Map `ScanSubmitRequest.credentials` into a Popen env injection dict
    plus a job-YAML fragment carrying env-var NAMES ONLY (D-09).

    Returns `(injected_env, connectors_yaml_fragment)`:
      - `injected_env` — {ENV_VAR_NAME: value} for `subprocess.Popen(env=...)`.
        This is a plain local dict; the caller must never assign it to a
        `ScanJob` column, a logger call, or the written config.yaml (D-11/D-12).
      - `connectors_yaml_fragment` — optional `broker_credentials` /
        `snmp_v3_credentials` keys, each value carrying only `pass_env` /
        `auth_key_env` / `priv_key_env` NAMES, never the credential value
        itself (mirrors `quirk/scanner/broker_scanner.py`'s
        `os.environ.get(pass_env, "")` / `snmp_scanner.py`'s
        `os.environ.get(credential.auth_key_env, "")` read idiom — no
        scanner-side change is required).

    Three key shapes, derived from `ScanSubmitRequest.known_credential_keys_only`'s
    allowlist (plan 03):
      - flat `CREDENTIAL_REGISTRY` names (e.g. `adcs_password`) -> the
        registry entry's own `env_fallback` name, so the registry (plan 02)
        stays the single source of truth — never a hardcoded name table here.
      - `broker:<host>` -> `QUIRK_JOB_BROKER_<SANITIZED_HOST>`.
      - `snmpv3:<host>:auth` / `snmpv3:<host>:priv` ->
        `QUIRK_JOB_SNMPV3_<SANITIZED_HOST>_AUTH` / `..._PRIV`.
      - `broker:<host>:user` / `snmpv3:<host>:username` -> USERNAMES
        (identifiers, not secrets — Phase 193 review CR-03): written inline
        into the YAML fragment's `user`/`username` fields per the
        BrokerCredential/SnmpV3Credential config contract, never injected
        into the subprocess env.

    The host slot `"default"` (the dashboard's single-slot credential UI)
    has documented fallback semantics at every consumer: scanners use the
    `"default"` entry for any host lacking a host-specific entry
    (broker_scanner mgmt enrichment, run_scan.py's SNMP phase,
    hardware_scanner's v3 ladder + bridge-evidence walk).

    Raises `ValueError` (the caller converts to 422) if two distinct hosts
    sanitize to the same env-var name, so one host's credential can never be
    delivered to another host's scan (T-193-30).
    """
    injected_env: Dict[str, str] = {}
    if not credentials:
        return injected_env, {}

    from quirk.config_redaction import CREDENTIAL_REGISTRY

    registry_by_name = {
        entry.name: entry for entry in CREDENTIAL_REGISTRY if entry.section == "connectors"
    }

    # env-var NAME -> the credentials key that claimed it, for collision detection.
    claimed_env_names: Dict[str, str] = {}

    def _claim(env_name: str, source_key: str) -> None:
        prior = claimed_env_names.get(env_name)
        if prior is not None and prior != source_key:
            raise ValueError(
                f"Credential env-var name collision: {source_key!r} and {prior!r} "
                f"both sanitize to {env_name!r} — use distinguishable host names"
            )
        claimed_env_names[env_name] = source_key

    broker_credentials: Dict[str, dict] = {}
    snmp_v3_credentials: Dict[str, dict] = {}

    for key, value in credentials.items():
        if not value:
            # D-15: blank credential values never block submission here —
            # they simply inject nothing. The connector-enabled-with-blank-
            # credentials warning is computed separately in create_job.
            continue
        if key.startswith("broker:"):
            remainder = key[len("broker:"):]
            if remainder.endswith(":user"):
                # Phase 193 review CR-03: `broker:<host>:user` carries the
                # USERNAME — an identifier, not a secret. BrokerCredential
                # stores `user` inline in YAML by contract (only the password
                # rides env-var indirection via `pass_env`), and
                # broker_scanner requires BOTH user and pass_env to
                # authenticate. Never injected into the subprocess env.
                host = remainder[: -len(":user")]
                broker_credentials.setdefault(host, {})["user"] = value
                continue
            host = remainder
            env_name = f"QUIRK_JOB_BROKER_{_sanitize_host_for_env(host)}"
            _claim(env_name, key)
            injected_env[env_name] = value
            broker_credentials.setdefault(host, {})["pass_env"] = env_name
        elif key.startswith("snmpv3:"):
            # Phase 193 review WR-02: parse the KIND from the END (rsplit) —
            # the validator's `^snmpv3:.+:(auth|priv)$` regex accepts hosts
            # containing colons (IPv6 literals), so a `split(":", 2)` parse
            # truncated the host and silently misfiled auth as priv. Any kind
            # outside the contract raises (caller converts to 422) instead of
            # defaulting to priv.
            prefix_host, kind = key.rsplit(":", 1)
            host = prefix_host[len("snmpv3:"):]
            if kind == "auth":
                env_name = f"QUIRK_JOB_SNMPV3_{_sanitize_host_for_env(host)}_AUTH"
                field_name = "auth_key_env"
            elif kind == "priv":
                env_name = f"QUIRK_JOB_SNMPV3_{_sanitize_host_for_env(host)}_PRIV"
                field_name = "priv_key_env"
            elif kind == "username":
                # Phase 193 review CR-03: `snmpv3:<host>:username` carries the
                # USM USERNAME — an identifier, not a secret. SnmpV3Credential
                # stores `username` inline in YAML by contract (only the
                # auth/priv passphrases ride env-var indirection), and USM
                # authentication with an empty username cannot succeed. Never
                # injected into the subprocess env.
                snmp_v3_credentials.setdefault(host, {})["username"] = value
                continue
            else:
                raise ValueError(
                    f"Unrecognized snmpv3 credential kind in {key!r} — "
                    "expected 'auth' or 'priv'"
                )
            _claim(env_name, key)
            injected_env[env_name] = value
            snmp_v3_credentials.setdefault(host, {})[field_name] = env_name
        else:
            entry = registry_by_name.get(key)
            if entry is None or not entry.env_fallback:
                continue
            injected_env[entry.env_fallback] = value

    yaml_fragment: Dict[str, dict] = {}
    if broker_credentials:
        yaml_fragment["broker_credentials"] = broker_credentials
    if snmp_v3_credentials:
        yaml_fragment["snmp_v3_credentials"] = snmp_v3_credentials
    return injected_env, yaml_fragment


def _connectors_with_blank_credential_warnings(
    resolved_connectors, credentials: Optional[Dict[str, str]]
) -> list:
    """D-15: connectors enabled with ALL declared credential fields blank warn,
    never block. Returns a list of `{"connector": flag, "message": str}` dicts
    for the success response's `credential_warnings` key.

    Scoped to the flat `CREDENTIAL_REGISTRY` connector fields this plan wires
    up (adcs/pg/mysql/snmp password fields) — broker/SNMPv3 per-host
    credentials have no single enabled/disabled flag to key a warning off of
    and are intentionally out of this helper's scope.
    """
    from quirk.config_redaction import CREDENTIAL_REGISTRY, credential_is_set

    submitted = credentials or {}
    # Map connector enable_* flag -> the CREDENTIAL_REGISTRY field name(s) it
    # gates, derived from this plan's own naming convention (enable_db gates
    # BOTH the PostgreSQL and MySQL password fields — a connector is only
    # warned about when EVERY one of its gated fields is blank).
    _FLAG_TO_CREDENTIAL_FIELDS = {
        "enable_adcs": ("adcs_password",),
        "enable_db": ("pg_scanner_password", "mysql_scanner_password"),
        "enable_snmp": ("snmp_community",),
    }
    warnings: list = []
    registry_names = {entry.name for entry in CREDENTIAL_REGISTRY if entry.section == "connectors"}
    for flag, field_names in _FLAG_TO_CREDENTIAL_FIELDS.items():
        applicable_fields = [f for f in field_names if f in registry_names]
        if not applicable_fields:
            continue
        if not getattr(resolved_connectors, flag, False):
            continue
        all_blank = True
        for field_name in applicable_fields:
            already_set = credential_is_set(
                "connectors", field_name, getattr(resolved_connectors, field_name, None)
            )
            submitted_value = submitted.get(field_name)
            if already_set or (submitted_value and submitted_value.strip()):
                all_blank = False
                break
        if not all_blank:
            continue
        warnings.append(
            {
                "connector": flag,
                "message": (
                    f"{flag} is enabled but no credential was supplied for "
                    f"{', '.join(repr(f) for f in applicable_fields)} — the "
                    "scan will run with reduced access for this connector."
                ),
            }
        )
    return warnings


def _stage_index(current_stage: Optional[str], status: str) -> int:
    """Map current_stage string to a 0..7 index for the progress bar.

    queued / None -> 0
    each named stage -> its 1-based index in _STAGE_ORDER
    completed (any status terminal with stage missing) -> 7
    """
    if status == "completed":
        return _STAGE_TOTAL
    if current_stage is None:
        return 0
    try:
        return _STAGE_ORDER.index(current_stage) + 1
    except ValueError:
        return 0


def _to_response(row: ScanJob) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=row.job_id,
        status=row.status,
        current_stage=row.current_stage,
        started_at=stamp_utc_iso(row.started_at),
        completed_at=stamp_utc_iso(row.completed_at),
        scan_run_id=row.scan_run_id,
        error_message=row.error_message,
        stage_index=_stage_index(row.current_stage, row.status),
        stage_total=_STAGE_TOTAL,
        discovery_batch_index=getattr(row, "discovery_batch_index", None),
        discovery_batch_total=getattr(row, "discovery_batch_total", None),
        discovery_hosts_checked=getattr(row, "discovery_hosts_checked", None),
    )


def _job_output_dir(job_id: str) -> Path:
    """Single owner of the per-job output layout (config.yaml, run.log)."""
    return Path("output/jobs") / job_id


def _get_or_404(db: Session, job_id: str) -> ScanJob:
    row = db.get(ScanJob, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail=format_error("DASHBOARD-008"))
    return row


# Popen handles for scans spawned by THIS server process, keyed by job_id.
# Liveness must come from the handle (proc.poll()), never from the bare pid:
# os.kill(pid, 0) reports zombies as alive (the server never wait()s its
# children, so a crashed scan stays a zombie until the next Popen), can be
# fooled by pid reuse, and on Windows sig 0 is CTRL_C_EVENT — it would
# interrupt the scan it was meant to observe. poll() has none of these
# problems and reaps the child as a side effect.
_PROCS: dict[str, subprocess.Popen] = {}
_PROCS_LOCK = threading.Lock()


def _reconcile_if_dead(db: Session, row: ScanJob) -> None:
    """Flip a `running` job to `failed` when its subprocess has already exited.

    On clean completion run_scan sets status to `completed` itself; on a crash
    (bad config, missing dependency, systemd sandbox denial) it dies without
    updating the row, which otherwise leaves the UI polling `running` forever.
    This reconciles such rows live, on the next status poll, and points the
    operator at the captured subprocess log.

    Rows whose handle is not in `_PROCS` were spawned by a previous server
    process; the startup sweep (`_recover_stale_jobs`) owns those.
    """
    if row.status != "running":
        return
    with _PROCS_LOCK:
        proc = _PROCS.get(row.job_id)
    if proc is None:
        return
    returncode = proc.poll()  # reaps the child if it exited
    if returncode is None:
        return
    with _PROCS_LOCK:
        _PROCS.pop(row.job_id, None)
    # Absolute path: the operator reading this message is rarely in the
    # server's CWD. Same process as the spawn, so resolve() matches the file
    # actually created in create_job.
    log_hint = (_job_output_dir(row.job_id) / "run.log").resolve()
    # Guarded update, not a blind write: the child commits its own terminal
    # status (completed/failed) just before exiting, and this poll may hold a
    # row read from before that commit. WHERE status='running' makes the
    # child's terminal status win the race.
    db.query(ScanJob).filter(
        ScanJob.job_id == row.job_id, ScanJob.status == "running"
    ).update(
        {
            "status": "failed",
            "completed_at": _utcnow_naive(),
            "error_message": (
                f"Scan process (pid {row.pid}) exited without completing "
                f"(exit code {returncode}). See {log_hint} for captured output."
            ),
        },
        synchronize_session=False,
    )
    db.commit()
    db.refresh(row)


@write_router.post("/jobs", status_code=201)
def create_job(payload: ScanSubmitRequest, db: Session = Depends(get_db)) -> dict:
    """Create a scan_jobs row and spawn run_scan.py as a subprocess. Non-blocking."""
    # AUDIT-07: validate and normalize targets before any DB write or subprocess spawn.
    from quirk.util.targets import parse_target_tokens
    try:
        valid_fqdns, valid_cidrs = parse_target_tokens(payload.targets)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    all_valid_tokens = valid_fqdns + valid_cidrs
    if not all_valid_tokens:
        raise HTTPException(
            status_code=422,
            detail="No valid targets provided — targets must not be empty or whitespace-only",
        )

    # Phase 143 / TAIL-02 / D-04: server-enforced trusted-targets consent gate — same
    # chokepoint function run_scan.py's CLI path calls, per D-04's dual-entry-point wording.
    # Fail-safe: mirrors the allow_internal_targets load pattern below — load server-side
    # SecurityCfg fresh, fail-open-to-empty-allowlist only on load error (an unreachable/missing
    # config.yaml must not accidentally BLOCK all scans; D-03's "empty = allow-all" posture
    # applies symmetrically to the fail-safe path here, unlike allow_internal_targets's
    # fail-CLOSED posture — trusted_targets' own default IS "allow all").
    from quirk.util.target_trust import is_target_trusted
    trusted_targets_cfg: list = []
    try:
        from quirk.config import load_config  # lazy import — avoids cycles
        _cfg_path = os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
        _cfg = load_config(_cfg_path)
        trusted_targets_cfg = list(getattr(_cfg.security, "trusted_targets", None) or [])
    except Exception:
        trusted_targets_cfg = []
    if trusted_targets_cfg:
        for _target in all_valid_tokens:
            _result = is_target_trusted(_target, trusted_targets_cfg)
            if not _result.ok:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Target {_result.redacted_preview!r} is not in the trusted-targets "
                        f"allowlist (security.trusted_targets in config.yaml)."
                    ),
                )

    # Phase 144 / D-02: large ranges are now chunked, not rejected. nmap
    # discovery used to run as a single subprocess covering the entire target
    # set with one hardcoded 300s timeout — an oversized CIDR would grind
    # through nmap's --host-timeout 10s per unreachable host until that wall
    # clock killed it. The discovery batch loop (run_scan.py, Plan 144-02)
    # now splits the deduplicated host list into _MAX_HOSTS_PER_CIDR-sized
    # sequential batches, each with its own fresh timeout, so no total-range
    # ceiling is needed here anymore — this block is informational-only
    # (logs the projected batch count) and never raises for host count.
    _force_nmap = payload.enable_nmap or payload.port_scope in ("top1000", "all")
    if _force_nmap and valid_cidrs:
        import ipaddress as _ipaddress
        import math as _math
        from quirk.scanner.target_expander import _MAX_HOSTS_PER_CIDR
        _total_nmap_hosts = len(valid_fqdns)
        for _cidr in valid_cidrs:
            _net = _ipaddress.ip_network(_cidr, strict=False)
            _total_nmap_hosts += _net.num_addresses
        _projected_batches = _math.ceil(_total_nmap_hosts / _MAX_HOSTS_PER_CIDR) or 1
        logger.info(
            "new job: %d nmap discovery hosts projected across %d sequential "
            "batch(es) of up to %d hosts each (Phase 144 chunked discovery, "
            "no reject ceiling)",
            _total_nmap_hosts, _projected_batches, _MAX_HOSTS_PER_CIDR,
        )

    # Re-join stripped tokens; this is what gets stored and passed to the scanner.
    normalized_targets = ",".join(all_valid_tokens)

    # Phase 193 / PARITY-02 / D-08: server-side availability re-check — the
    # client's disabled Switch (ConnectorsPanel) is UX only, never the
    # guarantee (T-193-23). Evaluate the FULLY RESOLVED post-apply_profile
    # connector state via the same `resolve_effective_config` the GET
    # /api/config/effective route uses, not just the raw `payload.connectors`
    # delta, so a vertical preset silently enabling an unavailable connector
    # is also caught (T-193-24). Placed before any ScanJob row or output
    # directory is created, so a 422 here leaves no trace.
    from quirk.dashboard.api.config_preview import resolve_effective_config
    from quirk.dashboard.api.connector_availability import probe_all_connectors

    try:
        resolved_cfg, _resolved_dict, _preset_changed = resolve_effective_config(
            targets=normalized_targets,
            profile=payload.profile,
            calibration=payload.calibration,
            enable_nmap=payload.enable_nmap,
            port_scope=payload.port_scope,
            custom_ports=payload.custom_ports,
            connectors_overlay=payload.connectors,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    availability = probe_all_connectors()
    unavailable_offenders = []
    for field in dataclasses.fields(resolved_cfg.connectors):
        flag_name = field.name
        if not flag_name.startswith("enable_"):
            continue
        if not getattr(resolved_cfg.connectors, flag_name, False):
            continue
        entry = availability.get(flag_name)
        if entry is not None and not entry.available:
            unavailable_offenders.append(entry)
    if unavailable_offenders:
        detail = "; ".join(
            f"Scan rejected: {entry.label} is not available in this environment "
            f"({entry.reason})"
            for entry in unavailable_offenders
        )
        raise HTTPException(status_code=422, detail=detail)

    job_id = str(uuid.uuid4())
    db_path = _default_db_path()
    output_dir = _job_output_dir(job_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    row = ScanJob(
        job_id=job_id,
        status="queued",
        target=normalized_targets,
        profile=payload.profile,
        calibration=payload.calibration,
        enable_nmap=payload.enable_nmap,
        started_at=_utcnow_naive(),
    )
    db.add(row)
    db.flush()

    # Phase 120 / AC-03: server-policy only; client-supplied value (if any) is
    # dropped by ScanSubmitRequest extra="ignore". We source the flag from the
    # server-side config — QUIRK_CONFIG_PATH env wins, falling back to
    # ./config.yaml. Any resolution failure defaults to False (fail-safe deny).
    allow_internal = False
    try:
        from quirk.config import load_config  # lazy import — avoids cycles
        cfg_path = os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
        cfg = load_config(cfg_path)
        allow_internal = bool(getattr(cfg.security, "allow_internal_targets", False))
    except Exception:
        # Fail-safe default: deny internal targeting when config is missing or
        # broken. Production callers can opt in only via valid server config.
        allow_internal = False

    # Phase 193 / PARITY-02 (D-13/D-14): connectors_overlay threads the
    # operator's accepted toggles into the job YAML — build_job_config_dict
    # already merges it LAST, after the custom-port-scope suppression.
    try:
        config_dict = build_job_config_dict(
            output_dir, normalized_targets, db_path, payload.calibration,
            allow_internal_targets=allow_internal,
            port_scope=payload.port_scope,
            custom_ports=payload.custom_ports,
            connectors_overlay=payload.connectors,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Phase 193 / PARITY-03 / D-09/D-11/D-12: credential VALUES are held in a
    # request-local variable ONLY (never assigned to `row`, never merged into
    # `config_dict`'s values, never logged) and injected into the scan
    # subprocess's environment below. The job YAML gets env-var NAMES ONLY,
    # via `credential_yaml_fragment` (`broker_credentials`/`snmp_v3_credentials`
    # — never a bare credential value).
    try:
        injected_env, credential_yaml_fragment = _build_credential_env(payload.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # D-15: connectors enabled with every declared credential field blank
    # warn, never block. Computed against the fully resolved connector state
    # from the D-08 gate above (`resolved_cfg`).
    credential_warnings = _connectors_with_blank_credential_warnings(
        resolved_cfg.connectors, payload.credentials
    )

    if credential_yaml_fragment:
        # Phase 193 review CR-02: `broker_credentials` is a TOP-LEVEL
        # AppConfig key (quirk/config.py reads `raw.get("broker_credentials")`)
        # — writing it under `connectors:` would trip the loader's
        # unknown-connector-key filter and be silently discarded.
        # `snmp_v3_credentials` IS a genuine ConnectorsCfg field and stays
        # under `connectors:`.
        broker_fragment = credential_yaml_fragment.get("broker_credentials")
        if broker_fragment:
            config_dict["broker_credentials"] = broker_fragment
        connectors_fragment = {
            k: v
            for k, v in credential_yaml_fragment.items()
            if k != "broker_credentials"
        }
        if connectors_fragment:
            config_dict["connectors"] = {
                **config_dict.get("connectors", {}),
                **connectors_fragment,
            }

    config_path = str(output_dir / "config.yaml")
    with open(config_path, "w") as fh:
        yaml.dump(config_dict, fh, default_flow_style=False)

    cmd = [
        sys.executable, "-m", "run_scan",
        "--config", config_path,
        "--profile", payload.profile,
        "--quiet",
        "--db-path", db_path,
        "--job-id", job_id,
    ]
    # Phase 121: auto-enable nmap for wide port scopes; honor user's explicit
    # enable_nmap checkbox for common/custom scopes (RESEARCH Pitfall 5).
    force_nmap = payload.port_scope in ("top1000", "all")
    if payload.enable_nmap or force_nmap:
        # Phase 146 / DISC-05, Pitfall 2: no static timeout is passed here —
        # the spawned run_scan.py process computes a per-batch timeout via
        # discovery_timeout_for_batch(), which is the only place that knows
        # batch sizes. That helper's hard min(..., 300) clamp is what
        # enforces the 300s ceiling now, not a static CLI flag.
        cmd += ["--discovery", "nmap"]

    # Pitfall 2: non-blocking — do not call communicate or proc.wait.
    # stdin=DEVNULL prevents the subprocess from inheriting the server's TTY;
    # without this, probe-budget and fuzz-gate input() prompts block silently.
    #
    # Capture stdout+stderr to a per-job log file rather than discarding them.
    # When run_scan dies on startup (bad config, missing dep, systemd sandbox
    # denial) the error lands here instead of /dev/null, so the failure is
    # diagnosable. The child dups the fd at exec, so the parent closes its own
    # handle immediately after Popen.
    log_path = output_dir / "run.log"
    log_fh = open(log_path, "wb")
    try:
        # Phase 193 / PARITY-03 / D-09: env is the PARENT environment merged
        # with the request-local injected credential vars — never a bare
        # dict of only `injected_env` (that would drop PATH/PYTHONPATH/
        # QUIRK_CONFIG_PATH and break every scan), and never
        # a direct assignment into os.environ (mutating it in place) of the server process (a race
        # under FastAPI's threadpool — two concurrent create_job calls would
        # stomp each other's env vars). `injected_env` is never stored beyond
        # this call (D-12).
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            env={**os.environ, **injected_env},
        )
    finally:
        log_fh.close()
    with _PROCS_LOCK:
        _PROCS[job_id] = proc
    row.pid = proc.pid
    row.status = "running"
    db.commit()

    response: dict = {"job_id": job_id, "status": "running"}
    if credential_warnings:
        response["credential_warnings"] = credential_warnings

    logger.info("scan_job created job_id=%s pid=%d target=%s", job_id, proc.pid, payload.targets)
    return response


@read_router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    row = _get_or_404(db, job_id)
    _reconcile_if_dead(db, row)
    return _to_response(row)


@write_router.delete("/jobs/{job_id}", status_code=204)
def cancel_job(job_id: str, db: Session = Depends(get_db)) -> None:
    row = _get_or_404(db, job_id)
    if row.pid and row.status == "running":
        try:
            os.kill(row.pid, signal.SIGTERM)
        except ProcessLookupError:
            # Race: process already exited. Optimistic cancel proceeds anyway.
            pass
    row.status = "cancelled"
    row.completed_at = _utcnow_naive()
    db.commit()
    return None
