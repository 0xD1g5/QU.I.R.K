# Phase 114: Automatic Merge Trigger - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning

<domain>
## Phase Boundary

After every enrolled sensor has pushed its results to the console, the console
**automatically** runs the existing `merge_scan()` pipeline (Option-A union CBOM
+ quantum-readiness score) so operators no longer have to run `quirk sensor
merge` by hand in the common deployment case. The merge is **toggleable**,
**failure-isolated** (a merge failure must never block or roll back the sensor
push that triggered it), and introduces **zero regression** to the manual merge
path.

**Delivers (AUTOMERGE-01–03):**
- Auto-merge fires from the `POST /api/sensor/push` success path once the
  trigger condition is met — no manual command required (AUTOMERGE-01).
- Config-driven enable/disable + trigger-condition selection; a merge failure
  never blocks/fails/rolls back an in-flight sensor push (AUTOMERGE-02).
- The manual `quirk sensor merge` command still works unchanged, coexisting
  with auto-merge — same Option-A union scoring, `coverage_warning`, and
  sensor-local `scanned_at` as v5.4 (AUTOMERGE-03).

**Locked constraints (milestone-level, carried from v5.5 / Phase 113):**
single-tenant only · additive schema only (new columns nullable/independent) ·
**no new heavy infra** (no scheduler thread, no Celery/Redis, no new process) ·
reuse `merge_scan()`, `IntegrationDelivery`, `MergeRun`, `safe_str()`, the
Phase 109/113 push failure-ladder · OS-agnostic sensor↔console wire contract
unchanged.

</domain>

<decisions>
## Implementation Decisions

