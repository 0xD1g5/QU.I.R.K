"""Regression test — oversized CIDR + forced nmap discovery must fail fast (422),
not grind through nmap's hardcoded 300s discovery timeout and crash mid-scan.

Root cause: the dashboard's "New Scan" form defaults port_scope to "top1000",
which forces nmap discovery (jobs.py force_nmap) with a hardcoded 300s timeout.
target_expander.py's expand_targets() already caps CIDR expansion at
_MAX_HOSTS_PER_CIDR (1024) for the main scan phase, but nmap discovery runs as
an earlier, separate subprocess that never consults that cap — an oversized
CIDR sails straight into `subprocess.run(..., timeout=300)`, which is
essentially guaranteed to time out against thousands of unreachable hosts
(--host-timeout 10s / --max-parallelism 100 means worst case ~=
(hosts / 100) * 10s). Reported live: "RuntimeError: Nmap discovery timed out
after 300s" every time a user submitted a large CIDR via the dashboard.

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


def test_oversized_cidr_rejected_422_when_nmap_forced(monkeypatch, tmp_path):
    """A /16 CIDR (65534 usable hosts) with the default port_scope="top1000"
    (which forces nmap) must be rejected with 422 before any subprocess spawns —
    not accepted and left to time out 300s later."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    _app, tc = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "10.0.0.0/16", "port_scope": "top1000"},
        headers={"X-Quirk-Request": "1"},
    )

    assert response.status_code == 422, (
        f"Oversized CIDR with nmap forced must be 422, got {response.status_code}: {response.text}"
    )
    assert "1024" in response.text or "hosts" in response.text.lower()


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


def test_multiple_small_cidrs_summing_over_cap_rejected(monkeypatch, tmp_path):
    """Two /22 CIDRs (1022 hosts each) each pass the per-CIDR cap individually
    but sum to over 2000 hosts — must be rejected as a combined-total guard,
    not silently accepted and left to grind past the 300s nmap budget."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    _app, tc = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "10.0.0.0/22,10.1.0.0/22", "port_scope": "top1000"},
        headers={"X-Quirk-Request": "1"},
    )

    assert response.status_code == 422, (
        f"Combined CIDRs over the total cap must be 422, got {response.status_code}: {response.text}"
    )
