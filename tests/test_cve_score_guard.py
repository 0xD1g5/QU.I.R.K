"""Phase 142 (CVE-04 / D-16) — permanent regression guard: CVE data must never
influence SCORE_WEIGHTS or assign_tier().

This test PASSES GREEN immediately — the invariant already holds before any
CVE code exists — and must stay green through every future phase. Explicit
phase-success-criteria text per ROADMAP.md Success Criteria #4.
"""
from __future__ import annotations

import datetime


def test_no_cve_key_in_score_weights() -> None:
    """No key in quirk.intelligence.scoring.SCORE_WEIGHTS contains the
    substring 'cve' (case-insensitive)."""
    from quirk.intelligence.scoring import SCORE_WEIGHTS

    cve_keys = [k for k in SCORE_WEIGHTS if "cve" in k.lower()]
    assert cve_keys == [], (
        f"SCORE_WEIGHTS must never contain CVE-derived keys (CVE-04): {cve_keys}"
    )


def test_assign_tier_unaffected_by_cve_attributes() -> None:
    """assign_tier() output is identical whether or not CVE-shaped attributes
    are present on the HardwareDevice — proving assign_tier structurally
    cannot read CVE data (it isn't even a parameter)."""
    from quirk.models import HardwareDevice
    from quirk.scanner.hardware_tier import assign_tier

    device = HardwareDevice.__new__(HardwareDevice)
    device.__dict__.update({
        "host": "10.0.0.1",
        "port": 22,
        "vendor": "Cisco",
        "model": "IOS",
        "pqc_status": "unsupported",
        "confidence": "high",
        "eol_date": None,
        "fingerprint_method": "ssh_banner",
    })

    tier_before = assign_tier(device)

    # Inject arbitrary CVE-shaped attributes onto the same device instance.
    device.cve_matches = [
        {"cve_id": "CVE-2017-12240", "severity": "CRITICAL"},
    ]
    device.cve_confidence = "high"
    device.__dict__["cve_matches"] = device.cve_matches
    device.__dict__["cve_confidence"] = device.cve_confidence

    tier_after = assign_tier(device)

    assert tier_before == tier_after, (
        f"assign_tier() output changed after injecting CVE data: "
        f"{tier_before!r} -> {tier_after!r} (CVE-04 invariant violated)"
    )
