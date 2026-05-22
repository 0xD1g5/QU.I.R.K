# Upgrading QU.I.R.K. (v4.x → v4.10)

This guide walks an existing QU.I.R.K. installation through the upgrade to
v4.10 — the public-launch release. If you have ever run `quirk run` against
your own infrastructure on any v4.x release, this is the document for you.

## Scope

This guide applies to any installation on v4.0 or later upgrading to v4.10.
Schema changes across the v4.x line are **additive-only**: every release in
the series only adds new columns and tables — it never drops, renames, or
retypes anything. That property is what makes `quirk db migrate` safe to run
against any v4.x database, even one that has skipped several intermediate
minor versions.

There are no destructive operations in this upgrade. There is also no in-tool
rollback: rolling forward via re-running `quirk db migrate` is always
preferred, and the rollback path (if you need it) is a file copy from your
pre-upgrade backup.

## Pre-upgrade checklist

Before installing the new version, complete each of the following:

1. **Note your current version.** Record the output for your upgrade log:

   ```bash
   quirk --version
   ```

2. **Back up `quirk.db`.** The simplest backup is a file copy while no scan
   is running. From the directory containing your `quirk.db`:

   ```bash
   cp quirk.db quirk.db.bak-$(date +%Y%m%d)
   ```

   Or, for a hot backup of a database that may be in use, use SQLite's
   built-in backup API:

   ```bash
   sqlite3 quirk.db ".backup quirk.db.bak-$(date +%Y%m%d)"
   ```

3. **Confirm no scan jobs are in progress.** If you use the scheduler, pause
   it; if you have an interactive scan running, wait for it to finish. The
   migration itself only touches schema and is safe to run alongside reads,
   but a clean state makes the verify step at the end unambiguous.

4. **Confirm release-artifact integrity** (recommended for security-sensitive
   environments). The Sigstore + Trusted Publishers pipeline used to publish
   v4.10 is described in [`release-process.md`](release-process.md); if you
   pin to verified artifacts, verify the v4.10 artifact attestation before
   pulling.

## Install the new version

Install or upgrade from PyPI using the canonical distribution name:

```bash
pip install -U "quirk-scanner[all]"
```

The `[all]` extra pulls in the full set of optional connectors and report
backends. If you previously installed a narrower extras set (for example
`quirk-scanner[identity]`), use the same set on upgrade — the migration step
below is independent of which extras are installed.

Verify the binary resolves to v4.10:

```bash
quirk --version
```

## Dry-run the migration

Before applying schema changes, run the migration in dry-run mode to preview
exactly what would change. This issues zero `ALTER TABLE` statements:

```bash
quirk db migrate --dry-run
```

Each line in the output identifies one column the additive registry knows
about, formatted as `table.column: status`. Status is one of:

- **`added`** — the column is missing on disk and *would* be added on a real
  run.
- **`already-present`** — the column already exists on disk; no action would
  be taken.

A partially-upgraded database (for example, a v4.8 install) will show a mix
of both; a fully-current v4.10 database will show every line as
`already-present`. Both outcomes are expected and safe.

The footer ends with `(dry-run; no changes written)`, and the exit code is 0.

## Apply the migration

Once you are comfortable with the dry-run output, apply the migration:

```bash
quirk db migrate
```

The output shape is identical to the dry-run output (one line per known
column), but this invocation actually issues the missing `ALTER TABLE ADD
COLUMN` statements. The summary footer reports counts of `added` vs
`already-present`, and the command exits 0 on success.

The migration is idempotent: running it twice in a row is harmless. The
second invocation will simply report every column as `already-present`.

## Verify

After the migration completes, perform two quick checks:

1. **Version check** — confirm the installed binary is v4.10:

   ```bash
   quirk --version
   ```

2. **Idempotence check** — re-run the migration and confirm every column
   reports `already-present`:

   ```bash
   quirk db migrate
   ```

   If any line still reports `added` on the second run, the first invocation
   did not complete cleanly — re-run and investigate the output.

If both checks pass, your database is current. You may now resume scheduled
scans and any other paused workflows.

## Rollback

Because the v4.x schema is additive-only, there is no in-tool downgrade
command — newer columns are simply ignored by older binaries, but no older
binary has been tested against post-upgrade `quirk.db` files, and we do not
support that configuration.

If you must roll back to a prior v4.x release, restore from the backup you
took in the pre-upgrade checklist and reinstall the previous version:

```bash
# 1. Stop anything that may be touching the live DB.
# 2. Restore the backup over the current file.
cp quirk.db.bak-YYYYMMDD quirk.db

# 3. Reinstall the previous version (replace <prev> with e.g. 4.9.0).
pip install "quirk-scanner[all]==<prev>"

# 4. Confirm.
quirk --version
```

If you do not have a backup, the supported path is to roll forward: re-run
`quirk db migrate` against the current binary, which is safe by construction.

## Related documentation

- [`release-process.md`](release-process.md) — describes the Sigstore +
  Trusted Publishers signing pipeline behind every v4.10 release artifact;
  consult before pinning to verified artifacts in security-sensitive
  environments.
- [`getting-started.md`](getting-started.md) — first-run guide if you are
  installing QU.I.R.K. fresh rather than upgrading.
- [`configuration.md`](configuration.md) — reference for the `quirk.yaml`
  schema, including `output.db_path` (the file `quirk db migrate` operates
  on when `--db` is not supplied).
