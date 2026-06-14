"""RED contract tests for AUDIT-05: SOURCE algo-hint granularity in CBOM builder.

AUDIT-05 success criterion: ``_extract_algo_from_rule_id`` in quirk/cbom/builder.py
must return granular algorithm strings for RSA and AES variants:
  - rsa-1024  -> "RSA-1024"
  - rsa-2048  -> "RSA-2048"
  - rsa-4096  -> "RSA-4096"
  - aes-128   -> "AES-128"
  - aes-192   -> "AES-192"
  - aes-256   -> "AES-256"

Currently the function returns the coarse canonical "RSA" for all RSA variants and
"AES-256" / "AES-128" only when those exact strings appear (not "rsa-1024" etc.).
The CBOM SOURCE path must surface distinct algorithmRef values so AES-256-GCM and
AES-128-CBC map to different components rather than collapsing to "AES".

These tests FAIL against the current codebase (v5.7) because:
- rsa-1024 / rsa-2048 / rsa-4096 all map to the coarse "RSA" (no size suffix).
- aes-192 has no mapping at all.
- A multi-finding fixture would collapse to fewer distinct algorithmRef values.

Wave 2 Plan 130-03 makes them pass.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from quirk.cbom.builder import _extract_algo_from_rule_id


# ---------------------------------------------------------------------------
# Granular RSA hint assertions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rule_id, expected", [
    ("python.cryptography.rsa-1024-key-size", "RSA-1024"),
    ("java.security.rsa-2048-short-key", "RSA-2048"),
    ("crypto.rsa-4096-use", "RSA-4096"),
])
def test_rsa_size_variants_map_to_distinct_hints(rule_id: str, expected: str) -> None:
    """RSA key-size variants must map to distinct granular hints (AUDIT-05)."""
    result = _extract_algo_from_rule_id(rule_id)
    assert result == expected, (
        f"_extract_algo_from_rule_id({rule_id!r}) returned {result!r}, "
        f"expected {expected!r}. AUDIT-05 requires RSA size variants to be distinct."
    )


# ---------------------------------------------------------------------------
# Granular AES hint assertions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rule_id, expected", [
    ("python.cryptography.insecure-aes-128-cbc", "AES-128"),
    ("crypto.aes-192-ecb-usage", "AES-192"),
    ("java.security.aes-256-gcm-key", "AES-256"),
])
def test_aes_size_variants_map_to_distinct_hints(rule_id: str, expected: str) -> None:
    """AES key-size variants must map to distinct granular hints (AUDIT-05)."""
    result = _extract_algo_from_rule_id(rule_id)
    assert result == expected, (
        f"_extract_algo_from_rule_id({rule_id!r}) returned {result!r}, "
        f"expected {expected!r}. AUDIT-05 requires AES size variants to be distinct."
    )


# ---------------------------------------------------------------------------
# Multi-finding fixture: three findings must produce THREE distinct algorithmRef values
# ---------------------------------------------------------------------------

def test_source_scan_fixture_yields_three_distinct_algorithmrefs() -> None:
    """AES-256-GCM, AES-128-CBC, RSA-2048 must produce three DISTINCT algorithmRef values (AUDIT-05).

    Simulates a SOURCE-scan run that surfaces three semgrep findings, each with a
    distinct rule_id fragment. The builder must not collapse them to the same hint.
    """
    # Simulate three source-scan endpoints as the CBOM builder would receive them
    rule_ids = [
        "python.cryptography.insecure-aes-256-gcm",   # -> "AES-256"
        "python.cryptography.insecure-aes-128-cbc",   # -> "AES-128"
        "python.cryptography.rsa-2048-short-key",      # -> "RSA-2048"
    ]

    hints = [_extract_algo_from_rule_id(r) for r in rule_ids]

    # All three must be non-None
    for rule_id, hint in zip(rule_ids, hints):
        assert hint is not None, (
            f"_extract_algo_from_rule_id({rule_id!r}) returned None — "
            f"no mapping found for this rule_id."
        )

    # All three must be distinct
    assert len(set(hints)) == 3, (
        f"Three distinct rule IDs produced only {len(set(hints))} distinct hints: {hints!r}. "
        f"AUDIT-05 requires AES-256-GCM / AES-128-CBC / RSA-2048 to map to three DISTINCT "
        f"algorithmRef values in the CBOM — currently they collapse."
    )


# ---------------------------------------------------------------------------
# Regression guard: non-AES/non-RSA entries map to existing canonical values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rule_id, expected", [
    ("crypto-md5-usage",    "MD5"),
    ("crypto-sha1-usage",   "SHA-1"),
    ("crypto-sha-1-usage",  "SHA-1"),
    ("crypto-3des-usage",   "3DES"),
    ("crypto-des-usage",    "DES"),
    ("crypto-rc4-usage",    "RC4"),
    ("use-of-aes",          "AES"),   # bare "aes" with no size suffix -> coarse "AES" preserved
    ("rsa-key-too-short",   "RSA"),   # bare "rsa" with no size suffix -> coarse "RSA" preserved
])
def test_non_aes_non_rsa_regression(rule_id: str, expected: str) -> None:
    """Non-AES/non-RSA entries (MD5, SHA-1, 3DES, DES, RC4) still map to canonical values (AUDIT-05 regression guard)."""
    result = _extract_algo_from_rule_id(rule_id)
    assert result == expected, (
        f"Regression: _extract_algo_from_rule_id({rule_id!r}) = {result!r}, "
        f"expected {expected!r}. AUDIT-05 must not break existing mappings."
    )
