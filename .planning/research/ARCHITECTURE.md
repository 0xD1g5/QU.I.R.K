# Architecture Research — v5.4 Distributed On-Prem Scanner

**Domain:** Agent/console split integrated into an existing single-package scanner
**Researched:** 2026-05-25
**Confidence:** HIGH (grounded in real repo symbols; no speculation)

---

## System Overview

```
SEGMENT A (DMZ / PCI zone)                  SEGMENT B (OT/ICS VLAN)
+----------------------------------+         +------------------------------+
|  quirk sensor                    |         |  quirk sensor                |
|  +---------------+               |         |  +---------------+           |
|  | run_scan.py   |  (unchanged)  |         |  | run_scan.py   | (unchanged|
|  | local quirk.db (ephemeral)    |         |  | local quirk.db (ephemeral)|
|  +------+--------+               |         |  +------+--------+           |
|         | sensor push            |         |         | sensor push        |
|         | POST /api/sensor/push  |         |         | POST /api/sensor/push
+---------+------------------------+         +---------+--------------------+
          | HTTPS (outbound only)                      | HTTPS (outbound only)
          +-----------------------------+--------------+
                                        v
+--------------------------------------------------------------------------+
|  CONSOLE  (customer-premises or air-gap-friendly host)                   |
|                                                                          |
|  quirk serve  (existing FastAPI -- quirk/dashboard/server.py)            |
|  +------------------------------------------------------------------+    |
|  |  NEW: POST /api/sensor/push  (routes/sensor.py)                  |    |
|  |       * require_auth() (reuse middleware/auth.py)                 |    |
|  |       * idempotent upsert on (host, port, sensor_id, scan_id)    |    |
|  |       * writes IntegrationDelivery audit row (reuse models.py)   |    |
|  +------------------------------------------------------------------+    |
|  +------------------------------------------------------------------+    |
|  |  NEW: merge pipeline  (quirk/sensor/merge.py)                    |    |
|  |       * gathers CryptoEndpoint rows WHERE sensor_id IS NOT NULL  |    |
|  |       * feeds existing build_evidence_summary() unchanged         |    |
|  |       * feeds existing compute_readiness_score() unchanged        |    |
|  |       * feeds existing build_cbom() unchanged                     |    |
|  +------------------------------------------------------------------+    |
|  +------------------------------------------------------------------+    |
|  |  EXISTING: console SQLite  (quirk.db -- authoritative store)     |    |
|  |  EXISTING: /api/scan/latest  (queries by scanned_at timestamp)   |    |
|  |  EXISTING: React dashboard (no change needed for v5.4)           |    |
|  +------------------------------------------------------------------+    |
+--------------------------------------------------------------------------+
```

---

## 1. Service Roles: Same Package, New Mode Flags

### Recommended approach: same package, two new subcommand intercepts in run_scan.py

The existing subcommand dispatch pattern is a series of
`if len(_sys.argv) > 1 and _sys.argv[1] == "<verb>"` intercepts at the top of
`run_scan.py`. Every prior capability (serve, schedule, scheduler, doctor, compliance,
qramm, analyze-token, token, export, ticket, errors, db) follows this identical pattern.
Adding `sensor` and `console` as two more intercepts requires no architectural change and
no package split.

```
quirk sensor  --config quirk.yaml --console-url https://console:8512 --sensor-id dmz-01
quirk console --config quirk.yaml   # launches the console-aware serve mode
```

Do NOT split into two packages. The single `quirk-scanner` PyPI distribution is already
the packaging model. Splitting would require a separate install on every sensor host, break
the existing pip install path, and create a divergent release train. Single package with
mode flags is the established precedent.

### How `quirk serve` becomes the console ingestion host

`quirk serve` already launches `quirk/dashboard/server.py` which mounts the FastAPI app
(the app factory is in `quirk/dashboard/api/app.py`). The ingestion endpoint
`POST /api/sensor/push` is a new route file dropped into `quirk/dashboard/api/routes/`
and included in the existing router registration. No new server process. The console
operator still runs `quirk serve` (or `quirk console` as a thin alias); the presence of
the new `/api/sensor/push` route is always available, gated by `require_auth()`.

