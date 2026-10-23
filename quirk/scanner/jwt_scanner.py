"""JWT/JWKS scanner module (SCAN-03).

Fetches JWKS endpoints and produces one CryptoEndpoint per JWT key found.
Degrades gracefully if httpx is not installed (HTTPX_AVAILABLE = False).

Phase 93 / AUTH-01: optional CredentialContext support.
  - cred_ctx.as_headers() injects Authorization/X-Api-Key headers.
  - cred_ctx.query_param() appends the key to the fetch URL (D-03: never in headers).
  - credentials are sent intact; key query params are redacted only in log records (D-09/D-10a).
  - D-12: auth is attached to the EXISTING JWKS/endpoint fetch only; no new probe targets.
"""
import base64
import json
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from quirk.models import CryptoEndpoint
from quirk.util.outbound_fetch import fetch_validated
from quirk.util.safe_exc import safe_str
from quirk.util.url_allowlist import validate_external_url

logger = logging.getLogger(__name__)

# Phase 93 / IN-01: single source of truth for query-param key names. Referenced by
# the log-redaction filter below; CredentialContext.query_param() defaults to "api_key".
_KEY_PARAM_NAMES = frozenset({
    "api_key", "apikey", "key", "token", "auth_token", "access_token",
})


_QUERY_KEY_RE = re.compile(
    r"([?&](?:"
    + "|".join(sorted((re.escape(n) for n in _KEY_PARAM_NAMES), key=len, reverse=True))
    + r")=)[^&\s\"']+",
    re.IGNORECASE,
)


