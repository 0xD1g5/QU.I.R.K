# Phase 44: UAT Debt Automation — Research

**Researched:** 2026-05-03
**Domain:** Pytest integration testing, chaos lab live-infra skip patterns, DB/Vault/Identity connectors, dashboard bug fixes
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**K8s Testing Strategy (Phase 29 UAT)**
- D-01: All three Phase 29 UAT scenarios (UAT-29-01 EKS, UAT-29-02 GKE, UAT-29-03 AKS) are formally classified as cloud-only.
- D-02: Existing `tests/test_k8s_connector.py` mock-based coverage is accepted as sufficient. No new Docker or cluster infrastructure added.
- D-03: Phase 29 UAT row in STATE.md closed as `cloud-only` with rationale: "EKS/GKE/AKS encryption detection requires cloud-managed control plane APIs not available in a local cluster. Scanner logic is covered by mock-based unit tests in test_k8s_connector.py."

**DB Testing Approach (Phase 27 UAT)**
- D-04: New live integration tests use the existing `database` chaos lab profile (PostgreSQL on port 25432, MySQL on port 23306). Same live_infra skip pattern as `tests/test_chaos_storage.py` and `tests/test_kerberos_scanner.py`.
- D-05: Both Phase 27 rows in STATE.md closed as `automated (chaos lab)`.
- D-06: New tests in dedicated `tests/test_uat_db_integration.py` (not folded into mock-based `tests/test_db_connector.py`).

**50% Reduction Path**
- D-07: 7 target rows for STATE.md closure: Phase 25 HUMAN-UAT, Phase 25 VERIFICATION, Phase 27 HUMAN-UAT, Phase 27 UAT, Phase 29 UAT, Phase 30 HUMAN-UAT, Phase 31 VERIFICATION.
- D-08: Phase 31 VERIFICATION uses `conftest.py` `dashboard_client` fixture with two pre-seeded `CryptoEndpoint` scan sessions in an in-memory SQLite DB, driving `GET /api/trends`.

**Phase 43 Open CR Findings**
- D-09: Fix 4 real bugs: CR-02 (ValueError on bad port in pdf.py), WR-01 (browser.close() not in finally), WR-03 (missing data_in_motion in print.tsx), WR-04 (scope="col" in data-at-rest.tsx and motion.tsx TableHead).
- D-10: WR-05 and WR-06 deferred.

**Vault + Identity Testing**
- D-11: Phase 25 (Kerberos + SAML) and Phase 30 Vault run against existing chaos lab profiles with live_infra skips.
- D-12: UAT-30-01 automation follows explicit 5-finding spec from vault seed.

### Claude's Discretion
- Whether Phase 25 UAT tests extend existing `test_kerberos_scanner.py` / `test_saml_scanner.py` or get a dedicated `tests/test_uat_identity_integration.py` file.
- Whether Phase 30 UAT tests extend `test_vault_connector.py` or get a dedicated `tests/test_uat_vault_integration.py` file.
- Exact skip_registry line numbers for new live_infra entries (determined during implementation).
- Order of plan execution.

### Deferred Ideas (OUT OF SCOPE)
- WR-05: FAIL cosmetic in summary table — deferred to future cleanup.
- WR-06: Hardcoded Chrome path in CI YAML — deferred to future CI cleanup phase.
- Phase 04/05/07/13/28/31 deferred items (other than Phase 31 VERIFICATION) — not targeted in Phase 44.
- Phase 28 VERIFICATION (cloud-only object storage) — not Phase 44's concern.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UAT-01 | Phase 27 DB UAT scenarios run against `database` chaos lab profile in CI — deferred items move to `passing` | `database` profile confirmed: postgres-ssl-off:25432, mysql-ssl-off:23306; db_connector.py scan functions verified; live_infra skip pattern in test_chaos_storage.py confirmed |
| UAT-02 | Phase 29 K8s UAT scenarios — cloud-managed encryption cases documented cloud-only per D-01/D-02/D-03 | Requirements.md UAT-02 wording confirmed; STATE.md closure requires explicit rationale entry only |
| UAT-03 | Phase 25 identity and Phase 30 Vault UAT scenarios re-run; failing scenarios get fixes or cloud-only justification | kerberos/saml profiles and vault-30 profile confirmed; skip env vars verified (QUIRK_KERBEROS_INTEGRATION, QUIRK_INTEGRATION_TESTS); 5 vault findings confirmed from seed.sh |
| UAT-04 | STATE.md Deferred Items table updated — net reduction of ≥50% of 14 carry-over items | 7 target rows identified in D-07; closure logic documented per-row |
</phase_requirements>

---

## Summary

