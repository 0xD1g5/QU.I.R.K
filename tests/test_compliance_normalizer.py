"""Phase 178 IDENT-01 (Plan 178-04): the single normalize_finding_title.

Proves the ONE normalizer function behaves identically to the prior
compliance-only implementation for the COMPLIANCE policy table, AND
diverges correctly from it for the IDENTITY policy table on the two
_IDENTITY_BEARING_PREFIXES titles (T-178-01) and the one new cert-expiry
entry (the demonstrated daily-churn defect this plan fixes).
"""
from __future__ import annotations

from quirk.compliance import (
    FINGERPRINT_TITLE_ALIASES,
    TITLE_IDENTITY_CLASS,
    TITLE_PREFIX_ALIASES,
    normalize_finding_title,
)


def test_default_table_matches_compliance_behavior():
    assert (
        normalize_finding_title("Outdated libgcrypt (1.8.5) in container image")
        == "Outdated libgcrypt in container image"
    )


def test_no_matching_prefix_returns_verbatim():
    title = "Plaintext HTTP service detected"
    assert normalize_finding_title(title) == title


def test_cert_expiry_normalizes_to_stable_title_under_fingerprint_policy():
    a = normalize_finding_title(
        "Certificate expiring in 30 day(s)", FINGERPRINT_TITLE_ALIASES
    )
    b = normalize_finding_title(
        "Certificate expiring in 29 day(s)", FINGERPRINT_TITLE_ALIASES
    )
    assert a == b == "Certificate expiring soon"


def test_identity_bearing_container_title_preserved_under_fingerprint_policy():
    title = (
        "Container image uses quantum-vulnerable crypto library "
        "(libssl1.1@1.1.1w)"
    )
    assert normalize_finding_title(title, FINGERPRINT_TITLE_ALIASES) == title


def test_same_identity_bearing_title_still_collapses_under_compliance_policy():
    title = (
        "Container image uses quantum-vulnerable crypto library "
        "(libssl1.1@1.1.1w)"
    )
    assert (
        normalize_finding_title(title)
        == "Container image uses quantum-vulnerable crypto library"
    )


def test_title_identity_class_is_exhaustive_and_closed_vocabulary():
    # 23 since 2026-09-14: "Weak SAML encryption certificate: -" was added
    # alongside the pre-existing signing title, because a SAML IdP publishes a
    # KeyDescriptor per USE and the encryption row was being mis-titled
    # "signing".
    #
    # NOTE: this literal is a tripwire, not the real exhaustiveness check —
    # `tests/test_compliance_title_join.py::test_every_interpolated_title_is_classified`
    # is, and it regenerates its occurrence set from the source AST on every run
    # (in both directions: unclassified AND stale). Bumping this number without
    # that gate passing proves nothing.
    assert len(TITLE_IDENTITY_CLASS) == 23
    assert set(TITLE_IDENTITY_CLASS.values()) <= {
        "NORMALIZE",
        "PRESERVE_IDENTITY",
        "NOT_IDENTITY_RELEVANT",
    }


def test_fingerprint_table_derived_size():
    # 7 compliance entries - 2 identity-bearing prefixes + 1 new cert entry = 6.
    assert len(FINGERPRINT_TITLE_ALIASES) == 6
    assert len(TITLE_PREFIX_ALIASES) == 7
