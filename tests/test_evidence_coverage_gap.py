"""Phase 45 / Plan 03 / Task 3 — evidence summary excludes coverage_gap (D-07)."""
from __future__ import annotations

from quirk.intelligence.evidence import build_evidence_summary


def test_evidence_summary_excludes_coverage_gap():
    findings = [
        {
            "severity": "INFO",
            "category": "coverage_gap",
            "host": "kerb",
            "port": 0,
            "title": "Scanner skipped — optional extra not installed",
            "recommendation": "pip install quirk[identity]",
        },
        {
            "severity": "HIGH",
            "host": "x",
            "port": 1,
            "title": "Plaintext HTTP service detected",
        },
    ]
    summary = build_evidence_summary(endpoints=[], findings=findings)

    # totals.findings is HIGH only — coverage_gap excluded
    assert summary["totals"]["findings"] == 1, (
        f"totals.findings={summary['totals']['findings']!r}; expected 1 (HIGH only, coverage_gap excluded)"
    )
    sev = summary["finding_severity_counts"]
    assert sev["HIGH"] == 1
    assert sev["INFO"] == 0, (
        f"finding_severity_counts.INFO={sev['INFO']!r}; coverage_gap must not inflate INFO"
    )


def test_evidence_summary_zero_coverage_gaps_unchanged():
    """Regression: when no coverage_gap findings, totals/sev counts behave as before."""
    findings = [
        {"severity": "HIGH", "host": "h1", "port": 1, "title": "A"},
        {"severity": "INFO", "host": "h2", "port": 2, "title": "B"},
        {"severity": "MEDIUM", "host": "h3", "port": 3, "title": "C"},
    ]
    summary = build_evidence_summary(endpoints=[], findings=findings)
    assert summary["totals"]["findings"] == 3
    sev = summary["finding_severity_counts"]
    assert sev["HIGH"] == 1
    assert sev["MEDIUM"] == 1
    assert sev["INFO"] == 1
