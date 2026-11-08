"""Phase 235.3 plan 01: per-target outcome sink + exception classifiers."""
from __future__ import annotations

import pytest

from quirk.scanner import target_outcome as to
from quirk.scanner.target_outcome import (
    OUTCOME_ANSWERED, OUTCOME_AUTH_FAILED, OUTCOME_MISSING_CREDENTIALS,
    OUTCOME_REFUSED, OUTCOME_UNREACHABLE, TargetOutcomeContractError,
    TargetOutcomes,
)
from quirk.util import url_allowlist as ua


def _stub(name, **attrs):
    cls = type(name, (Exception,), {})
    exc = cls("boom")
    for k, v in attrs.items():
        setattr(exc, k, v)
    return exc


def test_outcome_display_label_redacts_userinfo_and_query():
    raw = "http://u:p@localhost:20001/x?q=1"
    o = TargetOutcomes([raw])
    o.record(raw, OUTCOME_UNREACHABLE, "down")
    for r in o.resolved():
        assert "u:p" not in r.target and "?q=1" not in r.target
    assert "u:p" not in o.labels[raw]


@pytest.mark.parametrize("raw,label", [
    ("user:pass@reg.io/img:1", "reg.io/img:1"),
    ("u:p@10.0.0.1:443", "10.0.0.1:443"),
    ("reg.io/img@sha256:abcd", "reg.io/img@sha256:abcd"),
    ("host:5000/a/b:tag", "host:5000/a/b:tag"),
    ("alice@corp.example", "alice@corp.example"),
])
def test_outcome_label_redacts_schemeless_userinfo_password(raw, label):
    # 235.3-20 found scheme-less refs (container images) kept user:pass@.
    assert to.redact_target(raw) == label
    o = TargetOutcomes([raw])
    o.record(raw, OUTCOME_UNREACHABLE, "down")
    assert all("pass" not in r.target for r in o.resolved())


def test_outcome_no_collision_on_shared_prefix_and_query():
    a = "https://login.example.com/" + "t" * 60 + "/discovery/keys"
    b = "https://login.example.com/" + "t" * 60 + "/discovery/v2.0/keys"
    c, d = "https://h/x?tenant=a", "https://h/x?tenant=b"
    o = TargetOutcomes([a, b, c, d])
    assert len(o.expected) == 4
    o.answered(a)
    o.record(b, OUTCOME_UNREACHABLE, "x")
    o.answered(c)
    o.record(d, OUTCOME_UNREACHABLE, "x")
    kinds = [r.kind for r in o.resolved()]
    assert kinds == [OUTCOME_ANSWERED, OUTCOME_UNREACHABLE, OUTCOME_ANSWERED, OUTCOME_UNREACHABLE]


def test_outcome_non_string_target_coerced():
    o = TargetOutcomes([123])
    assert o.expected == ["123"]
    o.record(123, OUTCOME_UNREACHABLE)
    assert o.resolved()[0].kind == OUTCOME_UNREACHABLE


def test_outcome_duplicate_target_is_one_entry():
    assert TargetOutcomes(["a", "a"]).expected == ["a"]


def test_outcome_label_contract_violation_and_extra():
    o = TargetOutcomes(["s3:us-east-1"])
    with pytest.raises(TargetOutcomeContractError) as ei:
        o.record("s3:http://127.0.0.1:9000", OUTCOME_ANSWERED)
    assert isinstance(ei.value, ValueError)
    o.record("s3:http://127.0.0.1:9000", OUTCOME_ANSWERED, extra=True)
    res = o.resolved()
    assert res[0].kind == OUTCOME_UNREACHABLE
    assert res[0].detail == "no outcome recorded by scanner"
    o.record(o.sole_target(), OUTCOME_ANSWERED)
    assert o.resolved()[0].kind == OUTCOME_ANSWERED


def test_outcome_sole_target_requires_one():
    with pytest.raises(ValueError):
        TargetOutcomes(["a", "b"]).sole_target()


def test_outcome_keys_are_raw_not_redacted():
    raw = "http://user:pw@host:1/p?x=1"
    o = TargetOutcomes([raw])
    o.record(raw, OUTCOME_ANSWERED)
    with pytest.raises(TargetOutcomeContractError):
        o.record(to.redact_target(raw), OUTCOME_ANSWERED)


def test_outcome_unknown_kind_and_answered_wins():
    o = TargetOutcomes(["t"])
    with pytest.raises(ValueError):
        o.record("t", "bogus")
    o.record("t", OUTCOME_REFUSED)
    o.answered("t")
    assert o.resolved()[0].kind == OUTCOME_ANSWERED