An alternative `quirk console` subcommand can simply invoke the same `serve` logic with a
console-mode flag set -- or it can just be documentation that tells operators to run
`quirk serve`. Either is acceptable; the key is that no second process or port is required.

### Where the sensor reuses run_scan.py unchanged

The sensor mode is a thin wrapper:

1. Invoke `run_scan.py` locally (exactly as the scheduler does: `sys.executable -m
   run_scan --config ... --target ... --profile ...`). This is unchanged.
2. After the scan completes, read the resulting `CryptoEndpoint` rows from the local
   sensor `quirk.db`.
3. Serialize them to the wire format (see Section 3).
4. POST to the console's `/api/sensor/push`.
5. Optionally purge or archive the local sensor DB after a confirmed push.

The sensor never touches scoring, CBOM, or the evidence pipeline -- those run only on the
console after merge. The sensor is a scan runner + push agent; run_scan.py is unchanged.

The `quirk sensor` subcommand implementation lives in `quirk/cli/sensor_cmd.py` and
follows the same deferred-import + `_dispatch_schedule`-style pattern as the notification
and SIEM hooks already in `scheduler_cmd.py` (lines 171-197).

---

## 2. Data Model: Additive `sensor_id` + `segment` Columns

### The problem

The same RFC1918 address `10.0.0.1:443` can exist in Segment A (DMZ) and Segment B (PCI)
and represent two distinct services with different crypto posture. Today
`CryptoEndpoint` has no segment dimension, so the two rows would be indistinguishable.

### Solution: two new nullable columns on `crypto_endpoints`

```python
# In quirk/models.py -- append to CryptoEndpoint
sensor_id  = Column(String(128), nullable=True, index=True)  # e.g. "dmz-01"; NULL = local/legacy scan
segment    = Column(String(255), nullable=True)              # freeform label e.g. "DMZ / 10.0.0.0/24"
```

Both are `nullable=True`. Existing rows remain valid with `NULL` in both columns. A single-
host scan (the existing behavior) produces rows with `sensor_id=NULL` -- the system treats
NULL as the implicit "local" sensor. No existing query breaks.

The natural key for cross-sensor dedup becomes:
```
(host, port, sensor_id, scan_id)
```
where `scan_id` is the ISO timestamp that already serves as the scan session identity
(`run_scan.py:913` -- `scan_run_id: Optional[str] = run_stats["started_utc"]`).

### Migration path

Use the existing `_ensure_columns` helper in `quirk/db.py` (the Phase 77 D-21 generic
SQLite ALTER-TABLE-IF-MISSING helper, lines 127-157). Add an entry to `_ADDITIVE_MIGRATIONS`
(line 172 pattern):

```python
("crypto_endpoints", (
    ("sensor_id", "TEXT"),
    ("segment",   "TEXT"),
)),
```

This is idempotent, runs at `init_db`, and follows the exact pattern used for every prior
column addition. No migration tooling (Alembic) is needed or desirable -- SQLite ALTER
TABLE ADD COLUMN is the established contract in this project.

### Impact on downstream consumers

| Consumer | Impact | Action |
|---|---|---|
| `build_evidence_summary()` in `quirk/intelligence/evidence.py` | Takes `Iterable[CryptoEndpoint]`; new columns are ignored | No change |
| `compute_readiness_score()` in `quirk/intelligence/scoring.py` | Takes the evidence dict; no schema coupling | No change |
| `build_cbom()` in `quirk/cbom/builder.py` | Takes `list[CryptoEndpoint]`; new columns are ignored by all three passes | No change |
| `_fetch_session_endpoints()` in `quirk/intelligence/trends.py` | Filters by `CryptoEndpoint.scanned_at`; no coupling to new columns | No change; may need sensor-scope filter for per-sensor trend queries (future) |
| `notify/dispatcher.py` | Filters by `CryptoEndpoint.scanned_at` | No change |
| Dashboard `/api/scan/latest` route | Constructs `FindingItem` from endpoint state | Minor: expose `sensor_id`/`segment` in the Pydantic schema if the UI needs them; not required for v5.4 |
| `qramm/evidence_bridge.py` | Queries latest scan date; no protocol coupling | No change |

The scoring engine, CBOM builder, and evidence collector are all pure functions over
`list[CryptoEndpoint]`. Adding two new columns they never read is zero-impact.

