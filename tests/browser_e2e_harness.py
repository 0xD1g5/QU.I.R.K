"""Tier-2 browser-E2E harness — Phase 207 / COV-05.

This module is deliberately **not** a ``conftest.py``. A ``tests/conftest.py`` addition would
apply to the entire 3000+-test suite; a plain helper module imported by a single test file cannot
affect anything else. Keep it that way.

Why a new harness exists at all: the established ``dashboard_client`` fixture
(``tests/conftest.py``) is ``fastapi.testclient.TestClient``-based. ``TestClient`` drives the ASGI
app in-process and opens **no TCP port**, so Playwright — which needs a real HTTP origin to attach
to — cannot use it. Tier 2 therefore backgrounds a real ``uvicorn`` process on a real loopback port.

Every helper here converts a missing Chromium binary into a clean ``pytest.skip``, never an error.
That is load-bearing, not cosmetic: ``tests/test_uat_disposition_integrity.py`` executes cited
pytest nodes inside the required ``Linux Full Suite`` job, and an **erroring** node reddens that
required job even under a ``CI-EXEMPT:`` declaration (D-10). A skipping node does not.

Helpers:
    ``chromium_page()``          — function-scoped context manager yielding a fresh Playwright page.
    ``seed_dashboard_db(path)``  — file-backed SQLite with scan data and *no identity data*.
    ``serve_dashboard(path)``    — context manager yielding a real ``http://127.0.0.1:<port>`` origin.
    ``assert_spa_mounted(page)`` — D-04's MANDATORY vacuous-pass guard (dashboard shell routes).
    ``assert_print_view_mounted(page)`` — the same guard for the chrome-free ``/print`` route.
    ``collect_console_errors(p)` — attaches listeners, returns a mutable error list.
"""
from __future__ import annotations

import contextlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base, CryptoEndpoint

# The scan-session key every seeded row shares. Tests may reference it.
SEED_SCAN_RUN_ID = "2026-09-26T12:00:00"
SEED_SCANNED_AT = datetime(2026, 9, 26, 12, 0, 0)

# Viewport wide enough for the `hidden lg:block` full sidebar wordmark
# (src/dashboard/src/components/sidebar.tsx:87) to render rather than the `Q` monogram.
_VIEWPORT = {"width": 1440, "height": 900}

# The literal signature of app.py's unbuilt-dashboard placeholder branch
# (quirk/dashboard/api/app.py:176-184). Its presence means no application JS is on the page.
_PLACEHOLDER_SIGNATURE = "npm run build"

# Only the built bundle's authenticated shell renders this; LoginPage does not.
_SIDEBAR_NAV = 'nav[aria-label="Dashboard navigation"]'
# LoginPage's form. Its presence means an API token resolved and AuthProvider flipped
# to `unauthenticated` (src/dashboard/src/pages/login.tsx:95).
_LOGIN_FORM = 'form[aria-label="Dashboard login"]'
# Present on both the shell sidebar and LoginPage, so NOT sufficient alone — see D-04 below.
_WORDMARK = "QU.I.R.K."

# /print is chrome-free (App.tsx:80-82 returns <PrintPage/> above the shell), so it has no sidebar
# nav and no `aside` wordmark. These are its own bundle-only mount signals — see
# assert_print_view_mounted(). `body[data-ready="true"]` is the selector POST /api/export/pdf itself
# waits on (quirk/dashboard/api/routes/pdf.py:87).
_PRINT_READY = 'body[data-ready="true"]'
_PRINT_HEADING = "QU.I.R.K. — Scan Results"

# Identity findings are derived (not stored) — quirk/dashboard/api/routes/scan.py:419
# `_derive_identity_findings` reads these CryptoEndpoint columns plus a KERBEROS/SAML/DNSSEC
# `protocol` value. These are the columns the empty-identity invariant polices.
_IDENTITY_COLUMNS = (
    "kerberos_scan_json",
    "saml_scan_json",
    "dnssec_scan_json",
)
_IDENTITY_PROTOCOLS = ("KERBEROS", "SAML", "DNSSEC")


