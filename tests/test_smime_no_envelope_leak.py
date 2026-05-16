"""Phase 79 SMIME-04 — Privacy invariant test.

Feeds `scan_smime_targets` a target object carrying sentinel IMAP-style
envelope fields (`to`, `from_`, `subject`, `message_id`) AND scans
through real DER fixtures. Asserts that NONE of the sentinel strings
appear anywhere in the returned endpoint list or its `smime_scan_json`
blobs.

The scanner must NEVER read or echo IMAP envelope metadata. This is a
content-absence assertion against the full serialised output.
"""
from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace
from unittest.mock import patch

from quirk.scanner import smime_scanner
from quirk.scanner.smime_scanner import scan_smime_targets


FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures" / "smime"

SENTINELS = (
    "SENTINEL_TO_FIELD",
    "SENTINEL_FROM_FIELD",
    "SENTINEL_SUBJECT_FIELD",
    "SENTINEL_MESSAGEID_FIELD",
)


def _sentinel_target() -> SimpleNamespace:
    """A target object carrying IMAP-style envelope fields. The scanner
    must ignore these entirely."""
    return SimpleNamespace(
        host="ldap.example.com",
        port=389,
        realm="QUIRK.LAB",
        to="SENTINEL_TO_FIELD",
        from_="SENTINEL_FROM_FIELD",
        subject="SENTINEL_SUBJECT_FIELD",
        message_id="SENTINEL_MESSAGEID_FIELD",
    )


def _entry(uid: str, der: bytes) -> dict:
    return {
        "type": "searchResEntry",
        "dn": f"uid={uid},ou=people,dc=quirk,dc=lab",
        "raw_attributes": {
            "userSMIMECertificate": [der],
            "cn": [uid.encode()],
            "uid": [uid.encode()],
        },
    }


def _serialise(endpoints) -> str:
    """Concatenate every public string field of every endpoint plus the
    `smime_scan_json` blob into one searchable blob."""
    parts: list[str] = []
    for ep in endpoints:
        for attr_name in (
            "host",
            "port",
            "protocol",
            "service_detail",
            "severity",
            "cert_pubkey_alg",
            "cert_sig_alg",
            "scan_error",
            "smime_scan_json",
        ):
            val = getattr(ep, attr_name, None)
            if val is not None:
                parts.append(str(val))
    return "\n".join(parts)


def test_no_imap_envelope_fields_in_smime_output_safe_cert():
    """With carol.der (SAFE — zero endpoints), the sentinel fields on
    the target must not leak through any side-channel."""
    entries = [_entry("carol", (FIXTURE_DIR / "carol.der").read_bytes())]
    with patch.object(smime_scanner, "LDAP3_AVAILABLE", True), \
         patch.object(smime_scanner, "_bind_and_search", return_value=iter(entries)):
        endpoints = scan_smime_targets([_sentinel_target()], timeout=5)
    # carol → no findings; the blob is empty, but the assertion still
    # holds (and prevents future regressions where the scanner stuffs
    # target metadata into a tracing field).
    blob = _serialise(endpoints)
    for sentinel in SENTINELS:
        assert sentinel not in blob, (
            f"SMIME-04 envelope leak: {sentinel!r} found in scanner output"
        )


def test_no_imap_envelope_fields_in_smime_output_high_cert():
    """With alice.der (HIGH — endpoint emitted with populated
    smime_scan_json), assert NONE of the sentinel fields surface in any
    string field or the JSON blob."""
    entries = [_entry("alice", (FIXTURE_DIR / "alice.der").read_bytes())]
    with patch.object(smime_scanner, "LDAP3_AVAILABLE", True), \
         patch.object(smime_scanner, "_bind_and_search", return_value=iter(entries)):
        endpoints = scan_smime_targets([_sentinel_target()], timeout=5)

    assert len(endpoints) == 1, "alice should yield one HIGH endpoint"
    ep = endpoints[0]
    assert ep.smime_scan_json, "smime_scan_json must be populated for HIGH"

    # The JSON parses cleanly and contains zero sentinel substrings.
    parsed = json.loads(ep.smime_scan_json)
    parsed_str = json.dumps(parsed)
    for sentinel in SENTINELS:
        assert sentinel not in parsed_str, (
            f"SMIME-04 envelope leak in smime_scan_json: {sentinel!r}"
        )

    # And the same assertion against every public string field.
    blob = _serialise(endpoints)
    for sentinel in SENTINELS:
        assert sentinel not in blob, (
            f"SMIME-04 envelope leak in endpoint field: {sentinel!r}"
        )