### How a multi-sensor merged scan is represented vs. a normal single scan

A merged scan is NOT a new concept in the ORM. It is simply a query that gathers
`CryptoEndpoint` rows across multiple `sensor_id` values for a given time window (the
console-side merge scan timestamp). The merge pipeline (see Section 4) collects them into
one list and passes that list to the existing functions. The result is stored as a new scan
session row with a console-assigned `scan_id`. Normal single-host scans are unaffected --
they continue to produce rows with `sensor_id=NULL` and are queried the same way.

---

## 3. Ingestion API: Console Endpoint Shape

### Route

```
POST /api/sensor/push
Authorization: Bearer <QUIRK_API_TOKEN>   # reuses require_auth() from middleware/auth.py
Content-Type: application/json
```

### Wire payload

```json
{
  "sensor_id": "dmz-01",
  "segment": "DMZ / 10.0.0.0/24",
  "scan_id": "2026-05-25T14:32:00.123456",
  "sensor_version": "5.4.0",
  "endpoints": [
    {
      "host": "10.0.0.1",
      "port": 443,
      "protocol": "TLS",
      "scanned_at": "2026-05-25T14:32:05.000000",
      "tls_version": "TLSv1.2",
      "... all CryptoEndpoint fields as JSON-serializable values ..."
    }
  ]
}
```

The `endpoints` array is the direct serialization of the sensor's local `CryptoEndpoint`
rows. Every existing column that is not `NULL` is included. New columns (`sensor_id`,
`segment`) are not needed in the payload body -- the console applies them from the envelope.
Integer PK (`id`) is excluded from the payload; the console assigns new PKs on insert.

Design constraints:
- The payload schema is versioned via `sensor_version`. The console rejects payloads from
  sensors more than one major version older.
- Maximum payload size should be configurable (suggest 50 MB default). Sensors scanning
  very large inventories should chunk by stage rather than sending all at once.
- Chunked push: a sensor can POST multiple times for the same `scan_id`. The console uses
  `(host, port, sensor_id, scan_id)` as an upsert key -- idempotent re-push handling.

### Idempotency

On each pushed endpoint, the console does an INSERT OR REPLACE keyed on
`(host, port, sensor_id, scan_id)` (using SQLite's `ON CONFLICT` or a prior SELECT +
UPDATE pattern consistent with the existing `_ensure_columns` approach). Re-sending the
same scan is safe.

### Auth reuse

`require_auth()` in `quirk/dashboard/api/middleware/auth.py` already supports both
`Authorization: Bearer` and `X-API-Key` header formats with `hmac.compare_digest` timing-
safe comparison. The sensor uses the same `QUIRK_API_TOKEN` env var. No new auth
mechanism is needed. The sensor's config file carries a `console_url` and
`console_api_token` that mirror the existing `security.api_token` YAML field pattern.

### Delivery audit

Each `POST /api/sensor/push` writes one `IntegrationDelivery` row (reusing the
`integration_deliveries` table from models.py lines 245-260):

```python
IntegrationDelivery(
    scan_id=payload.scan_id,
    destination=f"sensor:{payload.sensor_id}",
    status="ok",   # or "failed"
    attempted_at=utcnow(),
    error_summary=safe_str(exc) if failed else None,
)
```

`safe_str(exc)` from `quirk/util/safe_exc.py` is already the established pattern for
error scrubbing (regex-strips API keys/tokens from exception text).

---

## 4. Merge Pipeline: Console Re-Runs the Canonical Engines

### Recommended: console collects endpoint rows, feeds the canonical engines unchanged

Do NOT merge already-scored results. Do NOT fork the scoring engine. The canonical path is:

```
sensor A endpoints (CryptoEndpoint rows, sensor_id="dmz-01")
sensor B endpoints (CryptoEndpoint rows, sensor_id="ot-vlan-01")
          |
          v
    merge_scan(console_db, scan_id="console-2026-05-25T14:35:00")
          |
          v
    merged_endpoints = list of all CryptoEndpoint rows for this console scan_id
          |
          v
    build_evidence_summary(merged_endpoints)   <- unchanged, quirk/intelligence/evidence.py
          |
          v
    compute_readiness_score(evidence)           <- unchanged, quirk/intelligence/scoring.py
          |
          v
    build_cbom(merged_endpoints)                <- unchanged, quirk/cbom/builder.py (3 passes)
          |
          v
    write_cbom_files(bom, output_dir)           <- unchanged
```

