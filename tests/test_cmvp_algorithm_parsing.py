"""RVW-022: CMVP certificate pages have two shapes; refusing to read one of
them must never look like "this module has no algorithms".

`quirk compliance cmvp refresh` used to look only for `table#fips-algo-table`.
Certificates that publish their algorithms as an "Approved Algorithms" field
instead parsed to `[]`, and that empty list was written straight into
`cmvp_cache.json` — silently deleting the compliance evidence behind a client
attestation, with no error raised anywhere.

Which shape a page uses varies PER CERTIFICATE, not per FIPS level: certs 4523
and 4884 are both FIPS 140-3 and only 4523 has the table. Verified against live
NIST pages on 2026-08-25.

These tests use inline HTML so they need no network.
"""
from __future__ import annotations

import pytest

from quirk.compliance.cmvp import (
    CMVPRefreshParseError,
    _cavp_label_to_family,
    _extract_algorithms,
)


def _soup(html: str):
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "lxml")


# Shape A — the table form (cell text is already a CAVP family name).
_TABLE_PAGE = """
<html><body>
<table id="fips-algo-table">
  <tr><td class="text-nowrap">AES</td><td>A1</td></tr>
  <tr><td class="text-nowrap">SHS</td><td>A2</td></tr>
  <tr><td class="text-nowrap">KTS</td><td>A3</td></tr>
</table>
</body></html>
"""

# Shape B — the "Approved Algorithms" field form (cells are variant names).
_APPROVED_FIELD_PAGE = """
<html><body>
<div class="row padrow">
  <div class="col-md-3">Approved Algorithms</div>
  <div class="col-md-9">
    <div class="row striped"><div class="col-md-12"><div class="row">
      <div class="col-md-3">AES-CBC</div><div class="col-md-4"><a href="#">A1908</a></div>
    </div></div></div>
    <div class="row striped"><div class="col-md-12"><div class="row">
      <div class="col-md-3">AES-GCM</div><div class="col-md-4"><a href="#">A1908</a></div>
    </div></div></div>
    <div class="row striped"><div class="col-md-12"><div class="row">
      <div class="col-md-3">Counter DRBG</div><div class="col-md-4"><a href="#">A1908</a></div>
    </div></div></div>
    <div class="row striped"><div class="col-md-12"><div class="row">
      <div class="col-md-3">SHA2-256</div><div class="col-md-4"><a href="#">A1908</a></div>
    </div></div></div>
  </div>
</div>
</body></html>
"""

# A page that publishes no algorithm data in either shape (observed live on
# cert 5263 — only a validation-history table and descriptive fields).
_NO_ALGORITHM_PAGE = """
<html><body>
<table id="validation-history-table"><tr><td>2024-01-01</td></tr></table>
<div class="row padrow">
  <div class="col-md-3">Module Name</div><div class="col-md-9">Some Module</div>
</div>
</body></html>
"""


class TestExtractAlgorithms:
    def test_table_shape_returns_families(self):
        families, strategy = _extract_algorithms(_soup(_TABLE_PAGE))
        assert strategy == "table"
        assert families == ["AES", "KTS", "SHS"]

    def test_approved_field_shape_is_read_not_skipped(self):
        """The shape the old parser could not see at all."""
        families, strategy = _extract_algorithms(_soup(_APPROVED_FIELD_PAGE))
        assert strategy == "approved-field"
        assert families, "RVW-022: the Approved Algorithms shape parsed to nothing"

    def test_approved_field_variants_are_folded_to_families(self):
        """coverage_for_algorithm() does an exact `family in algorithms` test,
        so storing variants like 'AES-CBC' would make every lookup miss."""
        families, _ = _extract_algorithms(_soup(_APPROVED_FIELD_PAGE))
        assert families == ["AES", "DRBG", "SHS"]
        assert "AES-CBC" not in families
        assert "SHA2-256" not in families

    def test_page_with_no_algorithm_data_reports_none_not_empty(self):
        """'none' is a parse failure signal, distinct from 'zero algorithms'."""
        families, strategy = _extract_algorithms(_soup(_NO_ALGORITHM_PAGE))
        assert strategy == "none"
        assert families == []


class TestFamilyFolding:
    @pytest.mark.parametrize(
        "label,expected",
        [
            ("AES-CBC", "AES"),
            ("AES-GCM", "AES"),
            ("HMAC-SHA2-256", "HMAC"),
            ("HMAC DRBG", "DRBG"),      # ordering: a DRBG, not an HMAC
            ("Counter DRBG", "DRBG"),
            ("ECDSA KeyGen (FIPS186-4)", "ECDSA"),
            ("RSA SigVer (FIPS186-4)", "RSA"),
            ("KAS-ECC Sp800-56Ar3", "KAS"),
            ("KTS-IFC", "KTS"),
            ("KDF SP800-108", "KBKDF"),  # ordering: before the generic KDF rule
            ("KDF SSH", "CVL"),
            ("SHA-1", "SHS"),
            ("SHA2-512", "SHS"),
            ("SHA3-256", "SHA-3"),
            ("Conditioning Component AES-CBC-MAC SP800-90B", "ENT"),
        ],
    )
    def test_known_labels_fold_correctly(self, label, expected):
        assert _cavp_label_to_family(label) == expected

    def test_unrecognised_label_is_dropped_not_guessed(self):
        """A wrong family silently changes which modules a client report claims
        cover an algorithm — worse than omitting one."""
        assert _cavp_label_to_family("Some Future Primitive v9") is None
        assert _cavp_label_to_family("") is None


class TestFetchCertDetailFailsClosed:
    def test_missing_algorithm_data_raises_rather_than_returning_empty(self):
        """The core RVW-022 contract: no silent empty algorithm list."""
        from quirk.compliance import cmvp

        class _Resp:
            text = _NO_ALGORITHM_PAGE

            def raise_for_status(self):
                return None

        class _Client:
            def get(self, *a, **k):
                return _Resp()

        with pytest.raises(CMVPRefreshParseError) as exc:
            cmvp._fetch_cert_detail(_Client(), "5263")
        assert "5263" in str(exc.value)

    def test_a_140_3_style_page_yields_a_non_empty_algorithm_list(self):
        """The review's named regression: a known 140-3 cert must not come back
        with zero algorithms. Uses the Approved-Algorithms shape, which is the
        one that produced the empty lists."""
        from quirk.compliance import cmvp

        class _Resp:
            text = _APPROVED_FIELD_PAGE

            def raise_for_status(self):
                return None

        class _Client:
            def get(self, *a, **k):
                return _Resp()

        detail = cmvp._fetch_cert_detail(_Client(), "4884")
        assert detail["algorithms"], "RVW-022: 140-3 module parsed to zero algorithms"
        assert detail["algorithms_source"] == "approved-field"
