"""Unit tests for quirk.ticketing.servicenow — ServiceNowChannel (Phase 105 TICKET-02/TICKET-04).

Covers:
  - test_create_incident: POST creates incident, returns sys_id
  - test_dedup_then_work_notes: second scan finds existing sys_id, PATCHes work_notes
  - test_correlation_id_is_fingerprint: correlation_id in POST body equals compute_fingerprint()
  - test_http_instance_url_rejected: http:// instance_url rejected at config parse
  - test_missing_instance_url: missing instance_url → _parse_servicenow_cfg returns None
  - test_missing_env_fields_rejected: empty user_env → _parse_servicenow_cfg returns None
  - test_https_valid_config: valid https + env names → ServiceNowTicketingCfg with table="incident"
  - test_ssrf_guard: internal/loopback instance_url → ValueError at __init__
  - test_credentials_not_in_logs: Basic auth in HTTPError → absent from error_summary (safe_str)
"""
from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_cfg(
    instance_url: str = "https://myco.service-now.com",
    user_env: str = "QUIRK_SNOW_USER",
    password_env: str = "QUIRK_SNOW_PASSWORD",
    table: str = "incident",
    allow_internal: bool = False,
):
    """Build a ServiceNowTicketingCfg with defaults suitable for unit tests."""
    from quirk.ticketing.config import ServiceNowTicketingCfg  # noqa: PLC0415

    return ServiceNowTicketingCfg(
        instance_url=instance_url,
        user_env=user_env,
        password_env=password_env,
        table=table,
        allow_internal=allow_internal,
    )


def _sample_finding() -> dict:
    return {
        "title": "Weak TLS cipher",
        "severity": "HIGH",
        "host": "example.com",
        "port": "443",
        "description": "TLS 1.0 accepted",
        "recommendation": "Disable TLS 1.0",
    }


class _FakeHTTPResponse:
    """Minimal mock of context-manager returned by opener.open()."""

    def __init__(self, status: int = 201, body: dict | None = None):
        self.status = status
        self._body = body or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return json.dumps(self._body).encode("utf-8")


class _FakeOpener:
    """Fake opener returned by build_opener; intercepts opener.open() calls."""

    def __init__(self, callback):
        self._callback = callback

    def open(self, req, timeout=None):
        return self._callback(req, timeout=timeout)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_incident(monkeypatch: pytest.MonkeyPatch) -> None:
    """First scan: POST creates incident, returns sys_id (not INC-number).

    Covers TICKET-02: a ServiceNow incident is created per finding with QRAMM evidence
    and correlation_id equal to the SHA256 fingerprint.
    """
    monkeypatch.setenv("QUIRK_SNOW_USER", "admin")
    monkeypatch.setenv("QUIRK_SNOW_PASSWORD", "secret")

    cfg = _make_cfg()
    finding = _sample_finding()

    from quirk.ticketing.servicenow import ServiceNowChannel  # noqa: PLC0415

    fake_sys_id = "a" * 32
    response_body = {"result": {"sys_id": fake_sys_id, "number": "INC0000042"}}
    captured = []

    def _fake_open(req, timeout=None):
        captured.append(req)
        return _FakeHTTPResponse(status=201, body=response_body)

    with patch(
        "quirk.ticketing.servicenow.urllib.request.build_opener",
        return_value=_FakeOpener(_fake_open),
    ):
        channel = ServiceNowChannel(cfg)
        fp = channel.compute_fingerprint(finding)
        evidence = channel.build_ticket_evidence(finding)
        result = channel.create_issue_from_finding(finding, fp, evidence)

    assert result == fake_sys_id
    assert captured[0].method == "POST"
    body = json.loads(captured[0].data)
    assert body["correlation_id"] == fp
    assert body["short_description"] == "Weak TLS cipher"


