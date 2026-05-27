"""Phase 109 CONSOLE-01: sensor push ingestion endpoint + Phase 111 DASH-02: sensor registry.

POST /api/sensor/push — ingest a sensor push envelope.
GET  /api/sensor/registry — return all enrolled sensors with push-status.

POST /api/sensor/push — Phase 109 CONSOLE-01: sensor push ingestion endpoint.

Security contract (§6 locked failure ladder)
---------------------------------------------
Auth (401)      Router-level require_auth; no require_csrf (M2M, never browser).
Body size (413) Content-Length header check + actual body length check → 413 + audit.
Parse           zstd decompress (capped at _MAX_DECOMPRESS_BYTES) + PushEnvelope parse;
                schema_version / sensor_version mismatch is warn-only, never 422/500.
Replay (422)    pushed_at outside ±15 min of received_at → 422 + console_utc + audit.
Sensor (4xx)    Unknown sensor_id → 404 + audit.
Dedup (409)     DuplicatePayloadError from _ingest_envelope → 409 fixed string + audit.
OK (200)        Persists SensorPush + CryptoEndpoint rows; audit status="ok".

Threat mitigations
------------------
T-109-04  Router-level Depends(require_auth) — no per-handler bypass possible.
T-109-05  ±15-min replay window + payload_id UNIQUE constraint.
T-109-06  _BODY_LIMIT=10MB Content-Length + body-length checks + _MAX_DECOMPRESS_BYTES cap.
T-109-07  safe_str(exc) on all error paths; fixed strings for 409/unknown-sensor.
T-109-08  IntegrationDelivery row written on EVERY attempt, committed outside ingest try.
T-109-09  Sensor lookup before any persistence; unknown → 4xx + audit.
T-109-10  UNIQUE constraint + rollback-first → 409 fixed string (never stringify exc).
T-109-11  X-Sensor-Signature header read + structurally validated; carried as qpush_sig;
          crypto verification deferred v5.5 (hmac_key column absent in Phase 107 schema).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List

import zstandard
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from quirk.cli.console_cmd import DuplicatePayloadError, UnknownSensorError, _ingest_envelope
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.sensor_auth import require_sensor_auth
from quirk.dashboard.api.schemas import SensorRegistryItem, SensorRegistryResponse
from quirk.models import IntegrationDelivery, Sensor
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routers — D-01/D-02: split push (sensor token) vs operator routes
# router           : operator require_auth — registry, merge, dashboard (D-02)
# sensor_push_router: per-sensor require_sensor_auth — POST /sensor/push only (D-01)
# ---------------------------------------------------------------------------
router = APIRouter(dependencies=[Depends(require_auth)])
sensor_push_router = APIRouter(dependencies=[Depends(require_sensor_auth)])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_BODY_LIMIT = 10 * 1024 * 1024           # 10 MB — Content-Length + body guard
_MAX_DECOMPRESS_BYTES = 20 * 1024 * 1024  # zstd cap (mirrors console_cmd.py D-09)
# Power-of-two C-layer window cap (zstd rounds max_window_size up to a window-log
# exponent; 20 MB would silently become 32 MB). The authoritative 20 MB limit is
# enforced by the post-read length check (WR-01).
_ZSTD_MAX_WINDOW = 32 * 1024 * 1024
_REPLAY_WINDOW = timedelta(minutes=15)    # pushed_at must be within ±15 min of received_at

# X-Sensor-Signature structural prefix (T-109-11 — crypto verify deferred v5.5)
_SIG_PREFIX = "hmac-sha256="

# ---------------------------------------------------------------------------
# Phase 111 DASH-02: sensor push-status constants + helper
# ---------------------------------------------------------------------------
# Sensors silent for more than _STALE_DAYS without any push are treated as
# decommissioned / forgotten — they become "unknown" rather than "stale" so
# the UI does not surface decade-old enrollments as perpetually overdue.
_STALE_DAYS = 30


def _sensor_status(s, now: datetime) -> str:
    """Compute push-status for a single Sensor row.

    Rules (replicate the per-sensor overdue logic from merge.scan._build_coverage_warning,
    but return a per-sensor string rather than an aggregate dict — Trap T7):

    - last_push_at is None → "unknown"  (never pushed, regardless of enrollment age)
    - last_push_at is set, now > last_push_at + 2×cadence → "stale"
    - otherwise → "current"

    ``expected_cadence_minutes`` defaults to 1440 (24h) when None.
    The 30-day decommissioned threshold from _build_coverage_warning is intentionally
    NOT applied here — _sensor_status reports each sensor's own status without
    suppressing old sensors (the UI can filter/sort as needed).
    """
    if s.last_push_at is None:
        return "unknown"

    last_push = s.last_push_at
    # Normalize: strip tzinfo if aware so comparison is always naive-UTC vs naive-UTC.
    # ``now`` is constructed as datetime.now(timezone.utc).replace(tzinfo=None) in the
    # caller — always naive.  If a future code path stores an aware datetime in
    # last_push_at, the mixed-tz comparison would raise TypeError at runtime (WR-01).
    if getattr(last_push, "tzinfo", None) is not None:
        last_push = last_push.replace(tzinfo=None)

    cadence_minutes = s.expected_cadence_minutes
    if cadence_minutes is None:
        cadence_minutes = 1440  # 24h fallback — architecture §6
    cadence = timedelta(minutes=cadence_minutes)

    if now > last_push + 2 * cadence:
        return "stale"
    return "current"


# ---------------------------------------------------------------------------
# Phase 111 DASH-02: GET /api/sensor/registry
# ---------------------------------------------------------------------------

@router.get("/sensor/registry")  # type: ignore[misc]
def get_sensor_registry(db: Session = Depends(get_db)) -> dict:
    """GET /api/sensor/registry — list all enrolled sensors with push status.

    Returns each Sensor row with a computed status: "current" | "stale" | "unknown".
    Read-only — no db.add/flush/commit.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sensors: List[Sensor] = (
        db.query(Sensor).order_by(Sensor.enrolled_at.desc()).all()
    )
    items: List[SensorRegistryItem] = [
        SensorRegistryItem(
            sensor_id=s.sensor_id,
            segment=s.segment,
            sensor_version=s.sensor_version,
            last_push_at=s.last_push_at,
            status=_sensor_status(s, now),
        )
        for s in sensors
    ]
    return SensorRegistryResponse(sensors=items).model_dump()


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------
class PushEnvelope(BaseModel):
    """Wire model for a sensor push payload.

    extra='ignore': unknown fields from newer sensor versions are dropped
    silently (D-11, version-skew warn-only policy).
    """

    model_config = ConfigDict(extra="ignore")

    payload_id: str
    pushed_at: str
    schema_version: str
    sensor_version: str
    sensor_id: str
    segment: str
    findings: list = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------