Phase 44 is a debt-closure phase, not a feature phase. Its output is: 4 new pytest integration test files (or extensions), 4 bug fixes to existing files, and 7 STATE.md row closures. No new chaos lab profiles, no new connector code.

The work divides cleanly into four independent workstreams: (1) DB integration tests for Phase 27 against the `database` chaos lab profile, (2) Vault integration tests for Phase 30 against the `vault` chaos lab profile, (3) identity integration tests for Phase 25 against `kerberos` and `saml` profiles, (4) Phase 31 VERIFICATION automation using a seeded in-memory DB against `GET /api/trends`, plus (5) four surgical bug fixes from 43-REVIEW.md. STATE.md closure is the final bookkeeping step.

**Primary recommendation:** Implement workstreams in dependency order — bug fixes first (unblocked, small), then integration tests (require chaos lab), then STATE.md closure (requires test evidence). All integration tests follow the established `QUIRK_*_INTEGRATION` + `skip_registry.py` pattern exactly; no novel patterns needed.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DB integration tests (Phase 27 UAT) | Test suite | DB connector (quirk/scanner/db_connector.py) | Tests drive the existing connector; no connector changes needed |
| Vault integration tests (Phase 30 UAT) | Test suite | Vault connector (quirk/scanner/vault_connector.py) | Tests drive the existing connector; no connector changes needed |
| Identity integration tests (Phase 25 UAT) | Test suite | kerberos_scanner.py / saml_scanner.py | New UAT assertions on existing scanner logic |
| Phase 31 VERIFICATION (trends) | Test suite | Dashboard API (GET /api/trends) | Seeded in-memory DB drives existing trends route |
| pdf.py bug fixes (CR-02, WR-01) | API / Backend | — | Python route handler fixes only |
| print.tsx bug fix (WR-03) | Frontend | — | TSX component change only |
| data-at-rest.tsx / motion.tsx (WR-04) | Frontend | — | TSX attribute addition only |
| STATE.md closure | Planning artifacts | — | Prose update only, no code |

---

## Standard Stack

### Core (all already installed, no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=7.x (project uses) | Test runner | Project standard |
| psycopg2-binary | >=2.9.0 (quirk[db]) | Live PostgreSQL connection | DB connector requires it |
| PyMySQL | >=1.1.0 (quirk[db]) | Live MySQL connection | DB connector requires it |
| hvac | >=2.0 (quirk[cloud]) | Live Vault connection | Vault connector requires it |
| sqlalchemy | existing | In-memory SQLite for trends fixture | Already used in conftest.py |

[VERIFIED: project source grep] All required packages are already declared in pyproject.toml under their respective extras groups. No new dependencies needed.

**No `pip install` step required for Phase 44.**

---

## Architecture Patterns

### Pattern 1: Live-Infra Skip (the canonical pattern for all new integration tests)

**What:** Tests that require Docker + a running chaos lab profile are gated behind an env var check and registered in `skip_registry.py`.

**When to use:** Every new `@pytest.mark.skipif` for live infrastructure.

**Exact format from verified sources:**

```python
# Source: tests/test_kerberos_scanner.py:360 [VERIFIED: codebase read]
@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("QUIRK_KERBEROS_INTEGRATION"),
    reason="Set QUIRK_KERBEROS_INTEGRATION=1 to run against local Samba DC chaos lab",
)
def test_samba_dc_integration():
    ...
```

```python
# Source: tests/test_saml_scanner.py:366 [VERIFIED: codebase read]
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("QUIRK_INTEGRATION_TESTS"),
    reason="Set QUIRK_INTEGRATION_TESTS=1 to run integration tests against chaos lab"
)
def test_chaos_lab_integration():
    ...
```

**Skip registry entry format** — must match file + approximate line number:
```python
# Source: tests/skip_registry.py [VERIFIED: codebase read]
("test_uat_db_integration.py",   <line>, "live_infra", "Requires PostgreSQL/MySQL database chaos lab"),
("test_uat_vault_integration.py", <line>, "live_infra", "Requires HashiCorp Vault chaos lab"),
```

**Critical constraint:** `test_skip_registry.py` enforces `ALLOWED_SKIPS` with ±2 line tolerance. A new unregistered skip causes CI failure. [VERIFIED: tests/test_skip_registry.py read]

### Pattern 2: In-Memory DB Fixture for Dashboard API Tests

**What:** `conftest.py` `dashboard_client` fixture creates a shared-cache SQLite in-memory engine, creates all tables, overrides `get_db`, and returns a `TestClient`.

**How to seed data for trends tests:**

```python
# Source: tests/test_intelligence_trends.py [VERIFIED: codebase read]
# The dashboard_client fixture does NOT expose the underlying session directly.
# For tests that need to seed data, use the pattern from test_identity_surface.py:
# create your own (client, TestingSession) pair using a named shared-cache URI.

import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, CryptoEndpoint
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
```

