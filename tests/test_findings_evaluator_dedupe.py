"""Tests for quirk.engine.findings_evaluator dedup ordering — Phase 72 D-04 / WR-24.

Covers:
- D-04 (WR-24): _dedupe_findings sort key is (severity_rank, title, host, port).
  Recommendation diffs no longer reshuffle output order.
- D-04a: _SEVERITY_RANK is module-private; not re-exported via __all__.
- D-05 (WR-10): risk_engine shim re-exports _dedupe_findings identical to canonical.
"""
from __future__ import annotations

import quirk.engine.findings_evaluator as fe
from quirk.engine.findings_evaluator import _dedupe_findings, _SEVERITY_RANK


def _finding(host: str, port: int, title: str, severity: str = "INFO",
             recommendation: str = "") -> dict:
    return {
        "host": host,
        "port": port,
        "title": title,
        "severity": severity,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# D-04: stable sort under recommendation-only diffs
# ---------------------------------------------------------------------------

def test_dedupe_sort_stable_under_recommendation_diff():
    """Two finding-sets that differ ONLY in recommendation text must produce
    identical dedup output ordering."""
    a = [
        _finding("h1", 443, "TLS finding", "HIGH", recommendation="rec-v1-alpha"),
        _finding("h2", 443, "Cert finding", "MEDIUM", recommendation="rec-v1-beta"),
    ]
    b = [
        _finding("h1", 443, "TLS finding", "HIGH", recommendation="rec-v2-completely-different"),
        _finding("h2", 443, "Cert finding", "MEDIUM", recommendation="rec-v2-also-different"),
    ]
    out_a = [(f["host"], f["port"], f["title"]) for f in _dedupe_findings(a)]
    out_b = [(f["host"], f["port"], f["title"]) for f in _dedupe_findings(b)]
    assert out_a == out_b


def test_dedupe_sort_severity_priority():
    """Findings should be ordered CRITICAL, HIGH, MEDIUM, LOW, INFO by _SEVERITY_RANK."""
    findings = [
        _finding("h1", 443, "low-finding", "LOW"),
        _finding("h2", 443, "high-finding", "HIGH"),
        _finding("h3", 443, "info-finding", "INFO"),
        _finding("h4", 443, "critical-finding", "CRITICAL"),
    ]
    out = _dedupe_findings(findings)
    severities = [f["severity"] for f in out]
    assert severities == ["CRITICAL", "HIGH", "LOW", "INFO"]


# ---------------------------------------------------------------------------
# D-04a: _SEVERITY_RANK private
# ---------------------------------------------------------------------------

def test_severity_rank_module_private():
    """_SEVERITY_RANK exists at module scope but should not be in __all__ if defined."""
    assert "_SEVERITY_RANK" in fe.__dict__
    assert _SEVERITY_RANK["CRITICAL"] == 0
    assert _SEVERITY_RANK["INFO"] == 4
    all_attr = getattr(fe, "__all__", None)
    if all_attr is not None:
        assert "_SEVERITY_RANK" not in all_attr


# ---------------------------------------------------------------------------
# D-05 / WR-10: shim re-exports private _dedupe_findings
# ---------------------------------------------------------------------------

def test_dedupe_via_risk_engine_shim_works():
    """The deprecated risk_engine shim must re-export _dedupe_findings identical
    to the canonical findings_evaluator._dedupe_findings."""
    from quirk.engine.risk_engine import _dedupe_findings as shim_dedupe
    from quirk.engine.findings_evaluator import _dedupe_findings as canonical
    assert shim_dedupe is canonical
