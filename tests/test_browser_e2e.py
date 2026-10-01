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

Phase 207.1 / COV-10 note (added by plan 207.1-01, 2026-09-27): this module also gains ``UAT-7-23``
(sidebar responsive collapse at the 1024px breakpoint) and, in a later plan, ``UAT-7-29``
(Cytoscape roadmap node drag). Both land here rather than in a new module for the same D-02 reason
as the cases above: the ``Browser E2E`` CI job selects tests by **explicit file path**
(``.github/workflows/python-ci.yml:511``), so a new test module would run in no job at all until
someone also edited CI.

``seed_dashboard_db`` was **measured** on 2026-09-27 to already yield a roadmap of **4 nodes across
3 phases (NOW x2, NEXT x1, LATER x1), 2 visible ``phase-`` edges and 1 invisible ``rank-`` edge** —
exactly what ``UAT-7-29`` needs — so the seed is deliberately NOT extended (D-01). Extending it
would put the four already-passing cases that share it (``UAT-7-01``, ``UAT-7-17``, ``UAT-7-32``,
plus the ``_assert_no_identity_data`` empty-identity invariant) at risk to serve one new case.

``cy.nodes()[0]`` is ``NOW-triage-high-impact-f``, whose ONLY connected edge is the invisible
``rank-`` one, so any drag test selecting a node by index observes no edge geometry and its
edge-follow assertion is silently unobservable. This is the trap ``.planning/REQUIREMENTS.md``
COV-10 records at ``:221-223``.

``chromium_page()`` stays function-scoped and un-parameterised (D-03): the harness's hard-coded
1440x900 is already above the 1024px breakpoint, and ``UAT-7-23`` needs a *transition across* the
breakpoint, which only a per-test ``page.set_viewport_size()`` can express. A ``viewport=``
constructor parameter would fix one viewport and could not express a transition.

