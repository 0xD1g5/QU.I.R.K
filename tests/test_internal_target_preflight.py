"""GET /api/config/internal-target-check -- 235.3 D-11 / P-12."""
from __future__ import annotations

import json
import socket

import pytest

from quirk.dashboard.api.routes.config import classify_internal_targets
from tests.test_config_effective_route import _app_with_db

URL = "/api/config/internal-target-check"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(tmp_path / "absent.yaml"))
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()
    return tc


def _conn(**kw):
    return {"connectors": json.dumps(kw)}


def test_401_without_token_200_with_token(monkeypatch, tmp_path):
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(tmp_path / "absent.yaml"))
    monkeypatch.setenv("QUIRK_API_TOKEN", "tok")
    _, tc = _app_with_db()
    assert tc.get(URL).status_code == 401
    assert tc.get(URL, headers={"Authorization": "Bearer tok"}).status_code == 200


def test_policy_false_reports_three_fields(client):
    r = client.get(
        URL,
        params={
            "targets": "127.0.0.1",
            **_conn(
                jwt_targets=["http://localhost:20001"],
                saml_targets=["http://10.1.2.3/md"],
            ),
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["allow_internal_targets"] is False
    got = [(e["field"], e["reason"]) for e in body["internal"]]
    assert got == [
        ("targets", "loopback"),
        ("jwt_targets", "loopback"),
        ("saml_targets", "internal_ip"),
    ]


def test_policy_true_reports_nothing(monkeypatch, tmp_path):
    cfg = tmp_path / "server.yaml"
    cfg.write_text("security:\n  allow_internal_targets: true\n")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(cfg))
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()
    r = tc.get(URL, params={"targets": "127.0.0.1"})
    assert r.status_code == 200
    assert r.json()["allow_internal_targets"] is True
    assert r.json()["internal"] == []


def test_unreadable_config_is_warning_not_503(monkeypatch, tmp_path):
    cfg = tmp_path / "server.yaml"
    cfg.write_text("security:\n  allow_internal_targets: true\n bad: [\n")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(cfg))
    monkeypatch.setenv("QUIRK_API_TOKEN", "env-token")
    _, tc = _app_with_db()
    r = tc.get(URL, params={"targets": "127.0.0.1"}, headers={"Authorization": "Bearer env-token"})
    assert r.status_code == 200
    assert r.json()["config_error"]
    assert r.json()["internal"] == []


def test_metadata_is_not_internal(client):
    r = client.get(URL, params=_conn(jwt_targets=["http://169.254.169.254/"]))
    assert r.status_code == 200
    assert r.json()["internal"] == []


def test_cidr_and_public(client):
    r = client.get(URL, params={"targets": "10.0.0.0/8, 8.8.8.8"})
    got = [(e["preview"], e["reason"]) for e in r.json()["internal"]]
    assert got == [("10.0.0.0/8", "internal_ip")]


def test_name_resolving_internal(client, monkeypatch):
    def fake(host, port, family=0, *a, **k):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0))]

    monkeypatch.setattr("quirk.util.url_allowlist.socket.getaddrinfo", fake)
    r = client.get(URL, params={"targets": "sso.corp.internal"})
    assert [e["reason"] for e in r.json()["internal"]] == ["internal_ip"]


def test_client_allow_internal_query_ignored(client):
    r = client.get(
        URL, params={"targets": "127.0.0.1", "allow_internal_targets": "true"}
    )
    assert r.json()["allow_internal_targets"] is False
    assert len(r.json()["internal"]) == 1


def test_bounds_truncates_at_64(client):
    targets = ",".join(f"10.0.0.{i}" for i in range(100))
    r = client.get(URL, params={"targets": targets})
    body = r.json()
    assert body["truncated"] is True
    assert len(body["internal"]) == 64


def test_classify_limit_helper():
    entries, trunc = classify_internal_targets({"targets": ["127.0.0.1"] * 5}, limit=3)
    assert trunc is True and len(entries) == 3


def test_preview_is_redacted(client):
    r = client.get(URL, params=_conn(jwt_targets=["http://u:p@localhost:1/x?tok=1"]))
    prev = r.json()["internal"][0]["preview"]
    assert "u:p" not in prev and "tok" not in prev


def test_bad_connectors_json_422(client):
    assert client.get(URL, params={"connectors": "{nope"}).status_code == 422


def test_route_not_on_unauthenticated_router():
    import quirk.dashboard.api.routes.config as m

    assert not any(
        getattr(r, "path", "").endswith("internal-target-check") for r in m.router.routes
    )
