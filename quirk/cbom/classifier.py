"""Algorithm classifier — maps raw algorithm strings to CycloneDX CryptoPrimitive
enum values and NIST PQC quantum security levels.

Usage::

    from quirk.cbom.classifier import classify_algorithm, quantum_safety_label

    primitive, nist_level, classical_level = classify_algorithm("RSA")
    # -> (CryptoPrimitive.PKE, 0, 112)

    label = quantum_safety_label(nist_level)
    # -> "quantum-vulnerable"
"""
from __future__ import annotations

from enum import Enum

from cyclonedx.model.crypto import CryptoPrimitive


class QuantumSafety(str, Enum):
    """Human-readable quantum safety classification."""

    QUANTUM_VULNERABLE = "quantum-vulnerable"
    QUANTUM_SAFE = "quantum-safe"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


def quantum_safety_label(nist_level: int | None) -> str:
    """Translate a NIST PQC security level to a human-readable label.

    Args:
        nist_level: Integer NIST security level (0 = quantum-vulnerable,
                    1+ = quantum-safe, None = unknown).

    Returns:
        One of "quantum-vulnerable", "quantum-safe", or "unknown".
    """
    if nist_level is None:
        return QuantumSafety.UNKNOWN.value
    if nist_level == 0:
        return QuantumSafety.QUANTUM_VULNERABLE.value
    return QuantumSafety.QUANTUM_SAFE.value


# ---------------------------------------------------------------------------
# Master algorithm lookup table
# Key: normalized algorithm name (lowercase, vendor suffix stripped)
# Value: (CryptoPrimitive, nist_quantum_security_level, classical_security_level)
# ---------------------------------------------------------------------------

