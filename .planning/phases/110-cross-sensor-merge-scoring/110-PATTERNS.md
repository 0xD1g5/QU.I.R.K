# Phase 110: Cross-Sensor Merge & Scoring - Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 6 (3 new, 3 modified)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/merge/scan.py` (NEW) | service | CRUD + batch | `quirk/dashboard/api/routes/scan.py` (union query + scoring pipeline) | role-match |
| `quirk/merge/__init__.py` (NEW) | config | — | any `quirk/*/\__init\__.py` | exact |
| `quirk/cbom/builder.py` (MODIFIED) | service | transform | self (minimal surgical change to 4 bom_ref sites) | exact |
| `quirk/cli/sensor_cmd.py` (MODIFIED) | controller | request-response | self (existing enroll/push/export-results subparsers) | exact |
| `quirk/models.py` (MODIFIED) | model | CRUD | self — `Sensor`, `ScanCheckpoint`, `IntegrationDelivery` table classes | exact |
| `tests/test_merge_scan.py` (NEW) | test | — | `tests/test_dar_k8s_scoring.py`, `tests/test_sensor_schema.py` | role-match |
| `tests/test_merge_cli.py` (NEW) | test | — | `tests/test_sensor_cmd.py`, `tests/test_console_cmd.py` | role-match |
| `tests/test_cbom_builder.py` (MODIFIED — new test cases) | test | — | self (existing sensor_id + backward-compat test patterns already sketched in RESEARCH.md) | exact |

---

## Pattern Assignments

---

### `quirk/merge/__init__.py` (NEW — empty package marker)

**Analog:** Any `quirk/*/\__init\__.py`

**Pattern:** Empty file. The project uses plain `__init__.py` with no auto-imports for new subpackages. Do not re-export from here.

---

### `quirk/merge/scan.py` (NEW — standalone callable service)

**Analogs:**
1. `quirk/dashboard/api/routes/scan.py` — union query pattern (SESSION_BRACKET, `func.max`, endpoint window)
2. `tests/test_dar_k8s_scoring.py` — `build_evidence_summary()` + `compute_readiness_score()` call chain
3. `quirk/cli/console_cmd.py` — `_default_db_path()` + `init_db()` + `Session()` pattern for CLI callables

**Imports pattern** (copy from `quirk/dashboard/api/routes/scan.py` L1-20 + `tests/test_dar_k8s_scoring.py` L1-13):
```python
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.cbom.builder import build_cbom
from quirk.models import CryptoEndpoint, Sensor
```

**SESSION_BRACKET constant** — import or redefine from `quirk/dashboard/api/routes/scan.py` L84:
```python
# quirk/dashboard/api/routes/scan.py L84
SESSION_BRACKET = timedelta(minutes=5)
```
Either `from quirk.dashboard.api.routes.scan import SESSION_BRACKET` or redefine locally as the same constant. Redefining locally avoids a dashboard-layer import inside a service module.

**Union query pattern** (model from `quirk/dashboard/api/routes/scan.py` L991-1008 — MAX scanned_at anchor):
```python
# From quirk/dashboard/api/routes/scan.py L995-1008
latest_ts = db.query(func.max(CryptoEndpoint.scanned_at)).scalar()
# ...
endpoints: list[CryptoEndpoint] = (
    db.query(CryptoEndpoint)
    .filter(
        CryptoEndpoint.scanned_at >= latest_ts - SESSION_BRACKET,
        CryptoEndpoint.scanned_at <= latest_ts,
    )
    .all()
)
```
For `merge_scan()`, extend this with a subquery join to select the latest-per-sensor_id rows:
```python
# Latest push per non-null sensor_id (RESEARCH.md §Union Query Pattern)
sub = (
    db.query(
        CryptoEndpoint.sensor_id,
        func.max(CryptoEndpoint.scanned_at).label("max_ts"),
    )
    .filter(CryptoEndpoint.sensor_id.isnot(None))
    .group_by(CryptoEndpoint.sensor_id)
    .subquery()
)
sensor_eps = (
    db.query(CryptoEndpoint)
    .join(sub, (CryptoEndpoint.sensor_id == sub.c.sensor_id)
               & (CryptoEndpoint.scanned_at == sub.c.max_ts))
    .all()
)
# Local (NULL sensor_id) rows via SESSION_BRACKET window
latest_local_ts = (
    db.query(func.max(CryptoEndpoint.scanned_at))
    .filter(CryptoEndpoint.sensor_id.is_(None))
    .scalar()
)
```

