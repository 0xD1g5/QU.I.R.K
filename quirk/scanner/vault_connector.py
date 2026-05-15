"""HashiCorp Vault connector for cryptographic posture enumeration (VAULT-01/02/03).

Scans HashiCorp Vault transit engine, PKI mounts, and auth methods.
Uses the official `hvac` Python SDK (>=2.4.0). Degrades gracefully when hvac is not
installed (HVAC_AVAILABLE=False -> empty result list).

Required Vault token capabilities (least-privilege):
  - read on  sys/auth                                (auth method enumeration)
  - read on  sys/mounts                              (PKI mount discovery)
  - list on  <transit_mount>/keys                    (transit key enumeration)
  - read on  <transit_mount>/keys/<name>             (transit key type/exportable)
  - read on  <pki_mount>/cert/ca                     (root CA cert)
  - read on  <pki_mount>/cert/ca_chain               (intermediate chain)

Decisions encoded (from .planning/phases/30-hashicorp-vault-connector/30-CONTEXT.md):
  - D-01: Transit keys are classification-only; severity=None unless exportable
  - D-02: exportable=True transit key -> severity="MEDIUM" (NOT counted in dar_vault_weak_count)
  - D-03: PKI emits root + each intermediate as separate endpoints; RSA<4096 or SHA-1 -> HIGH
  - D-04: PKI intermediate read failure is swallowed silently (root-only fallback)
  - D-05: Token auth is always HIGH unconditional; cannot be disabled in Vault
  - D-06: AUTH_RISK_MAP -- token/ldap=HIGH, userpass=MEDIUM, others=no finding
  - D-09: tls_verify parameter passed to hvac.Client(verify=...)
  - D-17: session_start parameter mandatory (ISSUE-3 structural requirement)
  - Pitfall 3: mount paths from list_mounted_secrets_engines have trailing slashes; strip for
    service_detail and API calls; auth paths kept as-is in service_detail (test contract)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List, Optional

from quirk.models import CryptoEndpoint
from quirk.util.safe_exc import safe_str

# ---------------------------------------------------------------------------
# hvac optional import (D-16, mirrors GCP_AVAILABLE / BOTO3_AVAILABLE).
# Names must remain at module level even when import fails so that
# unittest.mock.patch("quirk.scanner.vault_connector.hvac", ...) works.
# ---------------------------------------------------------------------------
try:
    import hvac as _hvac
    hvac = _hvac
    HVAC_AVAILABLE = True
except ImportError:
    hvac = None      # type: ignore[assignment]
    HVAC_AVAILABLE = False

# ---------------------------------------------------------------------------
# Vault transit key type -> (alg_name, key_size) mapping (D-01)
# Short-form alg names (RSA, ECDSA, AES, ed25519) match quirk/cbom/classifier.py.
# PQC names (ml-dsa-*, slh-dsa-*) match classifier.py PQC entries -> register
# as positive quantum-safe findings via Pass 1 of the CBOM builder.
# ---------------------------------------------------------------------------
VAULT_TRANSIT_KEY_MAP = {
    # Symmetric
    "aes128-gcm96":       ("AES", 128),
    "aes256-gcm96":       ("AES", 256),
    "chacha20-poly1305":  ("chacha20-poly1305", 256),
    # Asymmetric signing
    "ed25519":            ("ed25519", 256),
    "ecdsa-p256":         ("ECDSA", 256),
    "ecdsa-p384":         ("ECDSA", 384),
    "ecdsa-p521":         ("ECDSA", 521),
    "rsa-2048":           ("RSA", 2048),
    "rsa-3072":           ("RSA", 3072),
    "rsa-4096":           ("RSA", 4096),
    # HMAC
    "hmac":               ("HMAC", 256),
    # PQC (NIST FIPS 204/205) -- positive findings via classifier.py short-forms
    "ml-dsa-44":          ("ml-dsa-44", None),
    "ml-dsa-65":          ("ml-dsa-65", None),
    "ml-dsa-87":          ("ml-dsa-87", None),
    "slh-dsa-shake-128s": ("slh-dsa-128", None),
    "slh-dsa-shake-192s": ("slh-dsa-192", None),
    "slh-dsa-shake-256s": ("slh-dsa-256", None),
}

# ---------------------------------------------------------------------------
# Auth method risk map (D-05, D-06).
# Methods NOT in this dict produce no finding (positive posture or unknown).
# ---------------------------------------------------------------------------
AUTH_RISK_MAP = {
    "token": (
        "HIGH",
        "Token auth method enabled -- Vault cannot disable token auth, but avoid "
        "direct token usage; prefer AppRole, Kubernetes, or OIDC auth methods",
    ),
    "ldap": (
        "HIGH",
        "LDAP auth enabled -- ensure bind credentials are service-account scoped, "
        "not domain-admin bind DN",
    ),
    "userpass": (
        "MEDIUM",
        "Userpass auth enabled -- prefer short-lived token methods "
        "(AppRole, Kubernetes, OIDC)",
    ),
    # approle, kubernetes, oidc, jwt, aws, gcp, azure, cert, github -> no entry -> no finding
}


def _now_or(session_start: Optional[datetime]) -> datetime:
    """ISSUE-3 / D-17: stamp every endpoint with session_start (or fresh now)."""
    return (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)


def _strip_trailing_slash(mount: str) -> str:
    """Pitfall 3: list_mounted_secrets_engines returns paths with trailing slashes.
    PKI service_detail and API call arguments must not include the slash."""
    return (mount or "").rstrip("/")


# ---------------------------------------------------------------------------
# VAULT-01: Transit key classification + exportable MEDIUM finding
# ---------------------------------------------------------------------------

def _scan_transit_keys(
    client,
    mount_point: str,
    logger,
    session_start: Optional[datetime],
) -> List[CryptoEndpoint]:
    """Enumerate transit keys -> CryptoEndpoint per key.

    Severity rules (D-01, D-02):
      - exportable=True -> severity="MEDIUM"
      - else            -> severity=None (classification only)

    Returns [] on any sub-scanner exception (sub-scanner isolation).
    Per-key try/except so one bad key does not skip the rest.
    """
    results: List[CryptoEndpoint] = []
    now = _now_or(session_start)
    base_url = (getattr(client, "url", None) or "").rstrip("/")
    try:
        list_resp = client.secrets.transit.list_keys(mount_point=mount_point) or {}
        key_names = list_resp.get("data", {}).get("keys", {}) or {}
        # list_keys returns dict-of-dicts in hvac >= 2.0; iteration yields key names
        for key_name in key_names:
            try:
                read_resp = client.secrets.transit.read_key(
                    name=key_name, mount_point=mount_point,
                ) or {}
                key_data = read_resp.get("data", {}) or {}
                key_type = key_data.get("type", "")
                exportable = bool(key_data.get("exportable", False))
                alg_name, key_size = VAULT_TRANSIT_KEY_MAP.get(
                    key_type, (key_type or "UNKNOWN", None)
                )
                severity: Optional[str] = "MEDIUM" if exportable else None
                ep = CryptoEndpoint(
                    host=f"{base_url}/transit/keys/{key_name}",
                    port=8200,
                    protocol="VAULT",
                    cert_pubkey_alg=alg_name,
                    cert_pubkey_size=key_size,
                    service_detail=f"transit/{key_name}",
                    severity=severity,
                    dat_scan_json=json.dumps({
                        "key_name": key_name,
                        "key_type": key_type,
                        "exportable": exportable,
                        "latest_version": key_data.get("latest_version"),
                        "remediation": (
                            "Disable key export to prevent key material from "
                            "leaving Vault." if exportable else None
                        ),
                    }, default=str),
                    scanned_at=now,
                )
                results.append(ep)
            except Exception as exc:  # noqa: BLE001
                if logger:
                    logger.v(f"Vault transit read_key error for {key_name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.v(f"Vault transit list_keys error: {exc}")
    return results


# ---------------------------------------------------------------------------
# VAULT-02: PKI root + intermediate CA cert algorithm + size detection
# ---------------------------------------------------------------------------

def _classify_pki_cert(pem_str: str):
    """Parse a PEM-encoded x509 cert and return (alg_name, key_size, severity, reason, sig_alg_name).

    Severity ladder (D-03):
      - RSA public key with key_size < 4096   -> HIGH
      - SHA-1 signature hash algorithm        -> HIGH
      - All other paths                       -> None (no finding)

    Raises on parse failure -- caller wraps in try/except.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import rsa as _rsa

    cert = x509.load_pem_x509_certificate(pem_str.encode())
    sig_hash = cert.signature_hash_algorithm
    sig_alg_name = sig_hash.name if sig_hash is not None else "unknown"
    pub_key = cert.public_key()
    key_size = getattr(pub_key, "key_size", None)
    severity: Optional[str] = None
    reason = "ok"
    if isinstance(pub_key, _rsa.RSAPublicKey):
        alg_name = "RSA"
        if key_size is not None and key_size < 4096:
            severity = "HIGH"
            reason = f"RSA-{key_size} signing key below 4096-bit threshold"
    else:
        # ECDSA / EdDSA public key types -- name resolved from class
        alg_name = type(pub_key).__name__.replace("PublicKey", "") or "UNKNOWN"
    if severity is None and "sha1" in sig_alg_name.lower():
        severity = "HIGH"
        reason = f"SHA-1 signing algorithm ({sig_alg_name})"
    return alg_name, key_size, severity, reason, sig_alg_name