### Trigger mechanism (Area 1)
- **D-01:** Auto-merge fires via a **FastAPI `BackgroundTask`** scheduled from
  the `sensor_push()` handler **after** its own `db.commit()` succeeds (the
  existing commit at ~`sensor.py:377`). The push returns `{"status":
  "accepted", ...}` immediately; the merge runs after the response is sent.
  This keeps push latency unchanged and fully decouples the merge from the push
  transaction (the structural mechanism behind SC#3 failure-isolation).
- **D-02:** The background task **must open its own DB session** (e.g. via
  `get_session(db_path)`) and resolve its own `output_dir` for CBOM artifacts —
  it cannot reuse the request-scoped `Depends(get_db)` session, which closes
  once the response is sent. Mirror the db_path/output_dir resolution already
  in `sensor_cmd._cmd_merge` (`_default_db_path()` + `os.path.dirname`). Exact
  session/path wiring is the planner's call.
- **D-03:** Trigger evaluation happens **on every successful push** (both
  trigger modes are push-evaluated — see D-08/D-09). No standalone timer,
  poller, or scheduler thread is introduced (honors "no new heavy infra").

### "All sensors in" condition + double-fire guard (Area 2)
- **D-04:** Default ("all-sensors-in") trigger condition fires when **every
  non-revoked enrolled `Sensor` has a non-null `last_push_at`** AND **at least
  one push exists newer than the latest `MergeRun.merged_at`**. This naturally
  handles repeat assessment runs (the next day's fresh pushes re-trigger) and
  avoids re-merging stale identical data. Reuses `MergeRun` timestamps already
  persisted by `merge_scan()` and the per-sensor recency logic already in
  `merge.scan._build_coverage_warning` / `sensor.py::_sensor_status`. Honor
  Phase 113's `revoked_at` — revoked sensors are excluded from the "all in" set.
- **D-05:** Concurrency guard is an **idempotent re-check inside the background
  task** (no lock, no new schema). The push schedules the task only when the
  condition is met; the task re-evaluates "is there a push newer than the
  latest `MergeRun`?" as its final gate before merging. A second task that
  finds the first already produced a covering `MergeRun` **no-ops**.
- **D-06:** The small residual TOCTOU window (two tasks both observing a newer
  push before either writes its `MergeRun`) is **accepted** for v5.5 — on
  single-tenant on-prem a duplicate `MergeRun` row is harmless (an extra
  idempotent merge artifact, `scanned_at` never rewritten). The planner MAY
  tighten this cheaply (e.g. ordering/short-circuit) but a DB lock is out of
  scope.

### Config shape & defaults (Area 3)
- **D-07:** Auto-merge is **ON by default** (matches the phase goal:
  "eliminate the mandatory manual step for the common deployment case").
  Operators who prefer explicit control disable it in config; the manual
  workflow (AUTOMERGE-03) is then exactly v5.4 behavior. Toggling the setting
  must **not affect in-flight pushes** (the toggle is read at trigger-eval
  time, per push).
- **D-08:** Config exposes (a) an **enable/disable** boolean and (b) a
  **`trigger_condition` selector** with two values: `all-sensors-in` (D-04) and
  `cadence-window` (D-09). Both ship in v5.5. Lives in the existing config
  surface (`config.yaml` — same file `sensor_push`/console settings already use;
  exact key path is the planner's call, follow existing `security.*` /
  console-config conventions).
- **D-09:** **`cadence-window` is push-evaluated, not timer-driven** (no new
  infra). When this mode is active, a push triggers a merge when the elapsed
  time since the latest `MergeRun.merged_at` exceeds the configured window
  (default to the per-sensor `expected_cadence_minutes`, currently 1440), merging
  **whatever has arrived** and emitting `coverage_warning` for any sensor not yet
  in. The push that crosses the window boundary fires the merge — no separate
  scheduler thread.

### Failure surfacing (Area 4)
- **D-10:** An auto-merge failure writes an **`IntegrationDelivery` audit row**
  (`destination="auto_merge"`, `status="failed"`, `error_summary=safe_str(exc)`
  — never stringify a raw payload/token) **plus** a `logger.warning`. This
  reuses the Phase 109/113 push failure-ladder pattern, is queryable, and the
  existing registry/dashboard surfaces already read `IntegrationDelivery` rows —
  so the operator sees it with **no new storage and no UI/React work** in this
  phase. A successful auto-merge SHOULD also write an `ok` audit row for
  symmetry (planner's call on exact strings).
- **D-11:** The merge runs entirely inside the background task's own
  try/except. Because it executes after the push's response + commit, **no
  failure path can touch the push transaction** — SC#3 is satisfied
  structurally, not by convention.

### Regression protection (AUTOMERGE-03)
- **D-12:** `merge_scan()` is **reused unchanged** as the single merge
  implementation (it is already the planted "v5.5 auto-trigger seam" per
  `_cmd_merge`'s docstring). `quirk sensor merge` (`sensor_cmd._cmd_merge`) is
  **not modified** beyond what's needed — auto and manual merge call the same
  function. Existing v5.4 merge behavior (Option-A union, `coverage_warning`,
  sensor-local `scanned_at` never rewritten) is preserved by construction.

### Claude's Discretion
- Exact config key path/names for the enable flag and `trigger_condition`
  selector (follow existing `config.yaml` conventions).
- Exact background-task DB session + `output_dir` wiring (mirror `_cmd_merge`).
- Whether a successful auto-merge writes an `ok` `IntegrationDelivery` row and
  its exact `destination`/`error_summary` strings.
- Whether to add a lightweight surfacing of "last auto-merge result" to the
  registry response (optional sugar — not required; dashboard/banner work is
  explicitly out of scope this phase).
- Whether/how to expose the resolved `cadence-window` minutes (reuse
  `expected_cadence_minutes` default vs a dedicated config key).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Distributed architecture & wire contract
- `docs/architecture-distributed.md` — sensor/console split, locked wire
  contract and forbidden-additions the auto-merge change must not violate.
- `quantum-chaos-enterprise-lab/expected_results_distributed.md` — distributed
  e2e oracle; auto-merge must keep `lab.sh distributed e2e` green and must not
  change manual-merge expected output.

### The merge seam (reuse, do not reinvent)
- `quirk/merge/scan.py` — `merge_scan(db, *, now, stale_days, profile, weights,
  output_dir)` is the standalone auto-trigger callable. `_build_coverage_warning`
  (L34) for the "all in / missing sensors" recency logic; `MergeRun` persistence
  (`merged_at`, `coverage_warning_json`, `endpoint_count`, `sensor_count`).
- `quirk/cli/sensor_cmd.py` — `_cmd_merge` (L770) is the manual-merge wrapper +
  the documented "v5.5 auto-trigger seam (D-06)"; mirror its db_path/output_dir
  resolution. MUST remain regression-free (AUTOMERGE-03).

### The push trigger point
- `quirk/dashboard/api/routes/sensor.py` — `sensor_push()` handler (L203+) on
  `sensor_push_router` (`require_sensor_auth`). Success path ends at the final
  `db.commit()` (~L377) then `return {"status": "accepted", ...}`. The
  `BackgroundTask` is scheduled here, after commit. `_audit()` (L172) +
  `IntegrationDelivery` import are the failure-surfacing pattern to extend.
  `_sensor_status()` (L84) replicates the per-sensor recency logic.
- `quirk/dashboard/api/middleware/sensor_auth.py` — `require_sensor_auth`
  (Phase 113); `request.state.sensor_id` is token-authoritative.

### Models
- `quirk/models.py` — `Sensor` (L269, `last_push_at`, `expected_cadence_minutes`),
  `SensorToken` (L291, `revoked_at` from Phase 113 — exclude revoked from "all in"),
  `MergeRun` (merge ledger), `IntegrationDelivery` (audit rows).

### Operator docs (update target)
- `docs/operators-guide.md` — document the auto-merge toggle, the two trigger
  conditions, default-ON behavior, and how to read auto-merge audit rows.

### Requirements
- `.planning/REQUIREMENTS.md` §"Automatic Merge Trigger (AUTOMERGE)" — AUTOMERGE-01–03.

### Prior phase context
- `.planning/phases/113-per-sensor-authentication/113-CONTEXT.md` — per-sensor
  auth + `revoked_at`; the push path this phase hooks onto.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `merge_scan()` (`quirk/merge/scan.py`) — complete union→score→CBOM→`MergeRun`
  pipeline; the entire merge already exists as a standalone callable. This phase
  *calls* it, it does not reimplement merging.
- `_build_coverage_warning()` / `_sensor_status()` — per-sensor `last_push_at`
  recency logic for computing "all in" / "missing" / "stale".
- `IntegrationDelivery` + `_audit()` push-path pattern — extend with an
  `auto_merge` destination for failure (and optional success) surfacing.
- `MergeRun.merged_at` — the "since last merge" watermark for the trigger
  condition and the idempotent re-check.
- FastAPI `BackgroundTasks` — built-in, no new dependency, runs after response.

### Established Patterns
- **Push commits its own transaction, then returns** — the trigger must attach
  strictly after that commit so a merge failure cannot touch push data.
- **`safe_str()` / fixed-string audit summaries** — never leak a raw payload or
  stringified exception into `IntegrationDelivery`.
- **Additive, nullable schema only** — prefer reusing `MergeRun` timestamps over
  adding new columns; no merge-lock table.
- **Honor `revoked_at` (Phase 113)** — revoked sensors are not part of the
  "all enrolled checked in" set.

### Integration Points
- Schedule a `BackgroundTask(run_auto_merge, ...)` in `sensor_push()` after the
  final `db.commit()`, gated by config + trigger condition.
- New config keys: auto-merge enable flag + `trigger_condition` selector
  (`all-sensors-in` | `cadence-window`) in the existing `config.yaml` surface.
- New `IntegrationDelivery` `destination="auto_merge"` audit rows.
- `docs/operators-guide.md` auto-merge section.

</code_context>

<specifics>
## Specific Ideas

- The AUTOMERGE acceptance/gating tests should assert:
  1. With auto-merge ON and `all-sensors-in`: after the **last** enrolled
     sensor pushes, a `MergeRun` is produced (merged CBOM + score) with **no**
     manual `quirk sensor merge` call.
  2. With auto-merge OFF: the same final push produces **no** `MergeRun`; manual
     merge still works identically to v5.4.
  3. A merge that raises (e.g. bad/unmergeable data) leaves the triggering
     push's `accepted` response + ingested rows intact, and writes an
     `IntegrationDelivery` `auto_merge`/`failed` row.
  4. Two near-simultaneous final pushes do not corrupt state (at most a
     harmless duplicate `MergeRun`; the idempotent re-check coalesces).
  5. `cadence-window` mode: a push after the window elapses triggers a merge
     with `coverage_warning` listing not-yet-in sensors.
  6. Manual `quirk sensor merge` regression: identical Option-A union CBOM +
     `coverage_warning` + sensor-local `scanned_at` as v5.4.

</specifics>

<deferred>
## Deferred Ideas

- **Standalone scheduler/poller** for true time-based cadence merging — rejected
  for v5.5 (conflicts with "no new heavy infra"). cadence-window is
  push-evaluated instead (D-09). Revisit if a fleet needs merges without pushes.
- **Dashboard banner / React indicator** for "last auto-merge failed" — out of
  scope this phase (audit row + log is the v5.5 surfacing). Candidate for a UI
  phase if operators want at-a-glance auto-merge health.
- **DB merge-lock row / advisory lock** for a hard double-merge guarantee —
  not needed on single-tenant v5.5 (idempotent re-check + harmless duplicate is
  sufficient). Revisit only if multi-tenant/SaaS makes duplicates costly.
- **External cron + `quirk sensor merge`** for cadence — documented option but
  not the chosen in-product path; remains available to operators regardless.

</deferred>

---

*Phase: 114-automatic-merge-trigger*
*Context gathered: 2026-05-26*
