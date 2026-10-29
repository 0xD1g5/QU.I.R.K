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


def test_doctor_exits_0_all_pass(monkeypatch):
    """run_doctor() exits 0 when all non-informational checks pass."""
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    # Freeze compliance freshness so the test never fails as last_verified dates age.
    monkeypatch.setattr(
        "quirk.cli.doctor_cmd._check_compliance_freshness",
        lambda: (True, "[green][✓][/green] mocked freshness"),
    )
    # Force _check_db onto the canonical resolver and stub the sqlite call.
    monkeypatch.setenv("QUIRK_DB_PATH", "/tmp/quirk-doctor-test.db")
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr("os.access", lambda p, m: True)
    with mock.patch("sqlite3.connect") as mock_conn:
        mock_conn.return_value.execute = lambda q: None
        mock_conn.return_value.close = lambda: None
        # Phase 75 D-01 — informational probes via urlopen / gethostbyname.
        with mock.patch("quirk.cli.doctor_cmd.urlopen", side_effect=_ok_dashboard), \
             mock.patch("quirk.cli.doctor_cmd.socket.gethostbyname", return_value="93.184.216.34"):
            with pytest.raises(SystemExit) as exc:
                from quirk.cli.doctor_cmd import run_doctor
                run_doctor()
    assert exc.value.code == 0, f"expected exit 0, got {exc.value.code}"


def _stub_common(monkeypatch):
    monkeypatch.setattr(
        "quirk.cli.doctor_cmd._check_compliance_freshness",
        lambda: (True, "[green][✓][/green] mocked freshness"),
    )


def test_doctor_exits_0_with_only_optional_binaries_missing(monkeypatch, capsys):
    """Phase 235 D-24: nmap/syft/semgrep are informational; exit 0 when only they are missing."""
    monkeypatch.setattr("shutil.which", lambda x: None)
    _stub_common(monkeypatch)
    monkeypatch.setenv("QUIRK_DB_PATH", "/tmp/quirk-doctor-test.db")
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr("os.access", lambda p, m: True)
    with mock.patch("sqlite3.connect") as mock_conn:
        mock_conn.return_value.execute = lambda q: None
        mock_conn.return_value.close = lambda: None
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


def test_doctor_exits_1_below_python_floor(monkeypatch):
    """A Python below the floor is still a hard failure."""
    monkeypatch.setattr("quirk.cli.doctor_cmd._PYTHON_MIN", (99, 0))
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    _stub_common(monkeypatch)
    monkeypatch.setenv("QUIRK_DB_PATH", "/tmp/quirk-doctor-test.db")
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr("os.access", lambda p, m: True)
    with mock.patch("sqlite3.connect") as mock_conn:
        mock_conn.return_value.execute = lambda q: None
        mock_conn.return_value.close = lambda: None
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


def test_informational_checks_never_exit_1(monkeypatch):
    """D-14 cat 4/7/8 + Phase 75 D-18: informational probe failures must NOT exit 1."""
    from urllib.error import URLError

    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    monkeypatch.setattr(
        "quirk.cli.doctor_cmd._check_compliance_freshness",
        lambda: (True, "[green][✓][/green] mocked freshness"),
    )
    monkeypatch.setenv("QUIRK_DB_PATH", "/tmp/quirk-doctor-test.db")
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr("os.access", lambda p, m: True)
    with mock.patch("sqlite3.connect") as mock_conn:
        mock_conn.return_value.execute = lambda q: None
        mock_conn.return_value.close = lambda: None
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
