"""Tests for database connector -- PostgreSQL, MySQL, RDS (DB-01, DB-02, DB-03).

Tests mock psycopg2, PyMySQL, and boto3 to avoid network/DB connections.
Scanner modules: quirk/scanner/db_connector.py (Phase 27 -- not yet created, tests RED),
                 quirk/scanner/aws_connector.py (RDS extension)
"""
import pytest
from unittest.mock import patch, MagicMock, call
from sqlalchemy import create_engine, inspect as sa_inspect
from quirk.models import Base


# ---------------------------------------------------------------------------
# Schema / infrastructure tests (DB-01 / DB-02 -- dat_scan_json column)
# ---------------------------------------------------------------------------

def test_schema_fresh_db_has_dat_scan_json():
    """CryptoEndpoint model must have dat_scan_json column (D-07)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    col_names = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    assert "dat_scan_json" in col_names, "CryptoEndpoint model missing dat_scan_json column"


def test_v43_columns_idempotent():
    """_ensure_columns(crypto_endpoints, _V43_COLUMNS) must not raise on second
    call (idempotent guard).

    Phase 77 D-21: prior `_ensure_v43_columns` helper was consolidated into the
    generic `_ensure_columns` entry point + `_V43_COLUMNS` tuple constant.
    Idempotency semantic is unchanged.
    """
    from quirk.db import _V43_COLUMNS, _ensure_columns
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    _ensure_columns(engine, "crypto_endpoints", _V43_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _V43_COLUMNS)  # second call must not raise


# ---------------------------------------------------------------------------
# PostgreSQL tests (DB-01)
# ---------------------------------------------------------------------------

def test_pg_unavailable_returns_empty():
    """scan_pg_targets must return [] when psycopg2 is not installed (PSYCOPG2_AVAILABLE=False)."""
    with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", False):
        from quirk.scanner.db_connector import scan_pg_targets
        result = scan_pg_targets(targets=["localhost:5432"])
        assert result == []


def test_pg_ssl_off_produces_high():
    """PostgreSQL SHOW ssl = 'off' must produce a HIGH finding with protocol=POSTGRESQL and service_detail containing 'ssl-off'."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("off",)
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    mock_psycopg2 = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn

    with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.psycopg2", mock_psycopg2):
        from quirk.scanner.db_connector import scan_pg_targets
        results = scan_pg_targets(targets=["localhost:5432"], user="u", password="p")

    assert len(results) >= 1
    ep = results[0]
    assert ep.protocol == "POSTGRESQL"
    assert ep.severity == "HIGH"
    assert "ssl-off" in str(ep.service_detail)


def test_pg_no_privilege_produces_scan_error():
    """PostgreSQL with ssl=on but pg_read_all_stats absent must produce scan_error='insufficient-privilege' with INFO severity."""
    call_count = [0]

    mock_cursor = MagicMock()

    def fetchone_side(*args):
        call_count[0] += 1
        if call_count[0] == 1:
            return ("on",)   # SHOW ssl -> on
        return (False,)       # pg_has_role -> False (no privilege)

    mock_cursor.fetchone.side_effect = fetchone_side
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    mock_psycopg2 = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn

    with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.psycopg2", mock_psycopg2):
        from quirk.scanner.db_connector import scan_pg_targets
        results = scan_pg_targets(targets=["localhost:5432"], user="u", password="p")

    assert len(results) >= 1
    ep = results[0]
    assert ep.protocol == "POSTGRESQL"
    assert ep.scan_error == "insufficient-privilege"
    assert ep.severity == "INFO"


def test_pg_plaintext_connections_high():
    """PostgreSQL with ssl=on, pg_read_all_stats present, non-SSL connections found must produce HIGH finding."""
    call_count = [0]

    mock_cursor = MagicMock()

    def fetchone_side(*args):
        call_count[0] += 1
        if call_count[0] == 1:
            return ("on",)   # SHOW ssl -> on
        if call_count[0] == 2:
            return (True,)   # pg_has_role -> True (privilege present)
        return (3,)           # COUNT of non-SSL rows -> 3

    mock_cursor.fetchone.side_effect = fetchone_side
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    mock_psycopg2 = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn

    with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.psycopg2", mock_psycopg2):
        from quirk.scanner.db_connector import scan_pg_targets
        results = scan_pg_targets(targets=["localhost:5432"], user="u", password="p")

    assert any(ep.severity == "HIGH" for ep in results), "Expected HIGH finding for non-SSL connections"


def test_pg_session_start_used_for_scanned_at():
    """scan_pg_targets must pass session_start to scanned_at timestamp (ISSUE-3 pattern)."""
    from datetime import datetime, timezone
    session_start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("off",)
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    mock_psycopg2 = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn

    with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.psycopg2", mock_psycopg2):
        from quirk.scanner.db_connector import scan_pg_targets
        results = scan_pg_targets(targets=["localhost:5432"], session_start=session_start)

    assert len(results) >= 1
    assert results[0].scanned_at == datetime(2026, 1, 1, 12, 0, 0)  # tzinfo stripped


# ---------------------------------------------------------------------------
# MySQL tests (DB-02)
# ---------------------------------------------------------------------------

