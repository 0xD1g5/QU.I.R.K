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
import subprocess
import time
from pathlib import Path

import pytest

LAB_DIR = (
    Path(__file__).resolve().parent.parent / "quantum-chaos-enterprise-lab"
)
COMPOSE = LAB_DIR / "docker-compose.yml"


def _docker_available() -> bool:
    try:
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
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
    r = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "config", "--profiles"],
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted({line.strip() for line in r.stdout.splitlines() if line.strip()})


@pytest.fixture(scope="module")
def profiles() -> list[str]:
    return _discover_profiles()


def _up(profile: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PROFILE_ARGS"] = f"--profile {profile}"
    return subprocess.run(
        ["./lab.sh", "up"],
        cwd=LAB_DIR,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )


def _down() -> None:
    subprocess.run(
        ["./lab.sh", "down"],
        cwd=LAB_DIR,
        capture_output=True,
        timeout=120,
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
