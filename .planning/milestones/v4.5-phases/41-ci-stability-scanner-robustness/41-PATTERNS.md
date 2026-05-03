# Phase 41: CI Stability & Scanner Robustness - Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** 8 new/modified files requiring pattern guidance
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/test_skip_registry.py` | test / meta-gate | event-driven (collection hook) | `tests/test_hygiene.py` | role-match |
| `tests/test_scan_robustness.py` | test | request-response (unit, mocked) | `tests/test_broker_db_schema.py` | role-match |
| `tests/conftest.py` (modify) | test config / fixture | — | `tests/conftest.py` itself | exact (modify in place) |
| `quirk/config.py` (modify) | config / model | CRUD (TOML parse) | `quirk/config.py` itself — `IntelligenceCfg` / `config_from_dict` backward-compat block | exact (modify in place) |
| `quirk/models.py` (modify) | model | CRUD | `quirk/models.py` itself | exact (modify in place) |
| `quirk/db.py` (modify) | migration utility | CRUD | `quirk/db.py` — `_ensure_v43_columns` / `_ensure_email_columns` | exact (modify in place) |
| `quirk/intelligence/trends.py` (modify) | service / analytics | CRUD | `quirk/intelligence/trends.py` itself — lines 232–259 | exact (modify in place) |
| `run_scan.py` (modify — D-08, D-12, D-14) | orchestrator | request-response | `run_scan.py` itself — `_phase_timer` context manager + TLS/SSH try/finally blocks | exact (modify in place) |
| `pyproject.toml` (modify) | config | — | `pyproject.toml` itself | exact (modify in place) |
| `quantum-chaos-enterprise-lab/lab.sh` (modify — D-18) | shell utility | — | `lab.sh` itself — lines 97-108 | exact (modify in place) |

---

## Pattern Assignments

### `tests/test_skip_registry.py` (new — CI gate meta-test, CI-01, D-02, D-03)

**Analog:** `tests/test_hygiene.py`

The hygiene test file uses `ast` + `pathlib` to walk the source tree and assert structural invariants. This is the exact mechanism for the skip CI gate.

**Imports pattern** (`tests/test_hygiene.py` lines 1-20):
```python
import ast
import inspect
import pathlib
import re
import unittest

