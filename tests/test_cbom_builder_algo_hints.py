"""Regression tests for _extract_algo_from_rule_id algo-hint mapping (CR-03).

Verifies that:
- "des" maps to "DES" (not "3DES")
- "3des" still maps to "3DES" (and is matched before "des")
- "aes-256-cbc" maps to "AES-256"
- "aes-128-cipher" maps to "AES-128"
- "use-of-aes" maps to "AES" (generic catch-all)
- "rsa-key-too-short" maps to "RSA" (unchanged regression)
"""
import pytest

from quirk.cbom.builder import _extract_algo_from_rule_id


@pytest.mark.parametrize(
    "rule_id, expected",
    [
        ("crypto-des-usage", "DES"),
        ("crypto-3des-usage", "3DES"),
        ("java.lang.security.aes-256-cbc", "AES-256"),
        ("weak-aes-128-cipher", "AES-128"),
        ("use-of-aes", "AES"),
        ("rsa-key-too-short", "RSA"),
    ],
)
def test_extract_algo_from_rule_id(rule_id: str, expected: str) -> None:
    """Each rule_id fragment maps to its canonical algorithm name."""
    assert _extract_algo_from_rule_id(rule_id) == expected


def test_des_not_3des() -> None:
    """'crypto-des-usage' must return 'DES', not '3DES'."""
    result = _extract_algo_from_rule_id("crypto-des-usage")
    assert result == "DES", f"Expected 'DES', got {result!r}"


def test_3des_still_works() -> None:
    """'3des' rule IDs must still return '3DES' — 3DES is a real algorithm."""
    result = _extract_algo_from_rule_id("crypto-3des-usage")
    assert result == "3DES", f"Expected '3DES', got {result!r}"
