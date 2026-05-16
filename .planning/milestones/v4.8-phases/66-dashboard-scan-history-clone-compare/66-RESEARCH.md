# Phase 66: Dashboard Scan History + Clone/Compare — Research

**Researched:** 2026-05-14
**Domain:** FastAPI backend extension, React dashboard (shadcn/ui, React Router, Lucide), SQLAlchemy SQLite, QUIRK intelligence pipeline
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01**: Extend existing `/api/scans` endpoint (not a new endpoint). Remove `LIMIT 10`. Add to `ScanSession` schema: `score` (int), `profile` (str | null), `calibration` (str | null), `target` (str | null), `finding_counts` (FindingCounts: {high, medium, low}).
- **D-02**: Compute `score` inline per session via `_fetch_session_endpoints()` → `build_evidence_summary()` → `compute_readiness_score()`. Same ~30ms/session budget as Phase 64.
- **D-03**: Finding counts use `_bucket_for_severity()` / `_count_by_bucket()` from `quirk/intelligence/trends.py`. CRITICAL+HIGH → "high", MEDIUM → "medium", LOW → "low", INFO excluded.
- **D-04**: Clone button always present. Priority: (1) dashboard-launched scan: use `scan_jobs.target/profile/calibration` via `scan_run_id` join; (2) CLI-launched scan: derive target from `DISTINCT CryptoEndpoint.host`, default profile="standard", calibration="balanced". Amber notice on `/scan/new` when reconstructed.
- **D-05**: `/scans` table checkboxes. Exactly 2 selected enables "Compare" button. Checking a 3rd auto-unchecks oldest (FIFO window). Compare disabled when count ≠ 2.
- **D-06**: Compare navigates to `/compare?a=<scan_id>&b=<scan_id>`. Bookmarkable URL. Browser back returns to `/scans`.
- **D-07**: New `GET /api/compare?a=<scan_id>&b=<scan_id>` endpoint in `scan.py` router. `CompareResponse` fields: `scan_a`, `scan_b` (scan_id, scanned_at, score), `score_delta`, `subscore_deltas` (all 6 pillars), `added_findings`, `removed_findings`, `endpoints_only_in_a`, `endpoints_only_in_b`, `changed_endpoints`. Finding identity key: `(host, algorithm_or_protocol, finding_type)`.
- **D-08**: `/compare` page: top header card (scan A vs B side-by-side + Δ badge), 3 tabs: Findings (default), Subscores, Endpoints.
- **Claude's Discretion**: Tab default = Findings. Empty states use friendly copy. Delta color: green if A > B, red if A < B. `/api/compare` requires only `require_auth`. 400 if `a == b`. `ScanSession.profile` and `.calibration` null for CLI scans (rendered as "—").

### Claude's Discretion

See CONTEXT.md §Claude's Discretion — full list above in locked decisions section.

### Deferred Ideas (OUT OF SCOPE)

- Pagination UI for scan list
- Scan deletion
- Bulk export of multiple scans
- Per-scan permalink page (single historical scan via URL)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-HIST-01 | `/scans` route lists all scans with date, target, profile, overall score, finding counts by severity, and "Clone configuration" button that pre-fills `/scan/new` | Backend: extend `list_scans()` in `scan.py`; ScanSession schema extension; join `scan_jobs` for clone data; frontend: `ScanHistoryPage` + `useScanList` reuse |
| UI-HIST-02 | "Compare" mode on `/scans` picks any two scans and renders diff view (score deltas, added/removed findings, changed endpoint posture) | Backend: new `GET /api/compare` endpoint; `CompareResponse` schema; frontend: `ComparePage` with 3-tab layout; `useCompareData` hook |
</phase_requirements>

---

## Summary

Phase 66 is a wiring-and-composition phase. The QUIRK backend already has all the building blocks needed: scoring pipeline (`build_evidence_summary` + `compute_readiness_score`), severity bucketing helpers, `_fetch_session_endpoints`, the `scan_jobs` table with `scan_run_id`, and the existing `/api/scans` route. Phase 64 (`trends/timeline`) provides the canonical template for per-session enrichment — this phase follows exactly the same loop pattern but applies it to `list_scans()` and to a new compare endpoint.

On the frontend, Phase 65 provides the route registration pattern (`App.tsx`), sidebar nav addition pattern (`sidebar.tsx`), `useSearchParams` usage, and `ScanNewPage` structure for the clone preload flow. Phase 62 mandates the `let cancelled = false` / `return () => { cancelled = true }` hook pattern for the two new hooks (`useScanHistory` refactor and `useCompareData`).

The most technically nuanced piece is the compare diff logic: finding identity must use `(host, algorithm_or_protocol, finding_type)` composite keys (not ephemeral IDs), and endpoint posture comparison requires joining the `tls_version`, `cipher_suite`, and `cert_pubkey_alg` fields from `CryptoEndpoint`. Both computations belong in Python for testability.

