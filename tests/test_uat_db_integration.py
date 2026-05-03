"""UAT-01: Phase 27 DB UAT -- live integration against the `database` chaos lab profile.

Closes deferred items:
  - Phase 27 27-HUMAN-UAT.md (1 pending)
  - Phase 27 27-UAT.md (7 pending)

Run locally with:
    cd quantum-chaos-enterprise-lab && ./lab.sh up database
    QUIRK_DB_INTEGRATION=1 python -m pytest tests/test_uat_db_integration.py -v
"""

import os
import pytest

from quirk.scanner.db_connector import scan_pg_targets, scan_mysql_targets


pytestmark = pytest.mark.slow


PG_HOST = "localhost"
PG_PORT = 25432
MY_HOST = "localhost"
MY_PORT = 23306
DB_USER = "quirk_scanner"
DB_PASS = "quirk_scanner"


@pytest.mark.skipif(
    not os.environ.get("QUIRK_DB_INTEGRATION"),
    reason="Set QUIRK_DB_INTEGRATION=1 and start `docker compose --profile database up -d`",
)
def test_postgres_ssl_off_produces_high_finding():
    """UAT-27: PostgreSQL ssl=off -> HIGH ssl-off finding."""
    results = scan_pg_targets(
        targets=[f"{PG_HOST}:{PG_PORT}"],
        user=DB_USER,
        password=DB_PASS,
    )
    assert len(results) >= 1, f"Expected >=1 finding from PostgreSQL ssl-off; got 0"
    ep = next((r for r in results if "ssl-off" in (r.service_detail or "")), None)
    assert ep is not None, (
        f"Expected ssl-off finding; got service_details={[r.service_detail for r in results]}"
    )
    assert ep.protocol == "POSTGRESQL", f"Expected protocol POSTGRESQL, got {ep.protocol}"
    assert ep.severity == "HIGH", f"Expected severity HIGH, got {ep.severity}"


@pytest.mark.skipif(
    not os.environ.get("QUIRK_DB_INTEGRATION"),
    reason="Set QUIRK_DB_INTEGRATION=1 and start `docker compose --profile database up -d`",
)
def test_mysql_ssl_off_produces_high_finding():
    """UAT-27: MySQL --skip-ssl -> HIGH ssl-off finding."""
    results = scan_mysql_targets(
        targets=[f"{MY_HOST}:{MY_PORT}"],
        user=DB_USER,
        password=DB_PASS,
    )
    assert len(results) >= 1, f"Expected >=1 finding from MySQL ssl-off; got 0"
    ep = next((r for r in results if "ssl-off" in (r.service_detail or "")), None)
    assert ep is not None, (
        f"Expected ssl-off finding; got service_details={[r.service_detail for r in results]}"
    )
    assert ep.protocol == "MYSQL", f"Expected protocol MYSQL, got {ep.protocol}"
    assert ep.severity == "HIGH", f"Expected severity HIGH, got {ep.severity}"


@pytest.mark.skipif(
    not os.environ.get("QUIRK_DB_INTEGRATION"),
    reason="Set QUIRK_DB_INTEGRATION=1 and start `docker compose --profile database up -d`",
)
def test_postgres_finding_includes_host_and_port():
    results = scan_pg_targets(
        targets=[f"{PG_HOST}:{PG_PORT}"],
        user=DB_USER,
        password=DB_PASS,
    )
    assert any(r.port == PG_PORT for r in results), (
        f"No finding had port={PG_PORT}; ports={[r.port for r in results]}"
    )


@pytest.mark.skipif(
    not os.environ.get("QUIRK_DB_INTEGRATION"),
    reason="Set QUIRK_DB_INTEGRATION=1 and start `docker compose --profile database up -d`",
)
def test_mysql_finding_includes_host_and_port():
    results = scan_mysql_targets(
        targets=[f"{MY_HOST}:{MY_PORT}"],
        user=DB_USER,
        password=DB_PASS,
    )
    assert any(r.port == MY_PORT for r in results), (
        f"No finding had port={MY_PORT}; ports={[r.port for r in results]}"
    )
