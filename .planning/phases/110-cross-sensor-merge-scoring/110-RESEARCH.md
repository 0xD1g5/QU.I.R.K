# Phase 110: Cross-Sensor Merge & Scoring — Research

**Researched:** 2026-05-25
**Domain:** Cross-sensor merge pipeline, CBOM identity keying, scoring engine integration, coverage warning
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **(D-01) Option A scoring:** merged score = union re-run through `compute_readiness_score()` unchanged. NEVER weighted average or weakest-link.
- **(D-03) Component identity:** CBOM Pass-1 bom_ref must include `sensor_id`. NULL `sensor_id` keeps current ref (backward-compat).
- **(D-06) Manual merge:** `quirk sensor merge` is operator-invoked; `merge_scan()` is a standalone callable seam.
- **(D-14) Coverage & staleness:** overdue = `now > last_push_at + 2×cadence`; never-pushed enrolled sensor is also overdue; `coverage_warning` is null when all current; partial coverage always scored but always flagged; stale after 30 days.
- **Union definition:** latest push per sensor_id (max `scanned_at`) + NULL `sensor_id` local rows.
- **`merge_scan(db, ...) -> result`** standalone callable; `quirk sensor merge` is thin wrapper.
- **Scope:** all enrolled sensors by default; `--segment` filter deferred.
- **CBOM minimal builder change:** `crypto/certificate/{sensor_id}:{host}:{port}` when `sensor_id` present; NULL keeps `crypto/certificate/{host}:{port}`. NOT a fork of the engine.
- **`coverage_warning` shape:** `null` when all current, else `{missing_sensors: [...], reason: <str>}`.
- **Merged scan_id:** ISO-timestamp at merge execution time.
- **`scanned_at` preservation:** endpoints keep sensor-local `scanned_at`; only the result envelope carries merge timestamp.

### Claude's Discretion

- Exact `merge_scan()` parameter list and return type; how merged result rows are written.
- Precise SQL/ORM query for "latest push per sensor_id".
- `coverage_warning.reason` wording and per-sensor overdue detail.

### Deferred Ideas (OUT OF SCOPE)

- `--segment` subset merge filter.
- Automatic merge trigger / poller (v5.5, D-06).
- Physical two-segment chaos-lab reproduction (Phase 112, LAB-02).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MERGE-01 | Merge endpoints from N sensors via canonical `build_evidence_summary()` → `build_cbom()` pipeline; engines not forked or modified | Engine signatures verified; minimal builder.py identity-key change satisfies this without forking |
| MERGE-02 | Merged score via `compute_readiness_score()` over union (Option A); never averaging sub-results | Signature confirmed: takes `evidence: Mapping[str, Any]`; accepts evidence dict from `build_evidence_summary()` |
| MERGE-03 | CBOM emits two distinct components when two sensors report same RFC1918 `host:port`; proven by regression test | Exact line in builder.py L697 identified; minimal change specified; backward-compat path documented |
| MERGE-04 | Overdue/offline sensor → non-null `coverage_warning` in score JSON; partial data never silently complete | `Sensor.last_push_at + expected_cadence_minutes` columns confirmed; overdue formula verified |
| MERGE-05 | `quirk sensor merge` CLI produces unified CBOM + score as normal scan result; new merged scan_id; sensor-local `scanned_at` preserved | `run_sensor()` dispatch pattern verified; persistence path via `session.merge(ep)` identified |
</phase_requirements>

---

## Summary

Phase 110 delivers the cross-sensor merge by adding a `merge` subcommand to the existing `quirk/cli/sensor_cmd.py` sensor parser and a standalone `merge_scan()` callable in a new `quirk/merge/scan.py` module. The implementation has three moving parts: (1) a union query that assembles the latest CryptoEndpoint rows per sensor_id plus NULL-sensor local rows, (2) a minimal surgical change to `quirk/cbom/builder.py` Pass-2 to include `sensor_id` in cert and protocol bom_refs when present, and (3) coverage-warning computation from `Sensor.last_push_at` + `expected_cadence_minutes` rows before invoking the unchanged engine chain.

The MERGE-01-vs-D-03 tension is resolved in favour of the **minimal builder.py change** (see §CBOM Identity Resolution below). The pre-namespace alternative (mutating host fields before passing to `build_cbom`) would violate MERGE-01's spirit more severely — it silently corrupts the `host` and `port` fields that all other engine logic reads, and it would not survive the "engine unmodified" intent. A two-line surgical change to the `cert_bom_ref` derivation at builder.py L697 and the analogous proto_bom_ref derivations threads `sensor_id` into the identity key without touching any logic path.

The score JSON (the `intelligence-*.json` file written by `write_reports`) is consumed by the dashboard through the in-memory `compute_readiness_score()` return dict — the dashboard re-computes it from CryptoEndpoint rows each request, rather than reading a stored JSON. The merged scan result therefore persists as a set of CryptoEndpoint rows with a common `scanned_at` = merge ISO timestamp, and the dashboard picks it up naturally via `MAX(scanned_at)`. The `coverage_warning` field is a new top-level key in the `merge_scan()` return dict; the planner must decide how to surface it (CLI print + optional DB column on a new MergeScan table, or only CLI print).