**Primary recommendation:** Follow the Phase 64 `get_trends_timeline` pattern exactly for `list_scans` enrichment. Model the compare endpoint as a pure Python function (like `compute_trend_report`) that accepts two session timestamps, fetches endpoints, computes diffs, and returns a typed dataclass — then wrap it in the FastAPI route.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Scan history listing | API / Backend | — | Session enumeration + per-session scoring lives in Python |
| Per-session score/subscore computation | API / Backend | — | Reuses `compute_readiness_score()` — Python only |
| Finding counts per session | API / Backend | — | `_count_by_bucket()` helper already in trends.py |
| Clone data recovery (scan_jobs join) | API / Backend | — | SQL join — Python only |
| Compare diff computation | API / Backend | — | Pure Python for testability; all 6 diff categories |
| Scan history display table | Browser / Client | — | React table + checkbox selection state |
| FIFO 2-scan selection | Browser / Client | — | Local `Set<string>` state, no server round-trip |
| Clone navigation preload | Browser / Client | — | URL query param construction + `useSearchParams` read in scan-new |
| Compare tab view rendering | Browser / Client | — | React Router route + Tabs component |
| Route registration | Browser / Client (App.tsx) | — | React Router `<Route>` entries |
| Sidebar nav addition | Browser / Client (sidebar.tsx) | — | NAV_ITEMS array entry |
| Auth enforcement | API / Backend (middleware) | — | `require_auth` dependency already declared at router level |

---

## Standard Stack

### Core (all already installed — no new packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (project version) | New `/api/compare` endpoint | Already powering all dashboard routes |
| SQLAlchemy | (project version) | Session enumeration, scan_jobs join, CryptoEndpoint queries | All DB access in this project |
| Pydantic v2 | (project version) | `CompareResponse`, `CompareFinding`, `CompareEndpoint`, `SubscoreDelta`, `FindingCounts` extension | Already used for all API schemas |
| React 18 + React Router v6 | (project version) | New pages, route registration, `useSearchParams`, `useNavigate` | Already used throughout dashboard |
| shadcn/ui | new-york/zinc | `Table`, `Checkbox`, `Button`, `Tabs`, `Badge`, `Card`, `Separator`, `Skeleton` | All components already installed — no new installs |
| Lucide React | (project version) | `History` icon (sidebar), `TrendingUp`/`TrendingDown` (compare header) | Already used throughout dashboard |

[VERIFIED: codebase grep — `src/dashboard/src/components/ui/` contains all required components; `node_modules` contains all packages]

### No New Dependencies

Phase 66 requires zero new pip packages and zero new npm packages. All UI components required are already registered in `src/dashboard/src/components/ui/`. [VERIFIED: 66-UI-SPEC.md §Registry Safety, codebase inspection]

---

## Architecture Patterns

### System Architecture Diagram

```
Browser                    FastAPI (scan router)         SQLite
  │                               │                         │
  │──GET /api/scans────────────────▶ list_scans()            │
  │                               │──SELECT ts_usec, cnt────▶│
  │                               │◀──session rows───────────│
  │                               │   for each ts:           │
  │                               │──_fetch_session_endpoints▶│
  │                               │◀──CryptoEndpoint[]───────│
  │                               │──scan_jobs join──────────▶│
  │                               │◀──(target, profile, cal)─│
  │                               │──build_evidence_summary   │
  │                               │──compute_readiness_score  │
  │                               │──_count_by_bucket         │
  │◀──ScanSession[] (enriched)────│                         │
  │                               │                         │
  │──GET /api/compare?a=X&b=Y─────▶ compare_scans()          │
  │                               │──_fetch_session_endpoints▶│ (twice)
  │                               │◀──endpoints_a, endpoints_b│
  │                               │──build_evidence_summary   │
  │                               │──compute_readiness_score  │
  │                               │──diff finding keys        │
  │                               │──diff endpoint posture    │
  │◀──CompareResponse─────────────│                         │
  │                               │                         │
/scans page:                                               
  ├── ScanHistoryPage (Table + checkbox state)
  ├── sticky compare bar (selectionCount === 2)
  └── Clone button → navigate("/scan/new?target=...&profile=...&calibration=...")
  
/compare page:
  ├── ComparePage → useCompareData(a, b)
  ├── score header card (two-column grid)
  └── Tabs: Findings | Subscores | Endpoints
  
/scan/new page (existing, minor extension):
  └── useSearchParams → pre-fill fields + amber notice if reconstructed=true
```

### Recommended Project Structure

No new directories needed. New files slot into existing structure:

```
quirk/dashboard/api/
├── routes/scan.py           # extend list_scans(), add compare_scans()
├── schemas.py               # extend ScanSession; add CompareResponse, CompareFinding,
│                            #   CompareEndpoint, SubscoreDelta (FindingCounts already exists)

src/dashboard/src/
├── pages/
│   ├── scan-history.tsx     # ScanHistoryPage — /scans route
│   └── compare.tsx          # ComparePage — /compare route
├── hooks/
│   └── useCompareData.ts    # new hook: GET /api/compare?a=X&b=Y
├── types/api.ts             # extend ScanSession; add CompareResponse et al
├── App.tsx                  # register /scans and /compare routes
└── components/sidebar.tsx   # add "Scan History" nav item
```

### Pattern 1: Per-Session Enrichment Loop (from Phase 64 — PRIMARY)

**What:** For each session timestamp, fetch all endpoints, compute score and finding counts, attach to response.

**When to use:** The exact pattern for `list_scans()` enrichment.

