# Phase 44: UAT Debt Automation — Pattern Map

**Mapped:** 2026-05-03
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/test_uat_db_integration.py` | test (integration) | request-response | `tests/test_chaos_storage.py` | exact |
| `tests/test_kerberos_scanner.py` | test (integration) | request-response | self (lines 360-382) | exact — extend in place |
| `tests/test_saml_scanner.py` | test (integration) | request-response | self (lines 365-391) | exact — extend in place |
| `tests/test_vault_connector.py` | test (integration) | request-response | `tests/test_chaos_storage.py` | role-match (new live section at end) |
| `tests/test_dashboard_trends.py` | test (integration) | CRUD | `tests/test_identity_surface.py:565-598` + `tests/test_intelligence_trends.py` | exact |
| `tests/skip_registry.py` | config | — | self | extend in place |
| `quirk/dashboard/api/routes/pdf.py` | route handler | request-response | self | bug-fix only |
| `src/dashboard/src/pages/print.tsx` | component | request-response | self (lines 201-224) | bug-fix only |
| `src/dashboard/src/pages/data-at-rest.tsx` | component | CRUD | `src/dashboard/src/pages/motion.tsx` | exact |
| `src/dashboard/src/pages/motion.tsx` | component | CRUD | `src/dashboard/src/pages/data-at-rest.tsx` | exact |

---

## Pattern Assignments

### `tests/test_uat_db_integration.py` (NEW — test, live_infra integration)

**Analog:** `tests/test_chaos_storage.py` (lines 1-90)

**Module-level mark + pytestmark pattern** (`tests/test_chaos_storage.py` lines 13, 41-45):
```python
import os
import pytest
from quirk.scanner.db_connector import scan_pg_targets, scan_mysql_targets

pytestmark = pytest.mark.slow
```

**Live-infra skip decorator pattern** (`tests/test_chaos_storage.py` lines 41-45):
```python
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("QUIRK_RUN_DOCKER_IT"),
    reason="Set QUIRK_RUN_DOCKER_IT=1 to run live Docker integration",
)
def test_minio_unencrypted_bucket_produces_high_finding():
```
For DB tests, substitute `QUIRK_DB_INTEGRATION` as the env var (see RESEARCH.md Open Question 2):
```python
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("QUIRK_DB_INTEGRATION"),
    reason="Set QUIRK_DB_INTEGRATION=1 and start `docker compose --profile database up -d`",
)
```

**Core assertion pattern** (`tests/test_chaos_storage.py` lines 60-65):
```python
result = _scan_s3_encryption(session=session, logger=None, endpoint_url="http://localhost:29000")
unencrypted = [ep for ep in result if "unencrypted-bucket" in (ep.host or "")]
assert len(unencrypted) == 1
assert unencrypted[0].severity == "HIGH"
assert "S3/unencrypted" in unencrypted[0].service_detail
```
Translate for DB:
```python
results = scan_pg_targets(targets=["localhost:25432"], user="quirk_scanner", password="quirk_scanner")
assert len(results) >= 1
ep = next((r for r in results if "ssl-off" in (r.service_detail or "")), None)
assert ep is not None, f"Expected ssl-off finding; got: {[r.service_detail for r in results]}"
assert ep.protocol == "POSTGRESQL"
assert ep.severity == "HIGH"
```

**skip_registry entry to add** (`tests/skip_registry.py` lines 15-25 — current entries for format reference):
```python
("test_uat_db_integration.py", <line_pg>, "live_infra", "Requires PostgreSQL chaos lab (database profile)"),
("test_uat_db_integration.py", <line_my>, "live_infra", "Requires MySQL chaos lab (database profile)"),
```
Replace `<line_pg>` / `<line_my>` with the actual line numbers of each `@pytest.mark.skipif` decorator after finalizing the file.

---

### `tests/test_kerberos_scanner.py` (MODIFY — extend with UAT assertion comments)

**Analog:** self — existing `test_samba_dc_integration` at lines 360-382

**Existing live-infra integration test** (`tests/test_kerberos_scanner.py` lines 360-382) — already covers Phase 25 UAT pass criteria; no new test function needed:
```python
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("QUIRK_KERBEROS_INTEGRATION"),
    reason="Set QUIRK_KERBEROS_INTEGRATION=1 to run against local Samba DC chaos lab",
)
def test_samba_dc_integration():
    """KERB-05: Against a running Samba DC, scan returns RC4 etype 23 in results."""
    results = scan_kerberos_targets(["127.0.0.1"], timeout=10)
    assert isinstance(results, list)
    assert len(results) > 0
    etype_names = [ep.cert_pubkey_alg for ep in results]
    assert "rc4-hmac" in etype_names, f"Expected rc4-hmac in results, got {etype_names}"
    for ep in results:
        assert ep.protocol == "KERBEROS"
        assert ep.port == 88
