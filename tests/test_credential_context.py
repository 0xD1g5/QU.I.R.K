"""Tests for quirk.auth.credentials.CredentialContext (Phase 93 / AUTH-01).

Sentinel: QUIRK_SENTINEL_CRED_d41d8cd9
"""
from __future__ import annotations

import os
import tempfile

import pytest

SENTINEL = "QUIRK_SENTINEL_CRED_d41d8cd9"


# ---------------------------------------------------------------------------
# Task 1: CredentialContext dataclass behaviour tests
# ---------------------------------------------------------------------------

def _make_ctx(scheme: str, secret: bytes, *, header_name=None, query_param=None):
    """Helper: build a CredentialContext by directly seeding _secret_buf."""
    from quirk.auth.credentials import CredentialContext
    ctx = CredentialContext(scheme=scheme)
    ctx._secret_buf = bytearray(secret)
    if header_name is not None:
        ctx._header_name = header_name
    if query_param is not None:
        ctx._query_param = query_param
    return ctx


class TestAsHeaders:
    def test_bearer_scheme(self):
        ctx = _make_ctx("bearer", b"tok123")
        headers = ctx.as_headers()
        assert headers == {"Authorization": "Bearer tok123"}

    def test_api_key_header_default_name(self):
        ctx = _make_ctx("api_key_header", b"key456")
        headers = ctx.as_headers()
        assert headers == {"X-Api-Key": "key456"}

    def test_api_key_header_custom_name(self):
        ctx = _make_ctx("api_key_header", b"key789", header_name="X-Custom-Key")
        headers = ctx.as_headers()
        assert headers == {"X-Custom-Key": "key789"}

    def test_api_key_query_returns_empty(self):
        """api_key_query scheme: as_headers() returns {} (D-03)."""
        ctx = _make_ctx("api_key_query", b"qsecret", query_param="api_key")
        assert ctx.as_headers() == {}

    def test_basic_scheme(self):
        ctx = _make_ctx("basic", b"dXNlcjpwYXNz")
        headers = ctx.as_headers()
        assert headers == {"Authorization": "Basic dXNlcjpwYXNz"}


class TestQueryParam:
    def test_api_key_query_returns_tuple(self):
        ctx = _make_ctx("api_key_query", b"mykey", query_param="api_key")
        result = ctx.query_param()
        assert result == ("api_key", "mykey")

    def test_bearer_returns_none(self):
        ctx = _make_ctx("bearer", b"tok")
        assert ctx.query_param() is None

    def test_api_key_header_returns_none(self):
        ctx = _make_ctx("api_key_header", b"k")
        assert ctx.query_param() is None

    def test_basic_returns_none(self):
        ctx = _make_ctx("basic", b"creds")
        assert ctx.query_param() is None


class TestClose:
    def test_close_zeroes_buffer(self):
        ctx = _make_ctx("bearer", b"supersecret")
        n = len(ctx._secret_buf)
        ctx.close()
        assert bytes(ctx._secret_buf) == b"\x00" * n

    def test_close_idempotent_on_empty(self):
        ctx = _make_ctx("bearer", b"")
        ctx.close()  # should not raise
        assert bytes(ctx._secret_buf) == b""


class TestContextManager:
    def test_context_manager_calls_close(self):
        ctx = _make_ctx("bearer", b"secret_value")
        n = len(ctx._secret_buf)
        with ctx:
            pass
        assert bytes(ctx._secret_buf) == b"\x00" * n

    def test_context_manager_returns_self(self):
        ctx = _make_ctx("bearer", b"tok")
        with ctx as c:
            assert c is ctx


class TestRepr:
    def test_repr_does_not_contain_sentinel(self):
        ctx = _make_ctx("bearer", SENTINEL.encode("utf-8"))
        r = repr(ctx)
        assert SENTINEL not in r, f"Sentinel leaked into repr: {r!r}"

    def test_repr_does_not_contain_secret_value(self):
        ctx = _make_ctx("bearer", b"my_super_secret_token")
        r = repr(ctx)
        assert "my_super_secret_token" not in r


# ---------------------------------------------------------------------------
# Task 2: from_cli() tests (added after Task 1 TDD cycle)
# ---------------------------------------------------------------------------