# ---------------------------------------------------------------------------
# 1. Chromium
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def chromium_page():
    """Yield a fresh Playwright ``page``, or ``pytest.skip`` if Chromium is unavailable.

    FUNCTION-SCOPED, DELIBERATELY. Do **not** promote this into a module- or session-scoped
    pytest fixture, and do not hoist it into a shared fixture "for speed". A shared Playwright
    context is the exact shape of TRIAGE-149 Cluster 2 (``docs/test-triage-149.md:57-75``): a
    ``PlaywrightContextManager`` singleton torn down by an earlier full-suite test, order-dependent,
    **14 tests quarantined on that one root cause**, every one "confirmed passing standalone".
    Phase 207's isolated CI job exists precisely to avoid that failure mode; re-introducing a shared
    browser singleton inside the new job would defeat the entire point of the job.

    Sharing the *server process* across tests is fine and desirable (see ``serve_dashboard``).
    Sharing the *browser* is not.
    """
    # Imported inside the function, not at module top level: `playwright` is an extras-only
    # dependency (pyproject.toml `dashboard` extras). An unconditional top-level import silently
    # breaks minimal installs at collection time.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - exercised only on minimal installs
        pytest.skip(
            f"playwright is not importable ({exc}) — install the `dashboard` extras. "
            "Expected in minimal installs; Phase 207 Tier-2 executes in the Browser E2E job."
        )

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # Playwright Error / OSError / RuntimeError all land here.
            # Never let this propagate: an ERROR reddens the required Linux Full Suite job even
            # under a CI-EXEMPT declaration (D-10), while a SKIP does not. That breadth is
            # load-bearing and must NOT be narrowed.
            #
            # But breadth has a cost, observed live during 207-03: a *transient* launch failure on
            # a machine where Chromium IS installed becomes a skip that is byte-identical to the
            # intended "no Chromium here" skip. In the Browser E2E job (where Chromium is
            # installed on purpose) that reads as green-with-no-coverage — the exact shape
            # "a skip is not a pass" exists to catch, made invisible. Observed once in 8
            # consecutive local runs and not reproduced in the following 8.
            #
            # So the skip stays a skip, but it now reports whether the executable was actually on
            # disk. `NOT installed` = the expected Linux-Full-Suite skip. `IS present` = a
            # transient launch failure that must be investigated, not read as expected.
            try:
                exe = p.chromium.executable_path
                present = os.path.exists(exe)
            except Exception:  # pragma: no cover - executable_path is not itself expected to throw
                exe, present = "<unresolvable>", False
            verdict = (
                f"Chromium executable IS present at {exe} — this skip is therefore a TRANSIENT "
                "launch failure, NOT the expected missing-browser skip. Investigate it; do not "
                "read it as expected non-coverage."
                if present
                else f"Chromium executable is NOT installed (looked for {exe}) — this is the "
                "expected state in Linux Full Suite."
            )
            pytest.skip(
                "Cannot launch headless Chromium "
                f"({type(exc).__name__}: {exc}). Remedy: `python -m playwright install chromium`. "
                f"{verdict} Phase 207 Tier-2 executes for real in the Browser E2E job "
                "(D-01/D-02)."
            )
        try:
            context = browser.new_context(viewport=_VIEWPORT)
            try:
                page = context.new_page()
                yield page
            finally:
                context.close()
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# 2. DB seeding
# ---------------------------------------------------------------------------

