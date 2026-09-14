"""The exposure map must describe ONE scan, and must not draw an endpoint to itself.

Measured 2026-09-14 against the live 31-host multihost estate, `GET
/api/exposure-map` returned **27 nodes and 1225 edges**. Of those 1225:

  - 390 (32%) were SELF-edges, `source == target`
  - only 56 distinct node-pairs were actually represented
  - 1169 (95%) were duplicate rows

`10.80.0.11:443 -> 10.80.0.11:443` was drawn 66 times.

Root cause was missing scan scoping, not dense key reuse:
`compute_key_reuse_clusters` queried `crypto_endpoints` with no
`scan_run_id` filter, so it unioned all 24 scans in the database. Node
`10.80.0.1:9443` appeared in the map with ZERO rows in the latest scan — it
existed only in a run from the previous day, on a different lab profile whose
config deliberately excludes that address.

That is also what manufactured the self-edges: one endpoint appears once per
scan run, all-pairs pairs those rows against each other, and every such pair
collapses to `A -> A` once node ids are `f"{host}:{port}"`.

Scoped to one run the same data is 3 clusters and 19 edges across 12 nodes.

IMPORTANT — the cross-scan default is DELIBERATE for the report surface.
`quirk/reports/writer.py::_load_key_reuse` documents D-03: "key reuse [is] a
global, cross-scan query rather than a scan-scoped one". So
`compute_key_reuse_clusters(session)` with no `scan_run_id` MUST keep its
existing behaviour; scoping is opt-in, and it is the exposure map that opts in.
`test_default_is_still_cross_scan_for_the_report_surface` pins that so this fix
cannot silently change what reports show.
"""
from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from quirk.intelligence.exposure_map import (
    derive_exposure_map,
    derive_key_reuse_edges,
)
from quirk.intelligence.key_reuse import compute_key_reuse_clusters
from quirk.models import CryptoEndpoint

from tests.conftest import make_isolated_memory_engine

RUN_OLD = "2026-09-13T22:51:08.758882+00:00"
RUN_NEW = "2026-09-14T15:34:07.260655+00:00"

_FP_SHARED = "a" * 64


def _make_session():
    engine = make_isolated_memory_engine()
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, Session()


def _endpoint(host, port, fingerprint, scan_run_id, **kwargs):
    defaults = dict(
        protocol="TLS",
        cert_subject="CN=example.com",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        scan_run_id=scan_run_id,
    )
    defaults.update(kwargs)
    return CryptoEndpoint(
        host=host, port=port, cert_spki_fingerprint=fingerprint, **defaults
    )


def _seed_same_endpoint_scanned_twice(session):
    """The exact shape that produced the self-edges.

    Two endpoints share a key. BOTH were scanned in two different runs, so the
    database holds four rows describing two endpoints.
    """
    session.add_all([
        _endpoint("10.80.0.11", 443, _FP_SHARED, RUN_OLD),
        _endpoint("10.80.0.101", 443, _FP_SHARED, RUN_OLD),
        _endpoint("10.80.0.11", 443, _FP_SHARED, RUN_NEW),
        _endpoint("10.80.0.101", 443, _FP_SHARED, RUN_NEW),
    ])
    session.commit()


# ---------------------------------------------------------------------------
# 1. Scan scoping
# ---------------------------------------------------------------------------

