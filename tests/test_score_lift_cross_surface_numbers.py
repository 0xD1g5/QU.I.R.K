"""Phase 201 Plan 07 (LIFT-02/LIFT-05) — four-surface score-lift numeric
equality, machine-checked rather than assumed from a shared content model.

Scope note (calibration asymmetry, deliberate and out of scope for Phase
201): this suite pins ONE (profile, weights=None) pair across all four
surfaces — CLI markdown, HTML, DOCX, and the dashboard `_derive_roadmap`
payload. `weights=None` is not a simplification; it is required, because
`quirk/dashboard/api/routes/scan.py::_derive_roadmap` (per 201-04's design)
exposes only a keyword-only `profile` parameter with NO `weights` argument at
all — mirroring the endpoint's own `compute_readiness_score(evidence,
profile=stored_profile)` call, which also passes no weights. A non-None
weights value could therefore never be held constant on the dashboard
surface. The pre-existing asymmetry between `writer.py`/`executive.py`
(profile + `calibration_overrides`) and `routes/scan.py` (profile only) —
RESEARCH Pitfall 4 — is real, pre-existing, and explicitly out of scope for
Phase 201. A real-world difference between surfaces run under DIFFERENT
calibration is therefore expected and is NOT what this test guards against;
this test only guards the case where all four surfaces are given the SAME
calibration input and must then agree numerically.

Node IDs:
  test_four_surfaces_report_identical_per_item_lifts
  test_four_surfaces_report_identical_projected_aggregate
  test_projected_aggregate_equals_independent_rescore
  test_surface_visible_non_additivity_on_clamp_binding_fixture
  test_unmodelable_item_shows_no_number_on_any_surface
"""
from __future__ import annotations

import copy
import os
import re
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from quirk.dashboard.api.routes.scan import _derive_roadmap
from quirk.intelligence.remediation import slug_for_title
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.intelligence.score_lift import compute_item_lifts, compute_projected_score
from quirk.intelligence.scoring import compute_readiness_score
from quirk.reports.content_model import build_exec_content
from quirk.reports.docx_renderer import render_docx_report
from quirk.reports.html_renderer import render_html_report
from quirk.reports.writer import _roadmap_markdown

# Reuse plan 201-01/201-02's fixtures verbatim rather than retuning them here.
from tests.test_score_lift import _clamp_binding_evidence, _evidence

_PROFILE = "balanced"  # the pinned (profile, weights=None) pair, per module docstring


def _make_cfg(tmp_path) -> SimpleNamespace:
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Cross-Surface Numbers Test Org",
            report_owner="Numbers Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory=str(tmp_path)),
        intelligence=SimpleNamespace(profile=_PROFILE, calibration_overrides=None),
    )


def _build_all_surfaces(evidence: Dict[str, Any], tmp_path):
    """Drive all four surfaces from ONE evidence fixture and ONE (profile,
    weights=None) pair, mirroring the real writer.py/scan.py attachment
    seams (fetch lifts once, join by slug, attach to item dicts) rather than
    inventing a shortcut shape.

    Returns (items, exec_content, cli_md, html_text, docx_action_cells,
    dashboard_nodes, dashboard_projected).
    """
    score_raw = compute_readiness_score(evidence, profile=_PROFILE)
    items = build_phased_roadmap(evidence, score_raw)["items"]

    # writer.py's own None-vs-omitted-key contract (201-05): OMIT the key
    # rather than setting it to None.
    lifts_by_slug = compute_item_lifts(evidence, items, profile=_PROFILE)
    for item in items:
        slug = slug_for_title(item.get("title"))
        if slug is not None and slug in lifts_by_slug:
            item["score_lift"] = lifts_by_slug[slug]

    projected = compute_projected_score(evidence, items, profile=_PROFILE)

    exec_content = build_exec_content(
        score_raw=score_raw, findings=[], roadmap_items=items, projected_score=projected
    )

    # --- CLI markdown surface ---
    cli_md = _roadmap_markdown(items, projected)

    # --- HTML surface ---
    cfg = _make_cfg(tmp_path)
    html_path = os.path.join(str(tmp_path), "cross-surface.html")
    render_html_report(
        html_path, cfg, [], [], score_raw, {"confidence": 60}, items, exec_content=exec_content
    )
    html_text = open(html_path, encoding="utf-8").read()

    # --- DOCX surface ---
    docx_path = os.path.join(str(tmp_path), "cross-surface.docx")
    render_docx_report(docx_path, cfg, [], exec_content)
    from docx import Document

    doc = Document(docx_path)
    docx_action_cells: List[str] = []
    for tbl in doc.tables:
        headers = [c.text for c in tbl.rows[0].cells]
        if headers[:2] == ["Phase", "Action"]:
            for row in tbl.rows[1:]:
                docx_action_cells.append(row.cells[1].text)
    docx_paragraphs = [p.text for p in doc.paragraphs]

    # --- Dashboard surface ---
    # Mirrors routes/scan.py's endpoint: _derive_roadmap gives per-node lifts
    # (profile only, no weights — the parameter does not exist on this
    # surface); the projected aggregate is a SEPARATE call the endpoint makes
    # itself via a second build_phased_roadmap + compute_projected_score,
    # since _derive_roadmap's return type stays RoadmapData-only (201-04
    # key-decision).
    dashboard_data = _derive_roadmap(evidence, score_raw, profile=_PROFILE)
    dashboard_projection_items = build_phased_roadmap(evidence, score_raw).get("items", [])
    dashboard_projected = compute_projected_score(
        evidence, dashboard_projection_items, profile=_PROFILE
    )

    return (
        items,
        exec_content,
        cli_md,
        html_text,
        docx_action_cells,
        docx_paragraphs,
        dashboard_data.nodes,
        dashboard_projected,
    )


