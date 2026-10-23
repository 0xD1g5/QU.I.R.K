"""Shared unsigned-JWT predicate — Phase 230 / DETECT-05.

Decision enforcement:
  - D-14: One rule for "this JWT is unsigned", shared by ``quirk analyze-token``
    and the scan-time bearer finding so the two surfaces cannot disagree.
  - T-94-01: ``alg`` matching is case-insensitive ("None", "NONE" are unsigned).
  - WR-05: a JWT header with NO ``alg`` is as forgeable as ``alg:none``.

Public surface:
  is_unsigned_jwt_alg(alg: str | None) -> bool
  BEARER_ALG_ABSENT_MARKER: str   # service_detail marker for a missing alg
"""
from __future__ import annotations

from typing import Optional

BEARER_ALG_ABSENT_MARKER = "alg header absent"


def is_unsigned_jwt_alg(alg: Optional[str]) -> bool:
    """True when the declared alg is ``none`` (any case) or absent/empty."""
    return not alg or str(alg).lower() == "none"
