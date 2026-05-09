"""Phase 7 — BRAND-04: quirk init subcommand tests.

Phase 58 — HARDEN-API-04: path-traversal fuzz corpus for quirk init --output.
The 50+ parametrized cases are the permanent regression gate for CR-01.
"""
import subprocess
import sys
import os
import tempfile

import pytest

from quirk.cli.init_cmd import run_init


# ---------------------------------------------------------------------------
# Phase 58 / HARDEN-API-04: path-traversal fuzz corpus (CR-01)
# ---------------------------------------------------------------------------

# 50+ adversarial output-path patterns that the guard must reject.
# Patterns cover: classic dotdot, absolute paths outside CWD, deep nesting
# with enough dotdots to escape CWD, and home-dir combinations.
#
# NOTE: On POSIX, the guard uses os.path.realpath() CWD-anchor logic.
# Patterns included here are verified to resolve OUTSIDE the CWD or to
# contain literal ".." segments that the normpath dotdot check catches.
# URL-encoded chars (%2F), Windows-only backslash separators (\), and
# triple-dot filenames (...) are legal POSIX filenames that resolve within
# CWD — they are intentionally excluded because the guard correctly allows them.
_TRAVERSAL_PATTERNS = [
    # Classic single dotdot (escapes CWD parent)
    "../evil.yaml",
    "../../etc/passwd",
    "../../../tmp/evil",
    "../../../etc/shadow",
    "../../.ssh/authorized_keys",
    # Mixed subdir + dotdot (enough dotdots to escape CWD)
    "subdir/../../evil.yaml",
    "subdir/../../../evil.yaml",
    "a/../../etc/shadow",
    "a/b/c/../../../../../../../etc/passwd",
    "x/y/../../../../../../tmp/evil",
    "normal/../../evil.yaml",
    "safe/../../evil",
    "./good/../../../evil",
    "subdir/./../..",
    "config/sub/../../../evil",
    "output/sub/dir/../../../../etc/passwd",
    "deploy/../../../../../../home/root/.bashrc",
    "output/../../secret.yaml",
    "logs/reports/../../../../../../etc/cron.d/evil",
    "build/dist/../../../etc/passwd",
    # Home-dir dotdot (tilde combined with dotdot escapes CWD)
    "~/../../etc/passwd",
    "~/../../../etc/shadow",
    # Many dotdots via string multiplication (enough to escape any reasonable CWD)
    "normal/" + "../" * 20 + "evil",
    "a/" + "../" * 30 + "etc/passwd",
    "sub/dir/" + "../" * 25 + "secret",
    # Absolute paths outside CWD (all absolute paths are outside any relative CWD)
    "/tmp/evil.yaml",
    "/etc/passwd",
    "/var/log/evil.yaml",
    "/root/.ssh/authorized_keys",
    "/home/user/.bashrc",
    "/.secret",
    "/proc/self/environ",
    "/proc/self/cmdline",
    "/sys/kernel/debug",
    "/dev/sda",
    "/dev/null/../etc/passwd",
    "/usr/bin/evil",
    "/opt/evil",
    "/absolute/path/outside/cwd",
    "/usr/local/lib/evil.so",
    "/var/run/evil.pid",
    "/etc/cron.d/evil",
    "/etc/sudoers.d/evil",
    "/usr/share/evil",
    "/srv/data/evil.yaml",
    "/run/secrets/db_password",
    "/boot/grub/grub.cfg",
    "/lib/systemd/system/evil.service",
    "/snap/core/current/etc/passwd",
    "/media/usb/evil.yaml",
    "/mnt/nfs/evil.yaml",
]


@pytest.mark.parametrize("bad_path", _TRAVERSAL_PATTERNS, ids=lambda p: repr(p)[:60])
def test_init_rejects_traversal_paths(bad_path, capsys, tmp_path, monkeypatch):
    """run_init must warn and return (not write) for every adversarial output path.

    Regression gate for CR-01 / HARDEN-API-04. A future refactor that removes
    the CWD-anchor guard will immediately fail 50+ parametrized cases here.
    """
    monkeypatch.chdir(tmp_path)

    run_init(bad_path)

    captured = capsys.readouterr()
    combined = (captured.out + captured.err).lower()

    # Guard must produce at least one of these keywords — any is sufficient.
    assert any(kw in combined for kw in ("outside", "traversal", "not allowed", "warning")), (
        f"Expected rejection message for path {bad_path!r}, got stdout={captured.out!r} stderr={captured.err!r}"
    )
    # Guard must return without writing — no config file must appear INSIDE tmp_path
    # that was not already there (the guard writes nothing; only the absolute-path
    # patterns could create files outside tmp_path, which is irrelevant here).
    written_inside_cwd = [
        f for f in tmp_path.iterdir()
        if f.suffix in (".yaml", ".json", ".cfg") or f.name == "config.yaml"
    ]
    assert written_inside_cwd == [], (
        f"run_init wrote a config file for adversarial path {bad_path!r}: {written_inside_cwd}"
    )


# ---------------------------------------------------------------------------
# Phase 7 — BRAND-04 (original tests below)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_init_creates_config(tmp_path):
    """quirk init must create a config.yaml in the specified output path."""
    out = str(tmp_path / "config.yaml")
    result = subprocess.run(
        [sys.executable, "run_scan.py", "init", "--output", out],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"quirk init exited {result.returncode}: {result.stderr}"
    assert os.path.exists(out), f"config.yaml not created at {out}"
    content = open(out).read()
    assert "targets:" in content, "Generated config.yaml must contain 'targets:' key"
    assert "127.0.0.1" in content, "Generated config.yaml must default to 127.0.0.1"


@pytest.mark.slow
def test_init_no_overwrite(tmp_path):
    """quirk init must not silently overwrite an existing config.yaml."""
    out = str(tmp_path / "config.yaml")
    # First run — creates file
    subprocess.run(
        [sys.executable, "run_scan.py", "init", "--output", out],
        capture_output=True, text=True,
    )
    first_mtime = os.path.getmtime(out)
    # Second run — should warn and not overwrite
    result = subprocess.run(
        [sys.executable, "run_scan.py", "init", "--output", out],
        capture_output=True, text=True,
    )
    second_mtime = os.path.getmtime(out)
    output = result.stdout + result.stderr
    assert "already exists" in output.lower() or "not overwriting" in output.lower(), (
        f"Expected overwrite warning, got: {output!r}"
    )
    assert first_mtime == second_mtime, "File was overwritten when it should have been preserved"