def seed_dashboard_db(db_path) -> str:
    """Create a file-backed SQLite DB at ``db_path`` with one seeded scan session.

    ###########################################################################
    # SEEDS NO IDENTITY DATA. THIS IS A DELIBERATE REGRESSION GUARD, NOT AN
    # OVERSIGHT. DO NOT "COMPLETE" THIS FIXTURE BY ADDING IDENTITY ROWS.
    #
    # UAT-7-32's own pass criteria require that `/identity` loads without errors
    # *even when no identity scan data is present*. Populating kerberos/saml/dnssec
    # data here to make the fixture look finished would silently delete the only
    # guard that case has. The invariant is asserted in code below and the
    # assertion message names UAT-7-32.
    ###########################################################################

    Rows span two hosts, several protocols, a mix of TLS versions and key algorithms, and one
    certificate-bearing endpoint — enough for ``/findings``, ``/certificates``, ``/cbom``,
    ``/roadmap`` and ``/print`` to render non-trivially.

    Returns the shared ``scan_run_id``.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    common = dict(scan_run_id=SEED_SCAN_RUN_ID, scanned_at=SEED_SCANNED_AT)
    rows = [
        # Certificate-bearing, weak RSA-2048 + legacy TLS 1.0 support -> findings + roadmap items.
        CryptoEndpoint(
            host="web01.seed.local",
            port=443,
            protocol="TLS",
            tls_version="TLSv1.2",
            cipher_suite="ECDHE-RSA-AES128-GCM-SHA256",
            tls_supported_versions="TLSv1,TLSv1.1,TLSv1.2",
            tls_weak_ciphers_present=True,
            tls_legacy_suites_present=True,
            tls_pfs_supported=True,
            cert_subject="CN=web01.seed.local",
            cert_issuer="CN=Seed Test CA",
            cert_sans="web01.seed.local",
            cert_sig_alg="sha256WithRSAEncryption",
            cert_pubkey_alg="RSA",
            cert_pubkey_size=2048,
            cert_not_before=SEED_SCANNED_AT - timedelta(days=30),
            cert_not_after=SEED_SCANNED_AT + timedelta(days=45),
            chain_verified=True,
            severity="HIGH",
            **common,
        ),
        # Modern TLS 1.3 + ECDSA, second host -> non-trivial CBOM algorithm variety.
        CryptoEndpoint(
            host="web02.seed.local",
            port=8443,
            protocol="TLS",
            tls_version="TLSv1.3",
            cipher_suite="TLS_AES_256_GCM_SHA384",
            tls_supported_versions="TLSv1.2,TLSv1.3",
            tls_weak_ciphers_present=False,
            tls_legacy_suites_present=False,
            tls_pfs_supported=True,
            cert_subject="CN=web02.seed.local",
            cert_issuer="CN=Seed Test CA",
            cert_sig_alg="ecdsa-with-SHA384",
            cert_pubkey_alg="EC",
            cert_pubkey_size=384,
            cert_not_before=SEED_SCANNED_AT - timedelta(days=10),
            cert_not_after=SEED_SCANNED_AT + timedelta(days=300),
            chain_verified=True,
            severity="LOW",
            **common,
        ),
        # SSH endpoint -> a non-TLS protocol on the findings/CBOM surfaces.
        CryptoEndpoint(
            host="web02.seed.local",
            port=22,
            protocol="SSH",
            ssh_audit_json=json.dumps(
                {
                    "kex": [{"algorithm": "diffie-hellman-group14-sha1"}],
                    "key": [{"algorithm": "ssh-rsa", "keysize": 2048}],
                }
            ),
            severity="MEDIUM",
            **common,
        ),
    ]

    db = Session()
    try:
        db.add_all(rows)
        db.commit()
    finally:
        db.close()

    _assert_no_identity_data(Session)
    engine.dispose()
    return SEED_SCAN_RUN_ID


def _assert_no_identity_data(Session) -> None:
    """Assert the empty-identity invariant UAT-7-32 depends on.

    See the block comment in ``seed_dashboard_db``: identity data is absent ON PURPOSE.
    """
    db = Session()
    try:
        endpoints = db.query(CryptoEndpoint).all()
        offenders = []
        for ep in endpoints:
            for col in _IDENTITY_COLUMNS:
                if getattr(ep, col, None):
                    offenders.append(f"{ep.host}:{ep.port} has non-null {col}")
            if (ep.protocol or "").upper() in _IDENTITY_PROTOCOLS:
                offenders.append(f"{ep.host}:{ep.port} has identity protocol {ep.protocol}")
        assert not offenders, (
            "Seed fixture MUST contain no identity scan data — UAT-7-32 requires that "
            "/identity loads cleanly with NO identity data present, and this fixture is that "
            "case's only regression guard. Identity data found: "
            + "; ".join(offenders)
            + ". Do not 'complete' the fixture by adding identity rows; see the block comment "
            "in seed_dashboard_db()."
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. Real HTTP origin
# ---------------------------------------------------------------------------

def _free_port() -> int:
    """Bind an ephemeral port, read it, release it.

    Not hardcoded (e.g. 8512): a fixed port collides with a developer's running `quirk serve`
    and with a parallel test run.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextlib.contextmanager
