"""Dashboard API tests — Wave 0 stubs (RED state).
Test IDs match .planning/phases/05-web-dashboard/05-VALIDATION.md verification map.
"""
import pytest


def test_serve_command():
    """UI-01: quirk serve subcommand exists in run_scan.py or pyproject.toml scripts."""
    pytest.skip("stub — implement in 05-02")


def test_dashboard_loads(dashboard_client):
    """UI-01: GET / returns 200 (SPA index.html served)."""
    pytest.skip("stub — implement in 05-02")


def test_health_endpoint(dashboard_client):
    """UI-01: GET /api/health returns {status: ok}."""
    pytest.skip("stub — implement in 05-02")


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
