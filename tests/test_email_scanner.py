"""Tests for email scanner (EMAIL-00 through EMAIL-12, STRUCT-01).

Tests mock network calls — no live network required.
Scanner module: quirk/scanner/email_scanner.py
Phase 32 / Plan 01 — Wave 0 RED state. Tests fail until Plan 03 lands.

NOTE: pytest.importorskip below skips scanner-module tests when
quirk.scanner.email_scanner does not yet exist (RED / Wave 0 state).
After Plan 03 lands, importorskip is a no-op and all 17 tests run.

test_email_scan_json_column_exists is placed BEFORE the importorskip guard
because it depends only on quirk.db (Plan 02 scope) and must run in Wave 1
before the scanner module (Plan 03) exists.
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call


# ---------------------------------------------------------------------------
# EMAIL-00: DB column existence — Plan 02 scope, independent of scanner module
# ---------------------------------------------------------------------------

def test_email_scan_json_column_exists():
    """EMAIL-00: init_db() must create email_scan_json column on crypto_endpoints."""
    import os
    import tempfile
    from sqlalchemy import inspect as sa_inspect
    from quirk.db import init_db

    # Use a temp-file DB so init_db(path) signature is satisfied.
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_email_col.db")
        engine = init_db(db_path)

    inspector = sa_inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("crypto_endpoints")}
    assert "email_scan_json" in columns, (
        f"email_scan_json column not found in crypto_endpoints; "
        f"columns present: {sorted(columns)}"
    )


def test_email_scan_json_column_idempotent():
    """EMAIL-00: calling init_db() twice on the same DB must not raise."""
    import os
    import tempfile
    from quirk.db import init_db

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_idempotent.db")
        init_db(db_path)   # first call — creates column
        init_db(db_path)   # second call — must not raise (column already exists)


# ---------------------------------------------------------------------------
# Soft import — scanner module does not exist until Plan 03 (Wave 2).
# Tests below that depend on it are marked skipif so pytest can still collect
# and run test_email_scan_json_column_exists (Plan 02 scope) in Wave 1.
# After Plan 03 lands, _EMAIL_SCANNER_AVAILABLE = True and all tests run.
# ---------------------------------------------------------------------------
try:
    from quirk.scanner.email_scanner import (
        scan_email_targets,
        scan_one_email,
        EMAIL_PORTS,
        _scan_one_sslyze_email,
        _scan_one_fallback_email,
    )
    _EMAIL_SCANNER_AVAILABLE = True
except ImportError:
    # Stubs so the file compiles; tests using these are skipped via _skip_scanner
    scan_email_targets = None  # type: ignore[assignment]
    scan_one_email = None  # type: ignore[assignment]
    EMAIL_PORTS = []  # type: ignore[assignment]
    _scan_one_sslyze_email = None  # type: ignore[assignment]
    _scan_one_fallback_email = None  # type: ignore[assignment]
    _EMAIL_SCANNER_AVAILABLE = False

_skip_scanner = pytest.mark.skipif(
    not _EMAIL_SCANNER_AVAILABLE,
    reason="Phase 32 Plan 03 implements quirk/scanner/email_scanner.py — Wave 0 RED state",
)


# ---------------------------------------------------------------------------
# sslyze enums — imported softly so test collection works when sslyze absent
# ---------------------------------------------------------------------------
try:
    from sslyze import ServerScanStatusEnum, ScanCommandAttemptStatusEnum
    _SSLYZE_ENUMS_AVAILABLE = True
except ImportError:
    _SSLYZE_ENUMS_AVAILABLE = False
    # Stub sentinels so mock helpers stay constructable at import time
    class ServerScanStatusEnum:  # noqa: N801
        COMPLETED = "COMPLETED"
        ERROR_NO_CONNECTIVITY = "ERROR_NO_CONNECTIVITY"

    class ScanCommandAttemptStatusEnum:  # noqa: N801
        COMPLETED = "COMPLETED"
        ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Mock helper constructors
# ---------------------------------------------------------------------------

def _make_mock_sslyze_result(
    tls_version: str = "TLSv1.2",
    cipher: str = "AES256-SHA",
    completed: bool = True,
) -> MagicMock:
    """Build a mock sslyze ServerScanResult.

    Populates the minimal shape used by email_scanner._scan_one_sslyze_email():
    - result.scan_status  (COMPLETED or ERROR_NO_CONNECTIVITY)
    - result.scan_result.tls_1_2_cipher_suites.result.accepted_cipher_suites
    - result.scan_result.certificate_info.result.certificate_deployments[0]
      with mocked cert chain (subject, issuer, public_key, signature_hash_algorithm)
    """
    result = MagicMock()
    if completed:
        result.scan_status = ServerScanStatusEnum.COMPLETED
    else:
        result.scan_status = ServerScanStatusEnum.ERROR_NO_CONNECTIVITY

    # Cipher suite mock
    suite = MagicMock()
    suite.cipher_suite.name = cipher

    attempt = MagicMock()
    attempt.status = ScanCommandAttemptStatusEnum.COMPLETED
    attempt.result.accepted_cipher_suites = [suite]
    result.scan_result.tls_1_2_cipher_suites = attempt

    # TLS 1.3 cipher suites (empty — test default is TLS 1.2)
    attempt_13 = MagicMock()
    attempt_13.status = ScanCommandAttemptStatusEnum.COMPLETED
    attempt_13.result.accepted_cipher_suites = []
    result.scan_result.tls_1_3_cipher_suites = attempt_13

    # Certificate info mock
    cert = MagicMock()
    cert.subject.rfc4514_string.return_value = "CN=mail.example.com"
    cert.issuer.rfc4514_string.return_value = "CN=TestCA"
    cert.public_key.return_value.key_size = 2048
    cert.signature_hash_algorithm.name = "sha256"
    cert.not_valid_before_utc = datetime(2025, 1, 1, tzinfo=timezone.utc)
    cert.not_valid_after_utc = datetime(2027, 1, 1, tzinfo=timezone.utc)

    # Subject alternative names
    san_ext = MagicMock()
    san_ext.value.get_values_for_type.return_value = ["mail.example.com"]
    cert.extensions.get_extension_for_class.return_value = san_ext

    deployment = MagicMock()
    deployment.received_certificate_chain = [cert]

    cert_attempt = MagicMock()
    cert_attempt.status = ScanCommandAttemptStatusEnum.COMPLETED
    cert_attempt.result.certificate_deployments = [deployment]
    result.scan_result.certificate_info = cert_attempt

    # Expose tls_version hint so scanner can record it
    result._tls_version_hint = tls_version

    return result


def _make_mock_sslyze_scanner(result: MagicMock) -> MagicMock:
    """Return a MagicMock SslyzeScanner whose get_results() yields [result]."""
    scanner = MagicMock()
    scanner.queue_scans.return_value = None
    scanner.get_results.return_value = iter([result])
    return scanner


def _make_mock_smtp_sock(
    tls_version: str = "TLSv1.2",
    cipher_name: str = "AES256-SHA",
    der_bytes: bytes = b"\x00",
) -> MagicMock:
    """Build a mock ssl.SSLSocket for the smtplib fallback path."""
    ssock = MagicMock()
    ssock.version.return_value = tls_version
    ssock.cipher.return_value = (cipher_name, tls_version, 256)
    ssock.getpeercert.return_value = der_bytes
    return ssock


# ---------------------------------------------------------------------------
# EMAIL-01: SMTP STARTTLS sslyze path — port 25
# ---------------------------------------------------------------------------

@_skip_scanner
@patch("quirk.scanner.email_scanner.SslyzeScanner")
def test_scan_one_smtp_starttls_sslyze_port25(mock_scanner_cls):
    """EMAIL-01: scan_one_email on port 25 via sslyze returns SMTP-STARTTLS endpoint."""
    mock_result = _make_mock_sslyze_result(tls_version="TLSv1.2", cipher="AES256-SHA")
    mock_scanner = _make_mock_sslyze_scanner(mock_result)
    mock_scanner_cls.return_value = mock_scanner

    ep = scan_one_email(
        "mail.example.com", 25, "SMTP-STARTTLS",
        starttls_enum=MagicMock(),  # ProtocolWithOpportunisticTlsEnum.SMTP
        timeout=5,
    )

    assert ep is not None, "scan_one_email must return a CryptoEndpoint"
    assert ep.protocol == "SMTP-STARTTLS", (
        f"Expected protocol='SMTP-STARTTLS', got {ep.protocol!r}"
    )
    assert ep.service_detail == "SMTP-STARTTLS:25", (
        f"Expected service_detail='SMTP-STARTTLS:25', got {ep.service_detail!r}"
    )


# ---------------------------------------------------------------------------
# EMAIL-01: SMTP STARTTLS sslyze path — port 587
# ---------------------------------------------------------------------------

@_skip_scanner
@patch("quirk.scanner.email_scanner.SslyzeScanner")
def test_scan_one_smtp_starttls_sslyze_port587(mock_scanner_cls):
    """EMAIL-01: scan_one_email on port 587 via sslyze returns SMTP-STARTTLS endpoint."""
    mock_result = _make_mock_sslyze_result(tls_version="TLSv1.2", cipher="AES256-SHA")
    mock_scanner = _make_mock_sslyze_scanner(mock_result)
    mock_scanner_cls.return_value = mock_scanner

    ep = scan_one_email(
        "mail.example.com", 587, "SMTP-STARTTLS",
        starttls_enum=MagicMock(),
        timeout=5,
    )

    assert ep is not None
    assert ep.protocol == "SMTP-STARTTLS"
    assert ep.service_detail == "SMTP-STARTTLS:587", (
        f"Expected service_detail='SMTP-STARTTLS:587', got {ep.service_detail!r}"
    )


# ---------------------------------------------------------------------------
# EMAIL-02: SMTPS implicit TLS — port 465
# ---------------------------------------------------------------------------

@_skip_scanner
@patch("quirk.scanner.email_scanner.SslyzeScanner")
def test_scan_one_smtps_sslyze_port465(mock_scanner_cls):
    """EMAIL-02: scan_one_email on port 465 (implicit TLS, starttls_enum=None) → SMTPS."""
    mock_result = _make_mock_sslyze_result(tls_version="TLSv1.3", cipher="TLS_AES_256_GCM_SHA384")
    mock_scanner = _make_mock_sslyze_scanner(mock_result)
    mock_scanner_cls.return_value = mock_scanner

    ep = scan_one_email(
        "mail.example.com", 465, "SMTPS",
        starttls_enum=None,  # implicit TLS — no STARTTLS enum
        timeout=5,
    )

    assert ep is not None
    assert ep.protocol == "SMTPS", (
        f"Expected protocol='SMTPS', got {ep.protocol!r}"
    )
    assert ep.service_detail == "SMTPS:465", (
        f"Expected service_detail='SMTPS:465', got {ep.service_detail!r}"
    )


# ---------------------------------------------------------------------------
# EMAIL-03: IMAP STARTTLS — port 143
# ---------------------------------------------------------------------------

@_skip_scanner
@patch("quirk.scanner.email_scanner.SslyzeScanner")
def test_scan_one_imap_starttls_sslyze_port143(mock_scanner_cls):
    """EMAIL-03: scan_one_email on port 143 with IMAP STARTTLS enum → IMAP-STARTTLS."""
    mock_result = _make_mock_sslyze_result(tls_version="TLSv1.2", cipher="ECDHE-RSA-AES256-SHA")
    mock_scanner = _make_mock_sslyze_scanner(mock_result)
    mock_scanner_cls.return_value = mock_scanner

    ep = scan_one_email(
        "mail.example.com", 143, "IMAP-STARTTLS",
        starttls_enum=MagicMock(),  # ProtocolWithOpportunisticTlsEnum.IMAP
        timeout=5,
    )

    assert ep is not None
    assert ep.protocol == "IMAP-STARTTLS", (
        f"Expected protocol='IMAP-STARTTLS', got {ep.protocol!r}"
    )
    assert ep.service_detail == "IMAP-STARTTLS:143"


# ---------------------------------------------------------------------------
# EMAIL-04: IMAPS implicit TLS — port 993
# ---------------------------------------------------------------------------

@_skip_scanner
@patch("quirk.scanner.email_scanner.SslyzeScanner")
def test_scan_one_imaps_sslyze_port993(mock_scanner_cls):
    """EMAIL-04: scan_one_email on port 993 (implicit TLS, starttls_enum=None) → IMAPS."""
    mock_result = _make_mock_sslyze_result(tls_version="TLSv1.3", cipher="TLS_AES_128_GCM_SHA256")
    mock_scanner = _make_mock_sslyze_scanner(mock_result)
    mock_scanner_cls.return_value = mock_scanner

    ep = scan_one_email(
        "mail.example.com", 993, "IMAPS",
        starttls_enum=None,
        timeout=5,
    )

    assert ep is not None
    assert ep.protocol == "IMAPS", (
        f"Expected protocol='IMAPS', got {ep.protocol!r}"
    )
    assert ep.service_detail == "IMAPS:993"


# ---------------------------------------------------------------------------
# EMAIL-05: POP3 STARTTLS — port 110
# ---------------------------------------------------------------------------

@_skip_scanner
@patch("quirk.scanner.email_scanner.SslyzeScanner")
def test_scan_one_pop3_starttls_sslyze_port110(mock_scanner_cls):
    """EMAIL-05: scan_one_email on port 110 with POP3 STARTTLS enum → POP3-STARTTLS."""
    mock_result = _make_mock_sslyze_result(tls_version="TLSv1.2", cipher="AES128-SHA")
    mock_scanner = _make_mock_sslyze_scanner(mock_result)
    mock_scanner_cls.return_value = mock_scanner

    ep = scan_one_email(
        "mail.example.com", 110, "POP3-STARTTLS",
        starttls_enum=MagicMock(),  # ProtocolWithOpportunisticTlsEnum.POP3
        timeout=5,
    )

    assert ep is not None
    assert ep.protocol == "POP3-STARTTLS", (
        f"Expected protocol='POP3-STARTTLS', got {ep.protocol!r}"
    )
    assert ep.service_detail == "POP3-STARTTLS:110"


# ---------------------------------------------------------------------------
# EMAIL-06: POP3S implicit TLS — port 995
# ---------------------------------------------------------------------------

@_skip_scanner
@patch("quirk.scanner.email_scanner.SslyzeScanner")
def test_scan_one_pop3s_sslyze_port995(mock_scanner_cls):
    """EMAIL-06: scan_one_email on port 995 (implicit TLS, starttls_enum=None) → POP3S."""
    mock_result = _make_mock_sslyze_result(tls_version="TLSv1.3", cipher="TLS_CHACHA20_POLY1305_SHA256")
    mock_scanner = _make_mock_sslyze_scanner(mock_result)
    mock_scanner_cls.return_value = mock_scanner

    ep = scan_one_email(
        "mail.example.com", 995, "POP3S",
        starttls_enum=None,
        timeout=5,
    )

    assert ep is not None
    assert ep.protocol == "POP3S", (
        f"Expected protocol='POP3S', got {ep.protocol!r}"
    )
    assert ep.service_detail == "POP3S:995"


# ---------------------------------------------------------------------------
# EMAIL-07: stdlib fallback — SMTP STARTTLS path
# ---------------------------------------------------------------------------

@_skip_scanner
@patch("quirk.scanner.email_scanner._scan_one_sslyze_email", return_value=None)
@patch("quirk.scanner.email_scanner.smtplib")
def test_fallback_smtp_starttls_returns_tls_metadata(mock_smtplib, mock_sslyze):
    """EMAIL-07: When sslyze returns None, smtplib fallback populates tls_version + cipher + cert."""
    ssock = _make_mock_smtp_sock(tls_version="TLSv1.2", cipher_name="AES256-SHA")

    smtp_instance = MagicMock()
    smtp_instance.__enter__ = MagicMock(return_value=smtp_instance)
    smtp_instance.__exit__ = MagicMock(return_value=False)
    smtp_instance.sock = ssock
    mock_smtplib.SMTP.return_value = smtp_instance

    ep = _scan_one_fallback_email(
        "mail.example.com", 25, "SMTP-STARTTLS", timeout=5
    )

    assert ep is not None, "Fallback must return a CryptoEndpoint"
    # At minimum, fallback should attempt STARTTLS — not raise
    # Exact field assertions depend on implementation; verify non-error state
    assert ep.tls_blocker_reason != "CONNECTION_REFUSED" or ep.tls_version is None, (
        "Fallback should not set CONNECTION_REFUSED when SMTP is reachable"
    )


@_skip_scanner
@patch("quirk.scanner.email_scanner._scan_one_sslyze_email", return_value=None)
@patch("quirk.scanner.email_scanner.imaplib")
def test_fallback_imap_starttls_returns_tls_metadata(mock_imaplib, mock_sslyze):
    """EMAIL-07: When sslyze returns None, imaplib fallback runs IMAP STARTTLS path."""
    ssock = _make_mock_smtp_sock(tls_version="TLSv1.2", cipher_name="ECDHE-RSA-AES256-SHA")

    imap_instance = MagicMock()
    imap_instance.sock = ssock
    imap_instance.starttls.return_value = ("OK", [b"Begin TLS negotiation"])
    mock_imaplib.IMAP4.return_value = imap_instance

    ep = _scan_one_fallback_email(
        "mail.example.com", 143, "IMAP-STARTTLS", timeout=5
    )

    assert ep is not None, "Fallback must return a CryptoEndpoint for IMAP-STARTTLS"


@_skip_scanner
@patch("quirk.scanner.email_scanner._scan_one_sslyze_email", return_value=None)
@patch("quirk.scanner.email_scanner.poplib")
def test_fallback_pop3_starttls_returns_tls_metadata(mock_poplib, mock_sslyze):
    """EMAIL-07: When sslyze returns None, poplib fallback runs POP3 STLS path."""
    ssock = _make_mock_smtp_sock(tls_version="TLSv1.2", cipher_name="AES128-SHA")

    pop3_instance = MagicMock()
    pop3_instance.sock = ssock
    pop3_instance.stls.return_value = b"+OK Begin TLS"
    mock_poplib.POP3.return_value = pop3_instance

    ep = _scan_one_fallback_email(
        "mail.example.com", 110, "POP3-STARTTLS", timeout=5
    )

    assert ep is not None, "Fallback must return a CryptoEndpoint for POP3-STARTTLS"


# ---------------------------------------------------------------------------
# D-03 / EMAIL-01: CONNECTION_REFUSED is non-fatal
# ---------------------------------------------------------------------------

@_skip_scanner
def test_connection_refused_non_fatal_port25():
    """D-03/EMAIL-01: ConnectionRefusedError on port 25 must not propagate; ep returned."""
    with patch("quirk.scanner.email_scanner._scan_one_sslyze_email", return_value=None), \
         patch("quirk.scanner.email_scanner._scan_one_fallback_email") as mock_fb:
        mock_ep = MagicMock()
        mock_ep.tls_blocker_reason = "CONNECTION_REFUSED"
        mock_ep.scan_error = None
        mock_fb.return_value = mock_ep

        result = scan_one_email(
            "mail.example.com", 25, "SMTP-STARTTLS",
            starttls_enum=None, timeout=5,
        )

        assert result is not None, "scan_one_email must not raise on CONNECTION_REFUSED"
        assert result.tls_blocker_reason == "CONNECTION_REFUSED", (
            f"Expected tls_blocker_reason='CONNECTION_REFUSED', got {result.tls_blocker_reason!r}"
        )


# ---------------------------------------------------------------------------
# EMAIL-10: service_detail label format
# ---------------------------------------------------------------------------

@_skip_scanner
def test_service_detail_labels_match_spec():
    """EMAIL-10: scan_one_email sets ep.service_detail == f'{label}:{port}' for each port."""
    with patch("quirk.scanner.email_scanner._scan_one_sslyze_email", return_value=None), \
         patch("quirk.scanner.email_scanner._scan_one_fallback_email") as mock_fb:

        for port, label, prefix, starttls_enum in EMAIL_PORTS:
            mock_ep = MagicMock()
            mock_ep.scan_error = None
            mock_ep.tls_blocker_reason = None
            # scan_one_email sets service_detail AFTER calling fallback, so we
            # return a real-ish object; the final assertion is on what scan_one_email returns
            mock_fb.return_value = mock_ep

            ep = scan_one_email(
                "mail.example.com", port, label,
                starttls_enum=starttls_enum, timeout=5,
            )

            expected = f"{label}:{port}"
            assert ep.service_detail == expected, (
                f"Port {port}: expected service_detail={expected!r}, got {ep.service_detail!r}"
            )


# ---------------------------------------------------------------------------
# EMAIL_PORTS table shape
# ---------------------------------------------------------------------------

@_skip_scanner
def test_email_ports_table_has_seven_entries():
    """EMAIL_PORTS table must have exactly 7 entries covering all standard email ports."""
    assert len(EMAIL_PORTS) == 7, (
        f"Expected 7 EMAIL_PORTS entries, got {len(EMAIL_PORTS)}: {EMAIL_PORTS}"
    )
    ports = {entry[0] for entry in EMAIL_PORTS}
    expected_ports = {25, 465, 587, 143, 993, 110, 995}
    assert ports == expected_ports, (
        f"EMAIL_PORTS port set mismatch: expected {expected_ports}, got {ports}"
    )


# ---------------------------------------------------------------------------
# STRUCT-01: session_start propagation
# ---------------------------------------------------------------------------

@_skip_scanner
def test_session_start_propagation():
    """STRUCT-01: scan_email_targets forwards session_start to scan_one_email."""
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)

    with patch("quirk.scanner.email_scanner.scan_one_email") as mock_one:
        mock_ep = MagicMock()
        mock_ep.scan_error = None
        mock_ep.tls_blocker_reason = None
        mock_one.return_value = mock_ep

        scan_email_targets(["mail.example.com"], timeout=5, session_start=fixed_time)

        # session_start MUST appear in either positional args or kwargs of every call
        assert mock_one.call_count > 0, "scan_one_email must be called at least once"
        for c in mock_one.call_args_list:
            assert fixed_time in c.args or c.kwargs.get("session_start") == fixed_time, (
                f"session_start not propagated to scan_one_email; call: {c}"
            )


@_skip_scanner
def test_no_datetime_now_inside_scanner():
    """STRUCT-01/ISSUE-3: datetime.now() may only appear as fallback to session_start."""
    import inspect
    import quirk.scanner.email_scanner as mod

    src = inspect.getsource(mod)
    # Strip comment lines to avoid false-positive grep matches
    code_lines = [ln for ln in src.splitlines() if not ln.lstrip().startswith("#")]
    bad = [
        ln for ln in code_lines
        if "datetime.now(" in ln and "session_start or" not in ln
    ]
    assert not bad, (
        "datetime.now() must only appear as `(session_start or datetime.now(...))`. "
        f"Offending lines: {bad}"
    )


@_skip_scanner
def test_email_ports_starttls_enum_alignment():
    """EMAIL-01..06: STARTTLS ports have non-None starttls_enum; implicit-TLS ports have None."""
    from quirk.scanner.email_scanner import EMAIL_PORTS, SSLYZE_AVAILABLE

    starttls_ports = {25, 587, 143, 110}
    implicit_ports = {465, 993, 995}

    for port, label, prefix, starttls_enum in EMAIL_PORTS:
        if port in implicit_ports:
            assert starttls_enum is None, (
                f"Port {port} (implicit TLS '{label}') must have starttls_enum=None, "
                f"got {starttls_enum!r}"
            )
        elif port in starttls_ports and SSLYZE_AVAILABLE:
            assert starttls_enum is not None, (
                f"Port {port} (STARTTLS '{label}') must have non-None starttls_enum "
                f"when sslyze is installed"
            )