**Option A scoring pipeline** (copy call chain from `tests/test_dar_k8s_scoring.py` L38-44 + RESEARCH.md §Code Examples):
```python
# tests/test_dar_k8s_scoring.py L38-39 — canonical two-step
summary = build_evidence_summary(endpoints)
score_result = compute_readiness_score(summary, profile="balanced")
# score_result keys: "score", "rating", "subscores", "drivers"
```
For `merge_scan()`: pass `findings=None` to `build_evidence_summary()` — findings are not persisted in the DB (risk_engine runs at scan time, not ingest time).

**Coverage warning computation** (RESEARCH.md §Coverage Warning Computation):
```python
# Read Sensor rows — analog: quirk/models.py L269-288
sensors = db.query(Sensor).all()
overdue = []
for s in sensors:
    cadence = timedelta(minutes=s.expected_cadence_minutes)
    if s.last_push_at is None:
        overdue.append(s.sensor_id)
    elif now > s.last_push_at + 2 * cadence:
        overdue.append(s.sensor_id)
# null when all current; dict when any overdue
```
Use `Sensor.last_push_at` (NOT `CryptoEndpoint.scanned_at`) — see RESEARCH.md Pitfall 5.

**MergeRun persistence** — follow the `session.merge(ep)` + `session.commit()` idiom from `run_scan.py` L2162-2168:
```python
# run_scan.py L2161-2168
with get_session(cfg.output.db_path) as session:
    for ep in endpoints:
        session.merge(ep)
    session.commit()
```
For merged CryptoEndpoint rows: write with `scanned_at = merge_ts` (makes dashboard see a new session via MAX). For the `MergeRun` record: `session.add(MergeRun(...))` + `session.commit()`.

**DB session context manager** (copy from `quirk/cli/console_cmd.py` L169-197):
```python
# quirk/cli/console_cmd.py L169-197
from quirk.dashboard.api.deps import _default_db_path
from quirk.db import init_db
db_path = _default_db_path()
engine = init_db(db_path)
Session = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False,
)
with Session() as db:
    ...
```
Or use `get_session(db_path)` context manager from `quirk/db.py` L426-452 (already handles commit/rollback/close).

---

### `quirk/cbom/builder.py` (MODIFIED — 4 bom_ref sites + new helper)

**Analog:** self — surgical modification only. All 4 target lines verified in source.

**New helper to add near `_emit_coverage_note` at builder.py ~L426:**
```python
# Place after _emit_coverage_note (builder.py ~L438) — before build_cbom
def _sensor_prefix(ep) -> str:
    """Return 'sensor_id:' prefix for bom_ref when ep has a non-null sensor_id.

    NULL sensor_id (implicit local sensor, backward-compat path) returns ''.
    """
    sid = getattr(ep, "sensor_id", None)
    return f"{sid}:" if sid else ""
```

**Pass 2 cert bom_ref — builder.py L697** (CURRENT line, verbatim):
```python
cert_bom_ref = f"crypto/certificate/{ep.host}:{ep.port}"
```
Change to:
```python
cert_bom_ref = f"crypto/certificate/{_sensor_prefix(ep)}{ep.host}:{ep.port}"
```

**Pass 2b TLS surrogate index lookup — builder.py L758** (MUST stay in sync with L697):
```python
bom_ref_val = f"crypto/certificate/{ep.host}:{ep.port}"
```
Change to:
```python
bom_ref_val = f"crypto/certificate/{_sensor_prefix(ep)}{ep.host}:{ep.port}"
```
Context: this is the lookup key for `_tls_surrogate_index` (builder.py L750-762). The lookup must use the same formula as L697 or CODE_SIGNING cross-source dedup breaks silently.

**Pass 3 SSH protocol bom_ref — builder.py L844** (CURRENT line, verbatim):
```python
proto_bom_ref = f"crypto/protocol/ssh/{ep.host}:{ep.port}"
```
Change to:
```python
proto_bom_ref = f"crypto/protocol/ssh/{_sensor_prefix(ep)}{ep.host}:{ep.port}"
```

