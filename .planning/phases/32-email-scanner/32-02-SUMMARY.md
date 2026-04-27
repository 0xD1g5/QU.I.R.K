---
phase: 32-email-scanner
plan: 02
subsystem: database
tags: [email-scanner, db-migration, config, pyproject, sqlite, sqlalchemy, quirk]

requires:
  - phase: 32-email-scanner
    provides: "plan-01 test scaffolding (test_email_scan_json_column_exists)"

provides:
  - "email_scan_json TEXT NULL column on crypto_endpoints (fresh + existing DBs)"
  - "_ensure_email_columns(engine) idempotent migration helper in quirk/db.py"
  - "ConnectorsCfg.enable_email: bool = False in quirk/config.py"
  - "[motion] optional-dependencies group in pyproject.toml"

affects: [32-03-email-scanner-module, 32-05-run-scan-integration, 32-06-risk-engine]

tech-stack:
  added: []
  patterns:
    - "Inspector-first idempotent ALTER TABLE migration helper (_ensure_email_columns)"
    - "v4.4 Data in Motion section in models.py"
    - "ConnectorsCfg field naming: enable_<scanner> pattern extended to email"

key-files:
  created: []
  modified:
    - quirk/models.py
    - quirk/db.py
    - quirk/config.py
    - pyproject.toml
    - tests/test_email_scanner.py

key-decisions:
  - "cfg.connectors.enable_email (NOT cfg.scanners.email_enabled) — matches existing enable_* field convention in ConnectorsCfg"
  - "Test restructured to use _skip_scanner marker rather than module-level importorskip to allow DB-only tests to run before scanner module exists"
  - "Plan acceptance criteria bug (AppConfig() no-arg instantiation) auto-fixed to use ConnectorsCfg() directly"

requirements-completed: [STRUCT-02, STRUCT-03, EMAIL-00]

duration: 18min
completed: 2026-04-27
---

# Phase 32 Plan 02: DB + Config Foundation Summary

**SQLAlchemy `email_scan_json TEXT` column, idempotent ALTER TABLE migration, `ConnectorsCfg.enable_email=False`, and `[motion]` extras group in pyproject.toml — the storage and configuration substrate for Phase 32 email scanner**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-04-27T00:00:00Z
- **Completed:** 2026-04-27
- **Tasks:** 2
- **Files modified:** 5 (quirk/models.py, quirk/db.py, quirk/config.py, pyproject.toml, tests/test_email_scanner.py)

## Accomplishments

- Added `email_scan_json = Column(Text, nullable=True)` to `CryptoEndpoint` under a `# v4.4 Data in Motion fields` section header
- Added `_EMAIL_COLUMNS = ["email_scan_json"]` constant and `_ensure_email_columns(engine)` migration helper to `quirk/db.py`, following the exact inspector-first pattern of `_ensure_identity_columns` and `_ensure_v43_columns`
- `init_db()` now calls `_ensure_email_columns(engine)` after `_ensure_v43_columns(engine)` — fresh DBs get the column via `create_all`, existing DBs get it via idempotent `ALTER TABLE`
- Added `enable_email: bool = False` to `ConnectorsCfg` after `vault_tls_verify` — canonical namespace is `cfg.connectors.enable_email`
- Added `[motion]` group to `[project.optional-dependencies]` in `pyproject.toml` (empty body per Phase 32 scope; Phase 33 will populate)
- Fixed pre-existing bug in `tests/test_email_scanner.py`: `test_email_scan_json_column_exists` was unreachable due to module-level `importorskip` — restructured to `_skip_scanner` marker so DB tests run before the scanner module exists

## Task Commits

1. **TDD RED — test scaffolding** - `3658702` (test: add RED-state test for email_scan_json column and idempotency)
2. **Task 1 GREEN — models.py + db.py** - `f4704d6` (feat: add email_scan_json column to CryptoEndpoint and _ensure_email_columns migration helper)
3. **Task 2 — config.py + pyproject.toml** - `9c55784` (feat: add ConnectorsCfg.enable_email flag and [motion] extras group in pyproject.toml)

## pyproject.toml Diff (STRUCT-03 artifact)

```toml
+motion = [
+    # Phase 32: email scanner — sslyze is a soft import in tls_scanner/email_scanner; no hard dep needed.
+    # Phase 33 will add broker deps (kafka-python, etc.) here.
+]
```

Added after the `db = [...]` group, preserving the chronological/feature grouping convention.

## Idempotency Proof

```
python3 -c "
from quirk.db import init_db
import tempfile, os
with tempfile.TemporaryDirectory() as tmpdir:
    db_path = os.path.join(tmpdir, 'test.db')
    init_db(db_path)   # first call
    init_db(db_path)   # second call — no exception
    print('idempotent OK')
"
# Output: idempotent OK
```

`_ensure_email_columns` uses `sa_inspect(engine).get_columns("crypto_endpoints")` to build the `existing` set before attempting any `ALTER TABLE`. If `email_scan_json` is already present, the loop skips it without error.

## Column Inspector Dump

```
sqlite> .schema crypto_endpoints
...email_scan_json TEXT...

python3 -c "
from quirk.db import init_db
import tempfile, os
from sqlalchemy import inspect
with tempfile.TemporaryDirectory() as tmpdir:
    e = init_db(os.path.join(tmpdir, 'test.db'))
    cols = {c['name'] for c in inspect(e).get_columns('crypto_endpoints')}
    assert 'email_scan_json' in cols
    print('email_scan_json PRESENT')
"
# Output: email_scan_json PRESENT
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed unreachable DB-column test caused by module-level importorskip**
- **Found during:** Task 1 TDD RED setup
- **Issue:** `tests/test_email_scanner.py` used `pytest.importorskip` at module level, which raised `Skipped` during Python import before pytest could collect any tests — including `test_email_scan_json_column_exists` which has no dependency on the scanner module
- **Fix:** Replaced module-level `pytest.importorskip` with a conditional try/except import + `_skip_scanner = pytest.mark.skipif(not _EMAIL_SCANNER_AVAILABLE, ...)` decorator applied individually to scanner-specific tests. The 2 DB-column tests now run unconditionally; the 15 scanner tests skip gracefully until Plan 03 lands
- **Files modified:** tests/test_email_scanner.py
- **Verification:** `pytest tests/test_email_scanner.py --collect-only` collects 18 tests; DB tests run and pass; scanner tests skip
- **Committed in:** 3658702 (RED state commit)

**2. [Rule 1 - Bug] Plan acceptance criteria used `AppConfig()` which requires 6 positional args**
- **Found during:** Task 2 verification
- **Issue:** Plan verify command `AppConfig()` raises `TypeError: AppConfig.__init__() missing 6 required positional arguments`
- **Fix:** Used `ConnectorsCfg()` directly in verification — it has all-default fields and correctly tests `enable_email`
- **Files modified:** None (verification-only adjustment)
- **Verification:** `python3 -c "from quirk.config import ConnectorsCfg; assert ConnectorsCfg().enable_email is False; print('OK')"` exits 0

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes were necessary for correctness. No scope change.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `quirk/models.py`, `quirk/db.py`, `quirk/config.py`, and `pyproject.toml` are the substrate Plans 03 and 05 depend on
- `cfg.connectors.enable_email` is the gate flag; Plans 03/05 should check it before running email scans
- `email_scan_json` column is available for Plan 03 to populate when storing per-host scan summaries
- `[motion]` group in pyproject.toml satisfies STRUCT-02; STRUCT-03 artifact (diff) is captured above

---
*Phase: 32-email-scanner*
*Completed: 2026-04-27*
