"""Tests for REST fuzzer dispatch loop, crypto probes, and alg-confusion probe.

Phase 96 / FUZZ-01, FUZZ-02, FUZZ-04
--------------------------------------
TDD RED + GREEN phases covering:
- Dispatch loop with gate, scope gate, budget cap, rate limiter, 5xx cascade
- TLS downgrade, cipher, HSTS, HTTP-only credential probes
- JWT RS256 -> HS256 alg-confusion forge + acceptance probe

Design: all tests use mock/patch so no real network requests are made.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Minimal OpenAPI spec used across multiple tests
# ---------------------------------------------------------------------------

MINIMAL_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test", "version": "1.0.0"},
    "servers": [{"url": "http://example.com"}],
    "paths": {
        "/ping": {"get": {"responses": {"200": {"description": "OK"}}}},
        "/status": {"get": {"responses": {"200": {"description": "OK"}}}},
        "/health": {"get": {"responses": {"200": {"description": "OK"}}}},
        "/check": {"get": {"responses": {"200": {"description": "OK"}}}},
        "/info": {"get": {"responses": {"200": {"description": "OK"}}}},
    },
}

SINGLE_ENDPOINT_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test", "version": "1.0.0"},
    "servers": [{"url": "http://example.com"}],
    "paths": {
        "/probe": {"get": {"responses": {"200": {"description": "OK"}}}},
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code: int = 200, headers: dict | None = None):
    """Create a mock HTTP response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    return resp


def _ok_scope_result():
    """Create a mock validate_external_url result that passes."""
    result = MagicMock()
    result.ok = True
    result.reason = ""
    return result


def _rejected_scope_result():
    """Create a mock validate_external_url result that rejects."""
    result = MagicMock()
    result.ok = False
    result.reason = "RC_LOOPBACK"
    return result


def _ok_scope_result_with_ip(ip: str = "8.8.8.8"):
    """Mock validate_external_url result that passes and carries a pinned IP (SSRF-05)."""
    result = MagicMock()
    result.ok = True
    result.reason = ""
    result.resolved_ip = ip
    return result


# ---------------------------------------------------------------------------
# Phase 123 SSRF-01/SSRF-05: raw-socket TLS probes validate + pin the target
# (RED until Plan 03 routes the probe block through validate_external_url and
#  passes the pinned resolved_ip + server_hostname into the probes)
# ---------------------------------------------------------------------------

class TestRawSocketProbePreventsSSRF:
    """SSRF-01: raw-socket TLS probes validate the target URL before create_connection."""

    def test_probe_skipped_when_url_rejected(self):
        """When validate_external_url rejects the URL, raw socket probes are NOT called."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        session_mock = MagicMock()
        cfg = MagicMock()
        cfg.security = MagicMock()
        cfg.security.allow_internal_targets = False

        with patch("quirk.scanner.rest_fuzzer.validate_external_url",
                   return_value=_rejected_scope_result()) as mock_validate, \
             patch("quirk.scanner.rest_fuzzer._probe_tls_downgrade") as mock_tls, \
             patch("quirk.scanner.rest_fuzzer._probe_cipher_weak") as mock_cipher, \
             patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_sch:
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = []
            mock_sch.openapi.from_dict.return_value = mock_schema

            run_fuzz_scan(
                spec_dict={"openapi": "3.0.0"},
                base_url="https://127.0.0.1:8080",
                cfg=cfg, budget=5,
                prompt_fn=lambda _: "CONFIRM", is_tty=True,
                _session=session_mock,
            )

        # validate_external_url must have been called (not skipped)
        assert mock_validate.call_count >= 1
        # Probes must NOT have been called (rejected URL)
        assert mock_tls.call_count == 0
        assert mock_cipher.call_count == 0


class TestRawProbeUsesPinnedIP:
    """SSRF-01/SSRF-05: raw-socket probes use resolved_ip from ValidationResult, not hostname."""

    def test_probe_receives_pinned_ip(self):
        """_probe_tls_downgrade is called with the pinned IP, not the original hostname."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        session_mock = MagicMock()
        cfg = MagicMock()
        cfg.security = MagicMock()
        cfg.security.allow_internal_targets = False

        pinned = "93.184.216.34"  # example.com IP

        with patch("quirk.scanner.rest_fuzzer.validate_external_url",
                   return_value=_ok_scope_result_with_ip(pinned)), \
             patch("quirk.scanner.rest_fuzzer._probe_tls_downgrade",
                   return_value=False) as mock_tls, \
             patch("quirk.scanner.rest_fuzzer._probe_cipher_weak",
                   return_value=False), \
             patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_sch:
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = []
            mock_sch.openapi.from_dict.return_value = mock_schema

            run_fuzz_scan(
                spec_dict={"openapi": "3.0.0"},
                base_url="https://example.com",
                cfg=cfg, budget=5,
                prompt_fn=lambda _: "CONFIRM", is_tty=True,
                _session=session_mock,
            )

        # The first positional arg to _probe_tls_downgrade must be the pinned IP
        assert mock_tls.called
        call_host_arg = mock_tls.call_args[0][0]
        assert call_host_arg == pinned

        # The original hostname must be passed as server_hostname kwarg (SNI)
        call_kwargs = mock_tls.call_args[1]
        assert call_kwargs.get("server_hostname") == "example.com"