[VERIFIED: tests/conftest.py and tests/test_identity_surface.py read]

**Important nuance:** The plain `dashboard_client` fixture uses `sqlite:///file::memory:?cache=shared&uri=true` — a single shared-cache URI. If two tests use the same named DB and one seeds data, the other will see it. The `test_intelligence_trends.py` pattern avoids this with a unique `uuid` name per test. For Phase 31 VERIFICATION tests that intentionally need two sessions, use the named URI pattern.

### Pattern 3: Trends Wire Format (UAT-9-09 assertion target)

**What:** `GET /api/trends` returns a flat JSON object. [VERIFIED: tests/test_dashboard_trends.py and quirk/intelligence/trends.py read]

```json
{
  "current_session_ts": "2026-04-26T09:00:00",
  "previous_session_ts": "2026-04-25T09:00:00",
  "current_score": 65,
  "previous_score": 70,
  "score_delta": -5,
  "new_high": 1,
  "new_medium": 0,
  "new_low": 0,
  "resolved_high": 0,
  "resolved_medium": 1,
  "resolved_low": 0,
  "scan_errors_new_count": 0,
  "scan_errors_resolved_count": 0,
  "new_findings_sample": [...],
  "resolved_findings_sample": [...]
}
```

Key rules verified in trends.py:
- `new_high` buckets CRITICAL + HIGH together
- `score_delta` is `null` (not `0`) when fewer than 2 distinct sessions
- `scan_error` rows are excluded from new/resolved buckets and counted separately
- INFO severity is excluded from new/resolved buckets
- Sample arrays are capped at 5 items

### Pattern 4: DB Connector Live Paths

**What:** The `database` chaos lab profile runs PostgreSQL and MySQL with SSL explicitly disabled.

```yaml
# Source: quantum-chaos-enterprise-lab/docker-compose.yml [VERIFIED: codebase read]
postgres-ssl-off:
  image: postgres:15
  environment:
    POSTGRES_DB: quirk_db
    POSTGRES_USER: quirk_scanner
    POSTGRES_PASSWORD: quirk_scanner
  command: postgres -c ssl=off
  ports:
    - "25432:5432"

mysql-ssl-off:
  image: mysql:8
  environment:
    MYSQL_DATABASE: quirk_db
    MYSQL_USER: quirk_scanner
    MYSQL_PASSWORD: quirk_scanner
    MYSQL_ROOT_PASSWORD: "root"
  command: --skip-ssl
  ports:
    - "23306:3306"
```

**Expected scanner output** from `expected_results_v4.md` [VERIFIED: codebase read]:
- PostgreSQL port 25432: `protocol=POSTGRESQL, service_detail=PostgreSQL/ssl-off` (HIGH)
- MySQL port 23306: `protocol=MYSQL, service_detail=MySQL/ssl-off` (HIGH)

**Live integration test call pattern:**
```python
from quirk.scanner.db_connector import scan_pg_targets, scan_mysql_targets

results = scan_pg_targets(
    targets=["localhost:25432"],
    user="quirk_scanner",
    password="quirk_scanner",
)
# assert: len(results) >= 1; results[0].severity == "HIGH"; "ssl-off" in results[0].service_detail
```

### Pattern 5: Vault Connector Live Paths

**What:** The `vault` chaos lab profile runs `vault-30` (image 1.17) on port 28200 with a seed script that creates exactly 5 finding-relevant resources.

```bash
# Source: quantum-chaos-enterprise-lab/vault/seed.sh [VERIFIED: codebase read]
# Seeded state:
# 1. transit/keys/rsa-2048-classification  — non-exportable, no severity
# 2. transit/keys/rsa-2048-exportable       — exportable=true, MEDIUM severity
# 3. pki/root/generate/internal (RSA-2048)  — HIGH severity
# 4. auth/token                             — always present in dev mode, HIGH
# 5. auth/userpass                          — MEDIUM severity
```

Expected findings from `expected_results_v4.md` [VERIFIED: codebase read]:
- `transit/rsa-2048-classification` → no severity (classification only)
- `transit/rsa-2048-exportable` → MEDIUM
- `PKI/pki` → HIGH (RSA-2048 root CA)
- `auth/token` → HIGH
- `auth/userpass` → MEDIUM
- `dar_vault_weak_count == 2` (HIGH-only)

**Connection config for tests:**
```python
# vault_addr = "http://localhost:28200"
# vault_token = "root"
```

### Anti-Patterns to Avoid

