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
    diagnosing_mount_failure,
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
