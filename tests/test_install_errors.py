"""Phase 68 UX-02: install-day smoke tests for QRK-INSTALL-NNN format.

Covers the install-day failure scenarios called out by UX-02: missing extra,
missing nmap binary, unreadable scan database, port conflict on quirk serve,
and missing uvicorn. Each scenario must emit a stderr line matching the wire
format: [QRK-INSTALL-NNN] <cause>. Fix: <hint>.
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
QRK_FORMAT = re.compile(r"\[QRK-[A-Z]+-[A-Z0-9-]+\] .+\. Fix: .+")


# ---------------- unit tests (no subprocess) ----------------

def test_unreadable_db_format(tmp_path, monkeypatch):
    """doctor_cmd._check_db reports an unreadable QUIRK_DB_PATH via typed dict.

    Phase 75-01 (APCL-01 D-01/D-02) refactored ``_check_db`` from
    ``(path) -> (ok, msg)`` to ``() -> {ok, detail, remediation}`` and made
    it honor ``QUIRK_DB_PATH`` first. The QRK-INSTALL-003 string is no
    longer part of the dict; if the wire-format prefix matters it must be
    asserted by a separate test against the format_error registry.
    """
    from quirk.cli import doctor_cmd

    db_path = tmp_path / "quirk.db"
    db_path.write_bytes(b"")
    try:
        os.chmod(db_path, 0o000)
        monkeypatch.setenv("QUIRK_DB_PATH", str(db_path))
        result = doctor_cmd._check_db()
    finally:
        os.chmod(db_path, 0o644)

    assert result["ok"] is False
    assert "not readable" in result["detail"]
    assert result["remediation"]


def test_missing_nmap_format(monkeypatch):
    """doctor_cmd._check_binary('nmap') returns QRK-INSTALL-006 when nmap absent."""
    import shutil
    from quirk.cli import doctor_cmd

    monkeypatch.setattr(shutil, "which", lambda name: None)
    ok, msg = doctor_cmd._check_binary("nmap")
    assert ok is False
    assert "QRK-INSTALL-006" in msg, f"Expected QRK-INSTALL-006 in msg, got: {msg!r}"


def test_missing_syft_format(monkeypatch):
    """doctor_cmd._check_binary('syft') returns QRK-INSTALL-007 when syft absent."""
    import shutil
    from quirk.cli import doctor_cmd

    monkeypatch.setattr(shutil, "which", lambda name: None)
    ok, msg = doctor_cmd._check_binary("syft")
    assert ok is False
    assert "QRK-INSTALL-007" in msg


def test_format_error_matches_qrk_regex():
    """Every registry entry produces a string matching QRK_FORMAT."""
    from quirk.errors import ERROR_REGISTRY, format_error

    for code in ERROR_REGISTRY:
        msg = format_error(code)
        assert QRK_FORMAT.match(msg), f"Code {code!r} produced non-matching message: {msg!r}"


# ---------------- subprocess smoke tests (marked slow) ----------------

def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.slow
def test_port_conflict_format():
    """quirk serve on an occupied port emits [QRK-INSTALL-004] to stderr."""
    port = _free_port()
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    holder.bind(("127.0.0.1", port))
    holder.listen(1)
    try:
        result = subprocess.run(
            [sys.executable, "run_scan.py", "serve", "--port", str(port)],
            capture_output=True, text=True, timeout=20, cwd=REPO_ROOT,
        )
    finally:
        holder.close()

    combined = (result.stdout or "") + (result.stderr or "")
    assert "QRK-INSTALL-004" in combined, (
        f"Expected QRK-INSTALL-004 in output; got stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.returncode != 0, "quirk serve should exit non-zero on port conflict"


@pytest.mark.slow
def test_dashboard_missing_uvicorn_format():
    """Missing uvicorn at server.py import time emits [QRK-INSTALL-002]."""
    script = (
        "import builtins, sys\n"
        "_real_import = builtins.__import__\n"
        "def _block(name, *a, **kw):\n"
        "    if name == 'uvicorn' or name.startswith('uvicorn.'):\n"
        "        raise ImportError('forced for test')\n"
        "    return _real_import(name, *a, **kw)\n"
        "builtins.__import__ = _block\n"
        "from quirk.dashboard import server  # noqa: F401\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=15, cwd=REPO_ROOT,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "QRK-INSTALL-002" in combined, (
        f"Expected QRK-INSTALL-002; got stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.returncode != 0