def test_scoping_excludes_endpoints_absent_from_the_named_run():
    """A host present only in an OLDER run must not appear in the scoped map.

    This is the `10.80.0.1:9443` case: it was rendered as a node despite having
    zero rows in the scan being displayed.
    """
    engine, session = _make_session()
    try:
        session.add_all([
            _endpoint("10.80.0.1", 9443, _FP_SHARED, RUN_OLD),
            _endpoint("10.80.0.11", 443, _FP_SHARED, RUN_OLD),
            _endpoint("10.80.0.11", 443, _FP_SHARED, RUN_NEW),
            _endpoint("10.80.0.20", 443, _FP_SHARED, RUN_NEW),
        ])
        session.commit()

        scoped = compute_key_reuse_clusters(session, scan_run_id=RUN_NEW)
        hosts = {
            m["host"] for c in scoped["clusters"] for m in c["members"]
        }
        assert "10.80.0.1" not in hosts, (
            "An endpoint with zero rows in the requested scan appeared in the "
            f"scoped cluster set: {sorted(hosts)}"
        )
        assert hosts == {"10.80.0.11", "10.80.0.20"}
    finally:
        session.close()
        engine.dispose()


def test_default_is_still_cross_scan_for_the_report_surface():
    """D-03: no scan_run_id means the cross-scan aggregate, unchanged.

    `quirk/reports/writer.py::_load_key_reuse` depends on this. Scoping is
    opt-in precisely so this fix cannot alter what reports render.
    """
    engine, session = _make_session()
    try:
        session.add_all([
            _endpoint("10.80.0.1", 9443, _FP_SHARED, RUN_OLD),
            _endpoint("10.80.0.20", 443, _FP_SHARED, RUN_NEW),
        ])
        session.commit()

        unscoped = compute_key_reuse_clusters(session)
        hosts = {m["host"] for c in unscoped["clusters"] for m in c["members"]}
        assert hosts == {"10.80.0.1", "10.80.0.20"}, (
            "The unscoped call must still aggregate across scans (D-03) — "
            f"got {sorted(hosts)}"
        )
    finally:
        session.close()
        engine.dispose()


def test_map_defaults_to_the_latest_scan():
    """With no explicit scan, the map describes the most recent run."""
    engine, session = _make_session()
    try:
        session.add_all([
            _endpoint("10.80.0.1", 9443, _FP_SHARED, RUN_OLD),
            _endpoint("10.80.0.2", 9443, _FP_SHARED, RUN_OLD),
            _endpoint("10.80.0.11", 443, _FP_SHARED, RUN_NEW),
            _endpoint("10.80.0.20", 443, _FP_SHARED, RUN_NEW),
        ])
        session.commit()

        result = derive_exposure_map(session)
        node_ids = {n["id"] for n in result["nodes"]}
        assert node_ids == {"10.80.0.11:443", "10.80.0.20:443"}, (
            f"Map did not default to the latest scan: {sorted(node_ids)}"
        )
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# 2. Self-edges  /  3. Duplicates
#
# Guarded unconditionally, independent of scoping: an endpoint joined to itself
# is never meaningful, and a repeated pair adds no information. These hold even
# for an unscoped call, so a future caller that legitimately wants cross-scan
# edges still cannot produce a self-loop.
# ---------------------------------------------------------------------------

def test_no_self_edges_even_unscoped():
    engine, session = _make_session()
    try:
        _seed_same_endpoint_scanned_twice(session)
        edges = derive_key_reuse_edges(session)
        self_edges = [e for e in edges if e["source"] == e["target"]]
        assert not self_edges, (
            f"{len(self_edges)} self-edge(s) emitted; an endpoint is never "
            f"'key-reuse related' to itself: {self_edges[:3]}"
        )
    finally:
        session.close()
        engine.dispose()


def test_no_duplicate_pairs_even_unscoped():
    engine, session = _make_session()
    try:
        _seed_same_endpoint_scanned_twice(session)
        edges = derive_key_reuse_edges(session)
        pairs = [
            (tuple(sorted((e["source"], e["target"]))), e["edge_type"])
            for e in edges
        ]
        assert len(pairs) == len(set(pairs)), (
            f"Duplicate edge rows emitted: {len(pairs)} edges for "
            f"{len(set(pairs))} distinct pairs"
        )
    finally:
        session.close()
        engine.dispose()