```
Phase 44 closes Phase 25 UAT by re-running this test against the chaos lab. No new function required.  If the planner decides to add an explicit UAT-25 docstring annotation, copy this decorator/function shape exactly. The skip_registry entry at line 360 already exists — no new entry needed.

---

### `tests/test_saml_scanner.py` (MODIFY — extend with UAT assertion comments)

**Analog:** self — existing `test_chaos_lab_integration` at lines 365-391

**Existing live-infra integration test** (`tests/test_saml_scanner.py` lines 365-391):
```python
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("QUIRK_INTEGRATION_TESTS"),
    reason="Set QUIRK_INTEGRATION_TESTS=1 to run integration tests against chaos lab"
)
def test_chaos_lab_integration():
    """SAML-06: Full integration test against SimpleSAMLphp chaos lab at localhost:8080."""
    result = scan_saml_targets(
        ["http://localhost:8080/simplesaml/saml2/idp/metadata.php"],
        timeout=10,
    )
    assert len(result) > 0
    key_sizes = [ep.cert_pubkey_size for ep in result]
    assert 1024 in key_sizes, \
        f"Expected RSA-1024 cert in chaos lab results; got cert_pubkey_sizes={key_sizes}"
```
Phase 44 closes Phase 25 UAT by re-running this test. No new function required. The skip_registry entry at line 366 already exists.

---

### `tests/test_vault_connector.py` (MODIFY — add live integration section at end)

**Analog:** `tests/test_chaos_storage.py` for skip pattern; `tests/test_kerberos_scanner.py` lines 356-382 for section header style

**New section header pattern** (copy section comment style from `tests/test_kerberos_scanner.py` lines 356-358):
```python
# ---------------------------------------------------------------------------
# Section N: Phase 30 / UAT-30-01 Integration (SKIPPED unless env var set)
# ---------------------------------------------------------------------------
```

**New skip decorator** — use `QUIRK_VAULT_INTEGRATION` (new env var, consistent with `QUIRK_KERBEROS_INTEGRATION` naming):
```python
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("QUIRK_VAULT_INTEGRATION"),
    reason="Set QUIRK_VAULT_INTEGRATION=1 and start `docker compose --profile vault up -d`",
)
def test_vault_live_five_findings():
    """UAT-30-01: vault-30 chaos lab (port 28200) must produce exactly 5 findings."""
    from quirk.scanner.vault_connector import scan_vault_targets
    results = scan_vault_targets(
        targets=["http://localhost:28200"],
        token="root",
    )
    assert len(results) >= 5, f"Expected >=5 vault findings, got {len(results)}: {results}"
    # assert specific severities per UAT-30-01 pass criteria
    ...
```

**skip_registry entry to add**:
```python
("test_vault_connector.py", <line_v>, "live_infra", "Requires Vault-30 chaos lab (vault profile)"),
```

---

### `tests/test_dashboard_trends.py` (MODIFY — add seeded-DB fixture for Phase 31 VERIFICATION)

**Analog:** `tests/test_identity_surface.py` lines 565-598 (named shared-cache URI pattern) + `tests/test_intelligence_trends.py` lines 1-54 (CryptoEndpoint seed helper)

**Named shared-cache URI pattern — full helper** (`tests/test_identity_surface.py` lines 565-598):
```python
def _make_client_and_session(self):
    import uuid
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base
    from fastapi.testclient import TestClient

    db_name = f"test_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, TestingSession
```
For a module-level function (not class method), remove `self` parameter.

**Seeding two distinct sessions** (`tests/test_intelligence_trends.py` lines 57-58, 63-70):
```python
PREV_TS = datetime(2026, 4, 25, 9, 0, 0)
CURR_TS = datetime(2026, 4, 26, 9, 0, 0)

