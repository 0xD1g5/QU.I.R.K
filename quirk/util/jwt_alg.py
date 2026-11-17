"""Shared unsigned-JWT predicate — Phase 230 / DETECT-05.

Decision enforcement:
  - D-14: One rule for "this JWT is unsigned", shared by ``quirk analyze-token``
    and the scan-time bearer finding so the two surfaces cannot disagree.
  - T-94-01: ``alg`` matching is case-insensitive ("None", "NONE" are unsigned).
  - WR-05: a JWT header with NO ``alg`` is as forgeable as ``alg:none``.

Public surface:
  is_unsigned_jwt_alg(alg: str | None) -> bool
  BEARER_ALG_ABSENT_MARKER: str   # service_detail marker for a missing alg
  JWK_SECRET_MEMBERS: frozenset   # JWK members that carry private/symmetric key material
  JWK_SECRET_MARKER: str          # boolean flag naming key material was present
  jwk_has_secret_material(jwk) -> bool   # Phase 238 D-02 rule 2
  JWK_PUBLIC_MEMBERS: frozenset  # JWK members the JWT scan record keeps
  public_jwk_record(jwk) -> dict          # Phase 238 D-03 / WR-04
"""
from __future__ import annotations

from typing import Optional

BEARER_ALG_ABSENT_MARKER = "alg header absent"


def is_unsigned_jwt_alg(alg: Optional[str]) -> bool:
    """True when the declared alg is ``none`` (any case) or absent/empty."""
    return not alg or str(alg).lower() == "none"


JWK_SECRET_MEMBERS: frozenset = frozenset(
    {"k", "d", "p", "q", "dp", "dq", "qi", "oth"}
)
JWK_SECRET_MARKER = "secret_material_present"


def jwk_has_secret_material(jwk) -> bool:
    """True when a JWK carries private or symmetric key material
    (Phase 238 D-02 rule 2).

    False unless *jwk* is a dict. True when the dict sets
    ``JWK_SECRET_MARKER`` to exactly ``True``, or when any member in
    ``JWK_SECRET_MEMBERS`` has a truthy value (an empty string is not key
    material).
    """
    if not isinstance(jwk, dict):
        return False
    if jwk.get(JWK_SECRET_MARKER) is True:
        return True
    return any(jwk.get(member) for member in JWK_SECRET_MEMBERS)


# Phase 238 D-03 / WR-04: the public JWK members (RFC 7517 / RFC 7518) the JWT
# scan record keeps. An allowlist, so nested and non-standard members never
# reach the record.
JWK_PUBLIC_MEMBERS: frozenset = frozenset(
    {"kty", "kid", "use", "key_ops", "alg", "crv", "n", "e", "x", "y",
     "x5t", "x5t#S256", "x5u"}
)


def public_jwk_record(jwk) -> dict:
    """The JWT scan record for one JWK: public key metadata only.

    Keeps members in ``JWK_PUBLIC_MEMBERS`` whose value is a scalar (str, int,
    float or bool); ``key_ops`` keeps only its string items. Adds
    ``JWK_SECRET_MARKER`` (``jwk_has_secret_material``'s member test). Returns
    a record holding only the marker when *jwk* is not a dict.
    """
    record: dict = {}
    if isinstance(jwk, dict):
        for member in sorted(JWK_PUBLIC_MEMBERS):
            if member not in jwk:
                continue
            value = jwk[member]
            if member == "key_ops":
                if isinstance(value, list):
                    record[member] = [op for op in value if isinstance(op, str)]
            elif isinstance(value, (str, int, float, bool)):
                record[member] = value
    record[JWK_SECRET_MARKER] = isinstance(jwk, dict) and any(
        bool(jwk.get(m)) for m in JWK_SECRET_MEMBERS
    )
    return record
