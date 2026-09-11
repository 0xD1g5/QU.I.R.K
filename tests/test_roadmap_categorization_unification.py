"""Phase 201 Plan 03 — BACK-51 / LIFT-04: one-categorization-source unification gate.

Prior to this phase, two independently-derived answers to "what should I fix
and when" both reached the operator in the same report pass: the canonical
``build_phased_roadmap()`` (feeding CLI markdown, HTML, DOCX, and the
dashboard) and a second, severity-bucketed ``categorize_waves()`` that fed
ONLY the console "Migration Waves" summary table — confirmed live since
Phase 189. This file is the machine pin that closes BACK-51: it proves the
NOW/NEXT/LATER assignment for one fixture scan agrees across all four
consumer surfaces, and it guards against the second system ever quietly
reappearing (even as an unused "deprecated" stub, which is still the second
system BACK-51 exists to kill).

Sibling of tests/test_cross_surface_parity.py — mirrors its shared-fixture,
one-ExecContent shape, but is scoped to roadmap phase assignment rather than
narrative/top_risks content. Does NOT edit that file.
"""
from __future__ import annotations

from types import SimpleNamespace

import quirk.reports.writer as writer
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.intelligence.scoring import compute_readiness_score
from quirk.reports.content_model import build_exec_content, ExecContent
from quirk.reports.writer import _roadmap_markdown


# ---------------------------------------------------------------------------
# Shared fixture — spans all three phases (verified live, see canonical
# mapping recorded in 201-03-SUMMARY.md)
# ---------------------------------------------------------------------------

def _evidence() -> dict:
    return {
        "totals": {"endpoints": 10, "findings": 7},
        "protocol_counts": {"TLS": 6, "HTTP": 2, "SSH": 1, "UNKNOWN": 1},
        "plaintext_http_count": 1,
        "http_on_tls_port_count": 1,
        "mtls_present_count": 1,
        "certificate_observations": {
            "expired_count": 1,
            "expiring_count": 2,
            "self_signed_count": 1,
        },
        "cert_key_type_counts": {"RSA": 6, "ECDSA": 0},
        "scan_error": {"rate": 0.3},
        "finding_severity_counts": {
            "CRITICAL": 0,
            "HIGH": 2,
            "MEDIUM": 1,
            "LOW": 1,
            "INFO": 1,
        },
        "tls_enum_coverage_ratio": 0.7,
    }


_FINDINGS: list = []


def _canonical_roadmap() -> dict:
    """The single categorization source every surface must agree with."""
    evidence = _evidence()
    score_raw = compute_readiness_score(evidence)
    return build_phased_roadmap(evidence, score_raw)


def _canonical_phase_by_title(roadmap: dict) -> dict:
    return {item["title"]: item["phase"] for item in roadmap["items"]}


def _make_minimal_cfg():
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Roadmap Unification Test Org",
            report_owner="Unification Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_roadmap_categorization_unification"),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


_SCORE_RAW_FOR_EXEC = {
    "score": 42,
    "rating": "FAIR",
    "subscores": {
        "hygiene": 10,
        "modern_tls": 7,
        "identity_trust": 11,
        "agility_signals": 6,
        "data_at_rest": 5,
        "data_in_motion": 3,
    },
    "drivers": [
        "Weak TLS 1.0 configuration detected",
        "No PQC hybrid candidates identified",
    ],
}


# ---------------------------------------------------------------------------
# BACK-51: one categorization source, pinned across four surfaces
# ---------------------------------------------------------------------------

def test_cli_markdown_matches_canonical_phase_assignment() -> None:
    """_roadmap_markdown's NOW/NEXT/LATER section grouping agrees with
    build_phased_roadmap()'s own phase field for every title."""
    roadmap = _canonical_roadmap()
    canonical = _canonical_phase_by_title(roadmap)

    md = _roadmap_markdown(roadmap["items"])

    # Parse: which "## {tf}" heading each title's bullet line falls under.
    parsed: dict = {}
    current_phase = None
    for line in md.splitlines():
        stripped = line.strip()
        if stripped in ("## NOW", "## NEXT", "## LATER"):
            current_phase = stripped[3:]
            continue
        if stripped.startswith("- **") and current_phase:
            for title in canonical:
                if title in stripped:
                    parsed[title] = current_phase

    assert parsed == canonical, (
        f"CLI markdown phase assignment diverges from build_phased_roadmap(): "
        f"{parsed} != {canonical}"
    )


