---
phase: 179
slug: remediation-item-model
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-02
---

# Phase 179 — Validation Strategy

> Sourced from `179-RESEARCH.md` § Validation Architecture (HIGH confidence, every pattern read
> from live source).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`addopts = -m 'not slow'`) |
| **Quick run command** | `.venv/bin/pytest tests/test_remediation_item_model.py tests/test_scan_scope_signature.py tests/test_cve_score_guard.py -q` |
| **Full suite command** | `.venv/bin/pytest -q -m ""` |
| **Estimated runtime** | seconds quick · ~6.5 min full suite |

**Interpreter rule:** `.venv/bin/python` / `.venv/bin/pytest` only.
**Fixture idiom:** reuse the in-memory-SQLite pattern from `tests/test_qramm_models.py` /
`tests/test_hardware_device_model.py`. Do not invent a new fixture style.

---

## Sampling Rate

- **After every task commit:** the touched test file's quick-run command
- **After every plan wave:** the full quick set above
- **Before `/gsd:verify-work`:** full suite (phase-gate plan owns this run — no background runs
  from other plans; a prior executor left a stalled process)
- **Expected baseline:** exactly `1 failed` — `tests/test_skip_registry.py::test_no_unregistered_skips`
  (`DEFER-172-01`, carried). Compare failing-node SETS, never counts (Docker state changes
  collection).

---

## Per-Task Verification Map

