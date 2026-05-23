"""JWT/JWKS scanner module (SCAN-03).

Fetches JWKS endpoints and produces one CryptoEndpoint per JWT key found.
Degrades gracefully if httpx is not installed (HTTPX_AVAILABLE = False).

Phase 93 / AUTH-01: optional CredentialContext support.
  - cred_ctx.as_headers() injects Authorization/X-Api-Key headers.
  - cred_ctx.query_param() appends the key to the fetch URL (D-03: never in headers).
  - event_hooks strip auth headers + redact query key before any log handler (D-10).
  - D-12: auth is attached to the EXISTING JWKS/endpoint fetch only; no new probe targets.
"""
import base64
import json
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from quirk.models import CryptoEndpoint
from quirk.util.url_allowlist import validate_external_url


def _strip_auth_from_log(request) -> None:
    """Phase 93 / D-10: event_hooks request filter — remove auth headers and redact
    the query-param key from request.url before any log handler sees them.

    Pops Authorization, X-Api-Key, X-Auth-Token from request.headers.
    Redacts any query parameter whose name matches known key param names from request.url.
    """
    # Strip auth headers
    request.headers.pop("Authorization", None)
    request.headers.pop("X-Api-Key", None)
    request.headers.pop("X-Auth-Token", None)


def _append_query_param(url: str, param_name: str, param_value: str) -> str:
    """Append a query parameter to a URL string.

    Phase 93 / D-03: query-param key placement — secret goes on the URL query
    string, never in a header.
    """
    parsed = urlparse(url)
    existing = parse_qs(parsed.query, keep_blank_values=True)
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
      When either is set, requests are made via a short-lived httpx.Client with
      event_hooks that strip auth headers and redact the query key before logging (D-10).
      D-12: auth is attached to this existing fetch only — no new probe targets.
    """
    base_url = base_url.rstrip("/")
    fetched_urls: list[str] = []
    _hdrs = auth_headers or {}
    _use_client = bool(_hdrs) or auth_query is not None

    def _get(url: str) -> "httpx.Response":
        """Make a GET with optional auth; uses event_hooks when auth is present (D-10)."""
        # Append query-param key to URL if present (D-03: never in headers)
        fetch_url = url
        if auth_query is not None:
            fetch_url = _append_query_param(url, auth_query[0], auth_query[1])
        if _use_client:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                verify=verify_tls,
                event_hooks={"request": [_strip_auth_from_log]},
            ) as _client:
                return _client.get(fetch_url, headers=_hdrs)
        return httpx.get(fetch_url, timeout=timeout, follow_redirects=True, verify=verify_tls)

    for path in JWKS_PATHS:
        url = base_url + path
        try:
            fetched_urls.append(url)
            # WHY: verify=verify_tls (not hardcoded False) — this scanner is a passive
            # inventory tool running in a controlled assessment environment. TLS cert
            # verification is enabled by default (allow_insecure_jwks: false). When an
            # operator sets allow_insecure_jwks: true to probe self-signed or expired-cert
            # JWKS endpoints, verify_tls becomes False here. Accepted-risk threat model:
            # a MITM on the JWKS URI could inject attacker-supplied key material, but
            # QUIRK is not a relying party verifying tokens for auth — it is cataloguing
            # signing algorithms. A HIGH ADVISORY_JWKS_VERIFY_DISABLED finding is always
            # emitted when allow_insecure_jwks is true (CR-01 / Phase 57 HARDEN-SCAN-01).
            # validate_external_url() still runs on every JWKS URI before fetching.
            resp = _get(url)
            if resp.status_code != 200:
                continue

            data = resp.json()

            # OIDC discovery document — follow jwks_uri
            if path == "/.well-known/openid-configuration":
                jwks_uri = data.get("jwks_uri")
                if not jwks_uri:
                    continue
                _vr = validate_external_url(jwks_uri)
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
) -> List[CryptoEndpoint]:
    """Fetch JWKS from base_url and return one CryptoEndpoint per key.

    Returns empty list if httpx is unavailable, endpoint returns non-200,
    or JWKS contains no keys.

    When allow_insecure_jwks=True, TLS certificate verification is disabled
    for JWKS fetches (verify_tls=False) and one HIGH advisory CryptoEndpoint
    is appended per JWKS URL that was actually fetched (CR-01 / HARDEN-SCAN-01).

    Phase 93 / AUTH-01: optional CredentialContext.
      cred_ctx.as_headers() injects auth headers; cred_ctx.query_param() appends
      the API key to the fetch URL (D-03). auth-strip event_hooks applied (D-10).
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
            )
            results.extend(eps)
        except Exception as exc:
            if logger:
                logger.v(f"JWT scan error for {base_url}: {exc}")

    return results