def test_dedup_then_work_notes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """Two dispatch_finding calls with same finding: POST once, PATCH work_notes on second.

    Covers TICKET-02 dedup: GET finds existing sys_id → PATCH adds work_notes,
    no duplicate incident created.
    """
    monkeypatch.setenv("QUIRK_SNOW_USER", "admin")
    monkeypatch.setenv("QUIRK_SNOW_PASSWORD", "secret")

    from quirk.ticketing.servicenow import ServiceNowChannel  # noqa: PLC0415

    cfg = _make_cfg()
    finding = _sample_finding()

    fake_sys_id = "b" * 32
    captured_requests = []

    def _fake_open_first(req, timeout=None):
        captured_requests.append(req)
        if req.method == "GET":
            return _FakeHTTPResponse(status=200, body={"result": []})
        # POST
        return _FakeHTTPResponse(
            status=201, body={"result": {"sys_id": fake_sys_id, "number": "INC0000001"}}
        )

    def _fake_open_second(req, timeout=None):
        captured_requests.append(req)
        if req.method == "GET":
            return _FakeHTTPResponse(
                status=200, body={"result": [{"sys_id": fake_sys_id}]}
            )
        # PATCH
        return _FakeHTTPResponse(
            status=200, body={"result": {"sys_id": fake_sys_id}}
        )

    db_path = str(tmp_path / "test.db")
    from quirk.db import get_session, init_db  # noqa: PLC0415

    init_db(db_path)

    # First dispatch_finding
    with patch(
        "quirk.ticketing.servicenow.urllib.request.build_opener",
        return_value=_FakeOpener(_fake_open_first),
    ):
        channel = ServiceNowChannel(cfg)
        with get_session(db_path) as db:
            channel.dispatch_finding(finding, db, "scan-001")

    post_count_after_first = sum(1 for r in captured_requests if r.method == "POST")
    assert post_count_after_first == 1, "POST must be called once on first dispatch"

    # Second dispatch_finding
    with patch(
        "quirk.ticketing.servicenow.urllib.request.build_opener",
        return_value=_FakeOpener(_fake_open_second),
    ):
        with get_session(db_path) as db:
            channel.dispatch_finding(finding, db, "scan-002")

    post_count_total = sum(1 for r in captured_requests if r.method == "POST")
    patch_count_total = sum(1 for r in captured_requests if r.method == "PATCH")

    assert post_count_total == 1, "POST must not be called again on second dispatch"
    assert patch_count_total == 1, "PATCH must be called exactly once on second dispatch"

    # Verify the PATCH request body contains work_notes
    patch_req = next(r for r in captured_requests if r.method == "PATCH")
    assert patch_req.method == "PATCH"
    patch_body = json.loads(patch_req.data)
    assert "work_notes" in patch_body


