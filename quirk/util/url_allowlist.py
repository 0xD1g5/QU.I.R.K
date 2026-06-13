"""URL allowlist validator for QUIRK — Phase 57 / CR-04, CR-06; Phase 120 SSRF cluster fix.

Decision enforcement:
  D-01 (Phase 57): shared validator used by SAML scanner (CR-04) and broker mgmt API (CR-06).
  D-03 (Phase 57): ValidationResult shape (ok, reason, redacted_preview).
  D-08 (Phase 57): redacted_preview strips control chars, truncates to 32 chars.

Phase 120 hardening (SP-01 / AC-01 / AC-02 / CD-01 / CD-02):
  - Use ``socket.getaddrinfo(host, None, family=AF_UNSPEC)`` so IPv6-only / dual-stack
    hosts are checked against the IPv6 blocklist (loopback, link-local, ULA). The old
    the previous ``gethost*``-based resolver was IPv4-only and silently allowed
    IPv6 AAAA bypasses.
  - Iterate EVERY address returned by getaddrinfo; if any single address is blocked,
    the URL is rejected. (Previously only the first resolved address was checked.)
  - On ``socket.gaierror`` / ``OSError`` / ``UnicodeError`` we now fail-CLOSED
    (``RC_DNS_FAILURE``). The previous implementation fail-OPENED, allowing the
    caller's downstream HTTP client to perform the dangerous resolution itself.
  - Metadata HOSTNAME aliases (``metadata.google.internal``, ``metadata``,
    ``metadata.goog``) are matched BEFORE DNS resolution and cannot be bypassed by
    ``allow_internal=True``.

Residual risk — TOCTOU / DNS rebinding (accepted, Phase 120 T-120-04):
  This validator resolves the host once; the downstream HTTP client (httpx / requests)
  re-resolves at connect time, opening a TOCTOU window where a malicious authoritative
  nameserver could return a public IP to this resolver and a blocked IP to the connect
  resolver. Acceptable for QUIRK's on-prem deployment threat model. The defense-in-depth
  fix is "resolve-then-connect-to-IP with explicit SNI"; that is deferred to a future
  phase. See SECURITY.md for the formal acceptance.

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
        resolved_ip: The validated IP the caller should connect to (the first
            resolved address, or the IP literal). Empty string on rejection.
            Callers pin to this to close the DNS-rebinding TOCTOU window (SSRF-05).
    """

    ok: bool
    reason: str            # "" when ok=True; reason-code constant otherwise
    redacted_preview: str  # "" when ok=True; <=32-char preview otherwise
    resolved_ip: str = ""  # validated IP for caller pinning (SSRF-05); "" on reject


# ---------------------------------------------------------------------------
# Reason-code constants (D-03 — fixed enum, NOT free-form strings)
# ---------------------------------------------------------------------------

RC_INTERNAL_IP: Final[str] = "internal_ip"
RC_LOOPBACK: Final[str] = "loopback"
RC_LINK_LOCAL: Final[str] = "link_local"
RC_METADATA_SERVICE_IP: Final[str] = "metadata_service_ip"
RC_SCHEME_PREFIX: Final[str] = "scheme_prefix"
RC_DNS_FAILURE: Final[str] = "dns_failure"  # Phase 120: fail-closed on resolver error
RC_CONSOLE_ENDPOINT: Final[str] = "console_endpoint"  # SSRF-04 / D-01: reflective self-SSRF onto the console's own bind addr:port


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Cloud metadata service IPs — always blocked, even with allow_internal=True
# (per CR-04 threat model: cloud SSRF cred-theft chain).
_METADATA_IPS: frozenset[ipaddress.IPv4Address | ipaddress.IPv6Address] = frozenset({
    ipaddress.ip_address("169.254.169.254"),  # AWS / Azure IMDS, GCP
    ipaddress.ip_address("fd00:ec2::254"),    # AWS IMDS IPv6
})