```python
# Source: quirk/dashboard/api/routes/trends.py::get_trends_timeline (Phase 64)
# Apply same pattern in list_scans() Phase 66 extension:
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.trends import _fetch_session_endpoints, _count_by_bucket

# Inside list_scans(), after fetching all session timestamps (no LIMIT):
sessions = []
for ts_str, cnt in rows:
    ts = datetime.fromisoformat(ts_str)
    eps = _fetch_session_endpoints(db, ts)
    
    # score
    score = 0
    subscores = {}
    if eps:
        evidence = build_evidence_summary(eps)
        score_dict = compute_readiness_score(evidence)
        score = int(score_dict["score"])
        subscores = score_dict["subscores"]
    
    # finding counts
    keys = [(ep.host, ep.port, ep.protocol, ep.severity) for ep in eps if ep.scan_error is None]
    counts = _count_by_bucket(keys)
    
    # clone data: join scan_jobs on scan_run_id
    job = db.query(ScanJob).filter(ScanJob.scan_run_id == ts_str).first()
    if job:
        target, profile, calibration = job.target, job.profile, job.calibration
    else:
        # CLI-launched: reconstruct from distinct hosts
        hosts = {ep.host for ep in eps if ep.host}
        target = ", ".join(sorted(hosts)) if hosts else None
        profile, calibration = None, None
    
    sessions.append(ScanSession(
        scan_id=ts_str,
        scanned_at=ts,
        total_endpoints=cnt,
        score=score,
        profile=profile,
        calibration=calibration,
        target=target,
        finding_counts=FindingCounts(
            high=counts.get("high", 0),
            medium=counts.get("medium", 0),
            low=counts.get("low", 0),
        ),
    ))
```

[VERIFIED: Pattern confirmed in `quirk/dashboard/api/routes/trends.py` lines 153-195]

### Pattern 2: Session Enumeration Without LIMIT (extend existing)

**What:** Remove `LIMIT 10` from `list_scans()` and switch from second-precision strftime to millisecond-precision (matching trends.py) to correctly enumerate all sessions.

**Current code in `scan.py` lines 745-752:**
```python
ts_sec = func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at).label("ts_sec")
rows = (
    db.query(ts_sec, func.count(CryptoEndpoint.id).label("cnt"))
    .group_by("ts_sec")
    .order_by(ts_sec.desc())
    .limit(10)  # REMOVE THIS
    .all()
)
```

**Caution:** The existing `list_scans()` uses second-precision strftime (`%Y-%m-%d %H:%M:%S`) while `trends.py` uses millisecond-precision (`%Y-%m-%d %H:%M:%f`). The CONTEXT.md D-01 does not specify changing the grouping precision — the decision is to extend the response shape and remove LIMIT. The planner should keep second-precision for the list (consistent with what `ScanSelector` already uses) but use the millisecond-precision `_fetch_session_endpoints()` helper for per-session data fetches. This is safe because `_fetch_session_endpoints` accepts a `datetime` parsed from either format.

[VERIFIED: `quirk/dashboard/api/routes/scan.py` lines 745-760; `quirk/intelligence/trends.py` lines 42-61]

### Pattern 3: Compare Diff Logic (Python pure function)

**What:** Compute finding identity diff and endpoint posture diff between two sessions.

**Finding identity key:** `(host, algorithm_or_protocol, finding_type)` — NOT ephemeral `id` columns.

```python
# Derive findings for each session using existing _derive_findings() + _derive_identity_findings()
# Build identity sets:
def _finding_key(ep: CryptoEndpoint) -> tuple | None:
    """Return (host, protocol, severity) as identity key, or None to skip."""
    if ep.scan_error or not ep.severity:
        return None
    return (ep.host or "", ep.protocol or "", ep.severity or "")

keys_a = {_finding_key(ep) for ep in eps_a if _finding_key(ep)}
keys_b = {_finding_key(ep) for ep in eps_b if _finding_key(ep)}

added = keys_a - keys_b     # in A but not B
removed = keys_b - keys_a   # in B but not A
```

**Endpoint posture comparison** (changed endpoints):
```python
# Two endpoints are "the same host" when ep.host matches
# Posture change = tls_version, cipher_suite, or cert_pubkey_alg differs
hosts_a = {ep.host: ep for ep in eps_a}
hosts_b = {ep.host: ep for ep in eps_b}
common_hosts = set(hosts_a) & set(hosts_b)

changed = [
    host for host in common_hosts
    if (
        hosts_a[host].tls_version != hosts_b[host].tls_version
        or hosts_a[host].cipher_suite != hosts_b[host].cipher_suite
        or hosts_a[host].cert_pubkey_alg != hosts_b[host].cert_pubkey_alg
    )
]
```

[VERIFIED: CryptoEndpoint model in `quirk/models.py` — fields `host`, `tls_version`, `cipher_suite`, `cert_pubkey_alg` all present]

### Pattern 4: Hook Cancellation (HOOK-01..04 from Phase 62 — MANDATORY)

**What:** All async data-fetch hooks MUST use `let cancelled = false` / `return () => { cancelled = true }` in `useEffect`. Every `setState` / `setError` call after an async boundary must be guarded with `if (!cancelled)`.