**Primary recommendation:** Implement `merge_scan()` in a new `quirk/merge/scan.py` module; add `merge` to the `sensor_cmd.py` subparser; make the two-line builder.py bom_ref change; add a `coverage_warning` column on a new `merge_runs` table for Phase 111 consumption.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Union assembly (latest-per-sensor query) | Console / Python service | SQLite | DB query returns endpoint rows; Python assembles union |
| Coverage warning computation | Console / Python service | SQLite (Sensor rows) | Reads `last_push_at + expected_cadence_minutes` from sensors table |
| Option A scoring | Console / Python service (intelligence layer) | — | `compute_readiness_score(evidence)` is pure Python, no DB |
| CBOM generation | Console / Python service (CBOM layer) | — | `build_cbom(endpoints)` is pure Python |
| CLI dispatch | CLI / run_scan.py intercept | sensor_cmd.py | Follows existing `quirk sensor` intercept at run_scan.py L509 |
| Result persistence | SQLite | CryptoEndpoint table | Merged endpoints written as normal CryptoEndpoint rows with merge scan_id |
| coverage_warning persistence | SQLite (new merge_runs table) or in-memory only | — | Phase 111 dashboard needs to read it; new table is safest |

---

## CRITICAL: MERGE-01-vs-D-03 Resolution

### The Tension

MERGE-01 says "engines not forked or modified." D-03 says "CBOM component identity must include sensor_id." Today, `build_cbom()` in `builder.py` derives cert identity as `crypto/certificate/{ep.host}:{ep.port}` (L697) — no `sensor_id`. When two sensors push `10.0.0.5:443`, both rows have the same `host:port` and Pass-2 produces one component.

### All bom_ref derivations that key on host:port (builder.py)

**Pass 2 — Certificate components (L697):**

```python
# CURRENT (builder.py L697)
cert_bom_ref = f"crypto/certificate/{ep.host}:{ep.port}"

# PROPOSED minimal change
sensor_pfx = f"{ep.sensor_id}:" if getattr(ep, "sensor_id", None) else ""
cert_bom_ref = f"crypto/certificate/{sensor_pfx}{ep.host}:{ep.port}"
```

This is the **primary collision site** confirmed in CONTEXT.md and in the code. [VERIFIED: direct source read]

**Pass 2b — CODE_SIGNING cert fallback (L797):**

```python
# CURRENT (builder.py L797)
bom_ref_val = f"crypto/certificate/codesign/{ep.host}:{ep.port}"
```

This fallback fires only when `fp` (SHA-256 fingerprint) is None — i.e., the scanner did not set a fingerprint. CODE_SIGNING endpoints are local-scanner-only (no distributed push carries CODE_SIGNING protocol rows yet). NULL `sensor_id` will fire the existing path. This bom_ref **does not need to change in Phase 110** — there is no cross-segment CODE_SIGNING scenario, and the fingerprint-based primary path already provides a strong identity. [ASSUMED — no cross-segment code-sign use case in v5.4 scope]

**Pass 2b — TLS surrogate index lookup (L758):**

```python
bom_ref_val = f"crypto/certificate/{ep.host}:{ep.port}"
```

This builds the lookup key for the `_tls_surrogate_index`. When the cert_bom_ref derivation at L697 changes, this lookup must use the **same formula** — otherwise cross-source TLS-wins dedup breaks. This line at L758 must change alongside L697. [VERIFIED: direct source read]

**Pass 3 — TLS protocol components (L897):**

```python
# CURRENT (builder.py L897)
proto_bom_ref = f"crypto/protocol/tls/{ep.host}:{ep.port}"
```

Same collision risk: two sensors at `10.0.0.5:443` produce one TLS protocol component. **This must also change.** [VERIFIED: direct source read]

**Pass 3 — SSH protocol components (L844):**

```python
# CURRENT (builder.py L844)
proto_bom_ref = f"crypto/protocol/ssh/{ep.host}:{ep.port}"
```

Same: SSH on the same RFC1918 host across two segments collides. **This must also change.** [VERIFIED: direct source read]

### Complete set of lines requiring the sensor_id prefix

| Pass | Line (approx) | Current ref | Change needed |
|------|---------------|-------------|---------------|
| Pass 2 cert | L697 | `crypto/certificate/{host}:{port}` | Prefix `{sensor_id}:` when non-null |
| Pass 2b surrogate lookup | L758 | `crypto/certificate/{host}:{port}` | Same prefix — must stay in sync with L697 |
| Pass 3 TLS protocol | L897 | `crypto/protocol/tls/{host}:{port}` | Prefix `{sensor_id}:` when non-null |
| Pass 3 SSH protocol | L844 | `crypto/protocol/ssh/{ep.host}:{ep.port}` | Prefix `{sensor_id}:` when non-null |

**CODE_SIGNING codesign/ fallback (L797):** no change needed in Phase 110.

### Proposed shared helper

A single helper function isolates the prefix logic and prevents future drift:

```python
def _sensor_prefix(ep) -> str:
    """Return '{sensor_id}:' when the endpoint has a non-null sensor_id, else ''."""
    sid = getattr(ep, "sensor_id", None)
    return f"{sid}:" if sid else ""
```

Then each derivation becomes:

```python
# L697 (cert)
cert_bom_ref = f"crypto/certificate/{_sensor_prefix(ep)}{ep.host}:{ep.port}"

# L758 (surrogate lookup — must match L697)
bom_ref_val = f"crypto/certificate/{_sensor_prefix(ep)}{ep.host}:{ep.port}"

# L844 (SSH protocol)
proto_bom_ref = f"crypto/protocol/ssh/{_sensor_prefix(ep)}{ep.host}:{ep.port}"

# L897 (TLS protocol)
proto_bom_ref = f"crypto/protocol/tls/{_sensor_prefix(ep)}{ep.host}:{ep.port}"
```

### Backward-compatibility guarantee

When `sensor_id` is NULL (all pre-v5.4 scans), `_sensor_prefix(ep)` returns `""`, and the bom_ref is byte-identical to the current format. Existing single-host CBOM output is unchanged. [VERIFIED: direct source logic]

### Pre-namespace alternative (rejected)

The alternative — pre-mutating `ep.host` to `f"{sensor_id}:{host}"` before passing the list to `build_cbom()` — would:
1. Corrupt the `host` field that `build_evidence_summary()` reads for counting (scanned_at, cert observation, etc.)
2. Produce malformed host values in `CertificateProperties.subject_name` (passed through)
3. Require the caller to un-mangle after CBOM generation — error-prone
4. Still technically touch the engine's input shape, just upstream instead of inside

The minimal builder.py change is **strictly safer and simpler**. It threads `sensor_id` into the identity key only, at the identity-derivation site, and leaves every other field untouched.

**Recommendation: use the minimal builder.py change with `_sensor_prefix()` helper.** [ASSUMED: design recommendation based on code analysis]

---

## Standard Stack

No new external packages in this phase. All reused from existing codebase.

### Reused Engines (do NOT modify logic — only the identity key derivation)

| Component | Location | Input | Output |
|-----------|----------|-------|--------|
| `build_evidence_summary` | `quirk/intelligence/evidence.py` | `endpoints: Iterable[Any]`, `findings: Optional[Iterable[Mapping]]` | `Dict[str, Any]` (evidence dict) |
| `compute_readiness_score` | `quirk/intelligence/scoring.py` | `evidence: Mapping[str, Any]`, `profile`, `weights` | `Dict[str, Any]` — keys: `score`, `rating`, `subscores`, `drivers` |
| `build_cbom` | `quirk/cbom/builder.py` | `endpoints: list[CryptoEndpoint]` | `Bom` |
| `Sensor` model | `quirk/models.py` | — | `sensor_id`, `last_push_at`, `expected_cadence_minutes` columns |
| `CryptoEndpoint` | `quirk/models.py` | — | `sensor_id`, `segment`, `scanned_at`, all scan fields |

---

## Architecture Patterns

### System Architecture Diagram

```
quirk sensor merge
        |
        v
   merge_scan(db, ...)
        |
   [1] Build union query
        |--- latest CryptoEndpoint per sensor_id (max scanned_at)
        |--- + NULL sensor_id rows (local scan)
        |
   [2] Check coverage
        |--- Query sensors table for all enrolled sensors
        |--- Compute overdue: now > last_push_at + 2×cadence
        |--- Build coverage_warning (null or {missing_sensors, reason})
        |
   [3] Option A scoring pipeline (UNCHANGED engines)
        |--- build_evidence_summary(union_endpoints, union_findings)
        |--- compute_readiness_score(evidence)
        |--- build_cbom(union_endpoints)  [with sensor_prefix patch]
        |
   [4] Persist merged result
        |--- Write CryptoEndpoint rows with scanned_at = merge_ts
        |    (per-endpoint scanned_at preserved from sensor-local values)
        |--- Write merge_runs row with coverage_warning
        |
   [5] CLI print
        |--- merged scan_id + score + coverage_warning summary
```

### Recommended Project Structure (new file)

```
quirk/
├── merge/
│   ├── __init__.py
│   └── scan.py          # merge_scan() standalone callable
```

### `merge_scan()` Signature (recommended, discretion area)

```python
def merge_scan(
    db,                          # SQLAlchemy Session or db_path str
    *,
    now: datetime | None = None, # injectable for tests (default: datetime.utcnow())
    stale_days: int = 30,        # D-14 operator-overridable
) -> dict:
    """
    Returns:
        {
            "scan_id": "<ISO timestamp>",
            "score": <int>,
            "rating": <str>,
            "subscores": {...},
            "drivers": [...],
            "coverage_warning": null | {"missing_sensors": [...], "reason": <str>},
            "endpoint_count": <int>,
        }
    """
```

### Union Query Pattern (discretion area)

The union of "latest push per sensor_id" + "NULL sensor_id rows" in SQLAlchemy:

```python
from sqlalchemy import func

# Step 1: latest scanned_at per non-null sensor_id
sub = (
    db.query(
        CryptoEndpoint.sensor_id,
        func.max(CryptoEndpoint.scanned_at).label("max_ts"),
    )
    .filter(CryptoEndpoint.sensor_id.isnot(None))
    .group_by(CryptoEndpoint.sensor_id)
    .subquery()
)

# Step 2: sensor rows from latest push
sensor_eps = (
    db.query(CryptoEndpoint)
    .join(sub, (CryptoEndpoint.sensor_id == sub.c.sensor_id)
               & (CryptoEndpoint.scanned_at == sub.c.max_ts))
    .all()
)

# Step 3: local (NULL sensor_id) rows — use same SESSION_BRACKET as scan.py L1004
latest_local_ts = (
    db.query(func.max(CryptoEndpoint.scanned_at))
    .filter(CryptoEndpoint.sensor_id.is_(None))
    .scalar()
)
if latest_local_ts:
    local_eps = (
        db.query(CryptoEndpoint)
        .filter(
            CryptoEndpoint.sensor_id.is_(None),
            CryptoEndpoint.scanned_at >= latest_local_ts - SESSION_BRACKET,
            CryptoEndpoint.scanned_at <= latest_local_ts,
        )
        .all()
    )
else:
    local_eps = []

union_endpoints = sensor_eps + local_eps
```

**SESSION_BRACKET** is already defined in `quirk/dashboard/api/routes/scan.py` as `timedelta(minutes=5)`. Either import it or redefine locally in `merge/scan.py`. [VERIFIED: direct source read]

### Coverage Warning Computation

```python
from datetime import datetime, timedelta

def _compute_coverage_warning(db, now: datetime) -> dict | None:
    sensors = db.query(Sensor).all()
    overdue = []
    for s in sensors:
        cadence = timedelta(minutes=s.expected_cadence_minutes)
        if s.last_push_at is None:
            # Never pushed — always overdue
            overdue.append(s.sensor_id)
        elif now > s.last_push_at + 2 * cadence:
            overdue.append(s.sensor_id)
    if not overdue:
        return None
    return {
        "missing_sensors": overdue,
        "reason": f"{len(overdue)} enrolled sensor(s) overdue or never pushed",
    }
```

The `reason` wording is discretion-area. Inclusion of per-sensor cadence detail (last_push_at, overdue by X minutes) is also discretion-area. [ASSUMED: recommended implementation]

### Merged Result Persistence

The dashboard's `get_latest_scan` endpoint anchors on `MAX(scanned_at)` and loads all endpoints within a `SESSION_BRACKET` window. To make the merged result visible as a normal scan, write all merged CryptoEndpoint rows with `scanned_at = merge_ts` (the ISO timestamp of the merge execution). The **sensor-local `scanned_at`** must be preserved — store it as a separate field, or (simpler) keep it as-is and only set the outer scan envelope timestamp to `merge_ts`.

**Key insight:** The dashboard does not read a separate "scan result" table. It queries `CryptoEndpoint.scanned_at` directly and groups by truncated second. Writing merged endpoints with `scanned_at = merge_ts` is sufficient.

**Option (recommended):** Write a new `merge_runs` table (one row per merge execution) to persist `coverage_warning`, `scan_id`, and `endpoint_count` so Phase 111 dashboard can read it without re-computing overdue status. This is a new additive table and must go through `_ADDITIVE_MIGRATIONS`.

```python
class MergeRun(Base):
    __tablename__ = "merge_runs"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    scan_id         = Column(String(64), nullable=False, index=True)  # ISO merge timestamp
    merged_at       = Column(DateTime, nullable=False)
    endpoint_count  = Column(Integer, nullable=False, default=0)
    sensor_count    = Column(Integer, nullable=False, default=0)
    score           = Column(Integer, nullable=True)
    coverage_warning_json = Column(Text, nullable=True)  # JSON or NULL
```

[ASSUMED: recommended design for Phase 111 consumption]

### `quirk sensor merge` CLI Pattern

The existing `run_sensor()` function in `sensor_cmd.py` dispatches via `args.action`. Add `merge` to the `sub.add_parser` set and the dispatch block:

```python
# In sensor_cmd.py run_sensor():
merge_p = sub.add_parser("merge", help="Merge all sensor data and produce unified CBOM + score")
merge_p.add_argument("--db", default=None, help="Override console DB path")
merge_p.add_argument("--stale-days", type=int, default=30, dest="stale_days")

# In dispatch:
elif args.action == "merge":
    _cmd_merge(args)
```

```python
def _cmd_merge(args: argparse.Namespace) -> None:
    from quirk.merge.scan import merge_scan
    from quirk.db import get_session, init_db, _default_db_path
    db_path = args.db or _default_db_path()
    init_db(db_path)
    with get_session(db_path) as db:
        result = merge_scan(db, stale_days=args.stale_days)
    # Print results
    print(f"Merged scan_id: {result['scan_id']}")
    print(f"Score: {result['score']} ({result['rating']})")
    if result.get("coverage_warning"):
        w = result["coverage_warning"]
        print(f"WARNING: {w['reason']}")
        for sid in w["missing_sensors"]:
            print(f"  - {sid}")
    sys.exit(0)
```

