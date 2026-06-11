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

import logging
import os
import signal
import subprocess
import sys
import threading
import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from quirk.errors import format_error
from sqlalchemy.orm import Session

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


def _write_job_config(
    output_dir: Path,
    targets: str,
    db_path: str,
    calibration: str,
    allow_internal_targets: bool = False,
) -> str:
    """Write a minimal config YAML for a dashboard-dispatched scan.

    run_scan.py has no --target CLI flag; all target/output config must live
    in a YAML file passed via --config. Targets are classified as cidrs (if
    they contain '/') or fqdns (hostnames and bare IPs).
    """
    target_list = [t.strip() for t in targets.split(",") if t.strip()]
    fqdns = [t for t in target_list if "/" not in t]
    cidrs = [t for t in target_list if "/" in t]

    config = {
        "assessment": {
            "name": "Dashboard Scan",
            "data_classification": "confidential",
            "report_owner": "Dashboard",
            "timezone": "UTC",
        },
        "scan": {
            "concurrency": 100,
            "ports_tls": [443, 8443, 9443, 10443, 2222, 8000],
            "include_sni": True,
        },
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
    config_path = str(output_dir / "config.yaml")
    with open(config_path, "w") as fh:
        yaml.dump(config, fh, default_flow_style=False)
    return config_path


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
        started_at=row.started_at.isoformat() if row.started_at else None,
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
        scan_run_id=row.scan_run_id,
        error_message=row.error_message,
        stage_index=_stage_index(row.current_stage, row.status),
        stage_total=_STAGE_TOTAL,
    )


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
    log_hint = Path("output/jobs") / row.job_id / "run.log"
    row.status = "failed"
    row.completed_at = _utcnow_naive()
    row.error_message = (
        f"Scan process (pid {row.pid}) exited without completing "
        f"(exit code {returncode}). See {log_hint} for captured output."
    )
    db.commit()


@write_router.post("/jobs", status_code=201)
def create_job(payload: ScanSubmitRequest, db: Session = Depends(get_db)) -> dict:
    """Create a scan_jobs row and spawn run_scan.py as a subprocess. Non-blocking."""
    job_id = str(uuid.uuid4())
    db_path = _default_db_path()
    output_dir = Path("output/jobs") / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    row = ScanJob(
        job_id=job_id,
        status="queued",
        target=payload.targets,
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

    config_path = _write_job_config(
        output_dir, payload.targets, db_path, payload.calibration,
        allow_internal_targets=allow_internal,
    )

    cmd = [
        sys.executable, "-m", "run_scan",
        "--config", config_path,
        "--profile", payload.profile,
        "--quiet",
        "--db-path", db_path,
        "--job-id", job_id,
    ]
    if payload.enable_nmap:
        cmd += ["--discovery", "nmap", "--nmap-timeout", "300"]

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
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
        )
    finally:
        log_fh.close()
    with _PROCS_LOCK:
        _PROCS[job_id] = proc
    row.pid = proc.pid
    row.status = "running"
    db.commit()

    logger.info("scan_job created job_id=%s pid=%d target=%s", job_id, proc.pid, payload.targets)
    return {"job_id": job_id, "status": "running"}


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
