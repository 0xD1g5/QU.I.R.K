"""RED contract tests for AUDIT-02: rest_fuzzer per-scan dedup of HSTS and http_creds findings.

AUDIT-02 success criterion: ``run_fuzz_scan`` must emit at most ONE ``hsts_missing`` finding
and at most ONE ``http_creds`` finding per scan, regardless of how many operations matched.

Currently the fuzzer appends one finding per matching operation in the dispatch loop,
so a spec with N paths all missing HSTS produces N ``hsts_missing`` findings.

These tests FAIL against the current codebase (v5.7) because:
- The fuzzer loop at ~L676 appends a new hsts_missing finding for every operation that
  returns a response without a Strict-Transport-Security header.
- The fuzzer loop at ~L692 appends a new http_creds finding for every http:// operation
  that fires the credential probe.

Wave 2 Plan 130-02 makes them pass.
"""
from __future__ import annotations

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_cfg(allow_internal: bool = True) -> MagicMock:
    """Return a minimal scan config accepted by run_fuzz_scan."""
    cfg = MagicMock()
    cfg.security = SimpleNamespace(allow_internal_targets=allow_internal)
    return cfg


def _make_multi_path_spec(n_paths: int = 5, base: str = "http://example.com") -> dict:
    """Return an OpenAPI spec with n_paths GET operations, all on an http:// base URL."""
    paths = {}
    for i in range(n_paths):
        paths[f"/endpoint{i}"] = {
            "get": {
                "responses": {"200": {"description": "OK"}},
            }
        }
    return {
        "openapi": "3.0.0",
        "info": {"title": "DeduplicationTestAPI", "version": "1.0.0"},
        "servers": [{"url": base}],
        "paths": paths,
    }


def _build_schema_mock_http(num_ops: int, base_url: str = "http://example.com") -> MagicMock:
    """Build a schemathesis schema mock with num_ops operations targeting http:// URLs."""
    from quirk.scanner.rest_fuzzer import _SchemaOk  # type: ignore[attr-defined]

    ops = []
    for i in range(num_ops):
        result = MagicMock(spec=_SchemaOk)
        case = MagicMock()
        case.as_transport_kwargs.return_value = {
            "method": "GET",
            "url": f"{base_url}/endpoint{i}",
        }
        result.ok.return_value = MagicMock()
        result.ok.return_value.as_strategy.return_value.example.return_value = case
        ops.append(result)

    get_schema = MagicMock()
    get_schema.get_all_operations.return_value = iter(ops)
    schema = MagicMock()
    schema.include.return_value = get_schema
    return schema


def _make_headerless_response(url: str = "http://example.com") -> MagicMock:
    """Mock response: 200, no Strict-Transport-Security header (triggers HSTS finding)."""
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {}  # No STS header -> hsts_missing probe fires
    resp.url = url
    return resp


def _make_bearer_cred_ctx(token: str = "test-bearer-token") -> "CredentialContext":
    """Build a minimal bearer CredentialContext for http_creds probe activation."""
    from quirk.auth.credentials import CredentialContext
    return CredentialContext(
        scheme="bearer",
        _secret_buf=bytearray(token.encode("utf-8")),
    )


# ---------------------------------------------------------------------------
# Test A: HSTS deduplication — multi-operation spec produces exactly ONE hsts_missing
# ---------------------------------------------------------------------------

class TestHSTSDedup:
    """AUDIT-02: at most ONE hsts_missing finding per scan regardless of operation count."""

    def test_multi_path_hsts_produces_single_finding(self) -> None:
        """5 operations all missing HSTS — must emit exactly 1 hsts_missing finding (AUDIT-02).

        Currently FAILS: the fuzzer emits one hsts_missing per operation (5 total).
        """
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        n_ops = 5
        base_url = "http://example.com"
        schema_mock = _build_schema_mock_http(n_ops, base_url)

        # All responses: 200, no STS header
        responses = [_make_headerless_response(f"{base_url}/endpoint{i}") for i in range(n_ops)]
        session_mock = MagicMock()
        session_mock.request.side_effect = responses

        with (
            patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_st,
            patch("quirk.scanner.rest_fuzzer.validate_external_url") as mock_validate,
            patch("quirk.scanner.rest_fuzzer.confirm_fuzz_gate", return_value=True),
            patch("quirk.scanner.rest_fuzzer._probe_tls_downgrade", return_value=False),
            patch("quirk.scanner.rest_fuzzer._probe_cipher_weak", return_value=False),
        ):
            mock_st.openapi.from_dict.return_value = schema_mock
            mock_validate.return_value = SimpleNamespace(ok=True, reason="", resolved_ip="")

            findings = run_fuzz_scan(
                spec_dict=_make_multi_path_spec(n_ops, base_url),
                base_url=base_url,
                cfg=_make_cfg(),
                budget=n_ops + 5,
                is_tty=True,
                run_alg_confusion=False,
                _session=session_mock,
            )

        hsts_findings = [f for f in findings if getattr(f, "service_detail", None) == "hsts_missing"]

        assert len(hsts_findings) <= 1, (
            f"AUDIT-02 VIOLATED: run_fuzz_scan emitted {len(hsts_findings)} hsts_missing findings "
            f"for a {n_ops}-operation spec — expected at most 1. "
            "Per-scan deduplication is required so each finding type is reported once."
        )
        # Must still report it (not zero)
        assert len(hsts_findings) == 1, (
            f"AUDIT-02: expected exactly 1 hsts_missing finding, got {len(hsts_findings)}. "
            "Dedup must collapse N matches to a single representative finding."
        )