def _extract_cli_lift(cli_md: str, title: str) -> Optional[int]:
    for line in cli_md.splitlines():
        if f"**{title}**" in line:
            m = re.search(r"\(\+(\d+) pts\)", line)
            return int(m.group(1)) if m else None
    raise AssertionError(f"title {title!r} not found in CLI markdown")


def _extract_html_lift(html_text: str, title: str) -> Optional[int]:
    m = re.search(r"<strong>" + re.escape(title) + r"</strong>(.*?)</div>", html_text, re.DOTALL)
    assert m, f"title {title!r} not found in HTML output"
    lift_m = re.search(r"\(\+(\d+) pts\)", m.group(1))
    return int(lift_m.group(1)) if lift_m else None


def _extract_docx_lift(docx_action_cells: List[str], title: str) -> Optional[int]:
    for cell in docx_action_cells:
        if cell == title or cell.startswith(title + " ("):
            m = re.search(r"\(\+(\d+) pts\)", cell)
            return int(m.group(1)) if m else None
    raise AssertionError(f"title {title!r} not found in DOCX action cells: {docx_action_cells}")


def _dashboard_lift_by_title(nodes) -> Dict[str, Optional[float]]:
    return {n.title: n.score_lift for n in nodes}


# ---------------------------------------------------------------------------
# Fixture-shape prerequisite (not a behavior pin) — the four-surface equality
# test needs at least 3 modelable items and at least 1 unmodelable item to be
# meaningful.
# ---------------------------------------------------------------------------


def test_fixture_has_at_least_three_modelable_and_one_unmodelable_item(tmp_path):
    evidence = _evidence()
    score_raw = compute_readiness_score(evidence, profile=_PROFILE)
    items = build_phased_roadmap(evidence, score_raw)["items"]
    lifts_by_slug = compute_item_lifts(evidence, items, profile=_PROFILE)
    modelable = [it for it in items if slug_for_title(it["title"]) in lifts_by_slug]
    unmodelable = [it for it in items if slug_for_title(it["title"]) not in lifts_by_slug]
    assert len(modelable) >= 3, f"expected >=3 modelable items, got {[i['title'] for i in modelable]}"
    assert len(unmodelable) >= 1, f"expected >=1 unmodelable item, got {[i['title'] for i in items]}"


# ---------------------------------------------------------------------------
# Behavior 1/2: four-surface {slug: lift} equality + aggregate equality
# ---------------------------------------------------------------------------