_ALGORITHM_TABLE: dict[str, tuple[CryptoPrimitive, int | None, int | None]] = {
    # ------------------------------------------------------------------
    # SSH KEX algorithms (raw ssh-audit strings)
    # ------------------------------------------------------------------
    "curve25519-sha256": (CryptoPrimitive.KEY_AGREE, 0, 128),
    "ecdh-sha2-nistp256": (CryptoPrimitive.KEY_AGREE, 0, 128),
    "ecdh-sha2-nistp384": (CryptoPrimitive.KEY_AGREE, 0, 192),
    "ecdh-sha2-nistp521": (CryptoPrimitive.KEY_AGREE, 0, 256),
    "diffie-hellman-group14-sha256": (CryptoPrimitive.KEY_AGREE, 0, 112),
    "diffie-hellman-group14-sha1": (CryptoPrimitive.KEY_AGREE, 0, 112),
    "diffie-hellman-group16-sha512": (CryptoPrimitive.KEY_AGREE, 0, 128),
    "diffie-hellman-group-exchange-sha256": (CryptoPrimitive.KEY_AGREE, 0, 112),
    "sntrup761x25519-sha512": (CryptoPrimitive.KEM, 3, 128),
    "mlkem768x25519-sha256": (CryptoPrimitive.KEM, 3, 192),
    # ------------------------------------------------------------------
    # SSH host key algorithms
    # ------------------------------------------------------------------
    "ssh-rsa": (CryptoPrimitive.SIGNATURE, 0, 112),
    "rsa-sha2-256": (CryptoPrimitive.SIGNATURE, 0, 112),
    "rsa-sha2-512": (CryptoPrimitive.SIGNATURE, 0, 112),
    "ecdsa-sha2-nistp256": (CryptoPrimitive.SIGNATURE, 0, 128),
    "ecdsa-sha2-nistp384": (CryptoPrimitive.SIGNATURE, 0, 192),
    "ssh-ed25519": (CryptoPrimitive.SIGNATURE, 0, 128),
    "sk-ssh-ed25519": (CryptoPrimitive.SIGNATURE, 0, 128),
    # ------------------------------------------------------------------
    # SSH enc (symmetric cipher) algorithms
    # ------------------------------------------------------------------
    "aes128-ctr": (CryptoPrimitive.BLOCK_CIPHER, 1, 128),
    "aes192-ctr": (CryptoPrimitive.BLOCK_CIPHER, 1, 192),
    "aes256-ctr": (CryptoPrimitive.BLOCK_CIPHER, 1, 256),
    "aes128-gcm": (CryptoPrimitive.AE, 1, 128),
    "aes256-gcm": (CryptoPrimitive.AE, 1, 256),
    "chacha20-poly1305": (CryptoPrimitive.AE, 1, 256),
    # ------------------------------------------------------------------
    # SSH MAC algorithms
    # ------------------------------------------------------------------
    "hmac-sha2-256": (CryptoPrimitive.HASH, 0, 128),
    "hmac-sha2-512": (CryptoPrimitive.HASH, 2, 256),
    "hmac-sha1": (CryptoPrimitive.HASH, 0, 80),
    # ------------------------------------------------------------------
    # CycloneDX canonical names (used by builder for cert/TLS decomposition)
    # ------------------------------------------------------------------
    "rsa": (CryptoPrimitive.PKE, 0, 112),
    "ecdsa": (CryptoPrimitive.SIGNATURE, 0, 128),
    "ec": (CryptoPrimitive.SIGNATURE, 0, 128),
    "ed25519": (CryptoPrimitive.SIGNATURE, 0, 128),
    "ed448": (CryptoPrimitive.SIGNATURE, 0, 224),
    "dsa": (CryptoPrimitive.SIGNATURE, 0, 112),
    "dh-2048": (CryptoPrimitive.KEY_AGREE, 0, 112),
    "dh-4096": (CryptoPrimitive.KEY_AGREE, 0, 128),
    "dh-groupexchange": (CryptoPrimitive.KEY_AGREE, 0, 112),
    "x25519": (CryptoPrimitive.KEY_AGREE, 0, 128),
    "x448": (CryptoPrimitive.KEY_AGREE, 0, 224),
    "aes-256-gcm": (CryptoPrimitive.AE, 1, 256),
    "aes-128-gcm": (CryptoPrimitive.AE, 1, 128),
    "aes-256-cbc": (CryptoPrimitive.BLOCK_CIPHER, 3, 256),
    "aes-128-cbc": (CryptoPrimitive.BLOCK_CIPHER, 1, 128),
    # chacha20-poly1305 already present above (SSH enc form without hyphen variant)
    "3des": (CryptoPrimitive.BLOCK_CIPHER, 0, 112),
    "sha-1": (CryptoPrimitive.HASH, 0, 80),
    "sha-256": (CryptoPrimitive.HASH, 0, 128),
    "sha-384": (CryptoPrimitive.HASH, 2, 192),
    "sha-512": (CryptoPrimitive.HASH, 2, 256),
    # ------------------------------------------------------------------
    # JWT / JOSE algorithms (RFC 7518)
    # ------------------------------------------------------------------
    "rs256": (CryptoPrimitive.SIGNATURE, 0, 112),   # RSA PKCS1 + SHA-256
    "rs384": (CryptoPrimitive.SIGNATURE, 0, 112),   # RSA PKCS1 + SHA-384
    "rs512": (CryptoPrimitive.SIGNATURE, 0, 112),   # RSA PKCS1 + SHA-512
    "es256": (CryptoPrimitive.SIGNATURE, 0, 128),   # ECDSA P-256
    "es384": (CryptoPrimitive.SIGNATURE, 0, 192),   # ECDSA P-384
    "es512": (CryptoPrimitive.SIGNATURE, 0, 256),   # ECDSA P-521
    "hs256": (CryptoPrimitive.MAC, 0, 128),         # HMAC-SHA256
    "hs384": (CryptoPrimitive.MAC, 0, 192),         # HMAC-SHA384
    "hs512": (CryptoPrimitive.MAC, 0, 256),         # HMAC-SHA512
    "ps256": (CryptoPrimitive.SIGNATURE, 0, 112),   # RSA-PSS + SHA-256
    "ps384": (CryptoPrimitive.SIGNATURE, 0, 112),   # RSA-PSS + SHA-384
    "ps512": (CryptoPrimitive.SIGNATURE, 0, 112),   # RSA-PSS + SHA-512
    "eddsa": (CryptoPrimitive.SIGNATURE, 0, 128),   # EdDSA (Ed25519/Ed448)
    "none": (CryptoPrimitive.UNKNOWN, 0, 0),        # alg:none — critical vulnerability
    # ------------------------------------------------------------------
    # NIST PQC standards (FIPS 203 / 204 / 205)
    # ------------------------------------------------------------------
    "ml-kem-512": (CryptoPrimitive.KEM, 1, 128),
    "ml-kem-768": (CryptoPrimitive.KEM, 3, 192),
    "ml-kem-1024": (CryptoPrimitive.KEM, 5, 256),
    "ml-dsa-44": (CryptoPrimitive.SIGNATURE, 2, 128),
    "ml-dsa-65": (CryptoPrimitive.SIGNATURE, 3, 192),
    "ml-dsa-87": (CryptoPrimitive.SIGNATURE, 5, 256),
    "slh-dsa-128": (CryptoPrimitive.SIGNATURE, 1, 128),
    "slh-dsa-192": (CryptoPrimitive.SIGNATURE, 3, 192),
    "slh-dsa-256": (CryptoPrimitive.SIGNATURE, 5, 256),
    "sntrup761x25519": (CryptoPrimitive.KEM, 3, 128),
    "ml-kem-768+x25519": (CryptoPrimitive.KEM, 3, 192),
    # ------------------------------------------------------------------
    # DNSSEC algorithms (RFC 8624 / RFC 9905)
    # ------------------------------------------------------------------
    "rsamd5":             (CryptoPrimitive.PKE, None, None),        # DNSSEC alg 1 — MUST NOT
    "rsasha1":            (CryptoPrimitive.PKE, None, None),        # DNSSEC alg 5 — MUST NOT
    "dsa-nsec3-sha1":     (CryptoPrimitive.SIGNATURE, None, None),  # DNSSEC alg 6 — MUST NOT
    "rsasha1-nsec3-sha1": (CryptoPrimitive.PKE, None, None),        # DNSSEC alg 7 — MUST NOT
    "rsasha256":          (CryptoPrimitive.PKE, None, None),        # DNSSEC alg 8 — quantum-vulnerable
    "rsasha512":          (CryptoPrimitive.PKE, None, None),        # DNSSEC alg 10 — quantum-vulnerable
    "ecc-gost":           (CryptoPrimitive.SIGNATURE, None, None),  # DNSSEC alg 12 — MUST NOT
    "ecdsap256sha256":    (CryptoPrimitive.SIGNATURE, 1, 128),      # DNSSEC alg 13
    "ecdsap384sha384":    (CryptoPrimitive.SIGNATURE, 3, 192),      # DNSSEC alg 14
    # Note: "dsa", "ed25519", "ed448" already present above
    # ------------------------------------------------------------------
    # SAML / OIDC algorithm identifiers
    # ------------------------------------------------------------------
    # SAML XML algorithm URI shortened form (cert_pubkey_alg="SHA1" for SHA-1 URI findings)
    "sha1":   (CryptoPrimitive.HASH, None, None),        # SHA-1 deprecated — quantum-vulnerable hash
    # Note: OIDC JWT algorithm names (rs256, ps256, es256, eddsa, etc.) already present
    # in the JWT/JOSE section above — SAML/OIDC reuse the same algorithm strings
    # ------------------------------------------------------------------
    # Kerberos encryption types (RFC 4120 / RFC 3962 / RFC 8009)
    # ------------------------------------------------------------------
    "des-cbc-crc":                (CryptoPrimitive.BLOCK_CIPHER, None, None),   # etype 1 -- deprecated
    "des-cbc-md4":                (CryptoPrimitive.BLOCK_CIPHER, None, None),   # etype 2 -- deprecated
    "des-cbc-md5":                (CryptoPrimitive.BLOCK_CIPHER, None, None),   # etype 3 -- deprecated
    "aes128-cts-hmac-sha1-96":    (CryptoPrimitive.BLOCK_CIPHER, 0, 128),       # etype 17 -- quantum-vulnerable (Grover)
    "aes256-cts-hmac-sha1-96":    (CryptoPrimitive.BLOCK_CIPHER, 1, 256),       # etype 18 -- quantum-safe
    "aes256-cts-hmac-sha384-192": (CryptoPrimitive.BLOCK_CIPHER, 1, 256),       # etype 20 -- quantum-safe (RFC 8009)
    "rc4-hmac":                   (CryptoPrimitive.BLOCK_CIPHER, 0, 128),       # etype 23 -- quantum-vulnerable
}

