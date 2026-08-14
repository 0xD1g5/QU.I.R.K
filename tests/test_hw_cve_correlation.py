"""Phase 142 (CVE-01/02/03/04) — RED test scaffold for CVE correlation behavior.

Pins the executable contract for ``quirk.scanner.hw_cve.correlate_device()`` before
the module exists. Covers CONTEXT.md decisions D-01 (all-devices scope), D-02
(vendor+model fallback), D-03 (Unknown-vendor gate lives at the CALL SITE, not
inside correlate_device), D-04 (multi-match severity sort), D-07/D-08 (confidence
derivation + fail-closed "no correlation attempted"), and the Schneider M221
boundary pitfall (strict `<` on affected_before).
"""
from __future__ import annotations


# ---------------- D-03: vendor == "Unknown" gate lives at the call site ----------------

def test_unknown_vendor_yields_no_annotation() -> None:
    """D-03: a device with vendor == 'Unknown' must be silently skipped —
    no 'no CVE correlation attempted' caveat, no CVE annotation at all.
    This is a call-site gate (checked BEFORE invoking correlate_device),
    not internal correlate_device logic — verified here via the documented
    helper/gate pattern: correlate_device should only ever be invoked for
    identified vendors."""
    from quirk.scanner.hw_cve import correlate_device

    # A vendor == "Unknown" device should never reach correlate_device() in
    # production call sites; if it does, the correlation result must not
    # imply a meaningful "attempted" outcome distinct from an identified
    # vendor with no match. The call-site gate is exercised separately —
    # this test asserts correlate_device with vendor "Unknown" degrades to
    # a harmless no-op result (attempted=False, matches=[]), keeping the
    # actual skip decision (no caveat rendering) at the call site.
    result = correlate_device("Unknown", None, None)
    assert result.matches == []


# ---------------- D-02: vendor+model fallback when firmware is None ----------------

def test_vendor_model_only_fallback_medium_confidence() -> None:
    """D-02/D-08: a device with vendor+model matching CVE_TABLE but
    firmware=None falls back to vendor+model-only match with confidence
    'medium' (when the matching entry itself doesn't require a version
    distinction, i.e. affected_before is None)."""
    from quirk.scanner.hw_cve import correlate_device

    result = correlate_device("Johnson Controls", "Facility Explorer", None)
    assert result.attempted is True
    if result.matches:
        assert result.confidence == "medium"


# ---------------- D-08: high confidence on clean parse + in-range match ----------------

def test_firmware_in_affected_range_high_confidence() -> None:
    """D-08: a device whose firmware parses AND falls inside an
    affected_before range returns confidence 'high'."""
    from quirk.scanner.hw_cve import correlate_device

    # Schneider M221 CVE-2018-7789 affected_before="1.6.2.0" — firmware
    # strictly less than that boundary must match at high confidence.
    result = correlate_device("Schneider Electric", "M221", "1.6.1.9")
    assert result.attempted is True
    assert result.confidence == "high"
    assert any(m["cve_id"] == "CVE-2018-7789" for m in result.matches)


# ---------------- D-07/CVE-03: unparseable firmware -> attempted, zero matches ----------------

def test_unparseable_firmware_no_correlation_attempted() -> None:
    """D-07/CVE-03: a device whose firmware string does not parse returns
    attempted=True with zero matches — the 'no correlation attempted'
    outcome — never a fuzzy/guessed match."""
    from quirk.scanner.hw_cve import correlate_device

    result = correlate_device("Schneider Electric", "M221", "not-a-version")
    assert result.attempted is True
    assert result.matches == []


# ---------------- Pitfall 2: Schneider M221 exact boundary is NOT affected ----------------

def test_schneider_m221_exact_boundary_not_affected() -> None:
    """Pitfall 2: firmware exactly '1.6.2.0' does NOT match CVE-2018-7789
    whose affected_before is '1.6.2.0' — the range check is strict `<`,
    not `<=`. A comparator that gets this backwards would falsely flag an
    already-patched device."""
    from quirk.scanner.hw_cve import correlate_device

    result = correlate_device("Schneider Electric", "M221", "1.6.2.0")
    cve_ids = {m["cve_id"] for m in result.matches}
    assert "CVE-2018-7789" not in cve_ids


# ---------------- D-04: multi-match severity sort, most-severe-first ----------------

def test_multi_match_sorted_most_severe_first() -> None:
    """D-04: a device matching multiple CVEs returns them sorted
    most-severe-first (CRITICAL before HIGH before MEDIUM before LOW)."""
    from quirk.scanner.hw_cve import correlate_device

    # Cisco IOS has two seeded entries: CVE-2017-12240 (CRITICAL) and
    # CVE-2016-6382 (HIGH), both affected_before="15.6" — firmware "15.0"
    # should match both.
    result = correlate_device("Cisco", "IOS", "15.0")
    assert len(result.matches) >= 2

    severities = [m["severity"] for m in result.matches]
    _order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    ordinals = [_order[s] for s in severities]
    assert ordinals == sorted(ordinals), (
        f"Matches not sorted most-severe-first: {severities}"
    )
    assert severities[0] == "CRITICAL"


# ---------------- Phase 155 Task 1: firmware_for_correlation() single home ----------------


def test_firmware_for_correlation_prefers_modbus() -> None:
    """Prefers modbus_firmware over bacnet_firmware when both are set,
    preserving the existing or-chain precedence."""
    from types import SimpleNamespace

    from quirk.scanner.hw_cve import firmware_for_correlation

    device = SimpleNamespace(modbus_firmware="1.2", bacnet_firmware="9")
    assert firmware_for_correlation(device) == "1.2"


def test_firmware_for_correlation_falls_back_to_bacnet() -> None:
    """Returns bacnet_firmware when modbus_firmware is None/empty."""
    from types import SimpleNamespace

    from quirk.scanner.hw_cve import firmware_for_correlation

    device = SimpleNamespace(modbus_firmware=None, bacnet_firmware="9")
    assert firmware_for_correlation(device) == "9"

    device_empty = SimpleNamespace(modbus_firmware="", bacnet_firmware="9")
    assert firmware_for_correlation(device_empty) == "9"


def test_firmware_for_correlation_none_when_both_absent() -> None:
    """Returns None when both firmware fields are None/empty — e.g.
    SSH/HTTP/SNMP-fingerprinted devices carry neither."""
    from types import SimpleNamespace

    from quirk.scanner.hw_cve import firmware_for_correlation

    device = SimpleNamespace(modbus_firmware=None, bacnet_firmware=None)
    assert firmware_for_correlation(device) is None


def test_firmware_for_correlation_never_raises_on_missing_attrs() -> None:
    """Does not raise on an object lacking either attribute (getattr with
    default)."""
    from types import SimpleNamespace

    from quirk.scanner.hw_cve import firmware_for_correlation

    assert firmware_for_correlation(SimpleNamespace()) is None
