"""Regression test — oversized CIDR + forced nmap discovery must be ACCEPTED
(201) and chunked into sequential batches, not rejected 422.

Phase 144 / D-02 policy change: this test file originally asserted a 422
fail-fast reject for oversized CIDRs (Phase 71/121-era stopgap), because nmap
discovery ran as a single subprocess covering the whole target set with one
hardcoded 300s timeout — an oversized CIDR would grind through nmap's
--host-timeout 10s per unreachable host until that wall clock killed it.

Phase 144 replaces the single-shot subprocess with a sequential batch loop
(run_scan.py, Plan 144-02) over a deduplicated host list, chunked at
_MAX_HOSTS_PER_CIDR (1024) hosts per batch, each batch getting its own fresh
timeout. There is no longer a total-range ceiling (D-02) — large ranges are
chunked, not rejected. These tests are rewritten to assert 201 acceptance for
the same oversized-CIDR POST bodies that used to assert 422.

pytest -q tests/test_jobs_nmap_scope_cap.py
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base


def _make_test_engine():
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _app_with_db():
    engine = _make_test_engine()
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app, TestClient(app, raise_server_exceptions=False)


class _FakeProc:
    def __init__(self):
        self.pid = 99999
        self.returncode = None

    def poll(self):
        return self.returncode


def _fake_popen(*args, **kwargs):
    return _FakeProc()


def test_oversized_cidr_accepted_and_chunked_when_nmap_forced(monkeypatch, tmp_path):
    """Phase 144 / D-02: a /16 CIDR (65534 usable hosts) with the default
    port_scope="top1000" (which forces nmap) must now be ACCEPTED (201) —
    the batch loop chunks it into ~64 sequential batches instead of the old
    422 fail-fast reject."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    _app, tc = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "10.0.0.0/16", "port_scope": "top1000"},
        headers={"X-Quirk-Request": "1"},
    )

    assert response.status_code == 201, (
        f"Oversized CIDR with nmap forced must now be 201 (chunked, Phase 144 "
        f"D-02), got {response.status_code}: {response.text}"
    )


def test_oversized_cidr_allowed_when_nmap_not_forced(monkeypatch, tmp_path):
    """The same /16 CIDR with port_scope="common" (no nmap) must NOT be blocked
    by this guard — the existing target_expander.py cap governs the actual scan
    phase separately; this guard only protects the nmap discovery subprocess."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    _app, tc = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "10.0.0.0/16", "port_scope": "common"},
        headers={"X-Quirk-Request": "1"},
    )

    assert response.status_code == 201, (
        f"Oversized CIDR without nmap forced must not be blocked by this guard, "
        f"got {response.status_code}: {response.text}"
    )


def test_small_cidr_allowed_with_nmap_forced(monkeypatch, tmp_path):
    """A /24 CIDR (254 usable hosts, well under the 1024 cap) with nmap forced
    must be accepted normally."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    _app, tc = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "10.0.0.0/24", "port_scope": "top1000"},
        headers={"X-Quirk-Request": "1"},
    )

    assert response.status_code == 201, (
        f"Small CIDR with nmap forced must be accepted, got {response.status_code}: {response.text}"
    )


def test_multiple_small_cidrs_summing_over_cap_accepted_and_chunked(monkeypatch, tmp_path):
    """Phase 144 / D-02: two /22 CIDRs (1022 hosts each) sum to over 2000
    hosts combined — previously rejected by a combined-total guard, now
    ACCEPTED (201) and split into separate sequential batches."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    _app, tc = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "10.0.0.0/22,10.1.0.0/22", "port_scope": "top1000"},
        headers={"X-Quirk-Request": "1"},
    )

    assert response.status_code == 201, (
        f"Combined CIDRs over the old total cap must now be 201 (chunked, "
        f"Phase 144 D-02), got {response.status_code}: {response.text}"
    )