# ---------------------------------------------------------------------------
# Task 1: Dispatch loop tests
# ---------------------------------------------------------------------------


class TestRunFuzzScanGateFalse:
    """Gate-first: when gate returns False, no requests are dispatched."""

    def test_run_fuzz_scan_gate_false_zero_requests(self):
        """When gate returns False (non-CONFIRM), session.request.call_count == 0."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        session_mock = MagicMock()
        cfg = MagicMock()
        cfg.security = MagicMock()
        cfg.security.allow_internal_targets = False

        # prompt_fn returns non-CONFIRM so gate returns False
        result = run_fuzz_scan(
            spec_dict=MINIMAL_SPEC,
            base_url="http://example.com",
            cfg=cfg,
            budget=5,
            prompt_fn=lambda _: "no",
            is_tty=True,
            _session=session_mock,
        )

        assert result == []
        assert session_mock.request.call_count == 0


class TestDispatchUsesAsTransportKwargs:
    """Dispatch loop unpacks case.as_transport_kwargs() into session.request(**kwargs)."""

    def test_dispatch_uses_as_transport_kwargs(self):
        """With a mock schemathesis, session.request is called with the kwargs dict."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        session_mock = MagicMock()
        session_mock.request.return_value = _make_response(200)

        cfg = MagicMock()
        cfg.security = MagicMock()
        cfg.security.allow_internal_targets = False

        # Mock schemathesis iterator to return one GET operation
        mock_case = MagicMock()
        mock_case.as_transport_kwargs.return_value = {
            "method": "GET",
            "url": "http://example.com/probe",
            "headers": {"User-Agent": "schemathesis/4.4.4"},
            "cookies": {},
            "params": {},
        }

        mock_op = MagicMock()
        mock_op.as_strategy.return_value.example.return_value = mock_case

        from schemathesis.core.result import Ok as _SchemaOk
        mock_result = _SchemaOk(mock_op)

        with patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_schema_mod, \
             patch("quirk.scanner.rest_fuzzer.validate_external_url", return_value=_ok_scope_result()):
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = [mock_result]
            mock_schema_mod.openapi.from_dict.return_value = mock_schema

            result = run_fuzz_scan(
                spec_dict=SINGLE_ENDPOINT_SPEC,
                base_url="http://example.com",
                cfg=cfg,
                budget=5,
                prompt_fn=lambda _: "CONFIRM",
                is_tty=True,
                _session=session_mock,
            )

        # session.request must be called with the kwargs (GET method)
        assert session_mock.request.call_count == 1
        call_kwargs = session_mock.request.call_args
        # method should be GET
        assert call_kwargs.kwargs.get("method") == "GET" or (
            call_kwargs.args and call_kwargs.args[0] == "GET"
        ) or call_kwargs.kwargs.get("method", "GET") == "GET"