class TestFromCliAtFile:
    def test_bearer_at_file(self):
        from quirk.auth.credentials import CredentialContext
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", dir=".", delete=False) as f:
            f.write("my_bearer_token\n")
            fname = f.name
        try:
            ctx = CredentialContext.from_cli(bearer=f"@{fname}")
            assert ctx is not None
            assert ctx.as_headers() == {"Authorization": "Bearer my_bearer_token"}
        finally:
            os.unlink(fname)

    def test_api_key_query_at_file(self):
        from quirk.auth.credentials import CredentialContext
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", dir=".", delete=False) as f:
            f.write("querykey\n")
            fname = f.name
        try:
            ctx = CredentialContext.from_cli(api_key_query=f"@{fname}")
            assert ctx is not None
            assert ctx.as_headers() == {}
            result = ctx.query_param()
            assert result is not None
            param, val = result
            assert val == "querykey"
        finally:
            os.unlink(fname)

    def test_at_file_blocked_prefix(self):
        from quirk.auth.credentials import CredentialContext
        from quirk.util.targets import TargetFileError
        with pytest.raises((TargetFileError, ValueError)):
            CredentialContext.from_cli(bearer="@/etc/passwd")


class TestFromCliEnvVar:
    def test_bearer_env_var(self):
        from quirk.auth.credentials import CredentialContext
        os.environ["TEST_QUIRK_TOKEN"] = "env_bearer_value"
        ctx = CredentialContext.from_cli(bearer="TEST_QUIRK_TOKEN")
        assert ctx is not None
        assert ctx.as_headers() == {"Authorization": "Bearer env_bearer_value"}
        # env var must be deleted after consumption
        assert "TEST_QUIRK_TOKEN" not in os.environ

    def test_env_var_deleted_after_consumption(self):
        from quirk.auth.credentials import CredentialContext
        os.environ["TEST_QUIRK_API_KEY"] = "env_api_value"
        ctx = CredentialContext.from_cli(api_key="TEST_QUIRK_API_KEY")
        assert ctx is not None
        assert "TEST_QUIRK_API_KEY" not in os.environ


class TestFromCliNone:
    def test_no_args_returns_none(self):
        from quirk.auth.credentials import CredentialContext
        result = CredentialContext.from_cli()
        assert result is None


class TestFromCliInlineSecretRejected:
    def test_literal_not_env_var_raises_value_error(self):
        from quirk.auth.credentials import CredentialContext
        # A string that is neither @file nor a set env var should raise ValueError
        env_key = "QUIRK_DEFINITELY_NOT_SET_XYZ123"
        assert env_key not in os.environ
        with pytest.raises(ValueError) as exc_info:
            CredentialContext.from_cli(bearer=env_key)
        # error message should not echo the raw value verbatim as a "secret"
        # (here the value IS the env-var name, which is fine — just must not
        # contain the actual credential if it was an accidental inline secret)
        err_msg = str(exc_info.value)
        assert len(err_msg) > 0  # some guidance provided


# ---------------------------------------------------------------------------
# Phase 94 / TOKEN-02: bearer_declared_alg() — passive JWT alg classification
# ---------------------------------------------------------------------------

def _make_jwt(header: dict) -> str:
    import base64, json
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    return f"{b(header)}.{b({'sub': 'x'})}.sig"


def test_bearer_declared_alg_returns_jwt_alg():
    """TOKEN-02: a bearer JWT yields its declared alg (unverified header decode)."""
    ctx = _make_ctx("bearer", _make_jwt({"alg": "RS256", "typ": "JWT"}).encode())
    assert ctx.bearer_declared_alg() == "RS256"


def test_bearer_declared_alg_opaque_token_returns_none():
    """An opaque (non-JWT) bearer token has no declared alg."""
    ctx = _make_ctx("bearer", b"opaque-not-a-jwt")
    assert ctx.bearer_declared_alg() is None


def test_bearer_declared_alg_non_bearer_returns_none():
    """Non-bearer schemes never expose a declared alg."""
    ctx = _make_ctx("api_key_header", b"secret", header_name="X-Api-Key")
    assert ctx.bearer_declared_alg() is None


def test_bearer_declared_alg_does_not_leak_token():
    """The returned value is the alg string only — never the raw token."""
    secret = _make_jwt({"alg": "ES256"}).encode()
    ctx = _make_ctx("bearer", secret)
    result = ctx.bearer_declared_alg()
    assert result == "ES256"
    # The full token string must not be returned.
    assert secret.decode() not in (result or "")