# Must use distinct timestamps — rows with same timestamp = same session
db.add(CryptoEndpoint(host="a.example", port=443, protocol="TLS", severity="HIGH", scanned_at=PREV_TS))
db.add(CryptoEndpoint(host="b.example", port=443, protocol="TLS", severity="MEDIUM", scanned_at=PREV_TS))
db.add(CryptoEndpoint(host="a.example", port=443, protocol="TLS", severity="HIGH", scanned_at=CURR_TS))
db.add(CryptoEndpoint(host="c.example", port=22, protocol="SSH", severity="HIGH", scanned_at=CURR_TS))
db.commit()
```

**Trends wire format assertion** (from RESEARCH.md Pattern 3 — verified against `tests/test_dashboard_trends.py` and `quirk/intelligence/trends.py`):
```python
resp = client.get("/api/trends")
assert resp.status_code == 200
data = resp.json()
for key in ("current_session_ts", "previous_session_ts", "new_high", "new_medium",
            "new_low", "resolved_high", "resolved_medium", "resolved_low",
            "scan_errors_new_count", "scan_errors_resolved_count",
            "new_findings_sample", "resolved_findings_sample"):
    assert key in data, f"Missing key: {key}"
assert data["previous_session_ts"] is not None
assert data["score_delta"] is not None
```

No new skip_registry entry needed — this test uses in-memory SQLite, not live infra.

---

### `tests/skip_registry.py` (MODIFY — add new live_infra entries)

**Current full file** (lines 1-25 — complete content):
```python
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

**Entries to append** (insert after existing `live_infra` entries, with actual line numbers determined at implementation time):
```python
    ("test_uat_db_integration.py",    <line_pg>, "live_infra", "Requires PostgreSQL chaos lab (database profile)"),
    ("test_uat_db_integration.py",    <line_my>, "live_infra", "Requires MySQL chaos lab (database profile)"),
    ("test_vault_connector.py",       <line_v>,  "live_infra", "Requires Vault-30 chaos lab (vault profile)"),
```
The meta-test `test_skip_registry.py` enforces ±2 line tolerance. Add entries only after the test file is written and line numbers are final.

---

### `quirk/dashboard/api/routes/pdf.py` (MODIFY — CR-02 + WR-01 bug fixes)

**Current full file** (lines 1-85 — complete content read above):

**CR-02 fix — wrap port coercion in try/except ValueError** (current line 45, no try/except):
```python
# BEFORE (line 45):
port = int(os.environ.get("QUIRK_SERVE_PORT", "8512"))

# AFTER — insert before line 46 (print_url assignment):
try:
    port = int(os.environ.get("QUIRK_SERVE_PORT", "8512"))
except ValueError:
    return Response(
        content=json.dumps({"detail": "QUIRK_SERVE_PORT is not a valid integer."}).encode(),
        status_code=500,
        media_type="application/json",
    )
```

**WR-01 fix — move browser.close() into finally block** (current lines 49-62):
```python
# BEFORE (browser.close() inside with block but outside finally — lines 49-62):
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(print_url, wait_until="networkidle", timeout=30_000)
        page.wait_for_selector('body[data-ready="true"]', timeout=15_000)
        pdf_bytes = page.pdf(...)
        browser.close()   # <-- skipped on exception

# AFTER — browser.close() in finally:
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto(print_url, wait_until="networkidle", timeout=30_000)
            page.wait_for_selector('body[data-ready="true"]', timeout=15_000)
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "16mm", "bottom": "16mm", "left": "12mm", "right": "12mm"},
            )
        finally:
            browser.close()
```
The `data-ready` sentinel in `print.tsx` and the `wait_for_selector('body[data-ready="true"]', ...)` call are already correct from Phase 43 — do not change them.

**Error handling pattern to preserve** (lines 71-84 — unchanged):
```python
except Exception as exc:
    msg = str(exc)
    if "chromium" in msg.lower() or "executable" in msg.lower() or "no such file" in msg.lower():
        detail = f"PDF export failed. Ensure Playwright is installed: playwright install chromium. Error: {msg}"
        return Response(
            content=json.dumps({"detail": detail}).encode(),
            status_code=503,
            media_type="application/json",
        )
    return Response(
        content=json.dumps({"detail": f"PDF export failed: {msg}"}).encode(),
        status_code=500,
        media_type="application/json",
    )
```

---

### `src/dashboard/src/pages/print.tsx` (MODIFY — WR-03: add data_in_motion subscore)

**Current score-row block** (lines 200-225 — all 5 existing subscores):
```tsx
<div className="score-row">
  <div className="score-item">
    <div className="score-number">{score.score}</div>
    <div className="score-label">Overall Readiness ({score.rating})</div>
  </div>
  <div className="score-item">
    <div className="score-number">{score.subscores.hygiene}</div>
    <div className="score-label">Hygiene</div>
  </div>
  <div className="score-item">
    <div className="score-number">{score.subscores.modern_tls}</div>
    <div className="score-label">Modern TLS</div>
  </div>
  <div className="score-item">
    <div className="score-number">{score.subscores.identity_trust}</div>
    <div className="score-label">Identity</div>
  </div>
  <div className="score-item">
    <div className="score-number">{score.subscores.agility_signals}</div>
    <div className="score-label">Agility</div>
  </div>
  <div className="score-item">
    <div className="score-number">{score.subscores.data_at_rest}</div>
    <div className="score-label">Data at Rest</div>
  </div>
  {/* INSERT HERE — after data_at_rest, before closing </div> of score-row */}
</div>
```