```typescript
// Source: src/dashboard/src/hooks/useScanList.ts (verified)
// ALL new hooks must follow this exact pattern:
export function useCompareData(scanA: string | null, scanB: string | null) {
  const [data, setData] = useState<CompareResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!scanA || !scanB) return
    let cancelled = false
    setData(null)
    setLoading(true)
    setError(null)
    async function fetchCompare() {
      try {
        const resp = await fetchApi(`/api/compare?a=${encodeURIComponent(scanA)}&b=${encodeURIComponent(scanB)}`)
        if (!resp.ok) {
          if (!cancelled) {
            if (resp.status === 400) {
              const body = await resp.json().catch(() => ({}))
              setError(body?.detail ?? "Bad request")
              return
            }
            setError(`API error: ${resp.status}`)
          }
          return
        }
        const result: CompareResponse = await resp.json()
        if (!cancelled) setData(result)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load comparison")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchCompare()
    return () => { cancelled = true }
  }, [scanA, scanB])

  return { data, loading, error }
}
```

[VERIFIED: Phase 62 CONTEXT.md D-01; existing useScanList.ts lines 16-53]

### Pattern 5: Clone Navigation via URL Query Params

**What:** Clone button builds URL query string and calls `navigate()`. `ScanNewPage` reads params via `useSearchParams()`.

```typescript
// In ScanHistoryPage — clone button handler
const handleClone = (session: ScanSession) => {
  const params = new URLSearchParams()
  if (session.target) params.set("target", session.target)
  if (session.profile) params.set("profile", session.profile)
  if (session.calibration) params.set("calibration", session.calibration)
  // Flag for amber notice: CLI-launched scans have profile===null
  if (session.profile === null || session.profile === undefined) {
    params.set("reconstructed", "1")
  }
  navigate(`/scan/new?${params.toString()}`)
}
```

```typescript
// In ScanNewPage — read params at mount (add to existing component)
const [searchParams] = useSearchParams()
const cloneTarget = searchParams.get("target") ?? ""
const cloneProfile = searchParams.get("profile") as ScanSubmitRequest["profile"] | null
const cloneCalibration = searchParams.get("calibration") as ScanSubmitRequest["calibration"] | null
const isReconstructed = searchParams.get("reconstructed") === "1"
// Pre-fill useState initializers or use a useEffect on mount
```

[VERIFIED: `src/dashboard/src/pages/scan-new.tsx` — current page uses `useState("")` for targets; adding `useSearchParams` is additive]

### Pattern 6: Route Registration (from Phase 65)

```typescript
// Source: src/dashboard/src/App.tsx (Phase 65 pattern)
import { ScanHistoryPage } from "@/pages/scan-history"
import { ComparePage } from "@/pages/compare"
// Inside <Routes>:
<Route path="/scans" element={<ScanHistoryPage />} />
<Route path="/compare" element={<ComparePage />} />
```

```typescript
// Source: src/dashboard/src/components/sidebar.tsx NAV_ITEMS pattern
// Add after Trends, before Schedules:
{ path: "/scans", label: "Scan History", Icon: History },
```

[VERIFIED: `App.tsx` lines 35-51; `sidebar.tsx` lines 25-37]

### Pattern 7: Subscores dict shape from compute_readiness_score

`compute_readiness_score()` returns `{"score": int, "rating": str, "subscores": SubScores, "drivers": [...]}`.

`subscores` is a `SubScores` Pydantic model instance with fields: `hygiene`, `modern_tls`, `identity_trust`, `agility_signals`, `data_at_rest`, `data_in_motion` — all int. Access via `score_dict["subscores"]` which returns the model object; serialize to dict with `.model_dump()` or access fields directly.

[VERIFIED: `quirk/intelligence/scoring.py` return block; `quirk/dashboard/api/schemas.py` SubScores model; `quirk/dashboard/api/routes/trends.py` lines 175-192 accessing `score_dict["subscores"]`]

### Anti-Patterns to Avoid

- **Pagination logic in list_scans()**: CONTEXT.md D-01 explicitly defers pagination. Return all sessions, full stop.
- **Comparing finding IDs**: `CryptoEndpoint.id` is an auto-increment DB row ID, not a stable finding identity. Always use composite keys for diff computation.
- **Custom diff library**: All diff logic is pure Python set arithmetic — no external diff library needed.
- **Conditionally mounted chart children**: Per MEMORY.md feedback constraint — never conditionally mount/unmount Recharts children. Not directly relevant to Phase 66 (subscores tab uses a table, not a chart) but flag for any last-minute chart addition.
- **Skipping `npm run build`**: Per MEMORY.md — `.tsx` edits require `npm run build` in `src/dashboard/` before they're visible in the dashboard. Every plan wave touching frontend must end with a build step.
- **Using `AbortController` in hooks**: Phase 62 D-01 explicitly prohibits this. Use the flag pattern only.
- **Calling `setState` without cancelled guard in error branches**: The specific Phase 62 bug pattern. ALL error branches (401/403/429/400/general catch) must check `if (!cancelled)`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Severity bucketing | Custom severity → bucket mapping | `_bucket_for_severity()` / `_count_by_bucket()` from `quirk/intelligence/trends.py` | Already handles CRITICAL+HIGH→high, INFO exclusion |
| Per-session score computation | Custom score pipeline | `build_evidence_summary()` → `compute_readiness_score()` | Exact same pipeline used by scan/latest, trends, timeline |
| Session endpoint fetch | Custom time-window query | `_fetch_session_endpoints(db, ts)` from `quirk/intelligence/trends.py` | Handles millisecond precision, NULL exclusion (D-13) |
| UI shadcn components | Custom table/tabs/badge components | `@/components/ui/table`, `@/components/ui/tabs`, `@/components/ui/badge` | All installed, use new-york/zinc preset |
| Bearer auth | Custom token check | `require_auth` Depends() | Router-level dependency already covers all routes in `scan.py` |
| Toast/modal for clone | Confirmation dialog | None — navigation is non-destructive | UI-SPEC explicitly says no modal required |