- **Folding integration tests into mock-based test files:** `test_db_connector.py` is mock-only by design (D-06). Adding live tests there confuses the unit/integration boundary.
- **Using the plain `dashboard_client` fixture and expecting to seed data through it:** The fixture creates the DB and TestClient but does not expose the Session. Use the named shared-cache URI pattern from `test_identity_surface.py` when you need to seed rows.
- **Forgetting `skip_registry.py` update:** Any `pytest.mark.skipif` for live infra not registered in `ALLOWED_SKIPS` causes `test_skip_registry.py` to fail in CI. The meta-test has ±2 line tolerance, so exact line number does not need to be pre-calculated, but the file name must match.
- **Using the wrong env var name for skip gates:** Kerberos uses `QUIRK_KERBEROS_INTEGRATION`; SAML uses `QUIRK_INTEGRATION_TESTS`. Mixing them means one test can't be independently activated.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Live DB skip gate | Custom Docker availability check | `QUIRK_*_INTEGRATION` env var + `@pytest.mark.skipif` | Established project pattern; skip_registry meta-test enforces it |
| In-memory SQLite test fixture | New conftest fixtures | Existing `dashboard_client` (no seed) or named-cache UUID pattern (with seed) | Pattern already verified in test_intelligence_trends.py + test_identity_surface.py |
| Trends wire format assertions | Build response parser | Assert dict key presence and types directly (test_dashboard_trends.py pattern) | Simple dict assertions; no extra abstraction needed |
| Vault connection in tests | Custom vault client | `hvac` (used by vault_connector.py) or call `scan_vault_targets()` directly | Connector already handles auth, error handling |

---

## Bug Fix Details (Phase 43 CR Findings)

### CR-02: ValueError on bad QUIRK_SERVE_PORT (pdf.py)

**File:** `quirk/dashboard/api/routes/pdf.py` [VERIFIED: codebase read]

**Current code (line 45, outside try block):**
```python
port = int(os.environ.get("QUIRK_SERVE_PORT", "8512"))
```

**Required fix (D-09 spec):**
```python
try:
    port = int(os.environ.get("QUIRK_SERVE_PORT", "8512"))
except ValueError:
    return Response(
        content=json.dumps({"detail": "QUIRK_SERVE_PORT is not a valid integer."}).encode(),
        status_code=500,
        media_type="application/json",
    )
```

Do NOT silently fall back to a default — surface the misconfiguration with a clear error message (D-09 specifics).

### WR-01: browser.close() not in finally (pdf.py)

**File:** `quirk/dashboard/api/routes/pdf.py` [VERIFIED: codebase read]

**Current code (line 62):** `browser.close()` sits inside the `with sync_playwright()` block but outside a `finally`.

**Required fix:**
```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    try:
        context = browser.new_context()
        page = context.new_page()
        page.goto(print_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_selector("[data-quirk-ready='true']", timeout=15_000)
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "16mm", "bottom": "16mm", "left": "12mm", "right": "12mm"},
        )
    finally:
        browser.close()
```

Note: The CR-01 fix (sentinel wait) is already embedded in the WR-01 fix shape — use `domcontentloaded` + `wait_for_selector("[data-quirk-ready='true']")`. CR-01 is NOT in Phase 44's scope as a standalone fix; the `data-quirk-ready` sentinel in print.tsx was already addressed in Phase 43. Verify by reading current print.tsx state before implementing.

**Current print.tsx state** [VERIFIED: codebase read — line 152-158]: The sentinel `data-ready="true"` IS already present in print.tsx from Phase 43:
```tsx
useEffect(() => {
  if (data) {
    document.body.setAttribute('data-ready', 'true')
  }
  ...
```
And pdf.py already uses `page.wait_for_selector('body[data-ready="true"]', ...)`. So the WR-01 fix is purely about the `finally` block — no sentinel changes needed.

### WR-03: Missing data_in_motion subscore in print.tsx

**File:** `src/dashboard/src/pages/print.tsx:193-225` [VERIFIED: codebase read]

**Current state:** Score section renders 5 subscores (hygiene, modern_tls, identity_trust, agility_signals, data_at_rest). `data_in_motion` is missing.

**Required addition** — add after the `data_at_rest` score item:
```tsx
<div className="score-item">
  <div className="score-number">{score.subscores.data_in_motion}</div>
  <div className="score-label">Data in Motion</div>
</div>
```

### WR-04: Missing scope="col" on TableHead in data-at-rest.tsx and motion.tsx

**Files verified** [VERIFIED: codebase grep]:

- `src/dashboard/src/pages/data-at-rest.tsx`: Three `<TableHeader>` blocks at lines ~70, ~118, ~178. All `<TableHead>` elements lack `scope="col"`.
- `src/dashboard/src/pages/motion.tsx`: Two `<TableHeader>` blocks at lines ~50 and ~132. All `<TableHead>` elements lack `scope="col"`.

