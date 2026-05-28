"""Phase 120 / Plan 01 / Task 1 — SSRF regression tests.

Covers SP-01 / AC-01 / AC-02 / CD-01 / CD-02 from the 2026-05-27 audit:

  1. IPv6 AAAA bypass (host whose AAAA resolves to a blocked range MUST be rejected).
  2. Fail-closed on socket.gaierror (DNS failure MUST NOT return ok=True).
  3. Metadata HOSTNAME aliases (metadata.google.internal etc.) rejected before resolution.
  4. Dual-stack hostname where ANY returned address is blocked → reject.
  5. Genuine public IP still passes.
"""
from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from quirk.util.url_allowlist import (
    RC_INTERNAL_IP,
    RC_LINK_LOCAL,
    RC_LOOPBACK,
    RC_METADATA_SERVICE_IP,
    RC_SCHEME_PREFIX,
    RC_DNS_FAILURE,
    ValidationResult,
    validate_external_url,
)


def _ai_v6(addr: str):
    """Build a getaddrinfo-shaped IPv6 result tuple."""
    return (socket.AF_INET6, socket.SOCK_STREAM, 0, "", (addr, 0, 0, 0))


def _ai_v4(addr: str):
    """Build a getaddrinfo-shaped IPv4 result tuple."""
    return (socket.AF_INET, socket.SOCK_STREAM, 0, "", (addr, 0))


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_ipv6_aaaa_loopback_rejected(mock_gai):
    """AAAA resolves to ::1 — must reject as loopback, not be silently allowed."""
    mock_gai.return_value = [_ai_v6("::1")]
    r = validate_external_url("http://v6-loop.example/")
    assert r.ok is False
    assert r.reason == RC_LOOPBACK


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_ipv6_aaaa_link_local_rejected(mock_gai):
    """AAAA fe80::1 — IPv6 link-local must be blocked."""
    mock_gai.return_value = [_ai_v6("fe80::1")]
    r = validate_external_url("http://v6-ll.example/")
    assert r.ok is False
    assert r.reason == RC_LINK_LOCAL


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_ipv6_aaaa_ula_rejected(mock_gai):
    """AAAA fc00::1 — IPv6 ULA (private) must be blocked."""
    mock_gai.return_value = [_ai_v6("fc00::1")]
    r = validate_external_url("http://v6-ula.example/")
    assert r.ok is False
    assert r.reason == RC_INTERNAL_IP


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_dual_stack_blocked_when_any_address_blocked(mock_gai):
    """Public A + loopback AAAA → still reject. We check every returned address."""
    mock_gai.return_value = [_ai_v4("8.8.8.8"), _ai_v6("::1")]
    r = validate_external_url("http://dualstack.example/")
    assert r.ok is False
    assert r.reason == RC_LOOPBACK


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_ipv4_hostname_resolving_to_metadata_rejected(mock_gai):
    """A resolves to 169.254.169.254 → metadata reject, never the loopback/linklocal class."""
    mock_gai.return_value = [_ai_v4("169.254.169.254")]
    r = validate_external_url("http://aws-meta.example/")
    assert r.ok is False
    assert r.reason == RC_METADATA_SERVICE_IP


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_gaierror_fails_closed(mock_gai):
    """DNS failure (gaierror) must return ok=False — NOT fail-open as the old impl did."""
    mock_gai.side_effect = socket.gaierror("name resolution failed")
    r = validate_external_url("http://nonexistent.invalid/")
    assert r.ok is False
    assert r.reason == RC_DNS_FAILURE


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_oserror_fails_closed(mock_gai):
    """Any OSError from resolver must also fail closed."""
    mock_gai.side_effect = OSError("resolver explosion")
    r = validate_external_url("http://flaky-dns.example/")
    assert r.ok is False
    assert r.reason == RC_DNS_FAILURE


@pytest.mark.parametrize("host_alias", [
    "metadata.google.internal",
    "METADATA.google.internal",  # case insensitive
    "metadata",
    "metadata.goog",
])
def test_metadata_hostname_aliases_rejected(host_alias):
    """Metadata hostname aliases must be blocked BEFORE DNS resolution — no IP lookup needed."""
    r = validate_external_url(f"http://{host_alias}/computeMetadata/v1/")
    assert r.ok is False
    assert r.reason == RC_METADATA_SERVICE_IP


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_genuine_public_ipv4_still_passes(mock_gai):
    """Regression guard: genuine 8.8.8.8 still passes (no over-blocking)."""
    # 8.8.8.8 is an IP literal — no DNS lookup; mock should not be called.
    r = validate_external_url("http://8.8.8.8/")
    assert r.ok is True


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_genuine_public_hostname_passes(mock_gai):
    """Hostname resolving to public IP via getaddrinfo passes."""
    mock_gai.return_value = [_ai_v4("8.8.8.8")]
    r = validate_external_url("http://dns.google/")
    assert r.ok is True


def test_scheme_rejection_still_works():
    """Existing scheme-reject behaviour preserved."""
    assert validate_external_url("file:///etc/passwd").reason == RC_SCHEME_PREFIX
    assert validate_external_url("gopher://x/").reason == RC_SCHEME_PREFIX


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_allow_internal_bypass_does_not_unblock_metadata(mock_gai):
    """allow_internal=True must still block metadata IPs and metadata hostname aliases."""
    # IP-literal metadata.
    r = validate_external_url("http://169.254.169.254/", allow_internal=True)
    assert r.ok is False
    assert r.reason == RC_METADATA_SERVICE_IP
    # Hostname alias.
    r = validate_external_url("http://metadata.google.internal/", allow_internal=True)
    assert r.ok is False
    assert r.reason == RC_METADATA_SERVICE_IP
    # Hostname A that resolves to metadata IP.
    mock_gai.return_value = [_ai_v4("169.254.169.254")]
    r = validate_external_url("http://innocent-looking.example/", allow_internal=True)
    assert r.ok is False
    assert r.reason == RC_METADATA_SERVICE_IP


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_allow_internal_permits_loopback_and_private(mock_gai):
    """allow_internal=True still allows loopback / private addresses."""
    mock_gai.return_value = [_ai_v4("127.0.0.1")]
    r = validate_external_url("http://localhost-alias.example/", allow_internal=True)
    assert r.ok is True
    mock_gai.return_value = [_ai_v6("fc00::1")]
    r = validate_external_url("http://internal-v6.example/", allow_internal=True)
    assert r.ok is True


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_ipv6_zone_id_stripped(mock_gai):
    """getaddrinfo may return fe80::1%eth0 — zone-id suffix must be stripped before parse."""
    mock_gai.return_value = [_ai_v6("fe80::1%eth0")]
    r = validate_external_url("http://v6-zone.example/")
    assert r.ok is False
    assert r.reason == RC_LINK_LOCAL


def test_result_type_is_validation_result():
    """API contract: return type is the frozen ValidationResult dataclass."""
    r = validate_external_url("http://8.8.8.8/")
    assert isinstance(r, ValidationResult)
