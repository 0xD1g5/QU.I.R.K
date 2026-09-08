"""Phase 191 Plan 04 (SPKI-02) — Key Reuse section on the CLI technical markdown report.

The section always renders (D-06) — including a zero-cluster run — framed as remediation
leverage (D-05), ordered biggest-cluster-first (D-04), and always discloses coverage
(D-12). A failed/unwired loader (`key_reuse=None` or `{}`) must never raise.
"""
from __future__ import annotations

from types import SimpleNamespace

from quirk.reports.technical import KEY_REUSE_ADVISORY_CAPTION, build_tech_markdown


def _make_minimal_cfg(tmpdir="/tmp/quirk_test_key_reuse"):
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Key Reuse Test Org",
            report_owner="Key Reuse Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory=tmpdir),
    )


def _cluster(fingerprint, member_count, members):
    return {
        "fingerprint": fingerprint,
        "member_count": member_count,
        "cert_subject": f"CN=shared-{fingerprint[:6]}.example.com",
        "cert_pubkey_alg": "RSA",
        "cert_pubkey_size": 2048,
        "members": members,
    }


def _two_cluster_key_reuse():
    big = _cluster(
        "a" * 64,
        4,
        [
            {"host": "host1.example.com", "port": 443},
            {"host": "host2.example.com", "port": 443},
            {"host": "host3.example.com", "port": 8443},
            {"host": "host4.example.com", "port": 8443},
        ],
    )
    small = _cluster(
        "b" * 64,
        2,
        [
            {"host": "host5.example.com", "port": 443},
            {"host": "host6.example.com", "port": 443},
        ],
    )
    return {"clusters": [big, small], "fingerprinted": 6, "total": 10}


def test_two_clusters_render_heading_caption_coverage_and_ordering():
    md = build_tech_markdown(
        _make_minimal_cfg(), [], [], key_reuse=_two_cluster_key_reuse()
    )
    assert "## Key Reuse" in md
    assert KEY_REUSE_ADVISORY_CAPTION in md
    assert "6 of 10 TLS endpoints have SPKI fingerprints." in md

    big_idx = md.find("a" * 16)
    small_idx = md.find("b" * 16)
    assert big_idx != -1 and small_idx != -1
    assert big_idx < small_idx, (
        "4-member cluster must appear before the 2-member cluster (D-04)"
    )


def test_cluster_leverage_phrasing_not_n_separate_discoveries():
    md = build_tech_markdown(
        _make_minimal_cfg(), [], [], key_reuse=_two_cluster_key_reuse()
    )
    assert "remediates 4 endpoints" in md
    assert "remediates 2 endpoints" in md
    assert "findings discovered" not in md.lower()
    assert "4 separate discoveries" not in md.lower()
    assert "2 separate discoveries" not in md.lower()


def test_cluster_block_shows_identity_and_members():
    md = build_tech_markdown(
        _make_minimal_cfg(), [], [], key_reuse=_two_cluster_key_reuse()
    )
    assert "CN=shared-aaaaaa.example.com" in md
    assert "RSA" in md
    assert "2048" in md
    assert "host1.example.com:443" in md
    assert "host6.example.com:443" in md


def test_zero_cluster_run_still_renders_section_with_absence_sentence():
    key_reuse = {"clusters": [], "fingerprinted": 3, "total": 5}
    md = build_tech_markdown(_make_minimal_cfg(), [], [], key_reuse=key_reuse)
    assert "## Key Reuse" in md
    assert KEY_REUSE_ADVISORY_CAPTION in md
    assert "3 of 5 TLS endpoints have SPKI fingerprints." in md
    assert "No shared keys detected across 3 fingerprinted endpoints." in md


def test_key_reuse_none_or_empty_does_not_raise():
    md_none = build_tech_markdown(_make_minimal_cfg(), [], [], key_reuse=None)
    assert "## Key Reuse" in md_none

    md_empty = build_tech_markdown(_make_minimal_cfg(), [], [], key_reuse={})
    assert "## Key Reuse" in md_empty


def test_no_key_reuse_argument_at_all_still_works():
    md = build_tech_markdown(_make_minimal_cfg(), [], [])
    assert isinstance(md, str)
    assert "## Key Reuse" in md
