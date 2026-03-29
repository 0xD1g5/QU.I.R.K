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


def _fetch_jwks(base_url: str, timeout: int) -> tuple[Optional[list], Optional[str]]:
    """Probe JWKS paths against base_url.

    Returns (keys_list, jwks_path) on success, (None, None) if no endpoint found.
    Follows OIDC discovery when /.well-known/openid-configuration is encountered.
    """
    base_url = base_url.rstrip("/")

    for path in JWKS_PATHS:
        url = base_url + path
        try:
            resp = httpx.get(url, timeout=timeout, follow_redirects=True, verify=False)
            if resp.status_code != 200:
                continue

            data = resp.json()

            # OIDC discovery document — follow jwks_uri
            if path == "/.well-known/openid-configuration":
                jwks_uri = data.get("jwks_uri")
                if not jwks_uri:
                    continue
                resp2 = httpx.get(jwks_uri, timeout=timeout, follow_redirects=True, verify=False)
                if resp2.status_code != 200:
                    continue
                data = resp2.json()
                path = jwks_uri  # store actual JWKS URL as service_detail

            keys = data.get("keys", [])
            if keys:
                return keys, path

        except Exception:
            continue

    return None, None


def scan_jwt_endpoint(
    base_url: str,
    timeout: int = 10,
    logger=None,
) -> List[CryptoEndpoint]:
    """Fetch JWKS from base_url and return one CryptoEndpoint per key.

    Returns empty list if httpx is unavailable, endpoint returns non-200,
    or JWKS contains no keys.
    """
    if not HTTPX_AVAILABLE:
        return []

    keys, jwks_path = _fetch_jwks(base_url, timeout)
    if not keys:
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

    return endpoints


def scan_jwt_targets(
    targets: list,
    timeout: int = 10,
    logger=None,
) -> List[CryptoEndpoint]:
    """Scan a list of JWT API base URLs and return all CryptoEndpoints found.

    Returns empty list immediately if httpx is not available.
    """
    if not HTTPX_AVAILABLE:
        return []

    results: List[CryptoEndpoint] = []
    for base_url in targets:
        try:
            eps = scan_jwt_endpoint(base_url, timeout=timeout, logger=logger)
            results.extend(eps)
        except Exception as exc:
            if logger:
                logger.v(f"JWT scan error for {base_url}: {exc}")

    return results