class TestScopeGate:
    """Scope gate: rejected URLs do not consume budget, session.request not called."""

    def test_scope_gate_rejects_does_not_consume_budget(self):
        """URL rejected by validate_external_url: session.request not called, budget_used stays 0."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        session_mock = MagicMock()
        cfg = MagicMock()
        cfg.security = MagicMock()
        cfg.security.allow_internal_targets = False

        mock_case = MagicMock()
        mock_case.as_transport_kwargs.return_value = {
            "method": "GET",
            "url": "http://127.0.0.1/probe",
            "headers": {},
            "cookies": {},
            "params": {},
        }

        mock_op = MagicMock()
        mock_op.as_strategy.return_value.example.return_value = mock_case

        from schemathesis.core.result import Ok as _SchemaOk
        mock_result = _SchemaOk(mock_op)

        with patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_schema_mod, \
             patch("quirk.scanner.rest_fuzzer.validate_external_url", return_value=_rejected_scope_result()):
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = [mock_result]
            mock_schema_mod.openapi.from_dict.return_value = mock_schema

            result = run_fuzz_scan(
                spec_dict=SINGLE_ENDPOINT_SPEC,
                base_url="http://127.0.0.1",
                cfg=cfg,
                budget=5,
                prompt_fn=lambda _: "CONFIRM",
                is_tty=True,
                _session=session_mock,
            )

        # Session should NOT be called for rejected URLs
        assert session_mock.request.call_count == 0


class TestBudgetCap:
    """Budget cap: with budget=2 and 5 operations, at most 2 requests dispatched."""

    def test_budget_caps_dispatch(self):
        """With budget=2 and 5 operations, session.request called at most 2 times."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        session_mock = MagicMock()
        session_mock.request.return_value = _make_response(200)

        cfg = MagicMock()
        cfg.security = MagicMock()
        cfg.security.allow_internal_targets = False

        def make_mock_result(path: str):
            mock_case = MagicMock()
            mock_case.as_transport_kwargs.return_value = {
                "method": "GET",
                "url": f"http://example.com{path}",
                "headers": {},
                "cookies": {},
                "params": {},
            }
            mock_op = MagicMock()
            mock_op.as_strategy.return_value.example.return_value = mock_case
            from schemathesis.core.result import Ok as _SchemaOk
            return _SchemaOk(mock_op)

        five_results = [make_mock_result(f"/path{i}") for i in range(5)]

        with patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_schema_mod, \
             patch("quirk.scanner.rest_fuzzer.validate_external_url", return_value=_ok_scope_result()):
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = five_results
            mock_schema_mod.openapi.from_dict.return_value = mock_schema

            result = run_fuzz_scan(
                spec_dict=MINIMAL_SPEC,
                base_url="http://example.com",
                cfg=cfg,
                budget=2,
                prompt_fn=lambda _: "CONFIRM",
                is_tty=True,
                _session=session_mock,
            )

        assert session_mock.request.call_count <= 2


class TestRateLimiter:
    """Rate limiter: TokenBucket.acquire called before each dispatched request."""

    def test_rate_limiter_invoked(self):
        """TokenBucket.acquire() must be called once per dispatched request."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        session_mock = MagicMock()
        session_mock.request.return_value = _make_response(200)

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

        mock_bucket = MagicMock()

        with patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_schema_mod, \
             patch("quirk.scanner.rest_fuzzer.validate_external_url", return_value=_ok_scope_result()), \
             patch("quirk.scanner.rest_fuzzer.TokenBucket", return_value=mock_bucket):
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = [mock_result]
            mock_schema_mod.openapi.from_dict.return_value = mock_schema

            result = run_fuzz_scan(
                spec_dict=SINGLE_ENDPOINT_SPEC,
                base_url="http://example.com",
                cfg=cfg,
                budget=5,
                prompt_fn=lambda _: "CONFIRM",
                is_tty=True,
                _session=session_mock,
            )

        # acquire must be called at least once (one dispatched request)
        assert mock_bucket.acquire.call_count >= 1


class TestFiveXxCascadePause:
    """5xx cascade: three consecutive 500 responses stop the loop with a warning."""

    def test_5xx_cascade_pause(self):
        """Three consecutive 5xx responses must cause the loop to stop."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        cfg = MagicMock()
        cfg.security = MagicMock()
        cfg.security.allow_internal_targets = False

        session_mock = MagicMock()
        # Return 500 for every call
        session_mock.request.return_value = _make_response(500)

        def make_mock_result(path: str):
            mock_case = MagicMock()
            mock_case.as_transport_kwargs.return_value = {
                "method": "GET",
                "url": f"http://example.com{path}",
                "headers": {},
                "cookies": {},
                "params": {},
            }
            mock_op = MagicMock()
            mock_op.as_strategy.return_value.example.return_value = mock_case
            from schemathesis.core.result import Ok as _SchemaOk
            return _SchemaOk(mock_op)

        # 10 operations but should stop at 3 due to cascade
        ten_results = [make_mock_result(f"/path{i}") for i in range(10)]

        with patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_schema_mod, \
             patch("quirk.scanner.rest_fuzzer.validate_external_url", return_value=_ok_scope_result()):
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = ten_results
            mock_schema_mod.openapi.from_dict.return_value = mock_schema

            result = run_fuzz_scan(
                spec_dict=MINIMAL_SPEC,
                base_url="http://example.com",
                cfg=cfg,
                budget=50,
                prompt_fn=lambda _: "CONFIRM",
                is_tty=True,
                _session=session_mock,
            )

        # After 3 consecutive 5xx, loop must stop: at most 3 requests sent
        assert session_mock.request.call_count == 3


