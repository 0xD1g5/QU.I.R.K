"""Phase 142 (CVE-04 / D-16) — permanent regression guard: CVE data must never
influence SCORE_WEIGHTS or assign_tier().

This test PASSES GREEN immediately — the invariant already holds before any
CVE code exists — and must stay green through every future phase. Explicit
phase-success-criteria text per ROADMAP.md Success Criteria #4.

Phase 155 (T-155-01) extends this file's guard to the two new hardware
lifecycle modules — ``hardware_drift`` and ``hardware_eol`` — so this file
now guards the advisory-only firewall for hw_cve, hardware_drift, and
hardware_eol as one machine-enforced boundary.
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


# ---------------------------------------------------------------------------
# Phase 155 (T-155-01) — advisory-only firewall extended to hardware_drift
# and hardware_eol
# ---------------------------------------------------------------------------


def test_no_drift_or_eol_key_in_score_weights() -> None:
    """No key in quirk.intelligence.scoring.SCORE_WEIGHTS contains the
    substring 'drift', 'eol', or 'eos' (case-insensitive)."""
    from quirk.intelligence.scoring import SCORE_WEIGHTS

    bad_keys = [
        k for k in SCORE_WEIGHTS
        if any(term in k.lower() for term in ("drift", "eol", "eos"))
    ]
    assert bad_keys == [], (
        f"SCORE_WEIGHTS must never contain drift/eol/eos-derived keys "
        f"(T-155-01): {bad_keys}"
    )


def test_scoring_module_does_not_import_drift_or_eol() -> None:
    """The source of quirk/intelligence/scoring.py contains no import of
    hardware_drift, hardware_eol, or HardwareDriftEvent."""
    import pathlib

    import quirk.intelligence.scoring as scoring_module

    source = pathlib.Path(scoring_module.__file__).read_text()
    for forbidden in ("hardware_drift", "hardware_eol", "HardwareDriftEvent"):
        assert forbidden not in source, (
            f"quirk/intelligence/scoring.py must never reference {forbidden!r} "
            f"(T-155-01 advisory-only firewall)"
        )


def test_assign_tier_unaffected_by_drift_attributes() -> None:
    """assign_tier(device) output is identical whether or not drift-event-
    shaped attributes are attached to the device — proving assign_tier
    structurally cannot read drift-candidate data."""
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

    # Inject arbitrary drift-shaped attributes (e.g. a list of
    # DriftCandidate-like objects) onto the same device instance.
    device.drift_candidates = [
        {"event_type": "tier_crossing", "old_value": "Tier 2", "new_value": "Tier 1"},
    ]
    device.drift_events = ["some-event"]
    device.__dict__["drift_candidates"] = device.drift_candidates
    device.__dict__["drift_events"] = device.drift_events

    tier_after = assign_tier(device)

    assert tier_before == tier_after, (
        f"assign_tier() output changed after injecting drift-candidate data: "
        f"{tier_before!r} -> {tier_after!r} (T-155-01 invariant violated)"
    )


def test_assign_tier_eol_override_is_intentional() -> None:
    """assign_tier(device) DOES change when eol_date is set to a pre-2030
    date. This is INTENTIONAL, pre-existing Phase 128 assign_tier() EOL
    override behavior (hardware_tier.py: eol_date < 2030-01-01 forces
    "Tier N/A", D-18) that Phase 155's EOL catalog now actually triggers for
    real devices — it is an intentional, documented interaction, NOT an
    advisory-boundary violation of T-155-01 (which guards SCORE_WEIGHTS and
    scoring.py imports, not assign_tier()'s own long-standing EOL input)."""
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

    tier_before_eol = assign_tier(device)

    device.__dict__["eol_date"] = datetime.date(2027, 1, 1)
    tier_after_eol = assign_tier(device)

    assert tier_after_eol == "Tier N/A", (
        f"Expected assign_tier() to force 'Tier N/A' for a pre-2030 eol_date "
        f"(pre-existing Phase 128 D-18 behavior), got {tier_after_eol!r}"
    )
    assert tier_before_eol != tier_after_eol
