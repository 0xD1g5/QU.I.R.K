"""Phase 142 (CVE-01/02/03) — RED test scaffold for the firmware version parser.

Pins the executable contract for ``quirk.scanner.hw_cve.parse_firmware()`` before
the module exists. Covers the 5 verified real-world firmware string formats from
142-RESEARCH.md Pattern 2, plus fail-closed behavior on malformed/empty input
(CVE-03: an unparseable firmware string must never be fuzzy-matched).
"""
from __future__ import annotations

import pytest


# ---------------- verified format parsing ----------------

def test_parse_firmware_schneider_m221_4part() -> None:
    """Schneider M221 firmware "1.6.2.0" — 4-part dotted, no suffix."""
    from quirk.scanner.hw_cve import parse_firmware

    result = parse_firmware("1.6.2.0")
    assert result is not None
    assert isinstance(result, tuple)
    assert all(isinstance(part, int) for part in result)


def test_parse_firmware_johnson_controls_3part() -> None:
    """Johnson Controls FX16 firmware "9.0.1" — 3-part dotted, no suffix."""
    from quirk.scanner.hw_cve import parse_firmware

    result = parse_firmware("9.0.1")
    assert result is not None
    assert isinstance(result, tuple)


def test_parse_firmware_cisco_classic_ios_parenthetical() -> None:
    """Cisco classic IOS "15.2(4)M3" — parenthetical rebuild + train letters."""
    from quirk.scanner.hw_cve import parse_firmware

    result = parse_firmware("15.2(4)M3")
    assert result is not None
    assert isinstance(result, tuple)


def test_parse_firmware_cisco_iosxe_plain() -> None:
    """Cisco IOS-XE "16.9.1" — plain 3-part dotted, no parens."""
    from quirk.scanner.hw_cve import parse_firmware

    result = parse_firmware("16.9.1")
    assert result is not None
    assert isinstance(result, tuple)


def test_parse_firmware_juniper_junos_service_patch() -> None:
    """Juniper Junos "12.3R12-S19" — the -S19 service patch is a MORE-patched
    (greater) state than the bare "12.3R12" release — must NOT sort backwards
    via naive lexicographic/string comparison (142-RESEARCH.md Pitfall re:
    Juniper anti-pattern)."""
    from quirk.scanner.hw_cve import parse_firmware

    result = parse_firmware("12.3R12-S19")
    assert result is not None
    assert isinstance(result, tuple)


def test_parse_firmware_juniper_ordering_locks_anti_pattern() -> None:
    """Locks the Juniper anti-pattern: parse_firmware("12.3R12-S19") must
    compare GREATER than parse_firmware("12.3R12") — the service-patch suffix
    means more-patched, not less. A naive string compare gets this backwards."""
    from quirk.scanner.hw_cve import parse_firmware

    patched = parse_firmware("12.3R12-S19")
    base = parse_firmware("12.3R12")
    assert patched is not None
    assert base is not None
    assert patched > base


# ---------------- malformed / fail-closed inputs (CVE-03) ----------------

@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "not-a-version",
        "abc.def.ghi",
        "   ",
        "1.x.y",
    ],
)
def test_parse_firmware_malformed_returns_none(raw) -> None:
    """CVE-03: malformed/empty/None firmware strings must return None
    (fail-closed) — never a guessed/fuzzy comparable value."""
    from quirk.scanner.hw_cve import parse_firmware

    assert parse_firmware(raw) is None
