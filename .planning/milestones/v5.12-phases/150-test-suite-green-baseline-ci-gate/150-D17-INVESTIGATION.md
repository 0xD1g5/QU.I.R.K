# D-17 Investigation: `tests/test_sensor_ingest.py::test_push_endpoint_exists`

**Category:** G (150-03-SUMMARY.md) — the one CI failure not cleanly explained by an
extras-exclusion or `.planning/`-gitignore boundary.

**Scope:** reproduce in a clean `.[all]`-only venv matching CI's exact install, root-cause
before deciding fix vs. quarantine. No speculative skip per D-17.

## Investigation steps

### Step 1 — Standalone

Command:
```
$HOME/.cache/quirk-ci-parity-venv/bin/python -m pytest \
  "tests/test_sensor_ingest.py::test_push_endpoint_exists" -q -m "" -v
```

Result: **FAILS**, reproduces immediately.
```
AssertionError: /api/sensor/push not found in routes:
['/favicon.ico', '/favicon.svg', '/favicon.png', '/{full_path:path}']
```

Note the route list contains *no* `/api/*` routes at all, not just the sensor one —
not health, not config, nothing from any `include_router()` call.

### Step 2 — Whole file

Command:
```
$HOME/.cache/quirk-ci-parity-venv/bin/python -m pytest tests/test_sensor_ingest.py -q -m ""
```

Result (before the fix below): `1 failed, 9 passed` — only `test_push_endpoint_exists` fails;
every other test in the file (`test_push_requires_auth`, `test_push_200_accepted`,
`test_push_409_duplicate_payload`, etc. — all of which actually exercise the route via
`TestClient.post("/api/sensor/push", ...)`) **passes**. This is the first strong signal that
the route itself works and only the *introspection* test is broken.

### Step 3 — Full-suite ordering

Since the failure already reproduced standalone (Step 1) and in the single-file run (Step 2)
with an identical, deterministic `AssertionError`, this is not an order- or
state-dependent failure — no bisection across collection order was needed. The Task 1
full-suite parity run (32 failures, see `150-04-SUMMARY.md`) reproduced the exact same
failure with the exact same message, consistent with a deterministic, version-driven cause
rather than cross-test pollution.

### Step 4 — Direct `create_app()` call + route inspection

Command:
```python
QUIRK_DB_PATH=/tmp/x.db python -c "
from quirk.dashboard.api.app import create_app
app = create_app(db_path='/tmp/x.db')
for r in app.routes:
    print(type(r).__name__, getattr(r, 'path', None))
"
```

Result: `quirk/dashboard/api/routes/sensor.py` and all other route modules import
successfully (no ImportError). `application.routes` contains:
```
Route /openapi.json
Route /docs
Route /docs/oauth2-redirect
Route /redoc
_IncludedRouter None   (x12 — one per include_router() call: health, config, pdf, scan,
                         trends, qramm, schedules, jobs.read_router, jobs.write_router,
                         merge, sensor.router, sensor.sensor_push_router)
APIRoute /favicon.ico
APIRoute /favicon.svg
APIRoute /favicon.png
Mount /assets
APIRoute /{full_path:path}
```

**Root cause identified:** `fastapi==0.141.1` / `starlette==1.6.0` (the versions
`pip install -e ".[all]"` resolves today) changed `include_router()`'s internal
representation. Routes registered via `include_router()` are no longer flattened into
individual `APIRoute` objects inside `application.routes` at include time. Instead,
`application.routes` holds one `_IncludedRouter(original_router=<APIRouter>,
include_context=_RouterIncludeContext(prefix='/api', ...))` wrapper per `include_router()`
call. The actual `APIRoute` objects live, unprefixed, under
`_IncludedRouter.original_router.routes`; the `/api` prefix is carried separately on
`include_context.prefix` and applied lazily during request matching
(`_IncludedRouter._match` / `effective_candidates`), not baked into `application.routes`
at include time.

