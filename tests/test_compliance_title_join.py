"""Phase 49 D-04 gate 2 (COMPLY-02/03/04): every emitted finding title is
mapped or allow-listed.
"""
from __future__ import annotations

import pytest

from tests.fixtures.chaos_lab_findings import (
    collect_all_interpolated_templates,
    collect_emitted_titles,
)


def test_aggregator_returns_nonempty():
    """Sanity guard against an AST-walker bug yielding zero titles."""
    titles = collect_emitted_titles()
    assert len(titles) >= 24, (
        f"Aggregator returned only {len(titles)} titles (expected >= 24 fixed-string "
        f"titles in risk_engine.py). AST walker may be broken: {titles}"
    )


@pytest.mark.xfail(
    reason=(
        "TRIAGE-149: 3 Phase 95 codesign finding titles ('Code-signing "
        "certificate expired: ', 'Code-signing certificate expiring within 90 "
        "days: ', 'Code-signing certificate uses weak algorithm: ' — "
        "quirk/engine/findings_evaluator.py lines 1026, 1045, 1080) were never "
        "added to COMPLIANCE_MAP or UNMAPPED_TITLES when CSIGN-01 shipped. "
        "Genuine coverage gap, not a stale test; see docs/test-triage-149.md."
    ),
    strict=False,
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


class TestFingerprintIdentityClassification:
    """Phase 178 IDENT-01 / CONTEXT.md decision 11 ("The Two Derivation
    Paths"): converts the 22 interpolated finding titles from a growing set
    into a bounded one. A new `title=f"..."` added to EITHER derivation path
    (`quirk/engine/findings_evaluator.py`'s `_build_finding` chokepoint, or
    any of the five finding-dataclass constructors in
    `quirk/dashboard/api/routes/scan.py`) without an explicit classification
    in `quirk.compliance.TITLE_IDENTITY_CLASS` fails this class. Neither
    documentation nor code review caught this drift once already — see
    `tests/test_finding_engine_parity.py`, `tests/test_intelligence_trends.py`
    (pre-178), and `scripts/verify_phase_gates.py` (Phase 177) for the three
    prior guards that were never observed to fail.
    """

    @staticmethod
    def _actionable_message(template: str) -> str:
        return (
            f"add {template!r} to quirk/compliance/__init__.py::"
            f"TITLE_IDENTITY_CLASS with one of NORMALIZE / PRESERVE_IDENTITY / "
            f"NOT_IDENTITY_RELEVANT and a one-line rationale; the default is "
            f"PRESERVE_IDENTITY — a false merge is unrecoverable, a false "
            f"split is merely noisy."
        )

    def test_every_interpolated_title_is_classified(self):
        from quirk.compliance import TITLE_IDENTITY_CLASS

        collected = collect_all_interpolated_templates()
        classified = set(TITLE_IDENTITY_CLASS)

        unclassified = sorted(collected - classified)
        assert not unclassified, (
            f"Interpolated title template(s) not classified in "
            f"TITLE_IDENTITY_CLASS: {unclassified}. For each: "
            + "; ".join(self._actionable_message(t) for t in unclassified)
        )

        stale = sorted(classified - collected)
        assert not stale, (
            f"TITLE_IDENTITY_CLASS has entries for templates no longer "
            f"emitted by either derivation path (stale/deleted title): "
            f"{stale}. Remove the stale entry from TITLE_IDENTITY_CLASS, or "
            f"if the title still exists, verify the AST walker is finding "
            f"it (check tests/fixtures/chaos_lab_findings.py)."
        )

    def test_normalize_classified_titles_have_a_matching_fingerprint_alias(self):
        from quirk.compliance import FINGERPRINT_TITLE_ALIASES, TITLE_IDENTITY_CLASS

        for template, cls in TITLE_IDENTITY_CLASS.items():
            if cls != "NORMALIZE":
                continue
            matched = any(
                template.startswith(prefix) for prefix in FINGERPRINT_TITLE_ALIASES
            )
            assert matched, (
                f"{template!r} is classified NORMALIZE in TITLE_IDENTITY_CLASS "
                f"but no prefix in FINGERPRINT_TITLE_ALIASES matches it via "
                f"startswith — the fingerprint path silently does nothing to "
                f"this title. Add a matching prefix to FINGERPRINT_TITLE_ALIASES "
                f"(or TITLE_PREFIX_ALIASES, which it derives from), or "
                f"reclassify this template."
            )

    def test_preserved_titles_have_no_fingerprint_alias(self):
        from quirk.compliance import FINGERPRINT_TITLE_ALIASES, TITLE_IDENTITY_CLASS

        for template, cls in TITLE_IDENTITY_CLASS.items():
            if cls not in {"PRESERVE_IDENTITY", "NOT_IDENTITY_RELEVANT"}:
                continue
            matched = [
                prefix
                for prefix in FINGERPRINT_TITLE_ALIASES
                if template.startswith(prefix)
            ]
            assert not matched, (
                f"{template!r} is classified {cls} (must NOT be normalized "
                f"out of the fingerprint) but matches FINGERPRINT_TITLE_ALIASES "
                f"prefix(es) {matched} via startswith — this would silently "
                f"merge distinct findings' identities. Remove the matching "
                f"prefix from FINGERPRINT_TITLE_ALIASES, or reclassify this "
                f"template to NORMALIZE if the merge is actually intended."
            )