import run_scan

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
```

**Core AST-walk pattern** (`tests/test_hygiene.py` lines 39-62):
```python
def test_no_imports_from_quirk_connectors(self) -> None:
    violations = []
    quirk_dir = PROJECT_ROOT / "quirk"
    for py_file in quirk_dir.rglob("*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("quirk.connectors"):
                    violations.append((str(py_file), module))
    self.assertEqual(violations, [], ...)
```

**Adaptation for skip gate:** Replace the import-walk body with a search for `pytest.skip(`, `pytest.mark.skipif(`, and `pytest.importorskip(` call nodes. For each occurrence, check whether `(str(py_file), node.lineno)` appears in the `ALLOWED_SKIPS` registry. Collect unregistered occurrences and assert the list is empty.

**Registry data structure** (define in same file or imported from `tests/conftest.py`):
```python
# Each entry: (file_relative_to_tests_dir, line_number, category, reason)
ALLOWED_SKIPS = [
    ("test_broker_scanner_kafka.py",    12,  "optional_extra", "broker_scanner is [motion]; D-05"),
    ("test_broker_scanner_rabbitmq.py", 13,  "optional_extra", "broker_scanner is [motion]; D-05"),
    ("test_broker_scanner_redis.py",    13,  "optional_extra", "broker_scanner is [motion]; D-05"),
    ("test_chaos_storage.py",           41,  "live_infra",     "Requires Docker + MinIO"),
    ("test_chaos_storage.py",           67,  "live_infra",     "Requires Docker + MinIO"),
    ("test_dnssec_scanner.py",          475, "live_infra",     "Requires BIND9 chaos lab"),
    ("test_saml_scanner.py",            366, "live_infra",     "Requires SimpleSAMLphp chaos lab"),
    ("test_kerberos_scanner.py",        360, "live_infra",     "Requires Samba DC chaos lab"),
    ("test_cbom_motion_golden.py",      189, "live_infra",     "Fixture regen guard"),
]
```

---

### `tests/test_scan_robustness.py` (new — ROBUST-01, ROBUST-02, ROBUST-03)

**Analog:** `tests/test_broker_db_schema.py` (unit test structure) + `tests/test_email_scanner.py` (mock + soft-import pattern)

**Imports pattern** (`tests/test_broker_db_schema.py` lines 1-12):
```python
import tempfile
import os
import pytest
from sqlalchemy import text, inspect as sa_inspect
from quirk.db import init_db, _ensure_broker_columns
```

**Unit test with mock pattern** (`tests/test_cloud_connectors.py` lines 40-46):
```python
with patch("quirk.scanner.aws_connector.boto3.Session", return_value=mock_session):
    endpoints = scan_aws_targets(region="us-east-1", profile=None)
    assert len(endpoints) >= 1
```

**Pattern for ROBUST-01 (missing extra advisory to stderr):**
```python
import sys
import io
import pytest
from unittest.mock import patch, MagicMock

def test_missing_extra_advisory(capsys):
    """ROBUST-01: missing optional extra emits advisory line to stderr."""
    # Patch the optional import flag to False, then call the scanner
    with patch("quirk.scanner.kerberos_scanner.IMPACKET_AVAILABLE", False):
        from quirk.scanner.kerberos_scanner import scan_kerberos_targets
        scan_kerberos_targets(targets=["example.com"])
    captured = capsys.readouterr()
    assert "[advisory]" in captured.err
    assert "pip install quirk[" in captured.err
```

**Pattern for ROBUST-03 (BaseException wrapper — D-14):**
```python
def test_exception_captured(monkeypatch):
    """ROBUST-03: unexpected exception from scanner is caught; scan continues."""
    import run_scan
    # monkeypatch a scanner to raise RuntimeError
    monkeypatch.setattr(
        "quirk.scanner.jwt_scanner.scan_jwt_targets",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    # run_scan phase should not propagate; scan_errors should contain category="exception"
    ...
```

---

### `tests/conftest.py` — Skip registry + stale-skip deletions (D-02, D-04)

**Modify in place** — see RESEARCH for exact lines.

Key changes:
1. Line 111: Delete `pytest.skip("quirk.dashboard not yet implemented")` — replace entire `except ImportError:` block with `pytest.fail("quirk.dashboard import failed unexpectedly")` or use `pytest.importorskip` at module level in dashboard test files.
2. Add `ALLOWED_SKIPS` registry constant (or import it from `tests/skip_registry.py`).
3. No other structural changes to the fixture.

**Existing fixture pattern to preserve** (`tests/conftest.py` lines 75-109):
```python
@pytest.fixture
def dashboard_client():
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from quirk.dashboard.api.app import create_app
        from quirk.dashboard.api.deps import get_db
        from quirk.models import Base
        from fastapi.testclient import TestClient
        engine = create_engine(
            "sqlite:///file::memory:?cache=shared&uri=true",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        ...
        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        return TestClient(app)
    except ImportError:
        pytest.skip("quirk.dashboard not yet implemented")  # ← DELETE THIS LINE
```

---

### `quirk/config.py` — `[scan.timeouts]` / `[scan.retry]` sub-table (D-06, D-07)

**Modify in place** — add `TimeoutsCfg` and `RetryCfg` dataclasses, augment `ScanCfg`, update `config_from_dict`.

**Existing sub-object loading pattern** (`quirk/config.py` lines 156-215 — `config_from_dict`):

The `IntelligenceCfg` block (lines 157-188) is the canonical backward-compatible loader pattern: it reads from a dict, applies legacy key fallbacks, normalizes values, then constructs the dataclass. Copy this exact structure for `TimeoutsCfg`.

```python
# Existing pattern — copy for TimeoutsCfg loader:
intel_raw = raw.get("intelligence", {}) or {}
# ... legacy key fallbacks ...
intelligence_cfg = IntelligenceCfg(
    intelligence_version=str(intel_raw.get("intelligence_version", "4.2.0") or "4.2.0"),
    profile=profile,
    calibration_overrides=overrides,
)
```

**New dataclass pattern** (model on existing `ScanCfg` at lines 17-34):
```python
@dataclass
class TimeoutsCfg:
    default_seconds: int = 5
    fingerprint_seconds: int = 4
    tls_seconds: int = 6
    ssh_seconds: int = 6
    jwt_seconds: int = 10
    container_seconds: int = 120
    source_seconds: int = 300
    dnssec_seconds: int = 10
    saml_seconds: int = 10
    kerberos_seconds: int = 10
    vault_seconds: int = 10
    db_connect_seconds: int = 5
    broker_seconds: int = 10
    email_seconds: int = 10

@dataclass
class RetryCfg:
    retry_count: int = 0
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 5.0
```

**Deprecation-alias property pattern** (from RESEARCH.md — D-07):
```python
@property
def timeout_seconds(self):
    import warnings
    warnings.warn(
        "cfg.scan.timeout_seconds is deprecated; use cfg.scan.timeouts.default_seconds",
        DeprecationWarning, stacklevel=2,
    )
    return self.timeouts.default_seconds
```

**Backward-compat loader pattern for sub-table** (model on `intel_raw` loading, lines 159-189):
```python
# In config_from_dict — add before AppConfig construction:
timeouts_raw = (raw.get("scan") or {}).get("timeouts", {}) or {}
retry_raw = (raw.get("scan") or {}).get("retry", {}) or {}
timeouts_cfg = TimeoutsCfg(**{k: v for k, v in timeouts_raw.items()
                              if k in {f.name for f in dataclasses.fields(TimeoutsCfg)}})
retry_cfg = RetryCfg(**{k: v for k, v in retry_raw.items()
                        if k in {f.name for f in dataclasses.fields(RetryCfg)}})
```

---

### `quirk/models.py` — Add `scan_error_category` column (D-11, D-15)

**Modify in place** — single line addition after `scan_error` at line 35.

**Existing column declaration pattern** (`quirk/models.py` lines 35-36):
```python
scan_error = Column(Text, nullable=True)
tls_blocker_reason = Column(String(64), nullable=True)
```

**New column follows same pattern:**
```python
scan_error = Column(Text, nullable=True)
scan_error_category = Column(String(32), nullable=True)   # ← ADD: missing_extra|timeout|exception|config
```

---

### `quirk/db.py` — Migration helper for `scan_error_category` (D-11)

**Modify in place** — add a new `_ensure_phase41_columns` function following the exact pattern of all existing `_ensure_*_columns` helpers.

**Canonical migration helper pattern** (`quirk/db.py` lines 87-106 — `_ensure_v43_columns`):
```python
_V43_COLUMN_DDLS = {
    "dat_scan_json": "TEXT",
    "severity": "VARCHAR(16)",
}

def _ensure_v43_columns(engine) -> None:
    """Add v4.3 data-at-rest columns ... if absent."""
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col, col_type in _V43_COLUMN_DDLS.items():
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} {col_type}"))
        conn.commit()
```

**New helper follows this exactly:**
```python
_PHASE41_COLUMN_DDLS = {
    "scan_error_category": "VARCHAR(32)",
}

def _ensure_phase41_columns(engine) -> None:
    """Add Phase 41 scan_error_category column if absent (idempotent)."""
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col, col_type in _PHASE41_COLUMN_DDLS.items():
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} {col_type}"))
        conn.commit()
```

Then call `_ensure_phase41_columns(engine)` inside `init_db()` after the last existing `_ensure_*` call.

---

### `quirk/intelligence/trends.py` — Category-aware error counting (D-15)

**Modify in place** — change the `cur_err` / `prev_err` counting at lines 256-258.

**Current pattern** (`quirk/intelligence/trends.py` lines 256-259):
```python
cur_err = sum(1 for ep in current_eps if ep.scan_error is not None)
prev_err = sum(1 for ep in previous_eps if ep.scan_error is not None)
scan_errors_new_count = max(0, cur_err - prev_err)
scan_errors_resolved_count = max(0, prev_err - cur_err)
```

**New pattern — exclude `missing_extra` from alarm counts:**
```python
cur_err = sum(
    1 for ep in current_eps
    if ep.scan_error is not None
    and getattr(ep, "scan_error_category", None) != "missing_extra"
)
prev_err = sum(
    1 for ep in previous_eps
    if ep.scan_error is not None
    and getattr(ep, "scan_error_category", None) != "missing_extra"
)
scan_errors_new_count = max(0, cur_err - prev_err)
scan_errors_resolved_count = max(0, prev_err - cur_err)
```

The `getattr(..., None)` guard preserves backward compat with DB rows that predate the column.

---

### `run_scan.py` — D-08 (no mutation), D-12 (stderr advisory), D-14 (BaseException wrapper)

**Modify in place** — three distinct change areas.

**D-08: Remove TLS/SSH mutation pattern** (`run_scan.py` lines 413-459 — current BACK-45 pattern):
```python
# CURRENT (to be removed):
base_timeout = cfg.scan.timeout_seconds
base_conc = cfg.scan.concurrency
cfg.scan.timeout_seconds = tls_timeout          # ← DELETE
cfg.scan.concurrency = tls_conc                 # ← DELETE
tls_endpoints = []
try:
    with _phase_timer(run_stats, "tls_scanning"):
        if tls_targets:
            tls_endpoints = scan_tls_targets(cfg, tls_targets, ...)
finally:
    cfg.scan.timeout_seconds = base_timeout     # ← DELETE entire finally block
    cfg.scan.concurrency = base_conc
```

**D-08 replacement — read-only, pass explicit kwargs:**
```python
# NEW (D-08 compliant):
tls_timeout = cfg.scan.timeouts.tls_seconds
tls_conc = cfg.scan.tls_concurrency            # tls_concurrency stays on ScanCfg
with _phase_timer(run_stats, "tls_scanning"):
    if tls_targets:
        tls_endpoints = scan_tls_targets(
            cfg, tls_targets,
            timeout=tls_timeout,
            concurrency=tls_conc,
            logger=logger,
            progress_cb=None,
        )
```

**D-12: Stderr advisory pattern** (model on `quirk/scanner/kerberos_scanner.py` lines 246-256):
```python
# Existing pattern in kerberos_scanner.py:
if not IMPACKET_AVAILABLE:
    import sys
    print(
        "\n[QUIRK] Kerberos scanning requires the identity extras:\n"
        "    pip install quirk[identity]\n",
        file=sys.stderr,
    )
    return []
```

**D-12 new canonical format** (D-12 spec):
```python
# In run_scan.py, before each optional scanner call — or inside each scanner:
import sys
print(
    f"[advisory] scanner=<name> extra=<group> not installed"
    f" — run `pip install quirk[<group>]` to enable",
    file=sys.stderr,
)
ep = CryptoEndpoint(
    host="<scanner-name>", port=0, protocol="ADVISORY",
    scan_error=f"optional extra [<group>] not installed",
    scan_error_category="missing_extra",
)
```

**D-14: `try/except BaseException` wrapper pattern** (new pattern; model on `_phase_timer` context manager at lines 79-87 and existing scanner call sites):
```python
# Wrap each _phase_timer block or add at run_scan.py call site level:
try:
    with _phase_timer(run_stats, "jwt_scanning"):
        if cfg.connectors.enable_jwt and cfg.connectors.jwt_targets:
            jwt_endpoints = scan_jwt_targets(...)
except (KeyboardInterrupt, SystemExit):
    raise
except BaseException as exc:
    logger.error(f"jwt_scanning: unhandled exception: {exc!r}")
    ep = CryptoEndpoint(
        host="jwt_scanner", port=0, protocol="ERROR",
        scan_error=str(exc),
        scan_error_category="exception",
    )
    # append ep to the appropriate endpoints list or a top-level scan_errors list
```

**D-18: lab.sh down/reset arms** — modify in place, lines 97-108.

Current (lines 97-108):
```bash
  down)
    echo "🧯 Stopping lab: project=${PROJECT_NAME}"
    compose down
    echo "✅ Lab stopped."
    ;;
  reset)
    echo "♻️ Resetting lab (down -v + up -d): project=${PROJECT_NAME}"
    compose down -v
    compose up -d
```

Replacement:
```bash
  down)
    echo "🧯 Stopping lab: project=${PROJECT_NAME}"
    compose --profile "*" down --remove-orphans
    echo "✅ Lab stopped."
    ;;
  reset)
    echo "♻️ Resetting lab (down -v + up -d): project=${PROJECT_NAME}"
    compose --profile "*" down -v --remove-orphans
    compose up -d
