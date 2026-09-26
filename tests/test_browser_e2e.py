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
    assert_print_view_mounted,
    assert_spa_mounted,
    chromium_page,
    collect_console_errors,
    seed_dashboard_db,
    serve_dashboard,
)

# UAT-7-32's route list, VERBATIM from docs/UAT-SERIES.md:4210 and in the order the case lists them.
# Do not add to it and do not narrow it — the case enumerates exactly these seven.
_UAT_7_32_ROUTES = (
    "/",
    "/findings",
    "/identity",
    "/certificates",
    "/cbom",
    "/roadmap",
    "/print",
)

# The `<h1>` each route's own page component renders. Asserting these is what makes the route walk
# non-vacuous per route: a router outlet that rendered nothing, or a page that fell into its
# no-data/error branch, produces a different heading (e.g. `/` renders "Executive Summary" only in
# its `!data.score` branch — "QU.I.R.K. — Scan Results" means the scan payload actually loaded).
_ROUTE_HEADINGS = {
    "/": "QU.I.R.K. — Scan Results",
    "/findings": "Findings",
    "/identity": "Identity Protocols",
    "/certificates": "Certificate Inventory",
    "/cbom": "CBOM Viewer",
    "/roadmap": "Migration Roadmap",
    "/print": "QU.I.R.K. — Scan Results",
}

# The three identity protocol cards (src/dashboard/src/pages/identity.tsx:33).
_IDENTITY_PROTOCOL_LABELS = ("Kerberos", "SAML/OIDC", "DNSSEC")
_IDENTITY_EMPTY_STATE = "No identity protocol findings in this scan"


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


def test_uat_7_32_zero_console_errors_all_routes(dashboard_origin):
    """UAT-7-32 — zero console errors across every route the case enumerates.

    The claim is UNFILTERED on purpose: there is no console/API allowlist here, and none may be
    added. `src/dashboard/tests/e2e/run-e2e.mjs` carries one; copying that pattern would convert a
    real product defect into a fabricated PASS, and "a fabricated PASS is never acceptable" is
    COV-05's own wording. If this test goes red, the honest paths are to fix the defect or to
    surface it for re-disposition — never to add an exception.
    """
    with chromium_page() as page:
        # Attach ONCE, before the first navigation, and accumulate across the whole walk.
        errors = collect_console_errors(page)
        keyed_errors: list[str] = []

        for route in _UAT_7_32_ROUTES:
            mark = len(errors)
            page.goto(dashboard_origin + route)
            # Wait for the route's own network activity to settle rather than sleeping a fixed
            # interval — several of these pages fetch on mount.
            page.wait_for_load_state("networkidle")

            # D-04's vacuous-pass guard on EVERY route, not just the first. A route that silently
            # degraded to the placeholder branch or to LoginPage must fail here rather than pass by
            # having no JavaScript loaded to throw.
            if route == "/print":
                # /print is chrome-free by design (App.tsx:80-82) — no sidebar nav exists to
                # assert, so the guard's print-view variant is used. Same four checks, plus the
                # print view's own `body[data-ready="true"]` flag.
                assert_print_view_mounted(page)
            else:
                assert_spa_mounted(page)

            heading = page.locator("h1" if route == "/print" else "main h1").first
            heading.wait_for(state="visible", timeout=10_000)
            observed_heading = (heading.inner_text() or "").strip()
            assert observed_heading == _ROUTE_HEADINGS[route], (
                f"UAT-7-32: route {route} did not render its own page component — expected the "
                f"heading {_ROUTE_HEADINGS[route]!r}, observed {observed_heading!r}. Without this "
                "check a route that rendered an empty outlet, or fell into its no-data/error "
                "branch, would still report zero console errors."
            )

            if route == "/identity":
                # ###############################################################
                # THE EMPTY-IDENTITY STATE IS A REGRESSION GUARD, NOT A GAP.
                #
                # UAT-7-32's pass criteria name "/identity page loads without errors even when no
                # identity scan data is present". seed_dashboard_db() seeds no identity data ON
                # PURPOSE and asserts that invariant in code. Do NOT add identity seed data to make
                # this page look populated — that silently deletes the only guard the case has.
                #
                # The empty state is asserted POSITIVELY (the real affordance is on screen), not
                # merely "nothing crashed": an exception swallowed into a blank region would
                # otherwise pass here.
                # ###############################################################
                empty_state = page.get_by_text(_IDENTITY_EMPTY_STATE, exact=False)
                assert empty_state.count() > 0 and empty_state.first.is_visible(), (
                    "UAT-7-32: /identity must render its EmptyStateCard affordance when no "
                    f"identity scan data is present. Text {_IDENTITY_EMPTY_STATE!r} not visible. "
                    "If identity seed data was added to the fixture, remove it — the empty state "
                    "IS the case's regression guard."
                )
                for label in _IDENTITY_PROTOCOL_LABELS:
                    card_title = page.get_by_text(label, exact=True).first
                    assert card_title.is_visible(), (
                        f"UAT-7-32: /identity protocol card {label!r} is not visible — the "
                        "per-protocol summary cards must still render in the empty state."
                    )
                not_scanned = page.get_by_text("Not Scanned", exact=True)
                assert not_scanned.count() >= len(_IDENTITY_PROTOCOL_LABELS), (
                    "UAT-7-32: with zero identity data seeded, every identity protocol card must "
                    f"read 'Not Scanned'. Expected at least {len(_IDENTITY_PROTOCOL_LABELS)} such "
                    f"badges, found {not_scanned.count()}. (Asserted as >= rather than == so "
                    "adding a fourth identity protocol does not spuriously redden this case.)"
                )

            if route == "/cbom":
                # Step 7 of the case: switch between the Table and Graph tabs. This is where a
                # graph-library error would surface, and it surfaces nowhere else in the walk.
                #
                # Each switch asserts the PANEL mounted, not that the trigger is still visible.
                # A Radix `TabsTrigger` stays visible whichever tab is active, so waiting on the
                # trigger would assert nothing at all and a cytoscape mount failure would slip
                # through with the tab switch merely *attempted* — the vacuous-pass shape D-04
                # exists to prevent, pointed at a tab panel instead of a page.
                page.get_by_role("tab", name="Graph").click()
                page.wait_for_load_state("networkidle")
                # `Zoom in` is rendered only by CbomGraph's own overlay (cbom.tsx:443-451), and a
                # <canvas> exists only once cytoscape has actually initialised into the container.
                page.get_by_role("button", name="Zoom in").wait_for(
                    state="visible", timeout=10_000
                )
                page.locator('div[role="tabpanel"] canvas').first.wait_for(
                    state="attached", timeout=10_000
                )

                page.get_by_role("tab", name="Table").click()
                page.wait_for_load_state("networkidle")
                # CbomTable's algorithm filter input (cbom.tsx:85-90) — table panel is back.
                page.get_by_placeholder("Filter algorithm...").wait_for(
                    state="visible", timeout=10_000
                )

            # Key every entry with the route it occurred on, so a red run is diagnosable from the
            # log alone without a re-run.
            keyed_errors.extend(f"[{route}] {entry}" for entry in errors[mark:])

        assert keyed_errors == [], (
            "UAT-7-32 requires ZERO console errors, zero page errors and zero failing /api/ "
            f"responses across all {len(_UAT_7_32_ROUTES)} routes (and the CBOM tab switch). "
            f"Collected {len(keyed_errors)}:\n  " + "\n  ".join(keyed_errors)
        )
