"""Phase 50 docs presence gate: enforce architecture.md + operators-guide.md ship with the required sections so docs cannot silently regress.

Pattern modelled on tests/test_pqc_terminology_gate.py — read source file from disk, substring-check the contents.
"""
import os

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

_REQUIRED_DOCS = [
    "docs/architecture.md",
    "docs/operators-guide.md",
]

_REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "docs/architecture.md": (
        "data flow",
        "trust boundar",
        "```mermaid",
        "credential",
    ),
    "docs/operators-guide.md": (
        "troubleshoot",
        "compliance map maintenance",
        "quirk compliance status",
        "staleness_threshold_days",
        "tests/test_compliance_freshness.py",
        "https://www.pcisecuritystandards.org",
        "https://www.ecfr.gov",
        "hhs.gov",
        "https://csrc.nist.gov",
        "quirk init",
    ),
}


def _read(rel: str) -> str:
    """Read a repo-relative file and return its lower-cased contents."""
    return open(os.path.join(_REPO_ROOT, rel), encoding="utf-8").read().lower()


def test_required_docs_resolve():
    """Both Phase 50 docs must exist on disk — RED until Plans 50-02 / 50-03 ship."""
    for rel in _REQUIRED_DOCS:
        assert os.path.isfile(os.path.join(_REPO_ROOT, rel)), (
            f"Required Phase 50 doc missing: {rel}"
        )


def test_required_sections_present():
    """Each Phase 50 doc must contain its full required-substring set (case-insensitive)."""
    missing = []
    for rel, needles in _REQUIRED_SECTIONS.items():
        text = _read(rel)
        for needle in needles:
            if needle.lower() not in text:
                missing.append((rel, needle))
    assert not missing, f"Phase 50 docs missing required sections: {missing}"
