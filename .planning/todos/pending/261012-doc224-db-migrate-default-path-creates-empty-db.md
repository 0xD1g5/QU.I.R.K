---
type: todo
created: 2026-10-12
source: Phase 224 plan 08 (docs/upgrade-guide.md audit)
priority: low
area: run_scan.py (_resolve_db_path)
status: pending
resolves_phase: null
owner: "999.129"
---

# `quirk db migrate` without `--db` or `--config` silently creates and migrates an empty `./quirk.db`

**Filed:** 2026-10-12 (Phase 224 plan 08, docs/upgrade-guide.md audit)
**Priority:** P3 — operator trap; no data loss, but the command reports success against the wrong file
**Status:** open
Frontmatter added by Phase 227 (D-02): priority derived from the body Priority line (P3 → low).

## What happens

`quirk db migrate` resolves its path in `run_scan.py::_resolve_db_path`, which falls back to `"./quirk.db"`
(`run_scan.py:1013`). Every other component resolves the canonical `./quirk-output/quirk.db`
(`quirk/dashboard/api/deps.py:25`, `quirk/config_template.yaml:77`). Run from a standard working directory the
command therefore creates a brand-new empty `./quirk.db`, migrates it, prints `Summary: 0 added, 46
already-present, 46 total` and exits 0, while the real database is untouched. A typo in `--db` does the same
(`quirk db migrate --db typo.db` created `typo.db` in a scratch test).

## Fix

Resolve the default through `quirk.dashboard.api.deps._default_db_path()` (it already honours `QUIRK_DB_PATH`,
the canonical path, and the multiple-legacy-DB error), and have the real run refuse a `--db` path that does not
exist unless an explicit flag asks for creation. `docs/upgrade-guide.md` currently tells operators to always pass
`--db quirk-output/quirk.db`.

## Feasibility & Effort

- Feasibility: CONFIRMED by running the command in a scratch directory.
- Effort: S — one function swap plus tests for the three resolution paths.
- Unknowns: whether any script relies on the bare `./quirk.db` default.
- Spike needed: no.