**Pass 3 TLS protocol bom_ref — builder.py L897** (CURRENT line, verbatim):
```python
proto_bom_ref = f"crypto/protocol/tls/{ep.host}:{ep.port}"
```
Change to:
```python
proto_bom_ref = f"crypto/protocol/tls/{_sensor_prefix(ep)}{ep.host}:{ep.port}"
```

**Do NOT change:** builder.py L797 `bom_ref_val = f"crypto/certificate/codesign/{ep.host}:{ep.port}"` — CODE_SIGNING codesign/ fallback fires only when fp is None; no cross-segment CODE_SIGNING scenario exists in v5.4 scope.

---

### `quirk/cli/sensor_cmd.py` (MODIFIED — add `merge` subcommand)

**Analog:** self — existing `enroll`, `push`, `export-results` subparser registration and dispatch block (sensor_cmd.py L84-129).

**Subparser registration pattern** (copy from sensor_cmd.py L84-117):
```python
# sensor_cmd.py L84-117 — existing registration pattern
enroll_p = sub.add_parser("enroll", help="Enroll sensor against a console")
enroll_p.add_argument("console_url", ...)
enroll_p.add_argument("--segment", required=True, ...)
# ...
push_p = sub.add_parser("push", help="Run local scan and push results to console")
push_p.add_argument("--config", default=None, ...)
```
Add after `export_p` block, before `args = parser.parse_args(argv)`:
```python
merge_p = sub.add_parser("merge", help="Merge all sensor data and produce unified CBOM + score")
merge_p.add_argument("--db", default=None, help="Override console DB path")
merge_p.add_argument("--stale-days", type=int, default=30, dest="stale_days")
```

**Dispatch block pattern** (copy from sensor_cmd.py L119-129):
```python
# sensor_cmd.py L119-129 — existing dispatch
args = parser.parse_args(argv)
try:
    if args.action == "enroll":
        _cmd_enroll(args)
    elif args.action == "push":
        _cmd_push(args)
    elif args.action == "export-results":
        _cmd_export_results(args)
except KeyboardInterrupt:
    print("\nInterrupted.", file=sys.stderr)
    sys.exit(130)
```
Add `elif args.action == "merge": _cmd_merge(args)` inside the `try` block.

**`_cmd_merge` implementation pattern** — follow `_cmd_enroll`/`_cmd_push` pattern of lazy imports + `_default_db_path()` + `sys.exit(0)`:
```python
def _cmd_merge(args: argparse.Namespace) -> None:
    from quirk.merge.scan import merge_scan
    from quirk.dashboard.api.deps import _default_db_path
    from quirk.db import init_db, get_session

    db_path = args.db or _default_db_path()
    init_db(db_path)
    with get_session(db_path) as db:
        result = merge_scan(db, stale_days=args.stale_days)

    print(f"Merged scan_id: {result['scan_id']}")
    print(f"Score: {result['score']} ({result['rating']})")
    if result.get("coverage_warning"):
        w = result["coverage_warning"]
        print(f"WARNING: {w['reason']}")
        for sid in w["missing_sensors"]:
            print(f"  - {sid}")
    sys.exit(0)
```
Note: `sys` is already imported at module level in sensor_cmd.py (L37). Do not re-import.

---

### `quirk/models.py` (MODIFIED — new `MergeRun` table class)

**Analog:** `Sensor` (quirk/models.py L269-288), `IntegrationDelivery` table class, and the `_ensure_integration_deliveries_table` + `init_db` call-site pattern in `quirk/db.py`.

**New table class pattern** (model from `Sensor` class, quirk/models.py L269-288):
```python
class MergeRun(Base):
    """Merged scan result record (Phase 110 — MERGE-05).

    One row per merge_scan() execution. coverage_warning_json is NULL when
    all enrolled sensors are current, else a JSON object with missing_sensors
    and reason. Phase 111 dashboard reads this table to display coverage banner.

    No relationship() declarations — project uses plain Column style exclusively.
    """
    __tablename__ = "merge_runs"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    scan_id               = Column(String(64), nullable=False, index=True)   # ISO merge timestamp
    merged_at             = Column(DateTime,   nullable=False)
    endpoint_count        = Column(Integer,    nullable=False, default=0)
    sensor_count          = Column(Integer,    nullable=False, default=0)
    score                 = Column(Integer,    nullable=True)
    coverage_warning_json = Column(Text,       nullable=True)  # JSON or NULL
```
Place after the `SensorPush` class (models.py L335) — keeping all Phase 107/110 distributed models together.

