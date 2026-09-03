"""Phase 181 Plan 01 (SURF-01) — executable specification for the CBOM VEX surface.

Written BEFORE any builder code exists. `quirk/cbom/builder.py` currently emits
ZERO `vulnerabilities` — Plan 181-03 implements `_VEX_STATE_MAP` and
`_make_vex_entry` against the locked contract asserted here. Every test in this
module is expected to fail RED today (ImportError / AttributeError / TypeError
naming `_make_vex_entry` or `_VEX_STATE_MAP`), proving the specification exists
before the implementation that could violate it.

T-181-01 is the single most consequential assertion in this milestone: a
`not_observed` remediation item means "we did not verify" — it must map to
`ImpactAnalysisState.IN_TRIAGE` and NEVER to `ImpactAnalysisState.NOT_AFFECTED`.
`NOT_AFFECTED` asserts safety that was never established. Mapping one to the
other would publish an unverified safety claim inside a machine-readable
artifact that a client may feed straight into their own vulnerability-management
tooling — the exact overclaiming this entire milestone exists to prevent, at
the one point where it becomes externally consumable. A future reader must not
be able to "fix" a failing test here by relaxing this boundary; the module
docstring says so explicitly, in prose, so the intent survives any refactor.

Companion assertions locked by `.planning/phases/181-surfacing/181-CONTEXT.md`:
  - `closed` -> RESOLVED; `open` and `resurfaced` -> EXPLOITABLE.
  - `resurfaced` is distinguished from `open` via `VulnerabilityAnalysis.detail`
    plus `first_issued`/`last_updated`, never via a different enum state.
  - One VEX entry per REMEDIATION ITEM, never per constituent fingerprint.
  - Refused scans and the `unmapped` bucket emit NOTHING — an entry there would
    imply an assessment we explicitly declined to perform.
  - No fabricated CVE id / source / ratings. The CycloneDX 1.6 JSON schema's
    `definitions.vulnerability` has no `"required"` key, so a minimal, honest
    entry is fully legal and nothing needs to be invented to satisfy it.
  - `affects` stays empty and `id` is the slug — no `BomTarget`, so no estate
    identifier (host/port) ever enters the published artifact.

Mirrors `tests/test_vendor_trend_render_sections.py`'s module-docstring +
dict-factory idiom (Phase 161 HWLC-19 precedent).
"""
from __future__ import annotations

import pathlib
from datetime import datetime, timezone

import pytest


def _item(**overrides) -> dict:
    item = {
        "slug": "plaintext-http-exposure",
        "title": "Eliminate plaintext HTTP exposure",
        "state": "open",
        "first_seen": datetime(2026, 8, 1, tzinfo=timezone.utc),
        "last_updated": datetime(2026, 9, 1, tzinfo=timezone.utc),
        "detail": None,
    }
    item.update(overrides)
    return item


# ---------------------------------------------------------------------------
# Task 1 — T-181-01: not_observed -> IN_TRIAGE, never NOT_AFFECTED
# ---------------------------------------------------------------------------

def test_not_observed_maps_to_in_triage():
    from quirk.cbom.builder import _make_vex_entry
    from cyclonedx.model.impact_analysis import ImpactAnalysisState

    entry = _make_vex_entry(_item(state="not_observed"))

    assert entry.analysis.state is ImpactAnalysisState.IN_TRIAGE, (
        "T-181-01: a not_observed remediation item means 'we did not verify' "
        "and must map to IN_TRIAGE. Mapping it to NOT_AFFECTED would publish "
        "an unverified safety claim inside a machine-readable artifact."
    )
    assert entry.analysis.state is not ImpactAnalysisState.NOT_AFFECTED, (
        "T-181-01: not_observed must never resolve to NOT_AFFECTED — that is "
        "an unverified safety claim, and not_observed exists precisely to "
        "avoid making it."
    )


def test_not_affected_is_absent_from_the_entire_state_map():
    from quirk.cbom.builder import _VEX_STATE_MAP
    from cyclonedx.model.impact_analysis import ImpactAnalysisState

    assert ImpactAnalysisState.NOT_AFFECTED not in set(_VEX_STATE_MAP.values()), (
        "T-181-01: ImpactAnalysisState.NOT_AFFECTED must not appear as a value "
        "for ANY key in _VEX_STATE_MAP, not just 'not_observed' — this is an "
        "unverified safety claim and no future closure state may be routed to "
        "it, ever."
    )


def test_builder_source_never_names_not_affected():
    """Comment-stripped source scan — a third, independent gate on the same
    invariant. A comment explaining the ban must not itself trip the ban
    (grep-gate hygiene), so `#`-prefixed lines are filtered before the check."""
    import quirk.cbom.builder as builder_module

    source = pathlib.Path(builder_module.__file__).read_text()
    stripped = "\n".join(
        line for line in source.splitlines() if not line.strip().startswith("#")
    )

    assert "NOT_AFFECTED" not in stripped, (
        "T-181-01: quirk/cbom/builder.py must never name NOT_AFFECTED in live "
        "source — this is an unverified safety claim that must not enter the "
        "published VEX surface, by construction, not by review."
    )


# ---------------------------------------------------------------------------
# Task 2 — state mapping, item-level cardinality, resurfaced narrative
# ---------------------------------------------------------------------------

