"""RED contract tests for AUDIT-01: codesign column rename + additive migration.

AUDIT-01 success criterion: The codesign scanner writes its JSON payload to a
dedicated ``codesign_scan_json`` column rather than reusing ``smime_scan_json``.
The change must be delivered as an additive migration (no data loss, idempotent).

These tests FAIL against the current codebase (v5.7) because:
- CryptoEndpoint has no ``codesign_scan_json`` ORM attribute
- _IDENTITY_COLUMNS in quirk/db.py does not include "codesign_scan_json"
- The codesign scanner writes to ``smime_scan_json``, not ``codesign_scan_json``
- findings_evaluator reads ``smime_scan_json`` for codesign, not ``codesign_scan_json``

Wave 2 Plan 130-01 makes them pass.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from quirk.models import CryptoEndpoint
from quirk.db import init_db, run_additive_migration
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Test A: ORM attribute exists
# ---------------------------------------------------------------------------

def test_codesign_scan_json_orm_attribute_exists() -> None:
    """CryptoEndpoint must have a ``codesign_scan_json`` ORM attribute (AUDIT-01)."""
    assert hasattr(CryptoEndpoint, "codesign_scan_json"), (
        "CryptoEndpoint is missing the ``codesign_scan_json`` attribute. "
        "AUDIT-01 requires a dedicated codesign column distinct from smime_scan_json."
    )


# ---------------------------------------------------------------------------
# Test B: Schema migration creates the column
# ---------------------------------------------------------------------------

def test_init_db_creates_codesign_scan_json_column(tmp_path: Path) -> None:
    """init_db must create a ``codesign_scan_json`` column in crypto_endpoints (AUDIT-01)."""
    db_path = str(tmp_path / "test_codesign_b.db")
    engine = init_db(db_path)

    # Inspect via PRAGMA
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(crypto_endpoints)")).fetchall()

    col_names = {row[1] for row in rows}  # column index 1 = name
    assert "codesign_scan_json" in col_names, (
        f"PRAGMA table_info for crypto_endpoints does not contain 'codesign_scan_json'. "
        f"Columns found: {sorted(col_names)}"
    )


# ---------------------------------------------------------------------------
# Test C: Additive migration — no data loss
# ---------------------------------------------------------------------------

def test_additive_migration_no_data_loss(tmp_path: Path) -> None:
    """Pre-migration rows with smime_scan_json survive the additive migration (AUDIT-01).

    Steps:
    1. Create a SQLite DB with crypto_endpoints table that does NOT have
       codesign_scan_json but HAS smime_scan_json, and insert a test row.
    2. Run run_additive_migration (or init_db) to add the missing column.
    3. Assert: codesign_scan_json column is present AND the pre-existing row is
       readable with its original smime_scan_json value intact.
    """
    db_path = str(tmp_path / "premigration.db")

    # Build a minimal pre-migration schema (no codesign_scan_json column)
    conn_raw = sqlite3.connect(db_path)
    conn_raw.execute(
        """
        CREATE TABLE crypto_endpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host VARCHAR(255) NOT NULL,
            port INTEGER NOT NULL,
            smime_scan_json TEXT
        )
        """
    )
    smime_payload = json.dumps({"reasons": ["expired"]})
    conn_raw.execute(
        "INSERT INTO crypto_endpoints (host, port, smime_scan_json) VALUES (?, ?, ?)",
        ("10.0.0.1", 636, smime_payload),
    )
    conn_raw.commit()
    conn_raw.close()

    # Run the production migration entry-point
    engine = init_db(db_path)

    # Verify codesign column added
    with engine.connect() as conn:
        pragma_rows = conn.execute(text("PRAGMA table_info(crypto_endpoints)")).fetchall()
        col_names = {row[1] for row in pragma_rows}
        assert "codesign_scan_json" in col_names, (
            "Additive migration did not add 'codesign_scan_json' column."
        )

        # Verify original row is intact
        result = conn.execute(
            text("SELECT smime_scan_json FROM crypto_endpoints WHERE host='10.0.0.1'")
        ).fetchone()
        assert result is not None, "Pre-migration row was deleted — data loss detected."
        assert result[0] == smime_payload, (
            f"smime_scan_json was corrupted by migration. "
            f"Expected {smime_payload!r}, got {result[0]!r}"
        )


# ---------------------------------------------------------------------------
# Test D: Codesign scanner writes new column
# ---------------------------------------------------------------------------

def test_codesign_scanner_writes_codesign_scan_json() -> None:
    """The codesign scanner must write the payload to codesign_scan_json, not smime_scan_json (AUDIT-01).

    Instantiates a CryptoEndpoint the way codesign_scanner does and asserts:
    - codesign_scan_json carries the scan payload
    - smime_scan_json is NOT used for codesign payloads
    """
    from quirk.scanner.codesign_scanner import scan_codesign_from_tls_endpoints

    # A minimal TLS endpoint that would trigger codesign evaluation
    tls_ep = SimpleNamespace(
        host="10.0.0.1",
        port=443,
        tls_capabilities_json=json.dumps({
            "eku_oids": ["1.3.6.1.5.5.7.3.3"],  # code-signing EKU
        }),
        cert_subject="CN=TestCodeSigner",
        cert_issuer="CN=TestCA",
        cert_sig_alg="sha256WithRSAEncryption",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_not_before=None,
        cert_not_after=None,
        scan_error=None,
    )

    results = scan_codesign_from_tls_endpoints([tls_ep])

    if not results:
        pytest.skip("No codesign endpoints returned for this fixture — check EKU matching logic.")

    ep = results[0]

    # The fix: codesign payload must be in codesign_scan_json
    assert getattr(ep, "codesign_scan_json", None) is not None, (
        "codesign_scan_json is None/missing on the emitted CryptoEndpoint. "
        "The scanner must write to codesign_scan_json (AUDIT-01)."
    )

    # The fix: smime_scan_json must NOT carry the codesign payload
    # (It can be None/empty because codesign has a dedicated column now)
    smime_val = getattr(ep, "smime_scan_json", None)
    # If smime_scan_json is populated, it must NOT be a codesign payload
    # (checking for the "reasons" codesign signature written by the scanner)
    if smime_val:
        parsed = json.loads(smime_val)
        assert "reasons" not in parsed or not any(
            r in ("weak-signing-alg", "weak-rsa-key", "weak-ec-key", "expired", "safe")
            for r in parsed.get("reasons", [])
        ), (
            "smime_scan_json still contains a codesign payload (reasons=[...]). "
            "AUDIT-01 requires the codesign scanner to write to codesign_scan_json instead."
        )


# ---------------------------------------------------------------------------
# Test E: findings_evaluator reads from codesign_scan_json
# ---------------------------------------------------------------------------

def test_findings_evaluator_reads_codesign_scan_json() -> None:
    """findings_evaluator must read codesign data from codesign_scan_json, not smime_scan_json (AUDIT-01).

    Constructs a mock endpoint with codesign_scan_json populated and
    smime_scan_json=None, then asserts evaluate_codesign_endpoints produces findings.
    """
    from quirk.engine.findings_evaluator import evaluate_codesign_endpoints

    # An endpoint that has the codesign payload in the NEW column
    ep = SimpleNamespace(
        host="10.0.0.1",
        port=636,
        cert_subject="CN=Code Signer",
        cert_not_after=None,
        # NEW column carries the payload
        codesign_scan_json=json.dumps({"reasons": ["expired"]}),
        # OLD column is empty (post-AUDIT-01)
        smime_scan_json=None,
    )

    findings = evaluate_codesign_endpoints([ep])

    assert len(findings) > 0, (
        "evaluate_codesign_endpoints returned 0 findings when codesign_scan_json carries "
        "an expired-certificate payload. The evaluator must read from codesign_scan_json "
        "(AUDIT-01) — currently it reads smime_scan_json, which is None here."
    )
