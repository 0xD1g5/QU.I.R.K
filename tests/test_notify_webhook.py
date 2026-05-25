"""Tests for quirk.notify.channels.webhook — Phase 101 NOTIFY-05, ISEC-01.

TDD: RED → GREEN cycle.  Tests written first, then implementation.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import urllib.request

import pytest

from quirk.notify.config import WebhookNotifyCfg


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cfg(
    url_env: str = "QUIRK_WEBHOOK_URL",
    hmac_key_env: str | None = None,
    timeout_seconds: int = 10,
) -> WebhookNotifyCfg:
    return WebhookNotifyCfg(
        url_env=url_env,
        hmac_key_env=hmac_key_env,
        timeout_seconds=timeout_seconds,
    )


def _make_payload() -> dict:
    """A realistic to_integration_payload()-style dict (no host/port/protocol)."""
    return {
        "current_score": 70,
        "previous_score": 80,
        "score_delta": -10,
        "new_high": 2,
        "new_medium": 1,
        "new_low": 0,
        "resolved_high": 0,
        "resolved_medium": 0,
        "resolved_low": 0,
        "scan_errors_new_count": 0,
        "current_session_ts": "2026-05-25T00:00:00",
        "previous_session_ts": "2026-05-24T00:00:00",
    }


class _FakeHTTPResponse:
    """Minimal mock of the context-manager returned by urlopen."""

    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return b"ok"


# ---------------------------------------------------------------------------
# ValueError when URL env var is unset
# ---------------------------------------------------------------------------


def test_raises_when_url_env_unset(monkeypatch):
    """send_webhook raises ValueError when the URL env var is not set."""
    from quirk.notify.channels.webhook import send_webhook

    monkeypatch.delenv("QUIRK_WEBHOOK_URL", raising=False)

    with pytest.raises(ValueError, match="QUIRK_WEBHOOK_URL"):
        send_webhook(cfg=_make_cfg(), payload=_make_payload())


# ---------------------------------------------------------------------------
# ISEC-01: SSRF — loopback / metadata IP raises ValueError
# ---------------------------------------------------------------------------


def test_ssrf_loopback_raises_value_error(monkeypatch):
    """ISEC-01: A loopback webhook URL raises ValueError."""
    from quirk.notify.channels.webhook import send_webhook

    monkeypatch.setenv("QUIRK_WEBHOOK_URL", "https://127.0.0.1/webhook")
    with pytest.raises(ValueError, match="SSRF"):
        send_webhook(cfg=_make_cfg(), payload=_make_payload())


def test_ssrf_metadata_ip_raises_value_error(monkeypatch):
    """ISEC-01: A cloud metadata IP webhook URL raises ValueError."""
    from quirk.notify.channels.webhook import send_webhook

    monkeypatch.setenv("QUIRK_WEBHOOK_URL", "https://169.254.169.254/webhook")
    with pytest.raises(ValueError, match="SSRF"):
        send_webhook(cfg=_make_cfg(), payload=_make_payload())


# ---------------------------------------------------------------------------
# Happy path without HMAC: timeout passed, no signature header
# ---------------------------------------------------------------------------


def test_no_hmac_when_key_env_not_set(monkeypatch):
    """When hmac_key_env is None, no X-QUIRK-Signature header is added."""
    from quirk.notify.channels.webhook import send_webhook

    captured_requests = []

    def _fake_urlopen(req, timeout=None):
        captured_requests.append({"req": req, "timeout": timeout})
        return _FakeHTTPResponse(200)

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setenv("QUIRK_WEBHOOK_URL", "https://hooks.example.com/notify")

    send_webhook(cfg=_make_cfg(hmac_key_env=None, timeout_seconds=12), payload=_make_payload())

    assert len(captured_requests) == 1, "urlopen must be called exactly once"
    req = captured_requests[0]["req"]
    assert captured_requests[0]["timeout"] == 12, \
        f"Expected timeout=12, got {captured_requests[0]['timeout']}"
    assert req.get_header("X-quirk-signature") is None, \
        "X-QUIRK-Signature must NOT be present when no HMAC key is configured"


# ---------------------------------------------------------------------------
# HMAC signing: header present and correct when key is set
# ---------------------------------------------------------------------------


def test_hmac_header_present_when_key_set(monkeypatch):
    """When hmac_key_env is set and non-empty, X-QUIRK-Signature is added and correct."""
    from quirk.notify.channels.webhook import send_webhook

    captured_requests = []

    def _fake_urlopen(req, timeout=None):
        captured_requests.append({"req": req, "timeout": timeout})
        return _FakeHTTPResponse(200)

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setenv("QUIRK_WEBHOOK_URL", "https://hooks.example.com/notify")
    monkeypatch.setenv("QUIRK_HMAC_KEY", "super-secret-key")

    payload = _make_payload()
    send_webhook(
        cfg=_make_cfg(hmac_key_env="QUIRK_HMAC_KEY", timeout_seconds=10),
        payload=payload,
    )

    assert len(captured_requests) == 1
    req = captured_requests[0]["req"]

    # urllib capitalises first letter of header names in get_header
    sig_header = req.get_header("X-quirk-signature")
    assert sig_header is not None, "X-QUIRK-Signature header must be present when key is set"
    assert sig_header.startswith("sha256="), \
        f"Header must start with 'sha256=', got: {sig_header}"

    # Verify the HMAC is correct
    key = b"super-secret-key"
    body = json.dumps(payload).encode("utf-8")
    expected_sig = "sha256=" + hmac.new(key, body, hashlib.sha256).hexdigest()
    assert sig_header == expected_sig, \
        f"HMAC mismatch. Expected {expected_sig}, got {sig_header}"


# ---------------------------------------------------------------------------
# HMAC absent when key env var is set but empty
# ---------------------------------------------------------------------------


def test_hmac_absent_when_key_env_empty(monkeypatch):
    """When hmac_key_env is set but the env var is empty, no signature header."""
    from quirk.notify.channels.webhook import send_webhook

    captured_requests = []

    def _fake_urlopen(req, timeout=None):
        captured_requests.append({"req": req, "timeout": timeout})
        return _FakeHTTPResponse(200)

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setenv("QUIRK_WEBHOOK_URL", "https://hooks.example.com/notify")
    monkeypatch.setenv("QUIRK_HMAC_KEY", "")  # empty — no signing

    send_webhook(
        cfg=_make_cfg(hmac_key_env="QUIRK_HMAC_KEY"),
        payload=_make_payload(),
    )

    req = captured_requests[0]["req"]
    assert req.get_header("X-quirk-signature") is None, \
        "No X-QUIRK-Signature when key env var is empty"


# ---------------------------------------------------------------------------
# Body contains no topology keys (ISEC-03)
# ---------------------------------------------------------------------------


def test_body_omits_topology_keys(monkeypatch):
    """The POST body must not contain 'host', 'port', or 'protocol' keys."""
    from quirk.notify.channels.webhook import send_webhook

    captured_bodies = []

    def _fake_urlopen(req, timeout=None):
        captured_bodies.append(req.data)
        return _FakeHTTPResponse(200)

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setenv("QUIRK_WEBHOOK_URL", "https://hooks.example.com/notify")

    payload = _make_payload()
    send_webhook(cfg=_make_cfg(), payload=payload)

    body_dict = json.loads(captured_bodies[0])
    topology_keys = {"host", "port", "protocol"}
    found = topology_keys.intersection(body_dict.keys())
    assert not found, f"Body must not contain topology keys; found: {found}"


# ---------------------------------------------------------------------------
# Non-2xx response raises RuntimeError
# ---------------------------------------------------------------------------


def test_non_2xx_raises_runtime_error(monkeypatch):
    """A non-2xx HTTP response from the webhook raises RuntimeError."""
    from quirk.notify.channels.webhook import send_webhook

    def _fake_urlopen(req, timeout=None):
        return _FakeHTTPResponse(500)

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setenv("QUIRK_WEBHOOK_URL", "https://hooks.example.com/notify")

    with pytest.raises(RuntimeError, match="500"):
        send_webhook(cfg=_make_cfg(), payload=_make_payload())


# ---------------------------------------------------------------------------
# Source-level assertion: X-QUIRK-Signature and timeout appear in source
# ---------------------------------------------------------------------------


def test_source_has_signature_header_and_timeout():
    """Acceptance: webhook.py contains X-QUIRK-Signature and at least 1 timeout=."""
    import pathlib

    src = pathlib.Path(__file__).parent.parent / "quirk" / "notify" / "channels" / "webhook.py"
    text = src.read_text(encoding="utf-8")
    assert "X-QUIRK-Signature" in text, "webhook.py must contain X-QUIRK-Signature"
    assert "timeout=" in text, "webhook.py must contain timeout="


# ---------------------------------------------------------------------------
# CR-01 regression: 302 redirect must NOT be followed (SSRF guard)
# ---------------------------------------------------------------------------


def test_redirect_blocked_by_no_redirect_handler(monkeypatch):
    """CR-01 regression: a 302 redirect from the webhook endpoint raises HTTPError.

    The _NoRedirectHandler installed by send_webhook must refuse any 3xx redirect
    rather than following it.  This prevents a post-validation SSRF bypass where
    a compromised CDN could redirect to http://169.254.169.254/.
    """
    import urllib.error
    from quirk.notify.channels.webhook import send_webhook, _NoRedirectHandler

    # Confirm _NoRedirectHandler raises on redirect_request
    handler = _NoRedirectHandler()

    class _FakeReq:
        full_url = "https://hooks.example.com/notify"

    class _FakeHeaders:
        pass

    with pytest.raises(urllib.error.HTTPError) as exc_info:
        handler.redirect_request(
            _FakeReq(), fp=None, code=302, msg="Found",
            headers=_FakeHeaders(), newurl="http://169.254.169.254/latest/meta-data/"
        )

    assert exc_info.value.code == 302
    assert "Redirect blocked" in exc_info.value.reason
