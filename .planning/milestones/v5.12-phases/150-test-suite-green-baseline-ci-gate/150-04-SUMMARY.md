---
phase: 150-test-suite-green-baseline-ci-gate
plan: "04"
subsystem: ci
tags: [ci, pytest, venv, ci-parity, kerberos, sensor-api]

# Dependency graph
requires:
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "03"
    provides: "38-failure, 8-category real CI failure breakdown to reconcile against"
provides: "reusable CI-parity venv + authoritative failure inventory; D-16/D-17 closed"
affects: [150-05, 150-06, 150-07, 150-08, 150-09, SUITE-02, SUITE-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CI-parity venv at $HOME/.cache/quirk-ci-parity-venv, provisioned with exactly pip install -e \".[all]\" + pytest, outside the repo tree"
    - "Recursive _IncludedRouter-aware route-path walker for FastAPI route-existence assertions (fastapi>=0.141/starlette>=1.6)"

key-files:
  created:
    - .planning/phases/150-test-suite-green-baseline-ci-gate/150-D17-INVESTIGATION.md
  modified:
    - tests/test_v41_gap_closure.py
    - tests/test_sensor_ingest.py

key-decisions:
  - "No Python 3.11 interpreter available on this machine (only 3.14.6 via Homebrew/pyenv); parity venv built on 3.14.6 instead — known parity gap, documented below, does not block Task 1's install/exclusion verification goals"
  - "D-17 disposed as a test-construction defect, not a production regression or an environment skip: fastapi 0.141.1 / starlette 1.6.0 stopped flattening include_router() routes into application.routes at include time (lazy _IncludedRouter wrapper instead); confirmed via TestClient that /api/sensor/push and /api/health both dispatch correctly end-to-end"
  - "D-16 test deleted outright (not fixed in place) per plan instruction; local-only pass before deletion was traced to a stale, gitignored quirk.egg-info directory left over in the repo working tree from a pre-v4.10-rename install -- absent from any fresh checkout, which is exactly why CI raised PackageNotFoundError while local runs silently passed"

requirements-completed: []

# Metrics
duration: ~55min
completed: 2026-08-12
---

# Phase 150 Plan 04: CI-Parity Venv + D-16/D-17 Closure Summary

**Stood up a genuine CI-parity virtualenv outside the repo tree (`pip install -e ".[all]"` + `pytest`, zero `identity`/`hw`/`api` extras), ran the real full suite in it, and reconciled the result 1:1 against the real GitHub Actions run's 38-failure breakdown — then deleted the dead Phase-16 version-assertion test (D-16) and root-caused the one previously-unexplained `/api/sensor/push` failure as a stale FastAPI route-introspection technique, not a regression (D-17).**

## What Was Built

### Task 1 — CI-parity venv + failure inventory

Created `$HOME/.cache/quirk-ci-parity-venv` (outside the repo tree, per the plan's explicit
prohibition on reusing/modifying the repo's own `.venv/`) and provisioned it with exactly:

```
pip install -e ".[all]"
pip install pytest
```

**Known parity gap:** no Python 3.11 interpreter exists on this machine (`python3.11`/
`python3.12`/`python3.10` all absent; only Homebrew's `python3` at 3.14.6 and `pyenv`'s
`system` at 3.14.6 are available). The parity venv was built on **Python 3.14.6**, not
3.11 as CI's `actions/setup-python` uses. This is a real, acknowledged gap — the exclusion
boundary (D-01's extras policy) and package-metadata resolution were still validated
faithfully; interpreter-version-specific behavior differences are out of scope for this
plan to close and are not expected to matter for the extras-exclusion verification this
venv exists for.

Asserted the exclusion boundary before running anything:
```
pip list | grep -Ei "^(impacket|pysnmp|pymodbus|bacpypes3|schemathesis|openapi-spec-validator) "
```
→ **0 matches** (verification passed). `importlib.metadata.version('quirk-scanner')` →
`5.11.0` (editable install produced discoverable dist metadata).

Ran the true full suite exactly as CI does: `pytest -q -m ""`. Result:

```
32 failed, 3050 passed, 49 skipped, 79 xfailed, 1 xpassed, 127 warnings in 223.84s
```

**Reconciliation against 150-03-SUMMARY.md's 8 categories:**

| Category | CI count | Reproduced here | Notes |
|---|---|---|---|
| A — `.planning/` gitignored reads | 4 | **0** | Not reproduced: this is a local *working copy*, not a fresh public clone — `.planning/audit-2026-05-08/AUDIT-TASKS.md` exists on disk here even though it's gitignored. Confirmed via direct pytest invocation of all 4 tests: `7 passed` (folded with Category H below). This is expected, not a new gap — the tests themselves are still correctly disposed by D-15 in a later plan for the actual public-checkout case. |
| B — `hw` extras excluded | 6 | **6** | `test_bacnet_scanner.py` x2, `test_modbus_scanner.py` x3, `test_snmp_scanner_contract.py::test_arp_walk_import_guard_returns_empty_with_zero_network_calls` x1 — exact match. |
| C — `schemathesis`/`api` excluded | 18 | **18** | `test_rest_fuzzer_cascade.py` x3, `test_rest_fuzzer_dedup.py` x3, `test_rest_fuzzer_pinned_session.py` x1, `test_rest_fuzzer_probes.py` x11 — exact match. |
| D — `openapi-spec-validator` absent | 6 | **6** | All 6 `test_openapi_scanner.py` failures — exact match. |
| E — chaos-lab `email` cert bind-mount | 1 | **0** | Not reproduced: Docker is not running on this machine (`docker info` exit 1), so `test_profile_re_up_is_idempotent[email]` takes its registered `live_infra` skip path instead of attempting the bind-mount that fails in CI (where Docker *is* available). Confirmed via standalone run: `1 skipped`. Expected divergence, not a gap — D-12/D-13's cert-generation fix (later plan) addresses the underlying cause regardless of whether it reproduces in this sandbox. |
| F — `identity` excluded | 1 | **1** | `test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols` — exact match. |
| G — `/api/sensor/push` 404 | 1 | **1** | Reproduced and root-caused this plan — see Task 3 below. |
| H — package metadata `PackageNotFoundError` | 1 | **0** | Not reproduced: traced to a leftover, gitignored `quirk.egg-info/` directory in this repo's working tree from a pre-v4.10-rename install (`importlib.metadata.version("quirk")` resolves via path-based discovery to the stale `4.4.0` egg-info instead of raising `PackageNotFoundError`). Absent from any fresh checkout — exactly why CI hits the real `PackageNotFoundError` this test's own docstring already anticipated. Deleted per D-16 regardless (Task 2). |

**Total: 32 of 38 CI failures reproduced exactly** (B+C+D+F+G = 6+18+6+1+1 = 32). The 6
non-reproducing failures (A×4, E×1, H×1) are all explained by concrete, named local-vs-CI
environment differences (working-copy `.planning/` presence, Docker availability, stale
local egg-info cruft) — **none are unexplained, and no failure appeared locally that was
absent from the real CI run.**

`git status --porcelain` after the install + full-suite run showed only the pre-existing
`.planning/STATE.md` modification (from session start) plus already-gitignored egg-info
directories — no new tracked-file changes from the install.

### Task 2 — Deleted D-16 dead scaffold

Removed `test_package_manifest_version_is_4_1_0` from `tests/test_v41_gap_closure.py` in
full (method + `import importlib.metadata`, now unused). Updated the module docstring to
describe only the surviving SCORE-04 assertions. The other two methods
(`test_interactive_output_dir_default_is_quirk_output`,
`test_interactive_db_path_default_is_quirk_output`) are untouched and still pass.

Verified: `grep -rn "test_package_manifest_version_is_4_1_0" tests/ docs/` → 0 hits;
`tests/test_v41_gap_closure.py` → `2 passed`; `tests/test_skip_registry.py` → `1 passed`
(no registry entry needed or added, confirmed none existed before).

### Task 3 — D-17 root-caused: test-construction defect, not a regression

Investigated per the plan's 5-step order (full trail in
`.planning/phases/150-test-suite-green-baseline-ci-gate/150-D17-INVESTIGATION.md`, gitignored
per PUBREPO-01 so not committed to the public repo history — same pattern as `.planning/`
generally):

1. **Standalone** — reproduces immediately with a deterministic `AssertionError`.
2. **Whole file** — only this one test fails; all 9 other tests in the file (which exercise
   the route via `TestClient.post(...)`, not introspection) pass.
3. **Full-suite ordering** — already deterministic from steps 1-2, confirmed consistent with
   Task 1's full-suite run; no bisection needed (not order-dependent).
4. **Direct `create_app()` inspection** — root cause found: `fastapi==0.141.1` /
   `starlette==1.6.0` (resolved today by `.[all]`) changed `include_router()`'s internal
   representation. Routes are no longer flattened into `APIRoute` objects on
   `application.routes` at include time; each `include_router()` call instead produces a
   lazy `_IncludedRouter(original_router=<APIRouter>, include_context=...)` wrapper, with
   the actual routes living unprefixed under `original_router.routes` and the prefix applied
   during request matching. The old `[r.path for r in app.routes if isinstance(r,
   APIRoute)]` walk is blind to *every* `/api/*` route across all 12 `include_router()`
   calls in `create_app`, not just sensor/push. Confirmed via `TestClient` that
   `POST /api/sensor/push` returns `401 {"detail":"Sensor authentication required"}` and
   `GET /api/health` returns `200 {"status":"ok"}` — both exactly the expected production
   behavior. The route registration in `quirk/dashboard/api/app.py::create_app` is correct
   and unmodified.
5. **State-mutation search** — no `sys.modules` injection, `importlib.reload`, or shared
   router mutation anywhere touches `quirk.dashboard.api.app`/`sensor.py`; other
   `create_app()` call sites in the suite each build their own independent app instance.

**Disposition: test-construction defect** (per D-17's second allowed disposition). Fixed
`tests/test_sensor_ingest.py` by adding `_all_route_paths(app)`, a recursive walker that
descends into `_IncludedRouter.original_router.routes` and prepends
`include_context.prefix`, resolving the exact same "is `/api/sensor/push` a live route"
contract regardless of whether the installed FastAPI/Starlette version flattens
`include_router()` routes eagerly or wraps them lazily. The assertion itself —
`"/api/sensor/push" in route_paths` — is byte-for-byte unchanged; only the path-collection
mechanism was made version-resilient. No skip was registered (correctly excluded — this
isn't an absent-extra gap, `fastapi`/`starlette` are always present).

Verified: `pytest tests/test_sensor_ingest.py -q -m ""` → `10 passed`;
`pytest tests/test_skip_registry.py -q -m ""` → `1 passed`.

## Task Commits

| Task | Commit | Message |
|---|---|---|
| 2 | `607a1f5` | `test(150-04): delete dead Phase-16 package-version scaffold (D-16)` |
| 3 | `2e2fc00` | `fix(150-04): make sensor-push route-existence test version-resilient (D-17)` |

Task 1 produced no repo file changes (venv lives outside the repo tree; only a scratchpad
log and this SUMMARY document its output) — no commit for Task 1 itself.

## Deviations from Plan

**None requiring Rule 1-4 action.** Both investigations (D-16's local-pass mechanism, D-17's
root cause) surfaced environment-specific explanations that were fully within the plan's own
scoped investigation steps — no architectural changes, no blocking issues outside the plan's
explicit tasks.

## Issues Encountered

- **No Python 3.11 available on this machine.** Documented above as a known, accepted parity
  gap (interpreter version, not extras/install-command parity, which is what this plan's
  verification actually targets). Flagged for awareness in later plans (150-05 through
  150-09) that build on this venv — if a 3.11-specific behavior difference is ever suspected,
  this is the first place to look.
- Task 1's full-suite run initially appeared to hang around 33-38% (a `test_*` case
  attempting a live TCP connection to a real local-network host, `10.0.0.3:pcsync-https`,
  stuck in `SYN_SENT` for roughly a minute before the OS-level connect timeout fired). Not a
  new finding — this class of environment-dependent local-network probe is already a known
  quantity from prior Phase 149 triage (DNS-blocked-sandbox category); it resolved on its own
  and did not require intervention.

## User Setup Required

None. The CI-parity venv is a local build artifact (`$HOME/.cache/quirk-ci-parity-venv`,
outside the repo, not tracked by git) that later plans in this phase (150-05 through 150-09)
will reuse by rebuilding it fresh in their own execution context, per the same D-01
provisioning recipe documented in `CONTRIBUTING.md`.

## Next Phase Readiness

Ready for 150-05 and later plans in this phase. This plan's Wave 1 scope (stand up the
parity venv, close D-16, root-cause D-17) is fully complete — Categories B, C, D, F (31 tests
across 4 categories, D-09/D-10/D-11) and E (chaos-lab certs, D-12/D-13) remain for later
waves per the phase's existing plan sequence; those were explicitly out of scope for this
plan.

## Self-Check: PASSED

- `.planning/phases/150-test-suite-green-baseline-ci-gate/150-D17-INVESTIGATION.md` — FOUND
  (`grep -c "sensor/push"` → 7)
- Commit `607a1f5` — FOUND via `git log --oneline --all | grep 607a1f5`
- Commit `2e2fc00` — FOUND via `git log --oneline --all | grep 2e2fc00`
- `tests/test_v41_gap_closure.py` — FOUND, `2 passed` confirmed
- `tests/test_sensor_ingest.py` — FOUND, `10 passed` confirmed
- `tests/test_skip_registry.py` — FOUND, `1 passed` confirmed (both after Task 2 and after
  Task 3)
- `$HOME/.cache/quirk-ci-parity-venv/bin/python` — FOUND, confirmed distinct from repo's
  `.venv/bin/python`
