"""Phase 142 (CVE-04 / D-16) — permanent regression guard: CVE data must never
influence SCORE_WEIGHTS or assign_tier().

This test PASSES GREEN immediately — the invariant already holds before any
CVE code exists — and must stay green through every future phase. Explicit
phase-success-criteria text per ROADMAP.md Success Criteria #4.

Phase 155 (T-155-01) extends this file's guard to the two new hardware
lifecycle modules — ``hardware_drift`` and ``hardware_eol`` — so this file
now guards the advisory-only firewall for hw_cve, hardware_drift, and
hardware_eol as one machine-enforced boundary.

Phase 157 (T-157-05) extends the guard again to ``hardware_forecast`` — the
new EOL/tier forecast narrative module — by name.
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


# ---------------------------------------------------------------------------
# Phase 156 (T-156-04 / D-08) — advisory-only firewall extended to the
# drift-rendering surfaces
# ---------------------------------------------------------------------------


def _strip_comment_lines(source: str) -> str:
    """Strips '#'-comment-only lines before a substring search, so a future
    explanatory comment in a guarded module cannot self-invalidate the gate."""
    return "\n".join(
        line for line in source.splitlines() if not line.strip().startswith("#")
    )


def test_drift_report_modules_have_no_score_weights_reference() -> None:
    """No comment-stripped source of html_renderer.py, docx_renderer.py, or
    the hardware_drift route module references SCORE_WEIGHTS."""
    import pathlib

    import quirk.reports.html_renderer as html_renderer_module
    import quirk.reports.docx_renderer as docx_renderer_module

    # Lazy import inside the test (per plan instruction) so a collection-time
    # import failure in an unrelated dashboard dependency cannot take the
    # guard down.
    import quirk.dashboard.api.routes.hardware_drift as hardware_drift_route_module

    for module in (html_renderer_module, docx_renderer_module, hardware_drift_route_module):
        source = _strip_comment_lines(pathlib.Path(module.__file__).read_text())
        assert "SCORE_WEIGHTS" not in source, (
            f"{module.__file__} must never reference SCORE_WEIGHTS (T-156-04)"
        )


def test_drift_report_modules_do_not_import_scoring() -> None:
    """No comment-stripped source of html_renderer.py, docx_renderer.py, or
    the hardware_drift route module imports the scoring engine or the
    readiness-assessment module."""
    import pathlib

    import quirk.reports.html_renderer as html_renderer_module
    import quirk.reports.docx_renderer as docx_renderer_module
    import quirk.dashboard.api.routes.hardware_drift as hardware_drift_route_module

    for module in (html_renderer_module, docx_renderer_module, hardware_drift_route_module):
        source = _strip_comment_lines(pathlib.Path(module.__file__).read_text())
        for forbidden in ("quirk.intelligence.scoring", "quirk.assessment.readiness_score"):
            assert forbidden not in source, (
                f"{module.__file__} must never import {forbidden!r} (T-156-04)"
            )


def test_no_drift_report_key_in_score_weights() -> None:
    """No key in quirk.intelligence.scoring.SCORE_WEIGHTS contains the
    substring 'lifecycle' or 'drift' (case-insensitive) — extends the
    Phase 155 assertion to the Phase 156 reporting vocabulary."""
    from quirk.intelligence.scoring import SCORE_WEIGHTS

    bad_keys = [
        k for k in SCORE_WEIGHTS
        if any(term in k.lower() for term in ("lifecycle", "drift"))
    ]
    assert bad_keys == [], (
        f"SCORE_WEIGHTS must never contain lifecycle/drift-derived keys "
        f"(T-156-04): {bad_keys}"
    )


# ---------------------------------------------------------------------------
# Phase 157 (HWLC-18 / T-157-05) — advisory-only firewall extended to the
# forecast module by name.
#
# NOTE: quirk/reports/executive.py is deliberately NOT added to the module
# sets below. 157-PATTERNS.md proposed adding it, but executive.py
# legitimately imports and calls compute_readiness_score (it renders the
# actual readiness score) — including it here would fail test 4 below by
# construction. This mirrors the existing Phase 155/156 guards, which
# exclude executive.py for the identical reason. executive.py's forecast
# rendering is instead constrained by Plan 04's own render tests plus the
# build_eol_forecast signature test in tests/test_hardware_forecast.py.
# ---------------------------------------------------------------------------


def test_no_forecast_key_in_score_weights() -> None:
    """No key in quirk.intelligence.scoring.SCORE_WEIGHTS contains the
    substring 'forecast' (case-insensitive). The 'eol' vocabulary is
    already covered by test_no_drift_or_eol_key_in_score_weights."""
    from quirk.intelligence.scoring import SCORE_WEIGHTS

    bad_keys = [k for k in SCORE_WEIGHTS if "forecast" in k.lower()]
    assert bad_keys == [], (
        f"SCORE_WEIGHTS must never contain forecast-derived keys "
        f"(T-157-05): {bad_keys}"
    )


def test_scoring_module_does_not_import_forecast() -> None:
    """The comment-stripped source of quirk/intelligence/scoring.py contains
    no reference to hardware_forecast or build_eol_forecast."""
    import pathlib

    import quirk.intelligence.scoring as scoring_module

    source = _strip_comment_lines(pathlib.Path(scoring_module.__file__).read_text())
    for forbidden in ("hardware_forecast", "build_eol_forecast"):
        assert forbidden not in source, (
            f"quirk/intelligence/scoring.py must never reference {forbidden!r} "
            f"(T-157-05 advisory-only firewall)"
        )


def test_forecast_modules_have_no_score_weights_reference() -> None:
    """No comment-stripped source of hardware_forecast.py, html_renderer.py,
    or docx_renderer.py references SCORE_WEIGHTS."""
    import pathlib

    import quirk.scanner.hardware_forecast as hardware_forecast_module
    import quirk.reports.html_renderer as html_renderer_module
    import quirk.reports.docx_renderer as docx_renderer_module

    for module in (
        hardware_forecast_module,
        html_renderer_module,
        docx_renderer_module,
    ):
        source = _strip_comment_lines(pathlib.Path(module.__file__).read_text())
        assert "SCORE_WEIGHTS" not in source, (
            f"{module.__file__} must never reference SCORE_WEIGHTS (T-157-05)"
        )


def test_forecast_modules_do_not_import_scoring() -> None:
    """No comment-stripped source of hardware_forecast.py, html_renderer.py,
    or docx_renderer.py imports the scoring engine or readiness-assessment
    module."""
    import pathlib

    import quirk.scanner.hardware_forecast as hardware_forecast_module
    import quirk.reports.html_renderer as html_renderer_module
    import quirk.reports.docx_renderer as docx_renderer_module

    for module in (
        hardware_forecast_module,
        html_renderer_module,
        docx_renderer_module,
    ):
        source = _strip_comment_lines(pathlib.Path(module.__file__).read_text())
        for forbidden in ("quirk.intelligence.scoring", "quirk.assessment.readiness_score"):
            assert forbidden not in source, (
                f"{module.__file__} must never import {forbidden!r} (T-157-05)"
            )


def test_forecast_module_does_not_import_drift_events() -> None:
    """The comment-stripped source of hardware_forecast.py contains neither
    HardwareDriftEvent nor hardware_drift (D-01 forward-only invariant —
    new, no prior analog in this file)."""
    import pathlib

    import quirk.scanner.hardware_forecast as hardware_forecast_module

    source = _strip_comment_lines(
        pathlib.Path(hardware_forecast_module.__file__).read_text()
    )
    for forbidden in ("HardwareDriftEvent", "hardware_drift"):
        assert forbidden not in source, (
            f"quirk/scanner/hardware_forecast.py must never reference {forbidden!r} "
            f"(T-157-05 D-01 forward-only invariant)"
        )