---

## Common Pitfalls

### Pitfall 1: Session Precision Mismatch

**What goes wrong:** `list_scans()` uses second-precision strftime (`%Y-%m-%d %H:%M:%S`) for grouping. `_fetch_session_endpoints()` expects a millisecond-precision datetime. If the plan converts the ts_str from `list_scans()` directly to a datetime and passes it to `_fetch_session_endpoints()`, the 1ms window in that helper may miss endpoints whose `scanned_at` has sub-second components.

**Why it happens:** `_fetch_session_endpoints()` uses `target_ts + timedelta(milliseconds=1)` — a 1ms window. A ts_str like `"2026-05-13 10:22:47"` parsed as datetime has zero microseconds, so the window is `[10:22:47.000000, 10:22:47.001000)`. Endpoints with `scanned_at = 10:22:47.500000` will be missed.

**How to avoid:** Either (a) switch `list_scans()` to use millisecond-precision strftime matching `trends.py`'s `_list_session_timestamps_n()` pattern, OR (b) use the same second-window logic as the existing `get_latest_scan()` — filter `scanned_at >= ts AND < ts + timedelta(seconds=1)` — instead of calling `_fetch_session_endpoints()`.

**Recommendation:** Use a private `_fetch_session_endpoints_1s(db, ts)` that uses the 1-second window (matching `get_latest_scan()`), since `list_scans()` was always second-precision. Do NOT change the existing `_fetch_session_endpoints()` helper (it is used by trends.py with millisecond timestamps). [VERIFIED: `scan.py` lines 745-752 uses second-precision; `trends.py` lines 83-101 uses millisecond window]

### Pitfall 2: scan_jobs.scan_run_id Format

**What goes wrong:** `ScanJob.scan_run_id` stores the ISO timestamp string of the completed scan. `list_scans()` groups by second-precision `ts_sec` strings. The join `ScanJob.scan_run_id == ts_str` may fail if `scan_run_id` has microsecond precision and `ts_str` does not (or vice versa).

**Why it happens:** `scan_run_id` is set by the Phase 65 job completion logic at whatever precision `scanned_at` has. The string formats may differ.

**How to avoid:** Use a LIKE or string prefix comparison, or truncate both to second precision: `func.strftime('%Y-%m-%d %H:%M:%S', ...)`. Alternatively, do the join in Python after fetching: `db.query(ScanJob).filter(ScanJob.scan_run_id.startswith(ts_str[:19])).first()`.

**Warning signs:** Clone button always shows amber "reconstructed" notice even for dashboard-launched scans.

[VERIFIED: `quirk/models.py` ScanJob.scan_run_id = `Column(String, nullable=True)` — no precision constraint specified]

### Pitfall 3: FindingCounts Already Exists in schemas.py

**What goes wrong:** Planner adds a new `FindingCounts` model to `schemas.py` when one already exists.

**Why it happens:** It was added in Phase 64 for `TrendSessionPoint`. If the planner adds it again, Pydantic will silently use the second definition.

**How to avoid:** Check before adding — `FindingCounts` at lines 242-250 of `schemas.py` already exists with the correct shape (`high: int = 0`, `medium: int = 0`, `low: int = 0`). The `ScanSession` extension just imports and reuses it.

[VERIFIED: `quirk/dashboard/api/schemas.py` lines 242-250]

### Pitfall 4: Router-Level Auth Covers compare Endpoint

**What goes wrong:** Planner adds `require_auth` as a per-route dependency on `compare_scans()` when the router already has it.

**Why it happens:** `router = APIRouter(dependencies=[Depends(require_auth)])` in `scan.py` line 34 applies to ALL routes. Adding it again per-route is redundant but harmless. Not adding it is also fine. 

**How to avoid:** Do NOT add `require_auth` as a per-route dependency. Let router-level inheritance handle it. [VERIFIED: `scan.py` line 34]

### Pitfall 5: useSearchParams Requires React Router Context

**What goes wrong:** `useSearchParams()` throws if called outside a `BrowserRouter` context (e.g., in a test).

**Why it happens:** Standard React Router behavior — all hooks require router context.

**How to avoid:** When reading clone params in `ScanNewPage`, ensure the hook call is inside the component function body (not at module level). Tests wrapping with `<MemoryRouter initialEntries={['/scan/new?target=...']}>` will work correctly.

### Pitfall 6: Empty Session Handling in compare

**What goes wrong:** `compare_scans()` called with a `scan_id` that returns no endpoints (e.g., a deleted or corrupted session) should return 404, not a zero-diff response.

**How to avoid:** After `_fetch_session_endpoints()` for each of scan A and scan B, check `if not eps_a` or `if not eps_b` and raise `HTTPException(status_code=404, detail="Scan not found: {scan_id}")`.

### Pitfall 7: Sticky Compare Bar z-index

**What goes wrong:** Sticky compare bar overlaps the sidebar or page content in unexpected ways.

