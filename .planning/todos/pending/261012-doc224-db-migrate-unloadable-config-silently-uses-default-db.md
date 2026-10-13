# `quirk db migrate --config <file>` silently migrates `./quirk.db` when the config cannot be loaded

**Filed:** 2026-10-13 (Phase 224 gap closure C, docs/upgrade-guide.md audit)
**Priority:** P3 — operator trap, same family as `261012-doc224-db-migrate-default-path-creates-empty-db`
**Status:** open

## What happens

`_resolve_db_path` (`run_scan.py:1000-1013`) wraps `load_config(config_path)` in `except Exception: pass` and then
returns `"./quirk.db"`. A config that fails to load therefore does not stop `quirk db migrate --config c.yaml`; it
creates and migrates an empty `./quirk.db` in the current directory, prints `Summary: 0 added, 46 already-present,
46 total` and exits 0, while the database named in the config is untouched. Reproduced with a two-line config
(`output:` / `db_path: ./cfgdir/custom.db`): `load_config` raises `KeyError: 'assessment'`, `./quirk.db` was created
and `cfgdir/custom.db` was not. The same command with the shipped `quirk/config_template.yaml` (db_path changed to
`./cfgdir/custom.db`) created `cfgdir/custom.db` as the docs describe.

## Fix

Let `load_config` errors surface for `--config` (print the error and exit non-zero), and keep the silent fallback
only for the no-`--config` case until the default-path todo is resolved. `docs/upgrade-guide.md` now documents the
silent fallback as a caveat on the `output.db_path` bullet.

## Feasibility & Effort

- Feasibility: CONFIRMED by running the command against a partial config and against the shipped template.
- Effort: S — narrow the `except` and add a test for the failing-config path.
- Unknowns: whether `list-resumable` (the other caller of `_resolve_db_path`) relies on the swallow.
- Spike needed: no.
