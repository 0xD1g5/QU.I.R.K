"""PDF export tests — Wave 0 stubs (RED state).
Test IDs match .planning/phases/05-web-dashboard/05-VALIDATION.md verification map.
"""
import pytest


def test_pdf_export_endpoint(dashboard_client):
    """UI-04: POST /api/export/pdf returns 200 and a PDF binary response."""
    pytest.skip("stub — implement in 05-06")


def test_pdf_export_graceful_degradation():
    """UI-04: POST /api/export/pdf returns 503 with helpful message when playwright chromium not installed."""
    pytest.skip("stub — implement in 05-06")
