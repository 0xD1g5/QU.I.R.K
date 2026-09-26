"""D-10 contract guard — the Tier-2 browser module must never ERROR where Chromium is absent.

Why this file exists (Phase 207, finding W-10). ``dashboard_origin`` in
``tests/test_browser_e2e.py`` is **module-scoped**, so its setup — which starts a real uvicorn
subprocess — runs *before* any test body reaches ``chromium_page()``'s skip. A server that will not
start therefore raised ``pytest.fail`` during fixture **setup**, and pytest reports a setup failure
as an **ERROR**, not a failure. D-10's whole premise is that an ERROR reddens the required
``Linux Full Suite`` check regardless of any ``CI-EXEMPT:`` disposition, while a SKIP does not — so
that one path defeated the skip-never-error contract for the entire module.

Two properties are asserted here, and they pull in opposite directions on purpose:

1. Chromium absent  -> every node **skips**, even when the server is broken. (The W-10 regression.)
2. Chromium present -> a broken server still **errors or fails, loudly**. (Guards the fix against
   degenerating into "always skip", which would turn a genuinely broken server in the Browser E2E
   job into green-with-no-coverage.)

Both levers are real environment states, never production test-hooks:

* ``PLAYWRIGHT_BROWSERS_PATH`` pointed at an empty directory reproduces "the Chromium binary is not
  installed" exactly as ``Linux Full Suite`` sees it — verified: ``chromium.executable_path``
  resolves *into* that directory and ``os.path.exists`` is then False.
* A ``uvicorn.py`` shadow at the front of ``PYTHONPATH`` reproduces "the server will not start".
  ``serve_dashboard`` builds its child env with ``dict(os.environ)``, so the shadow propagates to
  the ``python -m uvicorn`` child, which exits non-zero before it can ever listen.

The run happens in a **subprocess** because the thing under test is how pytest *reports* an
outcome. Asserting on an exception type inside this process would test a different thing than the
one that reddens CI. Outcomes are read from a JUnit XML report rather than scraped from the summary
line, so the assertion cannot be fooled by wording changes in pytest's output.
"""

from __future__ import annotations

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TIER2_MODULE = "tests/test_browser_e2e.py"

# Generous: the module runs three real browser tests in the Chromium-present leg.
_SUBPROCESS_TIMEOUT_S = 900


def _chromium_is_installed() -> bool:
    """Deliberately NOT imported from the harness under test.

    This is the gate that decides which leg runs, so deriving it from the same helper the fix
    introduces would let one bug silently satisfy both sides.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            return os.path.exists(p.chromium.executable_path)
    except Exception:
        return False


def _run_tier2_module(tmp_path: Path, *, chromium: bool, uvicorn_ok: bool) -> list[tuple[str, str]]:
    """Run the Tier-2 module in a subprocess; return ``[(nodeid, outcome), ...]``.

    ``outcome`` is one of ``error``, ``failure``, ``skipped``, ``passed``.
    """
    env = dict(os.environ)

    if not chromium:
        empty_cache = tmp_path / "no-browsers"
        empty_cache.mkdir(exist_ok=True)
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(empty_cache)

    if not uvicorn_ok:
        shadow = tmp_path / "shadow"
        shadow.mkdir(exist_ok=True)
        (shadow / "uvicorn.py").write_text(
            'raise ImportError("D-10 contract test: uvicorn is deliberately unimportable")\n',
            encoding="utf-8",
        )
        env["PYTHONPATH"] = os.pathsep.join(
            part for part in (str(shadow), env.get("PYTHONPATH", "")) if part
        )

    report = tmp_path / "report.xml"
    proc = subprocess.run(
        [
            sys.executable, "-m", "pytest", _TIER2_MODULE,
            "-p", "no:cacheprovider", "-q", f"--junit-xml={report}",
        ],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        timeout=_SUBPROCESS_TIMEOUT_S,
    )

    assert report.exists(), (
        "the inner pytest run produced no JUnit report — it likely failed before collection.\n"
        f"exit={proc.returncode}\nstdout:\n{proc.stdout.decode('utf-8', 'replace')[-4000:]}"
    )

    outcomes: list[tuple[str, str]] = []
    for case in ET.parse(report).getroot().iter("testcase"):
        nodeid = f"{case.get('classname', '')}::{case.get('name', '')}"
        if case.find("error") is not None:
            outcomes.append((nodeid, "error"))
        elif case.find("failure") is not None:
            outcomes.append((nodeid, "failure"))
        elif case.find("skipped") is not None:
            outcomes.append((nodeid, "skipped"))
        else:
            outcomes.append((nodeid, "passed"))
    return outcomes


@pytest.mark.slow
def test_tier2_nodes_skip_never_error_when_chromium_is_absent(tmp_path):
    """W-10 — with no Chromium, a server that will not start must still produce SKIP, not ERROR.

    The broken server is the hostile half: without it this test passes trivially, because the
    server starts fine and every node skips in its body anyway. The production change that makes
    this fail is removing the Chromium precheck from ``dashboard_origin`` — the server is then
    started during module-scoped fixture setup and its failure is reported as an ERROR.
    """
    outcomes = _run_tier2_module(tmp_path, chromium=False, uvicorn_ok=False)

    assert outcomes, f"{_TIER2_MODULE} collected no tests"
    offenders = [(node, outcome) for node, outcome in outcomes if outcome != "skipped"]
    assert not offenders, (
        "D-10 requires every Tier-2 node to SKIP where Chromium is absent — an ERROR there reddens "
        "the required Linux Full Suite check regardless of any CI-EXEMPT disposition. "
        f"Non-skipped outcomes: {offenders}"
    )


@pytest.mark.slow
@pytest.mark.skipif(
    not _chromium_is_installed(),
    reason="Chromium is not installed — this leg asserts the behaviour where it IS present, "
    "which is the Browser E2E job (D-01/D-02), not Linux Full Suite.",
)
def test_tier2_still_reports_loudly_when_server_dies_and_chromium_is_present(tmp_path):
    """The other half of W-10's fix: a dead server is NOT environment-optional where Chromium is.

    Without this, the cheap way to satisfy the test above is to make the module skip
    unconditionally — which would turn a genuinely broken server in the Browser E2E job into
    green-with-no-coverage, the exact "a skip is not a pass" failure D-10 exists to prevent.
    """
    outcomes = _run_tier2_module(tmp_path, chromium=True, uvicorn_ok=False)

    assert outcomes, f"{_TIER2_MODULE} collected no tests"
    silent = [(node, outcome) for node, outcome in outcomes if outcome in ("skipped", "passed")]
    assert not silent, (
        "a server that will not start must be reported loudly when Chromium IS installed; "
        f"these nodes stayed silent instead: {silent}"
    )
