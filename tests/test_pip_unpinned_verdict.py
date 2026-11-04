"""Fixture-driven tests for scripts/pip_unpinned_verdict.py (235.1-05, D-02).

Fixtures were captured live on 2026-11-03/04 with /opt/homebrew/bin/python3.15
(3.15.2), pip 26.2.2, in a throwaway venv, local paths scrubbed to ``<venv>``:

  pip install --dry-run --quiet --report r.json quirk-scanner
      -> rc 0, selects 5.21.0            (pip_3_15_unpinned_report.json)
  pip install --dry-run --quiet --report r2.json "quirk-scanner>5.21.0"
      -> rc 1, ResolutionImpossible      (pip_3_15_resolution_impossible.txt)
  pip install --dry-run --quiet --report r3.json \
      --index-url http://127.0.0.1:9/simple --retries 0 --timeout 2 quirk-scanner
      -> rc 1, "(from versions: none)"   (pip_3_15_network_error.txt)

The verdict is tested against these shapes, never against live PyPI.  The
NETWORK_RE strings in test_network_text_variants are synthetic (pip prints
them only in non-quiet mode).
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tests.cli_helpers import run_fork_safe

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pip_unpinned_verdict.py"
FX = ROOT / "tests" / "fixtures"

_spec = importlib.util.spec_from_file_location("pip_unpinned_verdict", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)
verdict = mod.verdict


def _report():
    return json.loads((FX / "pip_3_15_unpinned_report.json").read_text(encoding="utf-8"))


def _with_version(version, name="quirk-scanner"):
    rep = _report()
    for item in rep["install"]:
        if item["metadata"]["name"] == "quirk-scanner":
            item["metadata"]["version"] = version
            item["metadata"]["name"] = name
    return rep


def test_older_release_selected_fails():
    state, msg = verdict(_report(), "", 0, "5.28.1")
    assert state == "FAIL" and "5.21.0" in msg


def test_resolution_impossible_passes():
    text = (FX / "pip_3_15_resolution_impossible.txt").read_text(encoding="utf-8")
    assert verdict(None, text, 1, "5.28.1")[0] == "PASS"


def test_network_error_fixture_fails():
    text = (FX / "pip_3_15_network_error.txt").read_text(encoding="utf-8")
    assert verdict(None, text, 1, "5.28.1")[0] == "FAIL"


@pytest.mark.parametrize("text", [
    "Could not fetch URL https://pypi.org/simple/x/",
    "NewConnectionError('<urllib3...>')",
    "Max retries exceeded with url",
    "Temporary failure in name resolution",
    "Network is unreachable",
])
def test_network_text_variants_fail_even_with_resolution_impossible(text):
    out = text + "\nERROR: ResolutionImpossible\n"
    assert verdict(None, out, 1, "5.28.1")[0] == "FAIL"


def test_from_versions_none_fails():
    out = "ERROR: Could not find a version (from versions: none)\n"
    assert verdict(None, out, 1, "5.28.1")[0] == "FAIL"


def test_report_without_quirk_scanner_fails():
    state, msg = verdict({"version": "1", "install": []}, "", 0, "5.28.1")
    assert state == "FAIL" and "no quirk-scanner" in msg


@pytest.mark.parametrize("bad", [None, [], "x", {"install": "nope"}, {"install": [None, 3]}])
def test_malformed_report_fails(bad):
    assert verdict(bad, "", 0, "5.28.1")[0] == "FAIL"


@pytest.mark.parametrize("picked", ["5.28.1", "5.29.0", "5.28.10", "6.0"])
def test_equal_or_newer_passes(picked):
    assert verdict(_with_version(picked), "", 0, "5.28.1")[0] == "PASS"


def test_numeric_not_lexical_compare():
    # lexically "5.9.0" > "5.28.1"; numerically it is older
    assert verdict(_with_version("5.9.0"), "", 0, "5.28.1")[0] == "FAIL"


def test_rc2_without_resolution_impossible_fails():
    assert verdict(None, "boom", 2, "5.28.1")[0] == "FAIL"


@pytest.mark.parametrize("name", ["quirk_scanner", "Quirk-Scanner", "quirk.scanner"])
def test_name_normalisation(name):
    assert verdict(_with_version("5.21.0", name), "", 0, "5.28.1")[0] == "FAIL"
    assert verdict(_with_version("5.28.1", name), "", 0, "5.28.1")[0] == "PASS"


def test_empty_expected_fails():
    assert verdict(_with_version("5.28.1"), "", 0, "")[0] == "FAIL"


def _cli(*args):
    return run_fork_safe([sys.executable, str(SCRIPT), *args], timeout=30)


def test_cli_fail_on_older():
    r = _cli("--report", str(FX / "pip_3_15_unpinned_report.json"),
             "--output", "/dev/null", "--rc", "0", "--expected", "5.28.1")
    assert r.returncode == 1
    assert r.stdout.splitlines()[0].startswith("FAIL:") and "5.21.0" in r.stdout


def test_cli_pass_on_resolution_impossible_and_missing_report(tmp_path):
    r = _cli("--report", str(tmp_path / "absent.json"),
             "--output", str(FX / "pip_3_15_resolution_impossible.txt"),
             "--rc", "1", "--expected", "5.28.1")
    assert r.returncode == 0
    assert r.stdout.splitlines()[0].startswith("PASS:")


def test_cli_missing_report_with_rc0_fails(tmp_path):
    r = _cli("--report", str(tmp_path / "absent.json"), "--output", "/dev/null",
             "--rc", "0", "--expected", "5.28.1")
    assert r.returncode == 1
