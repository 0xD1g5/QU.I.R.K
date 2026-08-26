"""Phase 164 FIRSTRUN-02: TARGET-domain error registry + wire-format tests (D-05, D-06).

Covers the two sibling scan-target input failures called out by D-05: a
missing --targets-file path (TARGET-001) and a malformed target token/CIDR
(TARGET-002). Both must be registered in quirk.errors.ERROR_REGISTRY and
render the wire format: [QRK-TARGET-NNN] <cause>. Fix: <hint>.

Also pins the D-05/D-07 library contract: quirk/util/targets.py must keep
raising stdlib FileNotFoundError / ValueError, never QUIRK-coded exceptions —
coding happens only at the CLI boundary (Plan 02), not inside the library.
"""
from __future__ import annotations

import re

import pytest

QRK_FORMAT = re.compile(r"\[QRK-[A-Z]+-[A-Z0-9-]+\] .+\. Fix: .+")


def test_target_codes_registered():
    """TARGET-001 and TARGET-002 are keys in ERROR_REGISTRY with matching .code fields."""
    from quirk.errors import ERROR_REGISTRY

    assert "TARGET-001" in ERROR_REGISTRY
    assert "TARGET-002" in ERROR_REGISTRY
    assert ERROR_REGISTRY["TARGET-001"].code == "TARGET-001"
    assert ERROR_REGISTRY["TARGET-002"].code == "TARGET-002"


def test_target_wire_format():
    """format_error() for both TARGET codes matches the [QRK-...] wire format."""
    from quirk.errors import format_error

    msg1 = format_error("TARGET-001")
    assert msg1.startswith("[QRK-TARGET-001]")
    assert QRK_FORMAT.match(msg1)

    msg2 = format_error("TARGET-002")
    assert msg2.startswith("[QRK-TARGET-002]")
    assert QRK_FORMAT.match(msg2)


def test_target_domain_renders_in_dump_md():
    """_dump_markdown() includes a ## TARGET section with both code rows."""
    from quirk.cli.errors_cmd import _dump_markdown

    md = _dump_markdown()
    assert "## TARGET" in md
    assert "| QRK-TARGET-001 |" in md
    assert "| QRK-TARGET-002 |" in md


def test_targets_module_still_raises_stdlib_exceptions():
    """D-05 library contract: quirk/util/targets.py raises stdlib exceptions only.

    Neither the FileNotFoundError nor the ValueError message may contain
    'QRK-' — proving coding happens at the CLI boundary (D-07), not inside
    the library.
    """
    import quirk.util.targets as targets

    with pytest.raises(FileNotFoundError) as exc_info:
        targets.load_targets_file("/nonexistent/quirk-164-missing.txt")
    assert "QRK-" not in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        targets.parse_target_tokens("10.0.0.0/99")
    assert "QRK-" not in str(exc_info.value)


def test_target_file_error_is_a_value_error():
    """TargetFileError subclasses ValueError — Plan 02's except ValueError branch relies on this."""
    import quirk.util.targets as targets

    assert issubclass(targets.TargetFileError, ValueError)


def test_target_003_is_registered_and_wire_formatted():
    """TARGET-003 covers the unreadable/not-a-regular-file case (WR-01/WR-02).

    Distinct from TARGET-001 on purpose: a directory or a permission-denied
    file DOES exist, so TARGET-001's "could not be found" cause text would be
    inaccurate for it (code review IN-01).
    """
    from quirk.errors import ERROR_REGISTRY, format_error

    assert "TARGET-003" in ERROR_REGISTRY
    rendered = format_error("TARGET-003")
    assert rendered.startswith("[QRK-TARGET-003] ")
    assert " Fix: " in rendered
    assert "could not be found" not in rendered, (
        "TARGET-003 must not reuse TARGET-001's not-found wording (IN-01)"
    )
