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

Phase 181 (ADVISORY-01, plan 181-07) extends the guard a final time, to close
out a requirement standing since Phase 177: remediation/closure/burndown
state must never feed the quantum-readiness score. This is a DIFFERENT guard
from ``tests/test_remediation_advisory_guard.py`` — that file is an AST
import-walk scoped to ``quirk/intelligence/*`` by its own directory-anchor
constant, and Phase 181 adds no module there, so its floor does not rise.
Phase 181's new surfaces (VEX impact-state mapping in
``quirk/cbom/builder.py``, and burndown rendering in ``quirk/reports/*`` and
``quirk/dashboard/api/routes/scan.py``) land exactly in THIS file's existing
report/CBOM/dashboard scope, following the same template as the Phase 155-160
blocks above. Two of those surfaces — ``quirk/reports/writer.py`` and
``quirk/dashboard/api/routes/scan.py`` — legitimately call
``compute_readiness_score``/``build_evidence_summary`` (computing the score
is part of their job, the same reason ``executive.py`` is excluded from the
Phase 157 block above), so they are guarded at the AST call-argument level
instead of by the strict "no scoring reference" form.
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


# Phase 160 HWLC-17: the new GET /hardware/vendor-trends endpoint lives in
# this same route module, so it already rides the guards below by name.


def test_vendor_trend_route_has_no_score_weights_reference() -> None:
    """The comment-stripped source of the hardware_drift route module
    contains the vendor-trends route literal but never SCORE_WEIGHTS — pins
    that the endpoint stays under this firewall's coverage (Phase 160
    HWLC-17 / T-160-04)."""
    import pathlib

    import quirk.dashboard.api.routes.hardware_drift as hardware_drift_route_module

    source = _strip_comment_lines(pathlib.Path(hardware_drift_route_module.__file__).read_text())
    assert "/hardware/vendor-trends" in source
    assert "SCORE_WEIGHTS" not in source


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


# ---------------------------------------------------------------------------
# Phase 160 (HWLC-17 / T-160-04) — advisory-only firewall over the catalog-level
# vendor PQC trend surface.
#
# Phase 161 (HWLC-19 / T-161-22) widened the module tuple to every surface that
# now renders vendor-trend content. quirk.reports.technical was previously
# excluded because the file carried no hardware content at all; plan 161-02
# (D-09) added the CLI vendor-trend section, so it is in scope from Phase 161
# onward. html_renderer and docx_renderer joined for the same reason via plan
# 161-05, and the Phase 160 dashboard route — formerly covered "separately" —
# is folded in here so a single tuple is the whole firewall.
# ---------------------------------------------------------------------------

# Every module that renders or serves vendor-trend content. Adding a new
# vendor-trend surface without adding it here is the failure this guard exists
# to prevent.
_VENDOR_TREND_SURFACE_MODULES = (
    "quirk.scanner.hardware_drift",
    "quirk.models_util",
    "quirk.reports.technical",              # Phase 161 / 161-02 D-09 — CLI section
    "quirk.reports.html_renderer",          # Phase 161 / 161-05 — HTML section
    "quirk.reports.docx_renderer",          # Phase 161 / 161-05 — DOCX section
    "quirk.dashboard.api.routes.hardware_drift",  # Phase 160 — vendor-trends route
)


def _vendor_trend_surface_sources():
    """Yield (module_path, comment-stripped source) for every guarded surface.

    Sources are read through _strip_comment_lines() so an explanatory comment
    naming SCORE_WEIGHTS can neither satisfy nor break the gate (T-161-23).
    """
    import importlib
    import pathlib

    for name in _VENDOR_TREND_SURFACE_MODULES:
        module = importlib.import_module(name)
        yield module.__file__, _strip_comment_lines(
            pathlib.Path(module.__file__).read_text(encoding="utf-8")
        )


def test_vendor_trend_modules_have_no_score_weights_reference() -> None:
    """No comment-stripped source of any vendor-trend surface references
    SCORE_WEIGHTS.

    Covers quirk.scanner.hardware_drift, quirk.models_util,
    quirk.reports.technical, quirk.reports.html_renderer,
    quirk.reports.docx_renderer and quirk.dashboard.api.routes.hardware_drift
    (T-160-04, widened by Phase 161 T-161-22).
    """
    for module_path, source in _vendor_trend_surface_sources():
        assert "SCORE_WEIGHTS" not in source, (
            f"{module_path} must never reference SCORE_WEIGHTS "
            f"(T-160-04 / T-161-22)"
        )


def test_vendor_trend_modules_do_not_import_scoring() -> None:
    """No comment-stripped source of any vendor-trend surface imports the
    scoring engine or the readiness-assessment module.

    Same widened module set as
    test_vendor_trend_modules_have_no_score_weights_reference — a surface that
    cannot name SCORE_WEIGHTS but imports the scoring package outright would
    defeat the firewall just as thoroughly (T-160-04 / T-161-22).
    """
    for module_path, source in _vendor_trend_surface_sources():
        for forbidden in ("quirk.intelligence.scoring", "quirk.assessment.readiness_score"):
            assert forbidden not in source, (
                f"{module_path} must never import {forbidden!r} "
                f"(T-160-04 / T-161-22)"
            )


def test_no_vendor_trend_key_in_score_weights() -> None:
    """No key in quirk.intelligence.scoring.SCORE_WEIGHTS contains the
    substring 'vendor_trend', 'pqc_trend', or 'vendor_pqc' (case-insensitive)
    — extends the existing lifecycle/drift/forecast key assertions to
    Phase 160's vocabulary."""
    from quirk.intelligence.scoring import SCORE_WEIGHTS

    bad_keys = [
        k for k in SCORE_WEIGHTS
        if any(term in k.lower() for term in ("vendor_trend", "pqc_trend", "vendor_pqc"))
    ]
    assert bad_keys == [], (
        f"SCORE_WEIGHTS must never contain vendor-trend-derived keys "
        f"(T-160-04): {bad_keys}"
    )


# ---------------------------------------------------------------------------
# Phase 181 (ADVISORY-01 / plan 181-07) — advisory-only firewall extended to
# the closure/burndown surfaces.
#
# This is NOT the same guard file as tests/test_remediation_advisory_guard.py.
# That file is an AST import-walk over quirk/intelligence/* (5 modules after
# Phase 180). Phase 181 adds NO module under quirk/intelligence/, so that
# file's floor does not rise and it is not touched by this plan. Phase 181's
# new code lives in report, CBOM, and dashboard modules — exactly this file's
# existing scope — so this is the file that closes ADVISORY-01.
# ---------------------------------------------------------------------------

# The four Phase 181 surfaces with NO legitimate scoring dependency. Adding a
# new closure/burndown-rendering surface without adding it here is the
# failure this guard exists to prevent.
_BURNDOWN_SURFACE_MODULES = (
    "quirk.cbom.builder",             # Plan 181-03 — VEX impact-state mapping
    "quirk.reports.technical",        # Plan 181-06 — CLI burndown section
    "quirk.reports.html_renderer",    # Plan 181-06 — HTML burndown section
    "quirk.reports.docx_renderer",    # Plan 181-06 — DOCX burndown section
)


def _burndown_surface_sources():
    """Yield (module_path, comment-stripped source) for every Phase 181
    zero-scoring-dependency surface.

    Sources are read through _strip_comment_lines() so an explanatory
    comment naming SCORE_WEIGHTS can neither satisfy nor break the gate
    (mirrors T-161-23 / T-181-22).
    """
    import importlib
    import pathlib

    for name in _BURNDOWN_SURFACE_MODULES:
        module = importlib.import_module(name)
        yield module.__file__, _strip_comment_lines(
            pathlib.Path(module.__file__).read_text(encoding="utf-8")
        )


def test_no_closure_key_in_score_weights() -> None:
    """No key in quirk.intelligence.scoring.SCORE_WEIGHTS contains the
    substring 'closure', 'burndown', 'remediation', 'not_observed', or
    'resurfaced' (case-insensitive). ADVISORY-01: closure state moving the
    readiness score would let remediation activity change a client's score
    with no cryptographic posture change."""
    from quirk.intelligence.scoring import SCORE_WEIGHTS

    bad_keys = [
        k for k in SCORE_WEIGHTS
        if any(
            term in k.lower()
            for term in ("closure", "burndown", "remediation", "not_observed", "resurfaced")
        )
    ]
    assert bad_keys == [], (
        f"SCORE_WEIGHTS must never contain closure/burndown-derived keys "
        f"(ADVISORY-01): closure state moving the score would let "
        f"remediation activity change a client's score with no "
        f"cryptographic posture change: {bad_keys}"
    )


def test_burndown_surface_modules_have_no_score_weights_reference() -> None:
    """No comment-stripped source of quirk.cbom.builder,
    quirk.reports.technical, quirk.reports.html_renderer, or
    quirk.reports.docx_renderer references SCORE_WEIGHTS (ADVISORY-01):
    closure state moving the readiness score would let remediation activity
    change a client's score with no cryptographic posture change."""
    for module_path, source in _burndown_surface_sources():
        assert "SCORE_WEIGHTS" not in source, (
            f"{module_path} must never reference SCORE_WEIGHTS (ADVISORY-01): "
            f"closure state moving the score would let remediation activity "
            f"change a client's score with no cryptographic posture change"
        )


def test_burndown_surface_modules_do_not_import_scoring() -> None:
    """No comment-stripped source of quirk.cbom.builder,
    quirk.reports.technical, quirk.reports.html_renderer, or
    quirk.reports.docx_renderer imports the scoring engine or the
    readiness-assessment module (ADVISORY-01): closure state moving the
    readiness score would let remediation activity change a client's score
    with no cryptographic posture change."""
    for module_path, source in _burndown_surface_sources():
        for forbidden in ("quirk.intelligence.scoring", "quirk.assessment.readiness_score"):
            assert forbidden not in source, (
                f"{module_path} must never import {forbidden!r} (ADVISORY-01): "
                f"closure state moving the score would let remediation "
                f"activity change a client's score with no cryptographic "
                f"posture change"
            )


def test_scoring_module_does_not_reference_closure_or_burndown() -> None:
    """The comment-stripped source of quirk/intelligence/scoring.py
    references none of compute_burndown, RemediationItem, closure, burndown
    — the scoring module never reaches back toward the closure substrate
    (ADVISORY-01): closure state moving the readiness score would let
    remediation activity change a client's score with no cryptographic
    posture change."""
    import pathlib

    import quirk.intelligence.scoring as scoring_module

    source = _strip_comment_lines(pathlib.Path(scoring_module.__file__).read_text())
    for forbidden in ("compute_burndown", "RemediationItem", "closure", "burndown"):
        assert forbidden not in source, (
            f"quirk/intelligence/scoring.py must never reference {forbidden!r} "
            f"(ADVISORY-01): closure state moving the score would let "
            f"remediation activity change a client's score with no "
            f"cryptographic posture change"
        )


# The two Phase 181 surfaces that DO legitimately compute a score. The
# strict "no scoring reference" form above cannot apply to these — they
# legitimately import and call compute_readiness_score()/
# build_evidence_summary() as part of their actual job (the same reason
# executive.py is excluded from the Phase 157 block above). What is guarded
# instead is the DATA PATH: no closure or burndown name may appear inside
# the evidence-construction or score-computation call itself.
_SCORE_COMPUTING_MODULES = (
    "quirk.reports.writer",
    "quirk.dashboard.api.routes.scan",
)

# Phase 181 names that must never reach a score input (ADVISORY-01).
_PHASE_181_CLOSURE_NAMES = (
    "burndown",
    "closure_refusal",
    "closure_counters",
    "compute_burndown",
    "_load_closure_burndown",
    "_load_remediation_items",
    "_derive_closure_burndown",
    "remediation_items",
    "closure_state",
    "not_observed",
    "resurfaced",
)


def test_closure_names_never_enter_the_score_call_path() -> None:
    """For each of quirk.reports.writer and
    quirk.dashboard.api.routes.scan, every compute_readiness_score(...) and
    build_evidence_summary(...) call node's source segment contains none of
    the Phase 181 closure/burndown names. Asserts at least one such call
    node is found per module, so a refactor that renames or removes the
    call fails loudly rather than passing vacuously (ADVISORY-01)."""
    import ast
    import importlib
    import pathlib

    for module_name in _SCORE_COMPUTING_MODULES:
        module = importlib.import_module(module_name)
        source = pathlib.Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)

        call_count = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            func_name = None
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr
            if func_name not in ("compute_readiness_score", "build_evidence_summary"):
                continue
            call_count += 1
            segment = ast.get_source_segment(source, node) or ""
            for forbidden in _PHASE_181_CLOSURE_NAMES:
                assert forbidden not in segment, (
                    f"{module.__file__}: a compute_readiness_score/"
                    f"build_evidence_summary call contains forbidden name "
                    f"{forbidden!r} (ADVISORY-01): closure state moving the "
                    f"readiness score would let remediation activity change "
                    f"a client's score with no cryptographic posture "
                    f"change: {segment!r}"
                )

        # Vacuous-pass guard: a rename or removal of the scoring call must
        # fail loudly, not silently pass by finding nothing.
        assert call_count >= 1, (
            f"{module.__file__}: expected at least 1 compute_readiness_score/"
            f"build_evidence_summary call node, found {call_count} — the "
            f"guard cannot verify a call path that no longer exists "
            f"(ADVISORY-01)"
        )


def test_exec_content_burndown_never_reaches_findings_evaluation() -> None:
    """The comment-stripped source of quirk/reports/writer.py never passes
    'burndown' or 'closure_refusal' into any call whose name contains
    'finding' (ADVISORY-01): the absent severity key on burndown/closure
    data is the structural mechanism that keeps it out of findings
    evaluation; this asserts the mechanism is actually relied upon rather
    than merely present."""
    import ast
    import importlib
    import pathlib

    module = importlib.import_module("quirk.reports.writer")
    source = pathlib.Path(module.__file__).read_text(encoding="utf-8")
    stripped_source = _strip_comment_lines(source)
    tree = ast.parse(stripped_source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        func_name = None
        if isinstance(func, ast.Name):
            func_name = func.id
        elif isinstance(func, ast.Attribute):
            func_name = func.attr
        if not func_name or "finding" not in func_name.lower():
            continue
        segment = ast.get_source_segment(stripped_source, node) or ""
        for forbidden in ("burndown", "closure_refusal"):
            assert forbidden not in segment, (
                f"quirk/reports/writer.py: a call to {func_name!r} (contains "
                f"'finding') contains forbidden name {forbidden!r} "
                f"(ADVISORY-01): closure/burndown data must never reach "
                f"findings evaluation: {segment!r}"
            )