def test_mysql_unavailable_returns_empty():
    """scan_mysql_targets must return [] when PyMySQL is not installed (PYMYSQL_AVAILABLE=False)."""
    with patch("quirk.scanner.db_connector.PYMYSQL_AVAILABLE", False):
        from quirk.scanner.db_connector import scan_mysql_targets
        result = scan_mysql_targets(targets=["localhost:3306"])
        assert result == []


def test_mysql_ssl_off_high():
    """MySQL Ssl_cipher empty must produce HIGH finding with service_detail='MySQL/ssl-off'."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("Ssl_cipher", "")  # empty cipher = SSL disabled
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    mock_pymysql = MagicMock()
    mock_pymysql.connect.return_value = mock_conn

    with patch("quirk.scanner.db_connector.PYMYSQL_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.pymysql", mock_pymysql):
        from quirk.scanner.db_connector import scan_mysql_targets
        results = scan_mysql_targets(targets=["localhost:3306"], user="u", password="p")

    assert len(results) >= 1
    ep = results[0]
    assert ep.protocol == "MYSQL"
    assert ep.severity == "HIGH"
    assert ep.service_detail == "MySQL/ssl-off"


def test_mysql_weak_cipher_medium():
    """MySQL Ssl_cipher with RC4 prefix must produce MEDIUM finding with service_detail containing '-weak'."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("Ssl_cipher", "RC4-SHA")
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    mock_pymysql = MagicMock()
    mock_pymysql.connect.return_value = mock_conn

    with patch("quirk.scanner.db_connector.PYMYSQL_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.pymysql", mock_pymysql):
        from quirk.scanner.db_connector import scan_mysql_targets
        results = scan_mysql_targets(targets=["localhost:3306"], user="u", password="p")

    assert len(results) >= 1
    ep = results[0]
    assert ep.protocol == "MYSQL"
    assert ep.severity == "MEDIUM"
    assert "-weak" in str(ep.service_detail)


