"""IDENT-05 / IDENT-06 (Phase 238, D-01, D-02, D-27, D-33): a weak key in a
target's published JWKS yields exactly one finding per key, on the CLI report
and the dashboard alike, through the one shared evaluator
(``quirk.engine.findings_evaluator.evaluate_identity_endpoints``).

Rule table (D-02), first match wins, one finding per distinct key:
  1. ``alg`` is exactly "none" (any case) -> CRITICAL "JWKS key declares alg:none"
  2. the JWKS publishes private or symmetric key material (the scanner's
     marker, or a non-empty secret member such as ``k``) -> CRITICAL
     "JWKS publishes secret key material"
  3. an HS* alg or ``kty: oct`` -> HIGH "JWKS key uses a symmetric (HMAC) algorithm"
  4. an RSA key under 2048 bits -> HIGH "JWKS key uses undersized RSA key"

Healthy keys (RS256 2048, ES256 P-256, EdDSA Ed25519) give no finding (D-33):
JWT rows never reach the OIDC RS-family lookup, where RS256 is HIGH.

Score treatment (D-04/D-27): an ordinary CRITICAL or HIGH. It moves the score
only through the existing consequence ceiling, with no new SCORE_WEIGHTS key.
One healthy TLS row scores 77; adding a CRITICAL JWKS key scores 31 and a HIGH
one scores 63, on derive_report_findings and derive_dashboard_scoring_findings.
"""
from __future__ import annotations

import base64
import copy
import datetime
import itertools
import json

import pytest

from quirk.dashboard.api.finding_derivation import (
    _derive_findings,
    _derive_identity_findings,
    derive_dashboard_finding_items,
    derive_dashboard_scoring_findings,
)
from quirk.engine.findings_evaluator import derive_report_findings
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.models import CryptoEndpoint

ALG_NONE = "JWKS key declares alg:none"
KEY_MATERIAL = "JWKS publishes secret key material"
HMAC = "JWKS key uses a symmetric (HMAC) algorithm"
RSA_SMALL = "JWKS key uses undersized RSA key"

_PAST = datetime.datetime(2020, 1, 1)
_FUTURE = datetime.datetime(2035, 1, 1)
_NOW = datetime.datetime(2026, 11, 16, 12, 0, 0)
_ids = itertools.count(23840)
_JWKS_HOST = "https://idp.jwks.test"


