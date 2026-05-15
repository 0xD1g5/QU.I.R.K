"""Phase 45 / Plan 03 / Task 1 — risk_engine ADVISORY → coverage_gap mapping.

Validates that ADVISORY CryptoEndpoint rows produced by
`quirk.util.optional_extra` (Phase 45 Plan 02) become INFO findings with
`category='coverage_gap'` and recommendation carrying the install hint.
"""
from __future__ import annotations

from types import SimpleNamespace

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
        scan_error="Kerberos scanning skipped — run `pip install quirk[identity]` to enable",
        scan_error_category="missing_extra",
    )
    findings = evaluate_endpoints(_cfg(), [ep])

    coverage = [f for f in findings if f.get("category") == "coverage_gap"]
    assert len(coverage) == 1, f"expected exactly one coverage_gap finding, got {findings!r}"

    f = coverage[0]
    assert f["severity"] == "INFO"
    assert f["host"] == "kerberos_scanner"
    assert f["port"] == 0
    assert "pip install quirk[identity]" in f.get("recommendation", "")

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
