"""Tests for source code scanner (SCAN-05).

Tests mock subprocess.run to avoid requiring semgrep binary.
Scanner module: quirk/scanner/source_scanner.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from quirk.scanner.source_scanner import (
    SourceRulesetUnavailable,
    SourceScanError,
    scan_source_repo,
    scan_source_targets,
)

EXIT7_FIXTURE = Path(__file__).parent / "fixtures" / "semgrep_exit7_p_cryptography.json"


@pytest.fixture
def fake_semgrep(tmp_path, monkeypatch):
    """Install an executable fake ``semgrep`` first on PATH.

    The real ``subprocess.run`` runs against it (no mock), so the genuine
    exit-7 / valid-JSON behaviour of a 404'd ruleset is exercised.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    bindir = tmp_path / "bin"
    bindir.mkdir()

    # macOS: a default close_fds=True spawn after Network.framework is loaded by
    # an earlier test in the same pytest process dies with SIGSEGV, so the fake
    # semgrep printed nothing and these tests failed only in the full suite.
    # Keep the REAL subprocess.run, just spawned fork-safely (close_fds=False).
    real_run = subprocess.run

    def _fork_safe_run(*args, **kwargs):
        kwargs.setdefault("close_fds", False)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _fork_safe_run)

    def _install(stdout: str, code: int) -> str:
        exe = bindir / "semgrep"
        exe.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            f"sys.stdout.write({stdout!r})\n"
            f"sys.exit({code})\n"
        )
        os.chmod(exe, 0o755)
        monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
        return str(repo)

    return _install

SAMPLE_SEMGREP_OUTPUT = {
    "results": [
        {
            "check_id": "python.cryptography.security.insecure-hash-algorithms.insecure-hash-algorithms-md5",
            "path": "app/auth.py",
            "start": {"line": 42, "col": 4},
            "end": {"line": 42, "col": 30},
            "extra": {
                "message": "Use of weak MD5 hash algorithm",
                "severity": "WARNING",
                "metadata": {"confidence": "HIGH"}
            }
        },
        {
            "check_id": "python.cryptography.security.insecure-cipher-algorithm.insecure-cipher-algorithm-des",
            "path": "app/encrypt.py",
            "start": {"line": 10, "col": 1},
            "end": {"line": 10, "col": 45},
            "extra": {
                "message": "Use of insecure DES cipher",
                "severity": "WARNING",
                "metadata": {"confidence": "HIGH"}
            }
        }
    ],
    "errors": [],
    "stats": {"total_time": 1.23}
}


def test_semgrep_not_found():
    """If semgrep binary is absent, must return empty list (per D-14)."""
    with patch("shutil.which", return_value=None), \
         patch("os.path.isdir", return_value=True):
        endpoints = scan_source_repo("/path/to/repo", timeout=120)
        assert endpoints == []


def test_semgrep_findings_parsed():
    """Each semgrep finding must produce one CryptoEndpoint with protocol='SOURCE' (per D-13)."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(SAMPLE_SEMGREP_OUTPUT)
    mock_proc.returncode = 0

    with patch("shutil.which", return_value="/usr/bin/semgrep"), \
         patch("subprocess.run", return_value=mock_proc), \
         patch("os.path.isdir", return_value=True):
        endpoints = scan_source_repo("/path/to/repo", timeout=120)
        assert len(endpoints) == 2
        for ep in endpoints:
            assert ep.protocol == "SOURCE"
            assert ep.host == "/path/to/repo"
            assert ep.port == 0
            assert ep.source_scan_json is not None


def test_semgrep_service_detail_format():
    """service_detail must be 'file:line' format (per D-13)."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(SAMPLE_SEMGREP_OUTPUT)
    mock_proc.returncode = 0

    with patch("shutil.which", return_value="/usr/bin/semgrep"), \
         patch("subprocess.run", return_value=mock_proc), \
         patch("os.path.isdir", return_value=True):
        endpoints = scan_source_repo("/path/to/repo", timeout=120)
        assert endpoints[0].service_detail == "app/auth.py:42"
        assert endpoints[1].service_detail == "app/encrypt.py:10"