def test_outcome_priority_missing_credentials_beats_unreachable():
    o = TargetOutcomes(["t"])
    o.record("t", OUTCOME_UNREACHABLE)
    o.record("t", OUTCOME_MISSING_CREDENTIALS)
    assert o.resolved()[0].kind == OUTCOME_MISSING_CREDENTIALS


def test_outcome_unrecorded_target_fails_closed():
    o = TargetOutcomes(["a", "b"])
    o.answered("a")
    r = o.resolved()
    assert r[1].kind == OUTCOME_UNREACHABLE
    assert r[1].detail == "no outcome recorded by scanner"


def test_outcome_url_guard_mapping():
    assert to.outcome_for_url_guard(ua.RC_LOOPBACK)[0] == OUTCOME_REFUSED
    kind, detail = to.outcome_for_url_guard(ua.RC_METADATA_SERVICE_IP)
    assert kind == OUTCOME_UNREACHABLE and "always blocked" in detail
    assert to.outcome_for_url_guard(ua.RC_DNS_FAILURE)[0] == OUTCOME_UNREACHABLE


def test_outcome_cloud_exception_classification():
    k, d = to.outcome_for_cloud_exception(
        _stub("ClientError", response={"Error": {"Code": "AccessDenied"}}))
    assert k == OUTCOME_AUTH_FAILED and "lack a required IAM permission" in d
    assert to.outcome_for_cloud_exception(_stub("NoCredentialsError"))[0] == OUTCOME_MISSING_CREDENTIALS
    assert to.outcome_for_cloud_exception(
        _stub("ClientError", response={"Error": {"Code": "InvalidAccessKeyId"}}))[0] == OUTCOME_AUTH_FAILED
    assert to.outcome_for_cloud_exception(_stub("EndpointConnectionError"))[0] == OUTCOME_UNREACHABLE
    assert to.outcome_for_cloud_exception(_stub("ClientAuthenticationError"))[0] == OUTCOME_AUTH_FAILED


def test_outcome_cloud_exception_real_botocore():
    exceptions = pytest.importorskip("botocore.exceptions")
    assert to.outcome_for_cloud_exception(exceptions.NoCredentialsError())[0] == OUTCOME_MISSING_CREDENTIALS


def test_outcome_db_exception_classification():
    assert to.outcome_for_db_exception(Exception(1045, "Access denied for user"))[0] == OUTCOME_AUTH_FAILED
    assert to.outcome_for_db_exception(Exception("could not connect to server"))[0] == OUTCOME_UNREACHABLE


def test_outcome_vault_exception_classification():
    assert to.outcome_for_vault_exception(_stub("Unauthorized"))[0] == OUTCOME_AUTH_FAILED
    assert to.outcome_for_vault_exception(ConnectionError())[0] == OUTCOME_UNREACHABLE


def test_outcome_advisory_categories_and_skip_reasons():
    c = to.COVERAGE_SKIP_ADVISORY_CATEGORIES
    assert {"missing_extra", "missing_binary"} <= c and len(c) == 6
    assert all(len(x) <= 32 for x in c)
    assert to.PER_TARGET_ERROR_CATEGORY not in c
    from quirk.models import SCAN_PHASE_SKIP_REASONS as R
    assert len(R) == 8 and {"internal-target-refused", "auth-failed"} <= R


# ---------------------------------------------------------------------------
# 235.3 review A-WR-01: GCP / Azure / AWS permission denials are auth_failed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", [401, 403])
def test_outcome_cloud_gcp_http_error_401_403_is_auth_failed(status):
    errors = pytest.importorskip("googleapiclient.errors")
    httplib2 = pytest.importorskip("httplib2")
    exc = errors.HttpError(httplib2.Response({"status": str(status)}),
                           b'{"error": {"code": %d, "message": "denied"}}' % status)
    assert to.outcome_for_cloud_exception(exc)[0] == OUTCOME_AUTH_FAILED


def test_outcome_cloud_gcp_http_error_500_stays_unreachable():
    errors = pytest.importorskip("googleapiclient.errors")
    httplib2 = pytest.importorskip("httplib2")
    exc = errors.HttpError(httplib2.Response({"status": "503"}), b"unavailable")
    assert to.outcome_for_cloud_exception(exc)[0] == OUTCOME_UNREACHABLE


def test_outcome_cloud_gcp_refresh_error_is_auth_failed():
    gexc = pytest.importorskip("google.auth.exceptions")
    exc = gexc.RefreshError("invalid_grant: Token has been expired or revoked.")
    assert to.outcome_for_cloud_exception(exc)[0] == OUTCOME_AUTH_FAILED