This is the only approach that guarantees:
- One canonical score (the six-subscore -> `/1.5` rollup in `scoring.py:288-291`)
- One canonical CBOM (the three-pass dedup in `builder.py:445-end`)
- The evidence schema (`EVIDENCE_SCHEMA_VERSION = "1.0.0"`) is respected
- Future scoring weight changes automatically apply to merged scans

The alternative -- merging pre-scored sub-results (averaging scores from sensors) -- is
wrong because the six subscores are not additive across disjoint endpoint populations. The
scoring engine applies ratio-based penalties (e.g., `_ratio(weak_cipher_count, denom)`)
that require the full endpoint population as denominator. Merging subscores from sensors
with different endpoint counts produces a meaningless weighted average, not a defensible
score.

### Where merge_scan lives

New module: `quirk/sensor/merge.py`. It:

1. Opens the console SQLite (same `db.py` / `init_db()` path, no new DB engine).
2. Queries `CryptoEndpoint` rows where `sensor_id` is not NULL and `scanned_at` falls
   within the merge window (user-configured tolerance, e.g., +-10 minutes of the console-
   triggered merge time).
3. Passes the list to `build_evidence_summary()`, `compute_readiness_score()`, and
   `build_cbom()`.
4. Persists the merged scan results (reports + CBOM files) to the console output directory.
5. Optionally triggers the existing notification/SIEM hooks via the same `_dispatch_schedule`
   after-hook pattern (Phase 101/103 hooks in `scheduler_cmd.py:171-197`).

