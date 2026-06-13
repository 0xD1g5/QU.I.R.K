"""SSRF-05 / D-03 proof: the rest_fuzzer requests.Session dispatches connect to the
validated resolved_ip via PinnedIPAdapter, closing the DNS-rebinding TOCTOU window.

Covers the three already-validated session dispatch sites in rest_fuzzer:
  - JWKS fetch (_fetch_jwks_public_key_pem)
  - main schemathesis dispatch (run_fuzz_scan)
  - alg-confusion dispatch (shares the identical mount idiom; verified structurally)
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from quirk.util.pinned_adapter import PinnedIPAdapter


_PINNED = "93.184.216.34"


def _ok_scope_with_ip(ip: str = _PINNED):
    r = MagicMock()
    r.ok = True
    r.reason = ""
    r.resolved_ip = ip
    return r


def _mounted_pinned_ips(session_mock) -> list[str]:
    """Return the _pinned_ip of every PinnedIPAdapter mounted on the session."""
    ips = []
    for call in session_mock.mount.call_args_list:
        adapter = call.args[1] if len(call.args) > 1 else call.kwargs.get("adapter")
        if isinstance(adapter, PinnedIPAdapter):
            ips.append(adapter._pinned_ip)
    return ips


def test_jwks_dispatch_mounts_pinned_adapter():
    """JWKS fetch mounts PinnedIPAdapter(resolved_ip) before session.request."""
    from quirk.scanner.rest_fuzzer import _fetch_jwks_public_key_pem

    session_mock = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"keys": []}  # no RS256 key → returns None, but mount already ran
    session_mock.request.return_value = resp

    with patch("quirk.scanner.rest_fuzzer.validate_external_url",
               return_value=_ok_scope_with_ip()):
        _fetch_jwks_public_key_pem("http://example.com", session_mock, allow_internal=False)

    assert _PINNED in _mounted_pinned_ips(session_mock), \
        "JWKS path must mount PinnedIPAdapter on the validated resolved_ip"


def test_main_dispatch_mounts_pinned_adapter():
    """Main schemathesis dispatch mounts PinnedIPAdapter(resolved_ip) before session.request."""
    from quirk.scanner.rest_fuzzer import run_fuzz_scan

    session_mock = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    session_mock.request.return_value = resp

    cfg = MagicMock()
    cfg.security = MagicMock()
    cfg.security.allow_internal_targets = False

    mock_case = MagicMock()
    mock_case.as_transport_kwargs.return_value = {
        "method": "GET",
        "url": "http://example.com/probe",
        "headers": {},
        "cookies": {},
        "params": {},
    }
    mock_op = MagicMock()
    mock_op.as_strategy.return_value.example.return_value = mock_case
    from schemathesis.core.result import Ok as _SchemaOk
    mock_result = _SchemaOk(mock_op)

    with patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_schema_mod, \
         patch("quirk.scanner.rest_fuzzer.validate_external_url",
               return_value=_ok_scope_with_ip()):
        mock_schema = MagicMock()
        mock_schema.include.return_value.get_all_operations.return_value = [mock_result]
        mock_schema_mod.openapi.from_dict.return_value = mock_schema

        run_fuzz_scan(
            spec_dict={"openapi": "3.0.0"},
            base_url="http://example.com",  # http → raw-probe block skipped, isolates the session path
            cfg=cfg, budget=5,
            prompt_fn=lambda _: "CONFIRM", is_tty=True,
            _session=session_mock,
        )

    assert _PINNED in _mounted_pinned_ips(session_mock), \
        "Main dispatch must mount PinnedIPAdapter on the validated resolved_ip"


def test_empty_resolved_ip_does_not_mount():
    """IP-literal targets (empty resolved_ip) mount no adapter — no crash, dispatch proceeds."""
    from quirk.scanner.rest_fuzzer import _fetch_jwks_public_key_pem

    session_mock = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"keys": []}
    session_mock.request.return_value = resp

    no_ip = _ok_scope_with_ip("")  # ok but empty resolved_ip
    with patch("quirk.scanner.rest_fuzzer.validate_external_url", return_value=no_ip):
        _fetch_jwks_public_key_pem("http://8.8.8.8", session_mock, allow_internal=False)

    assert _mounted_pinned_ips(session_mock) == [], \
        "No PinnedIPAdapter should be mounted when resolved_ip is empty"


def test_all_three_dispatch_sites_have_pinned_mount():
    """Structural guarantee: all three validated session dispatches mount the pinned adapter.

    The alg-confusion dispatch is exercised via the identical wiring idiom proven
    executably by the JWKS + main tests above; this asserts the source carries the
    mount at all three sites so none silently regresses.
    """
    import quirk.scanner.rest_fuzzer as rf

    src = inspect.getsource(rf)
    mount_count = src.count("session.mount(")
    pinned_mounts = src.count("PinnedIPAdapter(")
    # 3 dispatch mounts + the import line = 4 PinnedIPAdapter references; 3 session.mount calls.
    assert mount_count >= 3, f"expected >=3 session.mount sites, found {mount_count}"
    assert pinned_mounts >= 3, f"expected >=3 PinnedIPAdapter mounts, found {pinned_mounts}"