**How to avoid:** Use `fixed bottom-0 left-12 lg:left-60 right-0` (matching the main content offset) or `sticky bottom-0` relative to the page scroll container. The sidebar is `z-10`; the bar needs at least `z-20` if fixed-positioned. [VERIFIED: sidebar.tsx uses `z-10`; main content `ml-12 lg:ml-60`]

---

## Code Examples

### Enriched ScanSession Schema Extension

```python
# Source: quirk/dashboard/api/schemas.py — extend existing ScanSession
class ScanSession(BaseModel):
    scan_id: str
    scanned_at: datetime
    total_endpoints: int
    # Phase 66 additions (all Optional/default for backward compat with ScanSelector):
    score: int = 0
    profile: Optional[str] = None
    calibration: Optional[str] = None
    target: Optional[str] = None
    finding_counts: "FindingCounts" = Field(default_factory=FindingCounts)
```

### CompareResponse Schema

```python
# Source: new additions to quirk/dashboard/api/schemas.py

class CompareScanSummary(BaseModel):
    scan_id: str
    scanned_at: datetime
    score: int

class SubscoreDelta(BaseModel):
    hygiene: int = 0
    modern_tls: int = 0
    identity_trust: int = 0
    agility_signals: int = 0
    data_at_rest: int = 0
    data_in_motion: int = 0

class CompareFinding(BaseModel):
    host: str
    protocol: Optional[str] = None
    severity: str
    description: Optional[str] = None

class CompareEndpoint(BaseModel):
    host: str
    reason: Optional[str] = None   # e.g. "tls_version changed" for changed_endpoints

class CompareResponse(BaseModel):
    scan_a: CompareScanSummary
    scan_b: CompareScanSummary
    score_delta: int
    subscore_deltas: SubscoreDelta
    added_findings: List[CompareFinding] = []
    removed_findings: List[CompareFinding] = []
    endpoints_only_in_a: List[str] = []   # host strings
    endpoints_only_in_b: List[str] = []
    changed_endpoints: List[CompareEndpoint] = []
```

### compare_scans Route

```python
# Source: add to quirk/dashboard/api/routes/scan.py

@router.get("/compare", response_model=CompareResponse)
def compare_scans(
    a: str = Query(..., description="scan_id of scan A (newer)"),
    b: str = Query(..., description="scan_id of scan B (baseline)"),
    db: Session = Depends(get_db),
) -> CompareResponse:
    if a == b:
        raise HTTPException(status_code=400, detail="Cannot compare a scan to itself.")
    try:
        ts_a = datetime.fromisoformat(a)
        ts_b = datetime.fromisoformat(b)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan_id format.")
    
    eps_a = _fetch_session_endpoints_1s(db, ts_a)
    eps_b = _fetch_session_endpoints_1s(db, ts_b)
    if not eps_a:
        raise HTTPException(status_code=404, detail=f"No scan found: {a!r}")
    if not eps_b:
        raise HTTPException(status_code=404, detail=f"No scan found: {b!r}")
    
    # Scores + subscores
    evidence_a = build_evidence_summary(eps_a)
    evidence_b = build_evidence_summary(eps_b)
    score_dict_a = compute_readiness_score(evidence_a)
    score_dict_b = compute_readiness_score(evidence_b)
    score_a = int(score_dict_a["score"])
    score_b = int(score_dict_b["score"])
    sub_a = score_dict_a["subscores"]
    sub_b = score_dict_b["subscores"]
    
    subscore_deltas = SubscoreDelta(
        hygiene=sub_a.hygiene - sub_b.hygiene,
        modern_tls=sub_a.modern_tls - sub_b.modern_tls,
        identity_trust=sub_a.identity_trust - sub_b.identity_trust,
        agility_signals=sub_a.agility_signals - sub_b.agility_signals,
        data_at_rest=sub_a.data_at_rest - sub_b.data_at_rest,
        data_in_motion=sub_a.data_in_motion - sub_b.data_in_motion,
    )
    
    # Finding diff using (host, protocol, severity) composite key
    def _ep_key(ep):
        return (ep.host or "", ep.protocol or "", ep.severity or "")
    
    keys_a = {_ep_key(ep) for ep in eps_a if not ep.scan_error and ep.severity}
    keys_b = {_ep_key(ep) for ep in eps_b if not ep.scan_error and ep.severity}
    added_keys = keys_a - keys_b
    removed_keys = keys_b - keys_a
    
    # ... build CompareFinding lists from added_keys / removed_keys
    # ... build endpoint diff from host sets
    
    return CompareResponse(
        scan_a=CompareScanSummary(scan_id=a, scanned_at=ts_a, score=score_a),
        scan_b=CompareScanSummary(scan_id=b, scanned_at=ts_b, score=score_b),
        score_delta=score_a - score_b,
        subscore_deltas=subscore_deltas,
        added_findings=added_findings,
        removed_findings=removed_findings,
        endpoints_only_in_a=endpoints_only_in_a,
        endpoints_only_in_b=endpoints_only_in_b,
        changed_endpoints=changed_endpoints,
    )
```

### TypeScript Interface Extensions