**Required change** — mechanical: add `scope="col"` to every `<TableHead>` in both files:
```tsx
<TableHead scope="col" className="text-xs font-semibold">Engine</TableHead>
```

---

## Common Pitfalls

### Pitfall 1: Skip Registry Line Number Drift

**What goes wrong:** You write the test, then add it to `skip_registry.py` with the line number from your editor. Later edits to the file shift line numbers beyond ±2. The meta-test fails.

**Why it happens:** `skip_registry.py` requires approximate line numbers; ±2 tolerance exists but is not unlimited.

**How to avoid:** Add the skip_registry entry after finalizing the test file. Use the actual line number of the `@pytest.mark.skipif` decorator at the time of commit. Run `pytest tests/test_skip_registry.py` as a final check before committing.

**Warning signs:** `test_skip_registry.py::test_all_skips_are_registered` fails with "unregistered skip" message.

### Pitfall 2: dashboard_client Fixture Cannot Seed Data

**What goes wrong:** Test tries to `dashboard_client.db.add(...)` or access the underlying session through the TestClient. Fails because the fixture only returns the TestClient, not the session.

**Why it happens:** `conftest.py` `dashboard_client` does not expose the TestingSession.

**How to avoid:** For seeded tests, reproduce the named-cache UUID pattern from `test_identity_surface.py:565-598`. Do not try to access db through the client.

### Pitfall 3: Vault-30 Port vs Vault-Storage Port Confusion

**What goes wrong:** Integration test points at `localhost:20009` (the legacy `storage` profile vault) instead of `localhost:28200` (the Phase 30 `vault` profile vault). The storage profile vault is seeded differently (no explicit transit/PKI/auth setup matching UAT-30-01).

**Why it happens:** Two Vault instances exist in docker-compose.yml — `vault` (storage profile, port 20009, image 1.15) and `vault-30` (vault profile, port 28200, image 1.17).

**How to avoid:** Always use `http://localhost:28200` and `--profile vault` for Phase 30 UAT. Never use 20009 for UAT-30-01.

### Pitfall 4: scan_pg_targets Requires PSYCOPG2_AVAILABLE=True

**What goes wrong:** Live test calls `scan_pg_targets()` but psycopg2-binary isn't installed. The function returns `[]` silently (graceful degradation).

**Why it happens:** Connector has module-level `PSYCOPG2_AVAILABLE = False` when psycopg2 is absent.

**How to avoid:** The test's skip gate (`not os.environ.get("QUIRK_DB_INTEGRATION")`) implies the user has started the chaos lab — document in the test's docstring that `pip install quirk[db]` is also required. Assert `PSYCOPG2_AVAILABLE` at test start if you want an explicit failure mode.

### Pitfall 5: Trends Seeding — Two Distinct Sessions Required

**What goes wrong:** Test seeds CryptoEndpoints with the same `scanned_at` timestamp for both sessions. `compute_trend_report` treats them as one session; `score_delta` returns null.

**Why it happens:** Session identification is by distinct `scanned_at` values; rows with identical timestamps are in the same session.

**How to avoid:** Use two clearly distinct timestamps (e.g., `PREV_TS = datetime(2026, 4, 25, 9, 0, 0)` and `CURR_TS = datetime(2026, 4, 26, 9, 0, 0)`). This is the exact pattern in `test_intelligence_trends.py`.

---

## Code Examples

### DB Live Integration Test Skeleton

```python
# Source: tests/test_kerberos_scanner.py pattern [VERIFIED: codebase read]
# File: tests/test_uat_db_integration.py

import os
import pytest
from quirk.scanner.db_connector import scan_pg_targets, scan_mysql_targets

pytestmark = pytest.mark.slow


@pytest.mark.skipif(
    not os.environ.get("QUIRK_DB_INTEGRATION"),
    reason="Set QUIRK_DB_INTEGRATION=1 and start `docker compose --profile database up -d`",
)
def test_postgres_ssl_off_produces_high():
    """UAT-27: database chaos lab PostgreSQL/ssl-off → HIGH finding."""
    results = scan_pg_targets(
        targets=["localhost:25432"],
        user="quirk_scanner",
        password="quirk_scanner",
    )
    assert len(results) >= 1
    ep = next(
        (r for r in results if "ssl-off" in (r.service_detail or "")), None
    )
    assert ep is not None, f"Expected ssl-off finding; got: {[r.service_detail for r in results]}"
    assert ep.protocol == "POSTGRESQL"
    assert ep.severity == "HIGH"


@pytest.mark.skipif(
    not os.environ.get("QUIRK_DB_INTEGRATION"),
    reason="Set QUIRK_DB_INTEGRATION=1 and start `docker compose --profile database up -d`",
)
def test_mysql_ssl_off_produces_high():
    """UAT-27: database chaos lab MySQL/ssl-off → HIGH finding."""
    results = scan_mysql_targets(
        targets=["localhost:23306"],
        user="quirk_scanner",
        password="quirk_scanner",
    )
    assert len(results) >= 1
    ep = next(
        (r for r in results if "ssl-off" in (r.service_detail or "")), None
    )
    assert ep is not None
    assert ep.protocol == "MYSQL"
    assert ep.severity == "HIGH"
```