class _RedactKeyQueryFilter(logging.Filter):
    """Phase 230 / D-09, D-10a: redact key query params at the logging boundary.

    httpx logs ``HTTP Request: GET <url>`` at INFO with the full query string,
    so an ``api_key_query`` credential would otherwise reach log handlers. The
    outgoing request is never touched; only the rendered log record is rewritten.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = _QUERY_KEY_RE.sub(r"\1REDACTED", message)
        if redacted != message:
            record.msg = redacted
            record.args = None
        return True


# 230-REVIEW WR-02: the httpcore child loggers known to emit records (httpcore
# 1.0.x; `_sync`/`_async` modules call logging.getLogger with these names).
# Baseline for environments where the package source cannot be read (frozen
# builds ship bytecode only); _httpcore_logger_names() adds whatever the
# installed source actually names.
_HTTPCORE_LOGGER_BASELINE = (
    "httpcore.connection",
    "httpcore.http11",
    "httpcore.http2",
    "httpcore.proxy",
    "httpcore.socks",
)

_GETLOGGER_NAME_RE = re.compile(r"""getLogger\(\s*["'](httpcore(?:\.[\w.]+)?)["']\s*\)""")


def _httpcore_logger_names() -> set:
    """Every httpcore logger name: baseline + installed source + live loggers.

    ``Logger.addFilter`` filters only records created on that exact logger;
    records do not pass through an ancestor logger's filters as they
    propagate. So the filter has to sit on each emitting child logger, and
    those names are enumerated from the installed httpcore source at run time
    (never a hand-maintained list alone).
    """
    names = set(_HTTPCORE_LOGGER_BASELINE)
    try:
        import pathlib

        import httpcore  # noqa: F401 - only its location is used

        root = pathlib.Path(httpcore.__file__).parent
        for py in root.rglob("*.py"):
            try:
                names.update(_GETLOGGER_NAME_RE.findall(py.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                continue
    except Exception:  # noqa: BLE001 - enumeration must never break import
        pass
    for existing in list(logging.root.manager.loggerDict):
        if existing == "httpcore" or existing.startswith("httpcore."):
            names.add(existing)
    return names


def _install_redact_filter() -> None:
    """Attach one redaction filter to every logger that can render a fetch URL.

    Covered: ``httpx`` (its INFO ``HTTP Request: GET <url>`` line), each
    httpcore logger named by ``_httpcore_logger_names()`` (``httpcore`` itself
    plus its emitting children such as ``httpcore.http11`` and
    ``httpcore.connection``), and this module's logger. Not covered: records
    created on any other logger, and handler-level output. The filter only
    rewrites log records; the outgoing request is never touched.

    Idempotent across module reloads: a reload creates a new class object, so
    stale instances are detected by class name and replaced.
    """
    flt = _RedactKeyQueryFilter()
    for name in sorted({"httpx", __name__} | _httpcore_logger_names()):
        lg = logging.getLogger(name)
        for old in [f for f in lg.filters if type(f).__name__ == "_RedactKeyQueryFilter"]:
            lg.removeFilter(old)
        lg.addFilter(flt)


_install_redact_filter()


_DEFAULT_PORTS = {"http": 80, "https": 443}


def _norm_origin(url: str) -> tuple:
    """(scheme, host, port) with the scheme's default port filled in.

    230-REVIEW CR-01: credentials are attached only when a request URL has the
    same origin as the operator-supplied base URL. ``https://h`` and
    ``https://h:443`` are the same origin; the host is compared lowercased.
    """
    p = urlparse(url)
    scheme = (p.scheme or "").lower()
    try:
        port = p.port
    except ValueError:
        port = None
    if port is None:
        port = _DEFAULT_PORTS.get(scheme)
    return (scheme, (p.hostname or "").lower(), port)


def _origin_label(url: str) -> str:
    """Render an origin as ``scheme://host:port`` (never path, query or userinfo)."""
    scheme, host, port = _norm_origin(url)
    return f"{scheme}://{host}:{port}"


def _append_query_param(url: str, param_name: str, param_value: str) -> str:
    """Append a query parameter to a URL string.

    Phase 93 / D-03: query-param key placement — secret goes on the URL query
    string, never in a header.

    Phase 97 / D-03 (WR-04): if the URL already carries any key param name
    (checked case-insensitively against _KEY_PARAM_NAMES), raises ValueError
    to reject the target rather than silently overwriting an operator-probed
    value. The caller must catch this and skip (continue) the affected target;
    remaining targets in the iteration are unaffected.
    """
    parsed = urlparse(url)
    existing = parse_qs(parsed.query, keep_blank_values=True)
    # D-03 guard: detect any pre-existing key-param name (case-insensitive)
    for existing_key in existing:
        if existing_key.lower() in _KEY_PARAM_NAMES:
            logger.warning(
                "JWT target rejected — URL already carries a key query parameter; "
                "skipping to avoid silent overwrite (D-03): %s",
                safe_str(url),
            )
            raise ValueError(
                f"Target URL already carries a key query parameter ({existing_key!r}); "
                f"refusing to overwrite (D-03). Target: {safe_str(url)}"
            )
    existing[param_name] = [param_value]
    new_query = urlencode(existing, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

# Phase 57 / D-09: HIGH advisory service_detail when allow_insecure_jwks is set.
ADVISORY_JWKS_VERIFY_DISABLED = "JWKS/verify-disabled"

# JWKS discovery paths probed in order; stops after first success (non-empty keys)
JWKS_PATHS = [
    "/.well-known/jwks.json",
    "/oauth/jwks",
    "/.well-known/openid-configuration",
]

# EC curve bit-lengths by curve name
_EC_CRV_BITS = {
    "P-256": 256,
    "P-384": 384,
    "P-521": 521,
    "secp256k1": 256,
}


def _rsa_key_bits_from_n(n_b64url: str) -> Optional[int]:
    """Compute RSA key size in bits from base64url-encoded modulus n."""
    try:
        padded = n_b64url.replace("-", "+").replace("_", "/")
        padded += "=" * (4 - len(padded) % 4)
        return len(base64.b64decode(padded)) * 8
    except Exception:
        return None


def _fetch_jwks(
    base_url: str,
    timeout: int,
    *,
    verify_tls: bool = True,
    auth_headers: Optional[dict] = None,
    auth_query: Optional[tuple] = None,
    allow_internal: bool = False,
) -> tuple[Optional[list], Optional[str], list[str]]:
    """Probe JWKS paths against base_url.

    Returns (keys_list, jwks_path, fetched_urls) on success,
    (None, None, []) if no endpoint found.

    fetched_urls contains every URL that was actually requested with the given
    verify_tls setting, so callers can emit one advisory per URL when
    verify_tls=False.

    Follows OIDC discovery when /.well-known/openid-configuration is encountered.

    Phase 93 / AUTH-01:
      auth_headers: dict of headers to pass (e.g. {"Authorization": "Bearer ..."}).
      auth_query: (param_name, secret) tuple to append to the fetch URL (D-03).
      When either is set, requests are made via a short-lived httpx.Client; the
      credential is sent intact and only logged URLs are redacted (logging.Filter).
      D-12: auth is attached to this existing fetch only — no new probe targets.

    230-REVIEW CR-01: credentials (headers AND the query-param key) are attached
    only to URLs with the same origin (scheme, host, port) as ``base_url``. A
    discovery document's ``jwks_uri`` on another origin is fetched without
    credentials, and one WARNING (origins only, no secret) records the mismatch.
    """
    base_url = base_url.rstrip("/")
    fetched_urls: list[str] = []
    _hdrs = auth_headers or {}
    _has_creds = bool(_hdrs) or auth_query is not None
    _base_origin = _norm_origin(base_url)
    _warned: set = set()

    def _get(url: str) -> "httpx.Response":
        """Make a GET; credentials are sent intact, but only to the base origin."""
        same_origin = _norm_origin(url) == _base_origin
        if _has_creds and not same_origin and "cross-origin" not in _warned:
            _warned.add("cross-origin")
            logger.warning(
                "JWKS URL is on a different origin (%s) than the scan target (%s); "
                "fetching it without credentials",
                _origin_label(url), _origin_label(base_url),
            )
        _use_client = _has_creds and same_origin
        # Append query-param key to URL if present (D-03: never in headers)
        fetch_url = url
        if auth_query is not None and same_origin:
            fetch_url = _append_query_param(url, auth_query[0], auth_query[1])
        if _use_client:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=False,
                verify=verify_tls,
            ) as _client:
                return fetch_validated(
                    fetch_url,
                    fetch=lambda u, h: _client.get(u, headers=h),
                    headers=_hdrs,
                    allow_internal=allow_internal,
                )
        return fetch_validated(
            fetch_url,
            fetch=lambda u, h: httpx.get(
                u, timeout=timeout, follow_redirects=False, verify=verify_tls, headers=h or None
            ),
            allow_internal=allow_internal,
        )

    for path in JWKS_PATHS:
        url = base_url + path
        # CR-03: validate every base probe URL before fetching — SSRF guard, materially
        # more important now that credentials are attached. Previously only the
        # OIDC-followed jwks_uri was validated, leaving the base probe URLs unchecked.
        _vr_base = validate_external_url(url, allow_internal=allow_internal)
        if not _vr_base.ok:
            continue
        try:
            fetched_urls.append(url)
            # WHY: verify=verify_tls (not hardcoded False) — this scanner is a passive
            # inventory tool running in a controlled assessment environment. TLS cert
            # verification is enabled by default (allow_insecure_jwks: false). When an
            # operator sets allow_insecure_jwks: true to probe self-signed or expired-cert
            # JWKS endpoints, verify_tls becomes False here. Accepted-risk threat model:
            # a MITM on the JWKS URI could inject attacker-supplied key material, but
            # QUIRK is not a relying party verifying tokens for auth — it is cataloguing
            # signing algorithms. A HIGH ADVISORY_JWKS_VERIFY_DISABLED row is emitted for
            # each fetched URL when allow_insecure_jwks is true (Phase 57 HARDEN-SCAN-01).
            # validate_external_url() runs on every probe URL above and every jwks_uri below.
            resp = _get(url)
            if resp.status_code != 200:
                continue

            data = resp.json()

            # OIDC discovery document — follow jwks_uri
            if path == "/.well-known/openid-configuration":
                jwks_uri = data.get("jwks_uri")
                if not jwks_uri:
                    continue
                _vr = validate_external_url(jwks_uri, allow_internal=allow_internal)
                if not _vr.ok:
                    continue
                fetched_urls.append(jwks_uri)
                # WHY: same verify=verify_tls rationale as above — passive inventory
                # scanner; allow_insecure_jwks defaults false; advisory finding emitted
                # when enabled; validate_external_url() already ran on jwks_uri above.
                resp2 = _get(jwks_uri)
                if resp2.status_code != 200:
                    continue
                data = resp2.json()
                path = jwks_uri  # store actual JWKS URL as service_detail

            keys = data.get("keys", [])
            if keys:
                return keys, path, fetched_urls

        except Exception:
            continue

    return None, None, fetched_urls


def scan_jwt_endpoint(
    base_url: str,
    timeout: int = 10,
    logger=None,
    *,
    allow_insecure_jwks: bool = False,
    cred_ctx=None,
    allow_internal: bool = False,
) -> List[CryptoEndpoint]:
    """Fetch JWKS from base_url and return one CryptoEndpoint per key.

    Returns empty list if httpx is unavailable, endpoint returns non-200,
    or JWKS contains no keys.

    When allow_insecure_jwks=True, TLS certificate verification is disabled
    for JWKS fetches (verify_tls=False) and one HIGH advisory CryptoEndpoint
    is appended per JWKS URL that was actually fetched (CR-01 / HARDEN-SCAN-01).

    Phase 93 / AUTH-01: optional CredentialContext.
      cred_ctx.as_headers() injects auth headers; cred_ctx.query_param() appends
      the API key to the fetch URL (D-03). Credentials are sent intact; log redaction
      is a logging.Filter (D-09).
      D-12: consumer is EXISTING JWKS/endpoint fetch only; no new probe targets.
    """
    if not HTTPX_AVAILABLE:
        return []

    # Phase 93 / AUTH-01: extract auth data from CredentialContext (None-safe)
    _auth_headers: dict = cred_ctx.as_headers() if cred_ctx is not None else {}
    _auth_query = cred_ctx.query_param() if cred_ctx is not None else None

    verify_tls = not allow_insecure_jwks
    keys, jwks_path, fetched_urls = _fetch_jwks(
        base_url, timeout,
        verify_tls=verify_tls,
        auth_headers=_auth_headers if _auth_headers else None,
        auth_query=_auth_query,
        allow_internal=allow_internal,
    )
    if not keys:
        if allow_insecure_jwks and fetched_urls:
            # Emit advisories even when no keys found (fetch was attempted with verify_tls=False)
            endpoints: List[CryptoEndpoint] = []
            for url in fetched_urls:
                endpoints.append(CryptoEndpoint(
                    host=url,
                    port=443,
                    protocol="ADVISORY",
                    service_detail=ADVISORY_JWKS_VERIFY_DISABLED,
                    severity="HIGH",
                    scan_error_category="config",
                    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
                ))
            return endpoints
        return []

    endpoints: List[CryptoEndpoint] = []

    for key_entry in keys:
        kty = key_entry.get("kty", "")
        alg = key_entry.get("alg") or kty  # fall back to kty if alg absent

        # Compute key bit-length
        key_bits: Optional[int] = None
        if kty == "RSA":
            n = key_entry.get("n", "")
            if n:
                key_bits = _rsa_key_bits_from_n(n)
        elif kty == "EC":
            crv = key_entry.get("crv", "")
            key_bits = _EC_CRV_BITS.get(crv)

        ep = CryptoEndpoint(
            host=base_url,
            port=443,
            protocol="JWT",
            cert_pubkey_alg=alg,
            cert_pubkey_size=key_bits,
            jwt_scan_json=json.dumps(key_entry),
            service_detail=jwks_path,
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        endpoints.append(ep)

        if logger:
            logger.v(f"JWT {base_url} key kid={key_entry.get('kid')} alg={alg} bits={key_bits}")

    # Phase 57 / CR-01: emit one HIGH advisory per JWKS URL fetched with TLS verification disabled.
    if allow_insecure_jwks and fetched_urls:
        for url in fetched_urls:
            endpoints.append(CryptoEndpoint(
                host=url,
                port=443,
                protocol="ADVISORY",
                service_detail=ADVISORY_JWKS_VERIFY_DISABLED,
                severity="HIGH",
                scan_error_category="config",
                scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
            ))

    return endpoints


def scan_jwt_targets(
    targets: list,
    timeout: int = 10,
    logger=None,
    *,
    allow_insecure_jwks: bool = False,
    cred_ctx=None,
    allow_internal: bool = False,
) -> List[CryptoEndpoint]:
    """Scan a list of JWT API base URLs and return all CryptoEndpoints found.

    Returns empty list immediately if httpx is not available.

    When allow_insecure_jwks=True, propagates the flag to scan_jwt_endpoint so
    TLS verification is disabled and HIGH advisory CryptoEndpoints are emitted
    per JWKS URL (CR-01 / HARDEN-SCAN-01).

    Phase 93 / AUTH-01: optional CredentialContext (None = unauthenticated).
      D-12: cred_ctx is forwarded to the existing JWKS/endpoint fetch only;
      no new probe targets or finding types are added.
    """
    if not HTTPX_AVAILABLE:
        return []

    results: List[CryptoEndpoint] = []
    for base_url in targets:
        try:
            eps = scan_jwt_endpoint(
                base_url,
                timeout=timeout,
                logger=logger,
                allow_insecure_jwks=allow_insecure_jwks,
                cred_ctx=cred_ctx,
                allow_internal=allow_internal,
            )
            results.extend(eps)
        except Exception as exc:
            if logger:
                # CR-02: scrub before logging — an httpx exception commonly embeds the
                # ?api_key=<secret> fetch URL; the LEAK-03 AST gate does not inspect logger.* calls.
                logger.v(f"JWT scan error for {base_url}: {safe_str(exc)}")

    return results
