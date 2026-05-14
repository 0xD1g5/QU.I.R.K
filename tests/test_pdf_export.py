"""PDF export tests."""
import pytest

from quirk.errors import format_error


def test_pdf_export_endpoint(dashboard_client):
    """UI-04: POST /api/export/pdf returns 200 (PDF) or 503 (chromium absent)."""
    resp = dashboard_client.post("/api/export/pdf")
    # 200 = PDF generated; 503 = playwright chromium not installed (both valid in CI)
    assert resp.status_code in (200, 503), f"Unexpected status: {resp.status_code}"
    if resp.status_code == 200:
        assert resp.headers["content-type"] == "application/pdf"
        assert len(resp.content) > 1000  # non-empty PDF
    else:
        body = resp.json()
        assert "detail" in body
        assert "QRK-DASHBOARD-" in body["detail"]


def test_pdf_export_graceful_degradation(dashboard_client):
    """UI-04: POST /api/export/pdf returns 503 with helpful message when chromium absent."""
    import unittest.mock as mock

    with mock.patch(
        "quirk.dashboard.api.routes.pdf.sync_playwright",
        side_effect=Exception("Executable doesn't exist at /path/to/chromium"),
    ):
        resp = dashboard_client.post("/api/export/pdf")
    assert resp.status_code == 503
    body = resp.json()
    assert body["detail"] == format_error("DASHBOARD-012")