`test_push_endpoint_exists`'s `route_paths = [r.path for r in app.routes if
isinstance(r, APIRoute)]` walk predates this change and only sees the 3 favicon routes +
catch-all that are registered directly on the app (not via `include_router()`) — every
`/api/*` route, across all 12 included routers, is invisible to this walk, not just
`/api/sensor/push`.

Confirmed via `TestClient` that the route is fully functional end-to-end:
```python
client.post("/api/sensor/push", content=b"data")  # -> 401 {"detail":"Sensor authentication required"}
client.get("/api/health")                          # -> 200 {"status":"ok"}
```
Both responses are exactly the expected production behavior (401 = `require_sensor_auth`
correctly firing; 200 = health route correctly registered and dispatching). This is
conclusive: the route registration in `quirk/dashboard/api/app.py::create_app` is correct
and unchanged; only the test's route-introspection *technique* is stale relative to the
newer FastAPI/Starlette internal route representation.

### Step 5 — Search for router-removing/replacing state

```
grep -rn "sys.modules" tests/ | grep -Ei "sensor|dashboard|app"
grep -rn "importlib.reload" tests/
grep -rn "create_app" tests/ | grep -v test_sensor_ingest
```

Results: `sys.modules` hits are all in `test_dashboard_wiring.py` (mocking `uvicorn` for a
`serve()` unit test, unrelated to `app.py`/`sensor.py`). `importlib.reload` hits are all in
`test_html_report.py`/`test_sslyze_integration.py` (unrelated modules — `writer`, `tls_mod`).
Other `create_app` call sites (`test_qramm_evidence_bridge.py`,
`test_sensor_push_id_revalidation.py`, `test_jobs_target_validation.py`, etc.) each construct
their own fresh app instance per test via the same `create_app()` factory — no shared mutable
router state, no monkeypatching of `quirk.dashboard.api.app` module internals anywhere in the
suite. Nothing in the test suite removes or replaces `sensor_push_router`.

## Disposition

**Test-construction defect.** Fixed the test, not the production code — per D-17's three
allowed dispositions, this is disposition #2 ("Test-construction / cross-test-pollution
defect — fix the test... so it asserts the same contract robustly. No skip registration.").

`_all_route_paths(app)` was added to `tests/test_sensor_ingest.py`: a recursive walk that
descends into `_IncludedRouter.original_router.routes`, prepending
`include_context.prefix`, so it resolves the exact same "is `/api/sensor/push` a live route"
contract regardless of whether the installed FastAPI/Starlette version flattens
`include_router()` routes eagerly (old behavior) or lazily wraps them (new behavior). The
test still asserts `"/api/sensor/push" in route_paths` verbatim — the contract is unchanged,
only the path-collection mechanism was made version-resilient.

### Why not the other two dispositions

- **Real product defect:** rejected. `TestClient` proves the route dispatches correctly
  (401 with no auth header, matching `require_sensor_auth`'s documented contract) — there is
  no production regression to fix. `create_app()`'s `include_router()` calls are unchanged
  and correct; the *library* changed its internal representation, not QU.I.R.K.'s code.
- **Registered environment skip (`ci_extras_gap`):** rejected. This is not caused by an
  absent optional extra — `fastapi`/`starlette` are core `dashboard` extras always present
  wherever this test runs (local dev, CI, this parity venv). Skipping would hide the test's
  entire intent (proving the route exists) rather than fix a stale detection mechanism, and
  the fix is a small, permanent, version-resilient replacement — no reason to quarantine
  something with a real, available fix.

## Verification after fix

```
$HOME/.cache/quirk-ci-parity-venv/bin/python -m pytest tests/test_sensor_ingest.py -q -m ""
  -> 10 passed
$HOME/.cache/quirk-ci-parity-venv/bin/python -m pytest tests/test_skip_registry.py -q -m ""
  -> 1 passed
```

No assertion in `test_push_endpoint_exists` was weakened — `"/api/sensor/push" in
route_paths` is still the literal assertion; only how `route_paths` is computed changed.