def serve_dashboard(db_path, config_path=None):
    """Background a real uvicorn serving ``quirk.dashboard.api.app:app``; yield its origin URL.

    ``config_path`` should be a path under the test's tmp dir that does NOT exist (see below).

    Ports the proven Windows-CI idiom at ``.github/workflows/python-ci.yml:289-319`` — subprocess
    uvicorn plus a ``GET /api/health`` readiness poll. ``/api/health`` is the deterministic
    readiness route: exactly 200 once listening, never a 404 or an ambiguous redirect.

    No ``npm run build`` step and no Node dependency: the built bundle is committed at
    ``quirk/dashboard/static`` (14 tracked files) and gate-verified fresh (D-04 as corrected).
    """
    port = _free_port()
    child_env = dict(os.environ)

    # QUIRK_DB_PATH is returned verbatim by deps._default_db_path(), so this fully controls which
    # DB the served app reads — and keeps the test off the developer's real
    # ./quirk-output/quirk.db (threat T-207-06).
    child_env["QUIRK_DB_PATH"] = str(db_path)

    # QUIRK_SERVE_PORT — REQUIRED, not optional. `quirk serve` sets it
    # (quirk/dashboard/server.py:161); a bare `python -m uvicorn` does not, and this harness must
    # reproduce the real serve environment. POST /api/export/pdf renders
    # http://127.0.0.1:{QUIRK_SERVE_PORT or 8512}/print with its own Playwright instance
    # (quirk/dashboard/api/routes/pdf.py:48). Without this line the export route dials the
    # hardcoded 8512 default, nothing is listening there, and the connection-refused is mapped into
    # the DASHBOARD-012 bucket — whose message reads "Playwright not installed for PDF export"
    # even though Playwright is installed and working. That misleading 503 is what UAT-7-17's
    # download interception hits: no download event ever fires, and the failure looks like a
    # Playwright problem rather than a port problem. Found live during 207-03 Task 2.
    child_env["QUIRK_SERVE_PORT"] = str(port)

    # AUTH PASSTHROUGH — READ THIS BEFORE CHANGING EITHER LINE BELOW. This is the single most
    # likely cause of a confusing Tier-2 failure. src/dashboard/src/context/AuthProvider.tsx
    # probes GET /api/scans on mount: 200 -> authenticated; 401 -> unauthenticated -> LoginPage
    # renders with no sidebar and no routes. middleware/auth._get_configured_token() resolves
    # QUIRK_API_TOKEN first, then falls back to reading
    # os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml") and returning cfg.security.api_token.
    # Auth is disabled (passthrough) only when BOTH resolve empty. So the env var must be POPPED
    # and the config path must point at a file that does not exist — otherwise every Tier-2 test
    # silently lands on LoginPage instead of the dashboard. assert_spa_mounted() names this case
    # explicitly so the failure is not a puzzle.
    child_env.pop("QUIRK_API_TOKEN", None)
    if config_path is None:
        config_path = os.path.join(str(db_path) + ".no-such-dir", "absent-config.yaml")
    child_env["QUIRK_CONFIG_PATH"] = str(config_path)

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "quirk.dashboard.api.app:app",
            "--host", "127.0.0.1", "--port", str(port),
        ],
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    origin = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 30
        ready = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f"{origin}/api/health", timeout=2) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except OSError:
                pass
            time.sleep(1)
        if not ready:
            proc.kill()
            out = b""
            try:
                out = proc.communicate(timeout=10)[0] or b""
            except Exception:
                pass
            # A server that never came up is a real FAILURE, not a skip: nothing about it is
            # environment-optional the way a missing Chromium binary is.
            pytest.fail(
                f"uvicorn did not become ready on {origin}/api/health within 30s "
                f"(exit={proc.returncode}). Captured server output:\n"
                + out.decode("utf-8", "replace")
            )
        yield origin
    finally:
        # T-207-05: never leak a subprocess holding a port after an aborted run.
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                with contextlib.suppress(Exception):
                    proc.wait(timeout=10)
        with contextlib.suppress(Exception):
            if proc.stdout is not None:
                proc.stdout.close()


# ---------------------------------------------------------------------------
# 4. D-04 vacuous-pass guard
# ---------------------------------------------------------------------------

