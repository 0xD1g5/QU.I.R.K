"""Phase 52 DOCS-05: Tests for quirk.cli.doctor_cmd.run_doctor() health check.

Phase 75 D-01 / D-18: probes changed (TCP -> HTTP HEAD + DNS gethostbyname),
but exit-code semantics MUST remain identical to Phase 52 DOCS-05.
"""
from __future__ import annotations

import pytest
from unittest import mock


def _ok_dashboard(*_args, **_kwargs):
    resp = mock.MagicMock()
    resp.status = 200
    resp.close = lambda: None
    return resp


def test_doctor_exits_0_all_pass(monkeypatch, tmp_path):
    """run_doctor() exits 0 when all non-informational checks pass."""
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    # Freeze compliance freshness so the test never fails as last_verified dates age.
    monkeypatch.setattr(
        "quirk.cli.doctor_cmd._check_compliance_freshness",
        lambda: (True, "[green][✓][/green] mocked freshness"),
    )
    # Force _check_db onto the canonical resolver and stub the sqlite call.
    _real_db(monkeypatch, tmp_path)
    # Phase 75 D-01 — informational probes via urlopen / gethostbyname.
    with mock.patch("quirk.cli.doctor_cmd.urlopen", side_effect=_ok_dashboard), \
         mock.patch("quirk.cli.doctor_cmd.socket.gethostbyname", return_value="93.184.216.34"):
        with pytest.raises(SystemExit) as exc:
            from quirk.cli.doctor_cmd import run_doctor
            run_doctor()
    assert exc.value.code == 0, f"expected exit 0, got {exc.value.code}"


def _real_db(monkeypatch, tmp_path):
    """Point QUIRK_DB_PATH at a real, empty SQLite file under tmp_path."""
    import sqlite3
    db = tmp_path / "quirk-doctor-test.db"
    sqlite3.connect(str(db)).close()
    monkeypatch.setenv("QUIRK_DB_PATH", str(db))
    return db


def _stub_common(monkeypatch):
    monkeypatch.setattr(
        "quirk.cli.doctor_cmd._check_compliance_freshness",
        lambda: (True, "[green][✓][/green] mocked freshness"),
    )


def test_doctor_exits_0_with_only_optional_binaries_missing(monkeypatch, tmp_path, capsys):
    """Phase 235 D-24: nmap/syft/semgrep are informational; exit 0 when only they are missing."""
    monkeypatch.setattr("shutil.which", lambda x: None)
    _stub_common(monkeypatch)
    _real_db(monkeypatch, tmp_path)
    with mock.patch("quirk.cli.doctor_cmd.urlopen", side_effect=_ok_dashboard), \
         mock.patch("quirk.cli.doctor_cmd.socket.gethostbyname", return_value="93.184.216.34"):
        with pytest.raises(SystemExit) as exc:
            from quirk.cli.doctor_cmd import run_doctor
            run_doctor()
    assert exc.value.code == 0, f"expected exit 0, got {exc.value.code}"
    out = capsys.readouterr().out
    for name in ("nmap", "syft", "semgrep"):
        assert name in out
    assert out.count("(informational)") >= 3


def test_doctor_exits_1_below_python_floor(monkeypatch, tmp_path):
    """A Python below the floor is still a hard failure."""
    monkeypatch.setattr("quirk.cli.doctor_cmd._PYTHON_MIN", (99, 0))
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    _stub_common(monkeypatch)
    _real_db(monkeypatch, tmp_path)
    with mock.patch("quirk.cli.doctor_cmd.urlopen", side_effect=_ok_dashboard), \
         mock.patch("quirk.cli.doctor_cmd.socket.gethostbyname", return_value="93.184.216.34"):
        with pytest.raises(SystemExit) as exc:
            from quirk.cli.doctor_cmd import run_doctor
            run_doctor()
    assert exc.value.code == 1


def test_python_floor_is_3_10():
    from quirk.cli import doctor_cmd
    assert doctor_cmd._PYTHON_MIN == (3, 10)