def test_mysql_strong_cipher_no_finding():
    """MySQL with AES-256-GCM cipher must produce no finding (informational only -- no severity)."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("Ssl_cipher", "ECDHE-RSA-AES256-GCM-SHA384")
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    mock_pymysql = MagicMock()
    mock_pymysql.connect.return_value = mock_conn

    with patch("quirk.scanner.db_connector.PYMYSQL_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.pymysql", mock_pymysql):
        from quirk.scanner.db_connector import scan_mysql_targets
        results = scan_mysql_targets(targets=["localhost:3306"], user="u", password="p")

    # No findings with severity HIGH or MEDIUM
    assert all(
        getattr(ep, "severity", None) not in ("HIGH", "MEDIUM") for ep in results
    ), "Strong cipher should not produce HIGH or MEDIUM finding"


# ---------------------------------------------------------------------------
# RDS tests (DB-03) -- test _scan_rds_encryption via scan_aws_targets mock
# ---------------------------------------------------------------------------

def test_rds_unencrypted_high():
    """RDS instance with StorageEncrypted=False must produce HIGH finding with service_detail='RDS/none'."""
    mock_page = {"DBInstances": [{"DBInstanceIdentifier": "mydb", "DBInstanceArn": "arn:aws:rds:us-east-1:123:db:mydb", "StorageEncrypted": False, "KmsKeyId": ""}]}
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [mock_page]
    mock_rds = MagicMock()
    mock_rds.get_paginator.return_value = mock_paginator
    mock_session = MagicMock()
    mock_session.client.return_value = mock_rds

    with patch("quirk.scanner.aws_connector.BOTO3_AVAILABLE", True), \
         patch("quirk.scanner.aws_connector.boto3") as mock_boto3:
        mock_boto3.Session.return_value = mock_session
        from quirk.scanner.aws_connector import scan_aws_targets
        results = scan_aws_targets(region="us-east-1", profile=None)

    rds_results = [ep for ep in results if getattr(ep, "protocol", "") == "RDS"]
    assert len(rds_results) >= 1
    ep = rds_results[0]
    assert ep.severity == "HIGH"
    assert ep.service_detail == "RDS/none"


def test_rds_sse_rds_service_detail():
    """RDS instance with StorageEncrypted=True and no KmsKeyId must produce service_detail='RDS/sse-rds'."""
    mock_page = {"DBInstances": [{"DBInstanceIdentifier": "mydb", "DBInstanceArn": "arn:aws:rds:us-east-1:123:db:mydb", "StorageEncrypted": True, "KmsKeyId": ""}]}
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [mock_page]
    mock_rds = MagicMock()
    mock_rds.get_paginator.return_value = mock_paginator
    mock_session = MagicMock()
    mock_session.client.return_value = mock_rds

    with patch("quirk.scanner.aws_connector.BOTO3_AVAILABLE", True), \
         patch("quirk.scanner.aws_connector.boto3") as mock_boto3:
        mock_boto3.Session.return_value = mock_session
        from quirk.scanner.aws_connector import scan_aws_targets
        results = scan_aws_targets(region="us-east-1", profile=None)

    rds_results = [ep for ep in results if getattr(ep, "protocol", "") == "RDS"]
    assert len(rds_results) >= 1
    assert rds_results[0].service_detail == "RDS/sse-rds"


def test_rds_cmk_service_detail():
    """RDS instance with StorageEncrypted=True and CMK ARN must produce service_detail='RDS/sse-kms-cmk'."""
    mock_page = {"DBInstances": [{"DBInstanceIdentifier": "mydb", "DBInstanceArn": "arn:aws:rds:us-east-1:123:db:mydb", "StorageEncrypted": True, "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/mrk-abc123def456"}]}
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [mock_page]
    mock_rds = MagicMock()
    mock_rds.get_paginator.return_value = mock_paginator
    mock_session = MagicMock()
    mock_session.client.return_value = mock_rds

    with patch("quirk.scanner.aws_connector.BOTO3_AVAILABLE", True), \
         patch("quirk.scanner.aws_connector.boto3") as mock_boto3:
        mock_boto3.Session.return_value = mock_session
        from quirk.scanner.aws_connector import scan_aws_targets
        results = scan_aws_targets(region="us-east-1", profile=None)

    rds_results = [ep for ep in results if getattr(ep, "protocol", "") == "RDS"]
    assert len(rds_results) >= 1
    assert rds_results[0].service_detail == "RDS/sse-kms-cmk"


# ---------------------------------------------------------------------------
# Phase 72 D-20 / WR-07: password=None kwarg handling
# Phase 72 D-21 / WR-08: mysql safe_str exception coverage
# ---------------------------------------------------------------------------

def _capture_pg_kwargs(captured):
    """Build a psycopg2.connect mock that captures kwargs and raises after."""
    def _fake_connect(**kwargs):
        captured.update(kwargs)
        raise RuntimeError("stop-after-capture")
    return _fake_connect


def _capture_my_kwargs(captured):
    def _fake_connect(**kwargs):
        captured.update(kwargs)
        raise RuntimeError("stop-after-capture")
    return _fake_connect


def test_pg_connect_password_none_omits_kwarg():
    """password=None must omit the password kwarg entirely (libpq reads .pgpass)."""
    captured = {}
    mock_pg = MagicMock()
    mock_pg.connect.side_effect = _capture_pg_kwargs(captured)
    with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.psycopg2", mock_pg):
        from quirk.scanner.db_connector import scan_pg_targets
        scan_pg_targets(targets=["localhost:5432"], user="u", password=None)
    assert "password" not in captured, f"password kwarg must be omitted; got {captured}"


def test_pg_connect_password_empty_string_passes_through():
    """password='' must be passed through (explicit empty-password attempt)."""
    captured = {}
    mock_pg = MagicMock()
    mock_pg.connect.side_effect = _capture_pg_kwargs(captured)
    with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.psycopg2", mock_pg):
        from quirk.scanner.db_connector import scan_pg_targets
        scan_pg_targets(targets=["localhost:5432"], user="u", password="")
    assert captured.get("password") == "", f"password='' must pass through; got {captured}"


def test_pg_connect_password_nonempty_passes_through():
    """password='secret' must be passed through normally."""
    captured = {}
    mock_pg = MagicMock()
    mock_pg.connect.side_effect = _capture_pg_kwargs(captured)
    with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.psycopg2", mock_pg):
        from quirk.scanner.db_connector import scan_pg_targets
        scan_pg_targets(targets=["localhost:5432"], user="u", password="secret")
    assert captured.get("password") == "secret"


def test_mysql_connect_password_none_omits_kwarg():
    """MySQL: password=None must omit the password kwarg."""
    captured = {}
    mock_my = MagicMock()
    mock_my.connect.side_effect = _capture_my_kwargs(captured)
    with patch("quirk.scanner.db_connector.PYMYSQL_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.pymysql", mock_my):
        from quirk.scanner.db_connector import scan_mysql_targets
        scan_mysql_targets(targets=["localhost:3306"], user="u", password=None)
    assert "password" not in captured, f"password kwarg must be omitted; got {captured}"


def test_mysql_exception_uses_safe_str():
    """MySQL exception with credential-bearing message must be sanitized via safe_str.
    safe_str (Phase 59) matches long base64-shaped tokens and Authorization headers;
    when triggered it returns just the exception class name, dropping the message."""
    leaky_token = "AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHHIIIIJJJJKKKKLLLLMMMM"
    mock_my = MagicMock()
    mock_my.connect.side_effect = RuntimeError(
        f"Access denied — token leaked in error: {leaky_token}"
    )
    with patch("quirk.scanner.db_connector.PYMYSQL_AVAILABLE", True), \
         patch("quirk.scanner.db_connector.pymysql", mock_my):
        from quirk.scanner.db_connector import scan_mysql_targets
        results = scan_mysql_targets(targets=["localhost:3306"], user="u", password="secret")
    err_endpoints = [r for r in results if getattr(r, "scan_error", None)]
    assert err_endpoints, "expected at least one scan_error endpoint"
    for ep in err_endpoints:
        assert leaky_token not in (ep.scan_error or ""), (
            f"safe_str must strip credentials; got: {ep.scan_error}"
        )
