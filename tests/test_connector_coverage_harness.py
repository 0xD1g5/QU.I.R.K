"""Smoke tests for the shared Phase 235.3 harness (tests/connector_coverage_harness.py)."""
from __future__ import annotations

import os
import socket
import ssl
import urllib.error
import urllib.request

import pytest

from quirk.config import load_config
from tests import connector_coverage_harness as h


def test_build_config_loads_and_stays_under_tmp(tmp_path):
    path = h.build_config(tmp_path, {"connectors": {"enable_jwt": True, "jwt_targets": ["http://127.0.0.1:1"]}})
    cfg = load_config(path)
    assert cfg.connectors.enable_jwt is True
    assert cfg.connectors.jwt_targets == ["http://127.0.0.1:1"]
    assert cfg.output.db_path.startswith(str(tmp_path))
    assert str(cfg.output.directory).startswith(str(tmp_path))


def test_scrub_cloud_env_clears_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAFAKE")
    monkeypatch.setenv("AWS_PROFILE", "p")
    monkeypatch.setenv("AZURE_CLIENT_ID", "x")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/x")
    h.scrub_cloud_env(monkeypatch)
    for name in ("AWS_ACCESS_KEY_ID", "AWS_PROFILE", "AZURE_CLIENT_ID", "GOOGLE_APPLICATION_CREDENTIALS"):
        assert name not in os.environ
    assert os.environ["AWS_EC2_METADATA_DISABLED"] == "true"
    assert not os.path.exists(os.environ["AWS_CONFIG_FILE"])
    assert not os.path.exists(os.environ["AWS_SHARED_CREDENTIALS_FILE"])


def test_jwks_stub_serves_body_then_stops():
    with h.jwks_stub('{"keys": []}') as base:
        with urllib.request.urlopen(base + "/.well-known/jwks.json", timeout=5) as r:
            assert r.read() == b'{"keys": []}'
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/other", timeout=5)
    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen(base + "/.well-known/jwks.json", timeout=2)


def test_s3_stub_empty_list_and_xml_error():
    with h.s3_stub() as url:
        with urllib.request.urlopen(url + "/", timeout=5) as r:
            body = r.read().decode()
        assert "<ListAllMyBucketsResult" in body and "<Buckets/>" in body
    with h.s3_stub(status=403, code="InvalidAccessKeyId") as url:
        with pytest.raises(urllib.error.HTTPError) as ei:
            urllib.request.urlopen(url + "/", timeout=5)
        assert ei.value.code == 403
        assert b"<Code>InvalidAccessKeyId</Code>" in ei.value.read()


def test_tls_stub_completes_handshake_with_generated_cert(tmp_path):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with h.tls_stub(tmp_path) as port:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
            with ctx.wrap_socket(raw, server_hostname="127.0.0.1") as tls:
                assert tls.getpeercert(binary_form=True)
    pems = [p for p in os.listdir(tmp_path) if p.endswith(".pem")]
    assert pems  # generated under tmp, not committed


def test_closed_port_refuses_connection():
    port = h.closed_port()
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", port), timeout=2)


def test_quirk_output_snapshot_is_stable_listing():
    snap = h.quirk_output_snapshot()
    assert snap is None or isinstance(snap, list)
    assert h.quirk_output_snapshot() == snap


def test_phase_rows_empty_for_fresh_db(tmp_path):
    from quirk.db import init_db

    db = str(tmp_path / "q.db")
    init_db(db)
    assert h.phase_rows(db) == []


@pytest.mark.slow
def test_run_scan_in_process_records_unanswered_jwt_target_as_skipped(tmp_path, monkeypatch):
    """End-to-end smoke of the harness itself: one JWT target on a closed port."""
    h.scrub_cloud_env(monkeypatch)
    url = f"http://127.0.0.1:{h.closed_port()}"
    cfg_path = h.build_config(tmp_path, {
        "connectors": {"enable_jwt": True, "jwt_targets": [url]},
        "security": {"allow_internal_targets": True},
    })
    cfg = load_config(cfg_path)
    before = h.quirk_output_snapshot()
    h.run_scan_in_process(cfg_path, cfg.output.db_path)
    assert h.quirk_output_snapshot() == before
    rows = {r["phase_name"]: r for r in h.phase_rows(cfg.output.db_path)}
    assert rows["jwt_scanning"]["status"] == "skipped"
    assert rows["jwt_scanning"]["reason"] == "failed"
