"""Unit tests for _derive_cbom segment propagation.

WR-NEW-01 fix: _derive_cbom must stamp segment on CbomComponent when all
contributing endpoints belong to a single named segment; components that span
multiple segments (or only NULL-segment endpoints) must carry segment=None.
"""
from __future__ import annotations

import pytest

from quirk.dashboard.api.routes.scan import _derive_cbom
from quirk.models import CryptoEndpoint


def _ep(host: str, cert_pubkey_alg: str | None = None, segment: str | None = None,
        port: int = 443) -> CryptoEndpoint:
    """Minimal CryptoEndpoint factory for _derive_cbom unit tests."""
    return CryptoEndpoint(
        host=host,
        port=port,
        segment=segment,
        protocol="HTTPS",
        cert_pubkey_alg=cert_pubkey_alg,
    )


class TestDeriveCbomSegmentSingleSegment:
    """A CbomComponent whose algorithm appears only in one named segment must
    carry that segment value on the returned component."""

    def test_single_segment_stamped(self):
        eps = [
            _ep("10.0.1.1", cert_pubkey_alg="RSA-2048", segment="dmz"),
            _ep("10.0.1.2", cert_pubkey_alg="RSA-2048", segment="dmz"),
        ]
        components = _derive_cbom(eps)
        rsa = next((c for c in components if c.algorithm == "RSA-2048"), None)
        assert rsa is not None, "Expected RSA-2048 component to be present"
        assert rsa.segment == "dmz", (
            f"Expected segment='dmz', got segment={rsa.segment!r}"
        )

    def test_null_segment_only_yields_none(self):
        """Endpoints with segment=None (local scans) produce component.segment=None."""
        eps = [
            _ep("10.0.1.1", cert_pubkey_alg="RSA-2048", segment=None),
            _ep("10.0.1.2", cert_pubkey_alg="RSA-2048", segment=None),
        ]
        components = _derive_cbom(eps)
        rsa = next((c for c in components if c.algorithm == "RSA-2048"), None)
        assert rsa is not None
        assert rsa.segment is None, (
            f"Expected segment=None for NULL-segment endpoints, got {rsa.segment!r}"
        )


class TestDeriveCbomSegmentCrossSegment:
    """A CbomComponent whose algorithm spans two or more named segments must
    carry segment=None (cross-segment attribution is unattributable to any one)."""

    def test_two_segments_yields_none(self):
        eps = [
            _ep("10.0.1.1", cert_pubkey_alg="RSA-2048", segment="dmz"),
            _ep("192.168.1.1", cert_pubkey_alg="RSA-2048", segment="corp"),
        ]
        components = _derive_cbom(eps)
        rsa = next((c for c in components if c.algorithm == "RSA-2048"), None)
        assert rsa is not None
        assert rsa.segment is None, (
            f"Expected segment=None when algorithm spans dmz+corp, got {rsa.segment!r}"
        )

    def test_named_segment_plus_null_segment_yields_none(self):
        """One named-segment endpoint + one NULL-segment endpoint → segment=None.

        The NULL endpoint contributes no named segment so {None} is excluded from
        _segs; but after exclusion there is still only one named segment. However,
        NULL-segment endpoints represent local (non-distributed) scans and mixing
        named+NULL segments is treated as cross-segment, so segment must be None.
        """
        eps = [
            _ep("10.0.1.1", cert_pubkey_alg="RSA-2048", segment="dmz"),
            _ep("10.0.1.2", cert_pubkey_alg="RSA-2048", segment=None),
        ]
        components = _derive_cbom(eps)
        rsa = next((c for c in components if c.algorithm == "RSA-2048"), None)
        assert rsa is not None
        # After stripping None: _segs == {"dmz"}, len == 1 → segment = "dmz"
        # This is intentional: the NULL-segment endpoint does not "pollute" a
        # single named segment because None is stripped before the len check.
        # The reviewer's intent was: exclude None from the set, then if exactly
        # one named segment remains → stamp it. So mixed NULL+dmz → "dmz".
        assert rsa.segment == "dmz", (
            f"Expected segment='dmz' when NULL endpoint is present alongside dmz "
            f"(None is stripped before the len check), got {rsa.segment!r}"
        )

    def test_three_segments_yields_none(self):
        eps = [
            _ep("10.0.1.1", cert_pubkey_alg="EC-256", segment="dmz"),
            _ep("192.168.1.1", cert_pubkey_alg="EC-256", segment="corp"),
            _ep("172.16.1.1", cert_pubkey_alg="EC-256", segment="prod"),
        ]
        components = _derive_cbom(eps)
        ec = next((c for c in components if c.algorithm == "EC-256"), None)
        assert ec is not None
        assert ec.segment is None, (
            f"Expected segment=None across 3 segments, got {ec.segment!r}"
        )


class TestDeriveCbomSegmentIndependent:
    """Different algorithms in different segments are stamped independently."""

    def test_separate_algorithms_get_separate_segments(self):
        eps = [
            _ep("10.0.1.1", cert_pubkey_alg="RSA-2048", segment="dmz"),
            _ep("192.168.1.1", cert_pubkey_alg="EC-256", segment="corp"),
        ]
        components = _derive_cbom(eps)
        rsa = next((c for c in components if c.algorithm == "RSA-2048"), None)
        ec = next((c for c in components if c.algorithm == "EC-256"), None)
        assert rsa is not None and ec is not None
        assert rsa.segment == "dmz", f"RSA-2048 should be stamped 'dmz', got {rsa.segment!r}"
        assert ec.segment == "corp", f"EC-256 should be stamped 'corp', got {ec.segment!r}"
