"""
Tests for the cert_pubkey_alg fix in qcscan.reports.writer._extract_cert_key_type.

These tests verify that _extract_cert_key_type checks cert_pubkey_alg
(the canonical CryptoEndpoint field) FIRST, before any fallback attributes.

RED phase: tests fail until writer.py is fixed.
"""
import types
import unittest

from qcscan.reports.writer import _extract_cert_key_type


class CertPubkeyAlgExtractionTests(unittest.TestCase):
    def test_cert_pubkey_alg_found(self) -> None:
        """cert_pubkey_alg='RSA' should be returned as 'RSA'."""
        ep = types.SimpleNamespace(cert_pubkey_alg="RSA")
        result = _extract_cert_key_type(ep)
        self.assertEqual(result, "RSA")

    def test_cert_pubkey_alg_preferred_over_fallbacks(self) -> None:
        """cert_pubkey_alg must win over cert_key_type when both are present."""
        ep = types.SimpleNamespace(cert_pubkey_alg="ECDSA", cert_key_type="RSA")
        result = _extract_cert_key_type(ep)
        self.assertEqual(
            result,
            "ECDSA",
            "cert_pubkey_alg is the canonical field; it must take priority over cert_key_type",
        )

    def test_cert_pubkey_alg_none_falls_through(self) -> None:
        """When cert_pubkey_alg is None, fall back to cert_key_type."""
        ep = types.SimpleNamespace(cert_pubkey_alg=None, cert_key_type="RSA")
        result = _extract_cert_key_type(ep)
        self.assertEqual(result, "RSA")

    def test_cert_pubkey_alg_empty_string_falls_through(self) -> None:
        """When cert_pubkey_alg is empty string, fall back to cert_key_type."""
        ep = types.SimpleNamespace(cert_pubkey_alg="", cert_key_type="ECDSA")
        result = _extract_cert_key_type(ep)
        self.assertEqual(result, "ECDSA")

    def test_no_cert_attrs_returns_none(self) -> None:
        """Endpoint with no cert attributes should return None."""
        ep = types.SimpleNamespace()
        result = _extract_cert_key_type(ep)
        self.assertIsNone(result)

    def test_cert_pubkey_alg_lowercase_normalized_to_upper(self) -> None:
        """cert_pubkey_alg value should be uppercased in the output."""
        ep = types.SimpleNamespace(cert_pubkey_alg="rsa")
        result = _extract_cert_key_type(ep)
        self.assertEqual(result, "RSA")


if __name__ == "__main__":
    unittest.main()
