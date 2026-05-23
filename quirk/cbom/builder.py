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

from cyclonedx.model import Property
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

from quirk import __version__ as PLATFORM_VERSION  # closes cbom-intel-reports/IN-01 (Phase 77 D-07)
from quirk.cbom.classifier import classify_algorithm
from quirk.compliance.cmvp import coverage_for_algorithm  # Phase 81 CMVP-01: informational coverage list
from quirk.models import CryptoEndpoint
from quirk.util.safe_exc import safe_str

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level skip lists — exposed so unit tests can drive parametrize off them.
# Per D-10 / D-11 (Phase 42).
# ---------------------------------------------------------------------------

MOTION_PLAINTEXT_PROTOCOLS: frozenset[str] = frozenset({
    "KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN",
})

DAR_SKIP_PROTOCOLS: frozenset[str] = frozenset({
    "POSTGRESQL", "MYSQL", "RDS",
    "S3", "AZURE_BLOB",
    "KUBERNETES", "VAULT",
    "GCP", "CLOUD_SQL",
})


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
    # Map known algorithm names found in semgrep crypto rules.
    # Ordered list — longer/more-specific patterns checked first to avoid
    # false positives (e.g. "ecdsa" must match before "dsa", "3des" before "des").
    algo_hints = [
        ("ecdsa", "ECDSA"), ("sha-1", "SHA-1"), ("sha1", "SHA-1"),
        ("blowfish", "Blowfish"), ("3des", "3DES"),
        ("md5", "MD5"), ("md4", "MD4"), ("rc4", "RC4"),
        ("rsa", "RSA"), ("dsa", "DSA"), ("des", "DES"),
        ("aes-256", "AES-256"), ("aes-128", "AES-128"),
        ("aes", "AES"),
    ]
    for fragment, canonical in algo_hints:
        if fragment in rule_lower:
            return canonical
    return None


def _normalize_cloud_key_spec(key_spec: str) -> str | None:
    """Normalize AWS KMS KeySpec, Azure key_type, or GCP algorithm string to algorithm name."""
    spec_upper = (key_spec or "").upper().replace("-", "_")
    mapping = {
        "RSA_2048": "RSA", "RSA_3072": "RSA", "RSA_4096": "RSA",
        "ECC_NIST_P256": "ECDSA", "ECC_NIST_P384": "ECDSA", "ECC_NIST_P521": "ECDSA",
        "ECC_SECG_P256K1": "ECDSA", "SYMMETRIC_DEFAULT": "AES-256-GCM",
        "RSA": "RSA", "RSA_HSM": "RSA", "EC": "ECDSA", "EC_HSM": "ECDSA",
        "OCT": "AES-256-GCM", "OCT_HSM": "AES-256-GCM",
        # GCP Cloud KMS algorithm strings (Phase 26)
        "RSA_SIGN_PKCS1_2048_SHA256": "RSA", "RSA_SIGN_PKCS1_3072_SHA256": "RSA",
        "RSA_SIGN_PKCS1_4096_SHA256": "RSA", "RSA_SIGN_PKCS1_4096_SHA512": "RSA",
        "RSA_SIGN_PSS_2048_SHA256": "RSA", "RSA_SIGN_PSS_3072_SHA256": "RSA",
        "RSA_SIGN_PSS_4096_SHA256": "RSA", "RSA_SIGN_PSS_4096_SHA512": "RSA",
        "RSA_SIGN_RAW_PKCS1_2048": "RSA", "RSA_SIGN_RAW_PKCS1_3072": "RSA",
        "RSA_SIGN_RAW_PKCS1_4096": "RSA",
        "RSA_DECRYPT_OAEP_2048_SHA256": "RSA", "RSA_DECRYPT_OAEP_3072_SHA256": "RSA",
        "RSA_DECRYPT_OAEP_4096_SHA256": "RSA", "RSA_DECRYPT_OAEP_4096_SHA512": "RSA",
        "RSA_DECRYPT_OAEP_2048_SHA1": "RSA", "RSA_DECRYPT_OAEP_3072_SHA1": "RSA",
        "RSA_DECRYPT_OAEP_4096_SHA1": "RSA",
        "EC_SIGN_P256_SHA256": "ECDSA", "EC_SIGN_P384_SHA384": "ECDSA",
        "EC_SIGN_SECP256K1_SHA256": "ECDSA", "EC_SIGN_ED25519": "EdDSA",
        "GOOGLE_SYMMETRIC_ENCRYPTION": "AES-256-GCM",
        "AES_128_GCM": "AES-128-GCM", "AES_256_GCM": "AES-256-GCM",
        "AES_128_CBC": "AES-128-CBC", "AES_256_CBC": "AES-256-CBC",
        "AES_128_CTR": "AES-128-CTR", "AES_256_CTR": "AES-256-CTR",
        "HMAC_SHA256": "HMAC", "HMAC_SHA1": "HMAC", "HMAC_SHA384": "HMAC",
        "HMAC_SHA512": "HMAC", "HMAC_SHA224": "HMAC",
        "EXTERNAL_SYMMETRIC_ENCRYPTION": "AES-256-GCM",
        "ML_KEM_768": "ml-kem-768", "ML_KEM_1024": "ml-kem-1024",
        "KEM_XWING": "ml-kem-768",
        "PQ_SIGN_ML_DSA_44": "ml-dsa-44", "PQ_SIGN_ML_DSA_65": "ml-dsa-65",
        "PQ_SIGN_ML_DSA_87": "ml-dsa-87",
        "PQ_SIGN_SLH_DSA_SHA2_128S": "slh-dsa-128",
        "PQ_SIGN_HASH_SLH_DSA_SHA2_128S_SHA256": "slh-dsa-128",
        "PQ_SIGN_ML_DSA_44_EXTERNAL_MU": "ml-dsa-44",
        "PQ_SIGN_ML_DSA_65_EXTERNAL_MU": "ml-dsa-65",
        "PQ_SIGN_ML_DSA_87_EXTERNAL_MU": "ml-dsa-87",
    }
    return mapping.get(spec_upper)