**`_ensure_merge_runs_table` in `quirk/db.py`** — follow `_ensure_integration_deliveries_table` at db.py L365-373:
```python
def _ensure_merge_runs_table(engine) -> None:
    """Phase 110 MERGE-05: create merge_runs table if absent (idempotent).

    MergeRun is registered on Base.metadata via import of quirk.models.
    Uses Base.metadata.create_all with checkfirst=True — same pattern as
    _ensure_integration_deliveries_table. New table only — not new columns.
    """
    Base.metadata.create_all(engine, checkfirst=True)
```
Then add `_ensure_merge_runs_table(engine)` to `init_db()` after the existing `_ensure_integration_deliveries_table(engine)` call (db.py ~L410).

---

### `tests/test_merge_scan.py` (NEW — unit tests for MERGE-01/02/04/05)

**Analogs:**
1. `tests/test_dar_k8s_scoring.py` L1-29 — import pattern + `CryptoEndpoint(**overrides)` factory helper + `build_evidence_summary` + `compute_readiness_score` call chain
2. `tests/test_sensor_schema.py` L464-510 — scoring stability test pattern (mock evidence dict, compare before/after)

**Imports pattern** (copy from `tests/test_dar_k8s_scoring.py` L1-13):
```python
from __future__ import annotations
from datetime import datetime, timedelta, timezone

import pytest

from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.models import CryptoEndpoint
```

**CryptoEndpoint factory pattern** (copy from `tests/test_cbom_builder.py` L25-38):
```python
def _tls_endpoint(**overrides):
    defaults = dict(
        host="example.com", port=443, protocol=None,
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=example.com", cert_issuer="CN=Example CA",
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)
```
For sensor-aware tests: add `sensor_id="sensor-a"` or `sensor_id=None` to overrides.

**Option A test pattern** (RESEARCH.md §Option A test structure):
```python
def test_option_a_score_not_averaged():
    eps_a = [_tls_endpoint(host="10.0.1.1", sensor_id="s1")]
    eps_b = [_tls_endpoint(host="10.0.2.1", sensor_id="s2")]
    union = eps_a + eps_b
    evidence = build_evidence_summary(union)
    expected_score = compute_readiness_score(evidence)["score"]
    # merge_scan() must call exactly once over full union
    assert result["score"] == expected_score
```

**Coverage warning test pattern** (RESEARCH.md §Coverage Warning Computation):
Use `unittest.mock` or `pytest` fixtures to inject a mock `db` session returning `Sensor` rows with controlled `last_push_at` and `expected_cadence_minutes` values.

---

### `tests/test_cbom_builder.py` (MODIFIED — add MERGE-03 test cases)

**Analog:** self — existing test factory helpers `_tls_endpoint` (L25-38), `_certificate_components` helper (L131-141). Add new test functions after existing certificate tests.

**MERGE-03 test pattern** (RESEARCH.md §MERGE-03 regression test structure):
```python
from quirk.cbom.builder import build_cbom
from quirk.models import CryptoEndpoint
from cyclonedx.model.crypto import CryptoAssetType

def test_two_sensors_same_ip_two_components():
    ep_a = _tls_endpoint(host="10.0.0.5", port=443, sensor_id="sensor-a", segment="prod-east")
    ep_b = _tls_endpoint(host="10.0.0.5", port=443, sensor_id="sensor-b", segment="prod-west")
    bom = build_cbom([ep_a, ep_b])
    cert_refs = [
        getattr(c.bom_ref, "value", None)
        for c in bom.components
        if c.crypto_properties and c.crypto_properties.asset_type == CryptoAssetType.CERTIFICATE
    ]
    assert "crypto/certificate/sensor-a:10.0.0.5:443" in cert_refs
    assert "crypto/certificate/sensor-b:10.0.0.5:443" in cert_refs
    assert len(cert_refs) == 2  # NOT collapsed

def test_null_sensor_id_backward_compat():
    ep_local = _tls_endpoint(host="10.0.0.5", port=443, sensor_id=None)
    bom_local = build_cbom([ep_local])
    cert_refs = [
        getattr(c.bom_ref, "value", None)
        for c in bom_local.components
        if c.crypto_properties and c.crypto_properties.asset_type == CryptoAssetType.CERTIFICATE
    ]
    assert cert_refs == ["crypto/certificate/10.0.0.5:443"]  # byte-identical to pre-110 format
```