The merge scan is triggered by a new CLI subcommand `quirk sensor merge` (or by the
console's scheduler when all expected sensors have checked in -- a future refinement).

### CBOM dedup across sensors

`build_cbom()` already deduplicates algorithm components by `bom_ref` key in `algo_registry`
(Pass 1, `builder.py:461`). Two sensors both finding `RSA-2048` produce one algorithm
component in the merged CBOM. Cross-sensor dedup of X.509 certificate components (Pass 2)
uses `(cert_subject, cert_issuer, cert_not_after)` -- a cert present in two segments
(e.g., a shared wildcard cert) produces one CBOM component. This dedup behavior comes for
free from the existing logic.

---

## 5. Build Order: Dependency-Ordered Component Sequence

### Phase 1 (architecture doc -- mandatory first, no code)

Produce the architecture document itself. This is `999.58` folded in as the anchor phase.
The doc must specify:
- Final sensor/console wire format (Section 3 above, confirmed)
- Final `sensor_id`/`segment` column names and types (Section 2 above, confirmed)
- Windows sensor contract constraints (Section 6 below)
- Console merge trigger mechanism (manual `quirk sensor merge` vs. auto-poll)

No code ships in Phase 1. The output is the confirmed architecture doc bound to phases 2-N.

### Phase 2: data model + migration (net-new: 2 columns + `_ADDITIVE_MIGRATIONS` entry)

Components: `quirk/models.py` (2 new nullable columns on `CryptoEndpoint`), `quirk/db.py`
(one new entry in `_ADDITIVE_MIGRATIONS`).

This is purely additive. Single-host scans keep working; existing tests pass unchanged.

Existing code touched: `quirk/models.py` (additive), `quirk/db.py` (additive).
Net-new code: none beyond the two additions above.

### Phase 3: sensor push CLI + sensor_cmd.py (net-new module)

Component: `quirk/cli/sensor_cmd.py` -- the `quirk sensor` subcommand.

Sub-steps:
- `quirk sensor enroll` -- write `sensor_id`, `console_url`, `console_api_token` to
  config (additive YAML section, mirrors existing `[security]` config pattern).
- `quirk sensor push` -- reads local DB, serializes endpoints, POSTs to console.
- Wire into `run_scan.py` subcommand dispatch (one `if _sys.argv[1] == "sensor"` block).

Existing code touched: `run_scan.py` (one new intercept block, ~15 lines).
Net-new code: `quirk/cli/sensor_cmd.py`.

OS-agnostic constraint: `sensor_cmd.py` must use `pathlib.Path` throughout, not string
concatenation. No `subprocess.Popen(["/bin/bash", ...])` -- use `sys.executable -m run_scan`
exactly as `_dispatch_schedule` does.

### Phase 4: console ingestion API (net-new route)

Component: `quirk/dashboard/api/routes/sensor.py` -- `POST /api/sensor/push`.

Depends on Phase 2 (columns exist) and Phase 3 (wire format is defined).

Existing code touched:
- `quirk/dashboard/api/app.py` -- include the new router (one `app.include_router()` line).
- `quirk/dashboard/api/middleware/auth.py` -- no change; `require_auth()` is reused as-is.
- `quirk/models.py` -- no change; `IntegrationDelivery` already exists.

Net-new code: `quirk/dashboard/api/routes/sensor.py`.

### Phase 5: merge pipeline (net-new module)

Component: `quirk/sensor/merge.py` -- the cross-sensor merge scan.

Depends on Phase 4 (endpoints are being pushed and stored with `sensor_id` set).

Existing code touched: none (calls existing `build_evidence_summary`, `compute_readiness_score`,
`build_cbom`, `write_cbom_files` as imports -- no modifications to those modules).

Net-new code: `quirk/sensor/merge.py`, plus `quirk sensor merge` subcommand in
`quirk/cli/sensor_cmd.py` (additive to Phase 3 work).

### Phase 6: console dashboard awareness (modified existing)

Expose `sensor_id`/`segment` in `/api/scan/latest` Pydantic response and the React
dashboard findings table. This is the first phase that touches the frontend.

Existing code touched:
- `quirk/dashboard/api/schemas.py` -- add `sensor_id`/`segment` fields to `FindingItem`
  (nullable, backward-compat).
- `quirk/dashboard/api/routes/scan.py` -- populate those fields in the endpoint constructor.
- React dashboard -- add sensor/segment column to findings table (optional filter by sensor).

Net-new code: minimal frontend additions.

### Phase 7: stabilization tail (existing backlog items)

999.59 operators-guide all-configurations coverage, `_NoRedirectHandler` extract to
`quirk/util/no_redirect.py`, residual dep hygiene. These are independent of the sensor
feature train and can be sequenced anywhere after Phase 1.

---

## 6. Cross-Platform (OS-Agnostic) Sensor Contract

### The constraint

The v5.4 decision: the sensor/console wire contract must not bake in POSIX assumptions
even if full Windows packaging defers to v5.5. A Windows sensor running on Python for
Windows must be able to push results to a Linux console and vice versa without any
contract change.

### What the wire format must avoid

| POSIX assumption | Risk | Mitigation |
|---|---|---|
| File paths in payload (e.g., `source_scan_json` contains `semgrep file:line` paths) | Backslash vs. forward-slash in serialized paths | Normalize to forward-slash at serialization time on the sensor before push |
| `scanned_at` timezone handling | Windows `datetime.now()` may include tzinfo depending on Python version | Apply `_as_utc_naive()` from `quirk/intelligence/evidence.py:26` at serialization |
| `output/scheduled/` path in scheduler | Hardcoded path separator | Already uses `pathlib.Path` in `_dispatch_schedule` (`Path("output/scheduled") / safe_name / ...`, line 136) -- preserve this |
| SQLite path (`./quirk.db`) | Working directory assumptions differ on Windows | Use `pathlib.Path.cwd() / "quirk.db"` not a relative string |
| `sys.executable -m run_scan` subprocess invocation | Works on Windows | Already the established pattern in `_dispatch_schedule`; `sensor_cmd.py` must follow it |

### Windows scheduling host

The `scheduler_cmd.py` subprocess loop uses no POSIX-specific scheduling (no cron, no
systemd). It is a pure Python `while True: sleep(60)` loop (lines 207-223). This works on
Windows as-is. A Windows Service wrapper (e.g., NSSM or `pywin32`) can host it -- but
that is packaging, not architecture. The loop itself is already cross-platform.

### Validation path for Windows

The chaos lab (Linux Docker Compose) cannot test a Windows sensor. The arch doc must
specify a Windows CI path: a GitHub Actions `windows-latest` runner that:
1. Installs `quirk-scanner` from the built wheel.
2. Runs `quirk sensor push --dry-run` (a new flag that serializes but does not POST).
3. Asserts the payload is valid JSON with no backslash paths.

This is net-new CI work but scoped to a smoke test, not a full scan against live targets.

### What defers to v5.5

- Windows-native packaging (PyInstaller frozen executable or Windows container).
- Windows Service registration script.
- `lab.sh` equivalent for Windows validation.
- Full POSIX-ism audit of the scanner (not just the sensor path).

The v5.4 commitment is: any code added in v5.4 uses `pathlib.Path`, not hardcoded
POSIX separators, and the wire format carries no OS-specific data.

---

## Component Inventory: Net-New vs. Modified

| Component | File | Net-New or Modified | Phase |
|---|---|---|---|
| Architecture doc | `.planning/phases/NN-sensor-arch/` | Net-new (doc only) | 1 |
| `sensor_id` + `segment` columns | `quirk/models.py` | Modified (additive) | 2 |
| `_ADDITIVE_MIGRATIONS` entry | `quirk/db.py` | Modified (additive) | 2 |
| Sensor CLI subcommand | `quirk/cli/sensor_cmd.py` | Net-new | 3 |
| Subcommand dispatch intercept | `run_scan.py` | Modified (~15 lines) | 3 |
| Console ingestion route | `quirk/dashboard/api/routes/sensor.py` | Net-new | 4 |
| Router registration | `quirk/dashboard/api/app.py` | Modified (1 line) | 4 |
| Merge pipeline | `quirk/sensor/merge.py` | Net-new | 5 |
| `quirk sensor merge` subcommand | `quirk/cli/sensor_cmd.py` | Modified (additive) | 5 |
| `FindingItem` schema | `quirk/dashboard/api/schemas.py` | Modified (additive nullable fields) | 6 |
| Scan route endpoint construction | `quirk/dashboard/api/routes/scan.py` | Modified (populate new fields) | 6 |
| React findings table | `src/dashboard/` | Modified (new columns) | 6 |
| Windows CI smoke test | `.github/workflows/` | Net-new | 3-4 |

### Untouched by v5.4 (no modifications required)

- `quirk/intelligence/scoring.py` -- `compute_readiness_score()` is unchanged
- `quirk/intelligence/evidence.py` -- `build_evidence_summary()` is unchanged
- `quirk/cbom/builder.py` -- `build_cbom()` and all three passes are unchanged
- `quirk/cbom/writer.py` -- `write_cbom_files()` is unchanged
- `quirk/dashboard/api/middleware/auth.py` -- `require_auth()` is reused as-is
- `quirk/models.py:IntegrationDelivery` -- delivery audit table reused as-is
- `quirk/util/safe_exc.py` -- `safe_str()` reused as-is
- `quirk/util/url_allowlist.py` -- `validate_external_url()` reused for console URL validation
- `quirk/cli/scheduler_cmd.py` -- no change; `_dispatch_schedule` is the pattern model only
- `quirk/notify/dispatcher.py` -- no change; notification hooks fire after merge if configured

---

## Key Integration Seams and Risk Assessment

### Highest-risk seam: `sensor_id` NULL handling in existing queries

The existing `_fetch_session_endpoints()` in `quirk/intelligence/trends.py:83` and the
`/api/scan/latest` query in `quirk/dashboard/api/routes/scan.py` both filter by
`CryptoEndpoint.scanned_at`. They do not filter on `sensor_id`. After Phase 2, if the
console DB contains both local-scan rows (`sensor_id=NULL`) and pushed-sensor rows
(`sensor_id="dmz-01"`), a query by `scanned_at` alone may pick up a mix.

Mitigation: the console merge pipeline writes a new `scan_id` for the merged scan. The
existing query path (`/api/scan/latest`) then operates on the merged rows with that
`scan_id`. Sensor push rows are stored with the sensor's original `scan_id` (the sensor's
local ISO timestamp). The dashboard always shows the most-recent `scan_id` -- which is the
console merge scan, not individual sensor pushes. Individual sensor push rows are
intermediate data, not the authoritative result. Implement `sensor_id IS NULL OR
sensor_id = :sensor_id` filter variants as needed in the trends route for per-sensor drill-
down (future enhancement, not required for v5.4).