def _scan_pki_mounts(
    client,
    logger,
    session_start: Optional[datetime],
) -> List[CryptoEndpoint]:
    """Enumerate PKI mounts -> root CA + intermediate CA endpoints.

    Per D-03: Both root and intermediate CA certs are fetched per mount.
    Per D-04: Intermediate chain fetch failure is swallowed silently.
    Per Pitfall 3: service_detail and API calls strip trailing slash from mount path.
    """
    results: List[CryptoEndpoint] = []
    now = _now_or(session_start)
    base_url = (getattr(client, "url", None) or "").rstrip("/")
    try:
        engines = client.sys.list_mounted_secrets_engines() or {}
        mounts = engines.get("data", {}) or {}
        for mount_path, info in mounts.items():
            if (info or {}).get("type") != "pki":
                continue
            mount_clean = _strip_trailing_slash(mount_path)
            # ---- root CA ----
            try:
                root_pem = client.secrets.pki.read_ca_certificate(
                    mount_point=mount_clean,
                )
                if root_pem:
                    alg, size, sev, reason, sig_alg = _classify_pki_cert(root_pem)
                    results.append(CryptoEndpoint(
                        host=f"{base_url}/pki/{mount_clean}",
                        port=8200,
                        protocol="VAULT",
                        cert_pubkey_alg=alg,
                        cert_pubkey_size=size,
                        service_detail=f"PKI/{mount_clean}",
                        severity=sev,
                        dat_scan_json=json.dumps({
                            "mount_point": mount_clean,
                            "role": "root",
                            "sig_alg": sig_alg,
                            "key_size": size,
                            "finding": reason,
                        }, default=str),
                        scanned_at=now,
                    ))
            except Exception as exc:  # noqa: BLE001
                if logger:
                    logger.v(f"Vault PKI root CA read error for {mount_clean}: {exc}")

            # ---- intermediate chain (D-04: silent swallow on failure) ----
            try:
                chain_pem = client.secrets.pki.read_ca_certificate_chain(
                    mount_point=mount_clean,
                )
                if chain_pem:
                    # Phase 72 D-23 / WR-18: use cryptography.x509.load_pem_x509_certificates
                    # (plural; cryptography >= 36, pyproject pins >= 44.0) instead of the
                    # naive split heuristic — handles mixed line endings, embedded comments,
                    # and trailing whitespace correctly.
                    from cryptography import x509 as _x509
                    from cryptography.hazmat.primitives import serialization as _serialization
                    try:
                        chain_bytes = chain_pem.encode("utf-8") if isinstance(chain_pem, str) else chain_pem
                        chain_certs = _x509.load_pem_x509_certificates(chain_bytes)
                    except AttributeError:
                        # cryptography < 36 — should never hit at our >= 44.0 pin; defensive.
                        if logger:
                            logger.v(
                                "cryptography lib too old for load_pem_x509_certificates "
                                "(need >= 36); bump dependency"
                            )
                        chain_certs = []
                    except ValueError as _pem_err:
                        if logger:
                            logger.v(f"Vault PKI chain PEM parse failed: {safe_str(_pem_err)}")
                        chain_certs = []
                    for idx, _cert in enumerate(chain_certs, start=1):
                        single_pem = _cert.public_bytes(
                            _serialization.Encoding.PEM
                        ).decode("ascii")
                        try:
                            alg, size, sev, reason, sig_alg = _classify_pki_cert(single_pem)
                            results.append(CryptoEndpoint(
                                host=f"{base_url}/pki/{mount_clean}:intermediate-{idx}",
                                port=8200,
                                protocol="VAULT",
                                cert_pubkey_alg=alg,
                                cert_pubkey_size=size,
                                service_detail=f"PKI/{mount_clean}:intermediate-{idx}",
                                severity=sev,
                                dat_scan_json=json.dumps({
                                    "mount_point": mount_clean,
                                    "role": f"intermediate-{idx}",
                                    "sig_alg": sig_alg,
                                    "key_size": size,
                                    "finding": reason,
                                }, default=str),
                                scanned_at=now,
                            ))
                        except Exception as exc:  # noqa: BLE001
                            if logger:
                                logger.v(
                                    f"Vault PKI intermediate parse error "
                                    f"(mount={mount_clean}, idx={idx}): {exc}"
                                )
            except Exception:  # noqa: BLE001 -- D-04: swallow silently
                pass
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.v(f"Vault PKI list_mounted_secrets_engines error: {exc}")
    return results


