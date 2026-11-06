"""Phase 235.1 D-04 (INSTALL-06): a bare clone imports without tomllib.

A bare 3.10 clone has no installed distribution (PackageNotFoundError) and no
``tomllib`` (3.11+) or ``tomli``. ``import quirk`` must still yield the
pyproject version, not raise ModuleNotFoundError.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from tests.cli_helpers import run_fork_safe
from tests.pyproject_helpers import pyproject_version

REPO = Path(__file__).resolve().parent.parent

_SNIPPET = """
import importlib.metadata as m
def _raise(*a, **k):
    raise m.PackageNotFoundError("quirk-scanner")
m.version = _raise
import sys
sys.modules["tomllib"] = None
sys.modules["tomli"] = None
import quirk
print(quirk.__version__)
"""


def test_bare_clone_import_without_tomllib_yields_pyproject_version():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    proc = run_fork_safe([sys.executable, "-c", _SNIPPET], env=env)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == pyproject_version()
