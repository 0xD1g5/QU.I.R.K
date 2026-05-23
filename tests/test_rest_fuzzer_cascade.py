"""Regression tests for the REST fuzzer failure-cascade counter (TD-02 / D-06).

Phase 97 / TD-02 — WR-03 from 96-REVIEW
-----------------------------------------
These tests verify that the cascade back-off counter counts BOTH 5xx responses
AND connection/request exceptions toward the pause limit.

Prior to the D-06 fix, a connection exception (timeout, reset) reset the
consecutive counter to 0, so a server that only times out could never accumulate
the consecutive failures needed to trip the cascade pause — it escaped the back-off
entirely.

Three behaviors proven here:
1. Exception-only cascade: exception-on-every-dispatch trips the pause at
   _CONSECUTIVE_5XX_LIMIT — the loop breaks (does NOT run unbounded).
2. Success resets: a genuine success (2xx/3xx/<500, no exception) interleaved
   before the limit resets the failure counter so the cascade does NOT fire.
3. 5xx no-regression: N consecutive 5xx responses still trigger the pause —
   the 5xx behavior is preserved.

Design: inject a mock session via _session= parameter so tests never touch the
real network. schemathesis.openapi.from_dict is patched to avoid real OpenAPI
parsing; responses are controlled via side_effect sequences on session.request.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from quirk.scanner.rest_fuzzer import run_fuzz_scan, _CONSECUTIVE_5XX_LIMIT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Minimal response object returned by a mock session."""
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.headers: dict = {}


def _make_cfg(allow_internal: bool = True) -> MagicMock:
    """Return a minimal scan config accepted by run_fuzz_scan."""
    cfg = MagicMock()
    cfg.security = SimpleNamespace(allow_internal_targets=allow_internal)
    return cfg