def test_html_context_split_matches_canonical_phase_assignment() -> None:
    """build_exec_content()'s RoadmapItems, split the same way html_renderer
    splits them into roadmap_now/next/later, agree with the canonical mapping."""
    roadmap = _canonical_roadmap()
    canonical = _canonical_phase_by_title(roadmap)

    exec_content: ExecContent = build_exec_content(
        score_raw=_SCORE_RAW_FOR_EXEC,
        findings=_FINDINGS,
        roadmap_items=roadmap["items"],
    )

    # Mirror html_renderer.py:1128-1130's exact split expression.
    roadmap_now = [r for r in exec_content.roadmap_items if r.phase == "NOW"]
    roadmap_next = [r for r in exec_content.roadmap_items if r.phase == "NEXT"]
    roadmap_later = [r for r in exec_content.roadmap_items if r.phase == "LATER"]

    parsed = {}
    for phase_label, items in (("NOW", roadmap_now), ("NEXT", roadmap_next), ("LATER", roadmap_later)):
        for item in items:
            parsed[item.title] = phase_label

    assert parsed == canonical, (
        f"HTML context split diverges from build_phased_roadmap(): {parsed} != {canonical}"
    )


def test_docx_split_matches_canonical_phase_assignment() -> None:
    """docx_renderer's phase-split over exec_content.roadmap_items agrees
    with the canonical mapping (same split expression as docx_renderer.py:368-370)."""
    roadmap = _canonical_roadmap()
    canonical = _canonical_phase_by_title(roadmap)

    exec_content: ExecContent = build_exec_content(
        score_raw=_SCORE_RAW_FOR_EXEC,
        findings=_FINDINGS,
        roadmap_items=roadmap["items"],
    )

    roadmap_now = [r for r in exec_content.roadmap_items if r.phase == "NOW"]
    roadmap_next = [r for r in exec_content.roadmap_items if r.phase == "NEXT"]
    roadmap_later = [r for r in exec_content.roadmap_items if r.phase == "LATER"]

    parsed = {}
    for phase_label, items in (("NOW", roadmap_now), ("NEXT", roadmap_next), ("LATER", roadmap_later)):
        for item in items:
            parsed[item.title] = phase_label

    assert parsed == canonical, (
        f"DOCX phase split diverges from build_phased_roadmap(): {parsed} != {canonical}"
    )


def test_dashboard_derive_roadmap_matches_canonical_phase_assignment() -> None:
    """_derive_roadmap()'s RoadmapNode.phase agrees with the canonical mapping."""
    from quirk.dashboard.api.routes.scan import _derive_roadmap

    evidence = _evidence()
    score_raw = compute_readiness_score(evidence)
    canonical = _canonical_phase_by_title(build_phased_roadmap(evidence, score_raw))

    roadmap_data = _derive_roadmap(evidence, score_raw)
    parsed = {node.title: node.phase for node in roadmap_data.nodes}

    assert parsed == canonical, (
        f"Dashboard _derive_roadmap phase assignment diverges from "
        f"build_phased_roadmap(): {parsed} != {canonical}"
    )


# ---------------------------------------------------------------------------
# Regression guards
# ---------------------------------------------------------------------------

def test_categorize_waves_is_gone() -> None:
    """BACK-51: reintroducing any second categorization system — including a
    deprecated, unused one — is the regression this test exists to catch.

    quirk.reports.writer must have NO `categorize_waves` attribute at all,
    not merely an unused one. A thin "adapter" that re-derives severity
    buckets is equally prohibited by CONTEXT's BACK-51 decision: deletion,
    not deprecation.
    """
    assert not hasattr(writer, "categorize_waves"), (
        "BACK-51 VIOLATION: quirk.reports.writer.categorize_waves exists again. "
        "build_phased_roadmap() must be the SOLE categorization system — "
        "no adapter, no deprecated stub."
    )


def test_console_wave_counts_match_roadmap_phase_counts() -> None:
    """The console Migration Waves table's item-per-phase counter logic
    (writer.py's console render block) must equal build_phased_roadmap()'s
    own phase_counts for the same evidence — the two must never drift."""
    roadmap = _canonical_roadmap()
    expected = roadmap["phase_counts"]

    # Mirror the writer.py console counting logic exactly (writer.py's
    # tolerant phase/timeframe idiom, post BACK-51 rewrite).
    wave_counts = {"NOW": 0, "NEXT": 0, "LATER": 0}
    for item in roadmap.get("items", []):
        phase = item.get("phase")
        if phase not in wave_counts:
            timeframe = item.get("timeframe")
            from quirk.intelligence.roadmap import _TIMEFRAME_BY_PHASE
            timeframe_to_phase = {v: k for k, v in _TIMEFRAME_BY_PHASE.items()}
            phase = timeframe if timeframe in wave_counts else timeframe_to_phase.get(timeframe)
        if phase in wave_counts:
            wave_counts[phase] += 1

    assert wave_counts == expected, (
        f"Console Migration Waves counter diverges from build_phased_roadmap() "
        f"phase_counts: {wave_counts} != {expected}"
    )
