"""Phase 231 QRAMM-20 (D-11 / D-12 / D-12a): `doctor`, `qramm` and `cve` help.

Todo: ``261012-doc224-doctor-qramm-cve-do-not-implement-help``.

Before Phase 231, ``quirk doctor --help`` ran the full health check (DNS
lookup, 127.0.0.1:8512 probe, DB open), and ``quirk qramm --help`` /
``quirk cve --help`` fell through into the scan parser and printed
``usage: run_scan.py``. ``quirk cve status --format=json`` printed text (the
hand parser matched only a bare ``--format`` token) and
``--format xml`` exited 0.

This module pins:

* D-11: ``--help`` at both levels prints ``usage: quirk <cmd>``, exits 0 and
  runs nothing (in-process sentinels prove the handlers are never called).
* D-12: an unknown action or argument is an argparse usage error (exit 2,
  ``usage: quirk <cmd>`` on stderr), never the scan parser's usage.
* D-12a: ``--format=json`` and ``--format json`` both emit JSON.

Assertion rule (D-16, RESEARCH Pitfall 5): CI runs Python 3.11, the local
venv may be 3.14. argparse wording, quoting and colour differ between those
versions, so tests assert only the exit code, the ``usage: quirk <cmd>``
prefix and the substring ``invalid choice`` -- never a full argparse line.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

import pytest

from tests.cli_helpers import run_cli

SCAN_USAGE = "usage: run_scan.py"

HELP_FORMS = [
    (["doctor", "--help"], "usage: quirk doctor"),
    (["qramm", "--help"], "usage: quirk qramm"),
    (["qramm", "status", "--help"], "usage: quirk qramm status"),
    (["cve", "--help"], "usage: quirk cve"),
    (["cve", "status", "--help"], "usage: quirk cve status"),
]

USAGE_ERRORS = [
    (["qramm", "foo"], "usage: quirk qramm", True),
    (["cve", "foo"], "usage: quirk cve", True),
    (["qramm"], "usage: quirk qramm", False),
    (["cve"], "usage: quirk cve", False),
    (["doctor", "extra"], "usage: quirk doctor", False),
    (["cve", "status", "--format", "xml"], "usage: quirk cve status", True),
    (["qramm", "status", "extra"], "usage: quirk qramm", False),
]


def _fresh_env(tmp_path) -> dict[str, str]:
    """Environment pinning the CVE catalog verdict to FRESH (exit 0).

    ``QUIRK_DB_PATH`` points at a nonexistent file under ``tmp_path`` so that,
    should a regression make a command run, it can never open the canonical
    ``quirk-output/quirk.db``.
    """
    from quirk.scanner.hw_cve import CVE_TABLE_META

    env = dict(os.environ)
    env["QUIRK_DB_PATH"] = str(tmp_path / "absent.db")
    env["QUIRK_CI_STALENESS_OVERRIDE_DATE"] = datetime.date.fromisoformat(
        CVE_TABLE_META["last_verified"]
    ).isoformat()
    return env


def _install_sentinels(monkeypatch, calls: list) -> None:
    """Replace every handler with a sentinel that fails if it is reached."""

    def _boom(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("ran")

    monkeypatch.setattr("quirk.cli.doctor_cmd.run_doctor", _boom)
    monkeypatch.setattr("quirk.cli.qramm_cmd.run_qramm_status", _boom)
    monkeypatch.setattr("quirk.cli.cve_cmd.run_cve_status", _boom)


@pytest.mark.parametrize(
    "args,usage", HELP_FORMS, ids=[" ".join(a) for a, _ in HELP_FORMS]
)
def test_help_prints_own_usage_and_exits_zero(args, usage, tmp_path):
    result = run_cli(args, timeout=30, env=_fresh_env(tmp_path))
    assert result.returncode == 0, (
        f"exit={result.returncode} stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert usage in result.stdout, result.stdout
    assert SCAN_USAGE not in result.stdout
    assert SCAN_USAGE not in result.stderr


@pytest.mark.parametrize(
    "args,usage", HELP_FORMS, ids=[" ".join(a) for a, _ in HELP_FORMS]
)
def test_help_runs_nothing_in_process(args, usage, monkeypatch, capsys):
    import run_scan

    calls: list = []
    _install_sentinels(monkeypatch, calls)
    monkeypatch.setattr(sys, "argv", ["run_scan.py", *args])
    with pytest.raises(SystemExit) as exc:
        run_scan.main()
    out = capsys.readouterr().out
    assert calls == [], f"handler ran for {args}: {calls}"
    assert exc.value.code == 0, f"exit={exc.value.code!r}"
    assert usage in out, out


def test_cve_status_help_lists_format(tmp_path):
    result = run_cli(
        ["cve", "status", "--help"], timeout=30, env=_fresh_env(tmp_path)
    )
    assert result.returncode == 0, result.stderr
    assert "--format" in result.stdout
    assert "text" in result.stdout
    assert "json" in result.stdout


@pytest.mark.parametrize(
    "args,usage,invalid_choice",
    USAGE_ERRORS,
    ids=[" ".join(a) or "bare" for a, _, _ in USAGE_ERRORS],
)
def test_unknown_action_or_argument_is_usage_error(
    args, usage, invalid_choice, tmp_path
):
    result = run_cli(args, timeout=30, env=_fresh_env(tmp_path))
    assert result.returncode == 2, (
        f"exit={result.returncode} stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert usage in result.stderr, result.stderr
    assert SCAN_USAGE not in result.stdout
    assert SCAN_USAGE not in result.stderr
    if invalid_choice:
        assert "invalid choice" in result.stderr, result.stderr


def test_cve_status_format_equals_json_emits_json(tmp_path):
    result = run_cli(
        ["cve", "status", "--format=json"], timeout=30, env=_fresh_env(tmp_path)
    )
    assert result.returncode == 0, (
        f"exit={result.returncode} stderr={result.stderr!r}"
    )
    payload = json.loads(result.stdout)
    assert "last_verified" in payload


def test_cve_status_format_space_json_emits_json(tmp_path):
    result = run_cli(
        ["cve", "status", "--format", "json"], timeout=30, env=_fresh_env(tmp_path)
    )
    assert result.returncode == 0, (
        f"exit={result.returncode} stderr={result.stderr!r}"
    )
    payload = json.loads(result.stdout)
    assert "last_verified" in payload


def test_cve_status_passes_format_to_handler(monkeypatch):
    import run_scan

    seen: list = []

    def _fake(*args, **kwargs):
        seen.append((args, kwargs))

    monkeypatch.setattr("quirk.cli.cve_cmd.run_cve_status", _fake)
    monkeypatch.setattr(
        sys, "argv", ["run_scan.py", "cve", "status", "--format=json"]
    )
    run_scan.main()
    assert len(seen) == 1, seen
    args, kwargs = seen[0]
    assert kwargs.get("fmt", args[0] if args else None) == "json", seen