class TestProbeHsts:
    """HSTS probe: probe_hsts({}) is True; present header is False."""

    def test_probe_hsts_missing_is_finding(self):
        """probe_hsts({}) returns True (HSTS missing = finding)."""
        from quirk.scanner.rest_fuzzer import probe_hsts
        assert probe_hsts({}) is True

    def test_probe_hsts_present_is_not_finding(self):
        """probe_hsts({'strict-transport-security': 'max-age=31536000'}) returns False."""
        from quirk.scanner.rest_fuzzer import probe_hsts
        assert probe_hsts({"strict-transport-security": "max-age=31536000"}) is False

    def test_probe_hsts_case_insensitive_key(self):
        """probe_hsts handles lowercase header key (as returned by requests)."""
        from quirk.scanner.rest_fuzzer import probe_hsts
        assert probe_hsts({"strict-transport-security": "max-age=1"}) is False


class TestProbeTlsDowngrade:
    """TLS downgrade probe: returns bool (no unhandled exception from mock socket/ssl)."""

    def test_probe_tls_downgrade_returns_bool(self):
        """_probe_tls_downgrade(host, port) returns a bool on ssl failure (mocked)."""
        from quirk.scanner.rest_fuzzer import _probe_tls_downgrade
        import ssl

        with patch("quirk.scanner.rest_fuzzer.socket") as mock_socket_mod:
            # Simulate socket connection refused (OSError)
            mock_socket_mod.create_connection.side_effect = OSError("connection refused")
            result = _probe_tls_downgrade("example.com", 443)

        assert isinstance(result, bool)

    def test_probe_tls_downgrade_returns_false_on_ssl_error(self):
        """_probe_tls_downgrade returns False when TLS 1.0/1.1 is rejected."""
        from quirk.scanner.rest_fuzzer import _probe_tls_downgrade
        import ssl

        with patch("quirk.scanner.rest_fuzzer.socket") as mock_socket_mod:
            mock_socket_mod.create_connection.side_effect = ssl.SSLError("bad protocol version")
            result = _probe_tls_downgrade("example.com", 443)

        assert result is False


# ---------------------------------------------------------------------------
# Task 2: JWT alg-confusion probe tests
# ---------------------------------------------------------------------------