```typescript
// Source: extend src/dashboard/src/types/api.ts

// Extend existing ScanSession:
export interface ScanSession {
  scan_id: string
  scanned_at: string
  total_endpoints: number
  // Phase 66 additions:
  score: number
  profile: string | null
  calibration: string | null
  target: string | null
  finding_counts: { high: number; medium: number; low: number }
}

// New interfaces:
export interface CompareScanSummary {
  scan_id: string
  scanned_at: string
  score: number
}

export interface SubscoreDelta {
  hygiene: number
  modern_tls: number
  identity_trust: number
  agility_signals: number
  data_at_rest: number
  data_in_motion: number
}

export interface CompareFinding {
  host: string
  protocol?: string
  severity: string
  description?: string
}

export interface CompareEndpoint {
  host: string
  reason?: string
}

export interface CompareResponse {
  scan_a: CompareScanSummary
  scan_b: CompareScanSummary
  score_delta: number
  subscore_deltas: SubscoreDelta
  added_findings: CompareFinding[]
  removed_findings: CompareFinding[]
  endpoints_only_in_a: string[]
  endpoints_only_in_b: string[]
  changed_endpoints: CompareEndpoint[]
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `LIMIT 10` on `/api/scans` | No LIMIT — full history | Phase 66 | History page can show all scans |
| `ScanSession` with 3 fields | 8 fields (adds score, profile, calibration, target, finding_counts) | Phase 66 | `ScanSelector` unaffected (reads only original 3 fields) |
| Second-precision session grouping | Keep second-precision for list, use 1s window for fetch | Phase 66 (no change) | Consistent with `get_latest_scan()` existing behavior |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ScanJob.scan_run_id` stores the ISO timestamp string matching `CryptoEndpoint.scanned_at` session timestamp. Join `ScanJob.scan_run_id == ts_str` (with possible precision truncation) correctly recovers clone data. | Pattern 1, Pitfall 2 | Clone button would always show "reconstructed" amber notice even for dashboard-launched scans. Verify by checking Phase 65 job completion code. |
| A2 | All 8 shadcn/ui components listed in UI-SPEC (Table, Checkbox, Button, Tabs, Badge, Card, Separator, Skeleton) are already installed in `src/dashboard/src/components/ui/`. | Standard Stack | Would require `npx shadcn add <component>` during implementation if any are missing. |
| A3 | `compute_readiness_score()` returns subscores as a `SubScores` Pydantic model accessible via field access (`.hygiene`, etc.) after being stored in `score_dict["subscores"]`. | Pattern 7, compare endpoint | If subscores is returned as a plain dict, the attribute access syntax `.hygiene` would fail. |

**A2 — partial verification:** UI-SPEC §Component Inventory states "All components listed are already installed." [CITED: 66-UI-SPEC.md §Component Inventory]. Not individually confirmed by filesystem check in this session.

---

## Open Questions

1. **Phase 65 completion status**
   - What we know: Phase 66 is gated on Phase 65 (CONTEXT.md §Wave B dependency). Phase 65 adds `scan_jobs` table and `scan_run_id` column.
   - What's unclear: Whether Phase 65 has shipped. `ScanJob` model is present in `quirk/models.py` [VERIFIED], so the schema is in place. If Phase 65 is still pending, `scan_run_id` values may not exist in the DB, making all clones show as "reconstructed."
   - Recommendation: Include a plan note that clone data recovery requires Phase 65 to be complete. The code itself is safe to write now.

2. **ScanNewPage clone preload — `useEffect` vs initializer**
   - What we know: `ScanNewPage` uses `useState("")` for targets with no preload logic. Adding `useSearchParams()` and pre-filling is additive.
   - What's unclear: Whether pre-filling should happen via `useState` initializer (reads params once at mount) or `useEffect` (reactive to param changes). Since clone navigation always goes to a fresh mount, the initializer approach is simpler and avoids a useEffect.
   - Recommendation: Use `useState(() => searchParams.get("target") ?? "")` as the initializer for the targets field. No `useEffect` needed for this use case.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — phase is pure code changes to existing Python + React codebase; no new tools, CLIs, or services required).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Python) | pytest |