def _audit(
    db: Session,
    scan_id: str,
    status: str,
    error_summary: str | None = None,
) -> None:
    """Write one IntegrationDelivery row for this push attempt.

    Commit is OUTSIDE the ingest try-block (base.py L149 WR-01 pattern).
    If the audit write itself fails we log and continue — never mask the
    original error.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = IntegrationDelivery(
        scan_id=scan_id,
        finding_hash=None,
        destination="sensor_push",
        status=status,
        attempted_at=now,
        error_summary=error_summary,
    )
    db.add(row)
    try:
        db.commit()
    except Exception as exc:
        logger.warning("Audit row commit failed: %s", safe_str(exc))


# ---------------------------------------------------------------------------
# Route handler — on sensor_push_router (require_sensor_auth, not require_auth)
# ---------------------------------------------------------------------------
@sensor_push_router.post("/sensor/push")
async def sensor_push(request: Request, db: Session = Depends(get_db)) -> dict:
    """POST /api/sensor/push — ingest a sensor push envelope.

    Full §6 failure ladder with IntegrationDelivery audit on every branch.
    """
    received_at = datetime.now(timezone.utc).replace(tzinfo=None)
    # scan_id used for audit rows — use received_at ISO string as surrogate
    scan_id = received_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------------------
    # T-109-06 — Body size guard (Content-Length header check)
    # ------------------------------------------------------------------
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            cl_int = int(content_length)
        except ValueError:
            cl_int = 0
        if cl_int > _BODY_LIMIT:
            _audit(db, scan_id, "failed", "payload_too_large")
            raise HTTPException(status_code=413, detail="Payload too large (10 MB limit)")

    body = await request.body()
    if len(body) > _BODY_LIMIT:
        _audit(db, scan_id, "failed", "payload_too_large")
        raise HTTPException(status_code=413, detail="Payload too large (10 MB limit)")

    # ------------------------------------------------------------------
    # T-109-11 — X-Sensor-Signature: read + structural validate; carry as qpush_sig
    # (crypto verify deferred v5.5 — hmac_key column absent from Phase 107 schema)
    # ------------------------------------------------------------------
    qpush_sig: str | None = None
    raw_sig = request.headers.get("X-Sensor-Signature")
    if raw_sig is not None:
        if isinstance(raw_sig, str) and raw_sig.startswith(_SIG_PREFIX):
            qpush_sig = raw_sig
        else:
            logger.warning(
                "X-Sensor-Signature present but malformed (expected '%s<hex>'): dropping",
                _SIG_PREFIX,
            )

    # ------------------------------------------------------------------
    # Decompress body (zstd cap — T-109-06)
    # ------------------------------------------------------------------
    try:
        dctx = zstandard.ZstdDecompressor(max_window_size=_ZSTD_MAX_WINDOW)
        raw = dctx.stream_reader(body).read(_MAX_DECOMPRESS_BYTES + 1)
        if len(raw) > _MAX_DECOMPRESS_BYTES:
            _audit(db, scan_id, "failed", "decompressed_payload_too_large")
            raise HTTPException(
                status_code=413,
                detail="Decompressed payload exceeds 20 MB limit",
            )
    except HTTPException:
        raise
    except Exception as exc:
        _audit(db, scan_id, "failed", safe_str(exc))
        raise HTTPException(status_code=400, detail="Body is not valid zstd-compressed data")

    # ------------------------------------------------------------------
    # Parse JSON + PushEnvelope (extra='ignore' — version-skew warn-only)
    # ------------------------------------------------------------------
    try:
        envelope_dict = json.loads(raw.decode("utf-8"))
        envelope = PushEnvelope(**envelope_dict)
    except Exception as exc:
        _audit(db, scan_id, "failed", safe_str(exc))
        raise HTTPException(status_code=400, detail="Body could not be parsed as a push envelope")

    # Update scan_id to pushed_at once parsed (better traceability).
    # WR-03: clamp to 64 chars so untrusted pushed_at cannot overflow
    # IntegrationDelivery.scan_id String(64) or inject long strings into audit rows.
    scan_id = (envelope.pushed_at or scan_id)[:64]

    # schema_version / sensor_version mismatch → warn-only, never block
    # (logged at DEBUG so integration tests don't surface noise)
    logger.debug(
        "sensor_push: sensor_id=%s schema_version=%s sensor_version=%s",
        envelope.sensor_id,
        envelope.schema_version,
        envelope.sensor_version,
    )

    # ------------------------------------------------------------------
    # T-109-05 — Replay window check: pushed_at must be within ±15 min
    # ------------------------------------------------------------------
    pushed_at_dt: datetime | None = None
    try:
        pushed_at_dt = (
            datetime.fromisoformat(envelope.pushed_at.replace("Z", "+00:00"))
            .replace(tzinfo=None)
        )
    except (ValueError, AttributeError):
        pass

    if pushed_at_dt is None:
        _audit(db, scan_id, "failed", "unparseable_pushed_at")
        raise HTTPException(status_code=422, detail="pushed_at is not a valid ISO-8601 timestamp")

    delta = abs(received_at - pushed_at_dt)
    if delta > _REPLAY_WINDOW:
        console_utc = received_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        _audit(db, scan_id, "failed", "replay_window_exceeded")
        raise HTTPException(
            status_code=422,
            detail={"error": "replay_window_exceeded", "console_utc": console_utc},
        )

    # ------------------------------------------------------------------
    # T-109-09 — Sensor lookup: use token-resolved sensor_id (D-04)
    # Token identity is authoritative; envelope.sensor_id is informational only.
    # ------------------------------------------------------------------
    token_sensor_id = request.state.sensor_id  # resolved by require_sensor_auth (D-04)
    sensor_row = db.query(Sensor).filter(Sensor.sensor_id == token_sensor_id).first()
    if sensor_row is None:
        _audit(db, scan_id, "failed", "unknown_sensor_id")
        raise HTTPException(status_code=404, detail="Unknown sensor_id")

    # D-05: Envelope sensor_id mismatch check — token wins; body mismatch → 403
    if envelope.sensor_id != token_sensor_id:
        _audit(db, scan_id, "failed", "sensor_id_mismatch")
        raise HTTPException(status_code=403, detail="sensor_id mismatch: token does not match envelope")

    # ------------------------------------------------------------------
    # Ingest: dedup + last_push_at + CryptoEndpoint rows
    # ------------------------------------------------------------------
    try:
        _ingest_envelope(
            envelope_dict,
            config_path="config.yaml",
            skip_replay_window=False,
            qpush_sig=qpush_sig,
            db=db,
        )
    except DuplicatePayloadError:
        # T-109-10 — fixed string, never stringify exception (LEAK-02)
        # CR-01: call db.rollback() before _audit so the session is in a clean state
        db.rollback()
        _audit(db, scan_id, "failed", "duplicate_payload_id")
        raise HTTPException(status_code=409, detail="Duplicate payload_id")
    except UnknownSensorError:
        # CR-02: FK race — sensor deleted between route SELECT and _ingest_envelope INSERT.
        # Catch explicitly so this returns 404, not 500 (bare except).
        db.rollback()
        _audit(db, scan_id, "failed", "unknown_sensor_id")
        raise HTTPException(status_code=404, detail="Unknown sensor_id")
    except Exception as exc:
        # CR-01: db.rollback() before _audit to ensure clean session state
        db.rollback()
        _audit(db, scan_id, "failed", safe_str(exc))
        raise HTTPException(status_code=500, detail="Ingest failed")

    # ------------------------------------------------------------------
    # WR-02: write the "ok" audit row BEFORE the final commit so both the
    # ingest data and the audit row are committed atomically in one transaction.
    # _audit() calls db.add(); the final db.commit() below persists everything.
    # ------------------------------------------------------------------
    now_audit = datetime.now(timezone.utc).replace(tzinfo=None)
    ok_row = IntegrationDelivery(
        scan_id=scan_id,
        finding_hash=None,
        destination="sensor_push",
        status="ok",
        attempted_at=now_audit,
        error_summary=None,
    )
    db.add(ok_row)

    # Commit (ingest used flush-only; ok audit row added above — single commit)
    try:
        db.commit()
    except Exception as exc:
        logger.warning("Final commit failed: %s", safe_str(exc))
        db.rollback()
        _audit(db, scan_id, "failed", safe_str(exc))
        raise HTTPException(status_code=500, detail="Ingest commit failed")

    return {"status": "accepted", "sensor_id": envelope.sensor_id, "payload_id": envelope.payload_id}
