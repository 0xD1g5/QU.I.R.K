"""Phase 77 D-01 / scanners-protocol/IN-01: probe-rationale comment exists.

Closes scanners-protocol/IN-01: `_try_handshake` in
``quirk/scanner/tls_capabilities.py`` must carry a comment block explaining
WHY the function optionally probes TLS 1.0/1.1 (legacy-server posture
inventory for CBOM, not a real handshake-downgrade).
"""
from __future__ import annotations

import pathlib


SOURCE = pathlib.Path("quirk/scanner/tls_capabilities.py")


def test_try_handshake_carries_legacy_server_posture_comment() -> None:
    src = SOURCE.read_text(encoding="utf-8")
    assert (
        "legacy-server posture" in src
    ), "Phase 77 D-01: _try_handshake must carry a `legacy-server posture` rationale comment"


def test_try_handshake_comment_cites_audit_row() -> None:
    src = SOURCE.read_text(encoding="utf-8")
    assert (
        "scanners-protocol/IN-01" in src
    ), "Phase 77 D-01: rationale comment must cite audit row scanners-protocol/IN-01"
