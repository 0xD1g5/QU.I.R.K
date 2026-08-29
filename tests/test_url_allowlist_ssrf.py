"""Phase 120 / Plan 01 / Task 1 — SSRF regression tests.

Covers SP-01 / AC-01 / AC-02 / CD-01 / CD-02 from the 2026-05-27 audit:

  1. IPv6 AAAA bypass (host whose AAAA resolves to a blocked range MUST be rejected).
  2. Fail-closed on socket.gaierror (DNS failure MUST NOT return ok=True).
  3. Metadata HOSTNAME aliases (metadata.google.internal etc.) rejected before resolution.
  4. Dual-stack hostname where ANY returned address is blocked → reject.
  5. Genuine public IP still passes.

Phase 123 additions (SSRF-02, SSRF-05):
  6. SSRF-02 regression lock — metadata aliases blocked even with allow_internal=True (tagged ssrf02).
  7. SSRF-05 — resolved_ip populated on ValidationResult; single-resolution rebinding mitigation.

Phase 172 D-03 additions (SAFE-03) — ``test_*redact*`` nodes below:
  8. _redact_url_preview strips userinfo, query and fragment from a URL but
     deliberately retains scheme + host + truncated path.
  Falsifiability: reverting _redact_url_preview to truncation-only (its
  pre-Phase-172 behaviour) makes the userinfo/query-stripping tests below
  fail; re-adding host redaction (contradicting D-03/D-04's locked threat
  model) makes the bare-host-retained test fail; every validate_external_url
  rejection branch must still populate a non-empty redacted_preview or the
  regression test at the bottom of this section fails.
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
    _redact_url_preview,
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


# ---------------------------------------------------------------------------
# Phase 123 SSRF-02: regression-lock — metadata aliases blocked with allow_internal=True
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://metadata/latest/",
    "http://metadata.goog/",
    "http://169.254.169.254/latest/meta-data/",
], ids=["ssrf02_gcp_alias", "ssrf02_bare_alias", "ssrf02_goog_alias", "ssrf02_ip"])
def test_ssrf02_metadata_blocked_with_allow_internal(url):
    """SSRF-02 regression lock: metadata aliases + IPs rejected even allow_internal=True.

    Phase 120 implemented the blocking; this test locks the invariant under the
    SSRF-02/SP-03 requirement ID so it is selected by '-k ssrf02'.
    """
    r = validate_external_url(url, allow_internal=True)
    assert r.ok is False
    assert r.reason == RC_METADATA_SERVICE_IP


# ---------------------------------------------------------------------------
# Phase 123 SSRF-05: resolved_ip field + DNS-rebinding single-resolution invariant
# ---------------------------------------------------------------------------

@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_resolved_ip_populated(mock_gai):
    """SSRF-05: ValidationResult.resolved_ip is non-empty for a resolved hostname.

    Phase 123 RED test: fails until Plan 01 adds the resolved_ip field to
    ValidationResult and populates it in validate_external_url.
    """
    mock_gai.return_value = [_ai_v4("8.8.8.8")]
    r = validate_external_url("http://dns.google/")
    assert r.ok is True
    assert r.resolved_ip == "8.8.8.8"


def test_resolved_ip_populated_for_ip_literal():
    """SSRF-05: IP-literal URL also populates resolved_ip (no DNS call needed).

    Phase 123 RED test: fails until Plan 01 adds resolved_ip field and populates
    it for the IP-literal branch of validate_external_url.
    """
    r = validate_external_url("http://8.8.8.8/")
    assert r.ok is True
    assert r.resolved_ip == "8.8.8.8"


@patch("quirk.util.url_allowlist.socket.getaddrinfo")
def test_rebinding_mitigated_by_pinning(mock_gai):
    """SSRF-05: caller that uses resolved_ip cannot be redirected to a blocked IP on re-resolve.

    The validator resolves once; the returned resolved_ip is the IP the caller
    must connect to. We verify the returned IP matches the first resolution
    (public IP) and that getaddrinfo was called exactly once — confirming the
    validate_external_url implementation resolves once and returns the pinned IP
    for callers to use, rather than leaving resolution to the caller.

    Phase 123 RED test: fails until Plan 01 adds resolved_ip to ValidationResult.
    """
    # Single (and only) call to getaddrinfo returns a public IP.
    mock_gai.return_value = [_ai_v4("8.8.8.8")]
    r = validate_external_url("http://target.example/")
    assert r.ok is True
    assert r.resolved_ip == "8.8.8.8"
    # validate_external_url must resolve exactly once; callers connect to r.resolved_ip
    # instead of re-resolving (which a DNS-rebinding attacker could hijack).
    assert mock_gai.call_count == 1


# ---------------------------------------------------------------------------
# Phase 172 D-03 (SAFE-03) — _redact_url_preview cases
# ---------------------------------------------------------------------------

def test_redact_url_preview_strips_userinfo_query_fragment():
    """Userinfo, query and fragment are stripped; host is retained.

    Falsifiability: if _redact_url_preview reverts to truncation-only, this
    fails because 'user'/'pass'/'token'/'secret'/'frag' would all still be
    present in the (truncated) raw string at this URL's length.
    """
    raw = "http://user:pass@evil.example.com/path?token=secret#frag"
    preview = _redact_url_preview(raw, max_len=200)
    assert "evil.example.com" in preview
    assert "user" not in preview
    assert "pass" not in preview
    assert "token" not in preview
    assert "secret" not in preview
    assert "frag" not in preview


def test_redact_url_preview_bare_host_not_further_redacted():
    """A bare scheme+host+path URL is NOT redacted beyond D-03's scope.

    This is the executable form of D-04's disposition: D-03's threat model
    treats the operator-supplied host as non-secret, so it must survive.
    Falsifiability: if a future change starts hiding the host, this fails.
    """
    raw = "https://evil.example.com/openapi.json"
    preview = _redact_url_preview(raw, max_len=200)
    assert "evil.example.com" in preview


def test_redact_url_preview_truncates_after_stripping():
    """Truncation is still applied to the stripped result."""
    raw = "http://user:pass@evil.example.com/" + ("a" * 100) + "?token=secret"
    preview = _redact_url_preview(raw, max_len=32)
    assert len(preview) <= 32
    assert "token" not in preview
    assert "secret" not in preview
    assert "pass" not in preview


def test_redact_url_preview_strips_control_characters():
    """Control characters (terminal-escape injection defence) are still stripped."""
    raw = "http://evil.example.com/\x1b[31mred\x1b[0m"
    preview = _redact_url_preview(raw, max_len=200)
    assert "\x1b" not in preview
    assert "evil.example.com" in preview


def test_redact_url_preview_scheme_less_input_degrades_gracefully():
    """Non-URL, scheme-less input does not crash and returns a sanitised truncated value."""
    raw = "not a url at all"
    preview = _redact_url_preview(raw, max_len=8)
    assert preview == "not a u"[:8] or preview == raw[:8]
    assert len(preview) <= 8


def test_redact_url_preview_malformed_scheme_falls_back():
    """A malformed/unparseable-looking value falls back to truncate-only, no raise."""
    raw = "http://\x00\x01[not-a-real-host"
    # Must not raise.
    preview = _redact_url_preview(raw, max_len=32)
    assert isinstance(preview, str)
    assert len(preview) <= 32


@pytest.mark.parametrize(
    "url,expect_reason",
    [
        ("http://169.254.169.254/latest/meta-data/", RC_METADATA_SERVICE_IP),
        ("http://127.0.0.1/", RC_LOOPBACK),
        ("http://[fe80::1]/", RC_LINK_LOCAL),
        ("ftp://evil.example.com/", RC_SCHEME_PREFIX),
    ],
)
def test_validate_external_url_rejection_branches_populate_nonempty_redacted_preview(
    url, expect_reason
):
    """SAFE-03 sibling-sites regression lock: every rejection branch still
    populates a non-empty redacted_preview after the rename (Pitfall 2 — the
    10 call sites inside validate_external_url did not regress).
    """
    r = validate_external_url(url)
    assert r.ok is False
    assert r.reason == expect_reason
    assert r.redacted_preview != ""


# ---------------------------------------------------------------------------
# Phase 172 code review CR-01 — fallback path must not leak credentials
# ---------------------------------------------------------------------------

def test_redact_url_preview_userinfo_empty_host_does_not_leak():
    """CR-01 repro #1: userinfo with an empty/missing host falls through
    urlparse's `not parsed.hostname` guard into the fallback branch. The
    fallback must still be userinfo-stripped, not the raw cleaned string.

    Falsifiability: reverting the fail-closed regex pre-pass (so the fallback
    branches return the raw `cleaned` string again) makes this fail because
    'hunter2' would reappear verbatim.
    """
    raw = "https://user:hunter2@/openapi.json"
    preview = _redact_url_preview(raw, max_len=200)
    assert "hunter2" not in preview
    assert "user" not in preview


def test_redact_url_preview_userinfo_invalid_port_does_not_leak():
    """CR-01 repro #2: userinfo with an out-of-range port makes `.port` raise
    ValueError, caught by the `except (ValueError, AttributeError)` fallback.
    The fallback must still be userinfo-stripped.

    Falsifiability: reverting the fail-closed regex pre-pass makes this fail
    because 'hunter2' would reappear verbatim in the truncated raw string.
    """
    raw = "https://user:hunter2@evil.example.com:99999/openapi.json"
    preview = _redact_url_preview(raw, max_len=200)
    assert "hunter2" not in preview
    assert "user" not in preview
    # Host is not secret under D-03's threat model — it may still survive.
    assert "evil.example.com" in preview


def test_fetch_spec_bytes_from_url_userinfo_empty_host_end_to_end_does_not_leak():
    """CR-01 end-to-end repro: the exact reviewer repro through the real
    SpecParsingError raise site an attacker-supplied --openapi-spec URL
    reaches, not just the helper in isolation."""
    from quirk.scanner.openapi_scanner import _fetch_spec_bytes_from_url, SpecParsingError

    with pytest.raises(SpecParsingError) as exc_info:
        _fetch_spec_bytes_from_url(
            "https://user:hunter2@/openapi.json", cfg_targets=["acme.com"]
        )
    assert "hunter2" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# Phase 172 code review CR-02 — invalid port must not crash validate_external_url
# ---------------------------------------------------------------------------

def test_validate_external_url_out_of_range_port_does_not_raise():
    """CR-02: an out-of-range port literal must produce a handled rejection,
    not an uncaught ValueError propagating out of validate_external_url.

    Falsifiability: reverting the try/except around the `.port` read makes
    this fail with an uncaught ValueError instead of a ValidationResult.
    """
    r = validate_external_url("https://user:hunter2@evil.example.com:99999/openapi.json")
    assert r.ok is False
    assert "hunter2" not in r.redacted_preview


def test_fetch_spec_bytes_from_url_invalid_port_end_to_end_does_not_crash():
    """CR-02 end-to-end repro: the exact reviewer repro through the real
    SpecParsingError raise site — must raise SpecParsingError, not a bare
    ValueError with a traceback."""
    from quirk.scanner.openapi_scanner import _fetch_spec_bytes_from_url, SpecParsingError

    with pytest.raises(SpecParsingError) as exc_info:
        _fetch_spec_bytes_from_url(
            "https://user:hunter2@acme.com:99999/openapi.json", cfg_targets=["acme.com"]
        )
    assert "hunter2" not in str(exc_info.value)

