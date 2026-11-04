"""235.1-11 (HARNESS-04): the release smoke harness must not print PASS after
a failed, skipped, stale, foreign-port or hung step.

Everything here is CI-safe: no real docker (a stub ``docker`` is first on
PATH), no network, no chaos lab.  ``--out`` cannot be a pytest ``tmp_path``
(the driver refuses /tmp and /var/folders), so driver cases use a temp dir
under ``$HOME`` with ``--allow-out-anywhere``.

``SMOKE_DRIVER`` (env) points the driver tests at another copy of
release_smoke.sh so the "red on the defect" proof can be re-run against the
pre-fix driver; it is unset in normal runs.
"""
from __future__ import annotations

import os
import shutil
import socket
import tempfile
import uuid
from pathlib import Path

import pytest

from tests.cli_helpers import run_fork_safe

BASH = shutil.which("bash") or "/bin/bash"
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
INNER = SCRIPTS / "release_smoke_inner.sh"
DRIVER = Path(os.environ.get("SMOKE_DRIVER", str(SCRIPTS / "release_smoke.sh")))

PASS_TRANSCRIPT = "QUIRK release smoke - leg linux-3.11\n\nSUMMARY\n  PASS  1. x\n\nRESULT: PASS\n"
MIXED_TRANSCRIPT = "RESULT: PASS\nlater things went wrong\n  FAIL 9. y\n\nRESULT: FAIL\n"

STUB_DOCKER = r"""#!/bin/bash
# stub docker: STUB_EXEC_RC = rc of the inner run; STUB_CP_OUT = fail|file
case "$1" in
  info|pull|rm|run) exit 0 ;;
  image) echo "python@sha256:stub"; exit 0 ;;
  exec)
    for a in "$@"; do [ "$a" = "mkdir" ] && exit 0; done
    echo "stub inner stdout"; exit "${STUB_EXEC_RC:-0}" ;;
  cp)
    case "$2" in
      q235-*:/smoke/out/.)
        [ "${STUB_CP_OUT:-fail}" = "fail" ] && { echo "stub: cp failed" >&2; exit 1; }
        mkdir -p "$3"; cp "${STUB_TRANSCRIPT}" "$3/transcript.txt"; exit 0 ;;
    esac
    exit 0 ;;
esac
echo "stub docker: unhandled: $*" >&2; exit 99
"""


