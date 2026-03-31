"""Dashboard API tests — Wave 0 stubs (RED state).
Test IDs match .planning/phases/05-web-dashboard/05-VALIDATION.md verification map.
"""
import subprocess
import sys
import pytest


def test_serve_command():
    """UI-01: quirk serve subcommand exists in run_scan.py and exits 0 for --help."""
    result = subprocess.run(
        [sys.executable, "run_scan.py", "serve", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--port" in result.stdout
    assert "--host" in result.stdout
    assert "--no-open" in result.stdout


def test_dashboard_loads(dashboard_client):
    """UI-01: GET / returns 200 (SPA index.html or placeholder served)."""
    response = dashboard_client.get("/")
    assert response.status_code == 200


def test_health_endpoint(dashboard_client):
    """UI-01: GET /api/health returns {status: ok}."""
    response = dashboard_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_score_endpoint(dashboard_client):
    """UI-02: GET /api/scan/latest returns score fields."""
    pytest.skip("stub — implement in 05-04")


def test_findings_endpoint(dashboard_client):
    """UI-03: GET /api/scan/latest includes findings list."""
    pytest.skip("stub — implement in 05-04")


def test_certificates_endpoint(dashboard_client):
    """UI-03: GET /api/scan/latest includes certificates list."""
    pytest.skip("stub — implement in 05-04")


def test_cbom_endpoint(dashboard_client):
    """UI-03: GET /api/scan/latest includes cbom_components list."""
    pytest.skip("stub — implement in 05-04")