### Medium-risk seam: `scanned_at` grouping after sensor push

`notify/dispatcher.py:88` and `trends.py:50` both format `CryptoEndpoint.scanned_at` as
a string to group by session. Sensor pushes arrive with the sensor's local `scanned_at`
values (UTC naive, per existing `_as_utc_naive()` convention). The console must NOT rewrite
`scanned_at` to the push-receipt time -- that would break the grouping semantics. The
sensor's `scanned_at` is preserved verbatim; the console assigns its own `scan_id` for the
merged result only.

### Low-risk seam: CBOM `serialNumber` uniqueness

`build_cbom()` in `builder.py:445` generates a `serialNumber` for the BOM. For merged
CBOMs it reflects the console merge time. No collision risk; each merge invocation
produces a distinct value. The existing dedup behavior (Pass-1 `algo_registry` keyed by
`bom_ref`) handles cross-sensor algorithm dedup correctly with no changes.

---

## Anti-Patterns to Avoid

### Anti-Pattern: merge pre-scored results from sensors

Each sensor computes its own score, console averages them. This is wrong because the six
subscores use ratio-based penalties over the full endpoint population (`_ratio(count, denom)`
in `scoring.py`). A partial-population score is not comparable to a full-population score.
The console must re-run scoring over the union of all endpoints.