[ASSUMED: recommended implementation pattern]

### Per-Segment Scores (context-only breakdown)

Architecture doc §7 notes that `per_segment_scores` is added "for context only, never as a scoring input." The planner may choose to compute this as a dict of `{sensor_id: score_dict}` by running `compute_readiness_score(build_evidence_summary(segment_eps))` for each sensor's endpoints, then returning it alongside the unified score in `merge_scan()`'s return dict. This is Claude's Discretion territory.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-segment CBOM merge | Custom CycloneDX merge tool or sbommerge | Re-run `build_cbom(union_endpoints)` | Architecture §9 explicitly forbids sbommerge/CycloneDX CLI merge |
| Scoring across segments | Weighted average or weakest-link | `compute_readiness_score(build_evidence_summary(union))` | Math is wrong with pre-scored sub-results (ratio denominators) |
| Component identity uniqueness | Pre-mutate host fields | `_sensor_prefix()` in bom_ref derivation only | Mutating host corrupts evidence pipeline inputs |
| DB union query | Python-side manual dedup after fetching all rows | SQLAlchemy subquery join on max(scanned_at) per sensor_id | Avoids loading all historical endpoints |

---

## Common Pitfalls

### Pitfall 1: scanned_at Rewrite

**What goes wrong:** `merge_scan()` sets all endpoint `scanned_at` to the merge execution time, losing per-sensor scan timestamps.
**Why it happens:** Convenience — one timestamp for all rows.
**How to avoid:** Keep sensor-local `scanned_at` on each row. Only the `merge_runs.merged_at` / `scan_id` carries the merge timestamp. The dashboard anchors on `MAX(scanned_at)` which will be the merge_ts — that is acceptable because merged endpoints are written with `scanned_at = merge_ts` (this IS the new scan session). The per-sensor original `scanned_at` is preserved as a separate `sensor_scanned_at` column on MergeRun, or by reading it from the source rows before writing.
**Warning signs:** `coverage_warning` check compares `now` vs endpoint `scanned_at` instead of `Sensor.last_push_at`.

**Clarification on CONTEXT.md "scanned_at preservation":** The constraint is that merge does NOT rewrite the `CryptoEndpoint.scanned_at` fields of the *source* rows read from the ingestion table. The merged output rows (written to `crypto_endpoints` with the merge `scan_id`) carry `scanned_at = merge_ts` — this is what makes the dashboard see them as a new session. The source rows in the ingestion table remain untouched.

### Pitfall 2: D-01 Averaging

**What goes wrong:** Computing per-segment `compute_readiness_score()` results and averaging or min-ing them.
**Why it happens:** Intuition that "average of averages = total average."
**How to avoid:** Call `compute_readiness_score(build_evidence_summary(ALL_endpoints))` exactly once over the full union. Per-segment scores are computed for context only, never used as inputs.
**Warning signs:** Any division by `len(segments)` in the score path.

### Pitfall 3: Pass-2 Surrogate Index Out of Sync

**What goes wrong:** builder.py L697 (cert bom_ref) is updated to include sensor_id prefix, but L758 (TLS surrogate index lookup) is not updated — the lookup key no longer matches the component's bom_ref, silently breaking CODE_SIGNING cross-source dedup.
**Why it happens:** Two separate code paths derive the same key independently.
**How to avoid:** Use the `_sensor_prefix()` helper in BOTH L697 and L758. The regression test for MERGE-03 will catch this only if it also tests `CODE_SIGNING` cross-source dedup with a non-null sensor_id.
**Warning signs:** CODE_SIGNING test fails; TLS cert components gain spurious `quirk:code-signing-eku` properties after the builder change.

### Pitfall 4: No Enrolled Sensors

**What goes wrong:** `merge_scan()` is called when the console has no enrolled sensors and no local scan rows — union is empty — and `compute_readiness_score(build_evidence_summary([]))` produces a score of 100 (empty denominator).
**How to avoid:** Guard: if `len(union_endpoints) == 0`, return a structured error or a score-zero result with a `coverage_warning` noting "no data."

### Pitfall 5: Overdue Threshold Uses Wrong Field