_FALLBACK = (CryptoPrimitive.UNKNOWN, None, None)


def classify_algorithm(
    name: str,
) -> tuple[CryptoPrimitive, int | None, int | None]:
    """Classify a cryptographic algorithm string.

    Performs the following normalization steps before lookup:
    1. Strip vendor suffixes (``@openssh.com``, ``@libssh.org``, etc.)
    2. Lowercase the result
    3. Direct lookup in ``_ALGORITHM_TABLE``
    4. If not found, attempt a secondary lookup after removing hyphens between
       a letter and a digit (e.g. ``"aes128ctr"`` -> ``"aes128-ctr"``)

    Args:
        name: Raw algorithm string from TLS, SSH, or certificate scanner output.

    Returns:
        A 3-tuple ``(CryptoPrimitive, nist_quantum_level, classical_security_level)``.
        Unknown algorithms return ``(CryptoPrimitive.UNKNOWN, None, None)``.
    """
    if not name:
        return _FALLBACK

    # Step 1: strip vendor suffix
    normalized = name.split("@")[0]

    # Step 2: lowercase
    key = normalized.lower()

    # Step 3: direct lookup
    result = _ALGORITHM_TABLE.get(key)
    if result is not None:
        return result

    # Step 4: fuzzy normalization — handle SSH-style compact names like
    # "aes128ctr" that may arrive without hyphens
    import re
    # Insert hyphen between letters and digits when not already present:
    # "aes128ctr" -> not in table, but "aes128-ctr" might be
    denormalized = re.sub(r"([a-z])(\d)", r"\1-\2", key)
    denormalized = re.sub(r"(\d)([a-z])", r"\1-\2", denormalized)
    if denormalized != key:
        result = _ALGORITHM_TABLE.get(denormalized)
        if result is not None:
            return result

    return _FALLBACK
