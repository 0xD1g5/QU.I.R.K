"""GET /api/findings/{finding_id}/storyline — Phase 202 / Plan 03 (STORY-01).

Covers:
  - disambiguation: two findings sharing one CryptoEndpoint.id resolve to
    DIFFERENT storylines when keyed by (id, title) (D-06, the load-bearing
    case this route exists for)
  - narrative present (RSA keyword hit) vs. absent (A5 — the common case,
    D-07), with expected text imported from the catalog, never pasted
  - the severity gate (_classify_finding excludes LOW/INFO even on a
    keyword hit)
  - 422 on omitted title / non-numeric finding_id / oversized title
  - 404 (two distinct fixed details) on unknown finding_id vs. unmatched title
  - auth gating (matches sibling routes)
  - a forced-failure 500 with a fixed detail, no exception text, no path
  - all ten locked keys present on every response path
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.intelligence.remediation import REMEDIATION_CONSTITUENCY
from quirk.models import Base, CryptoEndpoint, RemediationItemFingerprint
from quirk.reports.content_model import ALGO_IMPACT_MAP, REMEDIATION_CATALOG
from quirk.ticketing.base import TicketingChannel

_ALL_TEN_KEYS = {
    "finding_id",
    "narrative",
    "quantum_impact",
    "remediation_guidance",
    "theme_slug",
    "theme_title",
    "theme_score_lift",
    "theme_finding_count",
    "theme_closed_count",
    "finding_position",
}


def _client_and_session():
    db_name = f"test_storyline_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app, headers={"X-Quirk-Request": "1"}), TestingSession


def _seed_endpoint(TestingSession, **kwargs) -> int:
    db = TestingSession()
    try:
        defaults = dict(
            host="10.0.0.1",
            port=443,
            protocol="TLS",
            scanned_at=datetime(2026, 9, 12, 12, 0, 0),
        )
        defaults.update(kwargs)
        ep = CryptoEndpoint(**defaults)
        db.add(ep)
        db.commit()
        db.refresh(ep)
        return ep.id
    finally:
        db.close()


def _seed_fingerprint_row(
    TestingSession,
    *,
    scan_run_id: str,
    slug: str,
    host: str = "10.0.0.1",
    port: int = 443,
    cli_title: str,
    state: str = "open",
) -> str:
    """Write a real RemediationItemFingerprint row. The fingerprint is
    computed by calling TicketingChannel.compute_fingerprint here (not
    hand-typed), so the test and the route agree by construction — a change
    to the hash formula breaks both together rather than silently desyncing
    them."""
    fp = TicketingChannel.compute_fingerprint({"host": host, "port": port, "title": cli_title})
    db = TestingSession()
    try:
        db.add(RemediationItemFingerprint(
            slug=slug,
            scan_run_id=scan_run_id,
            finding_fingerprint=fp,
            host=host,
            port=port,
            finding_title=cli_title,
            state=state,
        ))
        db.commit()
    finally:
        db.close()
    return fp


# ---------------------------------------------------------------------------
# Disambiguation (the load-bearing case, D-06)
# ---------------------------------------------------------------------------

def test_disambiguation_same_endpoint_id_different_title_different_storyline():
    """One endpoint yields 2+ findings sharing an id; (id, title) resolves
    each to ITS OWN storyline, not the first finding found by id.

    Endpoint fires two independent (non-elif) branches:
      - undersized RSA key -> HIGH, RSA keyword -> narrative POPULATED
      - self-signed cert   -> HIGH, no keyword   -> narrative ABSENT (A5)
    Both share the same CryptoEndpoint.id, proving the route does not just
    return "the first finding for this id".
    """
    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(
        TestingSession,
        cert_pubkey_alg="RSA",
        cert_pubkey_size=1024,
        cert_issuer="CN=self",
        cert_subject="CN=self",
    )

    resp_rsa = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "TLS certificate uses undersized RSA key"},
    )
    resp_self_signed = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "TLS certificate is self-signed"},
    )

    assert resp_rsa.status_code == 200
    assert resp_self_signed.status_code == 200

    data_rsa = resp_rsa.json()
    data_self_signed = resp_self_signed.json()

    # Same finding_id (both derived from the same CryptoEndpoint.id) ...
    assert data_rsa["finding_id"] == data_self_signed["finding_id"] == ep_id
    # ... but the two requested titles resolve to genuinely different
    # storylines: the RSA finding gets a real catalog narrative, the
    # self-signed finding gets honest absence.
    assert data_rsa["narrative"] is not None
    assert data_self_signed["narrative"] is None
    assert data_rsa != data_self_signed


# ---------------------------------------------------------------------------
# Narrative present / absent (D-07)
# ---------------------------------------------------------------------------

def test_narrative_present_undersized_rsa_matches_catalog_verbatim():
    """RSA-keyword finding returns narrative/quantum_impact/remediation_guidance
    built from ALGO_IMPACT_MAP/REMEDIATION_CATALOG — text imported from the
    catalog and compared, never pasted, so the test cannot pass if the route
    authored its own copy."""
    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(
        TestingSession,
        cert_pubkey_alg="RSA",
        cert_pubkey_size=1024,
    )

    resp = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "TLS certificate uses undersized RSA key"},
    )
    assert resp.status_code == 200
    data = resp.json()

    risk_label, impact_sentence, quantum_risk_sentence = ALGO_IMPACT_MAP["RSA"]
    assert data["narrative"] == f"{risk_label} — {impact_sentence}"
    assert data["quantum_impact"] == quantum_risk_sentence
    assert data["remediation_guidance"] == REMEDIATION_CATALOG["RSA"]
    assert set(data.keys()) == _ALL_TEN_KEYS


def test_narrative_absent_plaintext_http_returns_200_with_nulls():
    """A5: plaintext-HTTP finding has no algorithm keyword -> 200, all three
    narrative fields null. Absence is a normal successful response, not an
    error."""
    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(TestingSession, protocol="HTTP")

    resp = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "Unencrypted HTTP service"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["narrative"] is None
    assert data["quantum_impact"] is None
    assert data["remediation_guidance"] is None
    assert set(data.keys()) == _ALL_TEN_KEYS


def test_severity_gate_excludes_low_severity_even_with_keyword():
    """_classify_finding's own severity gate ({CRITICAL,HIGH,MEDIUM}) must not
    be silently bypassed by the route: a LOW-severity finding with an RSA
    keyword in its description still gets null narrative.

    No `_derive_findings` branch naturally emits a LOW-severity finding, so
    this exercises the route's gate handling directly by monkeypatching
    `finding_by_id_and_title` to return a synthetic LOW-severity FindingItem
    carrying an RSA keyword — proving the route does not bypass
    `_classify_finding`'s own severity threshold.
    """
    from unittest.mock import patch

    from quirk.dashboard.api.schemas import FindingItem

    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(TestingSession, protocol="HTTP")

    db = TestingSession()
    try:
        endpoint = db.query(CryptoEndpoint).filter(CryptoEndpoint.id == ep_id).one()
    finally:
        db.close()

    low_severity_finding = FindingItem(
        id=ep_id,
        host="10.0.0.1",
        port=443,
        severity="LOW",
        title="Informational RSA note",
        description="RSA key material observed but not actionable.",
    )

    with patch(
        "quirk.dashboard.api.routes.storyline.finding_by_id_and_title",
        return_value=(endpoint, low_severity_finding),
    ):
        resp = client.get(
            f"/api/findings/{ep_id}/storyline",
            params={"title": "Informational RSA note"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["narrative"] is None
    assert data["quantum_impact"] is None
    assert data["remediation_guidance"] is None


# ---------------------------------------------------------------------------
# 422 validation
# ---------------------------------------------------------------------------

def test_422_missing_title():
    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(TestingSession, protocol="HTTP")
    resp = client.get(f"/api/findings/{ep_id}/storyline")
    assert resp.status_code == 422


def test_422_non_numeric_finding_id():
    client, TestingSession = _client_and_session()
    resp = client.get(
        "/api/findings/not-a-number/storyline",
        params={"title": "Unencrypted HTTP service"},
    )
    assert resp.status_code == 422


def test_422_title_too_long():
    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(TestingSession, protocol="HTTP")
    resp = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "x" * 513},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 404 — two distinct fixed details
# ---------------------------------------------------------------------------

def test_404_unknown_finding_id():
    client, TestingSession = _client_and_session()
    resp = client.get(
        "/api/findings/999999/storyline",
        params={"title": "Unencrypted HTTP service"},
    )
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert "999999" not in detail
    assert "Unencrypted HTTP service" not in detail


def test_404_known_endpoint_unmatched_title():
    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(TestingSession, protocol="HTTP")
    resp = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "This title does not exist on this endpoint"},
    )
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert "This title does not exist on this endpoint" not in detail


def test_404_details_are_distinguishable():
    """The two 404 causes must not share the same detail string, so an
    operator/log reader can tell 'no such endpoint' from 'wrong title'."""
    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(TestingSession, protocol="HTTP")

    resp_no_endpoint = client.get(
        "/api/findings/999999/storyline",
        params={"title": "Unencrypted HTTP service"},
    )
    resp_no_title = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "Nonexistent title"},
    )
    assert resp_no_endpoint.json()["detail"] != resp_no_title.json()["detail"]


# ---------------------------------------------------------------------------
# Auth gating
# ---------------------------------------------------------------------------

def test_auth_rejects_unauthenticated_request(monkeypatch):
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    db_name = f"test_storyline_auth_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    tc = TestClient(app, raise_server_exceptions=False)

    ep_id = _seed_endpoint(TestingSession, protocol="HTTP")
    resp = tc.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "Unencrypted HTTP service"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Fixed 500 — no exception text, no path, exact fixed detail
# ---------------------------------------------------------------------------

def test_fixed_500_on_internal_failure():
    from unittest.mock import patch

    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(TestingSession, protocol="HTTP")

    with patch(
        "quirk.dashboard.api.routes.storyline.finding_by_id_and_title",
        side_effect=RuntimeError("/Users/someone/secret/path.db exploded"),
    ):
        resp = client.get(
            f"/api/findings/{ep_id}/storyline",
            params={"title": "Unencrypted HTTP service"},
        )

    assert resp.status_code == 500
    body_text = resp.text
    assert resp.json()["detail"] == "Storyline lookup failed"
    assert "Traceback" not in body_text
    assert "/Users/" not in body_text
    assert "secret/path.db" not in body_text


# ---------------------------------------------------------------------------
# theme_* / finding_position: empty-table honest absence (RSA finding with
# NO fingerprint rows seeded at all — the table exists, per Base.metadata,
# but holds zero rows for this scan). 202-05 now OWNS these fields; the
# join's own honest-absence behavior is what keeps this test green.
# ---------------------------------------------------------------------------

def test_theme_fields_null_when_fingerprint_table_is_empty_for_this_scan():
    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(
        TestingSession,
        cert_pubkey_alg="RSA",
        cert_pubkey_size=1024,
    )
    resp = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "TLS certificate uses undersized RSA key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "theme_slug",
        "theme_title",
        "theme_score_lift",
        "theme_finding_count",
        "theme_closed_count",
        "finding_position",
    ):
        assert key in data
        assert data[key] is None


# ---------------------------------------------------------------------------
# 202-05 (STORY-02, D-06/D-08/D-09): the theme-attribution fingerprint join
# ---------------------------------------------------------------------------

def test_tie_break_prefers_specific_theme_derived_from_data():
    """D-08: a fingerprint matching BOTH the severity catch-all and one
    specific title-based slug resolves to the SPECIFIC one. The expected
    winner is DERIVED from REMEDIATION_CONSTITUENCY at run time -- no
    literal slug string is asserted as the answer -- with a non-vacuity
    guard proving the seeded set actually contains one severity slug and
    one non-severity slug (the Phase-185 D-14 vacuous-test failure mode)."""
    client, TestingSession = _client_and_session()
    scan_run_id = "2026-09-12T00:00:00"
    ep_id = _seed_endpoint(
        TestingSession,
        cert_issuer="CN=self",
        cert_subject="CN=self",
        scan_run_id=scan_run_id,
    )
    cli_title = "TLS certificate is self-signed"  # identity-bridged (202-01)
    fp = _seed_fingerprint_row(
        TestingSession, scan_run_id=scan_run_id, slug="self-signed-certificates", cli_title=cli_title,
    )
    # Same fingerprint, second slug -- the multi-theme case (28/67 live).
    db = TestingSession()
    try:
        db.add(RemediationItemFingerprint(
            slug="high-impact-findings",
            scan_run_id=scan_run_id,
            finding_fingerprint=fp,
            host="10.0.0.1",
            port=443,
            finding_title=cli_title,
            state="open",
        ))
        db.commit()
    finally:
        db.close()

    seeded_slugs = ["self-signed-certificates", "high-impact-findings"]
    kinds = {slug: REMEDIATION_CONSTITUENCY[slug][0] for slug in seeded_slugs}
    # Non-vacuity guard: without both a severity slug and a non-severity slug
    # present, the "prefer non-severity" partition below would be trivially
    # satisfied without exercising the tie-break at all.
    assert "severity" in kinds.values(), "seeded set has no severity slug -- test would be vacuous"
    assert any(kind != "severity" for kind in kinds.values()), (
        "seeded set has no non-severity slug -- test would be vacuous"
    )
    expected_winner = next(slug for slug, kind in kinds.items() if kind != "severity")

    resp = client.get(f"/api/findings/{ep_id}/storyline", params={"title": cli_title})
    assert resp.status_code == 200
    data = resp.json()
    assert data["theme_slug"] == expected_winner
    assert data["theme_slug"] != "high-impact-findings"
    assert data["theme_title"] is not None


def test_catchall_only_renders_when_it_is_the_finding_only_theme():
    """D-09: undersized-RSA is HIGH severity and in no fingerprint tuple
    (202-01's census) -- the catch-all is its ONLY match and it IS rendered,
    not suppressed to A1. Locks the interpretation recorded in Task 2 so a
    future change to it is a visible, deliberate test edit."""
    client, TestingSession = _client_and_session()
    scan_run_id = "2026-09-12T02:00:00"
    ep_id = _seed_endpoint(
        TestingSession,
        cert_pubkey_alg="RSA",
        cert_pubkey_size=1024,
        scan_run_id=scan_run_id,
    )
    cli_title = "TLS certificate uses undersized RSA key"
    _seed_fingerprint_row(
        TestingSession, scan_run_id=scan_run_id, slug="high-impact-findings", cli_title=cli_title,
    )

    resp = client.get(f"/api/findings/{ep_id}/storyline", params={"title": cli_title})
    assert resp.status_code == 200
    data = resp.json()
    assert data["theme_slug"] == "high-impact-findings"
    assert data["theme_title"] is not None


def test_true_absence_untrusted_ca_constitutes_no_theme():
    """Contrast case needing no interpretation: untrusted-CA is MEDIUM and in
    no constituency tuple -- genuinely no theme, even with matching
    fingerprint rows present for OTHER slugs in the same scan."""
    client, TestingSession = _client_and_session()
    scan_run_id = "2026-09-12T03:00:00"
    ep_id = _seed_endpoint(
        TestingSession,
        cert_issuer="CN=CA",
        cert_subject="CN=host",
        chain_verified=False,
        scan_run_id=scan_run_id,
    )
    # Seed an unrelated fingerprint row for the same scan to prove this
    # finding's OWN fingerprint (not just the scan) determines the outcome.
    _seed_fingerprint_row(
        TestingSession,
        scan_run_id=scan_run_id,
        slug="plaintext-http-exposure",
        cli_title="Plaintext HTTP service detected",
    )

    resp = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "TLS certificate issued by untrusted CA"},
    )
    assert resp.status_code == 200
    data = resp.json()
    for key in ("theme_slug", "theme_title", "theme_score_lift", "theme_finding_count", "theme_closed_count"):
        assert data[key] is None


def test_unbridged_title_stays_null_and_never_reaches_fingerprint_compute():
    """A finding class in UNBRIDGED_DASHBOARD_TITLES gets honest absence --
    never a wrong theme -- and the route must REFUSE before ever computing a
    fingerprint, not merely miss on the lookup."""
    from unittest.mock import patch

    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(TestingSession, protocol="TLS", tls_weak_ciphers_present=True)

    with patch(
        "quirk.dashboard.api.routes.storyline.TicketingChannel.compute_fingerprint"
    ) as mock_fp:
        resp = client.get(
            f"/api/findings/{ep_id}/storyline",
            params={"title": "Weak cipher suites enabled"},
        )
    assert resp.status_code == 200
    data = resp.json()
    for key in ("theme_slug", "theme_title", "theme_score_lift", "theme_finding_count", "theme_closed_count"):
        assert data[key] is None
    mock_fp.assert_not_called()


def test_missing_fingerprint_table_degrades_to_200_with_narrative_intact():
    """Pitfall 4: against a DB where remediation_item_fingerprints genuinely
    does not exist (real DROP TABLE, not a patch), the response is 200 with
    all theme_* None AND the narrative fields still populated for a
    catalog-matching finding -- the two data paths are independent (S6)."""
    client, TestingSession = _client_and_session()
    ep_id = _seed_endpoint(TestingSession, cert_pubkey_alg="RSA", cert_pubkey_size=1024)

    # Genuinely drop the table so the route's query raises
    # OperationalError: no such table -- not simulated.
    engine = TestingSession.kw["bind"]
    RemediationItemFingerprint.__table__.drop(engine)

    resp = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "TLS certificate uses undersized RSA key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    for key in ("theme_slug", "theme_title", "theme_score_lift", "theme_finding_count", "theme_closed_count"):
        assert data[key] is None
    # Narrative section (202-03) is unaffected by the fingerprint-table loss.
    assert data["narrative"] is not None


def test_counts_eight_constituents_six_closed():
    """item_progress's own docstring example: 6 of 8 verified closed."""
    client, TestingSession = _client_and_session()
    scan_run_id = "2026-09-12T04:00:00"
    ep_id = _seed_endpoint(
        TestingSession, protocol="HTTP", host="10.0.0.1", port=80, scan_run_id=scan_run_id,
    )
    cli_title = "Plaintext HTTP service detected"

    # This finding's own row (row 1 of 8).
    _seed_fingerprint_row(
        TestingSession,
        scan_run_id=scan_run_id,
        slug="plaintext-http-exposure",
        host="10.0.0.1",
        port=80,
        cli_title=cli_title,
        state="closed",
    )
    # 7 more constituent rows -- 5 more closed, 2 open -- all under the same
    # slug/scan, distinct hosts so they get distinct fingerprints.
    for i in range(5):
        _seed_fingerprint_row(
            TestingSession,
            scan_run_id=scan_run_id,
            slug="plaintext-http-exposure",
            host=f"10.0.1.{i}",
            port=80,
            cli_title=cli_title,
            state="closed",
        )
    for i in range(2):
        _seed_fingerprint_row(
            TestingSession,
            scan_run_id=scan_run_id,
            slug="plaintext-http-exposure",
            host=f"10.0.2.{i}",
            port=80,
            cli_title=cli_title,
            state="open",
        )

    resp = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "Unencrypted HTTP service"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["theme_slug"] == "plaintext-http-exposure"
    assert data["theme_finding_count"] == 8
    assert data["theme_closed_count"] == 6
    # finding_position is always null, on every path including this
    # fully-populated one (UI-SPEC A4).
    assert data["finding_position"] is None


def test_never_zero_for_null_item_progress_zero_total():
    """A theme whose item_progress total is 0 yields theme_finding_count
    None, never 0 -- not naturally reachable through the route (a matched
    slug implies at least one constituent row, this finding's own), so
    exercised directly by patching item_progress at the unit level."""
    from unittest.mock import patch

    client, TestingSession = _client_and_session()
    scan_run_id = "2026-09-12T05:00:00"
    ep_id = _seed_endpoint(
        TestingSession, cert_pubkey_alg="RSA", cert_pubkey_size=1024, scan_run_id=scan_run_id,
    )
    cli_title = "TLS certificate uses undersized RSA key"
    _seed_fingerprint_row(
        TestingSession, scan_run_id=scan_run_id, slug="high-impact-findings", cli_title=cli_title,
    )

    with patch(
        "quirk.dashboard.api.routes.storyline.item_progress", return_value=(0, 0),
    ):
        resp = client.get(f"/api/findings/{ep_id}/storyline", params={"title": cli_title})

    assert resp.status_code == 200
    data = resp.json()
    assert data["theme_slug"] == "high-impact-findings"
    assert data["theme_finding_count"] is None
    assert data["theme_closed_count"] is None


def test_numeric_equality_with_roadmap_surface(monkeypatch):
    """theme_score_lift for a finding equals the score_lift the /api/scan/latest
    roadmap node for that SAME slug reports for the SAME scan -- proven by
    comparing two live API responses, not two internal function calls. This
    is the drift class Phase 201 fixed and the claim STORY-02 actually makes."""
    client, TestingSession = _client_and_session()
    scan_run_id = "2026-09-12T06:00:00"
    ep_id = _seed_endpoint(
        TestingSession,
        cert_issuer="CN=self",
        cert_subject="CN=self",
        scan_run_id=scan_run_id,
        scanned_at=datetime(2026, 9, 12, 6, 0, 0),
    )
    cli_title = "TLS certificate is self-signed"
    _seed_fingerprint_row(
        TestingSession, scan_run_id=scan_run_id, slug="self-signed-certificates", cli_title=cli_title,
    )

    def _fake_lifts(evidence, items, *, profile=None, weights=None):
        return {"self-signed-certificates": 7}

    monkeypatch.setattr("quirk.dashboard.api.routes.scan.compute_item_lifts", _fake_lifts)

    roadmap_resp = client.get("/api/scan/latest")
    assert roadmap_resp.status_code == 200
    roadmap_nodes = roadmap_resp.json()["roadmap"]["nodes"]
    roadmap_node = next(n for n in roadmap_nodes if n["slug"] == "self-signed-certificates")

    story_resp = client.get(
        f"/api/findings/{ep_id}/storyline",
        params={"title": "TLS certificate is self-signed"},
    )
    assert story_resp.status_code == 200
    story_data = story_resp.json()

    assert story_data["theme_slug"] == "self-signed-certificates"
    assert roadmap_node["score_lift"] == 7
    assert story_data["theme_score_lift"] == roadmap_node["score_lift"] == 7


def test_theme_score_lift_null_when_no_modelable_delta(monkeypatch):
    """A2: a theme whose slug has no entry in the lift map (every
    fingerprint/severity slug IS modelable per score_lift.py's `_DELTAS`
    table, so a genuinely absent-from-the-map slug is forced the same way
    `tests/test_scan_roadmap_score_lift.py`'s own Behavior-2 test forces it)
    yields theme_score_lift None, with theme_title and counts still
    populated -- the two are independently gated, matching item_progress's
    availability being strictly wider than the lift's."""
    client, TestingSession = _client_and_session()
    scan_run_id = "2026-09-12T07:00:00"
    ep_id = _seed_endpoint(
        TestingSession, cert_pubkey_alg="RSA", cert_pubkey_size=1024, scan_run_id=scan_run_id,
    )
    cli_title = "TLS certificate uses undersized RSA key"
    _seed_fingerprint_row(
        TestingSession, scan_run_id=scan_run_id, slug="high-impact-findings", cli_title=cli_title, state="closed",
    )

    monkeypatch.setattr(
        "quirk.dashboard.api.routes.scan.compute_item_lifts",
        lambda evidence, items, *, profile=None, weights=None: {},
    )

    resp = client.get(f"/api/findings/{ep_id}/storyline", params={"title": cli_title})
    assert resp.status_code == 200
    data = resp.json()
    assert data["theme_slug"] == "high-impact-findings"
    assert data["theme_title"] is not None
    assert data["theme_finding_count"] == 1
    assert data["theme_closed_count"] == 1
    assert data["theme_score_lift"] is None