### Phase 31 VERIFICATION: Seeded Trends Test Skeleton

```python
# Source: tests/test_intelligence_trends.py + test_identity_surface.py patterns [VERIFIED: codebase read]
# File: tests/test_uat_trends_verification.py

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from quirk.models import Base, CryptoEndpoint


PREV_TS = datetime(2026, 4, 25, 9, 0, 0)
CURR_TS = datetime(2026, 4, 26, 9, 0, 0)


def _make_client_and_session():
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db

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
    return TestClient(app), TestingSession


def test_trends_two_sessions_flat_wire_format():
    """UAT-31-VERIFICATION: /api/trends returns flat wire format with two seeded sessions."""
    client, SessionFactory = _make_client_and_session()
    db = SessionFactory()
    try:
        # Session 1 (previous)
        db.add(CryptoEndpoint(host="a.example", port=443, protocol="TLS", severity="HIGH", scanned_at=PREV_TS))
        db.add(CryptoEndpoint(host="b.example", port=443, protocol="TLS", severity="MEDIUM", scanned_at=PREV_TS))
        # Session 2 (current) — b resolved, c new
        db.add(CryptoEndpoint(host="a.example", port=443, protocol="TLS", severity="HIGH", scanned_at=CURR_TS))
        db.add(CryptoEndpoint(host="c.example", port=22, protocol="SSH", severity="HIGH", scanned_at=CURR_TS))
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/trends")
    assert resp.status_code == 200
    data = resp.json()

    # Flat wire format (UAT-9-09)
    for key in ("current_session_ts", "previous_session_ts", "new_high", "new_medium",
                "new_low", "resolved_high", "resolved_medium", "resolved_low",
                "scan_errors_new_count", "scan_errors_resolved_count",
                "new_findings_sample", "resolved_findings_sample"):
        assert key in data, f"Missing key: {key}"

    assert data["previous_session_ts"] is not None
    assert data["score_delta"] is not None
    assert data["new_high"] >= 1   # c.example:22 SSH HIGH is new
    assert data["resolved_medium"] >= 1   # b.example:443 TLS MEDIUM is resolved
```

### skip_registry.py Entry Format

```python
# Source: tests/skip_registry.py [VERIFIED: codebase read]
# Add entries after determining actual line numbers during implementation:
("test_uat_db_integration.py",    <line_pg>,  "live_infra", "Requires PostgreSQL chaos lab (database profile)"),
("test_uat_db_integration.py",    <line_my>,  "live_infra", "Requires MySQL chaos lab (database profile)"),
("test_uat_vault_integration.py", <line_v>,   "live_infra", "Requires Vault-30 chaos lab (vault profile)"),
# Identity tests — if new file created:
("test_uat_identity_integration.py", <line_k>, "live_infra", "Requires Samba DC chaos lab (kerberos profile)"),
("test_uat_identity_integration.py", <line_s>, "live_infra", "Requires SimpleSAMLphp chaos lab (saml profile)"),
# OR — if extending existing files, line numbers of the new skip decorators in those files
```

---

## STATE.md Closure Map

| Row to close | Current status | Closure action | Evidence required |
|---|---|---|---|
| Phase 25 HUMAN-UAT (2 pending) | partial | `automated (chaos lab)` | New integration tests pass against kerberos + saml profiles |
| Phase 25 VERIFICATION | human_needed | `automated (chaos lab)` | Same test evidence as HUMAN-UAT |
| Phase 27 HUMAN-UAT (1 pending) | partial | `automated (chaos lab)` | `test_uat_db_integration.py` passes against database profile |
| Phase 27 UAT (7 pending) | deferred | `automated (chaos lab)` | Same test evidence |
| Phase 29 UAT (10 pending) | testing | `cloud-only` | Add rationale string: "EKS/GKE/AKS encryption detection requires cloud-managed control plane APIs not available in a local cluster. Scanner logic is covered by mock-based unit tests in test_k8s_connector.py." |
| Phase 30 HUMAN-UAT (1 pending) | partial | `automated (chaos lab)` | `test_uat_vault_integration.py` passes against vault profile |
| Phase 31 VERIFICATION | human_needed | `automated (pytest)` | `test_uat_trends_verification.py` passes against in-memory DB fixture |