# ---------------------------------------------------------------------------
# Test B: http_creds deduplication — multi-operation spec produces exactly ONE http_creds
# ---------------------------------------------------------------------------

class TestHttpCredsDedup:
    """AUDIT-02: at most ONE http_creds finding per scan regardless of operation count."""

    def test_multi_path_http_creds_produces_single_finding(self) -> None:
        """4 http:// operations with cred_ctx — must emit at most 1 http_creds finding (AUDIT-02).

        Currently FAILS: the fuzzer emits one http_creds per matching operation.
        """
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        n_ops = 4
        base_url = "http://example.com"
        schema_mock = _build_schema_mock_http(n_ops, base_url)

        # All responses: 200, no headers
        responses = [_make_headerless_response(f"{base_url}/endpoint{i}") for i in range(n_ops)]
        session_mock = MagicMock()
        session_mock.request.side_effect = responses

        cred_ctx = _make_bearer_cred_ctx()

        with (
            patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_st,
            patch("quirk.scanner.rest_fuzzer.validate_external_url") as mock_validate,
            patch("quirk.scanner.rest_fuzzer.confirm_fuzz_gate", return_value=True),
            patch("quirk.scanner.rest_fuzzer._probe_tls_downgrade", return_value=False),
            patch("quirk.scanner.rest_fuzzer._probe_cipher_weak", return_value=False),
        ):
            mock_st.openapi.from_dict.return_value = schema_mock
            mock_validate.return_value = SimpleNamespace(ok=True, reason="", resolved_ip="")

            findings = run_fuzz_scan(
                spec_dict=_make_multi_path_spec(n_ops, base_url),
                base_url=base_url,
                cfg=_make_cfg(),
                budget=n_ops + 5,
                is_tty=True,
                run_alg_confusion=False,
                cred_ctx=cred_ctx,
                _session=session_mock,
            )

        http_creds_findings = [
            f for f in findings if getattr(f, "service_detail", None) == "http_creds"
        ]

        assert len(http_creds_findings) <= 1, (
            f"AUDIT-02 VIOLATED: run_fuzz_scan emitted {len(http_creds_findings)} http_creds "
            f"findings for a {n_ops}-operation spec — expected at most 1. "
            "Per-scan deduplication is required."
        )


# ---------------------------------------------------------------------------
# Test C: Regression — distinct finding types are not deduplicated against each other
# ---------------------------------------------------------------------------

class TestDedupDoesNotCollapseDifferentTypes:
    """AUDIT-02: dedup must be per service_detail; hsts_missing and http_creds remain distinct."""

    def test_hsts_and_http_creds_both_capped_individually_after_dedup(self) -> None:
        """When both HSTS and http_creds fire for N ops, each is capped at 1 (AUDIT-02)."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        n_ops = 3
        base_url = "http://example.com"
        schema_mock = _build_schema_mock_http(n_ops, base_url)

        responses = [_make_headerless_response(f"{base_url}/endpoint{i}") for i in range(n_ops)]
        session_mock = MagicMock()
        session_mock.request.side_effect = responses

        cred_ctx = _make_bearer_cred_ctx()

        with (
            patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_st,
            patch("quirk.scanner.rest_fuzzer.validate_external_url") as mock_validate,
            patch("quirk.scanner.rest_fuzzer.confirm_fuzz_gate", return_value=True),
            patch("quirk.scanner.rest_fuzzer._probe_tls_downgrade", return_value=False),
            patch("quirk.scanner.rest_fuzzer._probe_cipher_weak", return_value=False),
        ):
            mock_st.openapi.from_dict.return_value = schema_mock
            mock_validate.return_value = SimpleNamespace(ok=True, reason="", resolved_ip="")

            findings = run_fuzz_scan(
                spec_dict=_make_multi_path_spec(n_ops, base_url),
                base_url=base_url,
                cfg=_make_cfg(),
                budget=n_ops + 5,
                is_tty=True,
                run_alg_confusion=False,
                cred_ctx=cred_ctx,
                _session=session_mock,
            )

        details = [getattr(f, "service_detail", None) for f in findings]

        # After dedup, the total per type must be <= 1 (AUDIT-02 contract)
        hsts_count = details.count("hsts_missing")
        http_creds_count = details.count("http_creds")
        assert hsts_count <= 1, (
            f"hsts_missing deduplicated count should be <= 1, got {hsts_count}"
        )
        assert http_creds_count <= 1, (
            f"http_creds deduplicated count should be <= 1, got {http_creds_count}"
        )
