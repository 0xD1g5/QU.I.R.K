# Phase 31: Trend Analysis - Context

**Gathered:** 2026-04-26
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. can compare the two most recent distinct scan sessions — surfacing readiness
score delta, net-new findings (present in current session, absent in previous), and
resolved findings (present in previous session, absent in current) — with counts by
severity and top-5 sample identifiers per category.

The intelligence layer gains a new `quirk/intelligence/trends.py` module with
`compute_trend_report()`. A new `GET /api/trends` endpoint exposes the data. The React
dashboard gains a new `/trends` sidebar page (new file, new route, new nav entry).

No new SQLite table. All session grouping uses the existing `scanned_at`-based
second-truncated grouping established by `list_scans()` in `scan.py`.

</domain>

<decisions>
## Implementation Decisions

### Finding Match Key
- **D-01:** The canonical match key for comparing findings across sessions is
  `(host, port, protocol, severity)` — using exact column values from
  `CryptoEndpoint`. A finding exists in "new" if its key appears in the current
  session but not the previous; "resolved" if it appeared in the previous but not
  the current.
- **D-02:** `host` is used as-is (user-configured hostname or IP). Document the
  caveat in the trend report and API docstring: *"Trend accuracy depends on
  consistent target configuration between scans — IP-addressed targets may produce
  phantom new/resolved findings if IPs change."* This is acceptable behavior for the
  v4.3 consulting use case.
- **D-03:** Severity is deliberately included in the match key. A finding that
  changes severity (e.g., HIGH → MEDIUM after partial remediation) will appear as
  "HIGH resolved + MEDIUM new" — surfacing the improvement story for the consultant.
  This is the correct behavior.
- **D-04:** `scan_error` endpoints (rows where `scan_error IS NOT NULL`) are
  **excluded** from the finding delta. Connectivity failures are not crypto findings;
  including them would create phantom new/resolved noise when hosts are temporarily
  unreachable.
- **D-05:** Scan error count delta is surfaced **separately** alongside the finding
  delta: `scan_errors_new_count` and `scan_errors_resolved_count` — simple integers,
  no host-level detail. Tells the consultant "something changed in scan coverage"
  without cluttering the finding counts.

### Single-Session Behavior
- **D-06:** When only 1 scan session exists (no previous to compare against), `GET
  /api/trends` returns HTTP 200 with `score_delta: null`, all count fields at `0`,
  `previous_session_ts: null`, and empty sample arrays. The frontend shows a
  "Baseline scan — run another scan to see trends" empty state. No exception
  handling required in the client for the no-previous-session case.

### API Response Schema
- **D-07:** `GET /api/trends` response fields:
  - `current_session_ts` (ISO datetime) — timestamp of the session being treated as "current"
  - `previous_session_ts` (ISO datetime or null) — timestamp of the previous session (null if only 1 exists)
  - `current_score` (float or null) — readiness score of current session
  - `previous_score` (float or null) — readiness score of previous session
  - `score_delta` (float or null) — `current_score - previous_score`; null when no previous session
  - `new_high`, `new_medium`, `new_low` (int) — new finding counts by severity
  - `resolved_high`, `resolved_medium`, `resolved_low` (int) — resolved finding counts by severity
  - `scan_errors_new_count`, `scan_errors_resolved_count` (int) — error delta
  - `new_findings_sample` — top 5 new findings, each with `host`, `port`, `protocol`, `severity`
  - `resolved_findings_sample` — top 5 resolved findings, same shape
- **D-08:** `compute_trend_report()` accepts two session timestamps (current and
  previous) and the DB session, queries CryptoEndpoints for each window, applies the
  match key logic, and returns a `TrendReport` dataclass/TypedDict. The API route
  calls `list_scans()` to identify the two most recent distinct sessions, then passes
  the timestamps to `compute_trend_report()`.

