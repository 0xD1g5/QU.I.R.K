"""POST /api/config/internal-target-check -- 235.3 D-11 / P-12.

C-WR-07: the route was a GET, so with auth in passthrough mode (no
QUIRK_API_TOKEN) any page the operator visited could make the server resolve
attacker-chosen names. It is now a CSRF-protected POST with a hostname cap
and a wall-clock deadline on DNS, and it skips values that are not a
syntactically complete host.
"""
from __future__ import annotations

import socket
import threading
import time

import pytest

from quirk.dashboard.api.routes.config import classify_internal_targets
from tests.test_config_effective_route import _app_with_db

URL = "/api/config/internal-target-check"
CSRF = {"X-Quirk-Request": "1"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(tmp_path / "absent.yaml"))
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()
    return tc


def _post(tc, headers=None, **connectors):
    return tc.post(URL, json={"connectors": connectors}, headers={**CSRF, **(headers or {})})


def _fake_resolver(monkeypatch, ip="10.0.0.5", gate=None):
    calls = []

    def fake(host, port, family=0, *a, **k):
        calls.append(host)
        if gate is not None:
            gate.wait(5)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    monkeypatch.setattr("quirk.util.url_allowlist.socket.getaddrinfo", fake)
    return calls


def test_401_without_token_200_with_token(monkeypatch, tmp_path):
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(tmp_path / "absent.yaml"))
    monkeypatch.setenv("QUIRK_API_TOKEN", "tok")
    _, tc = _app_with_db()
    assert tc.post(URL, json={}, headers=CSRF).status_code == 401
    r = tc.post(URL, json={}, headers={**CSRF, "Authorization": "Bearer tok"})
    assert r.status_code == 200


def test_get_does_not_run_the_preflight(client, monkeypatch):
    """C-WR-07: a GET can be fired cross-site by an <img> tag; it must not
    reach the preflight or the resolver. (The SPA catch-all answers any
    unmatched GET with index.html, so the status is not a 405.)"""
    calls = _fake_resolver(monkeypatch)
    r = client.get(
        URL, params={"connectors": '{"jwt_targets": ["https://a.evil.example/"]}'}
    )
    assert calls == []
    assert "allow_internal_targets" not in r.text


def test_post_without_csrf_header_is_403(client):
    r = client.post(URL, json={"connectors": {"jwt_targets": ["http://127.0.0.1/"]}})
    assert r.status_code == 403


def test_policy_false_reports_connector_fields(client):
    r = _post(
        client,
        jwt_targets=["http://localhost:20001"],
        saml_targets=["http://10.1.2.3/md"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["allow_internal_targets"] is False
    got = [(e["field"], e["reason"]) for e in body["internal"]]
    assert got == [
        ("jwt_targets", "loopback"),
        ("saml_targets", "internal_ip"),
    ]


def test_plain_targets_are_never_reported(client):
    """C-WR-01: allow_internal_targets gates only the JWT / SAML connector URL
    lists (run_scan.py). TLS / SSH plain targets are never refused, so the
    preflight must not claim a skip for them."""
    r = client.post(
        URL, json={"targets": "127.0.0.1, 10.0.0.5, localhost, 10.0.0.0/8"}, headers=CSRF
    )
    assert r.status_code == 200, r.text
    assert r.json()["internal"] == []


def test_policy_true_reports_nothing(monkeypatch, tmp_path):
    cfg = tmp_path / "server.yaml"
    cfg.write_text("security:\n  allow_internal_targets: true\n")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(cfg))
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()
    r = _post(tc, jwt_targets=["http://127.0.0.1/"])
    assert r.status_code == 200
    assert r.json()["allow_internal_targets"] is True
    assert r.json()["internal"] == []


def test_unreadable_config_is_warning_not_503(monkeypatch, tmp_path):
    cfg = tmp_path / "server.yaml"
    cfg.write_text("security:\n  allow_internal_targets: true\n bad: [\n")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(cfg))
    monkeypatch.setenv("QUIRK_API_TOKEN", "env-token")
    _, tc = _app_with_db()
    r = _post(
        tc,
        headers={"Authorization": "Bearer env-token"},
        jwt_targets=["http://127.0.0.1/"],
    )
    assert r.status_code == 200
    assert r.json()["config_error"]
    assert r.json()["internal"] == []


