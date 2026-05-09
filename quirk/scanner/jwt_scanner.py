"""JWT/JWKS scanner module (SCAN-03).

Fetches JWKS endpoints and produces one CryptoEndpoint per JWT key found.
Degrades gracefully if httpx is not installed (HTTPX_AVAILABLE = False).
"""
import base64
import json
from datetime import datetime, timezone
from typing import List, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from quirk.models import CryptoEndpoint
from quirk.util.url_allowlist import validate_external_url

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
) -> tuple[Optional[list], Optional[str], list[str]]:
    """Probe JWKS paths against base_url.

    Returns (keys_list, jwks_path, fetched_urls) on success,
    (None, None, []) if no endpoint found.

    fetched_urls contains every URL that was actually requested with the given
    verify_tls setting, so callers can emit one advisory per URL when
    verify_tls=False.

    Follows OIDC discovery when /.well-known/openid-configuration is encountered.
    """
    base_url = base_url.rstrip("/")
    fetched_urls: list[str] = []

    for path in JWKS_PATHS:
        url = base_url + path
        try:
            fetched_urls.append(url)
            resp = httpx.get(url, timeout=timeout, follow_redirects=True, verify=verify_tls)
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
                resp2 = httpx.get(jwks_uri, timeout=timeout, follow_redirects=True, verify=verify_tls)
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
) -> List[CryptoEndpoint]:
    """Fetch JWKS from base_url and return one CryptoEndpoint per key.

    Returns empty list if httpx is unavailable, endpoint returns non-200,
    or JWKS contains no keys.

    When allow_insecure_jwks=True, TLS certificate verification is disabled
    for JWKS fetches (verify_tls=False) and one HIGH advisory CryptoEndpoint
    is appended per JWKS URL that was actually fetched (CR-01 / HARDEN-SCAN-01).
    """
    if not HTTPX_AVAILABLE:
        return []

    verify_tls = not allow_insecure_jwks
    keys, jwks_path, fetched_urls = _fetch_jwks(base_url, timeout, verify_tls=verify_tls)
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
) -> List[CryptoEndpoint]:
    """Scan a list of JWT API base URLs and return all CryptoEndpoints found.

    Returns empty list immediately if httpx is not available.

    When allow_insecure_jwks=True, propagates the flag to scan_jwt_endpoint so
    TLS verification is disabled and HIGH advisory CryptoEndpoints are emitted
    per JWKS URL (CR-01 / HARDEN-SCAN-01).
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
            )
            results.extend(eps)
        except Exception as exc:
            if logger:
                logger.v(f"JWT scan error for {base_url}: {exc}")

    return results
