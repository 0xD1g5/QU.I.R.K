"""Shared fixtures for dashboard test suite."""
import pytest


@pytest.fixture
def dashboard_client():
    """FastAPI TestClient for the dashboard app.
    Import deferred — dashboard/api/app.py created in 05-02.
    """
    try:
        from quirk.dashboard.api.app import app
        from fastapi.testclient import TestClient
        return TestClient(app)
    except ImportError:
        pytest.skip("quirk.dashboard not yet implemented")