class TestAlgConfusionForge:
    """_forge_hs256_token: forge returns bytes for RS256; None for non-RS256."""

    def _make_rs256_token(self) -> tuple[str, bytes]:
        """Generate a real RS256 JWT + public key PEM for forge tests."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import jwt

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        pub_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        token = jwt.encode({"sub": "user1", "role": "admin"}, priv_pem, algorithm="RS256")
        return token, pub_pem

    def test_alg_confusion_forge_returns_bytes_for_rs256(self):
        """_forge_hs256_token(rs256_token, pub_pem) returns bytes for an RS256 source token."""
        from quirk.scanner.rest_fuzzer import _forge_hs256_token
        import jwt

        token, pub_pem = self._make_rs256_token()
        result = _forge_hs256_token(token, pub_pem)

        assert result is not None
        assert isinstance(result, bytes)

        # Forged token header should show HS256
        decoded_header = jwt.get_unverified_header(result.decode("utf-8"))
        assert decoded_header["alg"] == "HS256"

    def test_alg_confusion_forged_claims_match_source(self):
        """Forged token claims match the source token claims."""
        from quirk.scanner.rest_fuzzer import _forge_hs256_token
        import jwt

        token, pub_pem = self._make_rs256_token()
        result = _forge_hs256_token(token, pub_pem)

        assert result is not None
        forged_str = result.decode("utf-8")

        # Decode without verification to check claims
        src_claims = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["RS256"],
        )
        forged_claims = jwt.decode(
            forged_str,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["HS256"],
        )
        assert src_claims.get("sub") == forged_claims.get("sub")
        assert src_claims.get("role") == forged_claims.get("role")

    def test_alg_confusion_skips_non_rs256_hs256(self):
        """_forge_hs256_token returns None for an HS256 source token."""
        from quirk.scanner.rest_fuzzer import _forge_hs256_token
        import jwt

        token = jwt.encode({"sub": "user1"}, "secret", algorithm="HS256")
        result = _forge_hs256_token(token, b"some_key_pem")

        assert result is None

    def test_alg_confusion_skips_alg_none(self):
        """_forge_hs256_token returns None for an alg:none token."""
        from quirk.scanner.rest_fuzzer import _forge_hs256_token
        import base64
        import json

        # Build an alg:none token manually
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "x"}).encode()).rstrip(b"=")
        token = f"{header.decode()}.{payload.decode()}."
        result = _forge_hs256_token(token, b"some_key_pem")

        assert result is None


class TestAlgConfusionProbeAccepted:
    """Alg-confusion acceptance: 2xx response with forged token emits CRITICAL finding."""

    def _make_rs256_cred_ctx(self) -> tuple:
        """Build a CredentialContext with a real RS256 bearer token."""
        from quirk.auth.credentials import CredentialContext
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import jwt

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        pub_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        token = jwt.encode({"sub": "user1"}, priv_pem, algorithm="RS256")
        ctx = CredentialContext(scheme="bearer")
        ctx._secret_buf = bytearray(token.encode())
        return ctx, pub_pem

    def test_alg_confusion_accepted_is_critical(self):
        """When run_alg_confusion=True and server returns 2xx, CRITICAL finding is emitted."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        cred_ctx, pub_pem = self._make_rs256_cred_ctx()

        session_mock = MagicMock()
        # First call: normal dispatch returns 200
        # JWKS fetch returns public key
        # Alg-confusion probe request returns 200 (accepted!)
        session_mock.request.return_value = _make_response(200)

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
             patch("quirk.scanner.rest_fuzzer.validate_external_url", return_value=_ok_scope_result()), \
             patch("quirk.scanner.rest_fuzzer._fetch_jwks_public_key_pem", return_value=pub_pem):
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = [mock_result]
            mock_schema_mod.openapi.from_dict.return_value = mock_schema

            findings = run_fuzz_scan(
                spec_dict=SINGLE_ENDPOINT_SPEC,
                base_url="http://example.com",
                cfg=cfg,
                cred_ctx=cred_ctx,
                budget=5,
                prompt_fn=lambda _: "CONFIRM",
                is_tty=True,
                run_alg_confusion=True,
                _session=session_mock,
            )

        critical_findings = [
            f for f in findings
            if getattr(f, "severity", None) == "CRITICAL"
            and getattr(f, "service_detail", None) == "alg_confusion"
        ]
        assert len(critical_findings) >= 1

    def test_alg_confusion_no_public_key_skips_info(self):
        """When no public key is discoverable, INFO probe_skipped finding, no forged request."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        cred_ctx, _ = self._make_rs256_cred_ctx()

        session_mock = MagicMock()
        session_mock.request.return_value = _make_response(200)

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

        # _fetch_jwks_public_key_pem returns None -> no public key
        with patch("quirk.scanner.rest_fuzzer.schemathesis") as mock_schema_mod, \
             patch("quirk.scanner.rest_fuzzer.validate_external_url", return_value=_ok_scope_result()), \
             patch("quirk.scanner.rest_fuzzer._fetch_jwks_public_key_pem", return_value=None):
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = [mock_result]
            mock_schema_mod.openapi.from_dict.return_value = mock_schema

            findings = run_fuzz_scan(
                spec_dict=SINGLE_ENDPOINT_SPEC,
                base_url="http://example.com",
                cfg=cfg,
                cred_ctx=cred_ctx,
                budget=5,
                prompt_fn=lambda _: "CONFIRM",
                is_tty=True,
                run_alg_confusion=True,
                _session=session_mock,
            )

        info_findings = [
            f for f in findings
            if getattr(f, "severity", None) == "INFO"
            and getattr(f, "service_detail", None) == "probe_skipped"
        ]
        assert len(info_findings) >= 1


class TestBudgetCeilingBoundsAllTraffic:
    """CR-01/CR-02 regression: the budget ceiling must bound ALL outbound traffic —
    including the connection-level TLS/cipher socket probes (run once, counted) and
    (when enabled) the alg-confusion forged-token request."""

    def _mock_ops(self, n):
        from schemathesis.core.result import Ok as _SchemaOk
        results = []
        for _ in range(n):
            mock_case = MagicMock()
            mock_case.as_transport_kwargs.return_value = {
                "method": "GET", "url": "https://example.com/probe",
                "headers": {}, "cookies": {}, "params": {},
            }
            mock_op = MagicMock()
            mock_op.as_strategy.return_value.example.return_value = mock_case
            results.append(_SchemaOk(mock_op))
        return results

    def test_socket_probes_run_once_and_count_budget(self):
        """TLS-downgrade + cipher probes fire exactly ONCE (not per-operation) and each
        consumes one unit of budget — so N operations cannot open 2N raw sockets."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        session_mock = MagicMock()
        session_mock.request.return_value = _make_response(200)
        cfg = MagicMock()
        cfg.security = MagicMock()
        cfg.security.allow_internal_targets = False

        with patch("quirk.scanner.rest_fuzzer.schemathesis") as mod, \
             patch("quirk.scanner.rest_fuzzer.validate_external_url", return_value=_ok_scope_result()), \
             patch("quirk.scanner.rest_fuzzer._probe_tls_downgrade", return_value=False) as tls_p, \
             patch("quirk.scanner.rest_fuzzer._probe_cipher_weak", return_value=False) as cip_p:
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = self._mock_ops(10)
            mod.openapi.from_dict.return_value = mock_schema

            run_fuzz_scan(
                spec_dict={"openapi": "3.0.0"},
                base_url="https://example.com",   # https → socket probes apply
                cfg=cfg, budget=5,
                prompt_fn=lambda _: "CONFIRM", is_tty=True,
                _session=session_mock,
            )

        # CR-02: each connection-level probe runs at most ONCE, never per-operation.
        assert tls_p.call_count == 1
        assert cip_p.call_count == 1
        # Total HTTP requests bounded by budget minus the 2 socket-probe units.
        assert session_mock.request.call_count <= 5
        # And total dispatched units (2 socket + HTTP) never exceeds the budget.
        assert (tls_p.call_count + cip_p.call_count + session_mock.request.call_count) <= 5

    def test_alg_confusion_request_counts_against_budget(self):
        """CR-01 regression: with alg-confusion enabled, the forged-token request is
        counted — total session.request calls never exceed the budget even though each
        GET iteration would otherwise dispatch a second (forged) request."""
        from quirk.scanner.rest_fuzzer import run_fuzz_scan

        session_mock = MagicMock()
        session_mock.request.return_value = _make_response(200)
        cfg = MagicMock(); cfg.security = MagicMock(); cfg.security.allow_internal_targets = False

        cred = MagicMock()
        cred.scheme = "bearer"
        cred.bearer_declared_alg.return_value = "RS256"
        cred._secret_buf = bytearray(b"header.payload.sig")

        with patch("quirk.scanner.rest_fuzzer.schemathesis") as mod, \
             patch("quirk.scanner.rest_fuzzer.validate_external_url", return_value=_ok_scope_result()), \
             patch("quirk.scanner.rest_fuzzer._fetch_jwks_public_key_pem", return_value=b"-----PUBKEY-----"), \
             patch("quirk.scanner.rest_fuzzer._forge_hs256_token", return_value=b"forged.jwt.token"):
            mock_schema = MagicMock()
            mock_schema.include.return_value.get_all_operations.return_value = self._mock_ops(20)
            mod.openapi.from_dict.return_value = mock_schema

            run_fuzz_scan(
                spec_dict={"openapi": "3.0.0"},
                base_url="http://example.com",   # http → no socket probes; isolate alg-confusion counting
                cfg=cfg, budget=6, cred_ctx=cred, run_alg_confusion=True,
                prompt_fn=lambda _: "CONFIRM", is_tty=True,
                _session=session_mock,
            )

        # Each GET op would dispatch 1 GET + 1 forged request; with counting, total <= budget.
        assert session_mock.request.call_count <= 6, (
            f"budget bypassed: {session_mock.request.call_count} requests > budget 6"
        )