*Task IDs filled in after planning. Requirement rows are fixed by research.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 179-01-T1 | 01 | 1 | REMED-01 | — | `remediation_items` + `remediation_item_fingerprints` + `scan_scope_signatures` created idempotently; 14-entry closed slug set | unit | `.venv/bin/pytest tests/test_remediation_item_model.py -x -q` | ✅ | ✅ green |
| 179-03-T1 | 03 | 2 | REMED-01 | T-179-01 | Join rows written explicitly at scan time, never recomputed at read time — 8 untouched plaintext endpoints persist as the literal fraction `(0, 8)`, never vanish | unit | `.venv/bin/pytest tests/test_remediation_persist.py::test_eight_plaintext_endpoints_persist_as_zero_of_eight tests/test_remediation_persist.py::test_fixing_one_of_eight_never_produced_by_this_module -x -q` | ✅ | ✅ green |
| 179-04-T1 | 04 | 3 | REMED-02 | — | `scan_scope_signatures` row per `scan_run_id`; discrete columns AND digest both populated and mutually consistent | unit | `.venv/bin/pytest tests/test_scan_scope_signature.py -x -q` | ✅ | ✅ green |
| 179-04-T2 | 04 | 3 | REMED-02 | T-179-02 | **Probe health positively asserted per family** — a stubbed degraded `ssh-audit` (TRIAGE-176-03's shape: exit 2, empty stdout, scan exit 0, `scan_error` NULL) still records the family UNHEALTHY | unit | `.venv/bin/pytest tests/test_scan_scope_signature.py::test_probe_health_positive_assertion -x -q` | ✅ | ✅ green |
| 179-01-T2 | 01 | 1 | REMED-03 | T-179-03 | `not_observed` is a distinct PERSISTED state, never derived from absence; unmatched defaults to it, **never `closed`** | unit | `.venv/bin/pytest tests/test_remediation_item_model.py::test_remediation_item_state_not_null tests/test_remediation_persist.py::test_no_written_row_has_closed_state -x -q` | ✅ | ✅ green |
| 179-02-T1 | 02 | 1 | REMED-03 | — | Operator aliases load from `config.yaml` `remediation_aliases:` into `AppConfig`, following the `broker_credentials` convention | unit | `.venv/bin/pytest tests/test_remediation_aliases_config.py -q` | ✅ | ✅ green |
| 179-05-T1 | 05 | 4 | REMED-02 | — | **Sensor-origin coverage gap documented** — sensor rows carry no `scan_run_id`, so they are excluded from closure; limitation stated in operator docs + follow-up logged | source assertion | `grep -n "sensor" docs/operators-guide.md` | ✅ | ✅ green |
| 179-01-T1 | 01 | 1 | — | — | New-table creation is idempotent — `init_db()` callable twice, no error | unit | `.venv/bin/pytest tests/test_init_db_idempotent.py -q` | ✅ extend | ✅ green |
| 179-01-T1 | 01 | 1 | — | — | The `--db-path` trap does not silently no-op the new tables | integration | `.venv/bin/pytest tests/test_run_scan_init_db_scope.py -q` | ✅ extend | ✅ green |
| 179-03-T3 | 03 | 2 | ADVISORY-01 | — | Zero scoring-path changes; firewall untouched, requirement left OPEN | guard | `.venv/bin/pytest tests/test_cve_score_guard.py tests/test_remediation_advisory_guard.py -q` | ✅ | ✅ green |
| 179-06-T0 | 06 | 5 | — | T-179-22 | `_SLUG_PRIORITY` second-source-of-truth guard (179-CONTEXT.md addendum) — proven falsifiable, RED-then-restored | unit | `.venv/bin/pytest tests/test_remediation_persist.py::test_slug_priority_key_set_matches_kind_slugs -q` | ✅ | ✅ green |
| 179-06-T3 | 06 | 5 | — | T-179-23 | Full unfiltered suite reproduces the carried one-failure baseline, zero new failing nodes | full suite | `.venv/bin/pytest -q -m ""` | ✅ | ✅ green |

*Status legend: not-yet-run (⬜) · `✅ green` · `❌ red` · `⚠️ flaky` — no row in this closed
document uses the not-yet-run state.*

---

## Wave 0 Requirements

- [x] `tests/test_remediation_item_model.py` — REMED-01 + REMED-03 (new file, Plan 01)
- [x] `tests/test_scan_scope_signature.py` — REMED-02 (new file, Plan 04)
- [x] `tests/test_remediation_aliases_config.py` — the operator-aliases half of REMED-03 (new
      dedicated file, Plan 02 — kept separate from `tests/test_config.py` to avoid shifting line
      numbers `tests/skip_registry.py` depends on for `DEFER-172-01`)

*No framework install — pytest + SQLAlchemy present.*

---

## Known Interactions

| Risk | Detail |
|---|---|
| **New tables are NOT additive migrations** | `run_additive_migration` is column-only (ALTER TABLE). All 7 prior new tables used `Base.metadata.create_all(engine, checkfirst=True)` inside an `_ensure_*_table(engine)` helper called from `init_db()`. Follow that pattern. |
| **`--db-path` silent no-op** | `init_db()` only initialises `cfg.output.db_path`. A `--db-path` at an uninitialised file yields zero rows and zero errors. New tables inherit this trap. |
| **Sensor-origin rows have no `scan_run_id`** | `_ingest_envelope` (`quirk/cli/console_cmd.py` ~line 565) sets `sensor_id`/`segment` only. Closure is scoped to CLI scans by decision; the limitation must be documented, not silently absorbed. Invisible locally — live DB is 30 rows, 0 with `sensor_id`. |
| **`quirk/db.py` is CRLF** | Everything else is LF. Scripted text-mode writes explode a 15-line change into 1151 lines. |
| **skip_registry line drift** | Allows by `(file, LINENO)`; edits shift lines and aggravate the carried `DEFER-172-01`. Distinguish drift from the carried failure; never broaden the registry to quiet it. |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A real re-engagement with `--profile quick` refuses closure rather than auto-generating false closures | REMED-02 | Requires two real scans of the same estate under different profiles; no fixture reproduces a genuine estate | Operator runs a second scan with a different profile; confirms closure is refused and the mismatch names which signature field differed |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` in frontmatter

**Approval:** approved (2026-09-02, plan 179-06 phase-close execution)