def _modulus_b64(bits: int) -> str:
    """base64url modulus of a real RSA key of *bits* bits."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    n = rsa.generate_private_key(public_exponent=65537, key_size=bits).public_key().public_numbers().n
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


_N_1024 = _modulus_b64(1024)
_N_2048 = _modulus_b64(2048)


def _jwt_row(host, jwk, bits, **kw) -> CryptoEndpoint:
    base = dict(
        id=next(_ids), host=host, port=443, protocol="JWT", scanned_at=_NOW,
        cert_pubkey_alg=jwk.get("alg") or jwk["kty"],
        cert_pubkey_size=bits,
        jwt_scan_json=json.dumps(jwk),
        service_detail="/.well-known/jwks.json",
    )
    base.update(kw)
    return CryptoEndpoint(**base)


def _tls_row() -> CryptoEndpoint:
    return CryptoEndpoint(
        id=next(_ids), host="10.238.4.1", port=443, protocol="TLS",
        scanned_at=_NOW,
        cert_subject="CN=leaf", cert_issuer="CN=ca",
        cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
        cert_not_before=_PAST, cert_not_after=_FUTURE,
        tls_version="TLSv1.3", tls_supported_versions="TLSv1.3",
        chain_verified=True, cert_sig_alg="sha256",
    )


WEAK_KEYS = {
    "alg_none": ({"kty": "oct", "alg": "none", "kid": "a", "k": ""}, None, ALG_NONE, "CRITICAL"),
    "key_material": (
        {"kty": "oct", "alg": "HS256", "kid": "s", "secret_material_present": True},
        128, KEY_MATERIAL, "CRITICAL",
    ),
    "hmac_no_material": ({"kty": "oct", "alg": "HS256", "kid": "h"}, None, HMAC, "HIGH"),
    "rsa_1024": (
        {"kty": "RSA", "alg": "RS256", "kid": "r", "n": _N_1024, "e": "AQAB"},
        1024, RSA_SMALL, "HIGH",
    ),
}

HEALTHY_KEYS = [
    ({"kty": "RSA", "alg": "RS256", "kid": "ok-rsa", "n": _N_2048, "e": "AQAB"}, 2048),
    ({"kty": "EC", "alg": "ES256", "kid": "ok-ec", "crv": "P-256", "x": "eA", "y": "eQ"}, 256),
    ({"kty": "OKP", "alg": "EdDSA", "kid": "ok-ed", "crv": "Ed25519", "x": "eA"}, None),
]


def _report(eps):
    return [(f["title"], f["severity"], f.get("protocol")) for f in derive_report_findings(eps)]


def _dash(eps):
    return [(f.title, f.severity, f.protocol) for f in derive_dashboard_finding_items(eps)]


def _ident(eps):
    return [(f.title, f.severity, f.protocol) for f in _derive_identity_findings(eps)]


def _jwt_only(triples):
    return [t for t in triples if t[2] == "JWT"]


def _scores(eps):
    out = []
    for findings in (derive_report_findings(eps), derive_dashboard_scoring_findings(eps)):
        ev = build_evidence_summary(endpoints=eps, findings=findings)
        out.append(compute_readiness_score(copy.deepcopy(ev)))
    return out


@pytest.mark.parametrize("case", sorted(WEAK_KEYS))
def test_report_and_dashboard_emit_one_finding_per_weak_key(case):
    jwk, bits, title, severity = WEAK_KEYS[case]
    eps = [_jwt_row(_JWKS_HOST, jwk, bits)]
    for triples in (_report(eps), _dash(eps), _ident(eps)):
        hits = [t for t in triples if t[0] == title]
        assert len(hits) == 1
        assert hits[0][1] == severity
        assert len(_jwt_only(triples)) == 1


def test_rule_order_first_match_wins():
    jwk = {"kty": "oct", "alg": "none", "kid": "x", "k": "c2VjcmV0c2VjcmV0MTIzNA"}
    eps = [_jwt_row(_JWKS_HOST, jwk, None)]
    for triples in (_report(eps), _dash(eps), _ident(eps)):
        assert _jwt_only(triples) == [(ALG_NONE, "CRITICAL", "JWT")]


def test_empty_k_is_not_key_material():
    jwk = {"kty": "oct", "alg": "HS256", "kid": "e", "k": ""}
    eps = [_jwt_row(_JWKS_HOST, jwk, None)]
    for triples in (_report(eps), _dash(eps), _ident(eps)):
        assert _jwt_only(triples) == [(HMAC, "HIGH", "JWT")]
        assert len([t for t in triples if t[1] == "CRITICAL"]) == 0


def test_jwk_with_nonempty_k_and_no_marker_is_key_material():
    """A JWK carrying a non-empty `k` member reads as published key material."""
    jwk = {"kty": "oct", "alg": "HS256", "kid": "l", "k": "c2VjcmV0c2VjcmV0MTIzNA"}
    eps = [_jwt_row(_JWKS_HOST, jwk, None)]
    for triples in (_report(eps), _dash(eps), _ident(eps)):
        assert _jwt_only(triples) == [(KEY_MATERIAL, "CRITICAL", "JWT")]


def test_healthy_keys_produce_no_finding():
    for jwk, bits in HEALTHY_KEYS:
        eps = [_jwt_row(_JWKS_HOST, jwk, bits)]
        assert _report(eps) == []
        assert _dash(eps) == []
        assert _ident(eps) == []
        scored = _scores([_tls_row(), _jwt_row(_JWKS_HOST, jwk, bits)])
        assert [s["score"] for s in scored] == [77, 77]


def test_kid_dedupe():
    jwk = {"kty": "oct", "alg": "HS256", "kid": "a"}
    same = [_jwt_row(_JWKS_HOST, jwk, None), _jwt_row(_JWKS_HOST, dict(jwk), None)]
    for triples in (_report(same), _dash(same), _ident(same)):
        assert len(_jwt_only(triples)) == 1
    two = [_jwt_row(_JWKS_HOST, jwk, None), _jwt_row(_JWKS_HOST, dict(jwk, kid="b"), None)]
    for triples in (_report(two), _dash(two), _ident(two)):
        assert len(_jwt_only(triples)) == 2


def test_keys_sharing_a_kid_are_evaluated_separately():
    """RFC 7517 allows keys of different types to share a kid. A healthy
    RS256-2048 key and an alg:none key both published as kid "1" on one host
    must still yield the alg:none CRITICAL, on all three derivers."""
    healthy = {"kty": "RSA", "alg": "RS256", "kid": "1", "n": _N_2048, "e": "AQAB"}
    unsigned = {"kty": "oct", "alg": "none", "kid": "1"}
    for pair in ([healthy, unsigned], [unsigned, healthy]):
        eps = [
            _jwt_row(_JWKS_HOST, pair[0], 2048 if pair[0] is healthy else None),
            _jwt_row(_JWKS_HOST, pair[1], 2048 if pair[1] is healthy else None),
        ]
        for triples in (_report(eps), _dash(eps), _ident(eps)):
            assert _jwt_only(triples) == [(ALG_NONE, "CRITICAL", "JWT")]
            assert len([t for t in triples if t[1] == "CRITICAL"]) == 1
        scored = _scores([_tls_row()] + eps)
        assert [s["score"] for s in scored] == [31, 31]


def test_three_keys_sharing_a_kid_each_get_their_own_rule():
    healthy = {"kty": "RSA", "alg": "RS256", "kid": "1", "n": _N_2048, "e": "AQAB"}
    unsigned = {"kty": "oct", "alg": "none", "kid": "1"}
    material = {"kty": "oct", "alg": "HS256", "kid": "1", "secret_material_present": True}
    eps = [
        _jwt_row(_JWKS_HOST, healthy, 2048),
        _jwt_row(_JWKS_HOST, unsigned, None),
        _jwt_row(_JWKS_HOST, material, 128),
    ]
    for triples in (_report(eps), _dash(eps), _ident(eps)):
        assert sorted(_jwt_only(triples)) == [
            (ALG_NONE, "CRITICAL", "JWT"),
            (KEY_MATERIAL, "CRITICAL", "JWT"),
        ]


def test_identical_keys_without_a_kid_yield_one_finding():
    """The same weak key reached twice (no kid) is one finding, not two."""
    jwk = {"kty": "RSA", "alg": "RS256", "n": _N_1024, "e": "AQAB"}
    eps = [_jwt_row(_JWKS_HOST, jwk, 1024), _jwt_row(_JWKS_HOST, dict(jwk), 1024)]
    for triples in (_report(eps), _dash(eps), _ident(eps)):
        assert _jwt_only(triples) == [(RSA_SMALL, "HIGH", "JWT")]
    other = dict(jwk, n=_modulus_b64(1024))
    eps = [_jwt_row(_JWKS_HOST, jwk, 1024), _jwt_row(_JWKS_HOST, other, 1024)]
    for triples in (_report(eps), _dash(eps), _ident(eps)):
        assert _jwt_only(triples) == [(RSA_SMALL, "HIGH", "JWT"), (RSA_SMALL, "HIGH", "JWT")]


def test_findings_for_endpoint_never_sees_jwt_rows():
    jwk = WEAK_KEYS["alg_none"][0]
    assert _derive_findings([_jwt_row(_JWKS_HOST, jwk, None)]) == []


@pytest.mark.parametrize(
    "case, expected",
    [
        ("healthy_rs256", 77),
        ("alg_none", 31),
        ("key_material", 31),
        ("hmac_no_material", 63),
        ("rsa_1024", 63),
    ],
)
def test_weak_jwks_key_lowers_score_on_both_surfaces(case, expected):
    if case == "healthy_rs256":
        jwk, bits = HEALTHY_KEYS[0]
    else:
        jwk, bits = WEAK_KEYS[case][0], WEAK_KEYS[case][1]
    eps = [_tls_row(), _jwt_row(_JWKS_HOST, jwk, bits)]
    scored = _scores(eps)
    assert [s["score"] for s in scored] == [expected, expected]
    for s in scored:
        reason = s.get("rating_cap_reason") or ""
        if expected == 31:
            assert "1 open CRITICAL finding" in reason
        elif expected == 63:
            assert "1 open HIGH finding" in reason


def test_scan_latest_identity_findings_carry_jwt():
    from sqlalchemy.orm import sessionmaker

    try:
        from fastapi.testclient import TestClient

        from quirk.dashboard.api.app import create_app
        from quirk.dashboard.api.deps import get_db
    except ImportError:
        pytest.skip("Dashboard dependencies not available")
    from tests.conftest import make_isolated_memory_engine

    engine = make_isolated_memory_engine()
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    run_id = "2026-11-16T12:00:00"
    db = Session()
    try:
        for jwk, bits, _title, _sev in WEAK_KEYS.values():
            db.add(_jwt_row(_JWKS_HOST, jwk, bits, id=None, scan_run_id=run_id))
        db.commit()
    finally:
        db.close()
    try:
        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200, resp.text
        jwt_entries = [
            f for f in resp.json().get("identity_findings", []) if f["protocol"] == "JWT"
        ]
        assert len(jwt_entries) == 4
        assert {f["source"] for f in jwt_entries} == {"jwt"}
        assert sorted(f["algorithm"] for f in jwt_entries) == ["HS256", "HS256", "RS256", "none"]
    finally:
        engine.dispose()
