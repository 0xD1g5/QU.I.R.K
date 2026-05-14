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
import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
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
            "allow_internal_targets": True,
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
        raise HTTPException(status_code=404, detail="Job not found")
    return row


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

    config_path = _write_job_config(output_dir, payload.targets, db_path, payload.calibration)

    cmd = [
        sys.executable, "run_scan.py",
        "--config", config_path,
        "--profile", payload.profile,
        "--quiet",
        "--db-path", db_path,
        "--job-id", job_id,
    ]
    if payload.enable_nmap:
        cmd += ["--discovery", "nmap"]

    # Pitfall 2: non-blocking — do not call communicate or proc.wait.
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    row.pid = proc.pid
    row.status = "running"
    db.commit()

    logger.info("scan_job created job_id=%s pid=%d target=%s", job_id, proc.pid, payload.targets)
    return {"job_id": job_id, "status": "running"}


@read_router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    row = _get_or_404(db, job_id)
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