def assert_spa_mounted(page) -> None:
    """D-04's MANDATORY vacuous-pass guard. Call it in EVERY Tier-2 test.

    Why it exists: a stale committed bundle, a failed ``/assets`` mount, a renamed content hash,
    or any future change that stops tracking ``quirk/dashboard/static``'s 14 files all produce the
    *same* silent outcome — a page that loads with **no application JavaScript on it**. In that
    state a "zero console errors" assertion passes **vacuously**, because nothing is loaded to
    throw. This guard turns that into a loud, named failure.
    """
    content = page.content()

    # (a) The unbuilt-dashboard placeholder branch (app.py:176-184) is NOT what we are looking at.
    assert _PLACEHOLDER_SIGNATURE not in content, (
        f"D-04 mount guard: page content contains the literal placeholder signature "
        f"'{_PLACEHOLDER_SIGNATURE}', which is the signature of quirk/dashboard/api/app.py's "
        "unbuilt-dashboard branch — index.html was not found on disk. A vacuous pass was "
        "prevented: the placeholder HTML loads fine and throws nothing."
    )

    # (b) React actually mounted, rather than merely serving the shell. index.html's body is
    #     exactly `<div id="root"></div>` plus the module script tag, so an empty #root means the
    #     bundle never executed.
    root_children = page.evaluate(
        "() => { const r = document.getElementById('root');"
        " return r ? r.children.length : -1; }"
    )
    assert root_children > 0, (
        f"D-04 mount guard: #root has {root_children} child elements "
        "(-1 means #root is absent entirely), so React never mounted — the page is the bare "
        "index.html shell with no application JavaScript on it. A vacuous pass was prevented: "
        "any 'no console errors' assertion would have passed against an empty page. Likely "
        "cause: a stale or untracked quirk/dashboard/static bundle, or a failed /assets mount "
        "(quirk/dashboard/api/app.py:161-168)."
    )

    # (c) Not the login form. QU.I.R.K. alone cannot distinguish these — LoginPage renders the
    #     same wordmark (src/dashboard/src/pages/login.tsx:80-82) — so assert the authenticated
    #     shell's sidebar nav, which only the dashboard renders.
    assert page.locator(_LOGIN_FORM).count() == 0, (
        "D-04 mount guard: the login form is present, so AuthProvider's GET /api/scans probe "
        "returned 401 and the SPA rendered LoginPage instead of the dashboard. A vacuous pass "
        "was prevented. Cause: an API token resolved in the served process — check that "
        "QUIRK_API_TOKEN is popped from the child env and QUIRK_CONFIG_PATH points at a file "
        "that does not exist (see serve_dashboard)."
    )
    assert page.locator(_SIDEBAR_NAV).count() > 0, (
        f"D-04 mount guard: the authenticated shell's sidebar nav ({_SIDEBAR_NAV}) is absent, so "
        "the dashboard shell did not render even though the login form is also absent. A vacuous "
        "pass was prevented — do not trust anything else observed on this page."
    )

    # (d) The sidebar wordmark is visible — an element only the built bundle can produce.
    #     Checked last so the more specific failures above report first.
    wordmark = page.locator("aside").get_by_text(_WORDMARK, exact=True).first
    assert wordmark.is_visible(), (
        f"D-04 mount guard: the sidebar wordmark '{_WORDMARK}' is not visible. A vacuous pass "
        "was prevented: the built bundle renders it at "
        "src/dashboard/src/components/sidebar.tsx:87 and nothing else does."
    )


def assert_print_view_mounted(page) -> None:
    """D-04's vacuous-pass guard for the chrome-free ``/print`` route.

    ``assert_spa_mounted()`` cannot be used on ``/print``: that route is intercepted **above** the
    dashboard shell (``src/dashboard/src/App.tsx:80-82`` returns ``<PrintPage />`` before ``Sidebar``
    or ``Routes`` are reached, with an in-code comment stating the omission is deliberate — a second
    registration inside the shell would render the sidebar on the print view). So there is no
    ``nav[aria-label="Dashboard navigation"]`` and no ``aside`` wordmark to assert, by design.

    This is the same guard pointed at the print view's own bundle-only artifacts, so ``/print`` is
    not the one route in the UAT-7-32 walk that can pass vacuously:
      (a) the unbuilt-dashboard placeholder branch is not what we are looking at;
      (b) React mounted (``#root`` has children);
      (c) this is not ``LoginPage``;
      (d) ``body[data-ready="true"]`` — the print view's own readiness flag, which only the built
          bundle sets. ``POST /api/export/pdf`` waits on this exact selector
          (``quirk/dashboard/api/routes/pdf.py:87``) before calling ``page.pdf()``;
      (e) the print report heading is visible.
    """
    content = page.content()

    assert _PLACEHOLDER_SIGNATURE not in content, (
        f"D-04 mount guard (/print): page content contains the literal placeholder signature "
        f"'{_PLACEHOLDER_SIGNATURE}' — quirk/dashboard/api/app.py's unbuilt-dashboard branch. "
        "A vacuous pass was prevented: the placeholder HTML loads fine and throws nothing."
    )

    root_children = page.evaluate(
        "() => { const r = document.getElementById('root');"
        " return r ? r.children.length : -1; }"
    )
    assert root_children > 0, (
        f"D-04 mount guard (/print): #root has {root_children} child elements (-1 means #root is "
        "absent entirely), so React never mounted — no application JavaScript is on this page and "
        "a 'zero console errors' assertion would pass vacuously."
    )

    assert page.locator(_LOGIN_FORM).count() == 0, (
        "D-04 mount guard (/print): the login form is present, so AuthProvider's GET /api/scans "
        "probe returned 401 and the SPA rendered LoginPage instead of the print view. See "
        "serve_dashboard's AUTH PASSTHROUGH comment."
    )

    assert page.locator(_PRINT_READY).count() > 0, (
        f"D-04 mount guard (/print): {_PRINT_READY} is absent — the print view never signalled "
        "readiness. This is the same selector POST /api/export/pdf waits on before rendering, so "
        "its absence means the print view did not finish rendering its data."
    )

    heading = page.locator("h1").first
    assert heading.is_visible() and heading.inner_text().strip() == _PRINT_HEADING, (
        f"D-04 mount guard (/print): expected the print report heading {_PRINT_HEADING!r} to be "
        f"visible; observed {heading.inner_text().strip()!r}. Only the built bundle renders it "
        "(src/dashboard/src/pages/print.tsx:444)."
    )