**What goes wrong:** Overdue detection reads `CryptoEndpoint.scanned_at` (the endpoint's scan time) instead of `Sensor.last_push_at` (the push receipt time).
**Why it happens:** `last_push_at` is updated by Phase 109 `_ingest_envelope` on accepted push; `scanned_at` is the actual scan time and may be minutes earlier.
**How to avoid:** Always read `Sensor.last_push_at` for coverage warning. The `scanned_at` of CryptoEndpoint rows is the actual measurement time, not the push time.

---

## Code Examples

### build_evidence_summary signature
[VERIFIED: direct source read `quirk/intelligence/evidence.py` L61-67]

```python
def build_evidence_summary(
    endpoints: Iterable[Any],          # list of CryptoEndpoint ORM objects
    findings: Optional[Iterable[Mapping[str, Any]]] = None,  # list of finding dicts
    *,
    expiring_days: int = 30,
    reference_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
```

**For merge:** `findings` is optional. In a cross-sensor merge context, `findings` would be the union of all `risk_engine` findings across all sensors — but risk_engine findings are not currently stored in the DB (they are computed at scan time and written to `findings-*.json`). For MERGE-01/MERGE-02, passing `findings=None` is valid; `build_evidence_summary()` computes all evidence from the endpoint objects directly.

### compute_readiness_score signature
[VERIFIED: direct source read `quirk/intelligence/scoring.py` L119-123]

```python
def compute_readiness_score(
    evidence: Mapping[str, Any],       # output of build_evidence_summary()
    *,
    profile: str | None = None,        # "strict" | "balanced" | "lenient"
    weights: Mapping[str, float] | None = None,
) -> Dict[str, Any]:
    # Returns: {"score": int, "rating": str, "subscores": {...}, "drivers": [...]}
```

### build_cbom signature
[VERIFIED: direct source read `quirk/cbom/builder.py` L445]

```python
def build_cbom(endpoints: list[CryptoEndpoint]) -> Bom:
```

Takes a plain `list[CryptoEndpoint]`. Returns a `Bom` object. No findings parameter — CBOM is built purely from endpoint fields.

### Minimal builder.py change (L697 + L758 + L844 + L897)
[VERIFIED: direct source read `quirk/cbom/builder.py`]

```python
# New helper function (add near the other helpers, e.g. after _emit_coverage_note at L426):
def _sensor_prefix(ep) -> str:
    """Return 'sensor_id:' prefix for bom_ref when ep has a non-null sensor_id.

    NULL sensor_id (implicit local sensor, backward-compat path) returns ''.
    """
    sid = getattr(ep, "sensor_id", None)
    return f"{sid}:" if sid else ""


# Pass 2 cert bom_ref (L697) — change from:
cert_bom_ref = f"crypto/certificate/{ep.host}:{ep.port}"
# to:
cert_bom_ref = f"crypto/certificate/{_sensor_prefix(ep)}{ep.host}:{ep.port}"


# Pass 2b TLS surrogate index lookup (L758) — change from:
bom_ref_val = f"crypto/certificate/{ep.host}:{ep.port}"
# to:
bom_ref_val = f"crypto/certificate/{_sensor_prefix(ep)}{ep.host}:{ep.port}"


# Pass 3 SSH protocol bom_ref (L844) — change from:
proto_bom_ref = f"crypto/protocol/ssh/{ep.host}:{ep.port}"
# to:
proto_bom_ref = f"crypto/protocol/ssh/{_sensor_prefix(ep)}{ep.host}:{ep.port}"


# Pass 3 TLS protocol bom_ref (L897) — change from:
proto_bom_ref = f"crypto/protocol/tls/{ep.host}:{ep.port}"
# to:
proto_bom_ref = f"crypto/protocol/tls/{_sensor_prefix(ep)}{ep.host}:{ep.port}"
```

---

## How Scan Results Are Persisted and Read

### Normal scan result persistence (run_scan.py)
[VERIFIED: direct source read `run_scan.py` + `quirk/reports/writer.py`]

1. CryptoEndpoint rows are written to SQLite via `session.merge(ep)` during scan stages.
2. `scan_run_id` = `run_stats["started_utc"]` (ISO timestamp string, set at scan start).
3. `write_reports()` is called at the end; it calls `build_evidence_summary()` + `compute_readiness_score()` + `build_cbom()` and writes output files to `cfg.output.directory`.
4. The dashboard's `get_latest_scan()` route reads endpoints by querying `MAX(CryptoEndpoint.scanned_at)` and loading all rows in a `SESSION_BRACKET` (5 min) window.
5. The dashboard re-computes the score in-flight — it does not read the `intelligence-*.json` file.

### scan_id format

`scan_id` is the ISO timestamp string of `scanned_at` — e.g. `"2026-05-25 16:31:00"` (space separator via `isoformat(sep=" ")`). For the merge, the `scan_id` will be the merge execution time formatted the same way.

### Where coverage_warning attaches

The `ScanLatestResponse` schema (`quirk/dashboard/api/schemas.py` L207) does not currently have a `coverage_warning` field. Phase 111 will add it. For Phase 110, `coverage_warning` lives in:
1. The `merge_scan()` return dict (consumed by the CLI and by Phase 111).
2. The `merge_runs.coverage_warning_json` column (for Phase 111 dashboard to read).
3. The CLI stdout print.

**The `ScanLatestResponse` schema is NOT modified in Phase 110** — that is Phase 111's work.

---

## Test Conventions

### Existing test patterns for CBOM and scoring
[VERIFIED: direct source read `tests/test_cbom_builder.py`]

Tests use `CryptoEndpoint(**overrides)` instantiation directly (not from DB). Factory helpers:

```python
def _tls_endpoint(**overrides):
    defaults = dict(
        host="example.com", port=443, protocol=None,
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        ...
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)
```

For sensor_id tests, add `sensor_id="uuid-a"` to the overrides.

### MERGE-03 regression test structure

```python
# Test: same RFC1918 host:port in two segments yields TWO distinct CBOM components

ep_a = CryptoEndpoint(
    host="10.0.0.5", port=443, protocol="TLS",
    sensor_id="sensor-a", segment="prod-east",
    cert_pubkey_alg="RSA", cert_pubkey_size=2048,
    cert_subject="CN=app", cert_issuer="CN=ca",
    tls_version="TLSv1.3",
    cipher_suite="TLS_AES_256_GCM_SHA384",
)
ep_b = CryptoEndpoint(
    host="10.0.0.5", port=443, protocol="TLS",
    sensor_id="sensor-b", segment="prod-west",
    cert_pubkey_alg="RSA", cert_pubkey_size=2048,
    cert_subject="CN=app", cert_issuer="CN=ca",
    tls_version="TLSv1.3",
    cipher_suite="TLS_AES_256_GCM_SHA384",
)

bom = build_cbom([ep_a, ep_b])
cert_refs = [
    getattr(c.bom_ref, "value", None)
    for c in bom.components
    if c.crypto_properties and c.crypto_properties.asset_type == CryptoAssetType.CERTIFICATE
]
assert "crypto/certificate/sensor-a:10.0.0.5:443" in cert_refs
assert "crypto/certificate/sensor-b:10.0.0.5:443" in cert_refs
assert len(cert_refs) == 2  # NOT collapsed


# Test: NULL sensor_id keeps backward-compat ref
ep_local = CryptoEndpoint(
    host="10.0.0.5", port=443, protocol="TLS",
    sensor_id=None,  # implicit local sensor
    cert_pubkey_alg="RSA", ...
)
bom_local = build_cbom([ep_local])
cert_refs_local = [getattr(c.bom_ref, "value", None) for c in bom_local.components
                   if c.crypto_properties and c.crypto_properties.asset_type == CryptoAssetType.CERTIFICATE]
assert cert_refs_local == ["crypto/certificate/10.0.0.5:443"]  # byte-identical to current
```

### Option A test structure

```python
# Test: merged score = compute_readiness_score over union, not average of sub-scores
# Feed 2 sensor segments, verify score = single call over union

eps_a = [CryptoEndpoint(host="10.0.1.1", port=443, protocol="TLS", sensor_id="s1", ...)]
eps_b = [CryptoEndpoint(host="10.0.2.1", port=443, protocol="TLS", sensor_id="s2", ...)]
union = eps_a + eps_b

evidence = build_evidence_summary(union)
expected_score = compute_readiness_score(evidence)["score"]

# merge_scan internal path must produce the same result
assert result["score"] == expected_score
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_merge_scan.py tests/test_cbom_builder.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MERGE-01 | Engines not forked; union fed to existing chain | unit | `pytest tests/test_merge_scan.py::test_option_a_uses_existing_engines -x` | Wave 0 |
| MERGE-02 | Score = union through compute_readiness_score, not average | unit | `pytest tests/test_merge_scan.py::test_option_a_score_not_averaged -x` | Wave 0 |
| MERGE-03 | Two sensors, same RFC1918 host:port → two CBOM components | unit | `pytest tests/test_cbom_builder.py::test_two_sensors_same_ip_two_components -x` | Wave 0 |
| MERGE-03 | NULL sensor_id → backward-compat bom_ref | unit | `pytest tests/test_cbom_builder.py::test_null_sensor_id_backward_compat -x` | Wave 0 |
| MERGE-04 | Overdue sensor → non-null coverage_warning | unit | `pytest tests/test_merge_scan.py::test_coverage_warning_overdue_sensor -x` | Wave 0 |
| MERGE-04 | All sensors current → null coverage_warning | unit | `pytest tests/test_merge_scan.py::test_coverage_warning_null_when_current -x` | Wave 0 |
| MERGE-05 | CLI outputs scan_id + score + warning | integration | `pytest tests/test_merge_cli.py -x` | Wave 0 |

### Wave 0 Gaps

- [ ] `tests/test_merge_scan.py` — covers MERGE-01, MERGE-02, MERGE-04, MERGE-05 unit cases
- [ ] `tests/test_merge_cli.py` — covers MERGE-05 CLI dispatch
- [ ] New test cases in `tests/test_cbom_builder.py` — covers MERGE-03 (two-segment regression + NULL backward-compat)
- [ ] `quirk/merge/__init__.py` + `quirk/merge/scan.py` — must exist before test collection passes

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | merge is console-local; no new auth surface |
| V3 Session Management | no | — |
| V4 Access Control | no | CLI-local; console DB access |
| V5 Input Validation | yes | sensor_id values from DB (already validated at ingest); coverage_warning reason is hardcoded string literals (T-88-03 pattern) |
| V6 Cryptography | no | merge does not handle secrets |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| coverage_warning.reason leaking internal sensor IDs | Information Disclosure | Sensor IDs are operator-generated UUIDs; already in DB; disclosure to console operator is acceptable. No raw exceptions in reason string. |
| Empty union producing score=100 | Tampering / false-positive posture | Guard: zero-endpoint union returns a score result with explicit `coverage_warning` noting no data. |
| `_sensor_prefix()` using unvalidated sensor_id in bom_ref | Injection | sensor_id is stored as-is from enrollment (validated as UUID4 at Phase 108 enrollment time via `_UUID_RE`). The bom_ref is internal to the CBOM JSON, not rendered to HTML or SQL. Acceptable. |

---

## Environment Availability

All dependencies already installed in the project environment. No new external tools required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| SQLAlchemy | union query | ✓ | existing | — |
| CycloneDX Python library | build_cbom | ✓ | existing | — |
| pytest | test suite | ✓ | existing | — |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CODE_SIGNING codesign/ fallback bom_ref (L797) does not need sensor_id change in Phase 110 — no cross-segment code-sign scenario in v5.4 | CBOM Identity Resolution | If cross-segment CODE_SIGNING is ever pushed, two endpoints with the same host:port but no fingerprint would collapse. Low risk in v5.4 scope. |
| A2 | Recommended `merge_scan()` signature and `merge_runs` table design | Architecture Patterns | If planner prefers a different persistence strategy (e.g., in-memory only for Phase 110), the MergeRun model is unnecessary. Adjust in planning. |
| A3 | `coverage_warning.reason` wording "N enrolled sensor(s) overdue or never pushed" | Coverage Warning | Cosmetic only; risk-free to change. |
| A4 | Per-segment scores breakdown computed for context in merge_scan() return dict | Architecture Patterns | If omitted, Phase 111 cannot show per-segment gauges from the merge result. Plan should specify whether this is included. |
| A5 | `SESSION_BRACKET = timedelta(minutes=5)` from `scan.py` should be reused or re-imported for the local-scan union query | Architecture Patterns | If not reused, local scan cohort window may differ. Safe to redefine locally as a constant. |

---

## Open Questions (RESOLVED)

> Resolution note (2026-05-25): the merged-result persistence path was reconciled with the LOCKED
> MERGE-05 decision during planning. MERGE-05 (preserve per-endpoint `scanned_at`, no rewrite to
> merge time) SUPERSEDES the Architectural-Summary suggestion to write merged `CryptoEndpoint` rows
> with `scanned_at = merge_ts`. Chosen path: `merge_scan()` computes over the union IN PLACE and
> persists the merged result ONLY as a `merge_runs` row (new merged `scan_id`, score JSON,
> `coverage_warning`, CBOM artifact path). **Consequence captured for Phase 111:** the dashboard must
> read `merge_runs` directly — the merged result is NOT surfaced via `MAX(scanned_at)`.

1. **RESOLVED — Where does `build_cbom` get called?** Inside `merge_scan()`, which writes the Bom to a
   file via `write_cbom_files(bom, outdir, stamp)` directly (no full `cfg` needed; importable from
   `quirk.cbom`). The CBOM artifact path is recorded on the `merge_runs` row.

2. **RESOLVED — `findings` parameter for `build_evidence_summary`:** pass `findings=None`. The evidence
   summary computes all scoring signals from endpoint fields alone (`severity`, `scan_error`,
   `cert_pubkey_alg`, etc.); no risk_engine re-run is needed for scoring.

3. **RESOLVED — Does `merge_scan()` need a `cfg` object?** No. It accepts optional
   `profile: str = "balanced"` and `weights: dict | None = None`. CLI `--profile`/`--calibration`
   flags are a follow-up; Phase 110 defaults suffice.

---

## Sources

### Primary (HIGH confidence)

- Direct source read: `quirk/cbom/builder.py` — all bom_ref derivation sites confirmed
- Direct source read: `quirk/intelligence/evidence.py` — `build_evidence_summary` signature + input handling
- Direct source read: `quirk/intelligence/scoring.py` — `compute_readiness_score` signature + return shape
- Direct source read: `quirk/models.py` — `CryptoEndpoint`, `Sensor`, `SensorPush` field set
- Direct source read: `quirk/cli/sensor_cmd.py` — sensor subparser + dispatch pattern
- Direct source read: `quirk/dashboard/api/routes/scan.py` — `get_latest_scan` endpoint, scan_id format, SESSION_BRACKET
- Direct source read: `quirk/dashboard/api/schemas.py` — `ScanLatestResponse` (no coverage_warning field yet)
- Direct source read: `quirk/reports/writer.py` — `write_reports()` flow, where build_cbom/scoring are called
- Direct source read: `tests/test_cbom_builder.py` — test conventions for CryptoEndpoint construction
- Direct source read: `.planning/phases/109-console-ingestion-api/109-02-SUMMARY.md` — `_ingest_envelope` details, `last_push_at` update
- Direct source read: `docs/architecture-distributed.md` — §5 data-model keying, §7 merge pipeline

### Secondary (MEDIUM confidence)

- `.planning/phases/110-cross-sensor-merge-scoring/110-CONTEXT.md` — locked decisions, flagged tension

---

## Metadata

**Confidence breakdown:**
- CBOM bom_ref change scope: HIGH — all four sites verified by direct source read
- Engine signatures: HIGH — verified from source
- Test patterns: HIGH — verified from source
- Persistence strategy (merge_runs table): MEDIUM — recommended design, not yet locked
- CLI merge pattern: HIGH — sensor_cmd.py dispatch pattern verified

**Research date:** 2026-05-25
**Valid until:** 2026-06-25 (30 days — stable codebase)
