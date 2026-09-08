"""
Mechanism-backing test for Phase 189 TRIAGE-05 (BACK-59) disposition.

Confirms that `_categorize_tls_error()` classifies an SSL error whose message
contains "WRONG_VERSION_NUMBER" — exactly what a TLS ClientHello sent to a
plaintext SSH banner produces — as `NOT_TLS_ON_PORT`, rather than a generic
`TLS_ERROR`. This is the mechanism half of the rationale recorded inline in
`docs/sample-config.yaml` and in `.planning/HORIZON.md`'s BACK-59 resolution:
the live half (an actual SSH listener producing this exact error against
QU.I.R.K.'s real TLS scan path) is recorded in `189-02-SUMMARY.md`, not here,
since it depends on an external listener being reachable.
"""

import ssl

from quirk.scanner.tls_scanner import _categorize_tls_error


def test_wrong_version_number_categorizes_as_not_tls_on_port():
    err = ssl.SSLError("[SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1082)")
    assert _categorize_tls_error(err) == "NOT_TLS_ON_PORT"


def test_lowercase_wrong_version_number_message_also_categorizes():
    err = ssl.SSLError("wrong version number")
    assert _categorize_tls_error(err) == "NOT_TLS_ON_PORT"


def test_unrelated_ssl_error_does_not_categorize_as_not_tls_on_port():
    err = ssl.SSLError("certificate verify failed")
    assert _categorize_tls_error(err) != "NOT_TLS_ON_PORT"