### Anti-Pattern: sensor keeps a persistent authoritative DB

The sensor's local `quirk.db` is ephemeral -- scan, push, optionally purge. If sensors
accumulate data indefinitely the console can never be the authoritative single store. The
sensor DB is a staging buffer, not a replica.

### Anti-Pattern: two-package split (quirk-sensor + quirk-console)

Doubles the release train, breaks the pip install story, requires sensors to install a
different package than the console. The existing single-package + subcommand-mode pattern
scales to this use case without a split.

### Anti-Pattern: inbound firewall access to segments

The push model is outbound-only by design. The console never initiates a connection to a
sensor. Any architecture that requires the console to poll or SSH into a sensor node
violates the segmentation requirement (no inbound access to segments).

### Anti-Pattern: bearer token in query parameters for sensor push

The existing auth middleware (`middleware/auth.py`) uses `Authorization: Bearer` header and
`X-API-Key` header. Do not accept the token as a query parameter -- it would appear in web
server access logs. The sensor's HTTP client must use the header form.

---

## Sources

- `quirk/models.py` -- `CryptoEndpoint` schema (lines 9-94), `IntegrationDelivery` (lines 245-260), `ScanJob.scan_run_id` (line 220)
- `quirk/db.py` -- `_ensure_columns` generic migration helper (lines 127-157), `_ADDITIVE_MIGRATIONS` registry (lines 172+)
- `quirk/cli/scheduler_cmd.py` -- `_dispatch_schedule` (lines 110-199), Phase 101/103 after-hook pattern (lines 171-197)
- `quirk/intelligence/scoring.py` -- six-subscore rollup `/ 1.5` (lines 288-291), `SCORE_WEIGHTS` (line 20), `compute_readiness_score` signature (line 119)
- `quirk/intelligence/evidence.py` -- `build_evidence_summary` (line 61), `_as_utc_naive` UTC normalization (line 26)
- `quirk/cbom/builder.py` -- `build_cbom` three-pass architecture (lines 445-end), Pass-1 algo registry dedup (line 461)
- `quirk/dashboard/api/middleware/auth.py` -- `require_auth` Depends(), `X-API-Key` + Bearer dual-header support (lines 34-63)
- `quirk/util/safe_exc.py` -- `safe_str()` secret-scrubbing exception formatter
- `quirk/util/url_allowlist.py` -- `validate_external_url()` SSRF guard
- `run_scan.py` -- subcommand dispatch pattern (lines 381-514), `scan_run_id` assignment (line 913), `session_start` (line 1515)
- `.planning/HORIZON.md` -- v5.4 scope definition and Windows constraint (lines 93-113)

---

*Architecture research for: QU.I.R.K. v5.4 Distributed On-Prem Scanner*
*Researched: 2026-05-25*
