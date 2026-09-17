#!/usr/bin/env python3
"""Verify a multihost scan produced what the topology should produce.

Usage:
    .venv/bin/python quantum-chaos-enterprise-lab/verify_multihost_scan.py [db_path]

Default db_path is quirk-output/quirk.db.

Why this exists: reading the dashboard tells you a tab is populated, not that it is
populated CORRECTLY, and an empty tab has several unrelated causes (connector off,
detail field unset, optional dependency missing, host down). Each check below names
the host it expects, so a failure points at one service rather than "Identity looks
thin". Read-only — opens the DB and prints; changes nothing.

Exit code 0 if every REQUIRED check passes, 1 otherwise. Checks marked OPTIONAL
report but do not affect the exit code (they depend on extras that `[all]` excludes
or on environment credentials).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB = Path(sys.argv[1] if len(sys.argv) > 1 else "quirk-output/quirk.db")

# (label, required, SQL, predicate on rowcount, what it proves)
CHECKS = [
    ("estate reachable", True,
     "SELECT COUNT(DISTINCT host) FROM crypto_endpoints WHERE host LIKE '10.80.0.%'",
     lambda n: n >= 25,
     "hosts answering on the multihost subnet (expect ~31 of 39; some are single-service)"),

    ("TLS estate", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE tls_version IS NOT NULL",
     lambda n: n >= 10,
     "endpoints with a negotiated TLS version"),

    ("expired certs (CLOCK CHECK)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE cert_not_after IS NOT NULL "
     "AND cert_not_after < datetime('now')",
     lambda n: n >= 1,
     "deliberately-expired certs at .11/.101-.104 read as EXPIRED. Zero here with a "
     "populated TLS estate means the system clock is wrong — findings are untrustworthy"),

    ("no 'not yet valid' certs (CLOCK CHECK)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE cert_not_before IS NOT NULL "
     "AND cert_not_before > datetime('now')",
     lambda n: n == 0,
     "a non-zero count means the clock is BEHIND and every cert finding is suspect"),

    ("SAML  (.41)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE host LIKE '%10.80.0.41%' "
     "OR protocol LIKE '%SAML%'",
     lambda n: n >= 1,
     "Identity tab — needs saml_targets set to the metadata URL"),

    ("PostgreSQL  (.30)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE protocol LIKE '%POSTGRES%' "
     "OR host LIKE '%10.80.0.30%'",
     lambda n: n >= 1,
     "Data at Rest — needs pg_targets + pg_scanner_user/password"),

    ("MySQL ssl-off  (.111)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE service_detail LIKE '%MySQL/ssl-off%'",
     lambda n: n >= 1,
     "Data at Rest — needs mysql_targets; this finding was missing before 2026-09-17"),

    ("S3 / MinIO  (.50)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE protocol LIKE '%S3%' "
     "OR service_detail LIKE '%bucket%' OR service_detail LIKE '%S3%'",
     lambda n: n >= 1,
     "Data at Rest — needs aws_endpoint_url AND AWS_ACCESS_KEY_ID/SECRET in the env. "
     "Zero here drops the WHOLE Data at Rest domain from the score as UNASSESSED"),

    ("Vault  (.61)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE service_detail LIKE '%transit/%' "
     "OR service_detail LIKE '%PKI/%' OR service_detail LIKE '%auth/%'",
     lambda n: n >= 4,
     "Data at Rest — expect 6: exportable transit, PKI root + intermediate, token, userpass"),

    ("broker / Redis  (.31)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE protocol LIKE '%REDIS%' "
     "OR protocol LIKE '%KAFKA%' OR protocol LIKE '%AMQP%'",
     lambda n: n >= 1,
     "Motion tab — needs broker_targets"),

    ("email  (.120/.121)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE protocol LIKE '%SMTP%' "
     "OR protocol LIKE '%IMAP%' OR protocol LIKE '%POP3%'",
     lambda n: n >= 4,
     "Motion tab — needs sslyze AND both mail hosts in targets.cidrs"),

    ("JWT / JWKS  (.90-.93)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE host LIKE '%:8000%' "
     "OR service_detail LIKE '%jwks%' OR service_detail LIKE '%.well-known%'",
     lambda n: n >= 1,
     "Findings tab — targets must be BASE URLs (not /token) and "
     "allow_internal_targets must be true"),

    ("Kerberos  (.42)", False,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE protocol LIKE '%KERBEROS%'",
     lambda n: n >= 1,
     "OPTIONAL — needs quirk-scanner[identity]; `[all]` excludes it"),

    ("SSH  (.70)", True,
     "SELECT COUNT(*) FROM crypto_endpoints WHERE protocol LIKE '%SSH%'",
     lambda n: n >= 1,
     "the jump host"),
]

NOISE = (
    "missing-extra advisories", False,
    "SELECT COUNT(*) FROM crypto_endpoints WHERE scan_error_category = 'missing_extra'",
    "a connector was enabled but its dependency is absent — check which",
)


def main() -> int:
    if not DB.exists():
        print(f"✗ no database at {DB}\n  run the scan first: quirk --config multihost-vm.yaml")
        return 1

    con = sqlite3.connect(str(DB))
    cur = con.cursor()

    print(f"Verifying {DB}\n")
    width = max(len(c[0]) for c in CHECKS)
    failures = 0

    for label, required, sql, predicate, why in CHECKS:
        try:
            n = cur.execute(sql).fetchone()[0]
        except sqlite3.Error as exc:
            print(f"  ?  {label:<{width}}  query failed: {exc}")
            continue
        ok = predicate(n)
        if ok:
            mark = "OK "
        elif required:
            mark, failures = "FAIL", failures + 1
        else:
            mark = "skip"
        print(f"  {mark:<4} {label:<{width}}  n={n}")
        if not ok:
            print(f"       -> {why}")

    label, _, sql, why = NOISE
    try:
        n = cur.execute(sql).fetchone()[0]
        if n:
            print(f"\n  note  {label}: {n} — {why}")
            # DISTINCT + cap: one advisory is emitted per scan run, so a DB holding
            # many runs repeats the same two rows dozens of times.
            for (h, d, c) in cur.execute(
                "SELECT host, scan_error, COUNT(*) FROM crypto_endpoints "
                "WHERE scan_error_category='missing_extra' "
                "GROUP BY host, scan_error ORDER BY COUNT(*) DESC LIMIT 8"
            ).fetchall():
                print(f"        {h}: {d}" + (f"  (x{c})" if c > 1 else ""))
    except sqlite3.Error:
        pass

    total = cur.execute("SELECT COUNT(*) FROM crypto_endpoints").fetchone()[0]
    sev = cur.execute(
        "SELECT severity, COUNT(*) FROM crypto_endpoints "
        "WHERE severity IS NOT NULL GROUP BY severity ORDER BY COUNT(*) DESC"
    ).fetchall()
    print(f"\n  {total} endpoints total | severities: "
          + (", ".join(f"{s}={c}" for s, c in sev) or "none recorded"))

    con.close()
    print("\n" + ("✓ all required checks passed" if not failures
                  else f"✗ {failures} required check(s) failed — see the -> lines above"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
