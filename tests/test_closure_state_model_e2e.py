"""FIND-11 / D-07: end-to-end proof of the closure state model on PRODUCTION writers.

Every row below is written in pipeline order by the real code:
``derive_report_findings`` -> ``persist_remediation_snapshot`` ->
``assess_probe_health`` -> ``ScanScopeSignature`` -> ``compute_closure``.
Nothing is hand-seeded as "open" or "closed" (a broken helper would fail the
positive cases as well as the negatives).

Phase 224 probe shape: scan 1 raises the issue on 8 hosts, scan 2 on 7.

Pitfall 3: a plaintext-HTTP finding is HIGH, so it lands in BOTH
``plaintext-http-exposure`` and ``high-impact-findings``; assertions are per slug.
Pitfall 4: the closed row's burndown bucket follows the CURRENT endpoint, so
buckets are asserted one by one and never summed.

Observed burndown (HTTP fast mode, h7 moved to TLS on scan 2), per bucket
{open, closed, not_observed}, ``_BURNDOWN_PIN`` below holds the exact dicts:
    scan 1 before scan 2 ran: {"unmapped": open 16, closed 0, not_observed 0}
    scan 1 after scan 2's closure: unmapped open 14, closed 2 (closure also
        flips the PRIOR scan's h7 rows, one per slug)
    scan 2: unmapped open 14, closed 2
    scan 3: unmapped open 14, closed 0
    The 16/14/2 are two slugs (plaintext-http-exposure AND high-impact-findings,
    Pitfall 3) x 8/7/1 hosts. Plaintext HTTP has no algorithm, so every row sits
    in the single "unmapped" bucket; the plan's predicted bucket movement
    (Pitfall 4) does not arise for this shape. The plan's "scan 1 closed == 0"
    holds for scan 1 as recorded before scan 2's closure, not after.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from quirk.cbom.builder import _make_vex_entry
from quirk.db import get_session, init_db
from quirk.engine.findings_evaluator import derive_report_findings
from quirk.intelligence.burndown import compute_burndown
from quirk.intelligence.closure import compute_closure
from quirk.intelligence.remediation import item_progress
from quirk.intelligence.remediation_persist import persist_remediation_snapshot
from quirk.intelligence.scope_signature import SCOPE_SIGNATURE_VERSION, assess_probe_health
from quirk.models import (
    CryptoEndpoint,
    RemediationClosureEvent,
    RemediationItem,
    RemediationItemFingerprint,
    ScanScopeSignature,
)
from quirk.reports.writer import _load_remediation_items

S1, S2, S3 = "scan-e2e-1", "scan-e2e-2", "scan-e2e-3"
HTTP_SLUG = "plaintext-http-exposure"
TLS_SLUG = "legacy-tls-versions"
N = 8
FAST_TIMINGS = {"fingerprinting": 1.0, "tls_scanning": 1.0, "ssh_scanning": 1.0}
_T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# endpoint factories
# ---------------------------------------------------------------------------
def http_ep(i, sid=None):
    return CryptoEndpoint(
        host=f"h{i}", port=80, protocol="HTTP", service_detail="HTTP/1.1 200 OK",
        tls_version="HTTP/1.1 200 OK", scan_run_id=sid,
    )


def tls_ep(i, sid=None, *, port=80, legacy=False, caps=True, scan_error=None):
    return CryptoEndpoint(
        host=f"h{i}", port=port, protocol="TLS",
        tls_version="TLSv1" if legacy else "TLSv1.3",
        tls_supported_versions="TLSv1,TLSv1.2" if legacy else "TLSv1.2,TLSv1.3",
        tls_capabilities_json=json.dumps({"ok": True}) if caps else None,
        scan_error=scan_error, scan_run_id=sid,
    )


def closed_ep(i, detail, sid=None, port=80):
    return CryptoEndpoint(host=f"h{i}", port=port, protocol="CLOSED", service_detail=detail, scan_run_id=sid)


def advisory_ep(i, sid=None, port=80):
    return CryptoEndpoint(
        host=f"h{i}", port=port, protocol="ADVISORY", scan_error="x",
        scan_error_category="missing_extra", scan_run_id=sid,
    )


def unknown_ep(i, sid=None, port=80, detail="OPEN_NOT_TLS"):
    """What run_scan.py writes when ``_http_probe_plain`` (or an SSH banner read)
    times out: ``fingerprint_service`` returns ``(True, "UNKNOWN", "OPEN_NOT_TLS")``
    and the row carries no ``scan_error`` (229-REVIEW CR-01)."""
    return CryptoEndpoint(host=f"h{i}", port=port, protocol="UNKNOWN", service_detail=detail, scan_run_id=sid)


def rest_fuzz_ep(i, sid=None, port=80):
    return CryptoEndpoint(host=f"h{i}", port=port, protocol="REST_FUZZ", scan_run_id=sid)


def openapi_ep(i, sid=None, port=443):
    return CryptoEndpoint(host=f"h{i}", port=port, protocol="OPENAPI", scan_run_id=sid)


def _cfg(tls_mode):
    return SimpleNamespace(
        scan=SimpleNamespace(tls_enum_mode=tls_mode, tls_designated_ports=[]),
        connectors=SimpleNamespace(),
    )


# ---------------------------------------------------------------------------
# the pipeline-order helper
# ---------------------------------------------------------------------------
def _run_scan(db_path, sid, order, endpoints, *, tls_mode="fast", timings=None):
    """One scan in pipeline order. ``endpoints`` is a list of unsaved rows."""
    timings = FAST_TIMINGS if timings is None else timings
    with get_session(db_path) as s:
        for ep in endpoints:
            ep.scan_run_id = sid
            s.add(ep)
        s.commit()
        for ep in endpoints:
            s.refresh(ep)
        s.expunge_all()
    findings = derive_report_findings(endpoints)
    persist_remediation_snapshot(db_path, sid, endpoints, findings)
    health = assess_probe_health(_cfg(tls_mode), endpoints, {"timings_sec": timings})
    with get_session(db_path) as s:
        s.add(ScanScopeSignature(
            scan_run_id=sid, signature_version=SCOPE_SIGNATURE_VERSION, digest="same",
            target_set_digest="tsd", probe_health_json=json.dumps(health),
            created_at=_T0 + timedelta(days=order),
        ))
        s.commit()
    return compute_closure(db_path, sid)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "q.db")
    init_db(path)
    return path


def _fp_states(db_path, sid, slug, host=None):
    with get_session(db_path) as s:
        q = s.query(RemediationItemFingerprint).filter_by(scan_run_id=sid, slug=slug)
        if host:
            q = q.filter_by(host=host)
        return sorted(r.state for r in q.all())


def _count(db_path, model):
    with get_session(db_path) as s:
        return s.query(model).count()


def _vex_for(db_path, sid, slug):
    items = [i for i in _load_remediation_items(db_path, sid) if i["slug"] == slug]
    assert items, f"no item for {slug} on {sid}"
    return _make_vex_entry(items[0]).analysis.state.name


def _burn(db_path, sid):
    with get_session(db_path) as s:
        b = compute_burndown(s, scan_run_id=sid)
    return {k: {x: v[x] for x in ("open", "closed", "not_observed")} for k, v in b.items()
            if v["fingerprints"]}


def _http_scan1(db_path):
    return _run_scan(db_path, S1, 0, [http_ep(i) for i in range(N)])


def _http_scan2(db_path, moved=(7,), **kw):
    eps = [tls_ep(i) if i in moved else http_ep(i) for i in range(N)]
    return _run_scan(db_path, S2, 1, eps, **kw)


_BURNDOWN_PIN = {
    "S1_before": {"unmapped": {"open": 16, "closed": 0, "not_observed": 0}},
    "S1_after": {"unmapped": {"open": 14, "closed": 2, "not_observed": 0}},
    "S2": {"unmapped": {"open": 14, "closed": 2, "not_observed": 0}},
    "S3": {"unmapped": {"open": 14, "closed": 0, "not_observed": 0}},
}


# ---------------------------------------------------------------------------
# Task 1
# ---------------------------------------------------------------------------
def test_scan1_detected_rows_are_open_and_vex_exploitable(db):
    _http_scan1(db)
    assert _fp_states(db, S1, HTTP_SLUG) == ["open"] * N
    with get_session(db) as s:
        item = s.query(RemediationItem).filter_by(scan_run_id=S1, slug=HTTP_SLUG).one()
        assert item.state == "open"
    assert _vex_for(db, S1, HTTP_SLUG) == "EXPLOITABLE"


def test_http_fast_mode_one_fixed_closes_on_scan2(db):
    _http_scan1(db)
    s1_before = _burn(db, S1)  # scan 1 as recorded by its own pipeline run
    counters = _http_scan2(db)
    assert counters["closed"] >= 1
    assert _fp_states(db, S2, HTTP_SLUG) == ["closed"] + ["open"] * 7
    assert _fp_states(db, S2, HTTP_SLUG, host="h7") == ["closed"]
    assert _fp_states(db, S1, HTTP_SLUG, host="h7") == ["closed"]
    with get_session(db) as s:
        assert item_progress(s, scan_run_id=S2, slug=HTTP_SLUG) == (1, 8)
        events = s.query(RemediationClosureEvent).filter_by(
            scan_run_id=S2, slug=HTTP_SLUG, event_type="closed").all()
        assert len(events) == 1
        b2 = compute_burndown(s, scan_run_id=S2)
    assert all(v["closed"] == 0 for v in s1_before.values())
    assert any(v["closed"] >= 1 for v in b2.values())
    assert s1_before == _BURNDOWN_PIN["S1_before"]
    assert _burn(db, S1) == _BURNDOWN_PIN["S1_after"]
    assert _burn(db, S2) == _BURNDOWN_PIN["S2"]


def test_http_all_fixed_closes_every_host(db):
    _http_scan1(db)
    counters = _http_scan2(db, moved=tuple(range(N)))
    assert counters["closed"] >= N
    assert _fp_states(db, S2, HTTP_SLUG) == ["closed"] * N
    with get_session(db) as s:
        item = s.query(RemediationItem).filter_by(scan_run_id=S2, slug=HTTP_SLUG).one()
        assert item.state == "closed"
    assert _vex_for(db, S2, HTTP_SLUG) == "RESOLVED"


def test_rerun_is_idempotent_in_rows_and_events(db):
    _http_scan1(db)
    _http_scan2(db)
    before = tuple(_count(db, m) for m in (RemediationItemFingerprint, RemediationItem, RemediationClosureEvent))
    compute_closure(db, S2)
    after = tuple(_count(db, m) for m in (RemediationItemFingerprint, RemediationItem, RemediationClosureEvent))
    assert before == after


# ---------------------------------------------------------------------------
# Task 2: TLS deep / fast (D-06)
# ---------------------------------------------------------------------------
def _tls_scans(db, tls_mode):
    _run_scan(db, S1, 0, [tls_ep(i, port=443, legacy=True) for i in range(N)], tls_mode=tls_mode)
    return _run_scan(
        db, S2, 1,
        [tls_ep(i, port=443, legacy=(i != 7)) for i in range(N)], tls_mode=tls_mode,
    )


def test_tls_deep_mode_closes_fixed_host(db):
    counters = _tls_scans(db, "deep")
    assert counters["closed"] >= 1
    assert _fp_states(db, S2, TLS_SLUG, host="h7") == ["closed"]
    assert _fp_states(db, S2, TLS_SLUG) == ["closed"] + ["open"] * 7


def test_tls_fast_mode_refuses_fixed_host(db):
    """D-06 pin: fast-mode TLS closure is deferred to HORIZON, not a defect."""
    counters = _tls_scans(db, "fast")
    assert counters["refused_probe"] >= 1
    assert counters["closed"] == 0
    assert "closed" not in _fp_states(db, S2, TLS_SLUG)


# ---------------------------------------------------------------------------
# Task 2: guardrail negatives built from real probe health (D-20, D-22)
# ---------------------------------------------------------------------------
_NEGATIVES = {
    "closed-timeout": dict(h7=lambda: closed_ep(7, "TIMEOUT")),
    "closed-unreachable": dict(h7=lambda: closed_ep(7, "UNREACHABLE")),
    "advisory-only": dict(h7=lambda: advisory_ep(7)),
    "tls-scan-error": dict(h7=lambda: tls_ep(7, scan_error="handshake failed")),
    # CR-01: an HTTP-probe timeout row, while http is healthy on h0..h6.
    "unknown-open-not-tls": dict(h7=lambda: unknown_ep(7)),
    "no-fingerprinting-timing": dict(
        h7=lambda: tls_ep(7), timings={"tls_scanning": 1.0, "ssh_scanning": 1.0}),
}


@pytest.mark.parametrize("case", sorted(_NEGATIVES))
def test_guardrail_negatives_refuse_and_write_no_closed_row(db, case):
    spec = _NEGATIVES[case]
    _http_scan1(db)
    eps = [http_ep(i) for i in range(7)] + [spec["h7"]()]
    counters = _run_scan(db, S2, 1, eps, timings=spec.get("timings"))
    assert counters["refused_probe"] >= 1, counters
    assert counters["closed"] == 0
    assert _fp_states(db, S2, HTTP_SLUG, host="h7") == []
    assert _fp_states(db, S1, HTTP_SLUG, host="h7") == ["open"]


def _probe_status(db_path, sid, family):
    with get_session(db_path) as s:
        sig = s.query(ScanScopeSignature).filter_by(scan_run_id=sid).one()
        return json.loads(sig.probe_health_json)[family]["status"]


def test_unknown_row_refused_when_http_has_no_targets(db):
    """CR-01: h0..h6 move to TLS (so http reports ``no_targets``, which D-21 accepts
    as a recheck) and h7's probe times out to an UNKNOWN row. The seven rechecked
    hosts close; h7 must not close on a timeout."""
    _http_scan1(db)
    eps = [tls_ep(i) for i in range(7)] + [unknown_ep(7)]
    counters = _run_scan(db, S2, 1, eps)
    assert _probe_status(db, S2, "http") == "no_targets"
    assert counters["closed"] == 14, counters  # 7 hosts x 2 slugs (Pitfall 3)
    assert counters["refused_probe"] >= 1, counters
    assert "closed" not in _fp_states(db, S2, HTTP_SLUG, host="h7")
    assert _fp_states(db, S1, HTTP_SLUG, host="h7") == ["open"]


def test_tls_finding_on_unknown_row_refused_in_deep_mode(db):
    """CR-01, another family: a legacy-TLS finding whose host:port now answers as
    UNKNOWN (a handshake/banner timeout) must not close because ``tls`` is healthy
    on the other seven hosts."""
    _run_scan(db, S1, 0, [tls_ep(i, port=443, legacy=True) for i in range(N)], tls_mode="deep")
    eps = [tls_ep(i, port=443, legacy=True) for i in range(7)] + [unknown_ep(7, port=443)]
    counters = _run_scan(db, S2, 1, eps, tls_mode="deep")
    assert _probe_status(db, S2, "tls") == "healthy"
    assert counters["closed"] == 0, counters
    assert counters["refused_probe"] >= 1, counters
    assert _fp_states(db, S1, TLS_SLUG, host="h7") == ["open"]


def test_failed_snapshot_never_reads_as_every_finding_gone(db, monkeypatch):
    """CR-02: scan 2's remediation snapshot fails (the writer swallows the error),
    so scan 2 has no fingerprint rows at all. Without a guard, clause (e) holds for
    every prior fingerprint and all 8 hosts close although nothing was fixed."""
    import quirk.intelligence.remediation_persist as persist_mod

    _http_scan1(db)

    def _boom(*_a, **_k):
        raise RuntimeError("simulated snapshot failure")

    monkeypatch.setattr(persist_mod, "build_phased_roadmap", _boom)
    counters = _run_scan(db, S2, 1, [http_ep(i) for i in range(N)])
    assert counters["closed"] == 0, counters
    assert counters["refused_missing_snapshot"] == 1, counters
    assert _fp_states(db, S1, HTTP_SLUG) == ["open"] * N
    assert _fp_states(db, S2, HTTP_SLUG) == []
    assert _count(db, RemediationClosureEvent) == 0


def test_unmapped_protocol_http_restfuzz_refused(db):
    """D-20: prior {HTTP, REST_FUZZ} at h7:80 has an unmapped protocol -> refuse."""
    _run_scan(db, S1, 0, [http_ep(i) for i in range(N)] + [rest_fuzz_ep(7)])
    eps = [http_ep(i) for i in range(7)] + [tls_ep(7)]
    counters = _run_scan(db, S2, 1, eps)
    assert counters["refused_probe"] >= 1
    assert counters["closed"] == 0
    assert _fp_states(db, S2, HTTP_SLUG, host="h7") == []


def test_unmapped_protocol_tls_openapi_refused_in_deep_mode(db):
    """D-20: prior {TLS, OPENAPI} at h7:443, tls healthy in deep mode -> refuse."""
    _run_scan(db, S1, 0, [tls_ep(i, port=443, legacy=True) for i in range(N)] + [openapi_ep(7)],
              tls_mode="deep")
    eps = [tls_ep(i, port=443, legacy=(i != 7)) for i in range(N)]
    counters = _run_scan(db, S2, 1, eps, tls_mode="deep")
    assert counters["refused_probe"] >= 1
    assert counters["closed"] == 0
    assert _fp_states(db, S2, TLS_SLUG, host="h7") == []


# ---------------------------------------------------------------------------
# Task 2: third scan
# ---------------------------------------------------------------------------
def test_third_scan_does_not_recount_closure(db):
    """Scan 3 repeats scan 2's endpoints. Observed scan-3 state:
    plaintext-http-exposure is 7 open / 0 closed on scan 3's own rows (the
    closure was recorded on scan 2, the scan that observed it, and is not
    re-counted); burndown scan 3 = unmapped open 14 (7 hosts x 2 slugs),
    closed 0. No new closure events or closed rows are written."""
    _http_scan1(db)
    _http_scan2(db)
    before = tuple(_count(db, m) for m in (RemediationClosureEvent,))
    closed_before = _count_closed(db)
    eps = [tls_ep(7) if i == 7 else http_ep(i) for i in range(N)]
    counters = _run_scan(db, S3, 2, eps)
    assert counters["closed"] == 0
    assert tuple(_count(db, m) for m in (RemediationClosureEvent,)) == before
    assert _count_closed(db, exclude=S3) == closed_before
    assert _fp_states(db, S3, HTTP_SLUG) == ["open"] * 7
    assert "closed" not in _fp_states(db, S3, HTTP_SLUG)
    assert _burn(db, S3) == _BURNDOWN_PIN["S3"]


def _count_closed(db_path, exclude=None):
    with get_session(db_path) as s:
        q = s.query(RemediationItemFingerprint).filter_by(state="closed")
        if exclude:
            q = q.filter(RemediationItemFingerprint.scan_run_id != exclude)
        return q.count()
