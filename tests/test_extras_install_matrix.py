"""Phase 80 ADCS-07 — Extras-install matrix test.

Asserts `cryptography>=44.0` survives across the three extras
combinations that Phase 80 expanded:

  - `quirk[adcs]`           — ldap3-only; no impacket; cryptography>=44.0.
  - `quirk[all]`            — already had `quirk[adcs]` added in 80-01;
                              still impacket-free per D-01 / Phase 45.
  - `quirk[adcs,identity]`  — operator-explicit; impacket allowed here
                              but `cryptography>=44.0` floor MUST hold.

Marked `@pytest.mark.slow` because each pip-resolver round-trip is
several seconds; CI invokes `pytest -m slow` separately.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _resolved_packages(extras: str, tmp_path: Path) -> dict[str, str]:
    """Run `pip install --dry-run -e <repo>[<extras>]` and parse the
    `--report` JSON to return ``{name_lower: version}``.

    Raises pytest.fail on resolver failure with the captured stderr.
    """
    report_path = tmp_path / f"report-{extras.replace(',', '_')}.json"
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--dry-run",
        "--ignore-installed",
        "--quiet",
        "--report",
        str(report_path),
        "-e",
        f"{REPO_ROOT}[{extras}]",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    if result.returncode != 0:
        pytest.fail(
            f"pip install --dry-run -e <repo>[{extras}] FAILED "
            f"(exit {result.returncode}). "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    combined = (result.stdout or "") + (result.stderr or "")
    assert f"does not provide the extra '{extras.split(',')[0]}'" not in combined, (
        f"pyproject.toml does not define the [{extras}] extras group."
    )
    assert report_path.exists(), (
        "pip --report did not write the JSON file; pip >= 22.2 required."
    )
    report = json.loads(report_path.read_text())
    out: dict[str, str] = {}
    for item in report.get("install", []):
        meta = item.get("metadata", {}) or {}
        name = (meta.get("name") or "").lower()
        ver = meta.get("version") or ""
        if name:
            out[name] = ver
    return out


def _version_ge_44(ver: str) -> bool:
    """Loose-but-correct `>= 44.0` test for the floor invariant. Splits
    on '.' and compares the leading integer component. Robust to
    cryptography's normal release shape (44.0, 44.0.1, 45.0b1)."""
    if not ver:
        return False
    head = ver.split(".", 1)[0]
    # Strip pre-release / dev suffixes (e.g., '44rc1').
    head_digits = "".join(c for c in head if c.isdigit())
    try:
        return int(head_digits) >= 44
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Case 1 — quirk[adcs]: ldap3 present, cryptography>=44.0, NO impacket.
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_adcs_extras_resolves_ldap3_cryptography44_no_impacket(tmp_path: Path) -> None:
    """ADCS-07 — `quirk[adcs]` must resolve with ldap3 + cryptography>=44.0
    and MUST NOT pull impacket (impacket transitively downgrades crypto)."""
    pkgs = _resolved_packages("adcs", tmp_path)

    assert "ldap3" in pkgs, (
        f"`ldap3` missing from quirk[adcs] resolution: {sorted(pkgs)}"
    )
    assert "cryptography" in pkgs, (
        f"`cryptography` missing from quirk[adcs] resolution: {sorted(pkgs)}"
    )
    assert _version_ge_44(pkgs["cryptography"]), (
        f"ADCS-07 floor violation: cryptography {pkgs['cryptography']} < 44.0 "
        f"in quirk[adcs]"
    )
    assert "impacket" not in pkgs, (
        "REGRESSION: impacket present in quirk[adcs] resolution — the "
        "[adcs] extras group must remain ldap3-only "
        "(Phase 45 / D-01 / Phase 80 ADCS-07). "
        f"Resolved: {sorted(pkgs)}"
    )


# ---------------------------------------------------------------------------
# Case 2 — quirk[all]: cryptography>=44.0, NO impacket (D-01 invariant).
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_all_extras_resolves_cryptography44_no_impacket(tmp_path: Path) -> None:
    """quirk[all] resolves with cryptography>=44.0 and MUST NOT contain
    impacket — the Phase 45 / D-01 guard, re-asserted for Phase 80."""
    pkgs = _resolved_packages("all", tmp_path)

    assert "cryptography" in pkgs, (
        f"`cryptography` missing from quirk[all] resolution: {sorted(pkgs)}"
    )
    assert _version_ge_44(pkgs["cryptography"]), (
        f"ADCS-07 floor violation: cryptography {pkgs['cryptography']} < 44.0 "
        f"in quirk[all]"
    )
    assert "impacket" not in pkgs, (
        "REGRESSION: impacket present in quirk[all] — Phase 45 / D-01: "
        "remove quirk[identity] from the [all] meta-extra in pyproject.toml. "
        f"Resolved: {sorted(pkgs)}"
    )
    # Sanity: [adcs] component is present (ldap3 surfaces).
    assert "ldap3" in pkgs, (
        f"quirk[all] missing ldap3 — quirk[adcs] not in [all]: {sorted(pkgs)}"
    )


# ---------------------------------------------------------------------------
# Case 3 — quirk[adcs,identity]: cryptography>=44.0 floor STILL holds.
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_adcs_plus_identity_keeps_cryptography44_floor(tmp_path: Path) -> None:
    """ADCS-07 — even when operators explicitly install
    `quirk[adcs,identity]` together (impacket allowed), `cryptography`
    must still resolve to >=44.0. This is the canary that catches
    impacket transitively downgrading cryptography in any future
    impacket release."""
    pkgs = _resolved_packages("adcs,identity", tmp_path)

    assert "cryptography" in pkgs, (
        f"`cryptography` missing from quirk[adcs,identity]: {sorted(pkgs)}"
    )
    assert _version_ge_44(pkgs["cryptography"]), (
        f"ADCS-07 floor violation: cryptography {pkgs['cryptography']} < 44.0 "
        f"in quirk[adcs,identity] — impacket may be downgrading the pin"
    )
    # ldap3 from both, plus impacket from [identity] (allowed here).
    assert "ldap3" in pkgs, f"ldap3 missing: {sorted(pkgs)}"
