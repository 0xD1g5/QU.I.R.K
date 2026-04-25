"""Database connector -- PostgreSQL and MySQL SSL posture scanner (DB-01, DB-02).

Detects:
- PostgreSQL: server SSL enforcement via pg_stat_ssl and pg_has_role privilege check
- MySQL/MariaDB: SSL session status via Ssl_cipher variable

Optional deps: psycopg2-binary (pip install quirk[db]), PyMySQL (pip install quirk[db])
Module-level None assignments ensure test patching via unittest.mock.patch works correctly.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from quirk.models import CryptoEndpoint

# ---------------------------------------------------------------------------
# Optional imports with module-level None (required for test patching)
# ---------------------------------------------------------------------------

try:
    import psycopg2  # type: ignore[import]
    PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None  # type: ignore[assignment]
    PSYCOPG2_AVAILABLE = False

try:
    import pymysql  # type: ignore[import]
    PYMYSQL_AVAILABLE = True
except ImportError:
    pymysql = None  # type: ignore[assignment]
    PYMYSQL_AVAILABLE = False

# ---------------------------------------------------------------------------
# MySQL weak cipher detection (per D-06 -- follow CRYPTO_LIB_ALLOWLIST convention)
# ---------------------------------------------------------------------------

MYSQL_WEAK_CIPHER_PREFIXES = frozenset([
    "RC4", "DES", "NULL", "EXPORT", "ANON", "MD5", "3DES",
])


def _is_weak_mysql_cipher(cipher: str) -> bool:
    """Return True if cipher name matches a known-weak prefix."""
    upper = cipher.upper()
    return any(upper.startswith(prefix) for prefix in MYSQL_WEAK_CIPHER_PREFIXES)


# ---------------------------------------------------------------------------
# PostgreSQL scanner (DB-01)
# ---------------------------------------------------------------------------

def scan_pg_targets(
    targets: list,
    user: Optional[str] = None,
    password: Optional[str] = None,
    logger=None,
    session_start=None,
) -> List[CryptoEndpoint]:
    """Scan PostgreSQL targets for SSL enforcement posture.

    3-tier probe (per D-04, with pg_has_role correction from RESEARCH.md Pitfall 1):
      1. SHOW ssl -- if 'off', emit HIGH finding immediately
      2. pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER') -- privilege check
      3. If privileged: COUNT(*) FROM pg_stat_ssl WHERE ssl = false
    """
    if not PSYCOPG2_AVAILABLE:
        if logger:
            logger.v("psycopg2-binary not installed -- PostgreSQL scanning unavailable")
        return []

    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results: List[CryptoEndpoint] = []

    for target in targets:
        host, _, port_str = str(target).partition(":")
        port = int(port_str) if port_str.isdigit() else 5432
        ep_host = f"postgresql://{host}:{port}"

        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user or "postgres",
                password=password or "",
                connect_timeout=5,
                sslmode="disable",  # probe without SSL to check server-side config
            )
            with conn:
                with conn.cursor() as cur:
                    # Tier 1: server-level SSL enabled?
                    cur.execute("SHOW ssl")
                    row = cur.fetchone()
                    ssl_enabled = (row[0].strip().lower() == "on") if row else False

                    if not ssl_enabled:
                        results.append(CryptoEndpoint(
                            host=ep_host,
                            port=port,
                            protocol="POSTGRESQL",
                            severity="HIGH",
                            service_detail="PostgreSQL/ssl-off",
                            scanned_at=now,
                        ))
                        continue

                    # Tier 2: privilege check (pg_has_role, NOT has_privilege -- see RESEARCH Pitfall 1)
                    cur.execute(
                        "SELECT pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER')"
                    )
                    priv_row = cur.fetchone()
                    has_priv = bool(priv_row[0]) if priv_row else False

                    if not has_priv:
                        # Cannot enumerate all connections -- emit scan_error (INFO, not vulnerability)
                        results.append(CryptoEndpoint(
                            host=ep_host,
                            port=port,
                            protocol="POSTGRESQL",
                            severity="INFO",
                            scan_error="insufficient-privilege",
                            service_detail="Remediation: GRANT pg_read_all_stats TO <scanner_user>",
                            scanned_at=now,
                        ))
                        continue

                    # Tier 3: count non-SSL connections across all backends
                    cur.execute("SELECT COUNT(*) FROM pg_stat_ssl WHERE ssl = false")
                    count_row = cur.fetchone()
                    non_ssl_count = int(count_row[0]) if count_row else 0

                    if non_ssl_count > 0:
                        results.append(CryptoEndpoint(
                            host=ep_host,
                            port=port,
                            protocol="POSTGRESQL",
                            severity="HIGH",
                            service_detail=f"PostgreSQL/plaintext-connections-allowed ({non_ssl_count} non-SSL)",
                            scanned_at=now,
                        ))
                    else:
                        # All connections use SSL -- informational (positive posture)
                        results.append(CryptoEndpoint(
                            host=ep_host,
                            port=port,
                            protocol="POSTGRESQL",
                            service_detail="PostgreSQL/ssl-enforced",
                            scanned_at=now,
                        ))

        except Exception as exc:
            if logger:
                logger.v(f"PostgreSQL scan error for {ep_host}: {exc}")

    return results


# ---------------------------------------------------------------------------
# MySQL/MariaDB scanner (DB-02)
# ---------------------------------------------------------------------------

def scan_mysql_targets(
    targets: list,
    user: Optional[str] = None,
    password: Optional[str] = None,
    logger=None,
    session_start=None,
) -> List[CryptoEndpoint]:
    """Scan MySQL/MariaDB targets for SSL session status.

    Connects with ssl_disabled=True to probe global SSL configuration
    without interference (per D-06, PyMySQL >= 1.1.0 ssl_disabled parameter).

    Severity ladder:
      Ssl_cipher empty/absent -> HIGH ("MySQL/ssl-off")
      Ssl_cipher weak prefix   -> MEDIUM ("MySQL/<cipher>-weak")
      Ssl_cipher strong        -> no finding (informational endpoint)
    """
    if not PYMYSQL_AVAILABLE:
        if logger:
            logger.v("PyMySQL not installed -- MySQL scanning unavailable")
        return []

    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results: List[CryptoEndpoint] = []

    for target in targets:
        host, _, port_str = str(target).partition(":")
        port = int(port_str) if port_str.isdigit() else 3306
        ep_host = f"mysql://{host}:{port}"

        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user or "root",
                password=password or "",
                connect_timeout=5,
                ssl_disabled=True,  # intentionally bypass SSL to query server status
            )
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SHOW STATUS LIKE 'Ssl_cipher'")
                    row = cur.fetchone()
                    # row is tuple: ('Ssl_cipher', 'value') or None
                    ssl_cipher = str(row[1]).strip() if row else ""

                    if not ssl_cipher:
                        results.append(CryptoEndpoint(
                            host=ep_host,
                            port=port,
                            protocol="MYSQL",
                            severity="HIGH",
                            service_detail="MySQL/ssl-off",
                            scanned_at=now,
                        ))
                    elif _is_weak_mysql_cipher(ssl_cipher):
                        results.append(CryptoEndpoint(
                            host=ep_host,
                            port=port,
                            protocol="MYSQL",
                            severity="MEDIUM",
                            service_detail=f"MySQL/{ssl_cipher}-weak",
                            scanned_at=now,
                        ))
                    else:
                        # Strong cipher -- informational (positive posture)
                        results.append(CryptoEndpoint(
                            host=ep_host,
                            port=port,
                            protocol="MYSQL",
                            service_detail=f"MySQL/{ssl_cipher}-ok",
                            scanned_at=now,
                        ))

        except Exception as exc:
            if logger:
                logger.v(f"MySQL scan error for {ep_host}: {exc}")

    return results
