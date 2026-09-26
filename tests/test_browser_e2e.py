"""Tier-2 browser E2E against the real served dashboard SPA — Phase 207 / COV-05.

Cases this module covers:
  - ``UAT-7-01`` — dashboard loads, no blank screen (this plan, 207-02)
  - ``UAT-7-32`` — zero console errors across every route (added by 207-03)
  - ``UAT-7-17`` — Export PDF click yields a valid downloaded PDF (added by 207-03)

Requirements: a Chromium browser binary **and** a backgrounded uvicorn process serving
``quirk.dashboard.api.app:app`` on a real loopback port. Playwright needs a real HTTP origin, so
the in-process ``TestClient``-based ``dashboard_client`` fixture cannot be used.

CI placement: this module **skips cleanly** in the required ``Linux Full Suite`` job, which
deliberately installs no Chromium, and **executes for real** only in the non-gating Browser E2E job
(D-01 / D-02). **A skip is not a pass** — coverage for these cases is established by that job's
real execution, and every disposition citing a node here carries a ``CI-EXEMPT:`` declaration
stating exactly that (D-10).

No pytest marker is registered and ``pyproject.toml`` is untouched on purpose: ``Linux Full Suite``
runs ``pytest -q -m ""``, an empty marker expression that selects everything and overrides
``addopts``, so a marker cannot keep this file out of the required job. Physical job placement —
selecting explicit file paths, which Plan 04 provides — is the only mechanism that works.
"""
from __future__ import annotations

import pytest

from tests.browser_e2e_harness import (
    assert_spa_mounted,
    chromium_page,
    collect_console_errors,
    seed_dashboard_db,
    serve_dashboard,
)


@pytest.fixture(scope="module")
def dashboard_origin(tmp_path_factory):
    """Yield a real ``http://127.0.0.1:<port>`` origin serving the real SPA with seeded data.

    MODULE-SCOPED on purpose. Sharing the *server process* across tests in this module is fine and
    desirable — the TRIAGE-149 Cluster-2 hazard is a shared *Playwright* context, not a shared
    server. Each test still gets its own browser via ``chromium_page()``.
    """
    tmp = tmp_path_factory.mktemp("browser_e2e")
    db_path = tmp / "quirk-e2e.db"
    seed_dashboard_db(db_path)
    with serve_dashboard(db_path, config_path=tmp / "absent-config.yaml") as origin:
        yield origin


def test_uat_7_01_spa_mounts_without_blank_screen(dashboard_origin):
    """UAT-7-01 — the dashboard loads: real SPA mounted, no blank screen, no console errors."""
    with chromium_page() as page:
        # Attach BEFORE navigating, or anything thrown during initial load is missed.
        errors = collect_console_errors(page)

        page.goto(dashboard_origin)

        # UAT-7-01's own stated budget is "loads within 5 seconds".
        page.get_by_text("QU.I.R.K.", exact=True).first.wait_for(
            state="visible", timeout=5000
        )

        # D-04: the mandatory vacuous-pass guard, before trusting anything else on this page.
        assert_spa_mounted(page)

        assert errors == [], (
            "UAT-7-01 requires zero console errors, zero page errors and zero failing /api/ "
            f"responses on first load. Collected {len(errors)}:\n  " + "\n  ".join(errors)
        )

        # Explicit "no blank white screen" check.
        body_text = (page.locator("body").inner_text() or "").strip()
        assert body_text, (
            "UAT-7-01: the rendered body has no visible text — a blank screen. "
            f"Page title was {page.title()!r}."
        )