def test_the_measured_regression_shape():
    """Two endpoints, each scanned twice, is ONE edge — not four, not six.

    Before the fix this shape produced all-pairs over four rows: 6 edges, of
    which 2 were self-edges and the rest duplicates of a single real pair.
    """
    engine, session = _make_session()
    try:
        _seed_same_endpoint_scanned_twice(session)
        edges = derive_key_reuse_edges(session, scan_run_id=RUN_NEW)
        assert len(edges) == 1, (
            f"Expected exactly one edge between the two endpoints, got "
            f"{len(edges)}: {edges}"
        )
        assert {edges[0]["source"], edges[0]["target"]} == {
            "10.80.0.11:443",
            "10.80.0.101:443",
        }
    finally:
        session.close()
        engine.dispose()


def test_zero_reuse_still_returns_both_keys():
    """Honest absence is preserved — empty lists, never omitted keys (D-08)."""
    engine, session = _make_session()
    try:
        session.add_all([
            _endpoint("10.80.0.11", 443, "b" * 64, RUN_NEW),
            _endpoint("10.80.0.20", 443, "c" * 64, RUN_NEW),
        ])
        session.commit()

        result = derive_exposure_map(session)
        assert result["nodes"] == []
        assert result["edges"] == []
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# Shared-CA hub nodes (2026-09-14) and operator-declared crown jewels.
# ---------------------------------------------------------------------------

def _tls(host, port, issuer, scan_run_id=RUN_NEW, fingerprint=None):
    return CryptoEndpoint(
        host=host,
        port=port,
        protocol="TLS",
        cert_issuer=issuer,
        cert_subject=f"CN={host}",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_spki_fingerprint=fingerprint,
        scan_run_id=scan_run_id,
    )


_CA_DN = "CN=ChaosLab-RootCA,OU=CA,O=ChaosLab,L=Lab,ST=NY,C=US"


def test_shared_ca_is_a_hub_not_all_pairs():
    """N endpoints under one CA produce N edges, not N*(N-1)/2.

    All-pairs over the reference estate's 10-member CA group would be 45 edges
    — rebuilding the edge explosion the scoping fix removed. A hub is linear.
    """
    from quirk.intelligence.exposure_map import derive_shared_ca_edges

    engine, session = _make_session()
    try:
        session.add_all([_tls(f"10.0.0.{i}", 443, _CA_DN) for i in range(1, 11)])
        session.commit()

        nodes, edges = derive_shared_ca_edges(session, scan_run_id=RUN_NEW)
        assert len(nodes) == 1, f"expected one CA hub, got {nodes}"
        assert len(edges) == 10, (
            f"hub must emit one edge per dependant (10), not all-pairs (45); "
            f"got {len(edges)}"
        )
        assert all(e["source"] == nodes[0]["id"] for e in edges)
        assert nodes[0]["node_type"] == "ca"
        assert nodes[0]["label"] == "ChaosLab-RootCA", (
            f"hub label should be the CN, not the full DN: {nodes[0]['label']!r}"
        )
    finally:
        session.close()
        engine.dispose()


def test_ca_with_a_single_dependant_is_not_a_shared_point_of_compromise():
    from quirk.intelligence.exposure_map import derive_shared_ca_edges

    engine, session = _make_session()
    try:
        session.add_all([
            _tls("10.0.0.1", 443, _CA_DN),
            _tls("10.0.0.2", 443, "CN=Other-CA"),
        ])
        session.commit()

        nodes, edges = derive_shared_ca_edges(session, scan_run_id=RUN_NEW)
        assert nodes == [] and edges == []
    finally:
        session.close()
        engine.dispose()


def test_ca_hub_id_cannot_collide_with_an_endpoint():
    """Hub ids are `ca:`-prefixed; endpoint ids are `host:port`."""
    from quirk.intelligence.exposure_map import derive_shared_ca_edges

    engine, session = _make_session()
    try:
        session.add_all([
            _tls("10.0.0.1", 443, _CA_DN),
            _tls("10.0.0.2", 443, _CA_DN),
        ])
        session.commit()

        nodes, _ = derive_shared_ca_edges(session, scan_run_id=RUN_NEW)
        assert nodes[0]["id"].startswith("ca:")
    finally:
        session.close()
        engine.dispose()


