"""Content gate for the hand-composed ``## [5.29.0]`` CHANGELOG section (Phase 240, REL-14).

``release.yml`` publishes this section as the public GitHub release body, and README.md is the PyPI long
description. This file owns the 5.29.0 assertions for both: the section must lead with score movements,
carry a fix-only ``### Security`` block, disclose exactly the score divergences the code still dispositions
(the phrase maps are checked for set equality against the live ``SEVERITY_DIVERGENCES`` and
``UNBRIDGED_DASHBOARD_TITLES``, so fixing or adding a divergence turns this red until the notes follow), and
state that the divergences fixed in 5.29.0 are withdrawn.

Reads CHANGELOG.md and README.md only; never touches ``.planning/`` (gitignored, absent in CI). Pinned to
5.29.0 via ``_PINNED_VERSION``; it does not read pyproject's version, so a later bump cannot repoint it.
In 5.29.0 the README assertions that used to live in tests/test_changelog_5280_section.py moved here.
"""
from __future__ import annotations

import re
from pathlib import Path

from quirk.dashboard.api.finding_title_bridge import (
    SEVERITY_DIVERGENCES,
    UNBRIDGED_DASHBOARD_TITLES,
)
from tests.test_changelog_5280_section import _parity_violations

_ROOT = Path(__file__).resolve().parent.parent
_CHANGELOG = _ROOT / "CHANGELOG.md"
_README = _ROOT / "README.md"

_PINNED_VERSION = "5.29.0"

# GHSA- is banned while the advisories are unpublished; the post-publication link commit relaxes it.
_INTERNAL_IDS = re.compile(
    r"999\.|\.planning|\b261\d{3}-|\bD-\d{2}\b|\bCR-0\d\b|\bWR-\d{2}\b|\bP-\d{2}\b|GHSA-"
)

# Number of public fix-only lines in the private release hand-off (one per advisory area).
_SECURITY_LINE_COUNT = 5

# One distinctive phrase per user-visible change, grouped by the release-notes row it comes from.
_REQUIRED_TERMS: tuple[str, ...] = (
    # confidence ceiling (SCORE-11)
    "confidence", "59", "50%",
    # Phase 237 release-notes row
    "12 HIGH", "--list-resumable", "Incomplete", "2N", "Finding and Port columns",
    # Phase 238 release-notes row
    "+6", "RSA-PSS", "SHA-1", "SCORING_VERSION", "JWT",
    # Phase 239 release-notes row
    "trusted_targets", "referrals", "non-ASCII", "registry",
    # Phase 236 outcomes
    "legacy TLS", "end-of-life",
    # SNMP vendor catalog corrections
    "PAN-OS",
    "FortiOS",
    "Junos OS Evolved",
)

# Live-derived: the key sets must EQUAL the live dicts.
_DIVERGENCE_PHRASES: dict[str, str] = {
    "Kerberos weak etype: ": "Kerberos weak-encryption",
    "DNSSEC: ": "DNSSEC",
    "Unencrypted HTTP service": "HTTP service beside an mTLS-required",
}
# MEDIUM, not score-moving, disclosed under the below-HIGH item. Never "undersized ECDSA": 5.29.0 withdraws it.
_DASHBOARD_ONLY_PHRASES: dict[str, str] = {
    "Quantum-": "non-RSA certificate keys",
}
_TODO_DIVERGENCE_PHRASES: tuple[tuple[str, str], ...] = (
    ("default report deriver drops tls_designated_ports", "TLS-designated ports"),
    ("report lists MEDIUM/LOW findings the dashboard does not derive", "below-HIGH findings"),
)
_HEDGE = "other findings may also differ"

# README is the PyPI long description: none of these withdrawn 5.28.0 divergence phrasings may survive anywhere in it.
_WITHDRAWN_README_PHRASES: tuple[str, ...] = (
    "legacy TLS version finding",
    "weak cipher suites (dashboard only",
    "undersized ECDSA certificate keys (",
    "end-of-life crypto libraries in container images (report only)",
    "scores 84 in the report and 69 on the dashboard",
    "84 in the report and 69 on the dashboard",
    "drift notification can show a different score",
    "Known gaps in 5.28.2",
)

# Divergences fixed in 5.29.0; the section must say they no longer differ.
_WITHDRAWN_CASES: tuple[str, ...] = (
    "legacy TLS version", "weak cipher suite", "undersized ECDSA",
    "end-of-life crypto libraries in container images", "drift notification", "headline score",
)


def _text() -> str:
    return _CHANGELOG.read_text(encoding="utf-8")


def _norm(s: str) -> str:
    return " ".join(s.split())


