"""Tests for quirk/util/url_allowlist.py — URL allowlist validator (Phase 57 / CR-04, CR-06).

Covers:
  - Public IP / domain accepted
  - RFC1918 addresses rejected (internal_ip)
  - Loopback addresses rejected (loopback)
  - Link-local rejected (link_local)
  - Metadata service IPs rejected even with allow_internal=True (metadata_service_ip)
  - Non-http/https schemes rejected (scheme_prefix)
  - allow_internal=True allows RFC1918/loopback/link-local but not metadata IPs
  - redacted_preview control-char stripping
  - ValidationResult type assertions
"""
import pytest

from quirk.util.url_allowlist import (
    validate_external_url,
    ValidationResult,
    RC_INTERNAL_IP,
    RC_LOOPBACK,
    RC_LINK_LOCAL,
    RC_METADATA_SERVICE_IP,
    RC_SCHEME_PREFIX,
)


# ---------------------------------------------------------------------------
# Main parametrized behaviour table
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,expected_ok,expected_reason", [
    # Public domain — allowed
    ("https://example.com", True, ""),
    # RFC1918 ranges — rejected
    ("http://10.0.0.5/x", False, RC_INTERNAL_IP),
    ("http://192.168.1.1/x", False, RC_INTERNAL_IP),
    ("http://172.16.0.1/x", False, RC_INTERNAL_IP),
    # Loopback — rejected
    ("http://127.0.0.1/x", False, RC_LOOPBACK),
    ("http://[::1]/x", False, RC_LOOPBACK),
    # Metadata service — rejected even with default allow_internal
    ("http://169.254.169.254/latest/meta-data/", False, RC_METADATA_SERVICE_IP),
    ("http://[fd00:ec2::254]/", False, RC_METADATA_SERVICE_IP),
    # Link-local (non-metadata) — rejected
    ("http://169.254.0.5/x", False, RC_LINK_LOCAL),
    # Non-http/https schemes — rejected
    ("file:///etc/passwd", False, RC_SCHEME_PREFIX),
    ("gopher://x/", False, RC_SCHEME_PREFIX),
], ids=[
    "public_domain",
    "rfc1918_10",
    "rfc1918_192",
    "rfc1918_172",
    "loopback_v4",
    "loopback_v6",
    "metadata_v4",
    "metadata_v6",
    "link_local",
    "scheme_file",
    "scheme_gopher",
])
def test_validate_external_url_defaults(url, expected_ok, expected_reason):
    result = validate_external_url(url)
    assert result.ok == expected_ok
    assert result.reason == expected_reason
    if not expected_ok:
        assert len(result.redacted_preview) <= 32
        # No ASCII control chars
        for ch in result.redacted_preview:
            assert ord(ch) >= 0x20 or ch in ("\t",), f"Control char in preview: {ord(ch):#04x}"


# ---------------------------------------------------------------------------
# allow_internal=True behaviour
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,expected_ok,expected_reason", [
    # RFC1918 allowed
    ("http://10.0.0.5/x", True, ""),
    # Metadata IP is STILL blocked even with allow_internal=True
    ("http://169.254.169.254/", False, RC_METADATA_SERVICE_IP),
    ("http://[fd00:ec2::254]/", False, RC_METADATA_SERVICE_IP),
], ids=[
    "allow_internal_rfc1918",
    "allow_internal_metadata_still_blocked_v4",
    "allow_internal_metadata_still_blocked_v6",
])
def test_validate_external_url_allow_internal(url, expected_ok, expected_reason):
    result = validate_external_url(url, allow_internal=True)
    assert result.ok == expected_ok
    assert result.reason == expected_reason


# ---------------------------------------------------------------------------
# redacted_preview quality
# ---------------------------------------------------------------------------

def test_control_char_stripping_in_preview():
    """Control characters in the URL should be stripped from redacted_preview."""
    url = "http://example.com/\x00\x01\x07path"
    result = validate_external_url(url)
    # Public hostname — ok=True; but let's also check a definitely-rejected URL
    # to exercise the preview path with control chars.
    url_bad = "file://\x00\x01example"
    result_bad = validate_external_url(url_bad)
    assert not result_bad.ok
    for ch in result_bad.redacted_preview:
        assert ord(ch) >= 0x20, f"Control char 0x{ord(ch):02x} found in preview"


def test_redacted_preview_max_length():
    """redacted_preview must not exceed 32 chars."""
    # Long RFC1918 URL to force preview truncation
    long_url = "http://10.0.0.1/" + "a" * 200
    result = validate_external_url(long_url)
    assert not result.ok
    assert len(result.redacted_preview) <= 32


# ---------------------------------------------------------------------------
# Type assertions
# ---------------------------------------------------------------------------

def test_returns_validation_result_instance():
    """validate_external_url must return a ValidationResult instance (not tuple)."""
    result = validate_external_url("https://example.com")
    assert isinstance(result, ValidationResult)


def test_ok_result_has_empty_reason_and_preview():
    """ok=True results must have empty reason and redacted_preview."""
    result = validate_external_url("https://example.com")
    assert result.ok is True
    assert result.reason == ""
    assert result.redacted_preview == ""