Net reduction: 7 rows closed out of 14 = 50% exactly (meets D-07 threshold).

---

## Runtime State Inventory

> This is a code/test phase with no renamed entities or database migrations. Not applicable.

None — verified by phase description (no rename, no refactor, no migration). All work is new test files, bug fixes to existing files, and STATE.md prose updates.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | DB/Vault/Identity integration tests | Assumed present (chaos lab already in use) | — | Tests skip via env var gate |
| psycopg2-binary | test_uat_db_integration.py (PostgreSQL) | Requires `pip install quirk[db]` | — | Tests skip if QUIRK_DB_INTEGRATION not set |
| PyMySQL | test_uat_db_integration.py (MySQL) | Requires `pip install quirk[db]` | — | Same skip gate |
| hvac | test_uat_vault_integration.py | Requires `pip install quirk[cloud]` | — | Skip via QUIRK_VAULT_INTEGRATION gate |
| pytest | All tests | ✓ | existing | — |
| playwright | pdf.py bug fix tests | ✓ (existing test coverage in test_pdf_export.py) | existing | — |

[ASSUMED] The chaos lab profiles (`database`, `vault`, `kerberos`, `saml`) can be started locally. The planner should note that the skip gates exist specifically to handle the case where they are unavailable.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing project standard) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `python -m pytest tests/ -m 'not slow' -q` |
| Full suite command | `python -m pytest tests/ -q` |
| Integration tests | `QUIRK_DB_INTEGRATION=1 python -m pytest tests/test_uat_db_integration.py -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UAT-01 | PostgreSQL/ssl-off → HIGH against live chaos lab | integration | `QUIRK_DB_INTEGRATION=1 pytest tests/test_uat_db_integration.py -v` | ❌ Wave 0 |
| UAT-01 | MySQL/ssl-off → HIGH against live chaos lab | integration | `QUIRK_DB_INTEGRATION=1 pytest tests/test_uat_db_integration.py -v` | ❌ Wave 0 |
| UAT-02 | K8s cloud-only rationale in STATE.md | prose/manual | N/A (STATE.md update only) | N/A |
| UAT-03 | Vault 5 findings against chaos lab | integration | `QUIRK_VAULT_INTEGRATION=1 pytest tests/test_uat_vault_integration.py -v` | ❌ Wave 0 |
| UAT-03 | Kerberos rc4-hmac against samba-dc chaos lab | integration | `QUIRK_KERBEROS_INTEGRATION=1 pytest tests/test_kerberos_scanner.py -k samba_dc -v` | ✅ (existing test_samba_dc_integration) |
| UAT-03 | SAML RSA-1024 against SimpleSAMLphp chaos lab | integration | `QUIRK_INTEGRATION_TESTS=1 pytest tests/test_saml_scanner.py -k chaos_lab -v` | ✅ (existing test_chaos_lab_integration) |
| UAT-03 | Phase 31 trends /api/trends flat wire format | unit (seeded DB) | `pytest tests/test_uat_trends_verification.py -v` | ❌ Wave 0 |
| UAT-04 | STATE.md ≥7 rows closed | prose/verification | N/A (STATE.md update only) | N/A |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/ -m 'not slow' -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_uat_db_integration.py` — covers UAT-01 (PostgreSQL + MySQL live integration)
- [ ] `tests/test_uat_vault_integration.py` — covers UAT-03 Vault (or extend test_vault_connector.py)
- [ ] `tests/test_uat_trends_verification.py` — covers UAT-04 Phase 31 VERIFICATION (seeded-DB /api/trends)
- [ ] `tests/skip_registry.py` — new ALLOWED_SKIPS entries for new live_infra tests
- Note: Kerberos and SAML integration tests already exist in their respective scanner test files — no new files needed for those.

---

## Security Domain