# Tool version — single-source via `from quirk import __version__ as PLATFORM_VERSION`
# at module top (Phase 77 D-07 / cbom-intel-reports/IN-01).

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
    "RSA": "RSA-kex",  # D-08/WR-12 Phase 73: relabel to disambiguate from cert-signature RSA-auth
    # Phase 90 PQC-02 gap-closure: bare hybrid NamedGroup-4588 name observed by
    # the raw openssl s_client probe — no _WITH_ separator, single token, maps
    # directly to the existing classifier alias x25519mlkem768 → (KEM, 3, 192).
    "X25519MLKEM768": "X25519MLKEM768",
}

_ENC_MAP: dict[str, str] = {
    "AES_256_GCM": "AES-256-GCM",
    "AES_128_GCM": "AES-128-GCM",
    "AES_256_CCM": "AES-256-CCM",
    "AES_128_CCM": "AES-128-CCM",
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


def _fips_status(nist_level: int | None) -> str:
    """Return FIPS 140-3 approval status from NIST quantum security level.

    Per Phase 52 D-02:
        nist_level >= 1    -> "approved"     (quantum-safe or NIST-approved classical)
        nist_level == 0    -> "non-approved" (quantum-vulnerable: RSA, 3DES, etc.)
        nist_level is None -> "non-approved" (unknown algorithm)

    The "certified" tier is reserved for a future phase with CMVP attestation
    support (Phase 52 D-01) and is intentionally never emitted in v4.7.
    """
    return "approved" if (nist_level is not None and nist_level >= 1) else "non-approved"


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
    # Phase 81 CMVP-01 / D-81-R3: attach an *additional* informational property
    # listing CMVP modules that cover this algorithm family. NEVER mutate
    # _fips_status() — v4.10-D-01 forbids activating the "certified" tier from
    # algorithm-name matching alone. This Property is alongside, not inside,
    # the existing quirk:fips140-3-status property.
    properties = [Property(name="quirk:fips140-3-status", value=_fips_status(nist_level))]
    _cmvp_coverage = coverage_for_algorithm(name)
    if _cmvp_coverage:
        _module_names = ", ".join(m["name"] for m in _cmvp_coverage)
        properties.append(Property(name="quirk:cmvp-coverage", value=_module_names))
    return Component(
        name=name,
        type=ComponentType.CRYPTOGRAPHIC_ASSET,
        bom_ref=f"crypto/algorithm/{bom_ref_key}",
        crypto_properties=CryptoProperties(
            asset_type=CryptoAssetType.ALGORITHM,
            algorithm_properties=algo_props,
        ),
        properties=properties,
    )


def _extract_ssh_algorithms(ssh_audit_json_str: str | None) -> dict[str, list[dict]]:
    """Parse ssh_audit_json and return kex/key/enc/mac algorithm lists.

    Returns empty dict on None or invalid JSON.
    """
    if not ssh_audit_json_str:
        return {}
    try:
        data = json.loads(ssh_audit_json_str)
    except json.JSONDecodeError as e:
        # closes cbom-intel-reports/IN-02 (Phase 77 D-08) — no longer silent;
        # surface parse failure via Phase 59 safe_str sanitization.
        logger.warning("Failed to parse SSH algorithms JSON: %s", safe_str(e))
        return {}
    except (TypeError, ValueError):
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


def _extract_fp(service_detail: str | None) -> str | None:
    """Extract the SHA-256 fingerprint hex from a CODE_SIGNING service_detail token.

    service_detail is pipe-delimited; this returns the value of the first
    "fingerprint=<hex>" token.  Returns None when the token is absent.

    Example: "fingerprint=deadbeef...|weak" → "deadbeef..."

    Security note (T-95-05): only the fixed "fingerprint=" token is parsed;
    no eval or exec is performed; unrecognised tokens are silently ignored.
    """
    if not service_detail:
        return None
    for token in service_detail.split("|"):
        if token.startswith("fingerprint="):
            value = token[len("fingerprint="):]
            return value if value else None
    return None


def _codesign_surrogate_key(ep: "CryptoEndpoint") -> tuple[str, str, str] | None:
    """Compute the cross-source surrogate key for a CODE_SIGNING endpoint.

    Returns (cert_subject, cert_pubkey_alg, cert_not_after) when all three
    fields are non-empty, else None.  The surrogate key is used to detect
    certs already emitted via TLS Pass-2 (CSIGN-03 cross-source dedup).
    """
    subj = str(getattr(ep, "cert_subject", "") or "").strip()
    alg = str(getattr(ep, "cert_pubkey_alg", "") or "").strip()
    not_after = str(getattr(ep, "cert_not_after", "") or "").strip()
    if subj and alg and not_after:
        return (subj, alg, not_after)
    return None


def _tls_surrogate_key(ep: "CryptoEndpoint") -> tuple[str, str, str] | None:
    """Compute the surrogate key for a TLS endpoint's certificate.

    Returns (cert_subject, cert_pubkey_alg, cert_not_after) when all three
    fields are non-empty, else None.
    """
    subj = str(getattr(ep, "cert_subject", "") or "").strip()
    alg = str(getattr(ep, "cert_pubkey_alg", "") or "").strip()
    not_after = str(getattr(ep, "cert_not_after", "") or "").strip()
    if subj and alg and not_after:
        return (subj, alg, not_after)
    return None


def _emit_coverage_note(bom_component: Component | None, note: str) -> None:
    """Attach a quirk:coverage-note property to the Bom root component (D-06).

    Used for genuinely plaintext endpoints or library-level-only observations
    where no cryptographic algorithm can be catalogued. Note values MUST be
    hardcoded string literals — never scanner-derived input (T-88-03).
    """
    if bom_component is None:
        return
    prop = Property(name="quirk:coverage-note", value=note)
    existing = list(bom_component.properties or [])
    existing.append(prop)
    bom_component.properties = existing


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
    # D-06: accumulate affirmative no-crypto markers during Pass-1; attach after assembly
    coverage_notes: list[str] = []

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
            # D-07: fallback — only register cert_pubkey_alg when ssh_audit_json was empty/unparseable;
            # if ssh_data is populated the host key algorithm is already captured from the key section.
            if ep.cert_pubkey_alg and not ssh_data:
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

        elif ep.protocol == "JWT":
            # JWT: cert_pubkey_alg holds algorithm (RS256, ES256, etc.)
            if ep.cert_pubkey_alg:
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

        elif ep.protocol == "BEARER_TOKEN":
            # TOKEN-02 (Phase 94): operator-supplied bearer credential, classified passively.
            # cert_pubkey_alg holds the declared JWT algorithm (e.g. RS256, ES256, HS256).
            # Label: "declared_algorithm (unverified)" — NEVER treated as enforced.
            # T-94-03: only the declared algorithm is registered; raw token never reaches CBOM.
            if ep.cert_pubkey_alg:
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
            # Affirmative coverage note — hardcoded literal per T-88-03 (never scanner-derived value)
            coverage_notes.append("bearer-token-declared-algorithm")

        elif ep.protocol == "CONTAINER":
            # Container: cipher_suite=library_name (e.g., "openssl", "libssl")
            # D-06 / SCORE-CBOM-01: library names are not algorithm names; emit coverage note
            # instead of registering a library string that would produce UNKNOWN primitive.
            if ep.cipher_suite:
                # D-06 / T-88-03: affirmative coverage marker (hardcoded literal — not scanner-derived value)
                coverage_notes.append(
                    "crypto library/pattern observed; algorithm-level detail not captured"
                    " by container scanner"
                )

        elif ep.protocol == "SOURCE":
            # Source: cipher_suite=semgrep rule_id, extract algorithm hint
            algo_hint = _extract_algo_from_rule_id(ep.cipher_suite)
            if algo_hint:
                _register_algorithm(algo_hint, algo_registry)
            elif ep.cipher_suite:
                # D-06 / T-88-03: raw rule ID does not encode a specific algorithm;
                # emit affirmative coverage note (hardcoded literal — never scanner-derived value)
                coverage_notes.append(
                    "crypto library/pattern observed; algorithm-level detail not captured"
                    " by source scanner"
                )

        elif ep.protocol in ("AWS", "AZURE", "GCP"):
            # Cloud: parse cloud_scan_json for algorithm/key spec
            try:
                cloud_data = json.loads(ep.cloud_scan_json or "{}")
            except (json.JSONDecodeError, TypeError, ValueError):
                cloud_data = {}
            key_spec = (cloud_data.get("KeySpec") or cloud_data.get("KeyAlgorithm")
                        or cloud_data.get("key_type") or cloud_data.get("gcp_algorithm"))
            if key_spec:
                normalized = _normalize_cloud_key_spec(key_spec)
                if normalized:
                    key_size = cloud_data.get("key_size") or ep.cert_pubkey_size
                    _register_algorithm(normalized, algo_registry, key_size=key_size)
            # Also register cert_pubkey_alg if set (ACM certs, GCS-SUMMARY sentinel is skipped via falsy check)
            if ep.cert_pubkey_alg and ep.cert_pubkey_alg not in ("GCS-SUMMARY",):
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

        elif ep.protocol == "CLOUD_SQL":
            # Cloud SQL findings encode severity (HIGH/MEDIUM), not algorithm names.
            # Skip algorithm registration — finding detail is in cloud_scan_json.
            pass

        elif ep.protocol == "DNSSEC":
            # DNSSEC: cert_pubkey_alg holds the DNSKEY algorithm name
            # Exclude synthetic finding types — they are not real cryptographic algorithms
            if ep.cert_pubkey_alg and ep.cert_pubkey_alg not in ("NONE", "NSEC", "DS-MISMATCH", "SHA1-DS"):
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

        elif ep.protocol == "SAML":
            # SAML: cert_pubkey_alg holds algorithm name (RSA, ECDSA) or SHA1 for URI findings
            if ep.cert_pubkey_alg:
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

        elif ep.protocol == "SMIME":
            # SMIME: cert_pubkey_alg holds algorithm name (RSA, ECDSA) from
            # userCertificate / userSMIMECertificate. Pass-1 only — Pass-2/3
            # skip the SMIME protocol literal (see skip tuples below).
            # Phase 79 SMIME-06.
            if ep.cert_pubkey_alg:
                _register_algorithm(
                    ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size
                )

        elif ep.protocol == "ADCS":
            # ADCS: cert_pubkey_alg holds the CA signing algorithm or template
            # key algorithm. Pass-1 only — Pass-2/3 skip the ADCS literal
            # (see skip tuples below). Phase 80 ADCS-06.
            if ep.cert_pubkey_alg:
                _register_algorithm(
                    ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size
                )

        elif ep.protocol == "CODE_SIGNING":
            # CODE_SIGNING: cert_pubkey_alg holds the signing key algorithm (RSA, ECDSA).
            # Pass-1 only — Pass-2/3 skip this protocol (cert dedup handled separately
            # after Pass-2; no ProtocolProperties for a non-transport protocol).
            # Phase 95 CSIGN-03.
            if ep.cert_pubkey_alg:
                _register_algorithm(
                    ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size
                )

        elif ep.protocol == "KERBEROS":
            # Kerberos: cert_pubkey_alg holds the etype name (e.g. "rc4-hmac", "aes256-cts-hmac-sha1-96")
            # Exclude "kerberos-unreachable" synthetic finding -- not a real algorithm (per D-18)
            if ep.cert_pubkey_alg and ep.cert_pubkey_alg != "kerberos-unreachable":
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

        elif ep.protocol == "VAULT":
            # D-01: Vault transit key type lives in cert_pubkey_alg
            # (e.g., "rsa-2048", "aes256-gcm96", "ed25519")
            # VAULT stays in DAR_SKIP_PROTOCOLS for Pass-2/3 (no X.509 cert components)
            if ep.cert_pubkey_alg:
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

        elif ep.protocol == "MYSQL":
            # D-04: MySQL cipher in service_detail as "MySQL/<cipher>-ok" or "MySQL/<cipher>-weak"
            detail = ep.service_detail or ""
            if "/" in detail:
                cipher_part = detail.split("/", 1)[1]
                if cipher_part.endswith(("-ok", "-weak")):
                    cipher_name = cipher_part.rsplit("-", 1)[0]
                else:
                    cipher_name = cipher_part
                if cipher_name and cipher_name.upper() not in ("SSL-OFF", "UNSPECIFIED", ""):
                    _register_algorithm(cipher_name, algo_registry)
                elif cipher_name.upper() == "SSL-OFF":
                    # D-06 / T-88-03: affirmative no-crypto marker (hardcoded literal)
                    coverage_notes.append(
                        "plaintext endpoint — MySQL connection uses no TLS;"
                        " no cryptographic material observed"
                    )

        elif ep.protocol in ("POSTGRESQL", "RDS"):
            # D-04: Postgres/RDS: cert_pubkey_alg may be set by RDS connector; bare Postgres skips cleanly
            if ep.cert_pubkey_alg:
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
            else:
                # D-06 / T-88-03: ssl-off endpoint — affirmative no-crypto marker (hardcoded literal)
                coverage_notes.append(
                    "plaintext endpoint — PostgreSQL/RDS connection uses no TLS;"
                    " no cryptographic material observed"
                )

        elif ep.protocol in ("S3", "AZURE_BLOB"):
            # D-05: S3/Azure Blob: service_detail encodes encryption posture
            # ("S3/sse-s3", "S3/sse-kms-aws", "S3/sse-kms-cmk", "S3/unencrypted")
            # Only register AES-256 when posture is positively confirmed as encrypted;
            # None/"" means "unknown" — do not emit a false-positive algorithm entry.
            _S3_ENCRYPTED_POSTURES = frozenset({
                "sse-s3", "sse-kms-aws", "sse-kms-cmk",      # S3
                "sse-cmek", "sse-microsoft-storage",           # Azure Blob
            })
            detail = ep.service_detail or ""
            detail_lower = detail.lower()
            if any(posture in detail_lower for posture in _S3_ENCRYPTED_POSTURES):
                _register_algorithm("AES-256", algo_registry)
            elif "unencrypted" in detail_lower or (detail and not any(
                posture in detail_lower for posture in _S3_ENCRYPTED_POSTURES
            )):
                # D-06 / T-88-03: unencrypted bucket — affirmative no-crypto marker (hardcoded literal)
                coverage_notes.append(
                    "unencrypted S3/Blob endpoint — no server-side encryption observed;"
                    " no algorithm material to catalog"
                )

        elif ep.protocol == "KUBERNETES":
            # Kubernetes config findings — no key material to catalog.
            pass

        elif ep.protocol in MOTION_PLAINTEXT_PROTOCOLS:
            # D-08: Plaintext broker subfamilies: no encryption to catalog (the absence IS the finding)
            pass

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
        if ep.protocol in (
            "SSH", "BEARER_TOKEN", "JWT", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC", "SMIME", "ADCS",
            "CODE_SIGNING",
            "REST_FUZZ",  # Phase 96 FUZZ-01: no X.509 cert — active fuzz findings carry no TLS metadata
            "OPENAPI",    # Phase 94 SPEC-01: spec findings carry no X.509 cert — algorithm registered in Pass-1
            *DAR_SKIP_PROTOCOLS,
            *MOTION_PLAINTEXT_PROTOCOLS,
        ):
            # BEARER_TOKEN (Phase 94 TOKEN-02) and JWT have no X.509 cert components —
            # their algorithm was already registered in Pass 1.
            # CODE_SIGNING (Phase 95 CSIGN-03): cert components emitted in the fingerprint
            # dedup pass below, not here, to enable TLS-wins cross-source reconciliation.
            # REST_FUZZ (Phase 96 FUZZ-01): active fuzz findings carry no TLS metadata;
            # skipped here to prevent phantom crypto/protocol/tls/* components.
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
    # Pass 2b — CODE_SIGNING certificate dedup (CSIGN-03, Phase 95)       #
    # ------------------------------------------------------------------ #
    # Build a surrogate-key index from TLS-derived cert components already
    # emitted in Pass 2.  Key = (cert_subject, cert_pubkey_alg, cert_not_after).
    # For each CODE_SIGNING endpoint:
    #   (a) Fingerprint-based same-source dedup: first occurrence for a given
    #       SHA-256 fingerprint wins; duplicates are skipped.
    #   (b) Cross-source surrogate dedup: when the surrogate key matches an
    #       existing TLS-derived cert component the TLS component wins and the
    #       CODE_SIGNING endpoint annotates it with a CycloneDX Property
    #       ("quirk:code-signing-eku" = "true") rather than emitting a new
    #       cert component.
    # Build a surrogate-key → cert-component index from the TLS-derived certs
    # emitted in Pass 2. Only TLS endpoints carry the (subject, alg, not_after)
    # metadata used by this dedup; restrict to them with an explicit allow-list
    # (an exclusion list would silently break if a new cert-emitting protocol
    # were added — WR-02).
    _TLS_CERT_SOURCE_PROTOCOLS = ("TLS",)
    _tls_surrogate_index: dict[tuple[str, str, str], Component] = {}
    for ep in endpoints:
        if ep.protocol not in _TLS_CERT_SOURCE_PROTOCOLS:
            continue
        key = _tls_surrogate_key(ep)
        if key is None:
            continue
        # Map to the cert component emitted for this TLS endpoint
        bom_ref_val = f"crypto/certificate/{ep.host}:{ep.port}"
        for c in cert_components:
            if getattr(c.bom_ref, "value", None) == bom_ref_val:
                _tls_surrogate_index[key] = c
                break

    # Now process CODE_SIGNING endpoints
    _codesign_fp_seen: dict[str, str] = {}  # fp_hex → bom_ref_value
    for ep in endpoints:
        if ep.protocol != "CODE_SIGNING":
            continue
        if not ep.cert_pubkey_alg:
            continue

        fp = _extract_fp(getattr(ep, "service_detail", None))
        surrogate = _codesign_surrogate_key(ep)

        # Cross-source reconciliation: TLS-derived cert wins
        if surrogate is not None and surrogate in _tls_surrogate_index:
            # Annotate the existing TLS cert component
            tls_cert_component = _tls_surrogate_index[surrogate]
            existing_props = list(tls_cert_component.properties or [])
            existing_props.append(
                Property(name="quirk:code-signing-eku", value="true")
            )
            tls_cert_component.properties = existing_props
            # Record fingerprint as already-seen so same-source dups are also suppressed
            if fp:
                _codesign_fp_seen.setdefault(fp, getattr(tls_cert_component.bom_ref, "value", ""))
            continue

        # Fingerprint-based same-source dedup
        if fp is not None:
            if fp in _codesign_fp_seen:
                continue  # duplicate fingerprint — already emitted
            bom_ref_val = f"crypto/certificate/codesign/{fp}"
            _codesign_fp_seen[fp] = bom_ref_val
        else:
            # No fingerprint: use host:port as fallback bom_ref (no dedup possible)
            bom_ref_val = f"crypto/certificate/codesign/{ep.host}:{ep.port}"

        # Determine algorithm refs (mirrors Pass-2 TLS pattern)
        sig_alg_ref_cs: BomRef | None = None
        if ep.cert_sig_alg:
            sig_key = _normalize_bom_ref_key(ep.cert_sig_alg)
            sig_alg_ref_cs = BomRef(value=f"crypto/algorithm/{sig_key}")

        pubkey_name_cs = ep.cert_pubkey_alg
        if ep.cert_pubkey_size:
            pubkey_name_cs = f"{ep.cert_pubkey_alg}-{ep.cert_pubkey_size}"
        pubkey_key_cs = _normalize_bom_ref_key(pubkey_name_cs)
        subject_pubkey_ref_cs = BomRef(value=f"crypto/algorithm/{pubkey_key_cs}")

        cs_cert_props = CertificateProperties(
            subject_name=ep.cert_subject,
            issuer_name=ep.cert_issuer,
            not_valid_before=ep.cert_not_before,
            not_valid_after=ep.cert_not_after,
            signature_algorithm_ref=sig_alg_ref_cs,
            subject_public_key_ref=subject_pubkey_ref_cs,
            certificate_format="X.509",
        )
        cs_cert_component = Component(
            name=f"cert:codesign:{fp or ep.host + ':' + str(ep.port)}",
            type=ComponentType.CRYPTOGRAPHIC_ASSET,
            bom_ref=bom_ref_val,
            crypto_properties=CryptoProperties(
                asset_type=CryptoAssetType.CERTIFICATE,
                certificate_properties=cs_cert_props,
            ),
        )
        cs_cert_component.properties = [
            Property(name="quirk:code-signing-eku", value="true")
        ]
        cert_components.append(cs_cert_component)
        # NOTE: we intentionally do NOT add this CODE_SIGNING-emitted component to
        # _tls_surrogate_index.  That index is strictly for TLS-derived wins; adding
        # CODE_SIGNING components there would cause same-metadata but distinct-fingerprint
        # certs to collapse incorrectly.  Fingerprint is the authoritative identity for
        # CODE_SIGNING certs; surrogate-key dedup only guards against TLS-source duplicates.

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

        elif ep.protocol in (
            "JWT", "BEARER_TOKEN", "CONTAINER", "SOURCE", "AWS", "AZURE",
            "DNSSEC", "SAML", "KERBEROS", "SMIME", "ADCS", "CODE_SIGNING",
            "REST_FUZZ",  # Phase 96 FUZZ-01: no ProtocolProperties; skipped to prevent phantom protocol:tls components
            "OPENAPI",    # Phase 94 SPEC-01: no ProtocolProperties; skipped to prevent phantom protocol:tls components
            *DAR_SKIP_PROTOCOLS,
            *MOTION_PLAINTEXT_PROTOCOLS,
        ):
            # These are not TLS/SSH network protocols — no ProtocolProperties component.
            # Their cryptographic assets are captured in Pass 1 (algorithms) and Pass 2 (certificates).
            # BEARER_TOKEN added Phase 94 TOKEN-02: no ProtocolProperties (bearer is not a transport protocol).
            # CODE_SIGNING (Phase 95 CSIGN-03): no ProtocolProperties; cert dedup handled below Pass-2.
            # REST_FUZZ (Phase 96 FUZZ-01): active fuzz findings carry no TLS metadata; skipped here
            # to prevent phantom crypto/protocol/tls/{host}:{port} CBOM components.
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

    # D-06 / SCORE-CBOM-01: attach affirmative no-crypto markers accumulated during Pass-1
    for note in coverage_notes:
        _emit_coverage_note(root_component, note)

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
