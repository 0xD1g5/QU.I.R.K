# Upgrading QU.I.R.K. (v4.10 or later → the latest release)

This guide walks an existing QU.I.R.K. installation through an upgrade to the
latest release on PyPI. If you have ever scanned your own infrastructure with
an earlier PyPI release, this is the document for you.

## Scope

This guide applies to any installation made from a PyPI release (4.10.0 is the
oldest; earlier versions were never published to PyPI). `quirk db migrate` is
**additive-only** for your data: it adds missing columns and tables, and it
never drops, renames, or retypes columns. A database created by 4.10.0 migrates
cleanly to the latest release, even across many intermediate versions.

`quirk db migrate` is the only database command. One step is not a plain add:
on a database whose `qramm_profiles` table predates that table's foreign key, it
rebuilds the table once. It copies every row into a new table, drops the old
table and renames the new one into its place, so no row or column is lost. The
migrate summary does not report this step. There is also no in-tool rollback:
rolling forward via re-running `quirk db migrate` is always preferred, and the rollback path (if you need it)
is a file copy from your pre-upgrade backup.

**Know which database file you are migrating.** Without `--db` or `--config`,
`quirk db migrate` operates on `./quirk.db` in the current directory, but a
database written by the standard configuration lives at
`./quirk-output/quirk.db`. Pass `--db` explicitly (the examples below use
`quirk-output/quirk.db`) — otherwise the command silently creates and migrates a
new, empty `./quirk.db` and leaves your real database untouched.

## Pre-upgrade checklist

Before installing the new version, complete each of the following:

1. **Note your current version.** Record the output for your upgrade log:

   ```bash
   quirk --version
   ```

2. **Back up `quirk.db`.** The simplest backup is a file copy while no scan
   is running. From the directory containing `quirk-output/`:

   ```bash
   cp quirk-output/quirk.db quirk-output/quirk.db.bak-$(date +%Y%m%d)
   ```

   Or, for a hot backup of a database that may be in use, use SQLite's
   built-in backup API:

   ```bash
   sqlite3 quirk-output/quirk.db ".backup quirk-output/quirk.db.bak-$(date +%Y%m%d)"
   ```

3. **Confirm no scan jobs are in progress.** If you use the scheduler, pause
   it; if you have an interactive scan running, wait for it to finish. The
   migration itself only touches schema, but a clean state makes the verify
   step at the end unambiguous.

4. **Confirm release-artifact integrity** (recommended for security-sensitive
   environments). The Sigstore + Trusted Publishers pipeline used to publish
   each release is described in [`release-process.md`](release-process.md); if
   you pin to verified artifacts, verify the artifact attestation (with
   `pypi-attestations`, as described there) before installing.

## Install the new version

Install or upgrade from PyPI using the canonical distribution name:

```bash
pip install -U "quirk-scanner[all]"
```

The `[all]` extra pulls in the cloud, CBOM, database, motion, Redis, dashboard,
AD CS, DOCX, notification and ticketing extras; it does not include
`[identity]`, `[hw]` or `[api]`. If you previously installed a narrower extras
set (for example `quirk-scanner[identity]`), use the same set on upgrade — the
migration step below is independent of which extras are installed.

Verify the binary resolves to the release you just installed (the first line
prints `QU.I.R.K. v<version>`):

```bash
quirk --version
```

## Dry-run the migration

Before applying schema changes, run the migration in dry-run mode to preview
which columns would be added. This issues zero `ALTER TABLE` statements:

```bash
quirk db migrate --dry-run --db quirk-output/quirk.db
```

Each line in the output identifies one column the additive registry knows
about, formatted as `table.column: status`. Status is one of:

- **`added`** — the column is missing on disk and *would* be added on a real
  run.
- **`already-present`** — the column already exists on disk; no action would
  be taken.

A database that is missing columns will show a mix of both; a fully-current
database shows every line as `already-present`. Both outcomes are expected and
safe. The footer is `Summary: <n> added, <n> already-present, <n> total
(dry-run; no changes written)`, and the exit code is 0.

**Known limitation.** The dry-run only inspects tables that already exist and
does not create missing ones. A database from an older release that predates a
newer table (a 4.10.0 database, for example) makes the dry-run stop with a
`NoSuchTableError` traceback (for table `sensor_tokens`) and exit code 1. If
that happens, skip the dry-run — the real migration below creates missing
tables first — and rely on the backup you took above. The dry-run also refuses
to run (exit code 2) if the database file does not exist.

## Apply the migration

Once you are comfortable with the dry-run output, apply the migration:

```bash
quirk db migrate --db quirk-output/quirk.db
```

This invocation first brings the database current (it creates any missing
tables and adds any missing columns), and then prints the same one-line-per-
column report as the dry-run. Because the schema is already current by the time
the report is generated, a real run lists every column as `already-present`
and its footer reads `Summary: 0 added, <n> already-present, <n> total`; only
the dry-run lists `added` lines. The command exits 0 on success. A `--db` path
that does not exist is created as a new, empty database, so check the path.

The migration is idempotent: running it twice in a row is harmless.

## Verify

After the migration completes, perform two quick checks:

1. **Version check** — confirm the installed binary is the release you
   installed:

   ```bash
   quirk --version
   ```

2. **Idempotence check** — run the dry-run again and confirm no column
   reports `added` (the footer should read `0 added`):

   ```bash
   quirk db migrate --dry-run --db quirk-output/quirk.db
   ```

   If any line still reports `added`, the migration did not complete cleanly —
   re-run `quirk db migrate` and investigate the output.

If both checks pass, your database is current. You may now resume scheduled
scans and any other paused workflows.

## Rollback

Because `quirk db migrate` is additive-only, there is no in-tool downgrade
command. No older binary has been tested against post-upgrade `quirk.db`
files, and we do not support that configuration.

If you must roll back to a prior release, restore from the backup you took in
the pre-upgrade checklist and reinstall the previous version:

```bash
# 1. Stop anything that may be touching the live DB.
# 2. Restore the backup over the current file.
cp quirk-output/quirk.db.bak-YYYYMMDD quirk-output/quirk.db

# 3. Reinstall the previous version (replace <prev> with a version listed by
#    `pip index versions quirk-scanner`, e.g. 5.21.0).
pip install "quirk-scanner[all]==<prev>"

# 4. Confirm.
quirk --version
```

If you do not have a backup, the supported path is to roll forward: re-run
`quirk db migrate --db quirk-output/quirk.db` against the current binary, which
is safe by construction.

## Related documentation

- [`release-process.md`](release-process.md) — describes the Sigstore +
  Trusted Publishers signing pipeline behind every file published to PyPI
  (the Windows zip attached to the GitHub release carries no attestation);
  consult before pinning to verified artifacts in security-sensitive
  environments.
- [`getting-started.md`](getting-started.md) — first-run guide if you are
  installing QU.I.R.K. fresh rather than upgrading.
- [`configuration.md`](configuration.md) — reference for the `config.yaml`
  schema, including `output.db_path` (the file `quirk db migrate` operates
  on when `--config` is supplied without `--db`; if that config cannot be
  loaded, the command silently falls back to `./quirk.db`).
