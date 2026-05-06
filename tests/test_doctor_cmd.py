"""Phase 52 DOCS-05: Tests for quirk.cli.doctor_cmd.run_doctor() health check."""
from __future__ import annotations
import sys
import pytest
from unittest import mock


def test_doctor_exits_0_all_pass(monkeypatch):
    """run_doctor() exits 0 when all non-informational checks pass."""
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    # Freeze compliance freshness so the test never fails as last_verified dates age.
    monkeypatch.setattr(
        "quirk.cli.doctor_cmd._check_compliance_freshness",
        lambda: (True, "[green][✓][/green] mocked freshness"),
    )
    with mock.patch("sqlite3.connect") as mock_conn:
        mock_conn.return_value.execute = lambda q: None
        mock_conn.return_value.close = lambda: None
        with mock.patch("socket.create_connection") as mock_sock:
            mock_sock.return_value.close = lambda: None
            with pytest.raises(SystemExit) as exc:
                from quirk.cli.doctor_cmd import run_doctor
                run_doctor()
    assert exc.value.code == 0, f"expected exit 0, got {exc.value.code}"


def test_doctor_exits_1_missing_binary(monkeypatch):
    """run_doctor() exits 1 when a required scanner binary is missing (D-14 cat 2)."""
    monkeypatch.setattr("shutil.which", lambda x: None)
    with pytest.raises(SystemExit) as exc:
        from quirk.cli.doctor_cmd import run_doctor
        run_doctor()
    assert exc.value.code == 1, f"expected exit 1, got {exc.value.code}"


def test_informational_checks_never_exit_1(monkeypatch):
    """D-14 cat 4/7/8: QRAMM, network, dashboard probes are informational only — never trigger exit 1."""
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    with mock.patch("sqlite3.connect") as mock_conn:
        mock_conn.return_value.execute = lambda q: None
        mock_conn.return_value.close = lambda: None
        # network probe + dashboard probe both fail; QRAMM module absent
        with mock.patch("socket.create_connection", side_effect=OSError("no network")):
            with pytest.raises(SystemExit) as exc:
                from quirk.cli.doctor_cmd import run_doctor
                run_doctor()
    assert exc.value.code == 0, (
        f"informational probe failures must not trigger exit 1, got {exc.value.code}"
    )