class TestStateMapping:
    """The three non-not_observed rows of the locked _VEX_STATE_MAP table."""

    @pytest.mark.parametrize(
        "state, expected_attr",
        [
            ("closed", "RESOLVED"),
            ("open", "EXPLOITABLE"),
            ("resurfaced", "EXPLOITABLE"),
        ],
    )
    def test_state_maps_to_expected_impact_analysis_state(self, state, expected_attr):
        from quirk.cbom.builder import _make_vex_entry
        from cyclonedx.model.impact_analysis import ImpactAnalysisState

        entry = _make_vex_entry(_item(state=state))
        assert entry.analysis.state is getattr(ImpactAnalysisState, expected_attr)


def test_resurfaced_retains_narrative_and_timestamps():
    from quirk.cbom.builder import _make_vex_entry

    detail = "Closed 2026-08-15; detected again 2026-09-01"
    first_seen = datetime(2026, 8, 15, tzinfo=timezone.utc)
    last_updated = datetime(2026, 9, 1, tzinfo=timezone.utc)

    resurfaced_entry = _make_vex_entry(
        _item(
            state="resurfaced",
            detail=detail,
            first_seen=first_seen,
            last_updated=last_updated,
        )
    )
    open_entry = _make_vex_entry(_item(state="open"))

    assert resurfaced_entry.analysis.detail == detail
    assert resurfaced_entry.analysis.first_issued == first_seen
    assert resurfaced_entry.analysis.last_updated == last_updated

    # T-181-02: resurfaced and open collapse to the SAME ImpactAnalysisState —
    # CycloneDX has no dedicated resurfaced state. The regression history
    # (that this item came back rather than never having been fixed) lives
    # in `detail`/timestamps, not in the enum. This is the locked decision,
    # not an accident, and this assertion exists to prove it stays that way.
    assert resurfaced_entry.analysis.state == open_entry.analysis.state


def test_one_entry_per_remediation_item_not_per_fingerprint():
    from quirk.cbom.builder import build_cbom

    items = [
        _item(slug="plaintext-http-exposure", state="open"),
        _item(slug="weak-tls-cipher-suite", state="closed"),
        _item(slug="ssh-host-key-rsa1024", state="not_observed"),
    ]

    bom = build_cbom([], remediation_items=items)
    vulns = list(bom.vulnerabilities)

    # A per-fingerprint implementation would iterate RemediationItemFingerprint
    # rows instead of RemediationItem rows and produce thousands of entries,
    # nearly all IN_TRIAGE. This cardinality assertion exists to catch exactly
    # that regression — one entry per ITEM, never per constituent finding.
    assert len(vulns) == 3
    assert {v.id for v in vulns} == {item["slug"] for item in items}


def test_no_remediation_items_leaves_bom_unchanged():
    """Byte-for-byte the pre-Phase-181 behavior: no remediation_items argument
    means no vulnerabilities on the BOM, so existing CBOM golden fixtures
    (which never touch `vulnerabilities`) stay valid without regeneration."""
    from quirk.cbom.builder import build_cbom

    bom = build_cbom([])
    assert list(bom.vulnerabilities) == []


# ---------------------------------------------------------------------------
# Task 3 — silence for refused/unmapped, and no fabricated identity
# ---------------------------------------------------------------------------

class TestSilence:
    """An entry for a refused-scan or unmapped item would imply we assessed
    something we explicitly declined to compare. Silence is the correct,
    honest output — not a fabricated IN_TRIAGE placeholder."""

    @pytest.mark.parametrize("state", ["unmapped", None, "totally-unknown-state"])
    def test_unmapped_or_unknown_state_returns_none(self, state):
        from quirk.cbom.builder import _make_vex_entry

        result = _make_vex_entry(_item(state=state))
        assert result is None, (
            "An entry for an unmapped or unknown closure state would imply we "
            "assessed items we explicitly declined to compare — the caller "
            "must receive None and emit nothing."
        )


def test_refused_scan_emits_no_vulnerabilities():
    """writer.py (Plan 181-03) owns the refusal decision and hands build_cbom
    an empty remediation_items list for a refused scan — see 181-CONTEXT.md:
    'Emit NOTHING for refused scans or the unmapped bucket.' This test asserts
    the builder honors an empty handover rather than inventing entries; it
    does not assert anything about writer.py's own refusal logic."""
    from quirk.cbom.builder import build_cbom

    bom = build_cbom([], remediation_items=[])
    assert list(bom.vulnerabilities) == []


def test_entry_fabricates_no_cve_identity():
    from quirk.cbom.builder import _make_vex_entry

    item = _item(state="open")
    entry = _make_vex_entry(item)

    # The CycloneDX 1.6 JSON schema's definitions.vulnerability carries no
    # "required" key (verified against the schema itself, not merely the
    # Python constructor) — a minimal, honest entry is fully legal, so
    # nothing needs to be invented (no CVE id, no source, no ratings) to
    # satisfy the schema.
    assert entry.id == item["slug"]
    assert not entry.id.upper().startswith("CVE-")
    assert entry.source is None
    assert len(list(entry.ratings)) == 0
    assert len(list(entry.affects)) == 0


def test_entry_carries_no_host_or_port():
    from quirk.cbom.builder import _make_vex_entry

    item = _item(state="open")
    entry = _make_vex_entry(item)

    # "203.0.113." and ":443" are deliberately absent from the item dict —
    # assert positively instead that no estate identifier surface exists:
    # affects is empty (no BomTarget/bom_ref), and the only free-text field
    # on the entry is a title the consultant already publishes elsewhere.
    assert list(entry.affects) == []
    assert entry.description == item["title"]
