"""IDENT-01 fingerprint stability + T-178-01 collision guards (Phase 178 Plan 01).

`TicketingChannel.compute_fingerprint` (quirk/ticketing/base.py) computes
SHA256(f"{host}:{port}::{title}"). Its docstring claims "stable across
re-scans (TICKET-03)" — a claim this test file falsifies for the cert-expiry
title interpolated at `quirk/dashboard/api/routes/scan.py:200`
(`f"Certificate expiring in {days_to_expiry} day(s)"`). Because
`days_to_expiry` changes by 1 every day, the fingerprint mints a brand-new
ticket daily instead of tracking one finding across re-scans.

This file has two jobs, deliberately asymmetric (see 178-CONTEXT.md /
178-01-PLAN.md rationale):

  1. `test_cert_expiry_fingerprint_stable_across_day_boundary` — proves the
     defect exists. Marked strict-xfail (see decorator below) because it is
     RED today and is EXPECTED to stay RED until Plan 178-04 lands the
     normalizer fix. A strict xfail means an unexpected pass fails the suite
     loudly, forcing the marker's removal in Plan 04 rather than letting it
     rot green.

  2. The T-178-01 collision guards below — proof that the eventual fix does
     NOT over-normalize. Over-normalizing two DIFFERENT vulnerable container
     crypto libraries at the same host:port down to one fingerprint would
     silently merge two distinct findings; the second library would never
     get its own ticket (dispatch_finding's dedup branch would treat it as
     a rediscovery of the first). This loss is unrecoverable, unlike the
     day-boundary defect's mere duplicate-ticket annoyance — the asymmetry
     is why these guards exist and must never regress.

Guarded interpolation sites (verified this session):
  - quirk/dashboard/api/routes/scan.py:200
    -> f"Certificate expiring in {days_to_expiry} day(s)"
  - quirk/engine/findings_evaluator.py:181
    -> f"Container image uses quantum-vulnerable crypto library ({name}@{version})"
"""
from __future__ import annotations

import pytest

from quirk.ticketing.base import TicketingChannel


def _finding(title: str, host: str = "10.0.0.1", port: int = 443) -> dict:
    """Minimal finding dict — compute_fingerprint reads only host/port/title."""
    return {"host": host, "port": port, "title": title}


# ---------------------------------------------------------------------------
# Day-boundary stability guard (IDENT-01) — RED today, GREEN after Plan 04
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "IDENT-01 RED: compute_fingerprint does not yet normalize the "
        "volatile days_to_expiry segment; Plan 178-04 removes this marker"
    ),
    strict=True,
)
def test_cert_expiry_fingerprint_stable_across_day_boundary():
    """Same cert, day 30 vs day 29, MUST yield the same fingerprint.

    Today compute_fingerprint hashes the full interpolated title verbatim,
    so "...30 day(s)" and "...29 day(s)" hash to different digests. This
    means every daily re-scan mints a fresh Jira/ServiceNow ticket for the
    same underlying finding instead of recognizing it as a rediscovery.
    """
    title_30 = "Certificate expiring in 30 day(s)"
    title_29 = "Certificate expiring in 29 day(s)"
    finding_30 = _finding(title_30)
    finding_29 = _finding(title_29)

    fp_30 = TicketingChannel.compute_fingerprint(finding_30)
    fp_29 = TicketingChannel.compute_fingerprint(finding_29)

    assert fp_30 == fp_29, (
        f"Fingerprint changed across a day boundary for the same certificate: "
        f"title={title_30!r} -> {fp_30}, title={title_29!r} -> {fp_29}. "
        f"This mints a new ticket every day instead of tracking one finding "
        f"across re-scans (IDENT-01)."
    )


def test_cert_expiry_fingerprint_differs_across_hosts():
    """Counterweight: identical title, different host, MUST differ.

    Stops the eventual fix from degenerating into "normalize everything to
    a constant" — host is a genuine discriminator and must survive
    normalization of the volatile days_to_expiry segment.
    """
    title = "Certificate expiring in 30 day(s)"
    finding_a = _finding(title, host="10.0.0.1")
    finding_b = _finding(title, host="10.0.0.2")

    fp_a = TicketingChannel.compute_fingerprint(finding_a)
    fp_b = TicketingChannel.compute_fingerprint(finding_b)

    assert fp_a != fp_b, (
        f"Two DIFFERENT hosts (10.0.0.1 vs 10.0.0.2) with the same cert-expiry "
        f"title collided into one fingerprint ({fp_a}). Host is a genuine "
        f"identity discriminator and must not be normalized away."
    )
