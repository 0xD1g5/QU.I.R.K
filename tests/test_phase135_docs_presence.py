"""Phase 135 docs presence gate: enforce README.md, CHANGELOG.md,
docs/getting-started.md, and docs/architecture.md ship with the v5.8.0
hardware-fingerprinting content so these docs cannot silently regress.

Pattern modelled on tests/test_phase50_docs_presence.py — read source file
from disk, substring-check the (lower-cased) contents. CHANGELOG.md also
gets a positional order check since ordering (most-recent-first) is itself
part of the CORE-01 requirement.
"""
import os

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

_REQUIRED_DOCS = [
    "README.md",
    "CHANGELOG.md",
    "docs/getting-started.md",
    "docs/architecture.md",
]

_REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "v5.8.0",
        "what's new in v5.8",
        "hardware fingerprinting",
        "cnsa 2.0",
        "crypto-bridge",
        "[hw]",
        "device",
        "firmware",
    ),
    "CHANGELOG.md": (
        "[5.8.0]",
        "[5.7.0]",
        "[5.6.0]",
    ),
    "docs/getting-started.md": (
        "quirk-scanner[hw]",
        "hardware",
        "not included",
    ),
    "docs/architecture.md": (
        "hardware scanning",
        "signal chain",
        "componenttype.device",
        "componenttype.firmware",
        "does not contribute to the quantum-readiness score",
    ),
}

# README must NOT regress back to the stale pre-135 version string.
_FORBIDDEN_SECTIONS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "v5.5.2.5 - beta",
    ),
}


def _read(rel: str) -> str:
    """Read a repo-relative file and return its lower-cased contents."""
    return open(os.path.join(_REPO_ROOT, rel), encoding="utf-8").read().lower()


def test_required_docs_resolve():
    """All four Phase 135 docs must exist on disk."""
    for rel in _REQUIRED_DOCS:
        assert os.path.isfile(os.path.join(_REPO_ROOT, rel)), (
            f"Required Phase 135 doc missing: {rel}"
        )


def test_required_sections_present():
    """Each Phase 135 doc must contain its full required-substring set (case-insensitive)."""
    missing = []
    for rel, needles in _REQUIRED_SECTIONS.items():
        text = _read(rel)
        for needle in needles:
            if needle.lower() not in text:
                missing.append((rel, needle))
    assert not missing, f"Phase 135 docs missing required sections: {missing}"


def test_readme_forbidden_sections_absent():
    """README.md must not regress to the pre-135 stale Beta version string."""
    present = []
    for rel, needles in _FORBIDDEN_SECTIONS.items():
        text = _read(rel)
        for needle in needles:
            if needle.lower() in text:
                present.append((rel, needle))
    assert not present, f"Phase 135 docs regressed to stale content: {present}"


def test_changelog_entries_in_most_recent_first_order():
    """CHANGELOG.md must list [5.8.0] before [5.7.0] before [5.6.0] (most-recent-first)."""
    text = _read("CHANGELOG.md")
    pos_580 = text.find("[5.8.0]")
    pos_570 = text.find("[5.7.0]")
    pos_560 = text.find("[5.6.0]")
    assert -1 not in (pos_580, pos_570, pos_560), (
        "One or more of [5.8.0]/[5.7.0]/[5.6.0] not found in CHANGELOG.md"
    )
    assert pos_580 < pos_570 < pos_560, (
        f"CHANGELOG.md entries out of most-recent-first order: "
        f"[5.8.0]@{pos_580}, [5.7.0]@{pos_570}, [5.6.0]@{pos_560}"
    )


def test_getting_started_quickstart_still_uses_all_extra():
    """The 3-step quickstart in getting-started.md must remain unchanged (still uses [all])."""
    text = _read("docs/getting-started.md")
    assert "quirk-scanner[all]" in text, (
        "getting-started.md quickstart no longer references quirk-scanner[all] — "
        "the CORE-03 [hw] section must be additive, not a replacement of the quickstart"
    )


def test_architecture_mermaid_has_hardware_scanner_node():
    """The §1 mermaid flowchart must show a hardware scanner node feeding DB, parallel to Scanners."""
    text = _read("docs/architecture.md")
    assert "flowchart" in text, "docs/architecture.md §1 mermaid block missing 'flowchart' directive"
    assert "scanners[" in text, "docs/architecture.md §1 mermaid block missing existing Scanners node"
    assert any(
        needle in text for needle in ("hardwarescan[", "hwcompat")
    ), "docs/architecture.md §1 mermaid block missing a hardware scanner node"