# Cloud metadata service HOSTNAME aliases (Phase 120 SP-01).
# Matched BEFORE DNS resolution so a hostile DNS can't return a non-metadata IP
# and still serve the GCP metadata API (which honours Host: metadata.google.internal).
_METADATA_HOSTS: Final[frozenset[str]] = frozenset({
    "metadata.google.internal",
    "metadata",
    "metadata.goog",
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


def _strip_zone_id(addr: str) -> str:
    """Strip IPv6 zone-id suffix (e.g. ``fe80::1%eth0`` → ``fe80::1``).

    ``ipaddress.ip_address`` rejects zone-id-suffixed strings, but
    ``getaddrinfo`` can return them for scoped IPv6 addresses.
    """
    pct = addr.find("%")
    return addr[:pct] if pct >= 0 else addr


def _get_console_endpoint() -> tuple[str | None, int | None]:
    """Return the dashboard/console's own bind ``(host, port)`` for self-SSRF blocking.

    Sourced from the ``QUIRK_SERVE_HOST`` / ``QUIRK_SERVE_PORT`` env vars that
    ``quirk/dashboard/server.py`` sets when it starts serving (SSRF-04 / D-02).
    Returns ``(None, None)`` — a graceful no-op — when either var is unset or the
    port is non-integer, so standalone CLI scans and the chaos lab's loopback
    targets are unaffected when no console is running.
    """
    import os

    host = os.environ.get("QUIRK_SERVE_HOST", "").strip()
    port_raw = os.environ.get("QUIRK_SERVE_PORT", "").strip()
    if not host or not port_raw:
        return (None, None)
    try:
        return (host, int(port_raw))
    except ValueError:
        return (None, None)


def _classify_ip(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
    url: str,
    *,
    allow_internal: bool,
    url_port: int | None = None,
) -> ValidationResult | None:
    """Apply the IP-class blocklist to one address.

    Returns a rejecting ``ValidationResult`` on hit, or ``None`` on pass-through.
    Metadata IPs and the console's own endpoint are ALWAYS rejected —
    ``allow_internal`` cannot bypass them.
    """
    # Metadata — always blocked.
    if ip in _METADATA_IPS:
        return ValidationResult(False, RC_METADATA_SERVICE_IP, _redact_preview(url))

    # Console self-SSRF — always blocked (SSRF-04 / D-01), BEFORE the
    # allow_internal early-return. Blocks ONLY the console's own addr:port, not
    # loopback in general, so the chaos lab's --allow-internal-targets loopback
    # scanning keeps working. Cheap short-circuit on port before any resolution.
    console_host, console_port = _get_console_endpoint()
    if console_host is not None and url_port is not None and url_port == console_port:
        try:
            console_ips = {
                ipaddress.ip_address(_strip_zone_id(entry[4][0]))
                for entry in socket.getaddrinfo(console_host, None, family=socket.AF_UNSPEC)
                if entry[4] and isinstance(entry[4][0], str)
            }
        except (socket.gaierror, OSError, UnicodeError, ValueError):
            console_ips = set()
        try:
            console_ips.add(ipaddress.ip_address(console_host))
        except ValueError:
            pass
        if ip in console_ips:
            # Mirrors the metadata block's no-log, redacted-return style.
            return ValidationResult(False, RC_CONSOLE_ENDPOINT, _redact_preview(url))

    # allow_internal suppresses loopback / link-local / private / reserved only.
    if allow_internal:
        return None

    if ip.is_loopback:
        return ValidationResult(False, RC_LOOPBACK, _redact_preview(url))
    if ip.is_link_local:
        return ValidationResult(False, RC_LINK_LOCAL, _redact_preview(url))
    if ip.is_private or ip.is_reserved:
        return ValidationResult(False, RC_INTERNAL_IP, _redact_preview(url))
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_external_url(url: str, *, allow_internal: bool = False) -> ValidationResult:
    """Validate *url* is safe to fetch externally (CR-04 / CR-06; Phase 120 SSRF).

    Rejects:
    - Non-http/https schemes (``file://``, ``gopher://``, etc.) → RC_SCHEME_PREFIX.
    - Metadata HOSTNAME aliases (``metadata.google.internal`` and family) →
      RC_METADATA_SERVICE_IP. Matched before DNS, even with ``allow_internal=True``.
    - Cloud metadata service IPs (``169.254.169.254``, ``fd00:ec2::254``) →
      RC_METADATA_SERVICE_IP — **always**, even when ``allow_internal=True``.
    - RFC1918 / private / reserved IPs → RC_INTERNAL_IP (unless ``allow_internal``).
    - Loopback addresses (``127.0.0.1``, ``::1``) → RC_LOOPBACK (unless ``allow_internal``).
    - Link-local addresses (IPv4 ``169.254.x.x`` non-metadata, IPv6 ``fe80::/10``) →
      RC_LINK_LOCAL (unless ``allow_internal``).
    - DNS resolution failure → RC_DNS_FAILURE (fail-closed; Phase 120 AC-02).

    Hostname targets (non-IP) are resolved via ``socket.getaddrinfo(host, None,
    family=AF_UNSPEC)`` and EVERY returned address is checked against the blocklist.
    Any single blocked address rejects the URL.

    Args:
        url: The URL string to validate.
        allow_internal: If True, RFC1918, loopback, link-local, and reserved addresses
            are accepted. Metadata-service IPs and metadata hostnames are ALWAYS
            rejected regardless.

    Returns:
        ``ValidationResult(ok=True, reason="", redacted_preview="")`` on success.
        ``ValidationResult(ok=False, reason=<reason_code>, redacted_preview=<snippet>)``
        on rejection.
    """
    parsed = urlparse(url)

    # 1. Scheme check — must be http or https.
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return ValidationResult(False, RC_SCHEME_PREFIX, _redact_preview(url))

    host = (parsed.hostname or "").lower()

    # 2. Metadata hostname alias gate — runs BEFORE resolution. Cannot be bypassed
    # by allow_internal because cloud metadata APIs honour Host: header even when
    # the IP looks innocuous (a hostile resolver can answer the alias with a
    # non-metadata IP while the metadata service still serves the alias).
    if host in _METADATA_HOSTS:
        return ValidationResult(False, RC_METADATA_SERVICE_IP, _redact_preview(url))

    # 3. Build the address set to check.
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    try:
        addresses.append(ipaddress.ip_address(host))
    except ValueError:
        # Hostname — resolve. AF_UNSPEC covers both A and AAAA records.
        try:
            results = socket.getaddrinfo(host, None, family=socket.AF_UNSPEC)
        except (socket.gaierror, OSError, UnicodeError):
            # Phase 120 AC-02: fail-CLOSED on resolver error. Previously fail-open.
            return ValidationResult(False, RC_DNS_FAILURE, _redact_preview(url))

        for entry in results:
            sockaddr = entry[4] if len(entry) >= 5 else None
            if not sockaddr:
                continue
            raw_ip = sockaddr[0]
            if not isinstance(raw_ip, str):
                continue
            try:
                addresses.append(ipaddress.ip_address(_strip_zone_id(raw_ip)))
            except ValueError:
                # Defensive: an unparseable address from the resolver is itself a
                # red flag. Treat as fail-closed.
                return ValidationResult(False, RC_DNS_FAILURE, _redact_preview(url))

        if not addresses:
            # getaddrinfo returned an empty list — treat as resolver failure.
            return ValidationResult(False, RC_DNS_FAILURE, _redact_preview(url))

    # 4. Apply blocklist to EVERY resolved address. Any single hit rejects.
    # url_port (scheme default when absent) feeds the console self-SSRF check.
    url_port = parsed.port if parsed.port is not None else (
        443 if parsed.scheme == "https" else 80
    )
    for ip in addresses:
        rejection = _classify_ip(
            ip, url, allow_internal=allow_internal, url_port=url_port
        )
        if rejection is not None:
            return rejection

    # SSRF-05: return the validated IP so callers pin to it (close DNS-rebind TOCTOU).
    first_ip = str(addresses[0]) if addresses else ""
    return ValidationResult(True, "", "", resolved_ip=first_ip)
