"""Tests for quirk.cbom.classifier — RED phase (classifier.py does not exist yet)."""
import pytest
from cyclonedx.model.crypto import CryptoPrimitive
from quirk.cbom.classifier import classify_algorithm, quantum_safety_label, QuantumSafety


# ---------------------------------------------------------------------------
# Quantum-vulnerable asymmetric algorithms (nist_level == 0)
# ---------------------------------------------------------------------------

def test_rsa_maps_to_pke_level0():
    primitive, nist_level, classical_level = classify_algorithm("RSA")
    assert primitive == CryptoPrimitive.PKE
    assert nist_level == 0
    assert classical_level == 112


def test_ecdsa_maps_to_signature_level0():
    primitive, nist_level, classical_level = classify_algorithm("ECDSA")
    assert primitive == CryptoPrimitive.SIGNATURE
    assert nist_level == 0
    assert classical_level == 128


def test_ec_alias_maps_like_ecdsa():
    primitive, nist_level, classical_level = classify_algorithm("EC")
    assert primitive == CryptoPrimitive.SIGNATURE
    assert nist_level == 0
    assert classical_level == 128


def test_ed25519_maps_to_signature_level0():
    primitive, nist_level, classical_level = classify_algorithm("Ed25519")
    assert primitive == CryptoPrimitive.SIGNATURE
    assert nist_level == 0
    assert classical_level == 128


def test_dh_maps_to_key_agree_level0():
    primitive, nist_level, classical_level = classify_algorithm("DH-2048")
    assert primitive == CryptoPrimitive.KEY_AGREE
    assert nist_level == 0
    assert classical_level == 112


def test_x25519_maps_to_key_agree_level0():
    primitive, nist_level, classical_level = classify_algorithm("X25519")
    assert primitive == CryptoPrimitive.KEY_AGREE
    assert nist_level == 0
    assert classical_level == 128


# ---------------------------------------------------------------------------
# SSH KEX algorithms
# ---------------------------------------------------------------------------

def test_ssh_kex_curve25519():
    primitive, nist_level, classical_level = classify_algorithm("curve25519-sha256")
    assert primitive == CryptoPrimitive.KEY_AGREE
    assert nist_level == 0
    assert classical_level == 128


def test_ssh_kex_vendor_suffix_stripped():
    result_plain = classify_algorithm("curve25519-sha256")
    result_vendor = classify_algorithm("curve25519-sha256@libssh.org")
    assert result_plain == result_vendor


def test_ssh_kex_dh_group14():
    primitive, nist_level, classical_level = classify_algorithm("diffie-hellman-group14-sha256")
    assert primitive == CryptoPrimitive.KEY_AGREE
    assert nist_level == 0
    assert classical_level == 112


def test_ssh_kex_sntrup761_hybrid():
    primitive, nist_level, classical_level = classify_algorithm("sntrup761x25519-sha512@openssh.com")
    assert primitive == CryptoPrimitive.KEM
    assert nist_level == 3
    assert classical_level == 128


# ---------------------------------------------------------------------------
# SSH host key algorithms
# ---------------------------------------------------------------------------

def test_ssh_hostkey_rsa():
    primitive, nist_level, classical_level = classify_algorithm("ssh-rsa")
    assert primitive == CryptoPrimitive.SIGNATURE
    assert nist_level == 0
    assert classical_level == 112


def test_ssh_hostkey_ed25519():
    primitive, nist_level, classical_level = classify_algorithm("ssh-ed25519")
    assert primitive == CryptoPrimitive.SIGNATURE
    assert nist_level == 0
    assert classical_level == 128


def test_ssh_hostkey_ecdsa_p256():
    primitive, nist_level, classical_level = classify_algorithm("ecdsa-sha2-nistp256")
    assert primitive == CryptoPrimitive.SIGNATURE
    assert nist_level == 0
    assert classical_level == 128


