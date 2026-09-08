"""Phase 191 Plan 03 (SPKI-02): correctness tests for
``quirk.intelligence.key_reuse.compute_key_reuse_clusters``.

There is no existing GROUP-BY-aggregate test in this repo to copy — this
file is built directly from the module's own published contract (see its
docstring) rather than from a prior analog: cluster formation, descending
member-count ordering, NULL-fingerprint exclusion (D-12), always-present
coverage counts, the always-present zero-reuse shape, and read-only
behavior (no row mutation as a side effect of calling the function).
"""
from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from quirk.intelligence.key_reuse import compute_key_reuse_clusters
from quirk.models import CryptoEndpoint

from tests.conftest import make_isolated_memory_engine


def _make_session():
    engine = make_isolated_memory_engine()
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, Session()


def _endpoint(host, port, fingerprint, **kwargs):
    defaults = dict(
        protocol="TLS",
        cert_subject="CN=example.com",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
    )
    defaults.update(kwargs)
    return CryptoEndpoint(host=host, port=port, cert_spki_fingerprint=fingerprint, **defaults)


def test_cluster_formation_two_shared_one_unique():
    """Three TLS endpoints, two sharing fingerprint X and one with
    fingerprint Y, produce exactly one cluster of the two X endpoints."""
    engine, session = _make_session()
    try:
        fp_x = "x" * 64
        fp_y = "y" * 64
        session.add_all(
            [
                _endpoint("a.example.com", 443, fp_x),
                _endpoint("b.example.com", 443, fp_x),
                _endpoint("c.example.com", 443, fp_y),
            ]
        )
        session.commit()

        result = compute_key_reuse_clusters(session)

        assert len(result["clusters"]) == 1
        cluster = result["clusters"][0]
        assert cluster["member_count"] == 2
        assert cluster["fingerprint"] == fp_x
        members = sorted(cluster["members"], key=lambda m: m["host"])
        assert members == [
            {"host": "a.example.com", "port": 443},
            {"host": "b.example.com", "port": 443},
        ]
    finally:
        session.close()
        engine.dispose()


def test_clusters_ordered_by_member_count_descending():
    """A 4-member cluster precedes a 2-member one."""
    engine, session = _make_session()
    try:
        fp_big = "b" * 64
        fp_small = "s" * 64
        rows = [_endpoint(f"small{i}.example.com", 443, fp_small) for i in range(2)]
        rows += [_endpoint(f"big{i}.example.com", 443, fp_big) for i in range(4)]
        session.add_all(rows)
        session.commit()

        result = compute_key_reuse_clusters(session)

        assert [c["fingerprint"] for c in result["clusters"]] == [fp_big, fp_small]
        assert [c["member_count"] for c in result["clusters"]] == [4, 2]
    finally:
        session.close()
        engine.dispose()


def test_null_fingerprint_endpoints_excluded_regardless_of_count():
    """Endpoints with cert_spki_fingerprint is None never form a cluster,
    no matter how many share NULL (D-12)."""
    engine, session = _make_session()
    try:
        session.add_all(
            [
                _endpoint("a.example.com", 443, None),
                _endpoint("b.example.com", 443, None),
                _endpoint("c.example.com", 443, None),
            ]
        )
        session.commit()

        result = compute_key_reuse_clusters(session)

        assert result["clusters"] == []
        assert result["total"] == 3
        assert result["fingerprinted"] == 0
    finally:
        session.close()
        engine.dispose()


def test_coverage_counts_always_present_including_when_clusters_empty():
    engine, session = _make_session()
    try:
        fp = "f" * 64
        session.add_all(
            [
                _endpoint("a.example.com", 443, fp),
                _endpoint("b.example.com", 443, None),
            ]
        )
        session.commit()

        result = compute_key_reuse_clusters(session)

        assert result["clusters"] == []
        assert result["total"] == 2
        assert result["fingerprinted"] == 1
    finally:
        session.close()
        engine.dispose()


def test_zero_reuse_database_returns_exact_key_shape():
    """A DB with zero rows returns {"clusters": [], "fingerprinted": 0,
    "total": 0} — never a missing key, never None (D-06/D-12)."""
    engine, session = _make_session()
    try:
        result = compute_key_reuse_clusters(session)

        assert set(result.keys()) == {"clusters", "fingerprinted", "total"}
        assert result["clusters"] == []
        assert result["fingerprinted"] == 0
        assert result["total"] == 0
    finally:
        session.close()
        engine.dispose()


def test_read_only_no_row_mutation():
    """Calling the function performs no writes: the endpoint rows are
    byte-identical afterwards."""
    engine, session = _make_session()
    try:
        fp = "r" * 64
        session.add_all(
            [
                _endpoint("a.example.com", 443, fp),
                _endpoint("b.example.com", 443, fp),
            ]
        )
        session.commit()

        before = [
            (row.host, row.port, row.cert_spki_fingerprint)
            for row in session.query(CryptoEndpoint).order_by(CryptoEndpoint.host).all()
        ]

        compute_key_reuse_clusters(session)

        assert len(session.new) == 0
        assert len(session.dirty) == 0
        assert len(session.deleted) == 0

        after = [
            (row.host, row.port, row.cert_spki_fingerprint)
            for row in session.query(CryptoEndpoint).order_by(CryptoEndpoint.host).all()
        ]
        assert before == after
    finally:
        session.close()
        engine.dispose()


def test_non_tls_endpoints_excluded_from_total_and_clusters():
    """Endpoints whose protocol isn't TLS never contribute to total,
    fingerprinted, or clusters, even if they share a fingerprint with a
    TLS endpoint."""
    engine, session = _make_session()
    try:
        fp = "n" * 64
        session.add_all(
            [
                _endpoint("a.example.com", 443, fp, protocol="TLS"),
                _endpoint("b.example.com", 22, fp, protocol="SSH"),
            ]
        )
        session.commit()

        result = compute_key_reuse_clusters(session)

        assert result["total"] == 1
        assert result["fingerprinted"] == 1
        assert result["clusters"] == []
    finally:
        session.close()
        engine.dispose()