def test_doctor_clean_cwd_no_db_exits_0(monkeypatch, tmp_path, capsys):
    """Clean machine: no database yet, no optional binaries -> exit 0, no DB created."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QUIRK_DB_PATH", raising=False)
    monkeypatch.setattr("shutil.which", lambda x: None)
    _stub_common(monkeypatch)
    with mock.patch("quirk.cli.doctor_cmd.urlopen", side_effect=_ok_dashboard), \
         mock.patch("quirk.cli.doctor_cmd.socket.gethostbyname", return_value="93.184.216.34"):
        with pytest.raises(SystemExit) as exc:
            from quirk.cli.doctor_cmd import run_doctor
            run_doctor()
    assert exc.value.code == 0, f"expected exit 0, got {exc.value.code}"
    out = capsys.readouterr().out
    assert "first scan" in out
    assert not (tmp_path / "quirk-output" / "quirk.db").exists()
    assert not (tmp_path / "quirk-output").exists()


def test_informational_checks_never_exit_1(monkeypatch, tmp_path):
    """D-14 cat 4/7/8 + Phase 75 D-18: informational probe failures must NOT exit 1."""
    from urllib.error import URLError

    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    monkeypatch.setattr(
        "quirk.cli.doctor_cmd._check_compliance_freshness",
        lambda: (True, "[green][✓][/green] mocked freshness"),
    )
    _real_db(monkeypatch, tmp_path)
    # Both informational probes fail.
    with mock.patch("quirk.cli.doctor_cmd.urlopen", side_effect=URLError("refused")), \
         mock.patch("quirk.cli.doctor_cmd.socket.gethostbyname",
                    side_effect=__import__("socket").gaierror("no resolver")):
        with pytest.raises(SystemExit) as exc:
            from quirk.cli.doctor_cmd import run_doctor
            run_doctor()
    assert exc.value.code == 0, (
        f"informational probe failures must not trigger exit 1, got {exc.value.code}"
    )


# ---------------------------------------------------------------------------
# Phase 235.1 D-01/D-03 — supported Python range (3.10 <= v < 3.15)
# ---------------------------------------------------------------------------

def _fake_version_info(monkeypatch, major, minor, micro=0):
    import collections
    VI = collections.namedtuple("VI", "major minor micro releaselevel serial")
    monkeypatch.setattr("sys.version_info", VI(major, minor, micro, "final", 0))


@pytest.mark.parametrize("ver", [(3, 15, 0), (3, 9, 18), (4, 0, 0)])
def test_python_range_rejects_outside(monkeypatch, ver):
    from quirk.cli import doctor_cmd
    _fake_version_info(monkeypatch, *ver)
    ok, line = doctor_cmd._check_python_version()
    assert ok is False
    assert "INSTALL-005" in line
    assert "3.10" in line and "3.14" in line


@pytest.mark.parametrize("ver", [(3, 10, 0), (3, 14, 9), (3, 12, 1)])
def test_python_range_accepts_inside(monkeypatch, ver):
    from quirk.cli import doctor_cmd
    _fake_version_info(monkeypatch, *ver)
    ok, _line = doctor_cmd._check_python_version()
    assert ok is True


def test_python_cap_exits_1_when_max_exclusive_lowered(monkeypatch, tmp_path):
    """The upper bound is enforced end to end: run_doctor exits 1 past the cap."""
    import sys
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QUIRK_DB_PATH", str(tmp_path / "quirk.db"))
    monkeypatch.setattr("quirk.cli.doctor_cmd._PYTHON_MAX_EXCLUSIVE", (3, 10))
    assert sys.version_info[:2] >= (3, 10)
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    _stub_common(monkeypatch)
    with mock.patch("quirk.cli.doctor_cmd.urlopen", side_effect=_ok_dashboard), \
         mock.patch("quirk.cli.doctor_cmd.socket.gethostbyname", return_value="93.184.216.34"):
        with pytest.raises(SystemExit) as exc:
            from quirk.cli.doctor_cmd import run_doctor
            run_doctor()
    assert exc.value.code == 1


def test_python_range_matches_pyproject_requires_python():
    """D-01: requires-python is ">=3.10,<3.15" and equals the doctor's bounds."""
    import re
    from pathlib import Path
    from quirk.cli import doctor_cmd

    text = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    hdr = re.search(r"^\[project\]\s*$", text, re.M)
    body = text[hdr.end():]
    nxt = re.search(r"^\[", body, re.M)
    table = body[: nxt.start()] if nxt else body
    m = re.search(r'^requires-python\s*=\s*"([^"]+)"\s*$', table, re.M)
    assert m, "pyproject [project] has no requires-python"
    spec = m.group(1)
    assert spec == ">=3.10,<3.15"
    lo = re.search(r">=(\d+)\.(\d+)", spec)
    hi = re.search(r"<(\d+)\.(\d+)", spec)
    assert (int(lo.group(1)), int(lo.group(2))) == doctor_cmd._PYTHON_MIN
    assert (int(hi.group(1)), int(hi.group(2))) == doctor_cmd._PYTHON_MAX_EXCLUSIVE


