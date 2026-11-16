"""Phase 236 D-10 / D-11 (T-236-DoS): the derivation module and the notify path must
import on a minimal install (no ``[dashboard]`` extra).

``quirk.notify.dispatcher`` imports ``finding_derivation`` at module level, and its
callers (``scheduler_cmd``, ``hardware_drift``) swallow exceptions, so an ImportError
would silently disable notifications.  Each test runs a FRESH subprocess whose first
action is a ``MetaPathFinder`` that makes fastapi/starlette/uvicorn unimportable, so a
venv that happens to have fastapi installed cannot mask a leak.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.cli_helpers import run_fork_safe

_REPO = Path(__file__).resolve().parents[1]
_SENTINEL = "MINIMAL_IMPORT_OK"

_BLOCKER = """
import importlib.abc, sys

_BLOCKED = ("fastapi", "starlette", "uvicorn")


class _Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in _BLOCKED:
            raise ImportError("blocked for minimal-install proof: " + name)
        return None


sys.meta_path.insert(0, _Block())
"""

_TAIL = """
leaked = sorted(m for m in sys.modules if m.split(".")[0] in _BLOCKED)
assert not leaked, "blocked modules present in sys.modules: " + repr(leaked)
print("@@SENTINEL@@")
""".replace("@@SENTINEL@@", _SENTINEL)


def _run(body: str) -> subprocess.CompletedProcess:
    # No cwd= (it defeats posix_spawn on macOS, tests/cli_helpers.py): the repo
    # root is put on PYTHONPATH instead so ``quirk`` resolves the same way.
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_REPO)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    return run_fork_safe(
        [sys.executable, "-c", _BLOCKER + body + _TAIL], timeout=60, env=env
    )


def _assert_ok(proc: subprocess.CompletedProcess) -> None:
    assert proc.returncode == 0, f"stdout={proc.stdout!r}\nstderr={proc.stderr[-2000:]!r}"
    assert _SENTINEL in proc.stdout


def test_blocker_actually_blocks_fastapi():
    """Self-check: the blocker makes ``import fastapi`` fail (it is not vacuous)."""
    proc = _run("try:\n    import fastapi\nexcept ImportError:\n    pass\nelse:\n    raise SystemExit('fastapi imported')\n")
    _assert_ok(proc)


def test_notify_chain_and_derivation_import_without_fastapi():
    _assert_ok(_run(
        "import quirk.notify.dispatcher\n"
        "import quirk.scanner.hardware_drift\n"
        "import quirk.cli.scheduler_cmd\n"
        "from quirk.dashboard.api.finding_derivation import derive_dashboard_scoring_findings\n"
        "derive_dashboard_scoring_findings([])\n"
    ))


@pytest.mark.parametrize(
    "module",
    ["quirk.scanner.hardware_drift", "quirk.cli.scheduler_cmd", "quirk.notify.dispatcher"],
)
def test_single_import_without_fastapi(module):
    """Single imports: a first import can mask a cycle in the combined test."""
    _assert_ok(_run(f"import {module}\n"))


def test_finding_derivation_single_import_without_fastapi():
    _assert_ok(_run(
        "from quirk.dashboard.api.finding_derivation import derive_dashboard_scoring_findings\n"
        "assert derive_dashboard_scoring_findings([]) == []\n"
    ))


def test_dispatch_path_resolves_dashboard_deriver_without_fastapi():
    """The dispatcher imports the deriver at call time (pydantic import hygiene), so
    module import alone proves nothing: drive dispatch_notifications itself."""
    _assert_ok(_run(
        "from datetime import datetime\n"
        "import quirk.notify.dispatcher as d\n"
        "from quirk.notify.config import NotifyCfg\n"
        "seen = {}\n"
        "class _Stop(Exception):\n"
        "    pass\n"
        "def _fake(cur, prev, db, **kw):\n"
        "    seen.update(kw)\n"
        "    raise _Stop()\n"
        "d.load_notifications_config = lambda: NotifyCfg(trigger_score_floor=-1000)\n"
        "d._find_two_sessions = lambda db: (datetime(2026, 1, 2), None)\n"
        "d.compute_trend_report = _fake\n"
        "try:\n"
        "    d.dispatch_notifications(run=None, schedule=None, db=None)\n"
        "except _Stop:\n"
        "    pass\n"
        "assert seen['findings_deriver'].__name__ == 'derive_dashboard_scoring_findings'\n"
        "assert seen['findings_deriver']([]) == []\n"
    ))