def test_correlation_id_is_fingerprint(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST body correlation_id equals base TicketingChannel.compute_fingerprint(finding).

    Covers TICKET-04 cross-backend identity: fingerprint formula is SHA256(host:port::title)
    from the inherited staticmethod — never a ServiceNow-local hash.
    """
    monkeypatch.setenv("QUIRK_SNOW_USER", "admin")
    monkeypatch.setenv("QUIRK_SNOW_PASSWORD", "secret")

    from quirk.ticketing.base import TicketingChannel  # noqa: PLC0415
    from quirk.ticketing.servicenow import ServiceNowChannel  # noqa: PLC0415

    cfg = _make_cfg()
    finding = _sample_finding()

    # Compute expected fingerprint via the base class staticmethod directly
    expected_fp = TicketingChannel.compute_fingerprint(finding)

    fake_sys_id = "c" * 32
    response_body = {"result": {"sys_id": fake_sys_id, "number": "INC0000099"}}
    captured = []

    def _fake_open(req, timeout=None):
        captured.append(req)
        return _FakeHTTPResponse(status=201, body=response_body)

    with patch(
        "quirk.ticketing.servicenow.urllib.request.build_opener",
        return_value=_FakeOpener(_fake_open),
    ):
        channel = ServiceNowChannel(cfg)
        fp = channel.compute_fingerprint(finding)
        evidence = channel.build_ticket_evidence(finding)
        channel.create_issue_from_finding(finding, fp, evidence)

    body = json.loads(captured[0].data)
    assert body["correlation_id"] == expected_fp, (
        f"correlation_id {body['correlation_id']!r} != base fingerprint {expected_fp!r}"
    )


def test_http_instance_url_rejected() -> None:
    """http:// instance_url must be rejected by _parse_servicenow_cfg (cleartext Basic auth guard).

    Covers TICKET-02 security criterion: http:// instance_url rejected at parse (returns None).
    """
    from quirk.ticketing.config import _parse_servicenow_cfg  # noqa: PLC0415

    raw = {
        "instance_url": "http://myco.service-now.com",
        "user_env": "U",
        "password_env": "P",
    }
    assert _parse_servicenow_cfg(raw) is None


def test_missing_instance_url() -> None:
    """Missing instance_url must be rejected by _parse_servicenow_cfg."""
    from quirk.ticketing.config import _parse_servicenow_cfg  # noqa: PLC0415

    raw = {"user_env": "U", "password_env": "P"}
    assert _parse_servicenow_cfg(raw) is None


def test_missing_env_fields_rejected() -> None:
    """Empty user_env must be rejected by _parse_servicenow_cfg."""
    from quirk.ticketing.config import _parse_servicenow_cfg  # noqa: PLC0415

    raw = {
        "instance_url": "https://myco.service-now.com",
        "user_env": "",
        "password_env": "P",
    }
    assert _parse_servicenow_cfg(raw) is None


def test_https_valid_config() -> None:
    """Valid https + env names produces ServiceNowTicketingCfg with table defaulting to 'incident'."""
    from quirk.ticketing.config import ServiceNowTicketingCfg, _parse_servicenow_cfg  # noqa: PLC0415

    raw = {
        "instance_url": "https://myco.service-now.com",
        "user_env": "QUIRK_SNOW_USER",
        "password_env": "QUIRK_SNOW_PASSWORD",
    }
    result = _parse_servicenow_cfg(raw)
    assert result is not None
    assert isinstance(result, ServiceNowTicketingCfg)
    assert result.table == "incident"
    assert result.allow_internal is False
    assert result.instance_url == "https://myco.service-now.com"


def test_ssrf_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Internal/loopback instance_url raises ValueError at ServiceNowChannel.__init__.

    Covers T-105-03: validate_external_url blocks RFC1918/loopback addresses.
    """
    monkeypatch.setenv("QUIRK_SNOW_USER", "u")
    monkeypatch.setenv("QUIRK_SNOW_PASSWORD", "p")

    from quirk.ticketing.servicenow import ServiceNowChannel  # noqa: PLC0415

    cfg = _make_cfg(instance_url="https://127.0.0.1/")
    with pytest.raises(ValueError, match="SSRF"):
        ServiceNowChannel(cfg)


def test_credentials_not_in_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """Exception embedding Basic auth must not appear in error_summary (safe_str enforcement).

    Covers T-105-01: safe_str scrubs Authorization: Basic + 40+ char base64 patterns.
    Plants a recognizable fake Basic auth credential string and asserts it is absent
    from the DB audit row error_summary.
    """
    monkeypatch.setenv("QUIRK_SNOW_USER", "admin")
    monkeypatch.setenv("QUIRK_SNOW_PASSWORD", "super_secret_password")

    from quirk.ticketing.servicenow import ServiceNowChannel  # noqa: PLC0415

    cfg = _make_cfg()
    finding = _sample_finding()

    # Plant a fake Basic auth header value (must be 40+ chars to trigger base64 scrubbing)
    fake_creds_b64 = "YWRtaW46c3VwZXJfc2VjcmV0X3Bhc3N3b3Jk"  # 38 chars — use longer
    fake_creds_b64 = "YWRtaW46c3VwZXJfc2VjcmV0X3Bhc3N3b3JkX2V4dHJh"  # 46 chars, valid base64
    assert len(fake_creds_b64) >= 40, "planted creds must be 40+ chars for safe_str scrubbing"
    planted_msg = f"Authorization: Basic {fake_creds_b64}"

    def _fake_open(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url,
            401,
            planted_msg,
            {},
            None,
        )

    with patch(
        "quirk.ticketing.servicenow.urllib.request.build_opener",
        return_value=_FakeOpener(_fake_open),
    ):
        channel = ServiceNowChannel(cfg)
        db_path = str(tmp_path / "creds_test.db")
        from quirk.db import get_session, init_db  # noqa: PLC0415
        from quirk.models import IntegrationDelivery  # noqa: PLC0415

        init_db(db_path)
        with get_session(db_path) as db:
            channel.dispatch_finding(finding, db, "scan-creds")

            rows = db.query(IntegrationDelivery).filter(
                IntegrationDelivery.destination == "servicenow"
            ).all()

    assert rows, "audit row must be written even on failure"
    row = rows[0]
    assert row.status == "failed"
    assert row.error_summary is not None
    # The planted credential substring must NOT appear in error_summary
    assert fake_creds_b64 not in row.error_summary, (
        f"Credential leaked into error_summary: {row.error_summary!r}"
    )