# ---------------------------------------------------------------------------
# Phase 235.1 D-08 — "configured but missing" scanner binary warning
# ---------------------------------------------------------------------------

def _run_doctor_with_config(monkeypatch, tmp_path, capsys, connectors, which):
    """Run run_doctor in tmp_path with a config.yaml holding ``connectors``."""
    import yaml

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COLUMNS", "400")  # keep Rich from wrapping table cells
    import sqlite3
    sqlite3.connect(str(tmp_path / "quirk.db")).close()
    monkeypatch.setenv("QUIRK_DB_PATH", str(tmp_path / "quirk.db"))
    if connectors is not None:
        (tmp_path / "config.yaml").write_text(
            yaml.safe_dump({"connectors": connectors}), encoding="utf-8"
        )
    monkeypatch.setattr("quirk.cli.doctor_cmd.shutil.which", which)
    _stub_common(monkeypatch)
    with mock.patch("quirk.cli.doctor_cmd.urlopen", side_effect=_ok_dashboard), \
         mock.patch("quirk.cli.doctor_cmd.socket.gethostbyname", return_value="93.184.216.34"):
        with pytest.raises(SystemExit) as exc:
            from quirk.cli.doctor_cmd import run_doctor
            run_doctor()
    return exc.value.code, capsys.readouterr().out


def _row(out, binary):
    return next(ln for ln in out.splitlines() if f"Binary: {binary}" in ln)


def test_doctor_configured_semgrep_missing_warns(monkeypatch, tmp_path, capsys):
    code, out = _run_doctor_with_config(
        monkeypatch, tmp_path, capsys,
        {"enable_source": True, "source_targets": ["/tmp/x"]}, lambda n: None,
    )
    assert code == 0
    row = _row(out, "semgrep")
    assert "configured but missing" in row
    assert "INSTALL-008" in row
    assert "Not assessed" in row


def test_doctor_configured_syft_missing_warns(monkeypatch, tmp_path, capsys):
    code, out = _run_doctor_with_config(
        monkeypatch, tmp_path, capsys,
        {"enable_container": True, "container_targets": ["alpine:3.20"]}, lambda n: None,
    )
    assert code == 0
    row = _row(out, "syft")
    assert "configured but missing" in row
    assert "INSTALL-007" in row
    assert "configured but missing" not in _row(out, "semgrep")


def test_doctor_configured_template_empty_targets_is_informational(monkeypatch, tmp_path, capsys):
    """quirk init template: enable_* true, targets absent -> no warning."""
    code, out = _run_doctor_with_config(
        monkeypatch, tmp_path, capsys,
        {"enable_source": True, "enable_container": True, "source_targets": []},
        lambda n: None,
    )
    assert code == 0
    assert "configured but missing" not in out
    assert "(informational)" in _row(out, "semgrep")
    assert "(informational)" in _row(out, "syft")


def test_doctor_configured_but_disabled_is_informational(monkeypatch, tmp_path, capsys):
    code, out = _run_doctor_with_config(
        monkeypatch, tmp_path, capsys,
        {"enable_source": False, "source_targets": ["/tmp/x"]}, lambda n: None,
    )
    assert code == 0
    assert "configured but missing" not in out


def test_doctor_configured_no_config_file_is_informational(monkeypatch, tmp_path, capsys):
    code, out = _run_doctor_with_config(monkeypatch, tmp_path, capsys, None, lambda n: None)
    assert code == 0
    assert "configured but missing" not in out
    assert "(informational)" in _row(out, "semgrep")