def test_four_surfaces_report_identical_per_item_lifts(tmp_path):
    """LIFT-05: the {slug: lift} mapping extracted from CLI markdown, HTML,
    DOCX, and the dashboard payload are all equal to each other, for one
    fixture scan under one pinned (profile, weights=None) pair."""
    evidence = _evidence()
    (
        items,
        exec_content,
        cli_md,
        html_text,
        docx_action_cells,
        docx_paragraphs,
        dashboard_nodes,
        dashboard_projected,
    ) = _build_all_surfaces(evidence, tmp_path)

    dashboard_by_title = _dashboard_lift_by_title(dashboard_nodes)

    cli_by_slug: Dict[str, Optional[int]] = {}
    html_by_slug: Dict[str, Optional[int]] = {}
    docx_by_slug: Dict[str, Optional[int]] = {}
    dashboard_by_slug: Dict[str, Optional[int]] = {}

    for item in items:
        title = item["title"]
        slug = slug_for_title(title)
        assert slug is not None, f"fixture item {title!r} has no slug — cannot key the comparison"

        cli_by_slug[slug] = _extract_cli_lift(cli_md, title)
        html_by_slug[slug] = _extract_html_lift(html_text, title)
        docx_by_slug[slug] = _extract_docx_lift(docx_action_cells, title)
        dash_val = dashboard_by_title[title]
        dashboard_by_slug[slug] = int(dash_val) if dash_val is not None else None

    assert cli_by_slug == html_by_slug == docx_by_slug == dashboard_by_slug, (
        "LIFT-05 VIOLATION: per-item lift mappings disagree across surfaces.\n"
        f"  CLI:       {cli_by_slug}\n"
        f"  HTML:      {html_by_slug}\n"
        f"  DOCX:      {docx_by_slug}\n"
        f"  Dashboard: {dashboard_by_slug}"
    )
    # At least one real positive lift must be present, or this assertion is vacuous.
    assert any(v is not None and v > 0 for v in cli_by_slug.values())


def test_four_surfaces_report_identical_projected_aggregate(tmp_path):
    """LIFT-05: the projected aggregate parsed from all four surfaces is the
    same number for the same fixture scan under the same pinned pair."""
    evidence = _evidence()
    (
        items,
        exec_content,
        cli_md,
        html_text,
        docx_action_cells,
        docx_paragraphs,
        dashboard_nodes,
        dashboard_projected,
    ) = _build_all_surfaces(evidence, tmp_path)

    cli_m = re.search(r"Projected score if all items resolved: (\d+)", cli_md)
    html_m = re.search(r"Projected score if all items resolved: (\d+)", html_text)
    docx_m = None
    for para in docx_paragraphs:
        m = re.search(r"Projected score if all items resolved: (\d+)", para)
        if m:
            docx_m = m
            break

    assert cli_m, "CLI markdown: projected-score line not found"
    assert html_m, "HTML: projected-score line not found"
    assert docx_m, "DOCX: projected-score line not found"

    cli_val = int(cli_m.group(1))
    html_val = int(html_m.group(1))
    docx_val = int(docx_m.group(1))
    dashboard_val = int(dashboard_projected)

    assert cli_val == html_val == docx_val == dashboard_val == int(exec_content.projected_score), (
        "LIFT-05 VIOLATION: projected aggregate disagrees across surfaces.\n"
        f"  CLI: {cli_val}  HTML: {html_val}  DOCX: {docx_val}  "
        f"Dashboard: {dashboard_val}  ExecContent: {exec_content.projected_score}"
    )

    # Verbatim disclaimer, byte-identical, on all three prose surfaces.
    disclaimer = (
        "Advisory — this projection is a simulation and does not affect the readiness score."
    )
    assert disclaimer in cli_md
    assert disclaimer in html_text
    assert disclaimer in docx_paragraphs


