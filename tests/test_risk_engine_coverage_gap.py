"""Phase 45 / Plan 03 / Task 1 — risk_engine ADVISORY → coverage_gap mapping.

Validates that ADVISORY CryptoEndpoint rows produced by
`quirk.util.optional_extra` (Phase 45 Plan 02) become INFO findings with
`category='coverage_gap'` and recommendation carrying the install hint.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from quirk.engine.findings_evaluator import evaluate_endpoints


def _cfg():
    return SimpleNamespace(
        scan=SimpleNamespace(ports_tls=[], ports_http=[]),
    )


def _ep(**kwargs):
    """Minimal duck-typed CryptoEndpoint stand-in."""
    defaults = dict(
        host="",
        port=0,
        protocol="UNKNOWN",
        scan_error=None,
        scan_error_category=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_advisory_row_becomes_coverage_gap_finding():
    ep = _ep(
        host="kerberos_scanner",
        port=0,
        protocol="ADVISORY",
        scan_error="Kerberos scanning skipped — run `pip install 'quirk-scanner[identity]'` to enable",
        scan_error_category="missing_extra",
    )
    findings = evaluate_endpoints(_cfg(), [ep])

    coverage = [f for f in findings if f.get("category") == "coverage_gap"]
    assert len(coverage) == 1, f"expected exactly one coverage_gap finding, got {findings!r}"

    f = coverage[0]
    assert f["severity"] == "INFO"
    assert f["host"] == "kerberos_scanner"
    assert f["port"] == 0
    assert "pip install 'quirk-scanner[identity]'" in f.get("recommendation", "")

    # Must NOT also produce the generic "Informational protocol observation" finding.
    titles = [x.get("title", "") for x in findings]
    assert "Informational protocol observation" not in titles, (
        f"ADVISORY row was double-emitted: {titles!r}"
    )


def test_non_advisory_endpoints_unchanged():
    """Plain HTTP endpoint still produces its existing HIGH plaintext finding."""
    ep = _ep(host="example.test", port=80, protocol="HTTP")
    findings = evaluate_endpoints(_cfg(), [ep])
    titles = [f.get("title", "") for f in findings]
    assert any("Plaintext HTTP" in t for t in titles), (
        f"regression — HTTP plaintext finding missing: {titles!r}"
    )
    # No coverage_gap leakage for non-ADVISORY rows.
    assert all(f.get("category") != "coverage_gap" for f in findings)


def test_advisory_with_other_category_falls_through():
    """ADVISORY rows whose scan_error_category is NOT missing_extra fall through to
    the existing scan_err handler (defensive — should never happen in practice)."""
    ep = _ep(
        host="weird",
        port=0,
        protocol="ADVISORY",
        scan_error="some other transient failure",
        scan_error_category="timeout",
    )
    findings = evaluate_endpoints(_cfg(), [ep])
    # Should NOT be tagged coverage_gap (defensive)
    assert all(f.get("category") != "coverage_gap" for f in findings), (
        f"unexpected coverage_gap on non-missing_extra ADVISORY: {findings!r}"
    )
    # Should fall through to the generic informational scan_err handler.
    titles = [f.get("title", "") for f in findings]
    assert any("Informational protocol observation" in t for t in titles), (
        f"expected generic scan_err handler to fire: {titles!r}"
    )


def test_missing_binary_advisory_becomes_titled_coverage_gap_finding():
    """235.1 D-06: ADVISORY/missing_binary -> one INFO coverage_gap finding with
    the dedicated title, naming the binary, and no generic observation."""
    ep = _ep(
        host="source_scanner",
        port=0,
        protocol="ADVISORY",
        scan_error="semgrep is not installed (QRK-INSTALL-008)",
        scan_error_category="missing_binary",
    )
    findings = evaluate_endpoints(_cfg(), [ep])

    coverage = [f for f in findings if f.get("category") == "coverage_gap"]
    assert len(coverage) == 1, f"expected one coverage_gap finding, got {findings!r}"
    f = coverage[0]
    assert f["severity"] == "INFO"
    assert f["title"] == "Scanner skipped \u2014 required tool not installed"
    assert "semgrep" in f["description"]
    titles = [x.get("title", "") for x in findings]
    assert "Informational protocol observation" not in titles
    assert len(findings) == 1


@pytest.mark.parametrize("category", [
    "internal_target_refused", "auth_failed", "missing_credentials", "targets_unreachable",
])
def test_coverage_skip_advisory_becomes_titled_coverage_gap_finding(category):
    """235.3 D-07: each coverage-skip ADVISORY -> exactly one INFO coverage_gap
    finding carrying the skip detail, and no generic observation duplicate."""
    detail = "1 of 1 targets refused (internal address)"
    ep = _ep(
        host="jwt_scanner", port=0, protocol="ADVISORY",
        scan_error=detail, scan_error_category=category,
    )
    findings = evaluate_endpoints(_cfg(), [ep])
    assert len(findings) == 1, f"expected one finding, got {findings!r}"
    f = findings[0]
    assert f["category"] == "coverage_gap"
    assert f["severity"] == "INFO"
    assert f["title"] == "Connector skipped \u2014 no target answered"
    assert detail in f["description"]
    assert "Informational protocol observation" not in f["title"]
