"""Truth table for the shared JWK key-material helper (Phase 238 D-02 rule 2).

These tests describe the JWK a scanned TARGET publishes: a published JWKS
entry that carries a private or symmetric member exposes key material.
"""
from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "jwk,expected",
    [
        ({"kty": "oct", "k": "abc"}, True),
        ({"kty": "oct", "k": ""}, False),
        ({"kty": "RSA", "n": "x", "d": "y"}, True),
        ({"kty": "RSA", "n": "x"}, False),
        ({"secret_material_present": True}, True),
        ({"secret_material_present": False}, False),
        ("not-a-dict", False),
        (None, False),
    ],
)
def test_published_jwk_key_material_truth_table(jwk, expected):
    from quirk.util.jwt_alg import jwk_has_secret_material

    assert jwk_has_secret_material(jwk) is expected


@pytest.mark.parametrize("member", ["k", "d", "p", "q", "dp", "dq", "qi", "oth"])
def test_jwk_with_private_member_is_key_material(member):
    from quirk.util.jwt_alg import jwk_has_secret_material

    assert jwk_has_secret_material({"kty": "RSA", member: "v"}) is True


def test_jwk_secret_members_constant_is_exact():
    from quirk.util.jwt_alg import JWK_SECRET_MEMBERS

    assert JWK_SECRET_MEMBERS == frozenset({"k", "d", "p", "q", "dp", "dq", "qi", "oth"})
    assert len(JWK_SECRET_MEMBERS) == 8


def test_jwk_secret_marker_constant_is_exact():
    from quirk.util.jwt_alg import JWK_SECRET_MARKER

    assert JWK_SECRET_MARKER == "secret_material_present"
