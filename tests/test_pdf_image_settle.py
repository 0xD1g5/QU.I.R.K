"""Phase 222 WR-01: the export's image wait settles on a broken image (real Chromium).

Deliberately NOT in tests/test_browser_e2e.py: every node there must fail loudly when
the dashboard server dies (tests/test_browser_e2e_skip_contract.py), and this check never
starts a server. It runs for real in the Browser E2E job (python-ci.yml) and skips in
Linux Full Suite through chromium_page()'s registered skip, where Chromium is absent.
"""

from __future__ import annotations

from quirk.dashboard.api.routes.pdf import IMAGE_SETTLE_PREDICATE
from tests.browser_e2e_harness import chromium_page


def test_222_image_settle_predicate_accepts_broken_image():
    """A broken (404) image is `complete` with naturalWidth 0; the predicate must settle
    on it rather than stall the export until its 15s timeout."""
    with chromium_page() as page:
        page.set_content('<img src="http://127.0.0.1:9/nope.svg">')
        page.wait_for_function(IMAGE_SETTLE_PREDICATE, timeout=5_000)
        assert page.evaluate("document.images[0].naturalWidth") == 0