Phase 219 / KBD-01 note (added by plan 219-02): ``test_kbd_01_keyboard_only_table_region_scroll``
and its paired control ``test_kbd_01_keyboard_control_unfocused_region_does_not_scroll`` are D-07's
keyboard-only walkthrough of the plan-01 conditional table-region wrapper
(``src/dashboard/src/components/ui/table.tsx``). This tier is **non-gating**
(``Browser E2E`` job, ``continue-on-error: true``, ``.github/workflows/python-ci.yml:442``), so
these two nodes **corroborate** real-browser keyboard operability rather than gate on it — the
gating proof is plan 03's axe ``scrollable-region-focusable`` rule withdrawal (D-08). They target
``/findings``, not ``/data-at-rest``: ``seed_dashboard_db`` seeds no data-at-rest rows at all (by
design, see above) and is deliberately not extended, so ``/data-at-rest`` renders no tables under
this seed and cannot host a deterministic overflow. They land in this module, not a new one, for
the same D-02 reason as every other case here: the ``Browser E2E`` CI job selects tests by
**explicit file path**.
"""
from __future__ import annotations

import pytest

from tests.browser_e2e_harness import (
    assert_print_view_mounted,
    assert_spa_mounted,
    chromium_page,
    collect_console_errors,
    diagnosing_mount_failure,
    seed_dashboard_db,
    serve_dashboard,
    skip_unless_chromium_installed,
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
# non-vacuous per route: a router outlet that rendered nothing, a page that never mounted, or an
# error branch that renders no `h1` at all fails here on every route.
#
# W-09 — WHAT THE HEADING DOES *NOT* PROVE. An earlier version of this comment claimed a page that
# "fell into its no-data/error branch produces a different heading". Verified against source, that
# is true for only two of the seven:
#   /          discriminates — executive.tsx:351 "Executive Summary" (no `data.score`) vs
#              :380 "QU.I.R.K. — Scan Results" (payload loaded).
#   /roadmap   discriminates — roadmap.tsx:241 "Remediation Roadmap" (empty) vs :252
#              "Migration Roadmap" (loaded).
#   /certificates  does NOT — certificates.tsx:42 and :54 render the IDENTICAL
#              "Certificate Inventory" h1 in the empty and populated branches. Reproduced: with the
#              `certificates` array emptied in the /api/scan/latest response and nothing else
#              changed, this heading assertion still passes. Closed below by a positive content
#              assertion; do not remove it and rely on the heading.
#   /findings, /identity, /cbom, /print  single h1, so no discrimination is available. /identity is
#              mitigated by its positive empty-state legs below, /cbom by its tab-panel assertions.
# Read this before writing any disposition that claims what UAT-7-32 proves per route.
_ROUTE_HEADINGS = {
    "/": "QU.I.R.K. — Scan Results",
    "/findings": "Findings",
    "/identity": "Identity Protocols",
    "/certificates": "Certificate Inventory",
    "/cbom": "CBOM Viewer",
    "/roadmap": "Migration Roadmap",
    "/print": "QU.I.R.K. — Scan Results",
}

# W-09's closure for /certificates — the only route whose heading discriminates nothing and that
# had no other positive assertion. These literals are written out by hand rather than imported from
# `seed_dashboard_db`: if both sides of the assertion read the same constant, a seeder that stopped
# writing certificates would silently keep the test green.
_SEEDED_CERT_HOSTS = ("web01.seed.local", "web02.seed.local")
_CERTIFICATES_EMPTY_STATE = "No TLS certificates discovered in this scan."

# The three identity protocol DISPLAY labels, from PROTOCOL_LABELS at
# src/dashboard/src/pages/identity.tsx:55-58. (I-02: this previously cited :33, which is
# `const PROTOCOLS = ["KERBEROS", "SAML", "DNSSEC"]` — the uppercase keys, not these
# labels. The assertions were always correct; the citation pointed at the wrong line.)
_IDENTITY_PROTOCOL_LABELS = ("Kerberos", "SAML/OIDC", "DNSSEC")
_IDENTITY_EMPTY_STATE = "No identity protocol findings in this scan"

# A4 in PostScript points, and the tolerance Chromium's own `format="A4"` output needs: the observed
# media box is 595.92 x 842.88, ~1pt over nominal 595 x 842 (Chromium rounds up from 210x297mm).
_A4_POINTS = (595.0, 842.0)
_A4_TOLERANCE_POINTS = 6.0


@pytest.fixture(scope="module")
def dashboard_origin(tmp_path_factory):
    """Yield a real ``http://127.0.0.1:<port>`` origin serving the real SPA with seeded data.

    MODULE-SCOPED on purpose. Sharing the *server process* across tests in this module is fine and
    desirable — the TRIAGE-149 Cluster-2 hazard is a shared *Playwright* context, not a shared
    server. Each test still gets its own browser via ``chromium_page()``.

    W-10: the Chromium precheck comes FIRST, before any server is started. A failure raised during
    module-scoped fixture setup is reported by pytest as an ERROR, and D-10 forbids an ERROR in the
    required ``Linux Full Suite`` job where Chromium is absent. Skipping here makes
    ``serve_dashboard``'s ``pytest.fail`` unreachable in that job, while leaving it loud in the
    Browser E2E job — both halves pinned by ``tests/test_browser_e2e_skip_contract.py``.
    """
    skip_unless_chromium_installed()

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

        # UAT-7-01's own stated budget is "loads within 5 seconds". The 5s figure is the
        # case's, so it is NOT widened here; the wrapper below changes only what a timeout
        # REPORTS, never how long it waits.
        #
        # W-04: both states D-04 exists to catch make this wordmark never appear — the
        # placeholder branch renders `QU.I.R.K. Dashboard`, which `exact=True` correctly
        # refuses to match, and an unmounted bundle renders nothing at all. Without the
        # wrapper both surface as an opaque 5s TimeoutError instead of their named cause.
        with diagnosing_mount_failure(page, guard=assert_spa_mounted):
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

            # WAIT FOR THE ROUTE'S OWN CONTENT *BEFORE* ASSERTING THE MOUNT GUARD, NOT AFTER.
            # `networkidle` does not imply React has committed a render — it means no in-flight
            # requests, which on a fast local origin can be true while the bundle is still
            # executing. Asserting the guard first would race React's first paint and the `#root`
            # leg could fire with 0 children, a FALSE failure claiming the bundle never mounted.
            # This ordering costs nothing and weakens no assertion: if the element never appears
            # the wait raises, and if it appears the guard still has to pass.
            #
            # BUT THE ORDERING IS NOT FREE, and `0eddf3ba`'s claim that "this weakens nothing"
            # was true of STRENGTH and false of DIAGNOSIS (Phase 207 review W-04). The heading
            # locator on the six shell routes is `main h1`, and BOTH states D-04 exists to catch
            # make it never appear:
            #   (a) `index.html` missing -> app.py's placeholder branch (app.py:177-183) renders
            #       no `<main>` at all;
            #   (b) `/assets` unmounted / bundle 404s -> `#root` stays empty, no heading is
            #       rendered anywhere.
            # So on six of seven routes each one degraded from its named D-04 diagnosis to an
            # opaque 15s Playwright TimeoutError. `diagnosing_mount_failure` restores the named
            # diagnosis WITHOUT reverting the ordering: the wait is unchanged and still runs
            # first, and on timeout the guard runs inside the handler so the failure names the
            # placeholder branch / unmounted bundle / login form. If the guard passes, the
            # timeout is re-raised — it is then the honest finding.
            #
            # HONEST PROVENANCE: this ordering was written in response to an intermittent red
            # observed during 207-03 (2 of 7 runs), but that failure's text was never captured and
            # this race was NOT confirmed to be its cause — a 42-route-load probe reading
            # `#root.children.length` immediately after `networkidle` found zero empty-root hits.
            # The likelier cause was external: another actor was moving the Playwright browser
            # cache aside in this same working tree during that window (it produced two spurious
            # "Executable doesn't exist" skips here while the cache was demonstrably intact before
            # and after). So treat this as a defensive ordering, not a diagnosed fix, and if this
            # test ever goes intermittently red again, CAPTURE THE FAILURE TEXT before theorising.
            # /print is chrome-free by design (App.tsx:80-82) — no sidebar nav exists to assert,
            # so the guard's print-view variant is used there. Same four checks, plus the print
            # view's own `body[data-ready="true"]` flag. Resolved BEFORE the wait so the timeout
            # handler can report the right route's diagnosis.
            guard = assert_print_view_mounted if route == "/print" else assert_spa_mounted

            heading = page.locator("h1" if route == "/print" else "main h1").first
            with diagnosing_mount_failure(page, guard=guard):
                heading.wait_for(state="visible", timeout=15_000)

            # D-04's vacuous-pass guard on EVERY route, not just the first. A route that silently
            # degraded to the placeholder branch or to LoginPage must fail here rather than pass by
            # having no JavaScript loaded to throw.
            guard(page)

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

            if route == "/certificates":
                # ###############################################################
                # W-09: THE HEADING ABOVE PROVES NOTHING ON THIS ROUTE.
                #
                # certificates.tsx renders the identical `Certificate Inventory` h1 in both its
                # empty branch (:42) and its populated branch (:54). Reproduced mechanically: with
                # the `certificates` array emptied in the /api/scan/latest response and nothing
                # else changed, the heading assertion above still passed, the EmptyStateCard
                # rendered, and both seeded hosts were absent. So without the assertions below,
                # UAT-7-32 would report a clean PASS for a /certificates page that silently
                # stopped loading the data the fixture seeds.
                #
                # Asserted POSITIVELY (the seeded rows are on screen), with the empty-state
                # absence second — the absence alone would also hold for a blank region.
                # ###############################################################
                for host in _SEEDED_CERT_HOSTS:
                    cell = page.get_by_text(host, exact=False)
                    assert cell.count() > 0 and cell.first.is_visible(), (
                        f"UAT-7-32: /certificates must render the seeded certificate row for "
                        f"{host!r}, and it is not visible. The heading assertion above CANNOT "
                        "catch this — certificates.tsx renders the same h1 whether or not any "
                        "certificates loaded. Either the seed stopped producing cert-bearing "
                        "endpoints or the page fell into its empty branch."
                    )
                empty_state = page.get_by_text(_CERTIFICATES_EMPTY_STATE, exact=False)
                assert empty_state.count() == 0, (
                    "UAT-7-32: /certificates rendered its EmptyStateCard "
                    f"({_CERTIFICATES_EMPTY_STATE!r}) while the fixture seeds two cert-bearing "
                    "endpoints — the certificate payload did not reach the page."
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
                # I-05: `visible`, not `attached` — an attached zero-size canvas would satisfy
                # `attached` while showing nothing, and a cytoscape mount that produced no
                # geometry is exactly the failure this wait is here to catch. `visible` requires a
                # non-empty bounding box, and it WAITS for one rather than failing on a transient
                # zero-size frame, so it is strictly stronger at no flake cost.
                page.locator('div[role="tabpanel"] canvas').first.wait_for(
                    state="visible", timeout=10_000
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

        # W-08: `keyed_errors` is built by slicing `errors[mark:]` at the END of each iteration, so
        # anything delivered after the final route's slice — a late `pageerror`, or a trailing
        # `>=400` /api/ response from the print view's own fetches — lands in `errors` and is never
        # keyed. Asserting only on `keyed_errors` would therefore make a claim NARROWER than the
        # unfiltered one this test exists to make, while reading exactly like the full claim.
        #
        # Asserted as a count reconciliation rather than by replacing the keyed assertion above:
        # the per-route keying is what makes a red run diagnosable without a re-run, and this
        # closes the tail without giving that up. The tail entries are unkeyed by construction —
        # they belong to no route's slice — so they are reported raw.
        tail = errors[len(keyed_errors):]
        assert not tail, (
            "UAT-7-32: console errors arrived AFTER the last route's slice was keyed, so the "
            "per-route assertion above could not see them. The case's claim is unfiltered and "
            f"these count against it. Collected {len(tail)} trailing:\n  "
            + "\n  ".join(str(entry) for entry in tail)
        )


def test_uat_7_17_export_pdf_download(dashboard_origin, tmp_path):
    """UAT-7-17 — clicking Export PDF yields a real, structurally valid A4 PDF.

    ###########################################################################
    # D-05 ASSERTION CEILING — READ BEFORE "STRENGTHENING" THIS TEST.
    #
    # This test asserts STRUCTURAL PDF validity ONLY: a download fired, the bytes are a real PDF,
    # it has pages, the page geometry is A4, the filename matches, and no error message rendered.
    #
    # It deliberately asserts NO score value, NO CRITICAL finding count and NO certificate count.
    # The Export PDF button drives the *dashboard* pipeline, which is known to emit a different
    # overall score and a different CRITICAL count than the consulting-grade report for the SAME
    # scan — an open P1, reproduced twice, tracked at
    # .planning/todos/pending/cli-dashboard-score-divergence-same-scan.md.
    #
    # Asserting any of those numbers would hard-code the value that P1's fix is supposed to change,
    # and this test would then fight the fix when it lands. The apparent "weakness" is deliberate
    # and recorded. Do not add such an assertion.
    ###########################################################################
    """
    with chromium_page() as page:
        # Both imports live INSIDE the chromium_page() block, not at module level and not above it.
        # `playwright` and `pypdf` are extras-only dependencies (pyproject.toml `dashboard`
        # extras), so a module-level import breaks collection on a minimal install, and an import
        # placed above this line would raise ImportError *before* chromium_page() gets the chance
        # to skip — turning the intended SKIP into an ERROR, which reddens the required
        # Linux Full Suite job even under a CI-EXEMPT declaration (D-10). Order is load-bearing.
        import pypdf
        from playwright.sync_api import TimeoutError as PwTimeoutError

        errors = collect_console_errors(page)

        page.goto(dashboard_origin)
        page.wait_for_load_state("networkidle")

        # W-05: WAIT FOR THE ROUTE'S OWN CONTENT BEFORE THE MOUNT GUARD. `networkidle` means no
        # in-flight requests; it does NOT mean React has committed a render, and on a fast
        # loopback origin both are true at once. Every leg of `assert_spa_mounted` is a
        # NON-waiting read (`page.content()`, `page.evaluate()`, `locator.count()`,
        # `locator.is_visible()`), so there is nothing to absorb a late commit and the `#root`
        # leg can fire with 0 children — a FALSE failure claiming the bundle never mounted.
        #
        # `0eddf3ba` fixed exactly this shape in test_uat_7_32 and left this second call site
        # untouched. test_uat_7_01 is safe only by accident: its wordmark wait implies a commit.
        # The `diagnosing_mount_failure` wrapper is what keeps the added wait from swallowing
        # D-04's named diagnosis into an opaque timeout — see its docstring.
        with diagnosing_mount_failure(page, guard=assert_spa_mounted):
            page.locator("main h1").first.wait_for(state="visible", timeout=15_000)

        assert_spa_mounted(page)

        export_button = page.get_by_role("button", name="Export PDF").first
        export_button.wait_for(state="visible", timeout=10_000)
        assert export_button.is_enabled(), (
            "UAT-7-17: the Export PDF button is disabled before any click — it is only disabled "
            "while an export is already in flight (pdfExporting)."
        )

        # The server side renders the PDF through its own Playwright instance against /print, so
        # allow well past the UAT case's 10-30s budget before declaring the download absent.
        #
        # The timeout is caught and re-raised as a diagnosable failure ON PURPOSE. A bare
        # `TimeoutError: waiting for event "download"` says only that nothing downloaded — it does
        # not say why, and the *why* is on screen: when POST /api/export/pdf returns non-200 the
        # handler renders its failure detail into the same status span it uses for success and
        # never creates the blob, so no download event can fire. Observed live during 207-03: one
        # run burned the full 120s and reported only the opaque Playwright error, forcing a re-run
        # to learn anything. The re-raise below folds the on-screen status text and every collected
        # console/page/API error into the failure message so one red run is enough.
        #
        # NOTE: this is a diagnostic wrapper, NOT a softened assertion — the test still fails.
        try:
            with page.expect_download(timeout=120_000) as download_info:
                export_button.click()
            download = download_info.value
        except PwTimeoutError as exc:
            status_texts = [
                text
                for text in (
                    (span.inner_text() or "").strip()
                    for span in page.locator("span.text-sm").all()
                )
                if text
            ]
            raise AssertionError(
                "UAT-7-17: clicking Export PDF fired no browser download within 120s "
                f"({type(exc).__name__}). This is almost always a server-side export failure "
                "rather than a download-interception problem: the handler only creates the blob "
                "on a 200 response.\n"
                f"  On-screen status text: {status_texts}\n"
                f"  Collected console/page/API errors ({len(errors)}): {errors}\n"
                "  If the status text names DASHBOARD-012 ('Playwright not installed for PDF "
                "export'), read it with suspicion — that bucket also absorbs "
                "connection-refused and timeout against the /print render target "
                "(quirk/dashboard/api/routes/pdf.py:109-120), so it fires even with Playwright "
                "installed and working. QUIRK_SERVE_PORT is already set by serve_dashboard; do "
                "not re-litigate that."
            ) from exc

        assert download.suggested_filename.startswith("quirk-report-"), (
            "UAT-7-17: the download's suggested filename should carry the handler's "
            f"`quirk-report-<date>.pdf` shape; observed {download.suggested_filename!r}."
        )
        assert download.suggested_filename.endswith(".pdf"), (
            f"UAT-7-17: expected a .pdf suffix; observed {download.suggested_filename!r}."
        )

        saved = tmp_path / "uat-7-17-export.pdf"
        download.save_as(saved)

        assert saved.exists(), f"UAT-7-17: the download was not saved to {saved}."
        size = saved.stat().st_size
        assert size > 0, f"UAT-7-17: the downloaded PDF is empty (0 bytes) at {saved}."
        assert saved.read_bytes()[:5] == b"%PDF-", (
            "UAT-7-17: the downloaded file does not begin with the %PDF- magic bytes; first 16 "
            f"bytes were {saved.read_bytes()[:16]!r}."
        )

        reader = pypdf.PdfReader(str(saved))
        assert len(reader.pages) >= 1, (
            f"UAT-7-17: the downloaded PDF parsed but has {len(reader.pages)} pages."
        )

        media_box = reader.pages[0].mediabox
        width = float(media_box.width)
        height = float(media_box.height)
        portrait = (
            abs(width - _A4_POINTS[0]) <= _A4_TOLERANCE_POINTS
            and abs(height - _A4_POINTS[1]) <= _A4_TOLERANCE_POINTS
        )
        landscape = (
            abs(width - _A4_POINTS[1]) <= _A4_TOLERANCE_POINTS
            and abs(height - _A4_POINTS[0]) <= _A4_TOLERANCE_POINTS
        )
        assert portrait or landscape, (
            "UAT-7-17 requires A4 page geometry. Observed media box "
            f"{width:.2f} x {height:.2f} points; A4 is {_A4_POINTS[0]} x {_A4_POINTS[1]} "
            f"(either orientation) within {_A4_TOLERANCE_POINTS} points."
        )

        # No error toast / error message. The handler writes BOTH its success text and its failure
        # detail into the same status span, so assert the success shape positively rather than
        # merely asserting the absence of a substring.
        status = page.get_by_text("PDF saved to", exact=False).first
        status.wait_for(state="visible", timeout=15_000)
        status_text = (status.inner_text() or "").strip()

        # ###################################################################
        # W-01: THE TWO ASSERTIONS THAT USED TO SIT HERE COULD NOT FAIL.
        #
        # They were `"failed" not in status_text.lower()` and
        # `get_by_text("PDF export failed").count() == 0`. `pdfMessage` is a single useState
        # string (executive.tsx:190) rendered in exactly one span (executive.tsx:462-463), and
        # the handler writes EITHER the success string (executive.tsx:321) or a failure string
        # (:328-332), never both. The `wait_for` above has already blocked until the success
        # string is on screen, so both checks interrogated a state the state machine had
        # already guaranteed. Worse, both were ineffective even if reachable: the dominant real
        # failure text is `coerceErrorDetail(body)`, which for the DASHBOARD-012 path reads
        # "Playwright not installed for PDF export. Fix: Run pip install playwright && ..." and
        # contains neither "failed" nor "PDF export failed".
        #
        # Replaced with an EXACT equality check on the status text, cross-referenced against the
        # filename of the artifact actually downloaded. That can fail: against a changed
        # directory prefix, a truncated or appended message, a status naming a different file
        # than the one that downloaded, or any failure string.
        #
        # Deliberately NOT added: an "absence of DASHBOARD-012 anywhere on the page" assertion.
        # In the success state reached here it would be one more assertion that cannot fail.
        # The DASHBOARD-012 surface is instead interrogated where it can genuinely fire — the
        # `expect_download` timeout handler above folds the on-screen status text into its
        # failure message and names that error code explicitly.
        #
        # D-05 is respected: this asserts a filename and a fixed prefix. No score value, no
        # CRITICAL count, no certificate count.
        # ###################################################################
        expected_status = f"PDF saved to ~/Downloads/{download.suggested_filename}"
        assert status_text == expected_status, (
            f"UAT-7-17: the on-screen status after a successful export should be exactly "
            f"{expected_status!r} — naming the same file that was downloaded — but the status "
            f"span reads {status_text!r}. Either the handler's success message changed shape, or "
            f"it is reporting a different artifact than the one the browser saved, or a failure "
            f"detail is being rendered into the same span "
            f"(executive.tsx:328-332 writes failures there too)."
        )

        assert errors == [], (
            "UAT-7-17: the Export PDF flow produced console/page/API errors:\n  "
            + "\n  ".join(errors)
        )


def test_uat_7_23_sidebar_responsive_collapse(dashboard_origin):
    """UAT-7-23 — sidebar collapses/expands at the 1024px breakpoint (COV-10).

    Asserted as MEASURED layout only (``bounding_box()["width"]``, visibility of the wordmark vs.
    the monogram) — never via the ``class`` attribute. ``sidebar.tsx:78``'s class string
    ``"w-12 lg:w-60"`` is present at EVERY viewport width; asserting it in a real browser would
    reproduce the exact vacuity the original GAP note banned (D-04). Only a measured box
    distinguishes the two states.

    Covers 5 of the case's 6 pass criteria:
      1. width collapses to 48px below 1024px and expands back to 240px above it
      2. wordmark/monogram visibility inverts with the breakpoint
      3. the collapsed-state "New Scan" tooltip renders through the Radix portal (D-05)
      4. a nav click while collapsed still routes correctly (D-06)
      5. re-crossing the breakpoint upward restores the expanded width

    Criterion 6 ("transition is smooth — no layout jumps or flicker") has no mechanical referent
    and is NOT asserted here. Per CONTEXT.md D-11 it is routed to HUMAN-UAT rather than dropped.
    That HUMAN-UAT item was run and PASSED by operator verdict on 2026-09-27, taking the case from a
    stated 5 of 6 to 6 of 6 -- see 207.1-HUMAN-UAT.md and the case's ledger evidence.

    Do NOT read that verdict as coverage for this node. Criterion 6 remains unasserted here and
    unassertable anywhere: a smoothness regression would not fail this test or any other. The
    verdict is a one-time human observation, not a guard. If someone later wants a guard, it needs a
    new mechanism -- not an added assertion on the five values below, which would be the proxy
    substitution D-11 declined.
    """
    with chromium_page() as page:
        page.goto(dashboard_origin)
        with diagnosing_mount_failure(page, guard=assert_spa_mounted):
            page.locator("main h1").first.wait_for(state="visible", timeout=15_000)
        assert_spa_mounted(page)

        aside = page.locator("aside")
        wordmark = aside.get_by_text("QU.I.R.K.", exact=True)
        monogram = aside.get_by_text("Q", exact=True)

        # Above the breakpoint: the harness's own hard-coded 1440x900 viewport (D-03).
        assert aside.bounding_box()["width"] == 240, (
            "UAT-7-23: expected the aside to measure 240px wide above the 1024px breakpoint "
            "at 1440x900."
        )
        assert wordmark.is_visible(), "UAT-7-23: expected the QU.I.R.K. wordmark visible at 1440px."
        assert not monogram.is_visible(), "UAT-7-23: expected the Q monogram hidden at 1440px."

        # Cross below the breakpoint. No wait between the resize and the measurement: this is a
        # pure Tailwind CSS media query with no matchMedia/useMediaQuery listener in the loop
        # (verified live, 2026-09-27 — the new width is reported at 0ms, identical to a 50ms
        # read). An unnecessary settle wait here would mask a future debounced-resize regression
        # rather than test for its absence.
        page.set_viewport_size({"width": 900, "height": 900})
        assert aside.bounding_box()["width"] == 48, (
            "UAT-7-23: expected the aside to measure 48px wide below the 1024px breakpoint "
            "at 900x900."
        )
        assert monogram.is_visible(), "UAT-7-23: expected the Q monogram visible at 900px."
        assert not wordmark.is_visible(), "UAT-7-23: expected the QU.I.R.K. wordmark hidden at 900px."

        # Collapsed-state tooltip (D-05): reached through the Radix portal, on the PAGE not the
        # sidebar subtree (TooltipContent portals outside <aside>). get_by_role("tooltip") is a
        # single unambiguous match; get_by_text("New Scan", exact=True) matches 2 elements (the
        # button's own CSS-hidden label span plus the portal content) and is forbidden.
        new_scan_button = page.get_by_role("button", name="New Scan")
        new_scan_button.hover()
        tooltip = page.get_by_role("tooltip")
        tooltip.wait_for(state="visible", timeout=2000)  # Radix has an ~700ms open delay
        assert tooltip.inner_text().strip() == "New Scan", (
            f"UAT-7-23: expected the collapsed-state tooltip text to be 'New Scan', got "
            f"{tooltip.inner_text().strip()!r}."
        )

        # Collapsed nav-click leg (D-06): still at 900px. Use a NAV_ITEMS entry, not the New Scan
        # button (which routes to /scan/new, not /findings).
        page.get_by_label("Findings", exact=True).click()
        page.wait_for_url("**/findings")
        assert page.url.endswith("/findings"), (
            f"UAT-7-23: expected the collapsed nav click to route to /findings, page.url is "
            f"{page.url!r}."
        )

        # Cross back above the breakpoint.
        page.set_viewport_size({"width": 1440, "height": 900})
        assert aside.bounding_box()["width"] == 240, (
            "UAT-7-23: expected the aside to measure 240px wide again after expanding back to "
            "1440x900."
        )


def test_uat_7_23_control_no_viewport_change(dashboard_origin):
    """Red-proof control for UAT-7-23 (D-10, SC#3).

    Performs the identical mount setup and deliberately omits the viewport-resize call the main
    test makes. Its job is to prove the main test's width assertions are load-bearing on the
    viewport change actually happening, rather than comparing a value to itself. This is a
    separate pytest test node, not a comment or a sub-assertion inside the main test, so a
    reviewer can confirm the red-proof exists without reading any test body.
    """
    with chromium_page() as page:
        page.goto(dashboard_origin)
        with diagnosing_mount_failure(page, guard=assert_spa_mounted):
            page.locator("main h1").first.wait_for(state="visible", timeout=15_000)
        assert_spa_mounted(page)

        aside = page.locator("aside")
        before = aside.bounding_box()["width"]
        # Deliberately no viewport-resize call here — the absence is the point of the test.
        # Do not "complete" this later by adding a resize.
        after = aside.bounding_box()["width"]
        assert before == after == 240, (
            "UAT-7-23 control: expected NO width change without a viewport resize; observed "
            f"before={before!r}, after={after!r}. A failure here means either the page is "
            "unstable or a stray resize crept into the control."
        )


# UAT-7-29 (Cytoscape roadmap node drag) — module-level constants and shared helpers.
#
# The container is selected by its ARIA role/label, not by a Tailwind class or Cytoscape's own
# injected container class (`__________cytoscape_container`): `roadmap.tsx:333` gives the
# container `<div>` `role="img"` and a distinctive `aria-label` starting "Migration roadmap DAG",
# which is stable against both a future className refactor and against Cytoscape's own internal
# naming.
_CY_CONTAINER_SELECTOR = '[role="img"][aria-label*="Migration roadmap"]'

# .visible() edge-discrimination note (207.1-RESEARCH.md Pitfall 1, verified live 2026-09-27):
# generic Cytoscape.js documentation describes opacity/visibility/display as three independent
# style axes, reading as though `.visible()` tracks only visibility/display and would report
# `true` for the seed's opacity:0 `rank-` edges too. That generic reading is WRONG for this
# codebase's installed cytoscape (`^3.33.1`, src/dashboard/package.json:39) — `.visible()` was
# live-verified to correctly report `false` for `rank-` edges and `true` for `phase-` edges. Do
# NOT "fix" `_select_draggable_candidate`'s filter based on generic docs; if a future cytoscape
# version bump ever changes this, the `phase-` prefix guard below is the independent backstop
# that fails loudly instead of silently steering onto the wrong edge.


def _resolve_cy(page):
    """Assert `container._cyreg.cy` resolved — SC#4, per D-08. Call before any mouse event.

    `_cyreg` is an undocumented Cytoscape internal: `roadmap.tsx:73-74` holds the live instance in
    a React `useRef` with no public export, so this internal registry object attached to the
    mounted container is genuinely the only reach. This is an `assert` with a named diagnosis, not
    a `None`-returning lookup — a future reader must get a diagnosis, not an `AttributeError` on
    `None`.
    """
    resolved = page.evaluate(
        "(sel) => { const el = document.querySelector(sel);"
        " return !!(el && el._cyreg && el._cyreg.cy); }",
        _CY_CONTAINER_SELECTOR,
    )
    assert resolved, (
        "UAT-7-29: container._cyreg.cy did not resolve. `_cyreg` is an undocumented Cytoscape "
        "internal — roadmap.tsx:73-74 holds the live instance in a React useRef with no public "
        "export, so this is genuinely the only reach available to a test. A Cytoscape version "
        "bump (declared range `^3.33.1` in src/dashboard/package.json) may have removed or "
        "renamed `_cyreg`. Investigate the installed cytoscape version BEFORE assuming this is a "
        "product regression."
    )


def _select_draggable_candidate(page):
    """Structurally select a node with a visible connected edge — D-07. Never selects by index.

    `cy.nodes()[0]` is `NOW-triage-high-impact-f`, whose only connected edge is the invisible
    `rank-` one (opacity: 0) — a test selecting by index would observe no usable endpoint
    geometry and its edge-follow assertion would be silently unobservable, exactly the trap
    `.planning/REQUIREMENTS.md:221-223` (COV-10) records. Instead this iterates every node and
    returns the first one whose `connectedEdges().filter(e => e.visible())` is non-empty.

    Returns ``(node_id, edge_id)``. Asserts, before returning:
      1. a qualifying node was found at all (D-01: the seed has 2 visible `phase-` edges, so at
         least one must exist) — a bare `[0]` on an empty result reads as a passing test that
         observed nothing, which is the whole point of this guard;
      2. the selected edge id starts with ``"phase-"`` — a second, independent guard against a
         future cytoscape version where `.visible()` stops discriminating `opacity: 0` `rank-`
         edges (see the module comment above and 207.1-RESEARCH.md Pitfall 1). Without this guard,
         such a regression would silently steer the test onto the wrong edge instead of failing.
    """
    candidate = page.evaluate(
        "(sel) => { const el = document.querySelector(sel); const cy = el._cyreg.cy;"
        " for (const n of cy.nodes().toArray()) {"
        "   const ve = n.connectedEdges().filter(e => e.visible());"
        "   if (ve.length > 0) return { nodeId: n.id(), edgeId: ve[0].id() };"
        " } return null; }",
        _CY_CONTAINER_SELECTOR,
    )
    assert candidate is not None, (
        "UAT-7-29: no node has a connectedEdges().filter(e => e.visible()) match — the seed's "
        "roadmap must contain at least one visible cross-phase edge (D-01: 2 visible `phase-` "
        "edges measured live on 2026-09-27). This assertion is the whole point of D-07 — a bare "
        "[0] on an empty result would read as a passing test that observed nothing."
    )
    node_id, edge_id = candidate["nodeId"], candidate["edgeId"]
    assert edge_id.startswith("phase-"), (
        f"UAT-7-29: selected edge {edge_id!r} is not a `phase-` edge. `.visible()` may no longer "
        "discriminate the seed's opacity:0 `rank-` edges on the installed cytoscape version — "
        "this is the second, independent guard against that regression (see module comment above "
        "and 207.1-RESEARCH.md Pitfall 1); without it, a future `.visible()` behaviour change "
        "would silently steer this test onto the invisible `rank-` edge instead of failing."
    )
    return node_id, edge_id


def test_uat_7_29_roadmap_node_drag(dashboard_origin):
    """UAT-7-29 — dragging a roadmap node moves it, its visible edge follows in real time, and
    nothing else on the canvas is disturbed.

    Covers all FIVE of the case's pass criteria (docs/UAT-SERIES.md:4123-4149):
      1. the dragged node's position changes
      2. its connected (visible) edge's endpoint updates position in real-time, i.e. WHILE the
         mouse is still down, not only after release (D-09)
      3. the node's new position holds after mouse release (no snap-back)
      4. the other three nodes on the canvas are byte-identical, pre-drag versus post-release
      5. no layout reset occurs (dagre does not silently re-run and reassign the pre-drag layout)

    The rejected data-layer-invariant substitute (docs/UAT-SERIES.md:4147) covered ZERO of these
    five — "a citation whose carve-out list is the case's entire criteria set is a false
    attestation, not a partial one." This test is written to clear that standard.
    """
    with chromium_page() as page:
        page.goto(dashboard_origin + "/roadmap")
        with diagnosing_mount_failure(page, guard=assert_spa_mounted):
            page.locator("main h1").first.wait_for(state="visible", timeout=15_000)
        assert_spa_mounted(page)

        # SC#4 / D-08 — _cyreg resolution asserted BEFORE any mouse event.
        _resolve_cy(page)

        # D-07 — structural selection, never by index.
        node_id, edge_id = _select_draggable_candidate(page)

        # Pre-drag state: dragged node's position + its visible edge's sourceEndpoint (model
        # coords, NOT the viewport-pixel rendered-endpoint variant), plus every OTHER node's
        # position, captured as a single list for criterion 4's byte-identical comparison.
        other_ids = page.evaluate(
            "(args) => { const cy = document.querySelector(args.sel)._cyreg.cy;"
            " return cy.nodes().map(n => n.id()).filter(id => id !== args.nodeId); }",
            {"sel": _CY_CONTAINER_SELECTOR, "nodeId": node_id},
        )
        assert other_ids, (
            "UAT-7-29: expected at least one OTHER node on the canvas besides the dragged node "
            f"{node_id!r} (the measured seed has 3) — criterion 4 cannot be asserted against an "
            "empty list."
        )
        pre = page.evaluate(
            "(args) => { const cy = document.querySelector(args.sel)._cyreg.cy;"
            " return {"
            "   pos: cy.$id(args.nodeId).position(),"
            "   edge: cy.$id(args.edgeId).sourceEndpoint(),"
            "   others: args.otherIds.map(id => cy.$id(id).position()),"
            "   zoom: cy.zoom(),"
            " }; }",
            {"sel": _CY_CONTAINER_SELECTOR, "nodeId": node_id, "edgeId": edge_id, "otherIds": other_ids},
        )
        assert pre["edge"] is not None, (
            f"UAT-7-29: pre-drag sourceEndpoint() for edge {edge_id!r} is None — the selected "
            "edge has no usable endpoint geometry before any drag has occurred."
        )

        # Translate the node's model position to a real page (viewport) coordinate for
        # page.mouse: container origin (getBoundingClientRect) + node's renderedPosition().
        container_box = page.evaluate(
            "(sel) => { const r = document.querySelector(sel).getBoundingClientRect();"
            " return { x: r.x, y: r.y }; }",
            _CY_CONTAINER_SELECTOR,
        )
        rendered = page.evaluate(
            "(args) => document.querySelector(args.sel)._cyreg.cy.$id(args.nodeId).renderedPosition()",
            {"sel": _CY_CONTAINER_SELECTOR, "nodeId": node_id},
        )
        start_x = container_box["x"] + rendered["x"]
        start_y = container_box["y"] + rendered["y"]

        page.mouse.move(start_x, start_y)
        page.mouse.down()
        page.mouse.move(start_x + 100, start_y + 50, steps=10)

        # MID-DRAG, mouse button still held (D-09). Sampling only after release would pass even
        # if the renderer repainted edges once at the end, which is NOT what "connected edges
        # update position in real-time" (criterion 2) says.
        mid = page.evaluate(
            "(args) => { const cy = document.querySelector(args.sel)._cyreg.cy;"
            " return { pos: cy.$id(args.nodeId).position(), edge: cy.$id(args.edgeId).sourceEndpoint() }; }",
            {"sel": _CY_CONTAINER_SELECTOR, "nodeId": node_id, "edgeId": edge_id},
        )
        page.mouse.up()

        post = page.evaluate(
            "(args) => { const cy = document.querySelector(args.sel)._cyreg.cy;"
            " return {"
            "   pos: cy.$id(args.nodeId).position(),"
            "   edge: cy.$id(args.edgeId).sourceEndpoint(),"
            "   others: args.otherIds.map(id => cy.$id(id).position()),"
            " }; }",
            {"sel": _CY_CONTAINER_SELECTOR, "nodeId": node_id, "edgeId": edge_id, "otherIds": other_ids},
        )

        # Criterion 1 — the node moves.
        assert mid["pos"] != pre["pos"], (
            f"UAT-7-29 criterion 1: expected node {node_id!r} to move mid-drag; pre={pre['pos']!r} "
            f"mid={mid['pos']!r}."
        )

        # Criterion 2 — the visible connected edge updates in real time, WHILE the mouse is down,
        # and its endpoint followed the node by approximately the same delta (not merely "changed").
        assert mid["edge"] is not None and pre["edge"] is not None, (
            f"UAT-7-29 criterion 2: edge {edge_id!r} sourceEndpoint() must be non-None both "
            f"pre-drag and mid-drag; pre={pre['edge']!r} mid={mid['edge']!r}. A comparison whose "
            "before and after are both None would 'pass' vacuously."
        )
        assert mid["edge"] != pre["edge"], (
            f"UAT-7-29 criterion 2: expected edge {edge_id!r}'s sourceEndpoint() to change "
            f"mid-drag; pre={pre['edge']!r} mid={mid['edge']!r}."
        )
        node_delta = (mid["pos"]["x"] - pre["pos"]["x"], mid["pos"]["y"] - pre["pos"]["y"])
        edge_delta = (mid["edge"]["x"] - pre["edge"]["x"], mid["edge"]["y"] - pre["edge"]["y"])
        # Tolerance is 25px, not the ~1px "exact lockstep" a naive reading of D-09/RESEARCH.md's
        # prose might suggest. FINDING (observed live, this run): the edge is a bezier-style edge
        # whose source anchor point is computed from the angle between source and target nodes,
        # not simply offset from the source node's center — so as the node moves, the anchor point
        # on its boundary shifts too, and the endpoint's raw delta is NOT identical to the node's
        # raw delta on every axis. Measured this run: node_delta's y matched edge_delta's y
        # EXACTLY (both axes' deltas agreed to 1e-9), while x diverged by ~19.6px on a 100px x
        # offset (~20%). 25px comfortably covers that measured divergence while still failing a
        # genuinely-decoupled endpoint (e.g. one that didn't move directionally with the node, or
        # moved by only a few px on a 100px/50px drag). Direction (sign) agreement on both axes is
        # asserted separately below as the sharper, geometry-independent form of "followed the
        # node" that this test can make without overfitting to one edge's curve routing.
        tolerance = 25.0
        assert (
            abs(node_delta[0] - edge_delta[0]) <= tolerance
            and abs(node_delta[1] - edge_delta[1]) <= tolerance
        ), (
            f"UAT-7-29 criterion 2: expected edge {edge_id!r}'s endpoint to follow node "
            f"{node_id!r} within tolerance; node_delta={node_delta!r} edge_delta={edge_delta!r} "
            f"(tolerance={tolerance})."
        )

        def _sign(v):
            return (v > 0) - (v < 0)

        assert _sign(node_delta[0]) == _sign(edge_delta[0]) and _sign(node_delta[1]) == _sign(
            edge_delta[1]
        ), (
            f"UAT-7-29 criterion 2: expected edge {edge_id!r}'s endpoint to move in the SAME "
            f"direction as node {node_id!r} on both axes; node_delta={node_delta!r} "
            f"edge_delta={edge_delta!r}."
        )

        # Criterion 3 — position (and edge endpoint) holds after release. No snap-back.
        assert post["pos"] == mid["pos"], (
            f"UAT-7-29 criterion 3: expected node {node_id!r}'s position to hold after release; "
            f"mid={mid['pos']!r} post={post['pos']!r}."
        )
        assert post["edge"] == mid["edge"], (
            f"UAT-7-29 criterion 3: expected edge {edge_id!r}'s sourceEndpoint() to hold after "
            f"release; mid={mid['edge']!r} post={post['edge']!r}."
        )

        # Criterion 4 — the other nodes are byte-identical, pre-drag versus post-release.
        assert pre["others"] == post["others"], (
            f"UAT-7-29 criterion 4: expected the other nodes {other_ids!r} to be unaffected by "
            f"dragging {node_id!r}; pre={pre['others']!r} post={post['others']!r}."
        )

        # Criterion 5 — no layout reset. This must be asserted against a value NOT already
        # consumed by criteria 1 and 3, or it proves nothing: `post != pre` is implied by
        # `mid != pre` (criterion 1) and `post == mid` (criterion 3), so it can never fail
        # independently once those hold, and it would ALSO be satisfied by a dagre re-run that
        # relocated the node to some arbitrary third position. Found by the Phase 207.1 code
        # review (WR-01) — the original form was a tautology wearing a fifth criterion's clothes.
        #
        # The falsifiable claim is that the node ended up where the DRAG put it: the mouse moved
        # (+100, +50) rendered pixels, which Cytoscape applies to the grabbed node's model
        # position divided by the viewport zoom. A silent layout reset reassigns dagre's own
        # coordinates and lands somewhere unrelated to the cursor, failing this.
        expected_pos = {
            "x": pre["pos"]["x"] + 100 / pre["zoom"],
            "y": pre["pos"]["y"] + 50 / pre["zoom"],
        }
        layout_tolerance = 10
        assert (
            abs(post["pos"]["x"] - expected_pos["x"]) <= layout_tolerance
            and abs(post["pos"]["y"] - expected_pos["y"]) <= layout_tolerance
        ), (
            f"UAT-7-29 criterion 5: expected node {node_id!r} to come to rest where the drag put "
            f"it, not where a re-run layout would place it; pre={pre['pos']!r} "
            f"post={post['pos']!r} expected~={expected_pos!r} zoom={pre['zoom']!r} "
            f"(tolerance={layout_tolerance})."
        )
        # Second half of the same evidence, and independent of the above: a real layout reset
        # would also move every untouched node, which criterion 4 has already ruled out.

        if pre["pos"] != {"x": 75, "y": 168} or pre["edge"] != {"x": 75, "y": 194}:
            print(
                "UAT-7-29 FINDING: pre-drag values disagree with the 2026-09-27 measurement "
                f"recorded in CONTEXT.md/RESEARCH.md — node pre-drag position={pre['pos']!r} "
                f"(expected {{'x': 75, 'y': 168}}), edge pre-drag sourceEndpoint={pre['edge']!r} "
                "(expected {'x': 75, 'y': 194}). Reported per plan instruction, not adjusted."
            )


def test_uat_7_29_control_no_mousedown(dashboard_origin):
    """Red-proof control for UAT-7-29 (D-10, SC#3).

    Performs the identical setup and mouse MOVEMENT as the main drag test and deliberately omits
    the mouse-button press — the absence is the point of this test, so nobody should "complete" it
    later by adding one. Its job is to prove the main test's assertions are load-bearing on
    the drag actually occurring, rather than comparing a value to itself. This is a separate
    pytest test node, not a comment or sub-assertion, so a reviewer can confirm the red-proof
    exists without reading any test body.
    """
    with chromium_page() as page:
        page.goto(dashboard_origin + "/roadmap")
        with diagnosing_mount_failure(page, guard=assert_spa_mounted):
            page.locator("main h1").first.wait_for(state="visible", timeout=15_000)
        assert_spa_mounted(page)

        _resolve_cy(page)
        node_id, edge_id = _select_draggable_candidate(page)

        before = page.evaluate(
            "(args) => { const cy = document.querySelector(args.sel)._cyreg.cy;"
            " return { pos: cy.$id(args.nodeId).position(), edge: cy.$id(args.edgeId).sourceEndpoint() }; }",
            {"sel": _CY_CONTAINER_SELECTOR, "nodeId": node_id, "edgeId": edge_id},
        )

        container_box = page.evaluate(
            "(sel) => { const r = document.querySelector(sel).getBoundingClientRect();"
            " return { x: r.x, y: r.y }; }",
            _CY_CONTAINER_SELECTOR,
        )
        rendered = page.evaluate(
            "(args) => document.querySelector(args.sel)._cyreg.cy.$id(args.nodeId).renderedPosition()",
            {"sel": _CY_CONTAINER_SELECTOR, "nodeId": node_id},
        )
        start_x = container_box["x"] + rendered["x"]
        start_y = container_box["y"] + rendered["y"]

        page.mouse.move(start_x, start_y)
        # Deliberately NO mouse-button press anywhere in this test — the omission is the point.
        # Do not "complete" this control later by adding one.
        page.mouse.move(start_x + 100, start_y + 50, steps=10)

        after = page.evaluate(
            "(args) => { const cy = document.querySelector(args.sel)._cyreg.cy;"
            " return { pos: cy.$id(args.nodeId).position(), edge: cy.$id(args.edgeId).sourceEndpoint() }; }",
            {"sel": _CY_CONTAINER_SELECTOR, "nodeId": node_id, "edgeId": edge_id},
        )

        assert before["pos"] == after["pos"], (
            f"UAT-7-29 control: expected NO position change for node {node_id!r} without a "
            f"mouse-button press; before={before['pos']!r} after={after['pos']!r}."
        )
        assert before["edge"] == after["edge"], (
            f"UAT-7-29 control: expected NO sourceEndpoint() change for edge {edge_id!r} without "
            f"a mouse-button press; before={before['edge']!r} after={after['edge']!r}."
        )


# KBD-01 (D-07) — keyboard-only table-region walkthrough + paired control. Module-level constants
# shared by both nodes so the control cannot drift from the main node's route/viewport (per the
# plan's explicit instruction). Chosen via local measurement: /findings renders an 8-column table
# (findings.tsx:122-187: Severity, Host, Port, Title, Protocol, Quantum Risk, Source, Storyline)
# over 2 seeded hosts, which overflows reliably at 600x700 (below the 1024px breakpoint, so the
# sidebar is collapsed too) — measured locally across 5 consecutive runs, all 5 landing on
# scrollWidth=668 / clientWidth=518, a stable 150px margin far wider than any plausible layout
# jitter.
_KBD_01_ROUTE = "/findings"
_KBD_01_VIEWPORT = {"width": 600, "height": 700}
_KBD_01_REGION_SELECTOR = '[role="region"][tabindex="0"]'


def _kbd_01_region_precondition(page):
    """Assert the overflow + role/tabindex precondition on the first table region.

    Returns the region's `aria-label` and overflow dimensions so both KBD-01 nodes verify an
    identical, independently-checked starting point (T-219-04 — a vacuous pass is the threat this
    guards against: no silent "the region never rendered" false green).
    """
    page.wait_for_selector(f"{_KBD_01_REGION_SELECTOR} table tbody tr", timeout=15_000)
    region = page.locator(_KBD_01_REGION_SELECTOR).first
    dims = region.evaluate(
        "(el) => ({ scrollWidth: el.scrollWidth, clientWidth: el.clientWidth,"
        " scrollHeight: el.scrollHeight, clientHeight: el.clientHeight,"
        " ariaLabel: el.getAttribute('aria-label') })"
    )
    assert dims["scrollWidth"] > dims["clientWidth"], (
        f"KBD-01 precondition: expected the table region to overflow horizontally at "
        f"{_KBD_01_VIEWPORT!r} on {_KBD_01_ROUTE!r}; scrollWidth={dims['scrollWidth']!r} "
        f"clientWidth={dims['clientWidth']!r}. The region never overflowed — narrow the viewport "
        "or pick another route."
    )
    return dims


def _kbd_01_press_until_stable(page, key, *, max_presses=60, settle_presses=3):
    """Press ``key`` repeatedly, reading ``scrollLeft`` after each, until it stops changing.

    Returns the final, stable ``scrollLeft``. Bounded at ``max_presses`` so a genuinely broken key
    binding fails fast instead of hanging.
    """
    prev = page.evaluate("(sel) => document.querySelector(sel).scrollLeft", _KBD_01_REGION_SELECTOR)
    stable_streak = 0
    for _ in range(max_presses):
        page.keyboard.press(key)
        page.wait_for_timeout(50)
        current = page.evaluate(
            "(sel) => document.querySelector(sel).scrollLeft", _KBD_01_REGION_SELECTOR
        )
        if current == prev:
            stable_streak += 1
            if stable_streak >= settle_presses:
                break
        else:
            stable_streak = 0
        prev = current
    return prev


def test_kbd_01_keyboard_only_table_region_scroll(dashboard_origin):
    """KBD-01 / D-07 — Tab-only navigation reaches the table region and arrow keys scroll it.

    Reaches the region using ONLY ``page.keyboard.press("Tab")`` from page load — no click, no
    mouse, no ``.focus()`` call anywhere in this test. ``page.evaluate``/``page.wait_for_function``
    are used only to READ state (``document.activeElement``, scroll offsets, dimensions), never to
    mutate focus or scroll.

    Scrolling is native (D-04): there is no app-side key handler anywhere in this codebase for
    these keys — the browser's own default keyboard behaviour on a scrollable, focused element does
    the work. The plan-01 wrapper's only JS behaviour is the conditional ``tabIndex``/``role``
    attribute toggle on mount/resize; it registers no ``onKeyDown``/``onKeyUp`` handler at all
    (confirmed in 219-01-SUMMARY.md's acceptance-criteria greps).
    """
    with chromium_page() as page:
        # Mount at the harness's default 1440x900 viewport FIRST (same idiom as UAT-7-23): the
        # D-04 mount guard asserts the full-width sidebar wordmark, which is only rendered above
        # the 1024px breakpoint. Narrowing happens only after the guard passes.
        page.goto(dashboard_origin + _KBD_01_ROUTE)
        with diagnosing_mount_failure(page, guard=assert_spa_mounted):
            page.locator("main h1").first.wait_for(state="visible", timeout=15_000)
        assert_spa_mounted(page)
        page.set_viewport_size(_KBD_01_VIEWPORT)

        dims = _kbd_01_region_precondition(page)

        # Tab loop: bounded at 80 presses, printing the focused-element sequence on failure so a
        # regression shows WHERE focus went instead of just "it never arrived".
        focused_sequence = []
        landed = False
        for _ in range(80):
            page.keyboard.press("Tab")
            descriptor = page.evaluate(
                "() => { const a = document.activeElement; return a ? "
                "(a.getAttribute('role') + '|' + a.getAttribute('tabindex')) : null }"
            )
            focused_sequence.append(descriptor)
            if descriptor == "region|0":
                landed = True
                break
        if not landed:
            raise AssertionError(
                "KBD-01: Tab never reached a region|0 element within 80 presses. Focused-element "
                f"sequence: {focused_sequence!r}"
            )

        focused_label = page.evaluate("() => document.activeElement.getAttribute('aria-label')")
        assert focused_label == dims["ariaLabel"], (
            "KBD-01: Tab landed on a region|0 element, but it is not the precondition-checked "
            f"table region; focused aria-label={focused_label!r}, expected {dims['ariaLabel']!r}."
        )

        scroll_left_initial = page.evaluate(
            "(sel) => document.querySelector(sel).scrollLeft", _KBD_01_REGION_SELECTOR
        )
        assert scroll_left_initial == 0, (
            f"KBD-01: expected the region's scrollLeft to start at 0, got {scroll_left_initial!r}."
        )

        for _ in range(5):
            page.keyboard.press("ArrowRight")
        page.wait_for_function(
            "(sel) => document.querySelector(sel).scrollLeft > 0",
            arg=_KBD_01_REGION_SELECTOR,
            timeout=2000,
        )
        scroll_left_after_arrows = page.evaluate(
            "(sel) => document.querySelector(sel).scrollLeft", _KBD_01_REGION_SELECTOR
        )
        assert scroll_left_after_arrows > 0, (
            "KBD-01: expected ArrowRight x5 on the focused region to increase scrollLeft above 0; "
            f"got {scroll_left_after_arrows!r}."
        )

        # Deviation from the plan's literal End/Home wording (recorded in SUMMARY): live
        # measurement in Chromium showed End/Home are no-ops on a region that overflows ONLY
        # horizontally -- those keys target the vertical scroll axis by default and this wrapper
        # has no vertical overflow to act on. Repeated ArrowRight/ArrowLeft are the keys this
        # specific region actually responds to for reaching its scroll extremes, so they replace
        # End/Home here; the underlying must-have (reach the far end, then return to 0, via native
        # key handling only) is unchanged.
        scroll_left_at_end = _kbd_01_press_until_stable(page, "ArrowRight")
        assert scroll_left_at_end >= scroll_left_after_arrows, (
            "KBD-01: expected continued ArrowRight presses to leave scrollLeft at or beyond the "
            f"post-5-press value; after_5={scroll_left_after_arrows!r} "
            f"at_end={scroll_left_at_end!r}."
        )

        scroll_left_after_home = _kbd_01_press_until_stable(page, "ArrowLeft")
        assert scroll_left_after_home == 0, (
            "KBD-01: expected repeated ArrowLeft presses to return scrollLeft to 0, got "
            f"{scroll_left_after_home!r}."
        )

        if dims["scrollHeight"] > dims["clientHeight"]:
            scroll_top_before = page.evaluate(
                "(sel) => document.querySelector(sel).scrollTop", _KBD_01_REGION_SELECTOR
            )
            page.keyboard.press("PageDown")
            page.wait_for_function(
                "(args) => document.querySelector(args.sel).scrollTop > args.floor",
                arg={"sel": _KBD_01_REGION_SELECTOR, "floor": scroll_top_before},
                timeout=2000,
            )
            scroll_top_after = page.evaluate(
                "(sel) => document.querySelector(sel).scrollTop", _KBD_01_REGION_SELECTOR
            )
            assert scroll_top_after > scroll_top_before, (
                "KBD-01: region also overflows vertically; expected PageDown to increase "
                f"scrollTop above {scroll_top_before!r}, got {scroll_top_after!r}."
            )
        # else: this wrapper has no height cap of its own, so any vertical scroll happens at the
        # page level rather than inside the region — not asserted here, per the plan's spec.


def test_kbd_01_keyboard_control_unfocused_region_does_not_scroll(dashboard_origin):
    """Red-proof control for KBD-01 (T-219-04): ArrowRight without focusing the region is a no-op.

    Same route, same viewport, same precondition as the main node, deliberately WITHOUT ever
    pressing Tab — focus stays on ``<body>``. Proves the main test's scroll is caused by the region
    itself having focus, not by some ambient page-level key handling.
    """
    with chromium_page() as page:
        # Mount at the harness's default 1440x900 viewport FIRST (same idiom as UAT-7-23): the
        # D-04 mount guard asserts the full-width sidebar wordmark, which is only rendered above
        # the 1024px breakpoint. Narrowing happens only after the guard passes.
        page.goto(dashboard_origin + _KBD_01_ROUTE)
        with diagnosing_mount_failure(page, guard=assert_spa_mounted):
            page.locator("main h1").first.wait_for(state="visible", timeout=15_000)
        assert_spa_mounted(page)
        page.set_viewport_size(_KBD_01_VIEWPORT)

        _kbd_01_region_precondition(page)

        active_tag = page.evaluate("() => document.activeElement.tagName")
        assert active_tag == "BODY", (
            f"KBD-01 control: expected focus to remain on <body> before any key press, got "
            f"<{active_tag.lower()}>."
        )

        scroll_left_before = page.evaluate(
            "(sel) => document.querySelector(sel).scrollLeft", _KBD_01_REGION_SELECTOR
        )
        assert scroll_left_before == 0, (
            f"KBD-01 control: expected the region's scrollLeft to start at 0, got "
            f"{scroll_left_before!r}."
        )

        for _ in range(5):
            page.keyboard.press("ArrowRight")
        # No wait_for_function here on purpose: proving a value STAYS put cannot be expressed as
        # "wait until a condition becomes true". A short fixed settle is the correct shape for a
        # negative assertion.
        page.wait_for_timeout(300)

        scroll_left_after = page.evaluate(
            "(sel) => document.querySelector(sel).scrollLeft", _KBD_01_REGION_SELECTOR
        )
        assert scroll_left_after == 0, (
            "KBD-01 control: expected ArrowRight x5 to leave scrollLeft at exactly 0 when the "
            f"region is not focused; got {scroll_left_after!r}."
        )