**Element to insert after `data_at_rest` item** (copy the existing `score-item` shape exactly):
```tsx
<div className="score-item">
  <div className="score-number">{score.subscores.data_in_motion}</div>
  <div className="score-label">Data in Motion</div>
</div>
```

---

### `src/dashboard/src/pages/data-at-rest.tsx` (MODIFY — WR-04: add scope="col" to all TableHead)

**Current TableHead pattern** (line 72, representative — all TableHead elements in this file are identical in structure):
```tsx
<TableHead className="text-xs font-semibold">Engine</TableHead>
```

**Required change — mechanical, apply to every `<TableHead>` in the file** (3 TableHeader blocks at ~lines 70, 118, 178):
```tsx
<TableHead scope="col" className="text-xs font-semibold">Engine</TableHead>
```

---

### `src/dashboard/src/pages/motion.tsx` (MODIFY — WR-04: add scope="col" to all TableHead)

**Current TableHead pattern** (line 52, representative):
```tsx
<TableHead className="text-xs font-semibold">Port</TableHead>
```

**Required change — mechanical, apply to every `<TableHead>` in the file** (2 TableHeader blocks at ~lines 50, 132):
```tsx
<TableHead scope="col" className="text-xs font-semibold">Port</TableHead>
```

---

## Shared Patterns

### Live-Infra Skip Gate
**Source:** `tests/test_chaos_storage.py` lines 41-45 and `tests/test_kerberos_scanner.py` lines 360-364
**Apply to:** `test_uat_db_integration.py` and the new vault integration section in `test_vault_connector.py`
```python
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("QUIRK_<SERVICE>_INTEGRATION"),
    reason="Set QUIRK_<SERVICE>_INTEGRATION=1 and start `docker compose --profile <profile> up -d`",
)
```
Env var names by service: `QUIRK_DB_INTEGRATION` (PostgreSQL/MySQL), `QUIRK_VAULT_INTEGRATION` (Vault-30), `QUIRK_KERBEROS_INTEGRATION` (Samba DC — existing), `QUIRK_INTEGRATION_TESTS` (SAML — existing).

### Skip Registry Entry Format
**Source:** `tests/skip_registry.py` lines 15-25
**Apply to:** Every new `@pytest.mark.skipif` for live infra
```python
("test_<file>.py", <line>, "live_infra", "Requires <service> chaos lab (<profile> profile)"),
```
Rules: `category` must be exactly `"live_infra"`; line number must match the `@pytest.mark.skipif` decorator line within ±2 at commit time; add entries only after finalizing test file.

### In-Memory SQLite with Seeding (Named Cache URI)
**Source:** `tests/test_identity_surface.py` lines 565-598
**Apply to:** `tests/test_dashboard_trends.py` seeded trends test
```python
import uuid
db_name = f"test_{uuid.uuid4().hex}"
engine = create_engine(
    f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
    connect_args={"check_same_thread": False},
)
```
Use this pattern (not the plain `dashboard_client` fixture from `conftest.py`) whenever a test needs to seed rows before making API calls.

### FastAPI Error Response Shape
**Source:** `quirk/dashboard/api/routes/pdf.py` lines 36-43 and 71-84
**Apply to:** CR-02 fix in `pdf.py`
```python
return Response(
    content=json.dumps({"detail": "<message>"}).encode(),
    status_code=<code>,
    media_type="application/json",
)
```

### score-item JSX Shape
**Source:** `src/dashboard/src/pages/print.tsx` lines 201-224
**Apply to:** WR-03 `data_in_motion` addition
```tsx
<div className="score-item">
  <div className="score-number">{score.subscores.<key>}</div>
  <div className="score-label"><Label Text></div>
</div>
```

---

## No Analog Found

None. All 10 files have strong analogs in the codebase.

---

## Metadata

**Analog search scope:** `tests/`, `quirk/dashboard/api/routes/`, `src/dashboard/src/pages/`
**Files scanned:** 10 primary analogs read in full or by targeted range
**Pattern extraction date:** 2026-05-03