def test_projected_aggregate_equals_independent_rescore(tmp_path):
    """LIFT-02: the projected aggregate equals ONE independent rescore of an
    all-resolved deep copy of the evidence — not a sum of per-item lifts."""
    evidence = _evidence()
    score_raw = compute_readiness_score(evidence, profile=_PROFILE)
    items = build_phased_roadmap(evidence, score_raw)["items"]
    projected = compute_projected_score(evidence, items, profile=_PROFILE)

    # Independent rescore, built by hand from the 201-RESEARCH Evidence-Delta
    # Map mutations for EVERY modelable slug `_evidence()`'s roadmap items
    # resolve to (verified live via `_slugs_for_items`) — not only the ones
    # that individually clear compute_item_lifts' strictly-positive filter,
    # since compute_projected_score resolves every modelable item at once for
    # the aggregate, matching its own single-rescore contract. Built directly
    # from the roadmap items' titles/slugs, NOT by calling
    # compute_projected_score again (that would be circular).
    resolved = copy.deepcopy(evidence)
    resolved["plaintext_http_count"] = 0  # plaintext-http-exposure
    resolved["http_on_tls_port_count"] = 0  # plaintext-http-exposure
    resolved["finding_severity_counts"]["HIGH"] = 0  # high-impact-findings
    resolved["finding_severity_counts"]["CRITICAL"] = 0  # high-impact-findings
    resolved["certificate_observations"]["expired_count"] = 0  # expired-certificates
    resolved["certificate_observations"]["expiring_count"] = 0  # near-expiry-certificates
    resolved["certificate_observations"]["self_signed_count"] = 0  # self-signed-certificates
    resolved["protocol_counts"]["UNKNOWN"] = 0  # unknown-open-services
    resolved["finding_severity_counts"]["LOW"] = 0  # legacy-tls-versions
    resolved["cert_key_type_counts"]["ECDSA"] = 1  # ecdsa-adoption-planning
    # tls-enum-coverage and crypto-governance-review are also present in this
    # fixture's roadmap items but have NO mutator in the Evidence-Delta Map
    # (honest-absence slugs) — nothing to apply for them.

    independent_rescore = compute_readiness_score(resolved, profile=_PROFILE)["score"]

    assert projected == independent_rescore, (
        "LIFT-02 VIOLATION: compute_projected_score does not match an "
        f"independent single rescore. projected={projected} "
        f"independent={independent_rescore}"
    )


# ---------------------------------------------------------------------------
# Behavior 3: end-to-end non-additivity on the clamp-binding fixture
# ---------------------------------------------------------------------------


def test_surface_visible_non_additivity_on_clamp_binding_fixture(tmp_path):
    """LIFT-02, proven at the surface, not just at the score_lift.py unit
    boundary: on the clamp-binding fixture, the sum of surface-visible
    per-item lifts (parsed out of the CLI markdown) strictly exceeds the
    surface-visible aggregate delta (parsed projected minus base)."""
    evidence = _clamp_binding_evidence()
    (
        items,
        exec_content,
        cli_md,
        html_text,
        docx_action_cells,
        docx_paragraphs,
        dashboard_nodes,
        dashboard_projected,
    ) = _build_all_surfaces(evidence, tmp_path)

    base_score = compute_readiness_score(evidence, profile=_PROFILE)["score"]

    surface_lift_sum = 0
    for item in items:
        lift = _extract_cli_lift(cli_md, item["title"])
        if lift is not None:
            surface_lift_sum += lift

    cli_m = re.search(r"Projected score if all items resolved: (\d+)", cli_md)
    assert cli_m
    surface_projected = int(cli_m.group(1))
    surface_aggregate_delta = surface_projected - base_score

    assert surface_lift_sum > surface_aggregate_delta, (
        "LIFT-02 VIOLATION: surface-visible per-item lift sum does not "
        f"strictly exceed the surface-visible aggregate delta on the "
        f"clamp-binding fixture. sum={surface_lift_sum} "
        f"aggregate_delta={surface_aggregate_delta} "
        f"(base={base_score}, projected={surface_projected})"
    )


# ---------------------------------------------------------------------------
# Behavior 4: absence — no number on any surface for an unmodelable item
# ---------------------------------------------------------------------------


def test_unmodelable_item_shows_no_number_on_any_surface(tmp_path):
    """SCORE-06 house style, checked end to end: an unmodelable item's title
    appears on all four surfaces, but no `pts` token follows it on the three
    prose surfaces, and its dashboard node's score_lift is None."""
    evidence = _evidence()
    (
        items,
        exec_content,
        cli_md,
        html_text,
        docx_action_cells,
        docx_paragraphs,
        dashboard_nodes,
        dashboard_projected,
    ) = _build_all_surfaces(evidence, tmp_path)

    unmodelable_title = "Establish crypto governance review"
    assert slug_for_title(unmodelable_title) is not None, (
        "fixture assumption changed: 'Establish crypto governance review' no "
        "longer resolves to a slug"
    )
    assert any(it["title"] == unmodelable_title for it in items), (
        f"fixture assumption changed: {unmodelable_title!r} not present in roadmap items"
    )

    assert _extract_cli_lift(cli_md, unmodelable_title) is None
    assert _extract_html_lift(html_text, unmodelable_title) is None
    assert _extract_docx_lift(docx_action_cells, unmodelable_title) is None

    dashboard_by_title = _dashboard_lift_by_title(dashboard_nodes)
    assert unmodelable_title in dashboard_by_title
    assert dashboard_by_title[unmodelable_title] is None
