"""CBOM builder — converts a list of CryptoEndpoint scan results into a
CycloneDX Bom object with deduplicated algorithm components, certificate
components, and protocol components.

Usage::

    from quirk.cbom.builder import build_cbom
    from quirk.models import CryptoEndpoint

    bom = build_cbom(endpoints)
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Optional

from cyclonedx.model.bom import Bom, BomMetaData
from cyclonedx.model.bom_ref import BomRef
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.dependency import Dependency
from cyclonedx.model.crypto import (
    AlgorithmProperties,
    CertificateProperties,
    CryptoAssetType,
    CryptoExecutionEnvironment,
    CryptoPrimitive,
    CryptoProperties,
    ProtocolProperties,
    ProtocolPropertiesCipherSuite,
    ProtocolPropertiesType,
)

from quirk.cbom.classifier import classify_algorithm
from quirk.models import CryptoEndpoint


# ---------------------------------------------------------------------------
# New-protocol helper functions
# ---------------------------------------------------------------------------

def _extract_algo_from_rule_id(rule_id: str | None) -> str | None:
    """Extract algorithm name hint from semgrep rule_id.

    E.g., 'python.cryptography.security.insecure-hash-algorithms-md5' -> 'MD5'
    """
    if not rule_id:
        return None
    rule_lower = rule_id.lower()
    # Map known algorithm names found in semgrep crypto rules
    algo_hints = {
        "md5": "MD5", "sha1": "SHA-1", "des": "3DES", "rc4": "RC4",
        "blowfish": "Blowfish", "md4": "MD4", "sha-1": "SHA-1",
        "rsa": "RSA", "dsa": "DSA", "aes": "AES-256-GCM",
    }
    for fragment, canonical in algo_hints.items():
        if fragment in rule_lower:
            return canonical
    return None


def _normalize_cloud_key_spec(key_spec: str) -> str | None:
    """Normalize AWS KMS KeySpec or Azure key_type to algorithm name."""
    spec_upper = (key_spec or "").upper().replace("-", "_")
    mapping = {
        "RSA_2048": "RSA", "RSA_3072": "RSA", "RSA_4096": "RSA",
        "ECC_NIST_P256": "ECDSA", "ECC_NIST_P384": "ECDSA", "ECC_NIST_P521": "ECDSA",
        "ECC_SECG_P256K1": "ECDSA", "SYMMETRIC_DEFAULT": "AES-256-GCM",
        "RSA": "RSA", "RSA_HSM": "RSA", "EC": "ECDSA", "EC_HSM": "ECDSA",
        "OCT": "AES-256-GCM", "OCT_HSM": "AES-256-GCM",
    }
    return mapping.get(spec_upper)

# Tool version — duplicated here to avoid circular imports with quirk.reports.writer
PLATFORM_VERSION = "4.1.0"

# ---------------------------------------------------------------------------
# Cipher suite decomposition
# ---------------------------------------------------------------------------

# Ordered fragment rules for TLS cipher suite decomposition.
# Each entry is (fragment_pattern, canonical_name) where fragment_pattern is
# matched against the uppercase suite name token list.
_KEX_MAP: dict[str, str] = {
    "ECDHE": "X25519",
    "ECDH": "X25519",
    "DHE": "DH-GroupExchange",
    "DH": "DH-2048",
    "RSA": "RSA",  # RSA key exchange (used in non-PFS suites)
}

_ENC_MAP: dict[str, str] = {
    "AES_256_GCM": "AES-256-GCM",
    "AES_128_GCM": "AES-128-GCM",
    "AES_256_CCM": "AES-256-GCM",
    "AES_128_CCM": "AES-128-GCM",
    "AES_256_CBC": "AES-256-CBC",
    "AES_128_CBC": "AES-128-CBC",
    "CHACHA20_POLY1305": "ChaCha20-Poly1305",
    "3DES_EDE_CBC": "3DES",
    "RC4_128": "RC4",
    "RC4": "RC4",
}

_AUTH_MAP: dict[str, str] = {
    "RSA": "RSA",
    "ECDSA": "ECDSA",
    "DSS": "DSA",
    "PSK": "PSK",
    "ANON": None,  # anonymous — no auth
}

_MAC_MAP: dict[str, str] = {
    "SHA384": "SHA-384",
    "SHA256": "SHA-256",
    "SHA": "SHA-1",
    "MD5": "MD5",
    "GCM": None,   # integrated in AEAD — not a separate MAC
    "CCM": None,
    "POLY1305": None,  # integrated in ChaCha20-Poly1305
}


def _decompose_cipher_suite(suite: str) -> list[str]:
    """Decompose a TLS cipher suite name into constituent algorithm names.

    Examples:
        TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 -> ['X25519', 'RSA', 'AES-256-GCM', 'SHA-384']
        TLS_AES_256_GCM_SHA384 (TLSv1.3) -> ['AES-256-GCM', 'SHA-384']
        TLS_RSA_WITH_AES_128_CBC_SHA -> ['RSA', 'AES-128-CBC', 'SHA-1']
    """
    if not suite:
        return []

    upper = suite.upper()

    # Detect TLSv1.3 suites — no key exchange in the suite name
    # TLSv1.3 suites look like TLS_AES_* or TLS_CHACHA20_*
    is_tls13 = bool(re.match(r"^TLS_(AES|CHACHA20|CAMELLIA)", upper))

    parts: list[str] = []

    # ---- Before WITH: key-exchange and authentication ----
    # Split on "WITH" to separate key-exchange from cipher
    if "_WITH_" in upper:
        pre_with, post_with = upper.split("_WITH_", 1)
    elif is_tls13:
        pre_with = ""
        post_with = upper[4:]  # strip leading "TLS_"
    else:
        pre_with = upper
        post_with = ""

    # Parse pre-WITH tokens for KEX and AUTH
    pre_tokens = pre_with.replace("TLS_", "").split("_")

    if not is_tls13:
        # Key exchange — first match wins
        kex_name: str | None = None
        for i, token in enumerate(pre_tokens):
            if token in _KEX_MAP:
                kex_name = _KEX_MAP[token]
                break
        if kex_name:
            parts.append(kex_name)

        # Authentication — may be separate from KEX in pre_tokens
        # e.g. ECDHE_RSA -> KEX=X25519, AUTH=RSA
        # Find auth token that is different from the KEX token
        kex_token_used = None
        for token in pre_tokens:
            if token in _KEX_MAP:
                kex_token_used = token
                break

        for token in pre_tokens:
            if token == kex_token_used:
                continue
            if token in _AUTH_MAP:
                auth_name = _AUTH_MAP[token]
                if auth_name and auth_name not in parts:
                    parts.append(auth_name)
                break

    # ---- Post-WITH: encryption + MAC ----
    # Build a "joined" string for multi-token matching (e.g. AES_256_GCM)
    remaining = post_with

    enc_found: str | None = None
    for key, name in _ENC_MAP.items():
        if key in remaining:
            enc_found = name
            break

    if enc_found:
        parts.append(enc_found)

    # Extract trailing MAC token
    # MAC is the last token in the suite name (after enc cipher)
    post_tokens = remaining.split("_")
    last = post_tokens[-1] if post_tokens else ""
    second_last = post_tokens[-2] if len(post_tokens) >= 2 else ""

    # Try two-token combo first (e.g. SHA_384 -> SHA384)
    combo = f"{second_last}{last}"
    mac_name = _MAC_MAP.get(combo) or _MAC_MAP.get(last)
    if mac_name:
        parts.append(mac_name)

    return [p for p in parts if p]  # filter None already done above


# ---------------------------------------------------------------------------
# Component factory helpers
# ---------------------------------------------------------------------------

def _normalize_bom_ref_key(name: str) -> str:
    """Convert a name to a safe bom_ref fragment."""
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name).lower()


def _make_algorithm_component(
    name: str,
    bom_ref_key: str,
    key_size: int | None = None,
) -> Component:
    """Build a CRYPTOGRAPHIC_ASSET/ALGORITHM Component."""
    primitive, nist_level, classical_level = classify_algorithm(name)

    algo_props = AlgorithmProperties(
        primitive=primitive,
        nist_quantum_security_level=nist_level,
        classical_security_level=classical_level,
        execution_environment=CryptoExecutionEnvironment.SOFTWARE_PLAIN_RAM,
        parameter_set_identifier=str(key_size) if key_size is not None else None,
    )
    return Component(
        name=name,
        type=ComponentType.CRYPTOGRAPHIC_ASSET,
        bom_ref=f"crypto/algorithm/{bom_ref_key}",
        crypto_properties=CryptoProperties(
            asset_type=CryptoAssetType.ALGORITHM,
            algorithm_properties=algo_props,
        ),
    )


def _extract_ssh_algorithms(ssh_audit_json_str: str | None) -> dict[str, list[dict]]:
    """Parse ssh_audit_json and return kex/key/enc/mac algorithm lists.

    Returns empty dict on None or invalid JSON.
    """
    if not ssh_audit_json_str:
        return {}
    try:
        data = json.loads(ssh_audit_json_str)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
    result: dict[str, list[dict]] = {}
    for section in ("kex", "key", "enc", "mac"):
        items = data.get(section, [])
        if isinstance(items, list):
            result[section] = items
    return result


# ---------------------------------------------------------------------------
# Registry helper
# ---------------------------------------------------------------------------

def _register_algorithm(
    name: str,
    registry: dict[str, Component],
    key_size: int | None = None,
) -> str:
    """Ensure an algorithm component exists in registry; return its bom_ref key."""
    bom_ref_key = _normalize_bom_ref_key(name)
    if bom_ref_key not in registry:
        registry[bom_ref_key] = _make_algorithm_component(name, bom_ref_key, key_size)
    return bom_ref_key


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_cbom(endpoints: list[CryptoEndpoint]) -> Bom:
    """Convert a list of CryptoEndpoint scan results into a CycloneDX Bom.

    Processing order:
    1. Pass 1 — collect deduplicated algorithm components (keyed by bom_ref)
    2. Pass 2 — build certificate components (one per TLS endpoint with cert info)
    3. Pass 3 — build protocol components (one per endpoint)
    4. Assemble Bom with metadata

    Args:
        endpoints: List of CryptoEndpoint ORM objects from a scan run.

    Returns:
        A CycloneDX Bom instance with CRYPTOGRAPHIC_ASSET components.
    """
    # keyed by bom_ref fragment (e.g. "aes-256-gcm")
    algo_registry: dict[str, Component] = {}
    cert_components: list[Component] = []
    protocol_components: list[Component] = []

    # ------------------------------------------------------------------ #
    # Pass 1 — Algorithm components                                        #
    # ------------------------------------------------------------------ #
    for ep in endpoints:
        if ep.protocol == "SSH":
            # SSH: parse ssh_audit_json
            ssh_data = _extract_ssh_algorithms(ep.ssh_audit_json)
            for section in ("kex", "key", "enc", "mac"):
                for entry in ssh_data.get(section, []):
                    alg = entry.get("algorithm")
                    if alg:
                        keysize = entry.get("keysize")
                        _register_algorithm(alg, algo_registry, key_size=keysize)

        elif ep.protocol == "JWT":
            # JWT: cert_pubkey_alg holds algorithm (RS256, ES256, etc.)
            if ep.cert_pubkey_alg:
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

        elif ep.protocol == "CONTAINER":
            # Container: cipher_suite=library_name, tls_version=library_version
            # No algorithm to register — library presence is the finding.
            pass

        elif ep.protocol == "SOURCE":
            # Source: cipher_suite=semgrep rule_id, extract algorithm hint
            algo_hint = _extract_algo_from_rule_id(ep.cipher_suite)
            if algo_hint:
                _register_algorithm(algo_hint, algo_registry)

        elif ep.protocol in ("AWS", "AZURE"):
            # Cloud: parse cloud_scan_json for algorithm/key spec
            cloud_data = json.loads(ep.cloud_scan_json or "{}")
            key_spec = cloud_data.get("KeySpec") or cloud_data.get("KeyAlgorithm") or cloud_data.get("key_type")
            if key_spec:
                normalized = _normalize_cloud_key_spec(key_spec)
                if normalized:
                    key_size = cloud_data.get("key_size") or ep.cert_pubkey_size
                    _register_algorithm(normalized, algo_registry, key_size=key_size)
            # Also register cert_pubkey_alg if set (ACM certs)
            if ep.cert_pubkey_alg:
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

        else:
            # TLS (default for backwards compatibility with existing protocol values)
            if ep.cipher_suite and ep.cipher_suite.upper() not in ("SSH", ""):
                for algo_name in _decompose_cipher_suite(ep.cipher_suite):
                    _register_algorithm(algo_name, algo_registry)

            # Certificate public key algorithm
            if ep.cert_pubkey_alg:
                pubkey_name = ep.cert_pubkey_alg
                if ep.cert_pubkey_size:
                    pubkey_name = f"{ep.cert_pubkey_alg}-{ep.cert_pubkey_size}"
                _register_algorithm(pubkey_name, algo_registry, key_size=ep.cert_pubkey_size)

            # Certificate signature algorithm
            if ep.cert_sig_alg:
                _register_algorithm(ep.cert_sig_alg, algo_registry)

    # ------------------------------------------------------------------ #
    # Pass 2 — Certificate components                                      #
    # ------------------------------------------------------------------ #
    for ep in endpoints:
        if ep.protocol in ("SSH", "CONTAINER", "SOURCE"):
            continue
        if not ep.cert_pubkey_alg:
            continue  # no cert info available

        cert_bom_ref = f"crypto/certificate/{ep.host}:{ep.port}"

        # Determine bom_ref keys for sig alg and pubkey alg
        sig_alg_ref: BomRef | None = None
        if ep.cert_sig_alg:
            sig_key = _normalize_bom_ref_key(ep.cert_sig_alg)
            sig_alg_ref = BomRef(value=f"crypto/algorithm/{sig_key}")

        pubkey_name = ep.cert_pubkey_alg
        if ep.cert_pubkey_size:
            pubkey_name = f"{ep.cert_pubkey_alg}-{ep.cert_pubkey_size}"
        pubkey_key = _normalize_bom_ref_key(pubkey_name)
        subject_pubkey_ref = BomRef(value=f"crypto/algorithm/{pubkey_key}")

        cert_props = CertificateProperties(
            subject_name=ep.cert_subject,
            issuer_name=ep.cert_issuer,
            not_valid_before=ep.cert_not_before,
            not_valid_after=ep.cert_not_after,
            signature_algorithm_ref=sig_alg_ref,
            subject_public_key_ref=subject_pubkey_ref,
            certificate_format="X.509",
        )
        cert_component = Component(
            name=f"cert:{ep.host}:{ep.port}",
            type=ComponentType.CRYPTOGRAPHIC_ASSET,
            bom_ref=cert_bom_ref,
            crypto_properties=CryptoProperties(
                asset_type=CryptoAssetType.CERTIFICATE,
                certificate_properties=cert_props,
            ),
        )
        cert_components.append(cert_component)

    # ------------------------------------------------------------------ #
    # Pass 3 — Protocol components                                         #
    # ------------------------------------------------------------------ #
    for ep in endpoints:
        if ep.protocol == "SSH":
            proto_bom_ref = f"crypto/protocol/ssh/{ep.host}:{ep.port}"

            # Reference KEX algorithm components as cipher suites
            ssh_data = _extract_ssh_algorithms(ep.ssh_audit_json)
            kex_refs: list[BomRef] = []
            for entry in ssh_data.get("kex", []):
                alg = entry.get("algorithm")
                if alg:
                    key = _normalize_bom_ref_key(alg)
                    kex_refs.append(BomRef(value=f"crypto/algorithm/{key}"))

            cipher_suites = []
            if kex_refs:
                cipher_suites.append(
                    ProtocolPropertiesCipherSuite(
                        name="SSH-KEX",
                        algorithms=kex_refs,
                    )
                )

            proto_component = Component(
                name=f"protocol:ssh:{ep.host}:{ep.port}",
                type=ComponentType.CRYPTOGRAPHIC_ASSET,
                bom_ref=proto_bom_ref,
                crypto_properties=CryptoProperties(
                    asset_type=CryptoAssetType.PROTOCOL,
                    protocol_properties=ProtocolProperties(
                        type=ProtocolPropertiesType.SSH,
                        version="2.0",
                        cipher_suites=cipher_suites if cipher_suites else None,
                    ),
                ),
            )
            protocol_components.append(proto_component)

        elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE"):
            # These are not TLS/SSH network protocols — no ProtocolProperties component.
            # Their cryptographic assets are captured in Pass 1 (algorithms) and Pass 2 (certificates).
            continue

        else:
            # TLS (default)
            proto_bom_ref = f"crypto/protocol/tls/{ep.host}:{ep.port}"

            # Build algorithm refs from cipher suite decomposition
            suite_algo_refs: list[BomRef] = []
            if ep.cipher_suite and ep.cipher_suite.upper() not in ("SSH", ""):
                for algo_name in _decompose_cipher_suite(ep.cipher_suite):
                    key = _normalize_bom_ref_key(algo_name)
                    suite_algo_refs.append(BomRef(value=f"crypto/algorithm/{key}"))

            cipher_suites = []
            if suite_algo_refs:
                suite_name = ep.cipher_suite or "unknown"
                cipher_suites.append(
                    ProtocolPropertiesCipherSuite(
                        name=suite_name,
                        algorithms=suite_algo_refs,
                    )
                )

            # Strip "TLSv" prefix from version
            tls_ver = ep.tls_version or ""
            tls_ver = tls_ver.replace("TLSv", "").replace("TLS ", "").strip()

            proto_component = Component(
                name=f"protocol:tls:{ep.host}:{ep.port}",
                type=ComponentType.CRYPTOGRAPHIC_ASSET,
                bom_ref=proto_bom_ref,
                crypto_properties=CryptoProperties(
                    asset_type=CryptoAssetType.PROTOCOL,
                    protocol_properties=ProtocolProperties(
                        type=ProtocolPropertiesType.TLS,
                        version=tls_ver if tls_ver else None,
                        cipher_suites=cipher_suites if cipher_suites else None,
                    ),
                ),
            )
            protocol_components.append(proto_component)

    # ------------------------------------------------------------------ #
    # Assemble Bom                                                         #
    # ------------------------------------------------------------------ #
    all_components = (
        list(algo_registry.values()) + cert_components + protocol_components
    )

    root_component = Component(
        name="QU.I.R.K.",
        type=ComponentType.APPLICATION,
        version=PLATFORM_VERSION,
    )

    metadata = BomMetaData(
        timestamp=datetime.now(timezone.utc),
        component=root_component,
    )

    # Build dependency graph: root component depends on all crypto components
    child_deps = [Dependency(ref=c.bom_ref) for c in all_components]
    root_dep = Dependency(ref=root_component.bom_ref, dependencies=child_deps)

    return Bom(
        components=all_components,
        metadata=metadata,
        dependencies=[root_dep],
    )
