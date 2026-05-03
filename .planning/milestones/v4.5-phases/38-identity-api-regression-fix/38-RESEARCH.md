# Phase 38: Identity API Regression Fix — Research

**Researched:** 2026-04-29
**Domain:** FastAPI scan endpoint; SQLAlchemy time-window query; pytest regression closure
**Confidence:** HIGH

---

## Summary

Phase 38 closes three tightly-coupled deferred items from v4.4: GAP-01 (the SAML/OIDC
regression in `/api/scan/latest`), GAP-02 (re-enable the deferred SAML scan-window pytest),
and GAP-03 (flip the Phase 36 `wave_0_complete` flag). All three trace to a single root
cause in `quirk/dashboard/api/routes/scan.py` at lines **593–608**: the scan-window query
anchors on `MAX(scanned_at)` with a hard 1-second range filter. When endpoints from a
single logical scan land with different `scanned_at` timestamps (legacy data, retries,
re-scans, or any case Phase 24's `session_start` plumbing did not eliminate),
SAML/DNSSEC endpoints stamped earlier than Kerberos are silently excluded from the
response — `identity_findings[]` returns empty for SAML/OIDC.

**Important correction to phase context:** the phase brief describes the test as
`skip`/`xfail`, but it is currently **a hard FAIL** (not skipped). The full pytest
suite shows `2 failed, 661 passed, 7 skipped` — the SAML scan-window test fails with
`AssertionError: 'SAML' not found in {'KERBEROS'}`. This means GAP-02 is not "remove a
skip marker" — it is "make the failing test pass."

**Important correction for GAP-03:** the file `36-VALIDATION.md` **does not currently
exist on disk**. It was deleted along with all other historical phase artifacts in
commit `a991a69` (the v4.5 milestone-init commit). The last good content is preserved
in commit `99f48d2` (`status: approved, nyquist_compliant: true, wave_0_complete: false`).
GAP-03 must therefore restore-and-update the file, not just edit a flag.

**Primary recommendation:** redesign the scan-window query so it returns *every*
endpoint that belongs to the latest scan **session** rather than every endpoint within
a 1-second physical timestamp window. Add a regression test that pins SAML+OIDC
presence in `identity_findings[]` for both same-session and skewed-timestamp scenarios,
then restore `36-VALIDATION.md` with `wave_0_complete: true`.

---

## User Constraints (from CONTEXT.md)

No `38-CONTEXT.md` exists on disk — `/gsd-discuss-phase` was not run. Treat the
phase brief and ROADMAP entry as the constraint set:

### Locked Decisions
- **Closes:** DEF-v4.4-01 and DEF-v4.4-02 (verbatim from STATE.md `## Deferred Items`).
- **Requirements:** GAP-01, GAP-02, GAP-03 from `.planning/REQUIREMENTS.md` lines 17–19.
- **Success Criterion 4:** "Full test suite passes with no regressions (662+ tests, 0 failures)."

### Claude's Discretion
- Implementation strategy for the scan-window fix (column-based grouping, scan_id
  attribution, or a wider session-bracket window — see "Architecture Patterns").
- Whether to add new schema columns or piggy-back on an existing one (`scanned_at`
  truncated to second is the current grouping key in `/api/scans` and is the path
  of least invasiveness).
- Test layout — extend `tests/test_identity_surface.py::Issue3ScanWindowRegressionTest`
  vs. add a new file. Recommendation: extend; the test fixture is already correct.

### Deferred Ideas (OUT OF SCOPE)
- Phase 24's `session_start` plumbing changes (already shipped — do not refactor).
- GAP-04 dashboard tab work (Phase 39).
- All other v4.5 requirements (CI-*, ROBUST-*, CBOM-*, DASH-*, LAB-*, UAT-*).

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GAP-01 | User running an identity scan sees SAML/OIDC entries restored in `/api/scan/latest` `identity_findings[]` (closes DEF-v4.4-02 / ISSUE-3 from Phase 24). | Root cause located at `quirk/dashboard/api/routes/scan.py:593-608` (scan-window query). Fix scope and three implementation options documented under "Architecture Patterns". |
| GAP-02 | Deferred SAML scan-window pytest is re-enabled and passes; goes from skip/xfail to GREEN. | Test located: `tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols` (lines 464–563). Currently a HARD FAILURE, not skipped. No skip marker to remove — make it green. |
| GAP-03 | Phase 36 `wave_0_complete: false` flipped to `true` in `36-VALIDATION.md`; matrix shows `nyquist_compliant: true, wave_0_complete: true`. | File deleted in commit `a991a69`. Last good content in commit `99f48d2`. Must be restored and updated. Hygiene test `tests/test_hygiene.py::CodeHygieneTests::test_all_completed_phase_validations_nyquist_compliant` is a **separate** failure unrelated to Phase 36 (covers phases 01–14 only). |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Scan session attribution | API / Backend (`scan.py`) | Database (`crypto_endpoints.scanned_at`) | The bug lives in the SQL query that defines what "the latest scan" means. The fix is API-layer. |
| Identity finding derivation | API / Backend (`_derive_identity_findings`) | — | Already correct — proven by `tests/test_identity_findings_accuracy.py` (60 matches, all pass). Do not modify. |
| SAML/OIDC scanner output | Scanner (`saml_scanner.scan_saml_targets`) | Database persistence | Already correct post-Phase 24 — `session_start` parameter and unified `scanned_at` stamping work. Do not modify. |
| VALIDATION.md flag tracking | Documentation (`.planning/phases/36-*/36-VALIDATION.md`) | — | Pure docs/markdown change. |

---

## Standard Stack

### Core (already in repo — no installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (existing) | `/api/scan/latest` route | Already wired; this is where the bug lives [VERIFIED: `quirk/dashboard/api/routes/scan.py:563`]. |
| SQLAlchemy ORM | (existing) | Endpoint query | The fragile `MAX + 1-second window` is a SQLAlchemy `func.max` + `timedelta` filter [VERIFIED: lines 593-608]. |
| pytest 8.x | (existing) | Test runner | Project standard per `36-VALIDATION.md` [VERIFIED: git show 99f48d2]. |
| `fastapi.testclient.TestClient` | (existing) | API regression test driver | Used in `Issue3ScanWindowRegressionTest` [VERIFIED: lines 485-507]. |
| in-memory SQLite via `sqlite:///file::memory:?cache=shared` | (existing) | Test DB | Mirrors `tests/conftest.py` pattern [CITED: `test_identity_surface.py:491-494`]. |

### Supporting (existing, no changes expected)

- `quirk.models.CryptoEndpoint` — schema unchanged for this phase.
- `quirk.dashboard.api.schemas.IdentityFinding` / `ScanLatestResponse` — schema unchanged.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Widening the 1-second time window | Add a `scan_id` UUID column populated by `run_scan.py` | Cleaner long-term but is a schema migration — heavier than this phase warrants. **Recommend deferring** to a future scanner-robustness phase. |
| Widening the time window | Group by `strftime('%Y-%m-%d %H:%M:%S', scanned_at)` like `/api/scans` already does at line 535, then return ALL endpoints whose second-truncated timestamp matches the latest distinct second | Lower risk; matches existing pattern; but still fragile if a single scan straddles a second boundary. **Acceptable as a stop-gap.** |
| **Recommended fix:** session-bracket window | Anchor on MAX(scanned_at), then load all endpoints whose `scanned_at` is within `[MAX - SESSION_WINDOW, MAX + 1s)` where `SESSION_WINDOW` is e.g. 5 minutes (configurable) | Pragmatic; honors how scanners actually behave (sequential within minutes); Phase 24's `session_start` already keeps endpoints from the same session within microseconds, so the bracket only matters for timestamp-skewed legacy data. |

The third option above (session-bracket window) is the recommended approach: it
fixes the regression test, requires no schema migration, and degrades gracefully if
multiple scans landed within the bracket window (the more recent scan's data wins
because nothing in the bracket pre-dates the latest scan's earliest endpoint).

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        run_scan.py (CLI)                            │
│  session_start = datetime.now(timezone.utc)   [Phase 24 — works]    │
│         │                                                           │
│         ├──> kerberos_scanner.scan(..., session_start=session_start)│
│         ├──> saml_scanner.scan_saml_targets(..., session_start=...) │
│         └──> dnssec_scanner.scan(..., session_start=session_start)  │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼ each scanner stamps endpoints with
                                   session_start (tz stripped)
┌─────────────────────────────────────────────────────────────────────┐
│              quirk.db / crypto_endpoints table                      │
│   id, host, port, protocol, cert_pubkey_alg, scanned_at, ...        │
│                                                                     │
│   Same-session rows share scanned_at (modulo microseconds)          │
│   BUT legacy/retry/re-scan rows can be stamped seconds-to-minutes   │
│   apart — this is what the regression test simulates.               │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼ HTTP GET /api/scan/latest
┌─────────────────────────────────────────────────────────────────────┐
│   quirk/dashboard/api/routes/scan.py :: get_latest_scan()           │
│                                                                     │
│   Step 1 (lines 593–595):  MAX(scanned_at)  → latest_ts             │
│   Step 2 (lines 602–608):  WHERE scanned_at >= latest_ts            │
│                              AND scanned_at < latest_ts + 1s        │
│                                                                     │
│   ✗ BUG: any endpoint stamped > 1s before MAX is excluded.          │
│   When Kerberos is the slowest scanner, MAX = its timestamp         │
│   and SAML/DNSSEC at earlier `session_start` are dropped.           │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼ endpoints (subset)
┌─────────────────────────────────────────────────────────────────────┐
│   _derive_identity_findings(endpoints)   [lines 185–331 — correct]  │
│   _derive_findings(endpoints)            [lines 43–182  — correct]  │
│   _derive_motion_findings(endpoints)     [lines 334–408 — correct]  │
│   _derive_cbom(endpoints)                [lines 411–485 — correct]  │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                ScanLatestResponse(identity_findings=[...])
                  ✗ SAML/OIDC missing because their endpoints
                    were filtered out at the SQL boundary above.
```

---

## Architecture Patterns

### Pattern 1 — Session-Bracket Window (RECOMMENDED for GAP-01)

**What:** Replace the 1-second forward window with a backward bracket anchored on
`MAX(scanned_at)`. Choose a bracket large enough to cover legitimate session
duration but small enough to avoid bleeding the previous scan into the current one.

**Why:** Phase 24's `session_start` plumbing already eliminates intra-session skew
*for new scans*. The bracket only matters for legacy data and for the regression
test simulating the original failure mode. A 5-minute bracket comfortably exceeds
all observed scanner durations and remains tighter than typical re-scan cadence.

**Sketch:**
```python
# Replace lines 593-608 in quirk/dashboard/api/routes/scan.py
SESSION_BRACKET = timedelta(minutes=5)  # exposed as module constant for test override

latest_ts_raw = db.query(func.max(CryptoEndpoint.scanned_at)).scalar()
if latest_ts_raw is None:
    raise HTTPException(404, "No scan results found. Run your first scan: ...")

latest_ts = latest_ts_raw  # already a datetime

endpoints: list[CryptoEndpoint] = (
    db.query(CryptoEndpoint)
    .filter(
        CryptoEndpoint.scanned_at >= latest_ts - SESSION_BRACKET,
        CryptoEndpoint.scanned_at <= latest_ts,
    )
    .all()
)
```

**Note on `?scan_id=`** (lines 573–588): the explicit-scan_id branch keeps its
existing 1-second window — the `scan_id` is itself a second-truncated ISO
timestamp, so 1 second is correct there. Only the implicit-latest branch
(else, lines 589–608) needs the bracket fix.

### Pattern 2 — Restore 36-VALIDATION.md

**What:** Recreate the file at `.planning/phases/36-dashboard-motion-tab/36-VALIDATION.md`
using the content from git commit `99f48d2`, with two flag changes:

```diff
 ---
 phase: 36
 slug: dashboard-motion-tab
 status: approved
 nyquist_compliant: true
-wave_0_complete: false
+wave_0_complete: true
 created: 2026-04-28
 approved: 2026-04-28
+gap_closed: 2026-04-29 (Phase 38, GAP-03)
 ---
```

**Validation matrix block:** the existing rows already track DASH-04/DASH-05
green. Append a closing note referencing Phase 38 GAP-01 to explain the late
flip of `wave_0_complete`.

### Anti-Patterns to Avoid

- **Don't widen the 1-second window globally to N minutes.** This affects the
  `?scan_id=` branch too, and breaks the contract that `scan_id` identifies a
  unique second.
- **Don't add a new `scan_id` column to `crypto_endpoints`.** That is a schema
  migration — out of scope for an "S" complexity phase, and would require updating
  every scanner's INSERT path.
- **Don't try to "fix" Phase 24.** Phase 24's `session_start` plumbing is correct.
  The bug is in the API query, not the scanners.
- **Don't skip the regression test or move it to integration-only.** The test as
  written is the right test — it pins the contract. Make it pass.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Generating a new scan-session UUID | Custom UUID generation in scanners | Stay with `scanned_at`-bracket approach | Schema migration is heavier than this phase needs |
| Test client for `/api/scan/latest` | Hand-rolled `requests` calls + a live Uvicorn | `fastapi.testclient.TestClient` | Already used in `Issue3ScanWindowRegressionTest:485-507` |
| In-memory test DB | tempfile + sqlite | `sqlite:///file::memory:?cache=shared&uri=true` | Already used in tests/conftest.py and the regression test |

---

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| **Stored data** | `quirk.db` SQLite file at repo root contains real scan endpoints (`crypto_endpoints` table) with various `scanned_at` values. After fix, OLD rows become reachable again — this changes which endpoints `/api/scan/latest` returns to a developer running the dashboard locally. **Action:** none required for code; document in PR that local `quirk.db` may need a fresh `quirk --config config.yaml` if a developer was relying on the broken behavior. | Note in PR description; no code action |
| **Live service config** | None — no n8n / Datadog / external service holds state about this code path. | None — verified by absence of external service references in `scan.py` |
| **OS-registered state** | None — no Task Scheduler / launchd / pm2 entries reference this endpoint. | None |
| **Secrets / env vars** | `QUIRK_OUTPUT_DIR` is read at line 648, unrelated to the bug. | None |
| **Build artifacts** | `quirk.egg-info/` exists at repo root — installed-package metadata. Renaming or restructuring the route module would invalidate it. **No rename planned**, so no action. The compiled assets in `quirk/dashboard/static/` reference `identity_findings` (in `index-xtGSAGU6.js`) — bundle is already correct, no rebuild needed. | None — the change is internal to the SQL filter |

---

## Common Pitfalls

### Pitfall 1: Re-running pytest with a populated `quirk.db`
**What goes wrong:** Some tests use the repo-root `quirk.db` rather than an
in-memory DB and could see leakage between runs after the fix.
**Why it happens:** The bracket window pulls in older endpoints that the broken
1-second window had been hiding.
**How to avoid:** The regression test itself uses an isolated in-memory DB — but
verify that the full suite still passes by running the entire `pytest` after the
change. Already-green tests must remain green.
**Warning sign:** Any test that asserts a specific count of endpoints in
`/api/scan/latest` and was previously relying on the 1-second window to filter.

### Pitfall 2: Pre-existing hygiene-test failure is NOT in Phase 38 scope
**What goes wrong:** `tests/test_hygiene.py::test_all_completed_phase_validations_nyquist_compliant`
fails because phases 01–14 VALIDATION.md files are missing on disk (they were
deleted in commit `a991a69` to clean up before v4.5).
**Why it happens:** The list `COMPLETED_PHASES` (lines 209–224) hard-codes 14
phase slugs; all 14 files are absent.
**How to avoid:** **Do NOT solve this in Phase 38.** It is unrelated to GAP-01/02/03.
The success criterion "662+ tests, 0 failures" is unachievable until either (a)
all 14 missing VALIDATION.md files are restored from git history, or (b) the
hygiene test's `COMPLETED_PHASES` list is shortened or the test is updated to
skip-on-missing. Recommend: surface this as a blocker in the plan-checker pass
and either descope the criterion to "no NEW failures" or fold a small task into
this phase to fix the hygiene test (delete it / mark xfail / restore the 14
files). **The user must decide.**

### Pitfall 3: The phase-context wording "skip/xfail" is wrong
**What goes wrong:** Following the brief literally, you would search for a skip
marker and find none on the regression test. Wasted time.
**Why it happens:** The DEF-v4.4-02 description in STATE.md and PROJECT.md says
"deferred test"; the historical handling actually let the test FAIL hard rather
than skip it (a test in `unittest.TestCase` cannot easily be marked `xfail` like
a pytest test would).
**How to avoid:** Trust the live `pytest` output: 2 fails, 0 deferrals attributable
to SAML scan-window. Treat GAP-02 as "make this hard-failing test green," not
"remove a marker."

### Pitfall 4: Hidden second consumer of `identity_findings`
**What goes wrong:** Frontend at `src/dashboard/src/pages/identity.tsx:65`
reads `data.identity_findings`. If you change schema (don't), the frontend must
follow. **In-scope change keeps schema constant** — this pitfall is a *do-not*.

### Pitfall 5: Bracket window too wide
**What goes wrong:** A 1-hour bracket would bleed yesterday's scan into today's.
**How to avoid:** Use 5 minutes; expose as a module-level constant so the
regression test can override it if needed. Document the chosen value.

---

## Code Examples

### Example 1: The current broken query (file:line)

```python
# quirk/dashboard/api/routes/scan.py:593-608  [VERIFIED in source]
latest_ts_str = db.query(
    func.strftime("%Y-%m-%d %H:%M:%S", func.max(CryptoEndpoint.scanned_at))
).scalar()
if latest_ts_str is None:
    raise HTTPException(status_code=404, detail="No scan results found. ...")
latest_ts = datetime.fromisoformat(latest_ts_str)
endpoints: list[CryptoEndpoint] = (
    db.query(CryptoEndpoint)
    .filter(
        CryptoEndpoint.scanned_at >= latest_ts,
        CryptoEndpoint.scanned_at < latest_ts + timedelta(seconds=1),
    )
    .all()
)
```

### Example 2: The failing regression test (file:line)

```python
# tests/test_identity_surface.py:464-563  [VERIFIED in source]
class Issue3ScanWindowRegressionTest(unittest.TestCase):
    def test_issue3_scan_window_returns_all_identity_protocols(self):
        # ... seeds DNSSEC + SAML at early_ts (12:00:00),
        # ... seeds Kerberos at late_ts (12:00:30, +30s)
        # ... GETs /api/scan/latest
        # asserts {KERBEROS, SAML, DNSSEC} ⊆ identity_protocols
        # CURRENT BEHAVIOR: AssertionError, 'SAML' not found in {'KERBEROS'}
```

### Example 3: SAML scanner already accepts session_start (file:line)

```python
# quirk/scanner/saml_scanner.py:369-380  [VERIFIED in source]
def scan_saml_targets(targets: list, timeout: int = 10, logger=None,
                      session_start=None) -> list:
    ...
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    # All endpoints in this call use `now` for scanned_at
```

This confirms the scanner side is already correct — fix is purely in the API query.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-scanner `datetime.now()` at endpoint creation time | Shared `session_start` from `run_scan.py` passed to all 3 identity scanners | Phase 24 (2026-04-24) | Eliminates intra-session skew for new scans, but the API query still uses 1s window — Phase 38 closes the remaining gap |
| 1-second forward window from MAX(scanned_at) | 5-minute backward bracket from MAX(scanned_at) | Phase 38 (this phase) | Fixes ISSUE-3 / DEF-v4.4-02 |

**Deprecated/outdated:** None — no library version churn relevant to this phase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A 5-minute session-bracket window is wide enough to never bleed two scans together in normal QU.I.R.K. usage. | Architecture Patterns / Pattern 1 | A user running back-to-back scans within 5 minutes would see merged data. **Mitigation:** make the bracket configurable; document the trade. **[ASSUMED]** |
| A2 | The hygiene-test failure for phases 01–14 is NOT a Phase 38 responsibility. | Pitfall 2 | If the user expects "0 failures" literally, plan must include a hygiene-test fix or restore-14-files task. **Recommend confirming with user before planning.** **[ASSUMED]** |
| A3 | No production deployment depends on the broken behavior (e.g., older scans being hidden). | Runtime State Inventory | Local `quirk.db` files may show different `/api/scan/latest` output after the fix. **[ASSUMED]** |
| A4 | The `?scan_id=` branch (lines 573–588) is correct and should not be modified. | Pattern 1 note | If users rely on `?scan_id=` returning the *exact* second's endpoints only, the bracket logic must stay scoped to the implicit-latest branch. **Recommend pinning with a separate test.** **[CITED: source code]** |

---

## Open Questions

1. **Should Phase 38 also fix the failing `test_all_completed_phase_validations_nyquist_compliant` hygiene test?**
   - What we know: it currently fails (14 phases worth of VALIDATION.md missing on disk after `a991a69` cleanup).
   - What's unclear: whether the user wants this folded into Phase 38 (so success criterion 4 is achievable) or treated as separate tech debt.
   - Recommendation: surface in `/gsd-discuss-phase`. Default — descope success criterion 4 to "no new failures attributable to GAP-01/02/03 changes." Alternative — add a small task to either restore the 14 VALIDATION.md files from git history, or update the test's `COMPLETED_PHASES` list / convert it to skip-on-missing.

2. **What bracket window value (`SESSION_BRACKET`)?**
   - What we know: scanners run sequentially; total scan duration in the chaos lab is well under 60s for current targets.
   - What's unclear: real-world enterprise scan durations.
   - Recommendation: 5 minutes (`timedelta(minutes=5)`) — covers worst-case sequential scanner timeouts (Kerberos default 10s × N targets, plus DNSSEC and SAML) by an order of magnitude, and is much shorter than typical re-scan cadence. Make it a module-level constant so it is testable and tunable.

3. **Should the bracket fix carry a config knob (e.g., `QUIRK_SCAN_WINDOW_SECONDS`)?**
   - Recommendation: not in this phase. Hardcode the constant; revisit in Phase 41 (CI Stability & Scanner Robustness).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All work | ✓ | local | — |
| pytest | Test execution | ✓ | 8.x | — |
| FastAPI + TestClient | Regression test | ✓ (existing in test) | — | — |
| SQLAlchemy | Query rewrite | ✓ (existing) | — | — |
| SimpleSAMLphp chaos lab profile | Success criterion 1 | ✓ on disk under `quantum-chaos-enterprise-lab/` | — | The unit test simulates the failure mode without needing live Docker |
| Docker (for live SimpleSAMLphp scan) | Manual UAT only | unverified | — | Skip live UAT; the regression test is sufficient for automated verification |

**No blocking dependencies.** All work is automatable in pytest.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (project standard) |
| Config file | `pyproject.toml` + `tests/conftest.py` |
| Quick run command | `pytest tests/test_identity_surface.py -x` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| GAP-01 | `/api/scan/latest` returns SAML+OIDC entries in `identity_findings[]` even when Kerberos endpoints are stamped 30s later | unit (FastAPI TestClient + in-memory SQLite) | `pytest tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols -x` | ✅ exists, currently FAIL |
| GAP-01 | `/api/scan/latest` returns SAML+OIDC when DNSSEC stamped 60s earlier than SAML | unit (NEW — extend the regression class) | `pytest tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_saml_visible_with_earlier_dnssec -x` | ❌ Wave 0 |
| GAP-01 | `?scan_id=<exact-second>` still uses the original 1-second window (regression guard for the explicit branch) | unit (NEW) | `pytest tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_explicit_scan_id_uses_exact_second -x` | ❌ Wave 0 |
| GAP-02 | The deferred test goes from FAIL to GREEN (same test as GAP-01 row 1) | unit | (same command) | ✅ exists, currently FAIL |
| GAP-03 | `36-VALIDATION.md` exists with `nyquist_compliant: true, wave_0_complete: true` | docs / static | `python -c "import re,pathlib;p=pathlib.Path('.planning/phases/36-dashboard-motion-tab/36-VALIDATION.md');assert p.exists();c=p.read_text();assert re.search(r'nyquist_compliant\\s*:\\s*true',c) and re.search(r'wave_0_complete\\s*:\\s*true',c)"` | ❌ Wave 0 (recreate from git history) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_identity_surface.py -x` (~1s)
- **Per wave merge:** `pytest -x` (~7-8s, currently 663 selected)
- **Phase gate:** Full suite GREEN; Phase 36 VALIDATION.md restored & flag-flipped

### Wave 0 Gaps
- [ ] `tests/test_identity_surface.py` — extend `Issue3ScanWindowRegressionTest` with at least one additional assertion case (e.g., DNSSEC earlier than SAML; explicit `?scan_id=` still narrowly scoped). Reuse the existing in-memory-SQLite + TestClient harness.
- [ ] `.planning/phases/36-dashboard-motion-tab/36-VALIDATION.md` — restore from git commit `99f48d2` and update flags.
- *(No new fixtures required — the regression class is self-contained.)*

---

## Security Domain

Phase 38 is a **read-path query correctness fix**. STRIDE relevance:

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | (no auth surface change) |
| V3 Session Management | no | (no session change) |
| V4 Access Control | no | (`/api/scan/latest` is unauthenticated by design — local dashboard) |
| V5 Input Validation | partial | `?scan_id=` is already validated with `datetime.fromisoformat` and HTTP 400 on bad input; do not weaken. |
| V6 Cryptography | no | (no crypto code touched) |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Time-window query bypass / silent data exclusion | Information Disclosure (negative — missing data) | The fix itself addresses the security-adjacent posture issue: a consultant reading `/api/scan/latest` was being told the IdP had no findings when the scanner had detected weak SAML signing. **Phase 38's fix is itself a security improvement.** |
| Bracket too wide leaks prior scans | Information Disclosure | Constrain `SESSION_BRACKET` to 5 min and make it a single source of truth |

No new auth, crypto, or sensitive-data handling — `security_enforcement` impact is
purely positive (corrects an under-reporting bug).

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Bracket window introduces a new test failure in another file that was implicitly relying on the 1-second window to hide older endpoints | Low | Medium | Run full pytest after the fix; specifically inspect `tests/test_dashboard_api.py` and any test that asserts `total_endpoints` on `/api/scan/latest`. |
| R2 | The pre-existing `test_all_completed_phase_validations_nyquist_compliant` failure makes "662+ tests, 0 failures" success criterion unachievable | High | High (blocks phase close) | Surface in `/gsd-discuss-phase`. Either descope SC4 or add a planning task to fix the 14 missing VALIDATION.md files. |
| R3 | 36-VALIDATION.md restoration drifts from current matrix accuracy | Low | Low | Use `git show 99f48d2` as base; update `wave_0_complete` and add a note tying flip to GAP-01 closure. |
| R4 | Frontend or TypeScript types break | Very low | Low | Schema is unchanged; `identity_findings: IdentityFinding[]` already declared at `src/dashboard/src/types/api.ts:125` and consumed at `src/dashboard/src/pages/identity.tsx:65`. |
| R5 | The regression test still fails after the fix because of an unrelated derivation bug | Low | Medium | The derivation logic (`_derive_identity_findings`, lines 185–331) is independently covered by `tests/test_identity_findings_accuracy.py` (currently green) — confirms scope is the SQL boundary, not the derivation. |

---

## Recommended Task Ordering for the Planner

This is a small ("S" complexity) phase. Suggested layout:

1. **Wave 0 — Test scaffolding + docs prep**
   - 38-01 — Extend `Issue3ScanWindowRegressionTest` with two additional assertions (DNSSEC-earlier-than-SAML; explicit `?scan_id=` retains 1-second scope). Confirm all three assertions FAIL on master (RED).
   - 38-02 — Restore `.planning/phases/36-dashboard-motion-tab/36-VALIDATION.md` from `git show 99f48d2`. Do NOT yet flip `wave_0_complete: true`.

2. **Wave 1 — GREEN fix**
   - 38-03 — Modify `quirk/dashboard/api/routes/scan.py` lines 589–608: introduce `SESSION_BRACKET = timedelta(minutes=5)` module constant; replace forward 1-second window with backward bracket on the implicit-latest branch only; leave the `?scan_id=` branch unchanged. Re-run regression class — all three assertions pass.
   - 38-04 — Run full `pytest`. Confirm no test regressed (excluding the pre-existing hygiene failure noted in R2).

3. **Wave 2 — Phase 36 flip + close-out**
   - 38-05 — Flip `wave_0_complete: true` in `36-VALIDATION.md` and add gap-closure note linking to Phase 38 GAP-01.
   - 38-06 — **Mandatory phase completion steps from CLAUDE.md:**
     - Create `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-38-Identity-API-Regression-Fix.md`
     - Update `docs/UAT-SERIES.md` (add UAT-38-01 covering the regression scenario; bump dates).
     - Sync `docs/UAT-SERIES.md` to vault.
     - Commit `docs/UAT-SERIES.md` via gsd-tools.cjs.

4. **(Optional, gated by R2 user decision)** — Add 38-07 to fix
   `test_all_completed_phase_validations_nyquist_compliant`. Two viable approaches:
   restore the 14 missing VALIDATION.md files from git history, OR shorten the
   `COMPLETED_PHASES` list to only phases that still have VALIDATION.md on disk (none),
   OR convert the test's "missing file" branch to a skip rather than a failure.

---

## Project Constraints (from CLAUDE.md)

These directives bind every plan in Phase 38:

- **PEP 8** for all Python changes.
- **Minimal diffs** — avoid unnecessary refactors. Only `scan.py` lines 589–608
  need to change for GAP-01.
- **Run `python -m compileall`** + relevant tests after changes.
- **If detection logic changes, update `labs/*/expected_results.md`.** Phase 38 does
  not change detection logic (the *same* SAML findings reach the response — they
  just stop being filtered out at the SQL boundary). No `expected_results.md`
  updates required.
- **Chaos Lab Maintenance rule:** Phase 38 does not change any chaos-lab profile,
  port, or service. `lab.sh`, the README, and `expected_results_*.md` need no
  updates. Document this in the phase plan to satisfy the plan-checker.
- **Mandatory Phase Completion Steps:** every plan MUST include the four mandatory
  steps from `CLAUDE.md` (Obsidian phase note, UAT-SERIES.md update, UAT-SERIES.md
  vault sync, UAT-SERIES.md commit) — see Wave 2 Task 38-06 above.

---

## Sources

### Primary (HIGH confidence)
- `quirk/dashboard/api/routes/scan.py` lines 563–728 — the buggy endpoint, `_derive_identity_findings`, schema assembly.
- `tests/test_identity_surface.py` lines 464–563 — failing regression test.
- `tests/test_identity_findings_accuracy.py` — confirms derivation logic is correct (currently green).
- `quirk/scanner/saml_scanner.py` lines 369–380 — confirms scanner side is correct (Phase 24 plumbing works).
- `quirk/dashboard/api/schemas.py` lines 82–155 — IdentityFinding model & `ScanLatestResponse`.
- `git show 99f48d2:.planning/phases/36-dashboard-motion-tab/36-VALIDATION.md` — last-known-good 36-VALIDATION.md content.
- `git log --diff-filter=D` confirms `a991a69` deleted phase artifacts.
- Live `pytest` run output: `2 failed, 661 passed, 7 skipped`.
- `.planning/v4.2-MILESTONE-AUDIT.md` lines 22–166 — origin of ISSUE-3, exact failure mode.
- `.planning/REQUIREMENTS.md` lines 17–19 — GAP-01/02/03 wording.
- `.planning/STATE.md` lines 100–106 — DEF-v4.4-01 / DEF-v4.4-02 status.
- `.planning/MILESTONES.md` lines 8–25 — closure expectations.

### Secondary (MEDIUM)
- `.planning/RETROSPECTIVE.md` lines 115–138 — Phase 23/24 history; "scan-window query is a systemic integration test."

### Tertiary (LOW)
- None — all claims in this report are tied to source files at exact line numbers
  or to git commits (citable and verifiable).

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library is already in the repo and verified by source-code grep.
- Architecture: HIGH — root cause traced to a specific 16-line block; fix sketch validated against the failing test's assertions.
- Pitfalls: HIGH — pre-existing hygiene-test failure verified by live pytest run; phase-context "skip/xfail" wording corrected against actual `pytest` output.

**Research date:** 2026-04-29
**Valid until:** 2026-05-13 (14 days — codebase is stable, no major churn expected before Phase 38 plan/execute)

---

## RESEARCH COMPLETE
