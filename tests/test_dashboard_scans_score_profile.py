"""DASH-06 regression: GET /api/scans must score each session under its OWN stored
calibration, not the hardcoded ``balanced`` default.

Falsifiability contract (D-04):
- Removing the ``profile=`` kwarg from the ``compute_readiness_score(...)`` call inside
  ``list_scans()`` (quirk/dashboard/api/routes/scan.py) turns
  ``test_list_scans_score_varies_by_calibration`` and
  ``test_list_scans_score_agrees_with_reference_scoring`` RED — both sessions would collapse
  back onto the single hardcoded ``balanced`` score.
- Changing ``profile``/``calibration`` nullability for ``ScanJob``-less (CLI-launched) sessions
  turns ``test_list_scans_cli_scan_still_null_and_balanced`` RED — that test locks the same
  null contract that ``tests/test_dashboard_scan_history.py::test_clone_reconstruction``
  (UI-HIST-01) already locks, and this file must not contradict it.

Ground truth (174-ASSUMPTIONS.md SS A1, A2; 174-CONTEXT.md D-01): ``ScanJob.calibration`` holds
the legal ``strict|balanced|lenient`` vocabulary that ``compute_readiness_score``'s ``profile=``
kwarg expects. ``ScanJob.profile`` holds the DIFFERENT ``quick|standard|deep`` scan-depth
vocabulary and must never be passed as ``profile=`` (scoring.py silently normalises any
unrecognised value back to ``balanced`` -- a no-op that looks like a fix but isn't).

Evidence shape: a single endpoint with an EXPIRED RSA-only certificate. This moves the score
through TWO of the four calibration-multiplied weight prefixes at once (`identity_expired_ratio`
and the flat `agility_rsa_only_penalty`), verified directly against
`quirk.intelligence.scoring.compute_readiness_score` in a scratch REPL before writing these
assertions: strict=79, balanced=85, lenient=89 for the exact evidence built below. An endpoint
with no expired/self-signed/RSA-only signal would score identically under all three calibrations
and make Test 1 vacuously pass-or-fail regardless of the fix.

This file uses no raw Popen/run process-spawning primitives anywhere.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.models import Base, CryptoEndpoint, ScanJob


# ---------------------------------------------------------------------------
# Harness — copied from tests/test_dashboard_scan_history.py (not imported
# across test modules, per that file's own established pattern).
# ---------------------------------------------------------------------------

def _make_client_and_session():
    db_name = f"test_scans_score_profile_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app), TestingSession


def _seed_session(TestingSession, scanned_at: datetime, endpoints: list[dict]):
    db = TestingSession()
    try:
        for ep in endpoints:
            db.add(CryptoEndpoint(scanned_at=scanned_at, **ep))
        db.commit()
    finally:
        db.close()


def _score_moving_endpoint_kwargs(scan_run_id: str, now: datetime) -> dict:
    """A single CryptoEndpoint row whose evidence provably moves the score across
    calibrations: an EXPIRED, RSA-only (no ECDSA) certificate.

    Triggers `identity_expired_ratio` (ratio-scaled) AND the flat
    `agility_rsa_only_penalty` -- both are members of the calibration-multiplied
    `identity_`/`agility_` weight prefixes (scoring.py PROFILE_MULTIPLIERS).
    """
    return dict(
        host="dashboard.example.com",
        port=443,
        protocol="TLS",
        severity="INFO",
        scan_error=None,
        tls_blocker_reason=None,
        service_detail="",
        cert_pubkey_alg="RSA",
        cert_not_after=now - timedelta(days=5),
        cert_subject="CN=dashboard.example.com",
        cert_issuer="CN=Some CA",
        tls_version="TLSv1.3",
        cipher_suite="TLS_AES_256_GCM_SHA384",
        tls_supported_versions="TLSv1.3",
        scan_run_id=scan_run_id,
    )


def _seed_scan_job(TestingSession, scan_run_id: str, target: str, calibration: str):
    db = TestingSession()
    try:
        db.add(ScanJob(
            job_id=str(uuid.uuid4()),
            status="completed",
            target=target,
            profile="deep",  # scan DEPTH vocabulary -- deliberately NOT the calibration value
            calibration=calibration,
            scan_run_id=scan_run_id,
        ))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Test 1 -- score varies by calibration
# ---------------------------------------------------------------------------

def test_list_scans_score_varies_by_calibration():
    """DASH-06: two sessions with IDENTICAL evidence but different ScanJob.calibration
    values must produce DIFFERENT integer scores from GET /api/scans, and the direction
    must match PROFILE_MULTIPLIERS (strict penalises more heavily than lenient, so the
    strict session's score must be LOWER, not merely different).
    """
    client, Session = _make_client_and_session()
    now = datetime.now(timezone.utc)

    strict_ts = now
    strict_run_id = strict_ts.isoformat()
    _seed_session(Session, strict_ts, [_score_moving_endpoint_kwargs(strict_run_id, now)])
    _seed_scan_job(Session, strict_run_id, "strict.example.com", "strict")

    lenient_ts = now - timedelta(minutes=5)
    lenient_run_id = lenient_ts.isoformat()
    _seed_session(Session, lenient_ts, [_score_moving_endpoint_kwargs(lenient_run_id, now)])
    _seed_scan_job(Session, lenient_run_id, "lenient.example.com", "lenient")

    resp = client.get("/api/scans")
    assert resp.status_code == 200
    items = {item["scan_id"]: item for item in resp.json()}

    assert strict_run_id in items, f"strict session missing from /api/scans: {list(items)}"
    assert lenient_run_id in items, f"lenient session missing from /api/scans: {list(items)}"

    strict_score = items[strict_run_id]["score"]
    lenient_score = items[lenient_run_id]["score"]

    assert strict_score != lenient_score, (
        f"Expected DIFFERENT scores for strict vs lenient calibration on identical "
        f"evidence; both returned {strict_score!r} -- the pre-fix symptom is every "
        f"session silently scored under the hardcoded 'balanced' default."
    )
    assert strict_score < lenient_score, (
        f"strict calibration must score LOWER than lenient (PROFILE_MULTIPLIERS strict=1.4x "
        f"balanced=1.0x lenient=0.7x on the same penalty evidence); got strict={strict_score} "
        f"lenient={lenient_score}"
    )


# ---------------------------------------------------------------------------
# Test 2 -- agrees with the reference scoring function
# ---------------------------------------------------------------------------

def test_list_scans_score_agrees_with_reference_scoring():
    """DASH-06: the score GET /api/scans returns for a strict-calibrated session must equal
    calling compute_readiness_score(...) directly on the same evidence with profile="strict".

    This is the "agrees with /api/scan/latest" half of D-04 expressed against the shared
    scoring function `scan.py:1476` already calls correctly -- `/api/scan/latest` itself is
    NOT used here because it additionally depends on an on-disk `intelligence-*.json` file
    resolved via `_resolve_output_dir()`, which is environment-coupled (real filesystem
    output directory) and cannot be deterministically seeded from an in-memory test DB
    without writing outside the test harness. The reference-function form pins the exact
    same contract (`compute_readiness_score(evidence, profile=<calibration>)`) without that
    coupling.
    """
    client, Session = _make_client_and_session()
    now = datetime.now(timezone.utc)
    ts = now
    run_id = ts.isoformat()
    ep_kwargs = _score_moving_endpoint_kwargs(run_id, now)
    _seed_session(Session, ts, [ep_kwargs])
    _seed_scan_job(Session, run_id, "strict.example.com", "strict")

    resp = client.get("/api/scans")
    assert resp.status_code == 200
    items = {item["scan_id"]: item for item in resp.json()}
    assert run_id in items

    class _Ep:
        """Minimal attribute-bearing stand-in matching what build_evidence_summary reads
        off a CryptoEndpoint row -- constructed from the exact same kwargs seeded above."""

    ep_obj = _Ep()
    for k, v in ep_kwargs.items():
        setattr(ep_obj, k, v)
    setattr(ep_obj, "scanned_at", ts)

    reference_evidence = build_evidence_summary([ep_obj])
    reference_score = int(
        compute_readiness_score(reference_evidence, profile="strict")["score"]
    )

    assert items[run_id]["score"] == reference_score, (
        f"/api/scans score {items[run_id]['score']!r} disagrees with the reference "
        f"compute_readiness_score(evidence, profile='strict') result {reference_score!r} "
        f"for the same session's evidence."
    )


# ---------------------------------------------------------------------------
# Test 3 -- inversion guard: CLI scans stay null / balanced
# ---------------------------------------------------------------------------

def test_list_scans_cli_scan_still_null_and_balanced():
    """DASH-06 inversion guard: a session with NO ScanJob row (a CLI-launched scan) must
    keep `profile`/`calibration` as None -- the exact contract
    tests/test_dashboard_scan_history.py::test_clone_reconstruction (UI-HIST-01) locks --
    and its score must equal the profile=None (balanced-fallback) reference computation.
    This proves the DASH-06 fix does not smuggle in a behaviour change to the CLI-scan path.

    Expected to PASS even against pre-fix scan.py -- this is a guard, not a defect probe.
    """
    client, Session = _make_client_and_session()
    now = datetime.now(timezone.utc)
    ts = now
    run_id = ts.isoformat()
    ep_kwargs = _score_moving_endpoint_kwargs(run_id, now)
    _seed_session(Session, ts, [ep_kwargs])
    # Intentionally NO ScanJob row -- CLI-launched scan.

    resp = client.get("/api/scans")
    assert resp.status_code == 200
    items = {item["scan_id"]: item for item in resp.json()}
    assert run_id in items

    item = items[run_id]
    assert item.get("profile") is None, (
        f"Expected profile=None for CLI scan; got {item.get('profile')!r}"
    )
    assert item.get("calibration") is None, (
        f"Expected calibration=None for CLI scan; got {item.get('calibration')!r}"
    )

    class _Ep:
        pass

    ep_obj = _Ep()
    for k, v in ep_kwargs.items():
        setattr(ep_obj, k, v)
    setattr(ep_obj, "scanned_at", ts)

    reference_evidence = build_evidence_summary([ep_obj])
    reference_score = int(
        compute_readiness_score(reference_evidence, profile=None)["score"]
    )

    assert item["score"] == reference_score, (
        f"CLI-scan (no ScanJob) session score {item['score']!r} must equal the "
        f"profile=None balanced-fallback reference {reference_score!r}"
    )
