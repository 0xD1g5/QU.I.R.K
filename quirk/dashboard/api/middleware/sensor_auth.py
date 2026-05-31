"""Per-sensor Bearer token authentication dependency — Phase 113 AUTH-01/AUTH-04.

Authenticates POST /api/sensor/push requests using a sensor-specific token
stored as a SHA-256 hash in the sensor_tokens table.

Security contract
-----------------
* Token identity is authoritative (D-04): token lookup resolves the sensor_id;
  request.state.sensor_id is set to the token row's sensor_id.
* Timing-safe comparison via hmac.compare_digest on equal-length hex (D-03 /
  T-113-06).
* Raw token value NEVER logged (T-113-05 / T-102-09).
* Unknown / revoked token → 401 + IntegrationDelivery audit row (AUTH-04 / D-09).
* No dual-accept: operator require_auth is NOT consulted on this path (D-10).
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.models import IntegrationDelivery, SensorToken
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def _ip_allowlist() -> list:
    """Parse QUIRK_SENSOR_IP_ALLOWLIST into a list of ip_network objects.

    Comma-separated IPs or CIDRs (e.g. "203.0.113.4, 198.51.100.0/24"). Empty /
    unset → empty list, which disables the allowlist (allow all). Malformed
    entries are skipped (logged once at WARNING) so a single typo cannot lock
    out every sensor silently — but a fully unparseable value yields an empty
    list and is therefore fail-OPEN by design: this is defense-in-depth layered
    on top of mandatory per-sensor token auth, not the primary control.
    """
    raw = os.environ.get("QUIRK_SENSOR_IP_ALLOWLIST", "").strip()
    if not raw:
        return []
    nets = []
    for entry in (e.strip() for e in raw.split(",")):
        if not entry:
            continue
        try:
            nets.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning("Ignoring malformed QUIRK_SENSOR_IP_ALLOWLIST entry: %r", entry)
    return nets


def _ip_allowed(client_host: Optional[str], nets: list) -> bool:
    """True when *client_host* falls inside any network in *nets*.

    No allowlist configured (empty nets) → always allowed. An unparseable or
    missing client address with an allowlist in force is denied (fail closed).
    """
    if not nets:
        return True
    if not client_host:
        return False
    try:
        ip = ipaddress.ip_address(client_host)
    except ValueError:
        return False
    return any(ip in net for net in nets)


def require_sensor_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> None:
    """FastAPI Depends() — authenticates sensor push requests via per-sensor token.

    Flow:
    1. Missing Authorization header → 401 (missing_sensor_token).
    2. SHA-256 hash of Bearer token absent from sensor_tokens → 401 (unknown_sensor_token).
    3. hmac.compare_digest defense-in-depth on matched row (D-03 timing-safe).
    4. revoked_at set on the row → 401 (revoked_sensor_token).
    5. Valid active token → request.state.sensor_id = token_row.sensor_id.

    Token never logged (T-102-09 / T-113-05).
    All 401 branches write an IntegrationDelivery audit row (D-09).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    scan_id = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _audit_and_raise(status_code: int, error_summary: str, detail: str) -> None:
        """Write an IntegrationDelivery audit row, commit, then raise HTTPException."""
        row = IntegrationDelivery(
            scan_id=scan_id,
            finding_hash=None,
            destination="sensor_push",
            status="failed",
            attempted_at=now,
            error_summary=error_summary,
        )
        db.add(row)
        try:
            db.commit()
        except Exception as exc:
            logger.warning("Audit row commit failed: %s", safe_str(exc))
        raise HTTPException(status_code=status_code, detail=detail)

    # 0. Optional network allowlist (defense-in-depth, off by default). Checked
    #    before token validation so an off-allowlist source never reaches token
    #    handling. request.client.host is the real sensor IP when the console
    #    runs behind a trusted reverse proxy (uvicorn proxy_headers).
    allow_nets = _ip_allowlist()
    if allow_nets:
        client_host = request.client.host if request.client else None
        if not _ip_allowed(client_host, allow_nets):
            _audit_and_raise(403, "sensor_ip_not_allowed", "Sensor source IP not permitted")

    # 1. Missing Authorization header
    if credentials is None:
        _audit_and_raise(401, "missing_sensor_token", "Sensor authentication required")

    # 2. Hash the presented token and look it up in sensor_tokens
    hashed = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    token_row = db.query(SensorToken).filter(SensorToken.token_hash == hashed).first()

    if token_row is None:
        _audit_and_raise(401, "unknown_sensor_token", "Unknown sensor token")

    # 3. Defense-in-depth: timing-safe compare on the matched row (D-03 / T-113-06)
    #    Both sides are SHA-256 hex strings (equal length) — no timing oracle.
    if not hmac.compare_digest(hashed, token_row.token_hash):
        # Should be unreachable given the ORM filter, but kept as a belt-and-suspenders
        # measure; still emits the unknown_sensor_token audit summary.
        _audit_and_raise(401, "unknown_sensor_token", "Unknown sensor token")

    # 4. Revocation check
    if token_row.revoked_at is not None:
        _audit_and_raise(401, "revoked_sensor_token", "Sensor token revoked")

    # 5. Valid active token — attach token-resolved sensor_id to request state (D-04)
    request.state.sensor_id = token_row.sensor_id
