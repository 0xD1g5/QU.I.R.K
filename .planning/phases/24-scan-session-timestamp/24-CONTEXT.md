# Phase 24: Scan-Session Timestamp Isolation - Context

**Gathered:** 2026-04-24 (discuss mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

A single `session_start = datetime.now(timezone.utc)` is created in `run_scan.py` immediately
before the first identity scanner block, then passed into `scan_dnssec_targets`,
`scan_saml_targets`, and `scan_kerberos_targets` as an optional parameter. Each scanner stamps
all its `CryptoEndpoint.scanned_at` fields from this shared timestamp instead of calling
`datetime.now()` at construction time.

This closes ISSUE-3 from the v4.2 milestone audit: when Kerberos targets are slow/unreachable,
their late timestamp becomes `MAX(scanned_at)`, and the 1-second scan-window query in
`GET /api/scan/latest` silently excludes DNSSEC and SAML endpoints stamped minutes earlier.

**In scope:**
- `run_scan.py` — create shared `session_start`, thread to 3 identity scanner call sites
- `quirk/scanner/dnssec_scanner.py` — accept `session_start` in `scan_dnssec_targets`
- `quirk/scanner/saml_scanner.py` — accept in `scan_saml_targets`, thread `now` to private functions
- `quirk/scanner/kerberos_scanner.py` — accept in `scan_kerberos_targets`, normalize tzinfo
- Tests in existing scanner test files + API integration test for ISSUE-3 regression

**Out of scope:**
- TLS, SSH, JWT, container, source scanners (no scan-window risk for non-identity protocols)
- The scan window query itself in `quirk/dashboard/api/routes/scan.py` (read-only, no change needed)
- New `session_start` table column or DB schema change (scanned_at column already exists)

</domain>

<decisions>
## Implementation Decisions

### Parameter Design (D-01)
- **D-01:** `session_start` is added as an **optional keyword argument** with default `None` to all
  three identity scanner entry points:
  ```python
  def scan_dnssec_targets(targets: list, timeout: int = 10, logger=None, session_start=None) -> list:
  def scan_saml_targets(targets: list, timeout: int = 10, logger=None, session_start=None) -> list:
  def scan_kerberos_targets(targets: list, timeout: int = 10, logger=None, session_start=None) -> list:
  ```
  Inside each function: `now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)`
  — existing tests that call these functions without `session_start` continue to pass unchanged.

### session_start Creation in run_scan.py (D-02)
- **D-02:** `session_start = datetime.now(timezone.utc)` is created **just before the DNSSEC
  scanner block** (~line 462), immediately before `scan_dnssec_targets` is called. This represents
  the start of identity scanning specifically, not the full scan run. Each identity scanner block
  then receives `session_start=session_start` in its call.

### SAML Internal Function Threading (D-03)
- **D-03:** `scan_saml_targets` computes `now` once (`(session_start or datetime.now(...)).replace(tzinfo=None)`),
  then passes `now` as a keyword argument to both private parse functions:
  - `_parse_saml_metadata(xml_bytes, target_url, now=now)` ← add `now` param
  - `_parse_oidc_discovery(json_bytes, target_url, now=now)` ← add `now` param
  Each private function replaces its own local `now = datetime.now(...)` with the received `now`.
  3 function signatures change (1 public + 2 private), not 5.

### Kerberos tzinfo Normalization (D-04)
- **D-04:** `kerberos_scanner.py` currently stamps endpoints with `datetime.now(timezone.utc)`
  (timezone-aware). When `session_start` is added, kerberos will use the same
  `.replace(tzinfo=None)` normalization as DNSSEC and SAML — bringing all 3 identity scanners
  into consistent naive-datetime storage. The 3 inline `datetime.now(timezone.utc)` calls at
  endpoint construction become `scanned_at=now`.

### Fix Scope (D-05)
- **D-05:** Only the 3 identity scanners are modified. TLS, SSH, JWT, container, and source
  scanners retain their own independent `datetime.now()` calls — they are not subject to the
  scan-window timing defect because they don't participate in identity endpoint retrieval.

### Test Plan Structure (D-06)
- **D-06:** 2-plan TDD structure, consistent with all prior identity phases (17–23):
  - **Plan 01 (RED):** Write failing tests for ISSUE-3 reproduction and session_start parameter
    acceptance across all 3 scanners. Tests must fail before Plan 02 is implemented.
  - **Plan 02 (GREEN):** Implement the fix. All tests from Plan 01 must pass.

### Test Placement (D-07)
- **D-07:** Session_start unit tests spread across existing scanner test files:
  - `tests/test_dnssec_scanner.py` — test `scan_dnssec_targets(session_start=<fixed_dt>)`
  - `tests/test_saml_scanner.py` — test `scan_saml_targets(session_start=<fixed_dt>)`
  - `tests/test_kerberos_scanner.py` — test `scan_kerberos_targets(session_start=<fixed_dt>)`

### ISSUE-3 Regression Test Scenario (D-08)
- **D-08:** The Success Criterion #3 test ("simulated scan with delayed Kerberos targets still
  returns DNSSEC and SAML endpoints") is an **API window integration test** using the existing
  `conftest.py` TestClient pattern:
  1. Use `TestClient` with in-memory SQLite (the `conftest.py` fixture with `get_db` override)
  2. Insert DNSSEC and SAML endpoints with `scanned_at = session_start` (early)
  3. Insert Kerberos endpoints with a later `scanned_at` to simulate Kerberos timeout delay
  4. Call `GET /api/scan/latest` via TestClient
  5. Assert the response contains identity findings from all 3 protocols (none silently excluded)
  This lives in `tests/test_identity_surface.py` alongside existing identity integration tests.

### Claude's Discretion
- Exact test fixture setup details (pytest fixtures vs setUp/tearDown) — follow whatever pattern
  `test_identity_surface.py` currently uses
- kerberos_scanner: whether `now` is computed once at top of `scan_kerberos_targets` or inline
  at each of the 3 endpoint creation sites — top-of-function is cleaner

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Bug Diagnosis
- `.planning/v4.2-MILESTONE-AUDIT.md` §ISSUE-3 — full diagnosis of the scan-window timing defect,
  root cause analysis, and prescribed fix. MUST READ before writing any plan.

### Files to Modify
- `run_scan.py` lines 462–498 — identity scanner invocation blocks (DNSSEC, SAML, Kerberos).
  `session_start` creation goes just before line 462.
- `quirk/scanner/dnssec_scanner.py` lines 188, 305 — `now` assignment and `scan_dnssec_targets` signature
- `quirk/scanner/saml_scanner.py` lines 153, 184, 299, 325, 367 — both private parse functions
  and `scan_saml_targets` signature
- `quirk/scanner/kerberos_scanner.py` lines 238, 283, 311, 337 — `scan_kerberos_targets` signature
  and 3 inline `scanned_at=datetime.now(timezone.utc)` call sites

### Scan Window Query (read-only — understand but do NOT modify)
- `quirk/dashboard/api/routes/scan.py` lines 447–607 — `get_latest_scan()` with the 1-second
  `MAX(scanned_at)` window query that causes the ISSUE-3 exclusion

### Test Infrastructure
- `tests/conftest.py` — `TestClient` fixture with in-memory SQLite and `get_db` dependency override.
  Use this for the ISSUE-3 API integration test.
- `tests/test_identity_surface.py` — existing identity integration test patterns and helper
  endpoint factories (`_kerberos_rc4_ep()`, `_saml_weak_ep()`, `_dnssec_rsasha1_ep()`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py` TestClient fixture — ready-made in-memory DB + API client for integration tests
- `_kerberos_rc4_ep()`, `_saml_weak_ep()`, `_dnssec_rsasha1_ep()` factory helpers in `test_identity_surface.py` — can be reused or adapted for the ISSUE-3 regression test

### Established Patterns
- DNSSEC and SAML store `scanned_at` as naive datetime (`.replace(tzinfo=None)`) — kerberos must match
- All prior identity phases used 2-plan TDD (01-PLAN.md = RED, 02-PLAN.md = GREEN)
- `scan_saml_targets` is the sole public entry point; `_parse_saml_metadata` and `_parse_oidc_discovery`
  are private helpers that need `now` threaded in as a param

### Integration Points
- `run_scan.py` lines 462–498: DNSSEC → SAML → Kerberos scanner blocks — `session_start` created
  once here and passed to all three
- `CryptoEndpoint.scanned_at` — the DB column that drives the scan-window query. All endpoints
  from a session must share the same second-level timestamp for the 1-second window to capture them

</code_context>

<specifics>
## Specific Ideas

- The ISSUE-3 integration test should simulate the actual failure mode: insert early-stamped
  DNSSEC/SAML endpoints and late-stamped Kerberos endpoints into the test DB, then confirm
  `GET /api/scan/latest` returns all three. This mirrors the production scenario exactly.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 24-scan-session-timestamp*
*Context gathered: 2026-04-24*
