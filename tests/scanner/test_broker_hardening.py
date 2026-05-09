"""Tests for Phase 57 / CR-05, CR-06 / HARDEN-SCAN-05, HARDEN-SCAN-06."""
import base64
import os
from unittest.mock import patch, MagicMock
import pytest

from quirk.config import SecurityCfg, BrokerCredential
from quirk.scanner.broker_scanner import (
    _enrich_rabbitmq_mgmt,
    _enrich_redis_config,
    scan_rabbitmq_targets,
    ADVISORY_BROKER_CLEARTEXT,
    ADVISORY_BROKER_CREDENTIAL,
)


def test_no_hardcoded_guest_credentials_in_module():
    import pathlib
    import quirk.scanner.broker_scanner as mod
    src = pathlib.Path(mod.__file__).read_text()
    assert "guest:guest" not in src, "guest:guest literal found in broker_scanner.py"


def test_default_no_http_probe():
    with patch("quirk.scanner.broker_scanner.urllib.request.urlopen") as mock_urlopen:
        result = _enrich_rabbitmq_mgmt("rabbit.example", 15672)
        mock_urlopen.assert_not_called()
        assert result == {}


def test_cleartext_optin_anonymous_probe():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"rabbitmq_version": "3.12"}'
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda self, *args: None
    with patch("quirk.scanner.broker_scanner.urllib.request.urlopen",
               return_value=mock_resp) as mock_urlopen:
        _enrich_rabbitmq_mgmt("rabbit.example", 15672, allow_cleartext=True)
        assert mock_urlopen.call_count == 1
        req = mock_urlopen.call_args.args[0]
        # No Authorization header in anonymous probe
        headers_lower = {k.lower(): v for k, v in req.headers.items()}
        assert "authorization" not in headers_lower


def test_cleartext_optin_with_credentials_sends_auth(monkeypatch):
    monkeypatch.setenv("TEST_BROKER_PASS", "secret123")
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{}'
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda self, *args: None
    with patch("quirk.scanner.broker_scanner.urllib.request.urlopen",
               return_value=mock_resp) as mock_urlopen:
        _enrich_rabbitmq_mgmt(
            "rabbit.example", 15672,
            credentials={"user": "admin", "pass_env": "TEST_BROKER_PASS"},
            allow_cleartext=True,
        )
        req = mock_urlopen.call_args.args[0]
        headers_lower = {k.lower(): v for k, v in req.headers.items()}
        auth = headers_lower.get("authorization")
        assert auth is not None, "No Authorization header sent when credentials provided"
        assert auth.startswith("Basic ")
        decoded = base64.b64decode(auth.split(" ", 1)[1]).decode()
        assert decoded == "admin:secret123"


def test_credentials_with_unset_env_falls_back_anonymous(monkeypatch):
    monkeypatch.delenv("TEST_UNSET_PASS", raising=False)
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{}'
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda self, *args: None
    with patch("quirk.scanner.broker_scanner.urllib.request.urlopen",
               return_value=mock_resp) as mock_urlopen:
        _enrich_rabbitmq_mgmt(
            "rabbit.example", 15672,
            credentials={"user": "admin", "pass_env": "TEST_UNSET_PASS"},
            allow_cleartext=True,
        )
        req = mock_urlopen.call_args.args[0]
        headers_lower = {k.lower(): v for k, v in req.headers.items()}
        assert "authorization" not in headers_lower


def test_redis_default_ssl_cert_reqs_required():
    with patch("quirk.scanner.broker_scanner.redis_lib.Redis") as mock_redis_cls:
        mock_redis_cls.return_value.config_get.return_value = {}
        _enrich_redis_config("redis.example", 6380)
        kwargs = mock_redis_cls.call_args.kwargs
        assert kwargs.get("ssl_cert_reqs") == "required", (
            f"Expected ssl_cert_reqs='required' by default, got {kwargs.get('ssl_cert_reqs')!r}"
        )


def test_redis_cleartext_optin_uses_none():
    with patch("quirk.scanner.broker_scanner.redis_lib.Redis") as mock_redis_cls:
        mock_redis_cls.return_value.config_get.return_value = {}
        _enrich_redis_config("redis.example", 6380, allow_cleartext=True)
        kwargs = mock_redis_cls.call_args.kwargs
        assert kwargs.get("ssl_cert_reqs") == "none"


def test_scan_rabbitmq_targets_emits_cleartext_advisory():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{}'
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda self, *args: None
    sec = SecurityCfg(allow_cleartext_broker_probe=True)
    with patch("quirk.scanner.broker_scanner.urllib.request.urlopen",
               return_value=mock_resp):
        endpoints = scan_rabbitmq_targets(
            hosts=["rabbit.example"],
            timeout=5,
            security=sec,
            broker_credentials={},
        )
        advisories = [
            e for e in endpoints
            if getattr(e, "service_detail", "") == ADVISORY_BROKER_CLEARTEXT
        ]
        assert len(advisories) == 1, (
            f"Expected 1 cleartext advisory, got {len(advisories)}"
        )
        assert advisories[0].severity == "HIGH"


def test_scan_rabbitmq_targets_emits_credential_advisory(monkeypatch):
    monkeypatch.setenv("TEST_LAB_PASS", "secret123")
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{}'
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda self, *args: None
    sec = SecurityCfg(allow_cleartext_broker_probe=True)
    creds = {
        "rabbit.example:15672": BrokerCredential(user="admin", pass_env="TEST_LAB_PASS")
    }
    with patch("quirk.scanner.broker_scanner.urllib.request.urlopen",
               return_value=mock_resp):
        endpoints = scan_rabbitmq_targets(
            hosts=["rabbit.example"],
            timeout=5,
            security=sec,
            broker_credentials=creds,
        )
        advisories = [
            e for e in endpoints
            if getattr(e, "service_detail", "") == ADVISORY_BROKER_CREDENTIAL
        ]
        assert len(advisories) == 1, (
            f"Expected 1 credential-probe advisory, got {len(advisories)}"
        )


def test_scan_rabbitmq_targets_default_no_advisories():
    endpoints = scan_rabbitmq_targets(
        hosts=["rabbit.example"],
        timeout=5,
        security=SecurityCfg(),
        broker_credentials={},
    )
    advisories = [
        e for e in endpoints
        if getattr(e, "protocol", "") == "ADVISORY"
    ]
    assert advisories == [], (
        f"Expected no advisories by default, got {advisories}"
    )