---

## Shared Patterns

### DB Session Pattern
**Source:** `quirk/db.py` L426-452 (`get_session` context manager) + `quirk/cli/console_cmd.py` L167-197
**Apply to:** `quirk/merge/scan.py`, `_cmd_merge` in `sensor_cmd.py`
```python
# get_session: commit on success, rollback on exception, close always
from quirk.db import get_session
with get_session(db_path) as db:
    # db is an expire_on_commit=False Session
    ...
```

### Default DB Path Resolution
**Source:** `quirk/dashboard/api/deps.py` L12-35
**Apply to:** `_cmd_merge` in `sensor_cmd.py`
```python
from quirk.dashboard.api.deps import _default_db_path
db_path = args.db or _default_db_path()
```
Priority: `QUIRK_DB_PATH` env var → `./quirk-output/quirk.db` canonical → legacy fallback.

### New Table Registration Pattern
**Source:** `quirk/db.py` L365-373 (`_ensure_integration_deliveries_table`) + L410 (call site in `init_db`)
**Apply to:** `MergeRun` table in `quirk/models.py` + corresponding `_ensure_merge_runs_table` + `init_db` call
```python
# db.py _ensure_* pattern — new table, not new columns → create_all, not ALTER TABLE
def _ensure_merge_runs_table(engine) -> None:
    Base.metadata.create_all(engine, checkfirst=True)
# Then in init_db(), after existing _ensure_* calls:
_ensure_merge_runs_table(engine)
```

### Lazy Imports in CLI Handlers
**Source:** `quirk/cli/sensor_cmd.py` L454-462 (`_cmd_push`) and L572-602 (`_cmd_export_results`)
**Apply to:** `_cmd_merge` in `sensor_cmd.py`
```python
# Pattern: top-level imports for stdlib/project-constants only; heavy deps inside handler
def _cmd_merge(args: argparse.Namespace) -> None:
    from quirk.merge.scan import merge_scan          # lazy import
    from quirk.dashboard.api.deps import _default_db_path  # lazy import
    from quirk.db import init_db, get_session        # lazy import
    ...
```

### sys.exit(0) on Success
**Source:** `quirk/cli/sensor_cmd.py` L220 (enroll), L564 (push), L678 (export-results)
**Apply to:** `_cmd_merge` — always terminate with `sys.exit(0)` on success.

### ORM Plain Column Style (No relationship())
**Source:** `quirk/models.py` L278 docstring for `Sensor` class: "No relationship() declarations — project uses plain Column style exclusively."
**Apply to:** `MergeRun` model — no `relationship()` declarations.

---

## No Analog Found

All files have direct analogs in the codebase. No greenfield patterns required.

| File | Role | Data Flow | Notes |
|------|------|-----------|-------|
| `quirk/merge/scan.py` | service | batch | Closest existing batch callable is the scan orchestration in `run_scan.py`, but that is a full CLI entrypoint. `merge_scan()` is a standalone callable seam — pattern is assembled from the scan.py query + scoring test patterns, not copied wholesale from a single source. |

---

## Metadata

**Analog search scope:** `quirk/`, `tests/`, `run_scan.py`
**Key files read:** `quirk/cli/sensor_cmd.py`, `quirk/cbom/builder.py` (targeted sections), `quirk/models.py`, `quirk/db.py`, `quirk/dashboard/api/routes/scan.py` (targeted sections), `quirk/dashboard/api/deps.py`, `quirk/cli/console_cmd.py` (targeted sections), `tests/test_cbom_builder.py`, `tests/test_dar_k8s_scoring.py`, `tests/test_sensor_schema.py` (targeted section)
**Pattern extraction date:** 2026-05-25