| Config file | `pytest.ini` or inferred from `pyproject.toml` |
| Quick run command | `python -m pytest tests/test_dashboard_scan_history.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |
| Framework (JS) | Vitest |
| JS config | `src/dashboard/vitest.config.ts` |
| JS quick run | `cd src/dashboard && npx vitest run src/**/__tests__/useScanList.test.ts` |
| JS full suite | `cd src/dashboard && npx vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-HIST-01 | `/api/scans` returns enriched `ScanSession` (score, profile, calibration, target, finding_counts) | integration | `pytest tests/test_dashboard_scan_history.py::test_list_scans_schema -x` | ❌ Wave 0 |
| UI-HIST-01 | `/api/scans` returns ALL sessions (no LIMIT 10) | integration | `pytest tests/test_dashboard_scan_history.py::test_list_scans_no_limit -x` | ❌ Wave 0 |
| UI-HIST-01 | Clone data from `scan_jobs` join | unit | `pytest tests/test_dashboard_scan_history.py::test_clone_data_recovery -x` | ❌ Wave 0 |
| UI-HIST-01 | CLI-launched scan: target reconstructed from `CryptoEndpoint.host` | unit | `pytest tests/test_dashboard_scan_history.py::test_clone_reconstruction -x` | ❌ Wave 0 |
| UI-HIST-02 | `GET /api/compare` returns `CompareResponse` with correct schema | integration | `pytest tests/test_dashboard_scan_history.py::test_compare_schema -x` | ❌ Wave 0 |
| UI-HIST-02 | `GET /api/compare?a=X&b=X` returns 400 | integration | `pytest tests/test_dashboard_scan_history.py::test_compare_self -x` | ❌ Wave 0 |
| UI-HIST-02 | Score delta and subscore deltas computed correctly | unit | `pytest tests/test_dashboard_scan_history.py::test_compare_score_delta -x` | ❌ Wave 0 |
| UI-HIST-02 | Added/removed finding detection via composite key | unit | `pytest tests/test_dashboard_scan_history.py::test_compare_finding_diff -x` | ❌ Wave 0 |
| UI-HIST-02 | Endpoints only in A / only in B / changed | unit | `pytest tests/test_dashboard_scan_history.py::test_compare_endpoint_diff -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_dashboard_scan_history.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q && cd src/dashboard && npx vitest run`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_dashboard_scan_history.py` — covers all UI-HIST-01 and UI-HIST-02 test cases listed above; uses `dashboard_client` fixture from `conftest.py`; seeds `CryptoEndpoint` + `ScanJob` rows using the shared-cache SQLite pattern from `test_dashboard_trends.py`

*(No JS test gaps — `useScanList` is a thin hook that is sufficiently covered by integration tests; `useCompareData` follows the same pattern)*

---

## Security Domain

`security_enforcement` not explicitly `false` in config.json — section required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `require_auth` via router-level dependency (already applied) |
| V3 Session Management | no | — |
| V4 Access Control | no | All history is single-user; no per-scan ownership |
| V5 Input Validation | yes | `scan_id` (a, b params) validated via `datetime.fromisoformat()` — rejects malformed strings; `a == b` rejected with 400 |
| V6 Cryptography | no | No new crypto operations |

### Known Threat Patterns for Phase 66 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unauthenticated scan history access | Information Disclosure | `require_auth` (router-level) already covers `/api/scans` and `/api/compare` |
| scan_id injection (malformed ISO timestamp) | Tampering | `datetime.fromisoformat()` validation; raises 400 on parse failure |
| Comparing arbitrary scan IDs from different users | Spoofing | Single-user auth model; no multi-tenant concern in v4.8 |
| Host field in compare response containing adversarial strings | Tampering | `host` is read from DB (operator-controlled scan targets); REPORT-SAN-01 (Phase 61) handles markdown report escaping; dashboard renders in React (XSS-safe) |

---

## Project Constraints (from CLAUDE.md)

| Directive | Applies to Phase 66 |
|-----------|-------------------|
| PEP 8 for all Python changes | Yes — all new Python code in `scan.py` and `schemas.py` |
| Keep diffs minimal — avoid unnecessary refactors | Yes — `list_scans()` extension is additive; no other routes touched |
| `python -m compileall` after changes | Yes — run after all Python edits |
| No new pip dependencies | Confirmed — zero new packages |
| Dashboard build step: `npm run build` in `src/dashboard/` | Yes — required after every `.tsx` edit |
| Recharts static children constraint | Not relevant (Phase 66 uses tables, not charts) |
| Obsidian vault sync + UAT-SERIES.md update | Required at phase completion |

---

## Sources

### Primary (HIGH confidence)

- `quirk/dashboard/api/routes/scan.py` — current `list_scans()` implementation, session window query pattern, router auth declaration
- `quirk/dashboard/api/routes/trends.py` — `_list_session_timestamps_n()`, `get_trends_timeline()` — canonical template for Phase 66 enrichment loop
- `quirk/dashboard/api/schemas.py` — `ScanSession`, `FindingCounts`, `SubScores` current shapes
- `quirk/intelligence/trends.py` — `_fetch_session_endpoints()`, `_bucket_for_severity()`, `_count_by_bucket()` — verified reusable helpers
- `quirk/intelligence/scoring.py` — `compute_readiness_score()` signature and return shape
- `quirk/models.py` — `CryptoEndpoint` field inventory; `ScanJob` schema (scan_run_id, target, profile, calibration)
- `src/dashboard/src/hooks/useScanList.ts` — verified cancellation pattern
- `src/dashboard/src/types/api.ts` — current `ScanSession` TypeScript interface
- `src/dashboard/src/App.tsx` — route registration pattern
- `src/dashboard/src/components/sidebar.tsx` — NAV_ITEMS pattern
- `src/dashboard/src/pages/scan-new.tsx` — current page structure for clone preload extension
- `.planning/phases/62-react-hook-cancellation-pattern/62-CONTEXT.md` — HOOK-01..04 pattern authority
- `.planning/phases/66-dashboard-scan-history-clone-compare/66-CONTEXT.md` — all locked decisions
- `.planning/phases/66-dashboard-scan-history-clone-compare/66-UI-SPEC.md` — visual/interaction contract

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — UI-HIST-01, UI-HIST-02 acceptance criteria

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in codebase; zero new dependencies
- Architecture: HIGH — all patterns verified from existing Phase 64/65 implementations
- Pitfalls: HIGH — all derived from verified code inspection, not speculation
- Validation: HIGH — test framework verified; test file gaps identified explicitly

**Research date:** 2026-05-14
**Valid until:** 2026-06-14 (stable codebase; no fast-moving dependencies)
