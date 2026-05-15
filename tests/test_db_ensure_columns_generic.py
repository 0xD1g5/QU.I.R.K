"""Phase 77-03 D-21 (api-cli-core/IN-06): consolidate 8 `_ensure_*_columns`
helpers into a single generic `_ensure_columns(engine, table, expected)`.

RESEARCH Pattern 3 + RESEARCH inventory: the 5 table-creating / FK helpers
(`_ensure_qramm_profiles_fk`, `_ensure_qramm_tables`, `_ensure_scheduled_tables`,
`_ensure_scan_jobs_table`, `_ensure_scan_checkpoints_table`) are UNTOUCHED —
they use a different pattern (Base.metadata.create_all / raw FK rebuild).
"""
from __future__ import annotations

import ast
import os
import pathlib
import tempfile

from sqlalchemy import inspect as sa_inspect


_DB_PATH = pathlib.Path("quirk/db.py")
_REMOVED_HELPERS = (
    "_ensure_identity_columns",
    "_ensure_gcp_columns",
    "_ensure_v43_columns",
    "_ensure_email_columns",
    "_ensure_broker_columns",
    "_ensure_phase41_columns",
    "_ensure_phase46_columns",
    "_ensure_phase54_qramm_columns",
)
_PRESERVED_HELPERS = (
    "_ensure_qramm_profiles_fk",
    "_ensure_qramm_tables",
    "_ensure_scheduled_tables",
    "_ensure_scan_jobs_table",
    "_ensure_scan_checkpoints_table",
)


def test_generic_helper_exists() -> None:
    """D-21: `_ensure_columns` callable must exist at module level."""
    from quirk.db import _ensure_columns  # noqa: WPS433

    assert callable(_ensure_columns)


def test_old_column_adding_helpers_removed() -> None:
    """D-21: the 8 column-adding helpers must be removed (AST gate)."""
    tree = ast.parse(_DB_PATH.read_text(encoding="utf-8"))
    defined = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    leftovers = defined.intersection(_REMOVED_HELPERS)
    assert not leftovers, f"D-21: column-adding helpers not removed: {sorted(leftovers)}"


def test_table_creating_helpers_preserved() -> None:
    """D-21: the 5 table-creating / FK helpers must be UNTOUCHED."""
    tree = ast.parse(_DB_PATH.read_text(encoding="utf-8"))
    defined = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    missing = set(_PRESERVED_HELPERS) - defined
    assert not missing, f"D-21: preserved helpers accidentally removed: {sorted(missing)}"


def test_init_db_creates_expected_columns_smoke() -> None:
    """D-21: integration smoke — init_db on a fresh SQLite file must produce a
    crypto_endpoints table with all migrated columns from the 8 consolidated
    helpers, and a qramm_answers table with `evidence_note`."""
    from quirk.db import init_db  # noqa: WPS433

    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "quirk_smoke.sqlite")
        engine = init_db(db_path)

        insp = sa_inspect(engine)
        crypto_cols = {c["name"] for c in insp.get_columns("crypto_endpoints")}
        expected_crypto = {
            # _IDENTITY_COLUMNS
            "kerberos_scan_json",
            "saml_scan_json",
            "dnssec_scan_json",
            # _GCP_COLUMNS
            "gcs_scan_json",
            # _V43_COLUMN_DDLS
            "dat_scan_json",
            "severity",
            # _EMAIL_COLUMNS
            "email_scan_json",
            # _BROKER_COLUMNS
            "broker_scan_json",
            # _PHASE41_COLUMN_DDLS
            "scan_error_category",
            # _PHASE46_COLUMN_DDLS
            "chain_verified",
        }
        missing = expected_crypto - crypto_cols
        assert not missing, f"D-21: crypto_endpoints missing columns after init_db: {missing}"

        qramm_cols = {c["name"] for c in insp.get_columns("qramm_answers")}
        assert "evidence_note" in qramm_cols, "D-21: evidence_note missing on qramm_answers"
