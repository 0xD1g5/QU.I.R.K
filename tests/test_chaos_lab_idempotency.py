"""CHAOS-04: Chaos-lab per-profile idempotency regression.

Exercises every Docker Compose profile twice via `./lab.sh up` and asserts
both cycles exit 0 — proves seed sidecars are idempotent and long-running
services survive a re-up against persisted volumes.

Marked `@pytest.mark.slow` and skipped cleanly when the Docker daemon is
unreachable. To run explicitly:

    pytest -m slow tests/test_chaos_lab_idempotency.py
"""
from __future__ import annotations

import os
import platform
import shutil
import time
from pathlib import Path

import pytest

from tests.cli_helpers import run_fork_safe

LAB_DIR = (
    Path(__file__).resolve().parent.parent / "quantum-chaos-enterprise-lab"
)
COMPOSE = LAB_DIR / "docker-compose.yml"

_DOCKER = shutil.which("docker")


def _docker_available() -> bool:
    if not _DOCKER:
        return False
    try:
        r = run_fork_safe([_DOCKER, "info"], timeout=5)
        return r.returncode == 0
    except Exception:
        return False


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not _docker_available(),
        reason="Docker daemon not available",
    ),
]


def _discover_profiles() -> list[str]:
    r = run_fork_safe(
        [_DOCKER, "compose", "-f", str(COMPOSE), "config", "--profiles"],
        check=True,
    )
    return sorted({line.strip() for line in r.stdout.splitlines() if line.strip()})


@pytest.fixture(scope="module")
def profiles() -> list[str]:
    return _discover_profiles()


def _up(profile: str):
    env = os.environ.copy()
    env["PROFILE_ARGS"] = f"--profile {profile}"
    # lab.sh's COMPOSE_FILE default ("docker-compose.yml") is relative and
    # was previously resolved against cwd=LAB_DIR. run_fork_safe never
    # passes cwd, so pin COMPOSE_FILE to an absolute path explicitly rather
    # than adding a `cd` inside lab.sh -- lab.sh's `.env` sourcing is
    # deliberately cwd-relative and load-bearing (tested by
    # tests/test_lab_profile_args_precedence.py's CLI-wins-over-.env
    # precedence check, which relies on invoking lab.sh from a cwd with no
    # `.env` present); anchoring the whole script to its own directory would
    # silently defeat that test by always sourcing quantum-chaos-enterprise-lab/.env.
    env["COMPOSE_FILE"] = str(COMPOSE)
    return run_fork_safe(
        [str(LAB_DIR / "lab.sh"), "up"],
        timeout=300,
        env=env,
    )


def _down() -> None:
    env = os.environ.copy()
    env["COMPOSE_FILE"] = str(COMPOSE)
    run_fork_safe(
        [str(LAB_DIR / "lab.sh"), "down"],
        timeout=120,
        env=env,
    )


def test_smime_and_adcs_profiles_discovered(profiles):
    """CHAOS-06 parity sanity — both new v4.10 profiles enumerate."""
    assert "smime" in profiles, f"smime missing from {profiles}"
    assert "adcs" in profiles, f"adcs missing from {profiles}"


# Parametrize via a module-level discovery so each profile produces a
# named test case (one row per profile) — failures localize cleanly.
def _profile_param_list() -> list[str]:
    if not _docker_available():
        return []
    try:
        return _discover_profiles()
    except Exception:
        return []


@pytest.mark.parametrize("profile", _profile_param_list())
def test_profile_re_up_is_idempotent(profile: str) -> None:
    # macOS *:88 collides with system KDC; mirror lab.sh's exclusion.
    if (
        profile == "kerberos"
        and platform.system() == "Darwin"
        and os.environ.get("LAB_INCLUDE_KERBEROS") != "1"
    ):
        pytest.skip(
            "macOS *:88 collides with system KDC; set LAB_INCLUDE_KERBEROS=1 to include (BACK-89)"
        )

    try:
        r1 = _up(profile)
        assert r1.returncode == 0, (
            f"{profile} first up failed (rc={r1.returncode}):\n"
            f"STDOUT:\n{r1.stdout}\nSTDERR:\n{r1.stderr}"
        )
        # Let seed sidecars settle before re-up.
        time.sleep(15)
        r2 = _up(profile)
        assert r2.returncode == 0, (
            f"{profile} second up failed (rc={r2.returncode}):\n"
            f"STDOUT:\n{r2.stdout}\nSTDERR:\n{r2.stderr}"
        )
    finally:
        _down()
