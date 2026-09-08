"""Phase 191 (SPKI-02): read-time key-reuse derivation.

Key reuse — two or more TLS endpoints presenting the same public key
(the same SPKI SHA-256 fingerprint) — is derived HERE, at read time, by a
``GROUP BY cert_spki_fingerprint HAVING COUNT(*) >= 2`` aggregate query.
There is no denormalized ``is_shared_key`` boolean column and no stored
``key_reuse_clusters`` table anywhere in this codebase (D-03, ROADMAP
success criterion 2) — the persisted fingerprint on ``CryptoEndpoint`` is
the only source of truth, and this module derives clusters from it fresh
on every call rather than caching a second copy that could drift.

Mirroring ``quirk/intelligence/burndown.py``'s conventions:

- All three top-level return keys (``clusters``, ``fingerprinted``,
  ``total``) are ALWAYS present, never sparse, even when there is zero
  reuse (D-06/D-12 honest-absence support) — a caller can distinguish
  "no shared keys were found" from "this data was never computed".
- Clusters are ordered by ``member_count`` descending, biggest
  remediation-leverage cluster first (D-04), with a stable fingerprint
  ascending tiebreaker so output is deterministic across runs.
- Endpoints with a NULL ``cert_spki_fingerprint`` are excluded from
  reuse analysis entirely (D-12) — they never appear in a cluster and
  never form a cluster of their own, no matter how many share NULL.
- This module is READ-ONLY: it never writes, never commits, and is never
  called from the scan pipeline — only from the report loader (191-04).
- This module never imports the quantum-readiness weighting module and the
  data it returns never reaches the quantum-readiness score (D-02) —
  enforced permanently by ``tests/test_key_reuse_score_guard.py``. The
  return shape deliberately carries no top-level ``severity``, ``host``,
  or ``port`` key, which is what structurally keeps it out of
  ``_build_finding()``'s findings chokepoint even via an indirect path.
"""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import func

from quirk.models import CryptoEndpoint


def compute_key_reuse_clusters(session: Any) -> dict:
    """Derive key-reuse clusters from persisted SPKI fingerprints.

    Returns, with ALL THREE keys ALWAYS present (never sparse):
        {
            "clusters": [...],    # ordered by member_count DESC (D-04),
                                   # fingerprint ASC tiebreaker; [] when
                                   # no reuse exists
            "fingerprinted": int, # TLS endpoints with a non-NULL fingerprint
            "total": int,         # TLS endpoints in total
        }

    Each cluster element:
        {
            "fingerprint": str,        # full 64-char hex digest
            "member_count": int,       # >= 2
            "cert_subject": str | None,
            "cert_pubkey_alg": str | None,
            "cert_pubkey_size": int | None,
            "members": [{"host": str, "port": int}, ...],
        }

    Read-only: this function persists nothing and performs no writes.
    """
    total = (
        session.query(func.count(CryptoEndpoint.id))
        .filter(CryptoEndpoint.protocol == "TLS")
        .scalar()
        or 0
    )
    fingerprinted = (
        session.query(func.count(CryptoEndpoint.id))
        .filter(
            CryptoEndpoint.protocol == "TLS",
            CryptoEndpoint.cert_spki_fingerprint.isnot(None),
        )
        .scalar()
        or 0
    )

    dupe_fingerprints = (
        session.query(
            CryptoEndpoint.cert_spki_fingerprint,
            func.count(CryptoEndpoint.id).label("member_count"),
        )
        .filter(
            CryptoEndpoint.protocol == "TLS",
            CryptoEndpoint.cert_spki_fingerprint.isnot(None),  # D-12: exclude NULL
        )
        .group_by(CryptoEndpoint.cert_spki_fingerprint)
        .having(func.count(CryptoEndpoint.id) >= 2)
        .order_by(
            func.count(CryptoEndpoint.id).desc(),  # D-04: biggest leverage first
            CryptoEndpoint.cert_spki_fingerprint.asc(),  # deterministic tiebreaker
        )
        .all()
    )

    clusters = []
    for fingerprint, member_count in dupe_fingerprints:
        members = (
            session.query(CryptoEndpoint)
            .filter(
                CryptoEndpoint.protocol == "TLS",
                CryptoEndpoint.cert_spki_fingerprint == fingerprint,
            )
            .order_by(CryptoEndpoint.host.asc(), CryptoEndpoint.port.asc())
            .all()
        )
        identity = members[0]
        clusters.append(
            {
                "fingerprint": fingerprint,
                "member_count": member_count,
                "cert_subject": identity.cert_subject,
                "cert_pubkey_alg": identity.cert_pubkey_alg,
                "cert_pubkey_size": identity.cert_pubkey_size,
                "members": [{"host": m.host, "port": m.port} for m in members],
            }
        )

    result: Dict[str, Any] = {
        "clusters": clusters,
        "fingerprinted": fingerprinted,
        "total": total,
    }
    return result
