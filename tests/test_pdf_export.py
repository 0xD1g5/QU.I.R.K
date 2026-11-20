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
        self.urls = []
        self._exc = image_wait_exc

    def route(self, *a, **k):
        pass

    def goto(self, url, *a, **k):
        self.urls.append(url)

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


def test_pdf_image_wait_uses_the_settle_predicate(dashboard_client):
    """WR-01: the export waits on IMAGE_SETTLE_PREDICATE (complete, not decoded).

    Its real-browser behaviour against a broken image is proven in
    tests/test_pdf_image_settle.py::test_222_image_settle_predicate_accepts_broken_image,
    which runs in the Browser E2E job (Chromium is absent from Linux Full Suite).
    """
    import unittest.mock as mock

    from quirk.dashboard.api.routes.pdf import IMAGE_SETTLE_PREDICATE

    page = _FakePage()
    with mock.patch("quirk.dashboard.api.routes.pdf.sync_playwright", _fake_playwright(page)):
        resp = dashboard_client.post("/api/export/pdf")
    assert resp.status_code == 200, resp.text
    assert page.predicates == [IMAGE_SETTLE_PREDICATE]
    assert "naturalWidth" not in IMAGE_SETTLE_PREDICATE


# 261120-export-pdf-ignores-selected-scan: the scan selected in the dashboard lives in
# in-tab React state, so the export must carry it to the server-side /print render.

def _query(url):
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    return parsed.path, parse_qs(parsed.query)


def test_pdf_export_prints_the_selected_scan(dashboard_client):
    import unittest.mock as mock

    scan_id = "2026-11-19 23:42:32.617768"
    page = _FakePage()
    with mock.patch("quirk.dashboard.api.routes.pdf.sync_playwright", _fake_playwright(page)):
        resp = dashboard_client.post("/api/export/pdf", json={"scan_id": scan_id})
    assert resp.status_code == 200, resp.text
    assert len(page.urls) == 1
    path, query = _query(page.urls[0])
    assert path == "/print"
    assert query == {"scan_id": [scan_id]}


def test_pdf_export_without_a_selection_prints_the_latest_scan(dashboard_client):
    import unittest.mock as mock

    for kwargs in ({}, {"json": {}}, {"json": {"scan_id": None}}):
        page = _FakePage()
        with mock.patch("quirk.dashboard.api.routes.pdf.sync_playwright", _fake_playwright(page)):
            resp = dashboard_client.post("/api/export/pdf", **kwargs)
        assert resp.status_code == 200, (kwargs, resp.text)
        assert _query(page.urls[0]) == ("/print", {}), kwargs


@pytest.mark.parametrize(
    "bad",
    ["", "x" * 65, "a&b=c", "../print", "http://evil.example/", "id#frag", "id?x=1", "id/x"],
)
def test_pdf_export_rejects_a_malformed_scan_id(dashboard_client, bad):
    import unittest.mock as mock

    launcher = mock.MagicMock()
    with mock.patch("quirk.dashboard.api.routes.pdf.sync_playwright", launcher):
        resp = dashboard_client.post("/api/export/pdf", json={"scan_id": bad})
    assert resp.status_code == 422, resp.text
    launcher.assert_not_called()