def test_metadata_is_not_internal(client):
    r = _post(client, jwt_targets=["http://169.254.169.254/"])
    assert r.status_code == 200
    assert r.json()["internal"] == []


def test_name_resolving_internal(client, monkeypatch):
    _fake_resolver(monkeypatch)
    r = _post(client, jwt_targets=["https://sso.corp.internal/"])
    assert [e["reason"] for e in r.json()["internal"]] == ["internal_ip"]


def test_client_allow_internal_field_ignored(client):
    r = client.post(
        URL,
        json={"connectors": {"jwt_targets": ["http://127.0.0.1/"]}, "allow_internal_targets": True},
        headers=CSRF,
    )
    assert r.json()["allow_internal_targets"] is False
    assert len(r.json()["internal"]) == 1


def test_bounds_truncates_at_value_limit(client):
    r = _post(client, jwt_targets=[f"http://10.0.0.{i}/" for i in range(100)])
    body = r.json()
    assert body["truncated"] is True
    assert len(body["internal"]) == 32


def test_classify_limit_helper():
    entries, trunc = classify_internal_targets({"jwt_targets": ["http://127.0.0.1/"] * 5}, limit=3)
    assert trunc is True and len(entries) == 3


def test_ip_literals_never_resolve(client, monkeypatch):
    calls = _fake_resolver(monkeypatch)
    r = _post(client, jwt_targets=[f"http://10.0.1.{i}/" for i in range(20)])
    assert calls == []
    assert len(r.json()["internal"]) == 20
    assert r.json()["truncated"] is False


def test_incomplete_hostnames_never_resolve(client, monkeypatch):
    """C-WR-07: a value typed half-way (debounce fires on a pause) must not
    leak a partial name to the resolver."""
    calls = _fake_resolver(monkeypatch)
    r = _post(
        client,
        jwt_targets=["http://loc", "https://sso", "https://a.example.c", "http://", "https://-x.corp"],
    )
    assert r.status_code == 200, r.text
    assert calls == []
    assert r.json()["internal"] == []


def test_dns_lookups_are_capped(client, monkeypatch):
    calls = _fake_resolver(monkeypatch)
    r = _post(client, jwt_targets=[f"https://h{i}.corp.example/" for i in range(40)])
    body = r.json()
    assert len(calls) == 16
    assert len(body["internal"]) == 16
    assert body["truncated"] is True


def test_dns_resolution_has_a_deadline(client, monkeypatch):
    """A hanging resolver must not hold the request: lookups past the
    deadline are abandoned and the answer says truncated."""
    import quirk.dashboard.api.routes.config as m

    gate = threading.Event()
    _fake_resolver(monkeypatch, gate=gate)
    monkeypatch.setattr(m, "_INTERNAL_CHECK_DEADLINE_S", 0.3)
    try:
        t0 = time.monotonic()
        r = _post(
            client,
            jwt_targets=["http://127.0.0.1/", "https://slow.corp.example/"],
        )
        elapsed = time.monotonic() - t0
    finally:
        gate.set()
    assert r.status_code == 200, r.text
    assert elapsed < 2.0
    body = r.json()
    assert body["truncated"] is True
    assert [e["preview"] for e in body["internal"]] == ["http://127.0.0.1/"]


def test_preview_is_redacted(client):
    r = _post(client, jwt_targets=["http://u:p@localhost:1/x?tok=1"])
    prev = r.json()["internal"][0]["preview"]
    assert "u:p" not in prev and "tok" not in prev


def test_bad_connectors_shape_422(client):
    r = client.post(URL, json={"connectors": ["not", "an", "object"]}, headers=CSRF)
    assert r.status_code == 422


def test_unknown_connector_key_422(client):
    r = _post(client, openapi_spec_path="http://localhost/spec.json")
    assert r.status_code == 422


def test_route_not_on_unauthenticated_router():
    import quirk.dashboard.api.routes.config as m

    assert not any(
        getattr(r, "path", "").endswith("internal-target-check") for r in m.router.routes
    )