def _section() -> str:
    text = _text()
    m = re.search(rf"^## \[{re.escape(_PINNED_VERSION)}\] - \d{{4}}-\d{{2}}-\d{{2}}\s*$", text, re.M)
    assert m, f"CHANGELOG.md has no '## [{_PINNED_VERSION}] - YYYY-MM-DD' heading"
    rest = text[m.end():]
    nxt = re.search(r"^## \[", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _subsection(title: str) -> str:
    sec = _section()
    m = re.search(rf"^### {re.escape(title)}\s*$", sec, re.M)
    assert m, f"5.29.0 section has no '### {title}' block"
    rest = sec[m.end():]
    nxt = re.search(r"^### ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _known_defects() -> str:
    return _subsection("Known defects")


def test_heading_dated_and_above_5282() -> None:
    text = _text()
    m = re.search(r"^## \[5\.29\.0\] - \d{4}-\d{2}-\d{2}$", text, re.M)
    assert m, "missing '## [5.29.0] - YYYY-MM-DD' heading"
    old = re.search(r"^## \[5\.28\.2\]", text, re.M)
    assert old and m.start() < old.start(), "[5.29.0] must sit above [5.28.2]"
    assert text.index("## [Unreleased]") < m.start()


def test_unreleased_stays_empty() -> None:
    text = _text()
    i = text.index("## [Unreleased]") + len("## [Unreleased]")
    nxt = re.search(r"^## \[", text[i:], re.M)
    assert nxt, "no release heading after [Unreleased]"
    assert text[i:i + nxt.start()].strip() == ""


def test_no_internal_or_advisory_ids() -> None:
    hits = _INTERNAL_IDS.findall(_section())
    assert not hits, f"internal ids leaked into release notes: {hits}"
    low = _section().lower()
    for banned in ("dependabot", "embargo"):
        assert banned not in low, banned


def test_upgrade_notes_lead_with_score_movements() -> None:
    sec = _section()
    up = sec.index("### Upgrade notes")
    for later in ("### Fixed", "### Changed", "### Security", "### Known defects"):
        if later in sec:
            assert up < sec.index(later), f"Upgrade notes must precede {later}"
    assert "scores" in _norm(_subsection("Upgrade notes")).lower()[:400]


def test_security_block_is_fix_only_and_counted() -> None:
    block = _subsection("Security")
    bullets = [ln for ln in block.splitlines() if ln.startswith("- ")]
    assert len(bullets) == _SECURITY_LINE_COUNT, bullets
    for ln in bullets:
        assert ln.startswith("- Hardened "), ln


def test_required_terms_present() -> None:
    s = _norm(_section())
    missing = [t for t in _REQUIRED_TERMS if t not in s]
    assert not missing, f"5.29.0 section must mention {missing}"


def test_divergence_phrase_sets_match_live_code() -> None:
    assert set(_DIVERGENCE_PHRASES) == set(SEVERITY_DIVERGENCES)
    assert set(_DASHBOARD_ONLY_PHRASES) == set(UNBRIDGED_DASHBOARD_TITLES)


def test_known_defects_disclose_live_divergences() -> None:
    kd = _norm(_known_defects()).lower()
    assert any("dashboard" in ln.lower() and "report" in ln.lower() and re.search(r"differ", ln, re.I)
               for ln in _known_defects().splitlines()) or ("dashboard" in kd and "differ" in kd)
    phrases = (list(_DIVERGENCE_PHRASES.values()) + list(_DASHBOARD_ONLY_PHRASES.values())
               + [p for _, p in _TODO_DIVERGENCE_PHRASES] + [_HEDGE])
    missing = [p for p in phrases if p.lower() not in kd]
    assert not missing, f"Known defects omit: {missing}"
    assert "semgrep" in kd and "key vault" in kd and "sensor identity" in kd


def test_remaining_divergence_item_does_not_reuse_withdrawn_ecdsa_phrase() -> None:
    items = re.split(r"\n(?=- )", _known_defects())
    live = [i for i in items if "can still differ" in _norm(i)]
    assert len(live) == 1, "expected exactly one remaining-divergence item"
    assert "undersized ecdsa" not in _norm(live[0]).lower()


def test_withdrawal_of_fixed_cases_is_stated() -> None:
    s = _norm(_section()).lower()
    assert "no longer differ" in s
    missing = [c for c in _WITHDRAWN_CASES if c.lower() not in s]
    assert not missing, f"5.29.0 section does not name fixed cases: {missing}"


def test_no_unqualified_parity_claim() -> None:
    assert _parity_violations(_section()) == []


def _readme() -> str:
    return _README.read_text(encoding="utf-8")


def _readme_whats_new_v529() -> str:
    text = _readme()
    m = re.search(r"^## What's New in v5\.29\s*$", text, re.M)
    assert m, "README.md has no \"## What's New in v5.29\" heading"
    assert m.start() < text.index("## What's New in v5.28"), "v5.29 must sit above v5.28"
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def test_readme_whats_new_v529_discloses_divergences() -> None:
    sec = _norm(_readme_whats_new_v529()).lower()
    phrases = (list(_DIVERGENCE_PHRASES.values()) + list(_DASHBOARD_ONLY_PHRASES.values())
               + [p for _, p in _TODO_DIVERGENCE_PHRASES] + [_HEDGE])
    missing = [p for p in phrases if p.lower() not in sec]
    assert not missing, f"README What's New v5.29 omits divergence phrases: {missing}"
    assert "semgrep" in sec and "key vault" in sec and "sensor identity" in sec


def test_readme_no_unqualified_parity_claim() -> None:
    assert _parity_violations(_readme()) == []


def test_readme_withdrawn_divergence_phrases_absent() -> None:
    norm = _norm(_readme()).lower()
    present = [p for p in _WITHDRAWN_README_PHRASES if p.lower() in norm]
    assert not present, f"README still carries withdrawn divergence wording: {present}"
