"""Shared TLS-row predicates — Phase 228 D-05, Phase 238 D-14 / WR-07.

One implementation for the report evaluator
(``quirk.engine.findings_evaluator``), the dashboard deriver
(``quirk.dashboard.api.finding_derivation``) and closure
(``quirk.intelligence.closure``), so a row shape that gets findings is also a
row shape that can close them. No inline copies at any call site.

Public surface:
  runs_tls_certificate_checks(ep) -> bool   # Phase 228 D-05
  mtls_required_variant(ep) -> str | None   # Phase 238 D-14
  is_observed_mtls(ep) -> bool              # Phase 238 WR-07
"""
from __future__ import annotations

from typing import Any, Optional

MTLS_REQUIRED = "MTLS_REQUIRED"


def runs_tls_certificate_checks(ep: Any) -> bool:
    """True when ``ep`` is a row that gets TLS/certificate checks (Phase 228 D-05).

    Exact-case ``== "TLS"`` on purpose: a case-variant protocol from a sensor
    import must not widen the checks, and the report stays byte-identical.
    Both pipelines must call this, never an inline ``== "TLS"`` copy.
    """
    return getattr(ep, "protocol", None) == "TLS"


def _scan_error_category(ep: Any) -> str:
    desc = getattr(ep, "scan_error", "") or ""
    if ":" in desc:
        return desc.split(":", 1)[0].strip()
    return desc.strip()


def is_observed_mtls(ep: Any) -> bool:
    """True for the post-handshake mTLS shape (Phase 238 D-14 / WR-07).

    The handshake completed and the server then rejected the client, so the
    row is a TLS row with ``tls_blocker_reason == "MTLS_REQUIRED"`` and no
    ``scan_error`` (``None`` or ``""``). Its observed fields are assessed and
    its findings can close. ``tls_version`` is not required: the evaluator
    assesses such a row either way, so closure must too.
    """
    return (
        runs_tls_certificate_checks(ep)
        and not getattr(ep, "scan_error", None)
        and getattr(ep, "tls_blocker_reason", None) == MTLS_REQUIRED
    )


def mtls_required_variant(ep: Any) -> Optional[str]:
    """Which stored mTLS shape ``ep`` is, or None (Phase 238 D-14).

    ``"handshake"``: the handshake failed for lack of a client certificate,
    so ``scan_error`` carries the ``MTLS_REQUIRED`` category and nothing was
    observed. ``"post_handshake"``: ``is_observed_mtls(ep)``; the observed
    fields are kept. Both pipelines call this, never an inline copy.
    """
    if not runs_tls_certificate_checks(ep):
        return None
    if _scan_error_category(ep) == MTLS_REQUIRED:
        return "handshake"
    if is_observed_mtls(ep):
        return "post_handshake"
    return None
