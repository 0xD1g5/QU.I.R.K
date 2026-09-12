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
from quirk.models import Base, CryptoEndpoint
from quirk.reports.content_model import ALGO_IMPACT_MAP, REMEDIATION_CATALOG

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
# theme_* / finding_position stay present-and-null (this plan's contract)
# ---------------------------------------------------------------------------

def test_theme_fields_present_and_null_not_owned_by_this_plan():
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
