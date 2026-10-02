"""PDF export tests."""
import pytest

from quirk.errors import format_error


@pytest.mark.skip(reason="TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_pdf_exportpy-test_pdf_export_endpoint")
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


class _FakePage:
    """Records the image-settle predicate; optionally raises on it."""

    def __init__(self, image_wait_exc=None):
        self.predicates = []
        self._exc = image_wait_exc

    def route(self, *a, **k):
        pass

    def goto(self, *a, **k):
        pass

    def wait_for_selector(self, *a, **k):
        pass

    def wait_for_function(self, expression, **k):
        self.predicates.append(expression)
        if self._exc is not None:
            raise self._exc

    def pdf(self, **k):
        return b"%PDF-1.4 fake"


def _fake_playwright(page):
    import unittest.mock as mock

    browser = mock.MagicMock()
    browser.new_context.return_value.new_page.return_value = page
    pw = mock.MagicMock()
    pw.chromium.launch.return_value = browser
    cm = mock.MagicMock()
    cm.__enter__.return_value = pw
    return mock.MagicMock(return_value=cm)


def test_pdf_image_wait_does_not_fail_export_on_timeout(dashboard_client):
    """WR-01: an image that never settles must not turn the export into a 503/500."""
    import unittest.mock as mock

    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    page = _FakePage(image_wait_exc=PlaywrightTimeoutError("Timeout 15000ms exceeded"))
    with mock.patch("quirk.dashboard.api.routes.pdf.sync_playwright", _fake_playwright(page)):
        resp = dashboard_client.post("/api/export/pdf")
    assert resp.status_code == 200, resp.text
    assert resp.content.startswith(b"%PDF")
    assert page.predicates, "export no longer waits for images at all"


def test_pdf_image_wait_predicate_accepts_broken_image(dashboard_client):
    """WR-01: the predicate must be satisfied by a broken (404) image, which is complete
    with naturalWidth 0 -- the wait is for settling, not for successful decode."""
    import unittest.mock as mock

    from playwright.sync_api import sync_playwright as real_pw

    page = _FakePage()
    with mock.patch("quirk.dashboard.api.routes.pdf.sync_playwright", _fake_playwright(page)):
        dashboard_client.post("/api/export/pdf")
    assert page.predicates
    with real_pw() as p:
        browser = p.chromium.launch(headless=True)
        try:
            pg = browser.new_page()
            pg.set_content('<img src="http://127.0.0.1:9/nope.svg">')
            pg.wait_for_function(page.predicates[0], timeout=5_000)
        finally:
            browser.close()