@pytest.fixture()
def home_out():
    d = Path(tempfile.mkdtemp(dir=str(Path.home()), prefix="qsmoke-test-"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def stub_env(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    dk = bindir / "docker"
    dk.write_text(STUB_DOCKER, encoding="utf-8")
    dk.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    return env, tmp_path


def _driver(out: Path, env: dict, *extra: str):
    return run_fork_safe(
        [BASH, str(DRIVER), "--leg", "linux-3.11", "--source", "pypi:5.28.0",
         "--out", str(out), "--allow-out-anywhere", *extra],
        env=env, timeout=120,
    )


def _last(out: Path) -> str:
    return (out / "transcript.txt").read_text(encoding="utf-8").splitlines()[-1]


def _seed_stale(out: Path):
    (out / "inner").mkdir(parents=True)
    (out / "inner" / "transcript.txt").write_text(PASS_TRANSCRIPT, encoding="utf-8")
    (out / "inner-stdout.txt").write_text("old run\n", encoding="utf-8")


def _diag(r) -> str:
    return f"rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"


# ---------------------------------------------------------------- inner script

def test_inner_self_check():
    r = run_fork_safe([BASH, str(INNER), "--self-check"], timeout=120)
    assert r.returncode == 0, _diag(r)
    assert "inner self-check: ok" in r.stdout


def test_inner_self_check_without_timeout_binary():
    """The background-watchdog fallback (no `timeout` on PATH) also stops a hang."""
    env = dict(os.environ, Q_NO_TIMEOUT_BIN="1")
    r = run_fork_safe([BASH, str(INNER), "--self-check"], env=env, timeout=120)
    assert r.returncode == 0, _diag(r)
    assert "run_bounded times out a hung command" in r.stdout


MUTATIONS = {
    # name: (old text in the inner script, replacement)
    "verdict_always_pass": ('  if [ "$1" -eq 0 ] && [ "$2" -eq 0 ] && [ "$3" -gt 0 ]; then',
                            "  if true; then"),
    "skip_ignored": ('[ "$1" -eq 0 ] && [ "$2" -eq 0 ] && [ "$3" -gt 0 ]',
                     '[ "$1" -eq 0 ] && [ "$3" -gt 0 ]'),
    "zero_checks_ignored": ('[ "$1" -eq 0 ] && [ "$2" -eq 0 ] && [ "$3" -gt 0 ]',
                            '[ "$1" -eq 0 ] && [ "$2" -eq 0 ]'),
    "unpinned_assertion_disabled": (
        'python3 "${PV}" --report "${d}/u.json" --output "${d}/u.txt" --rc 0 --expected 5.28.1 >/dev/null',
        "true"),
    "watchdog_removed": ('timeout -k 5 "${secs}" bash -c "${text}" </dev/null',
                         'bash -c "${text}" </dev/null'),
    "port_check_blind": ("sys.exit(0 if s.connect_ex((\"127.0.0.1\", int(sys.argv[1]))) == 0 else 1)",
                         "sys.exit(1)"),
    "everything_runs_bounded": ('*"cd "*|*"source "*|". "*|*"&& . "*|*"; . "*|*"export "*) return 0 ;;',
                                '*"zzzz"*) return 0 ;;'),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_inner_self_check_goes_red_on_mutation(name, tmp_path):
    old, new = MUTATIONS[name]
    src = INNER.read_text(encoding="utf-8")
    assert old in src, f"mutation anchor for {name} no longer in the script"
    d = tmp_path / "mut"
    d.mkdir()
    (d / "release_smoke_inner.sh").write_text(src.replace(old, new), encoding="utf-8")
    shutil.copy(SCRIPTS / "pip_unpinned_verdict.py", d / "pip_unpinned_verdict.py")
    r = run_fork_safe([BASH, str(d / "release_smoke_inner.sh"), "--self-check"], timeout=120)
    assert r.returncode == 1, f"mutation {name} stayed green\n{_diag(r)}"
    assert "inner self-check: FAILED" in r.stdout


def _listener():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    return s


def test_port_collision_is_refused():
    s = _listener()
    try:
        port = s.getsockname()[1]
        r = run_fork_safe([BASH, str(INNER), "--probe-port", str(port)], timeout=30)
        assert r.returncode == 1, _diag(r)
        assert "already in use" in r.stdout
    finally:
        s.close()
    r = run_fork_safe([BASH, str(INNER), "--probe-port", str(port)], timeout=30)
    assert r.returncode == 0, _diag(r)


# ---------------------------------------------------------------------- driver

def test_stub_control_clean_pass(stub_env, home_out):
    """Positive control: the stub can produce a genuine PASS, so the FAIL cases mean something."""
    env, tmp = stub_env
    t = tmp / "t.txt"
    t.write_text(PASS_TRANSCRIPT, encoding="utf-8")
    env.update(STUB_CP_OUT="file", STUB_TRANSCRIPT=str(t), STUB_EXEC_RC="0")
    out = home_out / "o"
    r = _driver(out, env)
    assert r.returncode == 0, _diag(r)
    assert _last(out) == "RESULT: PASS"


def test_stale_transcript_dead_container(stub_env, home_out):
    """CR-03a/c: container dies and the copy-out fails; the old PASS must not be reused."""
    env, _ = stub_env
    env.update(STUB_CP_OUT="fail", STUB_EXEC_RC="1")
    out = home_out / "o"
    _seed_stale(out)
    r = _driver(out, env)
    assert r.returncode == 1, _diag(r)
    assert _last(out) == "RESULT: FAIL", _diag(r)
    assert not (out / "inner" / "transcript.txt").exists()


def test_stale_transcript_copy_failure_only(stub_env, home_out):
    """CR-03c: the leg 'succeeded' but the copy-out failed -- stale PASS must not win."""
    env, _ = stub_env
    env.update(STUB_CP_OUT="fail", STUB_EXEC_RC="0")
    out = home_out / "o"
    _seed_stale(out)
    r = _driver(out, env)
    assert r.returncode == 1, _diag(r)
    assert _last(out) == "RESULT: FAIL"


def test_pass_mid_file_fail_last(stub_env, home_out):
    """CR-03b: a PASS line mid-file with FAIL last is a FAIL."""
    env, tmp = stub_env
    t = tmp / "t.txt"
    t.write_text(MIXED_TRANSCRIPT, encoding="utf-8")
    env.update(STUB_CP_OUT="file", STUB_TRANSCRIPT=str(t), STUB_EXEC_RC="0")
    out = home_out / "o"
    r = _driver(out, env)
    assert r.returncode == 1, _diag(r)
    assert _last(out) == "RESULT: FAIL"


def test_nonzero_leg_rc_with_pass_transcript_is_fail(stub_env, home_out):
    """CR-03b: RUN_RC != 0 beats a transcript that ends in PASS."""
    env, tmp = stub_env
    t = tmp / "t.txt"
    t.write_text(PASS_TRANSCRIPT, encoding="utf-8")
    env.update(STUB_CP_OUT="file", STUB_TRANSCRIPT=str(t), STUB_EXEC_RC="1")
    out = home_out / "o"
    r = _driver(out, env)
    assert r.returncode == 1, _diag(r)
    assert _last(out) == "RESULT: FAIL"


def test_refused_out_creates_nothing():
    """IN-05: a refused --out (inside the repo) leaves no directory behind."""
    victim = ROOT / f"does-not-exist-{uuid.uuid4().hex[:8]}" / "deeper"
    try:
        r = run_fork_safe(
            [BASH, str(DRIVER), "--leg", "linux-3.11", "--source", "pypi:5.28.0",
             "--out", str(victim), "--allow-out-anywhere"], timeout=60)
        assert r.returncode != 0, _diag(r)
        assert not victim.exists() and not victim.parent.exists(), "refused --out left a directory"
    finally:
        shutil.rmtree(victim.parent, ignore_errors=True)


def test_refused_out_off_volume_creates_nothing(home_out):
    """IN-05: refusal for 'not on the volume' also creates no ancestors."""
    victim = home_out / "a" / "b"
    r = run_fork_safe(
        [BASH, str(DRIVER), "--leg", "linux-3.11", "--source", "pypi:5.28.0",
         "--out", str(victim)], timeout=60)
    assert r.returncode != 0, _diag(r)
    assert not (home_out / "a").exists(), "refused --out created an ancestor"


def test_driver_has_no_dead_run_env():
    assert "run_env" not in DRIVER.read_text(encoding="utf-8")