### Trends Page UX
- **D-09:** New sidebar page at `/trends` — follows the exact established pattern:
  `src/dashboard/src/pages/trends.tsx`, new `<Route path="/trends">` in `App.tsx`,
  new entry in `NAV_ITEMS` array in `sidebar.tsx` with a TrendingUp icon from
  lucide-react.
- **D-10:** The Trends page layout:
  - **Header row:** "Comparing [prev_ts] → [current_ts]" (or "Baseline scan" empty state)
  - **Score delta card:** shows current score, arrow, previous score, and delta badge (color-coded: green for positive, red for negative)
  - **New findings card:** HIGH/MEDIUM/LOW counts
  - **Resolved findings card:** HIGH/MEDIUM/LOW counts
  - **Scan error delta:** compact row below the cards
  - **Two collapsible tables** (if samples exist): "New Findings (top 5)" and "Resolved Findings (top 5)", each with host / port / protocol / severity columns — using the same shadcn `Table` component pattern from `pages/findings.tsx`

### Structural / ISSUE-2/ISSUE-3 Requirements
- **D-11:** No new Python dependencies for Phase 31 — all logic uses existing SQLAlchemy
  queries and the `compute_readiness_score()` function already in `scoring.py`. No
  `pyproject.toml` diff required (no ISSUE-2 pattern triggered).
- **D-12:** `compute_trend_report()` is a pure function — accepts session timestamps and
  a DB session, returns a `TrendReport`. It does NOT call `datetime.now()` internally;
  timestamps come from the caller (ISSUE-3 spirit: no hidden time source).

### NULL Collision (Carrying Forward)
- **D-13:** NULL collision with v4.2-era scan sessions is **expected behavior** —
  document, do not fix. The `scanned_at` field may be NULL on pre-v4.3 endpoints.
  `compute_trend_report()` filters out rows where `scanned_at IS NULL` before
  session grouping. The first post-v4.3 trend report will show all DAR findings as
  "new" (they were absent from any previous session that lacked DAR columns). This is
  correct behavior — not a bug.

### Claude's Discretion
- Exact Pydantic schema class name for the API response (e.g., `TrendReportResponse`)
- Whether `compute_trend_report()` returns a dataclass or a Pydantic model
- The exact lucide-react icon for the Trends nav entry (TrendingUp recommended)
- Whether the score delta badge uses a `+` prefix for positive deltas
- Exact wording of the "Baseline scan" empty state message on the Trends page

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Session Grouping Pattern (primary reference)
- `quirk/dashboard/api/routes/scan.py:450` — `list_scans()` — second-truncated
  `strftime` grouping; this exact pattern must be reused in `compute_trend_report()`
  to ensure session boundaries are consistent with the rest of the app
- `quirk/dashboard/api/routes/scan.py:485` — `get_latest_scan()` — shows how a
  `±1 second` window query retrieves all endpoints in a session; same pattern applies
  when fetching two sessions for comparison

### Models and ORM
- `quirk/models.py` — `CryptoEndpoint` model; all fields available for match key
  and filtering (`host`, `port`, `protocol`, `severity`, `scan_error`, `scanned_at`)

### Intelligence Layer (where trends.py lives)
- `quirk/intelligence/scoring.py` — `compute_readiness_score()` function; the trends
  module calls this for both sessions to derive `current_score` and `previous_score`
- `quirk/intelligence/evidence.py` — `_collect_evidence()` pattern; if re-running
  scoring per session is expensive, check how evidence extraction works

### Frontend Page Pattern
- `src/dashboard/src/App.tsx` — route registration (copy pattern from existing routes)
- `src/dashboard/src/components/sidebar.tsx:18` — `NAV_ITEMS` array; add Trends entry
  here with lucide-react icon
- `src/dashboard/src/pages/findings.tsx` — shadcn `Table` component pattern; the
  new/resolved sample tables on the Trends page must follow this exact pattern
- `src/dashboard/src/hooks/useScanData.ts` — existing data hook; new `useTrendsData`
  hook should follow the same pattern (fetch `GET /api/trends`, handle loading/error)