def _make_spec() -> dict:
    """Return a minimal OpenAPI spec dict accepted by schemathesis."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "t", "version": "1"},
        "paths": {
            "/probe": {
                "get": {
                    "responses": {"200": {"description": "ok"}},
                },
            },
        },
    }


def _build_schema_mock(num_ops: int, url: str = "https://t.example.com/probe") -> MagicMock:
    """Build a schemathesis-compatible mock schema with num_ops operations."""
    from quirk.scanner.rest_fuzzer import _SchemaOk  # type: ignore[attr-defined]

    ops = []
    for _ in range(num_ops):
        result = MagicMock(spec=_SchemaOk)
        case = MagicMock()
        case.as_transport_kwargs.return_value = {
            "method": "GET",
            "url": url,
        }
        result.ok.return_value = MagicMock()
        result.ok.return_value.as_strategy.return_value.example.return_value = case
        ops.append(result)

    get_schema = MagicMock()
    get_schema.get_all_operations.return_value = iter(ops)

    schema = MagicMock()
    schema.include.return_value = get_schema

    return schema


# ---------------------------------------------------------------------------
# Test 1: exception-only cascade trips the pause
# ---------------------------------------------------------------------------

def test_exception_only_cascade_trips_pause() -> None:
    """TD-02 / D-06: connection exceptions must count toward the cascade limit.

    When every session.request() call raises a connection exception, the cascade
    pause must activate once _CONSECUTIVE_5XX_LIMIT consecutive failures are seen —
    the dispatch loop MUST break rather than running unbounded.
    """
    base_url = "https://t.example.com"
    dispatched: list[int] = []

    def _always_timeout(**kwargs):
        dispatched.append(1)
        raise TimeoutError("connect timeout")

    session_mock = MagicMock()
    session_mock.request.side_effect = _always_timeout

    extra = 5  # operations beyond the limit that must NOT be dispatched
    total_ops = _CONSECUTIVE_5XX_LIMIT + extra
    schema_mock = _build_schema_mock(total_ops, url="https://t.example.com/probe")

    with (
        patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_st,
        patch("quirk.scanner.rest_fuzzer.validate_external_url") as mock_validate,
        patch("quirk.scanner.rest_fuzzer.confirm_fuzz_gate", return_value=True),
        patch("quirk.scanner.rest_fuzzer._probe_tls_downgrade", return_value=False),
        patch("quirk.scanner.rest_fuzzer._probe_cipher_weak", return_value=False),
    ):
        mock_st.openapi.from_dict.return_value = schema_mock
        mock_validate.return_value = SimpleNamespace(ok=True, reason="")

        run_fuzz_scan(
            spec_dict=_make_spec(),
            base_url=base_url,
            cfg=_make_cfg(),
            budget=100,
            is_tty=True,
            run_alg_confusion=False,
            _session=session_mock,
        )

    # The cascade must have tripped: dispatched count must not exceed the limit
    assert len(dispatched) <= _CONSECUTIVE_5XX_LIMIT, (
        f"TD-02 VIOLATED: cascade did not trip — dispatched {len(dispatched)} requests "
        f"(expected <= {_CONSECUTIVE_5XX_LIMIT}). Connection exceptions must count toward "
        "the cascade limit; the loop must break, not run unbounded."
    )
    assert len(dispatched) >= 1, "At least one request must have been dispatched"


# ---------------------------------------------------------------------------
# Test 2: success resets the counter — cascade does NOT fire
# ---------------------------------------------------------------------------

def test_success_resets_cascade_counter() -> None:
    """TD-02 / D-06: a genuine success response must reset the failure counter.

    Pattern: FAIL, FAIL, SUCCESS (resets counter), FAIL, FAIL — the counter
    never reaches _CONSECUTIVE_5XX_LIMIT consecutively, so the loop must NOT
    break early. All 5 operations must complete.
    """
    base_url = "https://t.example.com"
    dispatched: list[int] = []

    # 2 exceptions, then success, then 2 more exceptions
    # _CONSECUTIVE_5XX_LIMIT = 3, so 2+2 never consecutively reach the limit
    responses: list = [
        TimeoutError("timeout"),
        TimeoutError("timeout"),
        _FakeResponse(200),     # resets the counter
        TimeoutError("timeout"),
        TimeoutError("timeout"),
    ]
    call_idx = [0]

    def _sequenced_request(**kwargs):
        dispatched.append(1)
        resp = responses[call_idx[0]]
        call_idx[0] += 1
        if isinstance(resp, BaseException):
            raise resp
        return resp

    session_mock = MagicMock()
    session_mock.request.side_effect = _sequenced_request

    schema_mock = _build_schema_mock(len(responses), url="https://t.example.com/probe")

    with (
        patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_st,
        patch("quirk.scanner.rest_fuzzer.validate_external_url") as mock_validate,
        patch("quirk.scanner.rest_fuzzer.confirm_fuzz_gate", return_value=True),
        patch("quirk.scanner.rest_fuzzer._probe_tls_downgrade", return_value=False),
        patch("quirk.scanner.rest_fuzzer._probe_cipher_weak", return_value=False),
    ):
        mock_st.openapi.from_dict.return_value = schema_mock
        mock_validate.return_value = SimpleNamespace(ok=True, reason="")

        run_fuzz_scan(
            spec_dict=_make_spec(),
            base_url=base_url,
            cfg=_make_cfg(),
            budget=100,
            is_tty=True,
            run_alg_confusion=False,
            _session=session_mock,
        )

    # All 5 dispatches must complete — cascade must NOT have fired
    assert len(dispatched) == len(responses), (
        f"TD-02 / success-reset VIOLATED: only {len(dispatched)} of {len(responses)} "
        "requests dispatched. A success at position 3 must reset the counter so the "
        "cascade does not fire prematurely."
    )


# ---------------------------------------------------------------------------
# Test 3: 5xx-only cascade still trips (no regression)
# ---------------------------------------------------------------------------

def test_5xx_only_cascade_still_trips() -> None:
    """TD-02 / D-06 no-regression: N consecutive 5xx responses must still trigger the pause.

    This confirms the original 5xx cascade behaviour is preserved after the D-06 fix.
    """
    base_url = "https://t.example.com"
    dispatched: list[int] = []

    def _always_503(**kwargs):
        dispatched.append(1)
        return _FakeResponse(503)

    session_mock = MagicMock()
    session_mock.request.side_effect = _always_503

    total_ops = _CONSECUTIVE_5XX_LIMIT + 5  # extra ops beyond the limit
    schema_mock = _build_schema_mock(total_ops, url="https://t.example.com/probe")

    with (
        patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_st,
        patch("quirk.scanner.rest_fuzzer.validate_external_url") as mock_validate,
        patch("quirk.scanner.rest_fuzzer.confirm_fuzz_gate", return_value=True),
        patch("quirk.scanner.rest_fuzzer._probe_tls_downgrade", return_value=False),
        patch("quirk.scanner.rest_fuzzer._probe_cipher_weak", return_value=False),
    ):
        mock_st.openapi.from_dict.return_value = schema_mock
        mock_validate.return_value = SimpleNamespace(ok=True, reason="")

        run_fuzz_scan(
            spec_dict=_make_spec(),
            base_url=base_url,
            cfg=_make_cfg(),
            budget=100,
            is_tty=True,
            run_alg_confusion=False,
            _session=session_mock,
        )

    # The cascade must have tripped at _CONSECUTIVE_5XX_LIMIT 5xx responses
    assert len(dispatched) <= _CONSECUTIVE_5XX_LIMIT, (
        f"5xx cascade no-regression VIOLATED: dispatched {len(dispatched)} requests "
        f"(expected <= {_CONSECUTIVE_5XX_LIMIT}). Consecutive 5xx must still trip the pause."
    )
    assert len(dispatched) >= 1, "At least one 5xx request must have been dispatched"
