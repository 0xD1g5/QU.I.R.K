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
     defect is fixed. Was RED (strict-expected-failure) prior to Plan
     178-04; that marker has now been removed because `quirk.compliance.
     FINGERPRINT_TITLE_ALIASES` normalizes the volatile `days_to_expiry`
     segment out of the fingerprint (see compute_fingerprint's docstring).

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

from quirk.ticketing.base import TicketingChannel


def _finding(title: str, host: str = "10.0.0.1", port: int = 443) -> dict:
    """Minimal finding dict — compute_fingerprint reads only host/port/title."""
    return {"host": host, "port": port, "title": title}


# ---------------------------------------------------------------------------
# Day-boundary stability guard (IDENT-01) — RED today, GREEN after Plan 04
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# T-178-01 — collision guard
#
# The version-churn tradeoff below is a deliberate, documented position, not
# an oversight: {name} and {version} in the container-crypto-library title
# family cannot be separated by TITLE_PREFIX_ALIASES' prefix mechanism, so
# preserving both as discriminators (i.e. NOT normalizing {version} away)
# outranks suppressing version-bump churn. Under-normalizing here merely
# produces a duplicate ticket on a library upgrade, which is annoying but
# fully recoverable. Over-normalizing would merge two distinct libraries
# under one fingerprint and silently drop the second finding — unrecoverable.
# ---------------------------------------------------------------------------


def test_two_distinct_container_libraries_do_not_collide():
    """Two DIFFERENT vulnerable libraries at the same host:port MUST differ.

    GREEN today; must STAY green after Plan 178-04's normalizer change.
    """
    title_libssl = (
        "Container image uses quantum-vulnerable crypto library "
        "(libssl1.1@1.1.1w)"
    )
    title_libgcrypt = (
        "Container image uses quantum-vulnerable crypto library "
        "(libgcrypt20@1.8.5)"
    )
    finding_libssl = _finding(title_libssl, host="10.0.0.5", port=443)
    finding_libgcrypt = _finding(title_libgcrypt, host="10.0.0.5", port=443)

    fp_libssl = TicketingChannel.compute_fingerprint(finding_libssl)
    fp_libgcrypt = TicketingChannel.compute_fingerprint(finding_libgcrypt)

    assert fp_libssl != fp_libgcrypt, (
        f"Two distinct vulnerable libraries (libssl1.1 vs libgcrypt20) at the "
        f"same host:port collided into one fingerprint ({fp_libssl}). This "
        f"means dispatch_finding takes the add_rediscovery_comment branch and "
        f"the second library never gets its own ticket (T-178-01)."
    )


def test_same_library_different_version_may_share_or_differ_is_pinned():
    """Same library, different version, MUST differ — pinned position.

    {version} is deliberately NOT normalized away for the container-crypto-
    library family: {name} and {version} cannot be separated by the
    TITLE_PREFIX_ALIASES prefix mechanism, so preserving the version as a
    discriminator outranks suppressing daily/incidental version churn
    (T-178-01 over the day-boundary defect this file also guards).
    """
    title_old = (
        "Container image uses quantum-vulnerable crypto library "
        "(libssl1.1@1.1.1v)"
    )
    title_new = (
        "Container image uses quantum-vulnerable crypto library "
        "(libssl1.1@1.1.1w)"
    )
    finding_old = _finding(title_old, host="10.0.0.5", port=443)
    finding_new = _finding(title_new, host="10.0.0.5", port=443)

    fp_old = TicketingChannel.compute_fingerprint(finding_old)
    fp_new = TicketingChannel.compute_fingerprint(finding_new)

    assert fp_old != fp_new, (
        f"Same library (libssl1.1) at different versions (1.1.1v vs 1.1.1w) "
        f"collided into one fingerprint ({fp_old}). This is the PINNED "
        f"position (T-178-01): {{name}} and {{version}} cannot be separated "
        f"by TITLE_PREFIX_ALIASES' prefix mechanism, so version is preserved "
        f"as a discriminator rather than normalized away, even though this "
        f"means a version bump alone mints a new ticket."
    )


def test_generic_crypto_library_catchall_does_not_collide():
    """Same as the first collision test, for the generic catch-all title family.

    Guards `TITLE_PREFIX_ALIASES`' "Container image contains crypto library ("
    prefix — the second of the two container-crypto title families that must
    not be over-normalized by Plan 178-04.
    """
    title_openssl = "Container image contains crypto library (openssl@3.0.2)"
    title_libcrypto = "Container image contains crypto library (libcrypto@1.1.1)"
    finding_openssl = _finding(title_openssl, host="10.0.0.5", port=443)
    finding_libcrypto = _finding(title_libcrypto, host="10.0.0.5", port=443)

    fp_openssl = TicketingChannel.compute_fingerprint(finding_openssl)
    fp_libcrypto = TicketingChannel.compute_fingerprint(finding_libcrypto)

    assert fp_openssl != fp_libcrypto, (
        f"Two distinct libraries (openssl vs libcrypto) under the generic "
        f"'Container image contains crypto library (' title family collided "
        f"into one fingerprint ({fp_openssl}). This means the second library "
        f"never gets its own ticket (T-178-01)."
    )