```

---

### `pyproject.toml` — Add `[tool.pytest.ini_options]` (D-16, CI-03)

**Modify in place** — append after `[tool.setuptools.package-data]` block (currently the last section, ending at line 74).

**No existing pytest ini block** — this is a new section. Pattern from RESEARCH.md:
```toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m not slow')",
    "integration: marks tests requiring live infrastructure",
]
addopts = "-m 'not slow'"
```

---

## Shared Patterns

### Optional-Extra ImportError Guard
**Source:** `quirk/scanner/broker_scanner.py` lines 58-74 (SSLYZE + kafka + redis guards)
**Apply to:** Any new code that conditionally imports an optional extra

```python
try:
    from kafka.admin import KafkaAdminClient
    KAFKA_AVAILABLE = True
except ImportError:
    KafkaAdminClient = None  # type: ignore[assignment]
    KAFKA_AVAILABLE = False
```

Pattern: set a `_AVAILABLE` boolean, stub out the type to `None` with type-ignore comment, gate usage on the boolean.

### DB Migration Helper
**Source:** `quirk/db.py` lines 87-106 (`_ensure_v43_columns`)
**Apply to:** `_ensure_phase41_columns` in `quirk/db.py`

Three invariants:
1. `_SAFE_COL_RE.match(col)` guard before every `ALTER TABLE`
2. `sa_inspect(engine).get_columns(...)` check before adding (idempotent)
3. `conn.commit()` inside the `with engine.connect()` block

### Backward-Compatible Config Loading
**Source:** `quirk/config.py` lines 157-215 (`config_from_dict` — `IntelligenceCfg` block)
**Apply to:** `TimeoutsCfg` / `RetryCfg` loading in `config_from_dict`

Pattern: `raw.get("section", {}) or {}` — double guard against None from YAML null values.

### AST-Walk Structural Assertion (meta-test)
**Source:** `tests/test_hygiene.py` lines 39-62
**Apply to:** `tests/test_skip_registry.py` CI gate

Pattern: `pathlib.rglob("*.py")` + `ast.parse` + `ast.walk` + collect violations into a list + `assertEqual(violations, [])`.

### Stderr Warning with Logger Fallback
**Source:** `quirk/scanner/kerberos_scanner.py` lines 246-256
**Apply to:** All missing-extra advisory emitters (D-12)

Pattern: `print(..., file=sys.stderr)` for the user-visible advisory, then `logger.warning(...)` for the structured log. Both fire before `return []`.

---

## Modify-Only Files (No Analog Research Needed)

| File | Change | Research Reference |
|------|--------|--------------------|
| `tests/test_cloud_connectors.py` | Delete 9× `@skipif(not _HAS_GCP_MODULE)` decorators | RESEARCH lines 71-79 |
| `tests/test_email_scanner.py` | Delete `_skip_scanner` pattern + 16 decorator usages | RESEARCH lines 84, 99 |
| `tests/test_broker_db_schema.py` | Delete `pytest.skip(...)` at line 70 (or entire `test_migration_preserves_existing_rows` if column is now always in Base.metadata) | RESEARCH line 80 |
| `tests/test_version.py` | Convert `pytest.skip(...)` at lines 32, 34 to `pytest.fail(...)` | RESEARCH lines 91-92 |
| Slow-test files (7 test files) | Add `@pytest.mark.slow` to identified tests | RESEARCH lines 221-229 |
| 21 scanner files (`quirk/scanner/*.py`) | Read timeout from `cfg.scan.timeouts.<name>_seconds` (read-only) | RESEARCH scanner table lines 121-143 |
| `run_scan.py` line 743 | Change `profile=cfg.scan.profile` to `profile=scan_profile` (bug fix) | RESEARCH line 145 |
| `docs/configuration.md` | Add `[scan.timeouts]` / `[scan.retry]` sub-table docs + upper-bound formula | RESEARCH lines 283-358 |

---

## No Analog Found

No files in Phase 41 are entirely without analog. All new files have closely matched structural predecessors in the codebase.

---

## Metadata

**Analog search scope:** `quirk/`, `tests/`, `run_scan.py`, `pyproject.toml`, `quantum-chaos-enterprise-lab/lab.sh`
**Files scanned:** 12 analog files read in full or targeted sections
**Pattern extraction date:** 2026-04-29