def test_shared_ca_respects_scan_scoping():
    from quirk.intelligence.exposure_map import derive_shared_ca_edges

    engine, session = _make_session()
    try:
        session.add_all([
            _tls("10.0.0.1", 443, _CA_DN, scan_run_id=RUN_OLD),
            _tls("10.0.0.2", 443, _CA_DN, scan_run_id=RUN_OLD),
            _tls("10.0.0.3", 443, _CA_DN, scan_run_id=RUN_NEW),
            _tls("10.0.0.4", 443, _CA_DN, scan_run_id=RUN_NEW),
        ])
        session.commit()

        _, edges = derive_shared_ca_edges(session, scan_run_id=RUN_NEW)
        targets = {e["target"] for e in edges}
        assert targets == {"10.0.0.3:443", "10.0.0.4:443"}
    finally:
        session.close()
        engine.dispose()


def test_one_endpoint_scanned_twice_is_one_dependant():
    """The same de-duplication discipline as the key-reuse self-edge fix."""
    from quirk.intelligence.exposure_map import derive_shared_ca_edges

    engine, session = _make_session()
    try:
        session.add_all([
            _tls("10.0.0.1", 443, _CA_DN),
            _tls("10.0.0.1", 443, _CA_DN),  # same endpoint, duplicate row
            _tls("10.0.0.2", 443, _CA_DN),
        ])
        session.commit()

        _, edges = derive_shared_ca_edges(session, scan_run_id=RUN_NEW)
        assert len(edges) == 2, f"duplicate rows became duplicate dependants: {edges}"
    finally:
        session.close()
        engine.dispose()


def test_crown_jewel_marks_declared_host_on_every_port():
    """A declaration names a SYSTEM, so it matches on the host portion."""
    engine, session = _make_session()
    try:
        session.add_all([
            _tls("10.0.0.20", 443, _CA_DN),
            _tls("10.0.0.99", 443, _CA_DN),
        ])
        session.commit()

        result = derive_exposure_map(session, crown_jewels=["10.0.0.20"])
        marked = {n["id"] for n in result["nodes"] if n["is_crown_jewel"]}
        assert marked == {"10.0.0.20:443"}, f"got {marked}"
    finally:
        session.close()
        engine.dispose()


def test_no_declaration_marks_nothing():
    """Honest absence — never guess a 'most important' host."""
    engine, session = _make_session()
    try:
        session.add_all([
            _tls("10.0.0.20", 443, _CA_DN),
            _tls("10.0.0.99", 443, _CA_DN),
        ])
        session.commit()

        for declaration in (None, [], ["", "  "]):
            result = derive_exposure_map(session, crown_jewels=declaration)
            assert not any(n["is_crown_jewel"] for n in result["nodes"]), declaration
    finally:
        session.close()
        engine.dispose()


def test_a_ca_hub_is_never_a_crown_jewel():
    """A crown jewel is a system the client owns, not an issuer identity."""
    engine, session = _make_session()
    try:
        session.add_all([
            _tls("10.0.0.20", 443, _CA_DN),
            _tls("10.0.0.21", 443, _CA_DN),
        ])
        session.commit()

        # Declare the CA's own CN — it must still not be marked.
        result = derive_exposure_map(
            session, crown_jewels=["ChaosLab-RootCA", _CA_DN, "10.0.0.20"]
        )
        for n in result["nodes"]:
            if n["node_type"] == "ca":
                assert not n["is_crown_jewel"], n
        assert any(
            n["is_crown_jewel"] for n in result["nodes"] if n["node_type"] == "endpoint"
        )
    finally:
        session.close()
        engine.dispose()
