"""Phase 71-02 / WR-03: verify subprocess failures in scanner modules
(ssh, container, source) emit a logger.warning and return a partial
result (None / empty list) without raising to the caller.
"""
import json
import logging
import subprocess
import tempfile
from pathlib import Path

import pytest

from quirk.scanner import container_scanner, source_scanner, ssh_scanner


def _force_caplog(caplog):
    caplog.set_level(logging.WARNING)


def test_ssh_subprocess_failure_logs_warning_and_returns_none(monkeypatch, caplog):
    """ssh_scanner._run_ssh_audit: simulated subprocess.TimeoutExpired
    must produce a WARNING log record and return None (partial result)."""
    _force_caplog(caplog)

    monkeypatch.setattr(ssh_scanner.shutil, "which", lambda _: "/usr/bin/ssh-audit")

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ssh-audit", timeout=5)

    monkeypatch.setattr(ssh_scanner.subprocess, "run", _raise_timeout)

    with caplog.at_level(logging.WARNING, logger="quirk.scanner.ssh_scanner"):
        result = ssh_scanner._run_ssh_audit("example.test", 22, timeout=5)

    assert result is None
    warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and r.name == "quirk.scanner.ssh_scanner"
    ]
    assert warnings, f"expected a WARNING from quirk.scanner.ssh_scanner; got {caplog.records!r}"
    assert "subprocess failed" in warnings[0].getMessage()


def test_container_subprocess_failure_logs_warning_and_returns_empty(monkeypatch, caplog):
    """container_scanner.scan_container_image: simulated FileNotFoundError
    must produce a WARNING log record and return [] (partial result)."""
    _force_caplog(caplog)

    monkeypatch.setattr(container_scanner.shutil, "which", lambda _: "/usr/bin/syft")

    def _raise_fnf(*args, **kwargs):
        raise FileNotFoundError("syft binary disappeared mid-scan")

    monkeypatch.setattr(container_scanner.subprocess, "run", _raise_fnf)

    with caplog.at_level(logging.WARNING, logger="quirk.scanner.container_scanner"):
        result = container_scanner.scan_container_image("alpine:3.19", timeout=30)

    assert result == []
    warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and r.name == "quirk.scanner.container_scanner"
    ]
    assert warnings, f"expected a WARNING from quirk.scanner.container_scanner; got {caplog.records!r}"
    assert "subprocess failed" in warnings[0].getMessage()


def test_source_subprocess_failure_logs_warning_and_returns_empty(monkeypatch, caplog):
    """source_scanner.scan_source_repo: simulated json.JSONDecodeError
    must produce a WARNING log record and return [] (partial result)."""
    _force_caplog(caplog)

    monkeypatch.setattr(source_scanner.shutil, "which", lambda _: "/usr/bin/semgrep")

    class _FakeProc:
        stdout = "not-json-at-all"
        stderr = ""
        returncode = 0

    monkeypatch.setattr(source_scanner.subprocess, "run", lambda *a, **kw: _FakeProc())

    with tempfile.TemporaryDirectory() as td:
        # validate_repo_path requires the path to exist + be a directory.
        with caplog.at_level(logging.WARNING, logger="quirk.scanner.source_scanner"):
            result = source_scanner.scan_source_repo(td, timeout=30)

    assert result == []
    warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and r.name == "quirk.scanner.source_scanner"
    ]
    assert warnings, f"expected a WARNING from quirk.scanner.source_scanner; got {caplog.records!r}"
    assert "subprocess failed" in warnings[0].getMessage()