The four bug fixes do not introduce new attack surface. The `ValueError` handling fix (CR-02) reduces information leakage by producing a structured JSON response rather than an unformatted FastAPI 500. No new authentication, cryptographic, or injection-risk code paths are introduced.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes (CR-02: env var coercion) | Explicit `try/except ValueError` with structured response |
| V2–V4, V6 | no | Not applicable to this phase |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pip install quirk[db]` is available in the dev environment for running live DB integration tests | Environment Availability | Live integration tests would silently return [] instead of finding ssl-off; tests would pass vacuously |
| A2 | The chaos lab profiles (database, vault, kerberos, saml) can be started on the development machine | Environment Availability | All live_infra tests would skip, blocking UAT-01/UAT-03 automation evidence |

---

## Open Questions (RESOLVED)

1. **New test files vs. extending existing ones for identity (Phase 25)**
   - What we know: `test_kerberos_scanner.py:360` and `test_saml_scanner.py:366` have existing live_infra integration tests (`test_samba_dc_integration`, `test_chaos_lab_integration`) that already cover UAT-5-22 and UAT-5-21 respectively.
   - What's unclear: Whether Phase 44 needs NEW UAT tests beyond those that already exist, or whether re-verifying the existing integration tests pass is sufficient to close Phase 25 HUMAN-UAT.
   - Recommendation: The existing integration tests in those files already cover the Phase 25 HUMAN-UAT pass criteria (rc4-hmac for Kerberos; RSA-1024 cert_pubkey_size for SAML). No new test file is needed for Phase 25. The planner should treat Phase 25 automation as "re-run existing `test_samba_dc_integration` and `test_chaos_lab_integration` against the chaos lab and confirm they pass" rather than writing new test logic.

2. **QUIRK_DB_INTEGRATION env var name**
   - What we know: This env var does not yet exist in the project. Kerberos uses `QUIRK_KERBEROS_INTEGRATION`; SAML uses `QUIRK_INTEGRATION_TESTS`.
   - What's unclear: Whether to use `QUIRK_DB_INTEGRATION` (new, consistent naming) or `QUIRK_RUN_DOCKER_IT` (used by test_chaos_storage.py for MinIO).
   - Recommendation: Use `QUIRK_DB_INTEGRATION=1` for the new DB tests. It follows the `QUIRK_*_INTEGRATION` naming pattern established by Kerberos and is more descriptive than the generic `QUIRK_RUN_DOCKER_IT`.

3. **Vault integration test env var name**
   - Similar to DB: no existing `QUIRK_VAULT_INTEGRATION` env var.
   - Recommendation: Use `QUIRK_VAULT_INTEGRATION=1` for consistency.

---

## Sources

### Primary (HIGH confidence)
- `tests/test_chaos_storage.py` — live_infra skip pattern (QUIRK_RUN_DOCKER_IT)
- `tests/test_kerberos_scanner.py:360` — live_infra skip pattern (QUIRK_KERBEROS_INTEGRATION)
- `tests/test_saml_scanner.py:366` — live_infra skip pattern (QUIRK_INTEGRATION_TESTS)
- `tests/skip_registry.py` — ALLOWED_SKIPS format and ±2 tolerance
- `tests/conftest.py` — dashboard_client fixture implementation
- `tests/test_intelligence_trends.py` — trends seeding pattern, TrendReport field names
- `tests/test_identity_surface.py:565-598` — named shared-cache URI pattern for seeded tests
- `quantum-chaos-enterprise-lab/docker-compose.yml` — all profile service definitions and ports
- `quantum-chaos-enterprise-lab/expected_results_v4.md:353-405` — database and vault expected findings
- `quantum-chaos-enterprise-lab/vault/seed.sh` — exact vault seeded state
- `quirk/dashboard/api/routes/pdf.py` — current pdf.py implementation (CR-02, WR-01)
- `src/dashboard/src/pages/print.tsx` — current print.tsx implementation (WR-03)
- `src/dashboard/src/pages/data-at-rest.tsx` — TableHead locations (WR-04)
- `src/dashboard/src/pages/motion.tsx` — TableHead locations (WR-04)
- `.planning/phases/43-dashboard-polish/43-REVIEW.md` — authoritative CR/WR descriptions
- `.planning/STATE.md §Deferred Items` — 14 carry-over rows to reduce
- `docs/UAT-SERIES.md §UAT-30-01, §UAT-9-09, §UAT-5-21, §UAT-5-22, §UAT-5-25` — pass criteria

### Secondary (MEDIUM confidence)
- `quirk/scanner/db_connector.py` — connector public API (scan_pg_targets, scan_mysql_targets signatures)
- `quirk/intelligence/trends.py` — TrendReport field names and null/0 rules
- `quirk/dashboard/api/routes/trends.py` — /api/trends response model

---

## Metadata

**Confidence breakdown:**
- Chaos lab profiles and ports: HIGH — verified from docker-compose.yml and expected_results_v4.md
- Skip pattern implementation: HIGH — verified from three existing live_infra tests
- Bug fix scope and line numbers: HIGH — verified from codebase reads of pdf.py, print.tsx, data-at-rest.tsx, motion.tsx, and 43-REVIEW.md
- Trends seeded-DB fixture approach: HIGH — verified from test_intelligence_trends.py and test_identity_surface.py patterns
- STATE.md row count and closure mapping: HIGH — verified from STATE.md Deferred Items table

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (stable domain — test patterns and chaos lab config are stable)