### Requirements
- `.planning/REQUIREMENTS.md` §Trend Analysis — TREND-01, TREND-02, TREND-03, TREND-04
  acceptance criteria

### Prior Phase Context (DAR architecture)
- `.planning/phases/27-database-encryption-detection/27-CONTEXT.md` — D-08
  (`dar_` subscore architecture, `compute_readiness_score()` signature)
- `.planning/phases/30-hashicorp-vault-connector/30-CONTEXT.md` — most recent scanner
  context; confirms `compute_readiness_score()` signature unchanged through Phase 30

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scan.py:list_scans()` — second-truncated session grouping; reuse the exact
  `func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at)` pattern in
  `compute_trend_report()` to derive the two session timestamps
- `scoring.py:compute_readiness_score()` — call once per session (current and
  previous) to derive the score delta; accepts an endpoint list, returns a float
- `findings.tsx` — `Table`, `TableBody`, `TableHeader`, `TableRow`, `TableCell`
  from shadcn `@/components/ui/table`; `SEVERITY_STYLES` badge map; copy for
  new/resolved sample tables on Trends page

### Established Patterns
- All pages follow: `pages/<name>.tsx` + `Route` in `App.tsx` + `NAV_ITEMS` entry
  in `sidebar.tsx` with a lucide-react icon — no deviation from this pattern
- All API routes live in `quirk/dashboard/api/routes/`; Phase 31 adds `GET /api/trends`
  either to `scan.py` or a new `trends.py` route file (Claude's discretion — `scan.py`
  already has `list_scans()` which trends.py depends on, so colocating is reasonable)
- `useScanData` hook in `src/dashboard/src/hooks/` — pattern for `useTrendsData`
- TDD RED+GREEN: Plan 01 = RED scaffold (empty `compute_trend_report()` + failing tests),
  Plan 02 = GREEN intelligence + API endpoint, Plan 03 = React Trends page + docs

### Integration Points
- `quirk/intelligence/trends.py` — new module; `compute_trend_report(current_ts, previous_ts, db)` → `TrendReport`
- `quirk/dashboard/api/routes/scan.py` (or new `trends.py`) — `GET /api/trends` route
- `src/dashboard/src/pages/trends.tsx` — new page component
- `src/dashboard/src/App.tsx` — add `/trends` route
- `src/dashboard/src/components/sidebar.tsx` — add Trends to `NAV_ITEMS`

</code_context>

<specifics>
## Specific Ideas

- The score delta badge: green text with `▲ +X.X pts` for positive, red with `▼ -X.X pts`
  for negative, neutral for zero delta. Mirrors the visual language of the executive score gauge.
- Session timestamps on the Trends page should be human-readable (e.g., "Apr 26, 09:00")
  not raw ISO strings — format with `toLocaleString()` or a date-fns helper.
- "Baseline scan" empty state (no previous session): a centered card with a clock or
  TrendingUp icon, subtitle "Run another scan to see your progress over time."
- The collapsible tables for top-5 samples: use a `<details>`/`<summary>` HTML element
  or a shadcn `Collapsible` component — consistent with the low-JS approach of other pages.

</specifics>

<deferred>
## Deferred Ideas

- **Historical time-series charts** — The user asked about building charts based on
  remediation scans over time. This would require persisting trend snapshots across
  many sessions (not just comparing the two most recent). The timestamp fields added in
  Phase 31 (`current_session_ts`, `previous_session_ts`) lay the groundwork. Defer to
  a future phase (v4.4 candidate) that introduces a `trend_snapshots` table and a
  multi-session chart view.
- **Full new/resolved finding lists** — Phase 31 returns top-5 samples. A future phase
  could paginate the full new/resolved set and link directly to the Findings tab
  filtered to those endpoints.
- **Per-scanner-type trend breakdown** — Score delta by surface (TLS, identity, DAR)
  rather than aggregate-only. Deferred — requires subscore history, not just total score.

</deferred>

---

*Phase: 31-trend-analysis*
*Context gathered: 2026-04-26*