def test_semgrep_cipher_suite_is_rule_id():
    """cipher_suite must hold the semgrep rule_id (per D-13)."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(SAMPLE_SEMGREP_OUTPUT)
    mock_proc.returncode = 0

    with patch("shutil.which", return_value="/usr/bin/semgrep"), \
         patch("subprocess.run", return_value=mock_proc), \
         patch("os.path.isdir", return_value=True):
        endpoints = scan_source_repo("/path/to/repo", timeout=120)
        assert "insecure-hash-algorithms-md5" in endpoints[0].cipher_suite


def test_semgrep_json_parse_error(fake_semgrep):
    """Invalid semgrep output must raise, never read as a clean repo."""
    repo = fake_semgrep("invalid json", 1)
    with pytest.raises(SourceScanError) as ei:
        scan_source_repo(repo, timeout=120)
    assert str(ei.value).startswith("source scan failed")
    assert not isinstance(ei.value, SourceRulesetUnavailable)


def test_semgrep_exit7_ruleset_404_raises_ruleset_unavailable(fake_semgrep):
    repo = fake_semgrep(EXIT7_FIXTURE.read_text(), 7)
    with pytest.raises(SourceRulesetUnavailable) as ei:
        scan_source_repo(repo, timeout=120)
    msg = str(ei.value)
    assert msg.startswith("ruleset unavailable")
    assert repo not in msg


def test_scan_source_targets_reraises_ruleset_unavailable(fake_semgrep):
    repo = fake_semgrep(EXIT7_FIXTURE.read_text(), 7)
    with pytest.raises(SourceRulesetUnavailable):
        scan_source_targets([repo])


def test_wrapped_phase_records_source_ruleset_failure(fake_semgrep):
    import run_scan

    repo = fake_semgrep(EXIT7_FIXTURE.read_text(), 7)
    recorder = run_scan._PhaseRecorder()
    run_stats = {"timings_sec": {}, "phase_records": recorder}
    error_endpoints: list = []
    result = run_scan._wrapped_phase(
        run_stats,
        "source_scanning",
        "source_scanner",
        lambda: scan_source_targets([repo]),
        error_endpoints,
        MagicMock(),
    )
    assert result is None or result == []
    rows = [r for r in recorder.rows() if r["phase_name"] == "source_scanning"]
    assert len(rows) == 1
    assert rows[0]["reason"] == "failed"
    # _wrapped_phase persists safe_str(exc), which prefixes the class name.
    assert "ruleset unavailable" in rows[0]["detail"]
    assert rows[0]["detail"].startswith("SourceRulesetUnavailable")
    assert len(error_endpoints) == 1
    assert error_endpoints[0].protocol == "ERROR"
    # 235.1-01 (SRCSCAN-03 WR-02): scan_error is now built with safe_str(exc),
    # so it carries the same class-name prefix as the persisted detail.
    assert error_endpoints[0].scan_error.startswith("SourceRulesetUnavailable")
    assert "ruleset unavailable" in error_endpoints[0].scan_error


def test_semgrep_warn_level_errors_do_not_fail(fake_semgrep):
    body = dict(SAMPLE_SEMGREP_OUTPUT)
    body["errors"] = [
        {"code": 3, "level": "warn", "type": "PartialParsing", "message": "x"}
    ]
    repo = fake_semgrep(json.dumps(body), 0)
    endpoints = scan_source_repo(repo, timeout=120)
    assert len(endpoints) == 2


def test_semgrep_not_installed_still_returns_empty(tmp_path):
    (tmp_path / "repo").mkdir()
    with patch("shutil.which", return_value=None):
        assert scan_source_repo(str(tmp_path / "repo")) == []


# --------------------------------------------------------------------------
# 235.1-03 (SRCSCAN-03, D-09): per-target isolation, redaction, classification
# --------------------------------------------------------------------------

@pytest.fixture
def fake_semgrep_repos(tmp_path, monkeypatch):
    """Fake ``semgrep`` that behaves differently per repo directory name.

    ``_install({"a": (stdout, rc), "b": ("TIMEOUT", 0)})`` returns the repo
    paths in dict order. A body of "TIMEOUT" sleeps past the caller's timeout.
    """
    bindir = tmp_path / "bin"
    bindir.mkdir()
    real_run = subprocess.run

    def _fork_safe_run(*args, **kwargs):
        kwargs.setdefault("close_fds", False)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _fork_safe_run)

    def _install(spec: dict) -> list:
        repos = []
        table = {}
        for name, (stdout, code) in spec.items():
            repo = tmp_path / name
            repo.mkdir()
            repos.append(str(repo))
            table[name] = [stdout, code]
        exe = bindir / "semgrep"
        exe.write_text(
            f"#!{sys.executable}\n"
            "import os, sys, time\n"
            f"TABLE = {table!r}\n"
            "name = os.path.basename(sys.argv[-1])\n"
            "out, code = TABLE[name]\n"
            "if out == 'TIMEOUT':\n"
            "    time.sleep(30)\n"
            "sys.stdout.write(out)\n"
            "sys.exit(code)\n"
        )
        os.chmod(exe, 0o755)
        monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
        return repos

    return _install


def _err_entry(code, message, level="error"):
    return {"code": code, "level": level, "type": "SemgrepError", "message": message}


def test_targets_one_timeout_keeps_other_results(fake_semgrep_repos):
    a, b = fake_semgrep_repos({
        "a": (json.dumps(SAMPLE_SEMGREP_OUTPUT), 0),
        "b": ("TIMEOUT", 0),
    })
    eps = scan_source_targets([a, b], timeout=1)
    findings = [e for e in eps if not e.scan_error]
    errors = [e for e in eps if e.scan_error]
    assert len(findings) == 2
    assert len(errors) == 1
    assert errors[0].protocol == "SOURCE"
    assert errors[0].scan_error_category == "timeout"
    assert a not in errors[0].scan_error and b not in errors[0].scan_error


def test_single_repo_rc1_results_plus_error_entry(fake_semgrep_repos):
    body = dict(SAMPLE_SEMGREP_OUTPUT)
    body["results"] = body["results"][:1]
    body["errors"] = [_err_entry(2, "boom while parsing")]
    (repo,) = fake_semgrep_repos({"a": (json.dumps(body), 1)})
    eps = scan_source_targets([repo])
    assert len([e for e in eps if not e.scan_error]) == 1
    errs = [e for e in eps if e.scan_error]
    assert len(errs) == 1 and errs[0].protocol == "SOURCE"


def test_targets_all_ruleset_unavailable_raises(fake_semgrep_repos):
    repos = fake_semgrep_repos({
        "a": (EXIT7_FIXTURE.read_text(), 7),
        "b": (EXIT7_FIXTURE.read_text(), 7),
    })
    with pytest.raises(SourceRulesetUnavailable):
        scan_source_targets(repos)


def test_targets_one_ruleset_unavailable_one_ok_does_not_raise(fake_semgrep_repos):
    a, b = fake_semgrep_repos({
        "a": (EXIT7_FIXTURE.read_text(), 7),
        "b": (json.dumps(SAMPLE_SEMGREP_OUTPUT), 0),
    })
    eps = scan_source_targets([a, b])
    assert len([e for e in eps if not e.scan_error]) == 2
    errs = [e for e in eps if e.scan_error]
    assert len(errs) == 1
    assert "ruleset unavailable" in errs[0].scan_error


def test_targets_all_fail_non_ruleset_raises_scan_error(fake_semgrep_repos):
    repos = fake_semgrep_repos({"a": ("invalid json", 1), "b": ("invalid json", 1)})
    with pytest.raises(SourceScanError) as ei:
        scan_source_targets(repos)
    assert not isinstance(ei.value, SourceRulesetUnavailable)


def test_scan_error_text_never_contains_repo_path(fake_semgrep_repos, tmp_path):
    import re as _re

    (repo,) = fake_semgrep_repos({"a": ("x", 0)})
    msg = f"cannot read {repo}/src/x.py and C:\\Users\\bob\\x.py and /etc/passwd"
    body = {"results": [], "errors": [_err_entry(2, msg)]}
    (repo,) = [repo]
    # Re-install with the path-bearing message (the repo dir already exists).
    exe = tmp_path / "bin" / "semgrep"
    exe.write_text(
        f"#!{sys.executable}\nimport sys\nsys.stdout.write({json.dumps(body)!r})\nsys.exit(1)\n"
    )
    eps = scan_source_targets([repo])
    (row,) = [e for e in eps if e.scan_error]
    assert repo not in row.scan_error
    assert str(tmp_path) not in row.scan_error
    assert not _re.search(r"(^|\s)/\w", row.scan_error)
    assert not _re.search(r"[A-Za-z]:\\", row.scan_error)
    assert str(tmp_path) not in row.host
    # Also on the raising path.
    exe.write_text(
        f"#!{sys.executable}\nimport sys\nsys.stdout.write({json.dumps(body)!r})\nsys.exit(2)\n"
    )
    with pytest.raises(SourceScanError) as ei:
        scan_source_repo(repo)
    assert str(tmp_path) not in str(ei.value)
    assert not _re.search(r"[A-Za-z]:\\", str(ei.value))


def test_configuration_in_filename_is_not_ruleset_unavailable(fake_semgrep):
    body = {"results": [], "errors": [_err_entry(2, "failed to read /x/configuration.yaml")]}
    repo = fake_semgrep(json.dumps(body), 2)
    with pytest.raises(SourceScanError) as ei:
        scan_source_repo(repo)
    assert not isinstance(ei.value, SourceRulesetUnavailable)


def test_error_code_7_at_rc0_is_ruleset_unavailable(fake_semgrep):
    body = {"results": [], "errors": [_err_entry(7, "invalid configuration file")]}
    repo = fake_semgrep(json.dumps(body), 0)
    with pytest.raises(SourceRulesetUnavailable):
        scan_source_repo(repo)


@pytest.mark.parametrize("results", [None, "oops", [1, "x"]])
def test_null_or_garbage_results_is_error_not_clean(fake_semgrep_repos, results):
    bad, good = fake_semgrep_repos({
        "a": (json.dumps({"results": results, "errors": []}), 0),
        "b": (json.dumps(SAMPLE_SEMGREP_OUTPUT), 0),
    })
    with pytest.raises(SourceScanError):
        scan_source_repo(bad)
    # Next to a good target it is a visible row, never a silent clean.
    eps = scan_source_targets([bad, good])
    assert len([e for e in eps if e.scan_error]) == 1
    assert len([e for e in eps if not e.scan_error]) == 2


# --------------------------------------------------------------------------
# 235.1 review WR-02: invalid_input rows are not evidence
# --------------------------------------------------------------------------

def test_wr02_invalid_plus_ruleset_unavailable_raises_not_ran(fake_semgrep_repos):
    """A rejected target plus a ruleset-404 target produced zero evidence; the
    phase must fail (recorded failed), not return rows and read as ``ran``."""
    import run_scan

    (repo,) = fake_semgrep_repos({"a": (EXIT7_FIXTURE.read_text(), 7)})
    with pytest.raises(SourceScanError) as ei:
        scan_source_targets(["-bad", repo])
    assert str(ei.value).startswith("source scan failed for all targets")
    recorder = run_scan._PhaseRecorder()
    run_stats = {"timings_sec": {}, "phase_records": recorder}
    run_scan._wrapped_phase(
        run_stats, "source_scanning", "source_scanner",
        lambda: scan_source_targets(["-bad", repo]), [], MagicMock(),
    )
    (row,) = [r for r in recorder.rows() if r["phase_name"] == "source_scanning"]
    assert row["reason"] == "failed"


def test_wr02_only_invalid_targets_raises(fake_semgrep_repos):
    fake_semgrep_repos({"a": ("{}", 0)})
    with pytest.raises(SourceScanError):
        scan_source_targets(["-bad"])


def test_wr02_invalid_plus_ok_target_still_returns_rows(fake_semgrep_repos):
    (good,) = fake_semgrep_repos({"b": (json.dumps(SAMPLE_SEMGREP_OUTPUT), 0)})
    eps = scan_source_targets(["-bad", good])
    assert len([e for e in eps if not e.scan_error]) == 2
    assert [e.scan_error_category for e in eps if e.scan_error] == ["invalid_input"]


# --------------------------------------------------------------------------
# 235.1 review WR-03 / WR-04 / IN-07: _redact path coverage and safety
# --------------------------------------------------------------------------

def test_wr03_posix_path_with_spaces_fully_redacted():
    from quirk.scanner.source_scanner import _redact

    out = _redact("failed at /Users/j/Acme Corp/src/x.py", "/elsewhere/repo")
    assert "Corp" not in out and "Acme" not in out and "/Users" not in out
    assert out.startswith("failed at <path>")


def test_wr03_windows_path_with_spaces_fully_redacted():
    from quirk.scanner.source_scanner import _redact

    out = _redact(r"C:\Users\John Doe\Acme Payments\x.py", "/elsewhere/repo")
    for leak in ("Doe", "Payments", "John", "Acme"):
        assert leak not in out


def test_wr03_forward_slash_echo_of_windows_repo_path_redacted():
    from quirk.scanner.source_scanner import _redact

    repo = r"C:\Users\jdoe\Acme Payments\app"
    out = _redact("error in C:/Users/jdoe/Acme Payments/app/x.py line 3", repo)
    for leak in ("jdoe", "Payments", "Acme", "Users"):
        assert leak not in out
    assert "line 3" in out


def test_wr03_unc_path_redacted():
    from quirk.scanner.source_scanner import _redact

    out = _redact(r"cannot open \\fileserver\clients\acme\x.py now", "/elsewhere/repo")
    for leak in ("fileserver", "clients", "acme"):
        assert leak not in out
    assert out.endswith("now") or "now" in out


def test_wr03_url_scheme_is_not_mistaken_for_a_drive_path():
    from quirk.scanner.source_scanner import _redact

    assert "http" in _redact("fetch http://x.example/rules failed", "/r")


@pytest.mark.parametrize("repo", [".", "src", "app"])
def test_wr04_short_repo_path_does_not_corrupt_message(repo):
    from quirk.scanner.source_scanner import _redact

    msg = "semgrep exited 2: Invalid rule config.yaml v1.2 in src and app code"
    out = _redact(msg, repo)
    assert out == msg


def test_wr04_absolute_repo_replaced_only_as_whole_path(tmp_path):
    from quirk.scanner.source_scanner import _redact

    repo = str(tmp_path / "proj")
    out = _redact(f"bad {repo}/a.py and {repo}2/b.py and {repo}", repo)
    assert out.startswith("bad <repo>/a.py")
    assert "<repo>2" not in out
    assert repo not in out


def test_in07_empty_repo_path_does_not_replace_cwd():
    from quirk.scanner.source_scanner import _redact

    cwd = os.getcwd()
    out = _redact(f"working in {cwd} ok", "")
    assert "<repo>" not in out


# --------------------------------------------------------------------------
# 235.1 review WR-05: semgrep error text is credential-scrubbed
# --------------------------------------------------------------------------

_CRED_MSG = 'Syntax error at line 3: password = "postgres://u:hunter2@db/prod"'


def test_wr05_partial_result_error_row_is_credential_scrubbed(fake_semgrep_repos):
    body = dict(SAMPLE_SEMGREP_OUTPUT)
    body["results"] = body["results"][:1]
    body["errors"] = [_err_entry(2, _CRED_MSG)]
    (repo,) = fake_semgrep_repos({"a": (json.dumps(body), 1)})
    eps = scan_source_targets([repo])
    (row,) = [e for e in eps if e.scan_error]
    assert "hunter2" not in row.scan_error
    assert "postgres://" not in row.scan_error
    assert row.scan_error.startswith("source scan incomplete")


def test_wr05_raising_path_message_is_credential_scrubbed(fake_semgrep_repos):
    (repo,) = fake_semgrep_repos(
        {"a": (json.dumps({"results": [], "errors": [_err_entry(2, _CRED_MSG)]}), 2)}
    )
    with pytest.raises(SourceScanError) as ei:
        scan_source_repo(repo)
    assert "hunter2" not in str(ei.value)


def test_wr05_benign_error_text_is_still_shown(fake_semgrep_repos):
    body = dict(SAMPLE_SEMGREP_OUTPUT)
    body["results"] = body["results"][:1]
    body["errors"] = [_err_entry(2, "Syntax error at line 3")]
    (repo,) = fake_semgrep_repos({"a": (json.dumps(body), 1)})
    (row,) = [e for e in scan_source_targets([repo]) if e.scan_error]
    assert "Syntax error at line 3" in row.scan_error