# ---------------------------------------------------------------------------
# VAULT-03: Auth method risk classification
# ---------------------------------------------------------------------------

def _scan_auth_methods(
    client,
    logger,
    session_start: Optional[datetime],
) -> List[CryptoEndpoint]:
    """Enumerate auth methods -> risk-tiered CryptoEndpoint per method.

    D-05: token method always emitted with HIGH (Vault cannot disable token auth).
    D-06: methods not in AUTH_RISK_MAP produce no endpoint (positive/unknown).

    Note: auth path keys from list_auth_methods() include trailing slashes (e.g. "token/").
    service_detail preserves the original path including trailing slash to match the
    expected format (f"auth/{path}") in the test contract.
    """
    results: List[CryptoEndpoint] = []
    now = _now_or(session_start)
    base_url = (getattr(client, "url", None) or "").rstrip("/")
    try:
        resp = client.sys.list_auth_methods() or {}
        methods = resp.get("data", {}) or {}
        for path, info in methods.items():
            method_type = (info or {}).get("type", "")
            risk = AUTH_RISK_MAP.get(method_type)
            if risk is None:
                continue  # no finding emitted
            severity, remediation = risk
            # Keep path as-is (including any trailing slash) for service_detail
            # so that test lookups via f"auth/{path}" match correctly.
            path_clean = _strip_trailing_slash(path)
            results.append(CryptoEndpoint(
                host=f"{base_url}/auth/{path_clean}",
                port=8200,
                protocol="VAULT",
                cert_pubkey_alg=method_type,
                service_detail=f"auth/{path}",
                severity=severity,
                dat_scan_json=json.dumps({
                    "auth_path": path,
                    "auth_type": method_type,
                    "remediation": remediation,
                }, default=str),
                scanned_at=now,
            ))
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.v(f"Vault list_auth_methods error: {exc}")
    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def scan_vault_targets(
    vault_addr: str,
    token: Optional[str] = None,
    transit_mount: str = "transit",
    tls_verify: bool = True,
    logger=None,
    session_start: Optional[datetime] = None,
    cfg=None,
) -> List[CryptoEndpoint]:
    """Enumerate HashiCorp Vault cryptographic posture (VAULT-01/02/03).

    Returns [] when hvac is not installed (HVAC_AVAILABLE=False).
    Returns a single scan_error endpoint when token is missing or invalid.
    Otherwise returns aggregated transit + PKI + auth findings.

    Sub-scanner isolation: each sub-scanner is wrapped in its own try/except,
    so a PKI failure does not suppress transit results.
    """
    if not HVAC_AVAILABLE:
        return []

    now = _now_or(session_start)
    # Phase 72 D-22 / WR-09: explicit token contract — caller must source the token
    # (env var, config, secret manager). No implicit os.environ fallback in connector.
    if token is None:
        raise ValueError(
            "vault_connector requires explicit token; "
            "pass the VAULT_TOKEN env value through if env fallback intended"
        )
    resolved_token = token
    if not resolved_token:
        # Caller passed an empty string explicitly — keep the existing scan_error path
        return [CryptoEndpoint(
            host=vault_addr or "vault://unknown",
            port=8200,
            protocol="VAULT",
            scan_error=(
                "vault-no-token: set VAULT_TOKEN env var or vault_token in config"
            ),
            scanned_at=now,
        )]

    resolved_addr = vault_addr or os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")
    # Phase 41 / D-08: per-scanner timeout sourced from canonical TimeoutsCfg
    # sub-table; literal 10 retained as defense-in-depth fallback for tests/mocks.
    vault_timeout = 10
    if cfg is not None and hasattr(cfg, "scan") and hasattr(cfg.scan, "timeouts"):
        vault_timeout = cfg.scan.timeouts.vault_seconds

    try:
        client = hvac.Client(
            url=resolved_addr,
            token=resolved_token,
            verify=tls_verify,
            timeout=vault_timeout,
        )
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.v(f"Vault hvac.Client construction error: {safe_str(exc)}")
        return [CryptoEndpoint(
            host=resolved_addr,
            port=8200,
            protocol="VAULT",
            scan_error=f"vault-client-init-failed: {safe_str(exc)}",
            scanned_at=now,
        )]

    try:
        if not client.is_authenticated():
            return [CryptoEndpoint(
                host=resolved_addr,
                port=8200,
                protocol="VAULT",
                scan_error=(
                    "vault-auth-failed: token rejected or Vault sealed"
                ),
                scanned_at=now,
            )]
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.v(f"Vault auth check network error: {safe_str(exc)}")
        return [CryptoEndpoint(
            host=resolved_addr,
            port=8200,
            protocol="VAULT",
            scan_error=f"vault-auth-failed: {safe_str(exc)}",
            scanned_at=now,
        )]

    results: List[CryptoEndpoint] = []
    # Sub-scanner isolation: each in its own try/except (D-04 spirit applied broadly)
    try:
        results.extend(_scan_transit_keys(client, transit_mount, logger, session_start))
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.v(f"Vault transit sub-scanner error: {exc}")
    try:
        results.extend(_scan_pki_mounts(client, logger, session_start))
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.v(f"Vault PKI sub-scanner error: {exc}")
    try:
        results.extend(_scan_auth_methods(client, logger, session_start))
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.v(f"Vault auth sub-scanner error: {exc}")

    return results