@pytest.mark.parametrize("code", ["AuthorizationFailed", "Forbidden"])
def test_outcome_cloud_azure_permission_denial_is_auth_failed(code):
    az = pytest.importorskip("azure.core.exceptions")
    exc = az.HttpResponseError(message="denied")
    exc.error = type("E", (), {"code": code})()
    assert to.outcome_for_cloud_exception(exc)[0] == OUTCOME_AUTH_FAILED


def test_outcome_cloud_aws_unauthorized_operation_is_auth_failed():
    exceptions = pytest.importorskip("botocore.exceptions")
    exc = exceptions.ClientError(
        {"Error": {"Code": "UnauthorizedOperation", "Message": "no"}}, "DescribeKey")
    kind, detail = to.outcome_for_cloud_exception(exc)
    assert kind == OUTCOME_AUTH_FAILED and "lack a required IAM permission" in detail


# ---------------------------------------------------------------------------
# 235.3 review A-WR-02: Azure chain-exhausted "no credentials" is missing
# ---------------------------------------------------------------------------

def test_outcome_cloud_azure_default_credential_empty_env_is_missing(monkeypatch):
    identity = pytest.importorskip("azure.identity")
    import os
    for k in list(os.environ):
        if k.startswith(("AZURE_", "IDENTITY_", "MSI_")):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("PATH", "/nonexistent")  # no az / pwsh / azd on PATH
    cred = identity.DefaultAzureCredential(
        exclude_managed_identity_credential=True,
        exclude_shared_token_cache_credential=True,
        exclude_visual_studio_code_credential=True,
    )
    with pytest.raises(Exception) as ei:
        cred.get_token("https://management.azure.com/.default")
    assert to.outcome_for_cloud_exception(ei.value)[0] == OUTCOME_MISSING_CREDENTIALS


def test_outcome_cloud_azure_chain_with_real_rejection_is_auth_failed():
    az = pytest.importorskip("azure.core.exceptions")
    msg = (
        "DefaultAzureCredential failed to retrieve a token from the included credentials.\n"
        "Attempted credentials:\n"
        "\tEnvironmentCredential: EnvironmentCredential authentication unavailable. "
        "Environment variables are not fully configured.\n"
        "\tAzureCliCredential: AADSTS700082: The refresh token has expired due to inactivity.\n"
        "To mitigate this issue, please refer to the troubleshooting guidelines here at "
        "https://aka.ms/azsdk/python/identity/defaultazurecredential/troubleshoot."
    )
    exc = az.ClientAuthenticationError(message=msg)
    assert to.outcome_for_cloud_exception(exc)[0] == OUTCOME_AUTH_FAILED


def test_outcome_cloud_azure_401_client_auth_error_stays_auth_failed():
    az = pytest.importorskip("azure.core.exceptions")
    exc = az.ClientAuthenticationError(message="Unauthorized")
    exc.error = type("E", (), {"code": "InvalidAuthenticationToken"})()
    assert to.outcome_for_cloud_exception(exc)[0] == OUTCOME_AUTH_FAILED



# ---------------------------------------------------------------------------
# 235.3 review A-WR-08: libpq "no password supplied" / pg_hba rejection
# ---------------------------------------------------------------------------

def test_outcome_db_no_password_supplied_is_missing_credentials():
    exc = Exception("connection to server at \"db\" (10.0.0.5), port 5432 failed: "
                    "fe_sendauth: no password supplied\n")
    assert to.outcome_for_db_exception(exc)[0] == OUTCOME_MISSING_CREDENTIALS


def test_outcome_db_pg_hba_rejection_is_auth_failed():
    exc = Exception('connection to server at "db" (10.0.0.5), port 5432 failed: FATAL:  '
                    'no pg_hba.conf entry for host "10.0.0.9", user "quirk", '
                    'database "postgres", no encryption')
    assert to.outcome_for_db_exception(exc)[0] == OUTCOME_AUTH_FAILED


def test_outcome_db_password_authentication_failed_is_auth_failed():
    exc = Exception('FATAL:  password authentication failed for user "quirk"')
    assert to.outcome_for_db_exception(exc)[0] == OUTCOME_AUTH_FAILED


def test_outcome_db_real_psycopg2_no_password():
    """A real psycopg2 exception type carrying libpq's no-password message."""
    psycopg2 = pytest.importorskip("psycopg2")
    exc = psycopg2.OperationalError("fe_sendauth: no password supplied\n")
    assert to.outcome_for_db_exception(exc)[0] == OUTCOME_MISSING_CREDENTIALS
