# Database Connector Setup

QU.I.R.K.'s database connector (`enable_db`) checks the connection-encryption posture of PostgreSQL
and MySQL/MariaDB servers. It connects to each configured server as a scanner account and reports
whether plaintext connections are accepted. (RDS storage encryption is a separate check; see
[AWS Connector Setup](aws.md).)

## Minimum Database Permissions

| Engine | What the connector runs | Account needs |
|--------|--------------------------|---------------|
| PostgreSQL | `SHOW ssl`, `pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER')`, then `SELECT COUNT(*) FROM pg_stat_ssl WHERE ssl = false` | Login permission, plus membership in `pg_read_all_stats` to count plaintext connections |
| MySQL / MariaDB | `SHOW STATUS LIKE 'Ssl_cipher'` | An account that can connect and run that statement |

To let the PostgreSQL scan count plaintext connections, grant the predefined role:

```sql
GRANT pg_read_all_stats TO quirk_scanner;
```

Without it, when `SHOW ssl` reports on, the PostgreSQL scan stops at the privilege check and
reports an `insufficient-privilege` advisory instead of counting plaintext connections.

## Prerequisites

- Network access from the scan host to each database port
- The `psycopg2-binary` (PostgreSQL) and `PyMySQL` (MySQL) drivers; both ship in the `db` extra,
  which `[all]` includes:

  ```bash
  pip install 'quirk-scanner[db]'
  ```

  Either driver alone enables its own engine.

## Credential Setup

Usernames go in `config.yaml`; passwords are credentials and are best supplied through the
environment:

```bash
export QUIRK_PG_SCANNER_PASSWORD="<password>"
export QUIRK_MYSQL_SCANNER_PASSWORD="<password>"
```

When a PostgreSQL password is not set at all, libpq supplies one (`PGPASSWORD` or `.pgpass`); when
a MySQL password is not set, PyMySQL sends an empty password. When a username is not set the scans
connect as `postgres` and `root` respectively.

## config.yaml Snippet

```yaml
connectors:
  enable_db: true
  pg_targets:
    - "db1.example.com"                 # host or host:port — port defaults to 5432
  pg_scanner_user: "quirk_scanner"      # optional — defaults to "postgres"
  mysql_targets:
    - "db2.example.com:3306"            # host or host:port — port defaults to 3306
  mysql_scanner_user: "quirk_scanner"   # optional — defaults to "root"
```

Each engine has its own target list: with only `pg_targets` set, MySQL is not scanned, and the
reverse. The database phase is skipped when both lists are empty. Connect timeout is
`scan.timeouts.db_connect_seconds` (default `5`).

## What Gets Scanned

| Engine | Check | Result |
|--------|-------|--------|
| PostgreSQL | `SHOW ssl` is off | HIGH `PostgreSQL/ssl-off` |
| PostgreSQL | The account is not a `pg_read_all_stats` member | INFO `insufficient-privilege` advisory |
| PostgreSQL | One or more plaintext rows in `pg_stat_ssl` | HIGH `PostgreSQL/plaintext-connections-allowed (N non-SSL)` |
| PostgreSQL | No plaintext connections | `PostgreSQL/ssl-enforced` (informational) |
| MySQL / MariaDB | `Ssl_cipher` is empty (the scan connects with SSL disabled, so an accepted plaintext connection reads as empty) | HIGH `MySQL/ssl-off` |
| MySQL / MariaDB | `Ssl_cipher` starts with `RC4`, `DES`, `NULL`, `EXPORT`, `ANON`, `MD5` or `3DES` | MEDIUM `MySQL/<cipher>-weak` |
| MySQL / MariaDB | Any other cipher | `MySQL/<cipher>-ok` (informational) |

Both scans connect with SSL disabled. Any connection that cannot be made is reported as a
`connection-error:` scan error; the source notes that a MySQL server with `require_secure_transport`
on rejects the probe this way. PostgreSQL and MySQL results feed the `data_at_rest` subscore.

## Graceful Degradation

If one driver is missing and the other is installed, the missing engine's scan returns an empty
result set and, in verbose runs, logs one of:

```
psycopg2-binary not installed -- PostgreSQL scanning unavailable
PyMySQL not installed -- MySQL scanning unavailable
```

When both drivers are missing the whole database phase is skipped as `missing-extra`. All other
scanners continue to run normally.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `connection-error:` scan error on a target | Wrong host/port, bad credentials, or a server that refuses the plaintext probe | Check the target and the scanner user and password |
| `insufficient-privilege` advisory on PostgreSQL | The scanner account is not a `pg_read_all_stats` member | `GRANT pg_read_all_stats TO <scanner_user>;` |
| Database phase skipped as `no-eligible-targets` | Both `pg_targets` and `mysql_targets` are empty | Add targets for the engine you want scanned |
| MySQL not scanned although `enable_db` is on | `mysql_targets` is empty | Add `mysql_targets`; each engine has its own list |
