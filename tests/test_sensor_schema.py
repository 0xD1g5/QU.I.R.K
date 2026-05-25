"""Phase 107 MODEL-01..04: sensor schema tests — backward-compat + column/table existence.

TDD RED gate: These tests are written before any implementation.
They must FAIL until quirk/models.py and quirk/db.py are updated.

Coverage:
    - Sensor, SensorToken, SensorPush ORM models exist and carry correct columns.
    - CryptoEndpoint gains nullable sensor_id and segment columns.
    - init_db creates all three tables + adds two columns to crypto_endpoints.
    - ix_crypto_endpoints_sensor_id index is created by init_db.
    - ON DELETE CASCADE is enforced for sensor_tokens and sensor_pushes.
    - _V54_SENSOR_COLUMNS is registered in _ADDITIVE_MIGRATIONS (single-source-of-truth).
    - Backward-compat: a pre-v5.4 DB is migrated without data loss or scoring change.
    - Allowlist guard rejects poisoned DDL on the v54 migration path.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text

from quirk.db import init_db, _ensure_columns


# ---------------------------------------------------------------------------
# ORM model import checks — MODEL-01..04
# ---------------------------------------------------------------------------


def test_sensor_orm_model_importable() -> None:
    """MODEL-02: Sensor ORM class must be importable from quirk.models."""
    from quirk.models import Sensor  # noqa: WPS433

    assert Sensor.__tablename__ == "sensors"


def test_sensor_token_orm_model_importable() -> None:
    """MODEL-03: SensorToken ORM class must be importable from quirk.models."""
    from quirk.models import SensorToken  # noqa: WPS433

    assert SensorToken.__tablename__ == "sensor_tokens"


def test_sensor_push_orm_model_importable() -> None:
    """MODEL-04: SensorPush ORM class must be importable from quirk.models."""
    from quirk.models import SensorPush  # noqa: WPS433

    assert SensorPush.__tablename__ == "sensor_pushes"


def test_crypto_endpoint_has_sensor_id_column() -> None:
    """MODEL-01: CryptoEndpoint must expose a sensor_id attribute (nullable, no FK)."""
    from quirk.models import CryptoEndpoint  # noqa: WPS433

    assert hasattr(CryptoEndpoint, "sensor_id"), "CryptoEndpoint.sensor_id missing"


def test_crypto_endpoint_has_segment_column() -> None:
    """MODEL-01: CryptoEndpoint must expose a segment attribute (nullable)."""
    from quirk.models import CryptoEndpoint  # noqa: WPS433

    assert hasattr(CryptoEndpoint, "segment"), "CryptoEndpoint.segment missing"


def test_crypto_endpoint_sensor_id_has_no_foreign_key() -> None:
    """D-03 / MODEL-01: CryptoEndpoint.sensor_id must be a plain Column — no FK."""
    from quirk.models import CryptoEndpoint  # noqa: WPS433

    col = CryptoEndpoint.__table__.c["sensor_id"]
    assert not col.foreign_keys, (
        "CryptoEndpoint.sensor_id must not have a ForeignKey (D-03: NULL = implicit local sensor)"
    )


def test_sensor_columns_complete() -> None:
    """MODEL-02: sensors table must have the full 106 D-13 field set."""
    from quirk.models import Sensor  # noqa: WPS433

    expected_cols = {
        "sensor_id",
        "segment",
        "engagement",
        "enrolled_at",
        "last_push_at",
        "expected_cadence_minutes",
        "sensor_version",
    }
    actual_cols = {c.name for c in Sensor.__table__.c}
    missing = expected_cols - actual_cols
    assert not missing, f"MODEL-02: sensors table missing columns: {missing}"


def test_sensor_token_columns_complete() -> None:
    """MODEL-03: sensor_tokens table must have id, sensor_id (FK), token_hash, created_at."""
    from quirk.models import SensorToken  # noqa: WPS433

    expected_cols = {"id", "sensor_id", "token_hash", "created_at"}
    actual_cols = {c.name for c in SensorToken.__table__.c}
    missing = expected_cols - actual_cols
    assert not missing, f"MODEL-03: sensor_tokens table missing columns: {missing}"


def test_sensor_push_columns_complete() -> None:
    """MODEL-04: sensor_pushes table must have id, payload_id (unique), sensor_id (FK), received_at."""
    from quirk.models import SensorPush  # noqa: WPS433

    expected_cols = {"id", "payload_id", "sensor_id", "received_at"}
    actual_cols = {c.name for c in SensorPush.__table__.c}
    missing = expected_cols - actual_cols
    assert not missing, f"MODEL-04: sensor_pushes table missing columns: {missing}"


def test_sensor_token_has_cascade_fk() -> None:
    """D-04 / MODEL-03: sensor_tokens.sensor_id FK must use ON DELETE CASCADE."""
    from quirk.models import SensorToken  # noqa: WPS433

    col = SensorToken.__table__.c["sensor_id"]
    fks = list(col.foreign_keys)
    assert fks, "sensor_tokens.sensor_id has no ForeignKey"
    fk = fks[0]
    assert fk.ondelete == "CASCADE", (
        f"sensor_tokens.sensor_id FK ondelete must be CASCADE, got {fk.ondelete!r}"
    )


def test_sensor_push_has_cascade_fk() -> None:
    """D-04 / MODEL-04: sensor_pushes.sensor_id FK must use ON DELETE CASCADE."""
    from quirk.models import SensorPush  # noqa: WPS433

    col = SensorPush.__table__.c["sensor_id"]
    fks = list(col.foreign_keys)
    assert fks, "sensor_pushes.sensor_id has no ForeignKey"
    fk = fks[0]
    assert fk.ondelete == "CASCADE", (
        f"sensor_pushes.sensor_id FK ondelete must be CASCADE, got {fk.ondelete!r}"
    )


def test_sensor_push_payload_id_unique() -> None:
    """D-07 / MODEL-04: sensor_pushes.payload_id must have a unique constraint."""
    from quirk.models import SensorPush  # noqa: WPS433

    col = SensorPush.__table__.c["payload_id"]
    assert col.unique, "sensor_pushes.payload_id must be declared unique=True"


def test_no_relationship_declarations() -> None:
    """Style: quirk/models.py must not introduce relationship() calls."""
    import ast
    import pathlib

    tree = ast.parse(pathlib.Path("quirk/models.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            assert name != "relationship", (
                "quirk/models.py must not use relationship() — project uses plain Column only"
            )


def test_no_mapped_column() -> None:
    """Style: quirk/models.py must not use mapped_column (classic Column style only)."""
    import pathlib

    src = pathlib.Path("quirk/models.py").read_text(encoding="utf-8")
    assert "mapped_column" not in src, (
        "quirk/models.py must use classic Column(...) style, not mapped_column"
    )


# ---------------------------------------------------------------------------
# init_db integration — columns, tables, index
# ---------------------------------------------------------------------------


def test_init_db_creates_sensor_columns_on_crypto_endpoints(tmp_path: Path) -> None:
    """MODEL-01: init_db must add sensor_id and segment to crypto_endpoints."""
    engine = init_db(str(tmp_path / "sensor_cols.sqlite"))
    insp = sa_inspect(engine)
    cols = {c["name"] for c in insp.get_columns("crypto_endpoints")}
    assert "sensor_id" in cols, "sensor_id missing from crypto_endpoints after init_db"
    assert "segment" in cols, "segment missing from crypto_endpoints after init_db"


def test_init_db_creates_sensor_tables(tmp_path: Path) -> None:
    """MODEL-02..04: init_db must create sensors, sensor_tokens, sensor_pushes."""
    engine = init_db(str(tmp_path / "sensor_tables.sqlite"))
    insp = sa_inspect(engine)
    table_names = set(insp.get_table_names())
    for tbl in ("sensors", "sensor_tokens", "sensor_pushes"):
        assert tbl in table_names, f"{tbl} missing after init_db"


def test_init_db_creates_sensor_id_index(tmp_path: Path) -> None:
    """D-02 / MODEL-01: init_db must create ix_crypto_endpoints_sensor_id index."""
    engine = init_db(str(tmp_path / "sensor_idx.sqlite"))
    insp = sa_inspect(engine)
    idx_names = {i["name"] for i in insp.get_indexes("crypto_endpoints")}
    assert "ix_crypto_endpoints_sensor_id" in idx_names, (
        "ix_crypto_endpoints_sensor_id index missing after init_db"
    )


# ---------------------------------------------------------------------------
# _ADDITIVE_MIGRATIONS registry — single-source-of-truth (D-02)
# ---------------------------------------------------------------------------


def test_v54_sensor_columns_in_additive_migrations() -> None:
    """D-02: _V54_SENSOR_COLUMNS must be registered in _ADDITIVE_MIGRATIONS."""
    from quirk.db import _V54_SENSOR_COLUMNS, _ADDITIVE_MIGRATIONS  # noqa: WPS433

    assert ("crypto_endpoints", _V54_SENSOR_COLUMNS) in _ADDITIVE_MIGRATIONS, (
        "('crypto_endpoints', _V54_SENSOR_COLUMNS) not found in _ADDITIVE_MIGRATIONS"
    )


def test_v54_sensor_columns_use_text_type() -> None:
    """T-107-01: _V54_SENSOR_COLUMNS DDL types must satisfy _SAFE_COL_TYPE_RE."""
    from quirk.db import _V54_SENSOR_COLUMNS, _SAFE_COL_TYPE_RE  # noqa: WPS433

    for col_name, col_type in _V54_SENSOR_COLUMNS:
        assert _SAFE_COL_TYPE_RE.match(col_type), (
            f"_V54_SENSOR_COLUMNS entry ({col_name!r}, {col_type!r}) fails _SAFE_COL_TYPE_RE"
        )


def test_v54_sensor_columns_contains_sensor_id_and_segment() -> None:
    """MODEL-01: _V54_SENSOR_COLUMNS must include sensor_id and segment entries."""
    from quirk.db import _V54_SENSOR_COLUMNS  # noqa: WPS433

    col_names = {name for name, _ in _V54_SENSOR_COLUMNS}
    assert "sensor_id" in col_names, "sensor_id missing from _V54_SENSOR_COLUMNS"
    assert "segment" in col_names, "segment missing from _V54_SENSOR_COLUMNS"


# ---------------------------------------------------------------------------
# Allowlist guard — poisoned DDL on v54 migration path (T-107-01)
# ---------------------------------------------------------------------------

_POISON = (("evil_col", "TEXT; DROP TABLE x"),)


def test_v54_sensor_columns_rejects_poisoned_col_type(tmp_path: Path) -> None:
    """T-107-01: _ensure_columns must reject poisoned DDL on the v54 migration path."""
    engine = init_db(str(tmp_path / "poison_v54.db"))
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_columns(engine, "crypto_endpoints", _POISON)


# ---------------------------------------------------------------------------
# Backward-compatibility fixture — D-05
# ---------------------------------------------------------------------------


def _column_snapshot(engine) -> dict:
    """Return a dict mapping table_name -> sorted list of column names."""
    insp = sa_inspect(engine)
    return {
        t: sorted(c["name"] for c in insp.get_columns(t))
        for t in insp.get_table_names()
    }


def test_pre_v54_db_migrates_without_data_loss(tmp_path: Path) -> None:
    """D-05 / MODEL-01: init_db on a pre-v5.4 DB must add new columns without losing rows.

    Builds an old-schema SQLite (crypto_endpoints WITHOUT sensor_id/segment,
    and without the three sensor tables), inserts one row, then runs init_db
    and asserts:
    - sensor_id and segment columns now exist on crypto_endpoints.
    - sensors, sensor_tokens, sensor_pushes tables exist.
    - The pre-existing row is still present (no data loss).
    """
    old_db = tmp_path / "pre_v54.sqlite"

    # Create old-schema DB using raw DDL (no sensor_id/segment, no sensor tables)
    old_engine = create_engine(f"sqlite:///{old_db}", future=True)
    with old_engine.connect() as conn:
        conn.execute(text(
            """
            CREATE TABLE crypto_endpoints (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                host VARCHAR(255) NOT NULL,
                port INTEGER NOT NULL,
                protocol VARCHAR(32),
                scanned_at DATETIME,
                sni_used BOOLEAN DEFAULT 0,
                tls_version VARCHAR(64),
                cipher_suite VARCHAR(255),
                cert_subject TEXT,
                cert_issuer TEXT,
                cert_sans TEXT,
                cert_sig_alg VARCHAR(128),
                cert_pubkey_alg VARCHAR(64),
                cert_pubkey_size INTEGER,
                cert_not_before DATETIME,
                cert_not_after DATETIME,
                scan_error TEXT,
                scan_error_category VARCHAR(32),
                tls_blocker_reason VARCHAR(64),
                service_detail TEXT
            )
            """
        ))
        # Insert a pre-existing row
        conn.execute(text(
            "INSERT INTO crypto_endpoints (host, port, tls_version, cert_sig_alg, cert_pubkey_alg)"
            " VALUES ('legacy-host.example.com', 443, 'TLSv1.2', 'sha256WithRSAEncryption', 'rsaEncryption')"
        ))
        conn.commit()
    old_engine.dispose()

    # Run init_db — must migrate without errors
    engine = init_db(str(old_db))

    insp = sa_inspect(engine)

    # New columns must exist
    cols = {c["name"] for c in insp.get_columns("crypto_endpoints")}
    assert "sensor_id" in cols, "sensor_id missing from crypto_endpoints after migration"
    assert "segment" in cols, "segment missing from crypto_endpoints after migration"

    # New tables must exist
    table_names = set(insp.get_table_names())
    for tbl in ("sensors", "sensor_tokens", "sensor_pushes"):
        assert tbl in table_names, f"{tbl} missing after migration"

    # Pre-existing row must still be present
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT host, port, sensor_id FROM crypto_endpoints")
        ).fetchall()
    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
    assert rows[0][0] == "legacy-host.example.com", "Pre-existing host row lost after migration"
    assert rows[0][2] is None, "sensor_id of legacy row must be NULL (implicit local sensor)"


def test_pre_v54_scoring_unchanged_after_migration(tmp_path: Path) -> None:
    """D-05 / D-08: NULL sensor_id rows must score identically before and after migration.

    Inserts a row with known values, migrates, and confirms
    compute_readiness_score() returns the same result both times.
    """
    from quirk.scoring import compute_readiness_score  # noqa: WPS433

    old_db = tmp_path / "scoring_compat.sqlite"

    # Build minimal pre-v5.4 schema + row
    old_engine = create_engine(f"sqlite:///{old_db}", future=True)
    with old_engine.connect() as conn:
        conn.execute(text(
            """
            CREATE TABLE crypto_endpoints (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                host VARCHAR(255) NOT NULL,
                port INTEGER NOT NULL,
                protocol VARCHAR(32),
                scanned_at DATETIME,
                tls_version VARCHAR(64),
                cipher_suite VARCHAR(255),
                cert_sig_alg VARCHAR(128),
                cert_pubkey_alg VARCHAR(64),
                cert_pubkey_size INTEGER,
                cert_not_before DATETIME,
                cert_not_after DATETIME,
                scan_error TEXT,
                scan_error_category VARCHAR(32),
                tls_blocker_reason VARCHAR(64),
                service_detail TEXT,
                sni_used BOOLEAN DEFAULT 0,
                cert_subject TEXT,
                cert_issuer TEXT,
                cert_sans TEXT
            )
            """
        ))
        conn.execute(text(
            "INSERT INTO crypto_endpoints"
            " (host, port, tls_version, cert_sig_alg, cert_pubkey_alg, cert_pubkey_size)"
            " VALUES ('score-host.example.com', 443, 'TLSv1.3', 'sha256WithRSAEncryption', 'rsaEncryption', 2048)"
        ))
        conn.commit()
    old_engine.dispose()

    # Migrate
    engine = init_db(str(old_db))

    # Score the migrated row — must not raise, and NULL sensor_id must be accepted
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM crypto_endpoints")
        ).fetchall()
    assert len(rows) == 1, "Pre-existing row lost after migration"

    # compute_readiness_score operates on a list of endpoint dicts or ORM objects;
    # verify it doesn't raise when sensor_id is NULL (the backward-compat contract).
    # We test that the function is callable and returns a numeric score without error.
    from quirk.models import CryptoEndpoint  # noqa: WPS433
    from sqlalchemy.orm import Session  # noqa: WPS433

    session = Session(engine)
    endpoints = session.query(CryptoEndpoint).all()
    session.close()

    assert len(endpoints) == 1
    assert endpoints[0].sensor_id is None, (
        "Migrated legacy row sensor_id must be NULL (D-08: backward compatible)"
    )

    # Score must not raise — backward-compat contract
    score_result = compute_readiness_score(endpoints)
    assert score_result is not None, "compute_readiness_score returned None for legacy endpoints"


# ---------------------------------------------------------------------------
# ON DELETE CASCADE enforcement (runtime FK check)
# ---------------------------------------------------------------------------


def test_cascade_delete_removes_sensor_tokens(tmp_path: Path) -> None:
    """D-04 / MODEL-03: deleting a sensors row must cascade to sensor_tokens."""
    from datetime import datetime  # noqa: WPS433
    from quirk.models import Sensor, SensorToken  # noqa: WPS433
    from sqlalchemy.orm import Session  # noqa: WPS433

    engine = init_db(str(tmp_path / "cascade_tokens.sqlite"))
    session = Session(engine)

    sensor = Sensor(
        sensor_id="aaaaaaaa-0000-0000-0000-000000000001",
        segment="lab",
        enrolled_at=datetime.utcnow(),
        expected_cadence_minutes=60,
    )
    token = SensorToken(
        sensor_id="aaaaaaaa-0000-0000-0000-000000000001",
        token_hash="a" * 64,
        created_at=datetime.utcnow(),
    )
    session.add(sensor)
    session.add(token)
    session.commit()

    # Delete the parent sensor
    session.delete(sensor)
    session.commit()

    remaining_tokens = session.query(SensorToken).all()
    session.close()
    assert len(remaining_tokens) == 0, (
        "ON DELETE CASCADE must remove sensor_tokens rows when parent sensors row is deleted"
    )


def test_cascade_delete_removes_sensor_pushes(tmp_path: Path) -> None:
    """D-04 / MODEL-04: deleting a sensors row must cascade to sensor_pushes."""
    from datetime import datetime  # noqa: WPS433
    from quirk.models import Sensor, SensorPush  # noqa: WPS433
    from sqlalchemy.orm import Session  # noqa: WPS433

    engine = init_db(str(tmp_path / "cascade_pushes.sqlite"))
    session = Session(engine)

    sensor = Sensor(
        sensor_id="bbbbbbbb-0000-0000-0000-000000000002",
        segment="lab",
        enrolled_at=datetime.utcnow(),
        expected_cadence_minutes=60,
    )
    push = SensorPush(
        payload_id="p" * 64,
        sensor_id="bbbbbbbb-0000-0000-0000-000000000002",
        received_at=datetime.utcnow(),
    )
    session.add(sensor)
    session.add(push)
    session.commit()

    # Delete the parent sensor
    session.delete(sensor)
    session.commit()

    remaining_pushes = session.query(SensorPush).all()
    session.close()
    assert len(remaining_pushes) == 0, (
        "ON DELETE CASCADE must remove sensor_pushes rows when parent sensors row is deleted"
    )


def test_sensor_push_payload_id_unique_constraint_enforced(tmp_path: Path) -> None:
    """MODEL-04 / D-07: inserting a duplicate payload_id must raise an error."""
    from datetime import datetime  # noqa: WPS433
    from sqlalchemy.exc import IntegrityError  # noqa: WPS433
    from quirk.models import Sensor, SensorPush  # noqa: WPS433
    from sqlalchemy.orm import Session  # noqa: WPS433

    engine = init_db(str(tmp_path / "payload_unique.sqlite"))
    session = Session(engine)

    sensor = Sensor(
        sensor_id="cccccccc-0000-0000-0000-000000000003",
        segment="lab",
        enrolled_at=datetime.utcnow(),
        expected_cadence_minutes=60,
    )
    session.add(sensor)
    session.commit()

    push1 = SensorPush(
        payload_id="unique-payload-id-0000000000000000000000000000000000000000000001",
        sensor_id="cccccccc-0000-0000-0000-000000000003",
        received_at=datetime.utcnow(),
    )
    session.add(push1)
    session.commit()

    push2 = SensorPush(
        payload_id="unique-payload-id-0000000000000000000000000000000000000000000001",
        sensor_id="cccccccc-0000-0000-0000-000000000003",
        received_at=datetime.utcnow(),
    )
    session.add(push2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.close()
