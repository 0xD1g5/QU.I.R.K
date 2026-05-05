"""Phase 49 D-04 gate 2 (COMPLY-02/03/04): every emitted finding title is
mapped or allow-listed.
"""
from __future__ import annotations

from tests.fixtures.chaos_lab_findings import collect_emitted_titles


def test_aggregator_returns_nonempty():
    """Sanity guard against an AST-walker bug yielding zero titles."""
    titles = collect_emitted_titles()
    assert len(titles) >= 24, (
        f"Aggregator returned only {len(titles)} titles (expected >= 24 fixed-string "
        f"titles in risk_engine.py). AST walker may be broken: {titles}"
    )


def test_every_emitted_title_is_mapped_or_allowlisted():
    from quirk.compliance import COMPLIANCE_MAP, UNMAPPED_TITLES

    emitted = collect_emitted_titles()
    known = set(COMPLIANCE_MAP) | set(UNMAPPED_TITLES)
    orphans = sorted(emitted - known)
    assert not orphans, (
        f"Emitted finding titles missing from COMPLIANCE_MAP and UNMAPPED_TITLES: "
        f"{orphans}. Either add a mapping or add to UNMAPPED_TITLES with an "
        f"inline comment explaining why no compliance frameworks apply."
    )
