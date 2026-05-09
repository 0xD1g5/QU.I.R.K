"""URL allowlist validator for QUIRK — Phase 57 / CR-04, CR-06.

Decision enforcement:
  D-01: shared validator used by SAML scanner (CR-04) and broker mgmt API (CR-06).
  D-03: ValidationResult shape (ok, reason, redacted_preview).
  D-08: redacted_preview strips control chars, truncates to 32 chars.

Public surface:
  validate_external_url(url, *, allow_internal=False) -> ValidationResult
"""
from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationResult:
    """Frozen result returned by validation functions.

    Attributes:
        ok: True when the input passed all checks.
        reason: Empty string when ok=True; a reason-code constant otherwise.
        redacted_preview: Empty string when ok=True; a <= 32-char, control-char-
            stripped preview of the rejected input otherwise.
    """

    ok: bool
    reason: str            # "" when ok=True; reason-code constant otherwise
    redacted_preview: str  # "" when ok=True; <=32-char preview otherwise


# ---------------------------------------------------------------------------
# Reason-code constants (D-03 — fixed enum, NOT free-form strings)
# ---------------------------------------------------------------------------

RC_INTERNAL_IP: Final[str] = "internal_ip"
RC_LOOPBACK: Final[str] = "loopback"
RC_LINK_LOCAL: Final[str] = "link_local"
RC_METADATA_SERVICE_IP: Final[str] = "metadata_service_ip"
RC_SCHEME_PREFIX: Final[str] = "scheme_prefix"


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Cloud metadata service IPs — always blocked, even with allow_internal=True
# (per CR-04 threat model: cloud SSRF cred-theft chain).
_METADATA_IPS: frozenset[ipaddress.IPv4Address | ipaddress.IPv6Address] = frozenset({
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("fd00:ec2::254"),
})

# Only http and https are safe fetch schemes; everything else is rejected.
_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})

# Pattern for stripping ASCII control characters (D-08).
_CTRL_RE: re.Pattern[str] = re.compile(r"[\x00-\x1f\x7f]")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _redact_preview(raw: str, max_len: int = 32) -> str:
    """Strip ASCII control characters from *raw* and truncate to *max_len* chars.

    Used to build the ``redacted_preview`` field so that log entries or error
    messages cannot contain terminal-escape injection or unreadable binary data.

    Args:
        raw: The raw input string (URL, path, image ref, …).
        max_len: Maximum length of the returned string (default 32 per D-08).

    Returns:
        A sanitised, truncated substring of *raw*.
    """
    cleaned = _CTRL_RE.sub("", raw)
    return cleaned[:max_len]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_external_url(url: str, *, allow_internal: bool = False) -> ValidationResult:
    """Validate *url* is safe to fetch externally (CR-04 / CR-06).

    Rejects:
    - Non-http/https schemes (``file://``, ``gopher://``, etc.) → RC_SCHEME_PREFIX.
    - Cloud metadata service IPs (``169.254.169.254``, ``fd00:ec2::254``) →
      RC_METADATA_SERVICE_IP — **always**, even when *allow_internal* is True.
    - RFC1918 / private / reserved IPs → RC_INTERNAL_IP (unless *allow_internal*).
    - Loopback addresses (``127.0.0.1``, ``::1``) → RC_LOOPBACK (unless *allow_internal*).
    - Link-local addresses (non-metadata ``169.254.x.x``) → RC_LINK_LOCAL (unless *allow_internal*).

    Hostname targets (non-IP) are resolved via DNS and the resulting IP is subject
    to the same IP-class checks. If DNS resolution fails the target is treated as
    unreachable and accepted (ok=True) so the caller's connection attempt fails naturally.

    Args:
        url: The URL string to validate.
        allow_internal: If True, RFC1918, loopback, and link-local addresses are
            accepted. Metadata-service IPs are ALWAYS rejected regardless.

    Returns:
        ``ValidationResult(ok=True, reason="", redacted_preview="")`` on success.
        ``ValidationResult(ok=False, reason=<reason_code>, redacted_preview=<snippet>)``
        on rejection.
    """
    parsed = urlparse(url)

    # 1. Scheme check — must be http or https.
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return ValidationResult(False, RC_SCHEME_PREFIX, _redact_preview(url))

    host = parsed.hostname or ""

    # 2. IP address checks.
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Host is a domain name — resolve to check the actual destination IP.
        # If DNS resolution fails the host is unreachable; return ok=True so the
        # caller's normal connection attempt fails naturally.
        try:
            resolved = socket.gethostbyname(host)
            ip = ipaddress.ip_address(resolved)
        except (socket.gaierror, ValueError):
            return ValidationResult(True, "", "")

    # 2a. Metadata service — always blocked, even with allow_internal=True.
    if ip in _METADATA_IPS:
        return ValidationResult(False, RC_METADATA_SERVICE_IP, _redact_preview(url))

    # 2b. allow_internal bypass for non-metadata IPs.
    if allow_internal:
        return ValidationResult(True, "", "")

    # 2c. Loopback (127.0.0.1, ::1, …).
    if ip.is_loopback:
        return ValidationResult(False, RC_LOOPBACK, _redact_preview(url))

    # 2d. Link-local (169.254.x.x / fe80::/10).
    if ip.is_link_local:
        return ValidationResult(False, RC_LINK_LOCAL, _redact_preview(url))

    # 2e. Private / reserved (RFC1918 and others).
    if ip.is_private or ip.is_reserved:
        return ValidationResult(False, RC_INTERNAL_IP, _redact_preview(url))

    return ValidationResult(True, "", "")