# ---------------------------------------------------------------------------
# Symmetric / hash (quantum-resistant at sufficient key length)
# ---------------------------------------------------------------------------

def test_aes256gcm_level1():
    primitive, nist_level, classical_level = classify_algorithm("AES-256-GCM")
    assert primitive == CryptoPrimitive.AE
    assert nist_level == 1
    assert classical_level == 256


def test_aes128gcm_level1():
    primitive, nist_level, classical_level = classify_algorithm("AES-128-GCM")
    assert primitive == CryptoPrimitive.AE
    assert nist_level == 1
    assert classical_level == 128


def test_chacha20_poly1305_level1():
    primitive, nist_level, classical_level = classify_algorithm("ChaCha20-Poly1305")
    assert primitive == CryptoPrimitive.AE
    assert nist_level == 1
    assert classical_level == 256


def test_sha384_level2():
    primitive, nist_level, classical_level = classify_algorithm("SHA-384")
    assert primitive == CryptoPrimitive.HASH
    assert nist_level == 2
    assert classical_level == 192


def test_sha256_level0():
    primitive, nist_level, classical_level = classify_algorithm("SHA-256")
    assert primitive == CryptoPrimitive.HASH
    assert nist_level == 0
    assert classical_level == 128


def test_sha1_level0():
    primitive, nist_level, classical_level = classify_algorithm("SHA-1")
    assert primitive == CryptoPrimitive.HASH
    assert nist_level == 0
    assert classical_level == 80


def test_3des_block_cipher():
    primitive, nist_level, classical_level = classify_algorithm("3DES")
    assert primitive == CryptoPrimitive.BLOCK_CIPHER
    assert nist_level == 0
    assert classical_level == 112


# ---------------------------------------------------------------------------
# PQC (quantum-safe)
# ---------------------------------------------------------------------------

def test_ml_kem_768_level3():
    primitive, nist_level, classical_level = classify_algorithm("ML-KEM-768")
    assert primitive == CryptoPrimitive.KEM
    assert nist_level == 3
    assert classical_level == 192


def test_ml_kem_1024_level5():
    primitive, nist_level, classical_level = classify_algorithm("ML-KEM-1024")
    assert primitive == CryptoPrimitive.KEM
    assert nist_level == 5
    assert classical_level == 256


def test_ml_dsa_65_level3():
    primitive, nist_level, classical_level = classify_algorithm("ML-DSA-65")
    assert primitive == CryptoPrimitive.SIGNATURE
    assert nist_level == 3
    assert classical_level == 192


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_unknown_algorithm_returns_unknown():
    primitive, nist_level, classical_level = classify_algorithm("TOTALLY-UNKNOWN-ALG")
    assert primitive == CryptoPrimitive.UNKNOWN
    assert nist_level is None
    assert classical_level is None


def test_case_insensitive():
    lower = classify_algorithm("aes-256-gcm")
    upper = classify_algorithm("AES-256-GCM")
    assert lower == upper


def test_ssh_enc_aes128_ctr():
    primitive, nist_level, classical_level = classify_algorithm("aes128-ctr")
    assert primitive == CryptoPrimitive.BLOCK_CIPHER
    assert nist_level == 1
    assert classical_level == 128


def test_ssh_mac_hmac_sha2_256():
    primitive, nist_level, classical_level = classify_algorithm("hmac-sha2-256")
    assert primitive == CryptoPrimitive.HASH
    assert nist_level == 0
    assert classical_level == 128


# ---------------------------------------------------------------------------
# QuantumSafety enum / quantum_safety_label helper
# ---------------------------------------------------------------------------

def test_quantum_safety_enum():
    assert quantum_safety_label(0) == "quantum-vulnerable"
    assert quantum_safety_label(1) == "quantum-safe"
    assert quantum_safety_label(3) == "quantum-safe"
    assert quantum_safety_label(5) == "quantum-safe"
    assert quantum_safety_label(None) == "unknown"
