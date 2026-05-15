"""Phase 59 LEAK-02: per-connector regression tests verifying that
scan_error writes never carry credential-shaped substrings.

Approach: each connector's exception path funnels through safe_str().
These tests assert (a) safe_str strips the credential payloads we know
real libraries surface, and (b) every modified file imports safe_str.
"""
from __future__ import annotations

import pathlib

import pytest

from quirk.util.safe_exc import safe_str

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

MODIFIED_FILES = [
    "quirk/scanner/vault_connector.py",
    "quirk/scanner/gcp_connector.py",
    "quirk/scanner/tls_scanner.py",
    "quirk/scanner/email_scanner.py",
    "quirk/scanner/broker_scanner.py",
    "quirk/scanner/ssh_scanner.py",
    # quirk/discovery/tls_scanner.py removed in Phase 71 (WR-13, dead duplicate)
    "quirk/cbom/writer.py",
]


# ---------------------------------------------------------------------------
# Behavior tests — verify safe_str strips known credential payloads
# ---------------------------------------------------------------------------

def test_vault_scan_error_strips_token() -> None:
    """T-59-04: Vault hvac token in exception must be stripped."""
    exc = Exception("https://vault:8200?token=s.AbCdEfGhIjKlMnOpQrSt1234")
    result = safe_str(exc)
    assert result == "Exception"


def test_gcp_scan_error_strips_adc_path() -> None:
    """T-59-05: GCP ADC path in exception must be stripped."""
    exc = Exception("/home/user/.config/gcloud/application_default_credentials.json missing")
    result = safe_str(exc)
    assert result == "Exception"


def test_email_scan_error_strips_smtp_password() -> None:
    """T-59-06: SMTP connection string password must be stripped."""
    exc = Exception("smtp://user:secret123@mail.example.com:587 auth failed")
    result = safe_str(exc)
    assert result == "Exception"


def test_broker_scan_error_strips_redis_password() -> None:
    """T-59-06: Redis connection string password must be stripped."""
    exc = Exception("redis://default:supersecret@redis:6379 auth failed")
    result = safe_str(exc)
    assert result == "Exception"


def test_ssh_scan_error_class_name_only_for_creds() -> None:
    """T-59-07: Authorization Bearer header in SSH exception must be stripped."""
    exc = Exception("Authorization: Bearer abc.def.ghi")
    result = safe_str(exc)
    assert result == "Exception"


def test_tls_scan_error_benign_passthrough() -> None:
    """T-59-07: Benign connection errors pass through with message intact."""
    result = safe_str(ConnectionRefusedError("[Errno 111] Connection refused"))
    assert result.startswith("ConnectionRefusedError:")


def test_cbom_writer_scan_error_strips_creds() -> None:
    """T-59-14: CBOM validator text with DB connection string is stripped."""
    exc = Exception("validator config: postgresql://admin:S3cret!@db:5432/x")
    result = safe_str(exc)
    assert result == "Exception"


# ---------------------------------------------------------------------------
# Import-presence gate — all 8 modified files must import safe_str
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("relpath", MODIFIED_FILES)
def test_all_callsites_import_safe_str(relpath: str) -> None:
    path = PROJECT_ROOT / relpath
    text = path.read_text(encoding="utf-8")
    assert "from quirk.util.safe_exc import safe_str" in text, (
        f"{relpath} must import safe_str"
    )
