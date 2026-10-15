"""Validated outbound HTTP fetches that follow redirects one hop at a time.

Callers: quirk.scanner.openapi_scanner, quirk.scanner.saml_scanner,
quirk.scanner.jwt_scanner. Each passes its own single-hop ``fetch`` callable so
the helper stays transport-agnostic (it imports no HTTP client) and existing
module-level ``httpx`` mocks keep intercepting.
"""
from __future__ import annotations

import urllib.parse
from typing import Any, Callable, Optional

from quirk.util.url_allowlist import _redact_url_preview, validate_external_url

MAX_REDIRECT_HOPS = 5
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
_SENSITIVE_HEADERS = frozenset(
    {"authorization", "x-api-key", "x-auth-token", "cookie", "proxy-authorization"}
)


class OutboundFetchRejected(ValueError):
    """Raised when a fetch hop fails URL validation or the hop cap is exceeded."""

    def __init__(self, reason: str, preview: str, hop: int) -> None:
        self.reason = reason
        self.preview = preview
        self.hop = hop
        super().__init__(f"outbound fetch refused at hop {hop} ({reason}): {preview!r}")


def _origin(url: str) -> tuple:
    p = urllib.parse.urlparse(url)
    return (p.scheme, (p.hostname or "").lower(), p.port)


def fetch_validated(
    url: str,
    *,
    fetch: Callable[[str, dict], Any],
    allow_internal: bool,
    headers: Optional[dict] = None,
    extra_check: Optional[Callable[[str], None]] = None,
    max_hops: int = MAX_REDIRECT_HOPS,
) -> Any:
    """Fetch ``url`` via ``fetch(url, headers)``, validating every hop (including hop 0)."""
    current = url
    hdrs = dict(headers or {})
    for hop in range(max_hops + 1):
        vr = validate_external_url(current, allow_internal=allow_internal)
        if not vr.ok:
            raise OutboundFetchRejected(vr.reason, vr.redacted_preview, hop)
        if extra_check is not None:
            extra_check(current)
        resp = fetch(current, hdrs)
        status = getattr(resp, "status_code", None)
        if not (isinstance(status, int) and status in _REDIRECT_CODES):
            return resp
        resp_headers = getattr(resp, "headers", None)
        if not hasattr(resp_headers, "get"):
            return resp
        loc = resp_headers.get("location")
        if not loc:
            return resp
        nxt = urllib.parse.urljoin(current, loc)
        if _origin(nxt) != _origin(current):
            hdrs = {k: v for k, v in hdrs.items() if k.lower() not in _SENSITIVE_HEADERS}
        current = nxt
    raise OutboundFetchRejected("too_many_redirects", _redact_url_preview(current), max_hops)