@contextlib.contextmanager
def diagnosing_mount_failure(page, guard=None):
    """Convert an opaque Playwright ``TimeoutError`` from a content wait into D-04's NAMED
    mount diagnosis, without weakening the wait.

    WHY THIS EXISTS (Phase 207 review W-04). Every Tier-2 test waits on some route-specific
    content — a heading, the wordmark — *before* asserting the D-04 mount guard, because
    ``networkidle`` means "no in-flight requests", not "React has committed a render", and
    asserting the guard first races first paint (the ``#root`` leg can fire with 0 children,
    a FALSE failure claiming the bundle never mounted).

    That ordering is correct, but on its own it has a cost: the two states D-04 exists to
    catch BOTH make the awaited content never appear, so both surface as a 15-second
    ``TimeoutError: waiting for locator("main h1")`` instead of their named cause:

      (a) ``index.html`` missing -> ``quirk/dashboard/api/app.py``'s placeholder branch,
          which renders no ``<main>`` at all, so ``main h1`` can never match;
      (b) ``/assets`` not mounted / bundle 404s -> ``#root`` stays empty, so no route
          heading is ever rendered.

    Diagnosis is D-04's entire stated purpose ("turns that into a loud, **named** failure").
    So the wait stays exactly as strong as it was, and on timeout the guard is run inside
    the handler: if the page is in a state the guard can name, the test fails with that
    named ``AssertionError`` instead of the timeout. If the guard PASSES — the SPA really did
    mount and the awaited content genuinely never appeared — the original timeout is
    re-raised unchanged, because then the timeout IS the honest finding.

    Nothing here can convert a failure into a pass: both paths raise.
    """
    from playwright.sync_api import TimeoutError as PwTimeoutError

    if guard is None:
        guard = assert_spa_mounted
    try:
        yield
    except PwTimeoutError:
        # Raises AssertionError with the specific D-04 cause if there is one to name.
        guard(page)
        # The guard found nothing wrong, so the content wait's own timeout is the finding.
        raise


def collect_console_errors(page) -> list[str]:
    """Attach listeners and return a mutable list that accumulates error-level page problems.

    Attach BEFORE navigating, or anything thrown during initial load is missed.

    Captures exactly three error classes, per UAT-7-32's wording that warnings are acceptable and
    errors are not:
      - ``console`` messages whose type is ``error`` (console.warn/info/log are ignored)
      - ``pageerror`` events (uncaught exceptions)
      - ``response`` events for ``/api/`` URLs with status >= 400
    """
    errors: list[str] = []

    def _on_console(msg) -> None:
        if msg.type == "error":
            errors.append(f"console.error: {msg.text}")

    def _on_pageerror(exc) -> None:
        errors.append(f"pageerror: {exc}")

    def _on_response(resp) -> None:
        if "/api/" in resp.url and resp.status >= 400:
            errors.append(f"http {resp.status}: {resp.url}")

    page.on("console", _on_console)
    page.on("pageerror", _on_pageerror)
    page.on("response", _on_response)
    return errors