def test_doctor_configured_binary_present_is_green(monkeypatch, tmp_path, capsys):
    code, out = _run_doctor_with_config(
        monkeypatch, tmp_path, capsys,
        {"enable_source": True, "source_targets": ["/tmp/x"]},
        lambda n: "/opt/bin/" + n,
    )
    assert code == 0
    row = _row(out, "semgrep")
    assert "/opt/bin/semgrep" in row
    assert "configured but missing" not in row


# ---------------------------------------------------------------------------
# Phase 235.1 D-10 — truthful, side-effect-free _check_db
# ---------------------------------------------------------------------------

def _db_target(monkeypatch, path, via):
    """Point _check_db at ``path`` through the env var or the default resolver."""
    if via == "env":
        monkeypatch.setenv("QUIRK_DB_PATH", str(path))
    else:
        monkeypatch.delenv("QUIRK_DB_PATH", raising=False)
        monkeypatch.setattr("quirk.dashboard.api.deps._default_db_path", lambda: str(path))


def _deny_write_for(monkeypatch, denied_dir):
    import os
    real_access = os.access
    denied = str(denied_dir)

    def fake_access(p, mode, *a, **k):
        if mode == os.W_OK and str(p) == denied:
            return False
        return real_access(p, mode, *a, **k)

    monkeypatch.setattr("quirk.cli.doctor_cmd.os.access", fake_access)


@pytest.mark.parametrize("via", ["env", "default"])
def test_check_db_directory_at_path_fails(monkeypatch, tmp_path, via):
    from quirk.cli.doctor_cmd import _check_db
    d = tmp_path / "dbdir"
    d.mkdir()
    _db_target(monkeypatch, d, via)
    r = _check_db()
    assert r["ok"] is False
    assert "is not a file" in r["detail"]


@pytest.mark.parametrize("via", ["env", "default"])
def test_check_db_file_in_ancestor_place_fails(monkeypatch, tmp_path, via):
    from quirk.cli.doctor_cmd import _check_db
    f = tmp_path / "afile"
    f.write_text("x")
    _db_target(monkeypatch, f / "quirk.db", via)
    r = _check_db()
    assert r["ok"] is False
    assert "cannot create database" in r["detail"]


@pytest.mark.parametrize("via", ["env", "default"])
def test_check_db_unwritable_ancestor_fails(monkeypatch, tmp_path, via):
    from quirk.cli.doctor_cmd import _check_db
    ro = tmp_path / "ro"
    ro.mkdir()
    _db_target(monkeypatch, ro / "sub" / "quirk.db", via)
    _deny_write_for(monkeypatch, ro)
    r = _check_db()
    assert r["ok"] is False
    assert "cannot create database" in r["detail"]
    assert not (ro / "sub").exists()


@pytest.mark.parametrize("via", ["env", "default"])
def test_check_db_not_yet_created_is_informational_and_creates_nothing(monkeypatch, tmp_path, via):
    from quirk.cli.doctor_cmd import _check_db
    target = tmp_path / "new" / "quirk.db"
    _db_target(monkeypatch, target, via)
    r = _check_db()
    assert r["ok"] is True
    assert r["informational"] is True
    assert "created by the first scan" in r["detail"]
    assert not (tmp_path / "new").exists()


@pytest.mark.parametrize("via", ["env", "default"])
def test_check_db_existing_sqlite_file_reachable(monkeypatch, tmp_path, via):
    import sqlite3
    from quirk.cli.doctor_cmd import _check_db
    db = tmp_path / "quirk.db"
    sqlite3.connect(str(db)).close()
    _db_target(monkeypatch, db, via)
    r = _check_db()
    assert r["ok"] is True
    assert "reachable" in r["detail"]
    assert "informational" not in r


def test_check_db_unreadable_existing_file_fails(monkeypatch, tmp_path):
    import os
    from quirk.cli.doctor_cmd import _check_db
    db = tmp_path / "quirk.db"
    db.write_bytes(b"")
    _db_target(monkeypatch, db, "env")
    real_access = os.access
    monkeypatch.setattr(
        "quirk.cli.doctor_cmd.os.access",
        lambda p, m, *a, **k: False if (m == os.R_OK and str(p) == str(db)) else real_access(p, m, *a, **k),
    )
    r = _check_db()
    assert r["ok"] is False
    assert "not readable" in r["detail"]
