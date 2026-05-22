"""Phase 88 D-05/D-06 / SCORE-CBOM-01: Zero-algo profile coverage gate.

Resolves Phase 42 OBS-1 — five chaos lab profiles that previously emitted
zero algorithm components now either:
  - D-05: emit REAL algorithm components (crypto the scanners ALREADY observe), or
  - D-06: carry an affirmative quirk:coverage-note property on the Bom root
          component (for genuinely plaintext / library-only endpoints).

This parametrized test forward-locks that contract in perpetuity. A profile
that satisfies neither condition violates SCORE-CBOM-01.

Security note (T-88-03): quirk:coverage-note values are HARDCODED string
literals in builder.py — never scanner-derived input.
"""
from __future__ import annotations

import pytest

from quirk.cbom.builder import build_cbom
from tests._cbom_profiles import PROFILE_ENDPOINTS


@pytest.mark.parametrize("profile", [
    "database",
    "registry",
    "source",
    "ssh-weak",
    "storage-s3",
])
def test_zero_algo_profile_emits_components_or_marker(profile: str) -> None:
    """SCORE-CBOM-01: Five formerly-zero-algo profiles must now either emit
    real algorithm components (D-05) OR carry an affirmative quirk:coverage-note
    property on the Bom root component (D-06 marker convention).

    Failure means Phase 42 OBS-1 is not resolved for this profile — add real
    algorithm components (D-05) or an affirmative hardcoded marker (D-06).
    """
    fn = PROFILE_ENDPOINTS[profile]
    bom = build_cbom(fn())

    # Collect algorithm component names
    algo_names = [
        c.name for c in bom.components
        if getattr(c, "crypto_properties", None)
        and c.crypto_properties.asset_type.value == "algorithm"
    ]

    # Collect quirk:coverage-note properties from the Bom root component (D-06)
    coverage_notes: list[str] = []
    if bom.metadata and bom.metadata.component:
        for prop in (bom.metadata.component.properties or []):
            if prop.name == "quirk:coverage-note":
                coverage_notes.append(prop.value)

    assert algo_names or coverage_notes, (
        f"Profile '{profile}' emits zero algorithm components and has no "
        f"quirk:coverage-note property — Phase 42 OBS-1 not resolved. "
        f"Add real components (D-05) or an affirmative hardcoded marker (D-06)."
    )


def test_ssh_weak_emits_real_weak_algorithm_components() -> None:
    """D-05 gate: ssh-weak profile must emit the specific weak algorithms that
    ssh-audit observes — not just a synthetic placeholder.

    The fixture now carries realistic ssh_audit_json so the SSH builder branch
    registers diffie-hellman-group1-sha1, ssh-dss, and hmac-md5.
    """
    fn = PROFILE_ENDPOINTS["ssh-weak"]
    bom = build_cbom(fn())

    algo_names = {
        c.name for c in bom.components
        if getattr(c, "crypto_properties", None)
        and c.crypto_properties.asset_type.value == "algorithm"
    }

    for expected in ("diffie-hellman-group1-sha1", "ssh-dss", "hmac-md5"):
        assert expected in algo_names, (
            f"ssh-weak profile missing expected weak algorithm '{expected}'. "
            f"Got: {sorted(algo_names)}. "
            "Ensure _build_ssh_weak_lab_endpoints ssh_audit_json includes this algorithm "
            "and classifier._ALGORITHM_TABLE has a non-UNKNOWN entry for it (D-05)."
        )
