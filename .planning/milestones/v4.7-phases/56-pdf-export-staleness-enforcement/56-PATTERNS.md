# Phase 56: PDF Export & Staleness Enforcement - Pattern Map

**Mapped:** 2026-05-08
**Files analyzed:** 2 (1 new, 1 modified)
**Analogs found:** 2 / 2

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/dashboard/src/hooks/useQRAMMPrintData.ts` | hook | request-response (parallel fetch) | `src/dashboard/src/hooks/useScanData.ts` | role-match (same shape; different endpoint chain) |
| `src/dashboard/src/pages/print.tsx` | component (extend) | request-response | itself — extend existing sub-component pattern | exact |

---

## Pattern Assignments

### `src/dashboard/src/hooks/useQRAMMPrintData.ts` (hook, request-response)

**Analog:** `src/dashboard/src/hooks/useScanData.ts`

**Imports pattern** (`useScanData.ts` lines 1–3):
```typescript
import { useState, useEffect } from "react"
import type { ScanLatestResponse } from "@/types/api"
import { useSelectedScan } from "@/hooks/useSelectedScan"
```

For the new hook, the import block becomes:
```typescript
import { useState, useEffect } from "react"
import type { QRAMMSessionSummary, QRAMMScoreResponse, QRAMMComplianceMapRow } from "@/types/api"
```
No context import — the hook is self-contained (CONTEXT.md D-03 explicitly forbids reusing `useQRAMMSession`).

**Return-shape interface pattern** (`useScanData.ts` lines 5–9):
```typescript
interface UseScanDataResult {
  data: ScanLatestResponse | null
  loading: boolean
  error: string | null
}
```

Mirror this exactly for `UseQRAMMPrintDataResult`:
```typescript
interface UseQRAMMPrintDataResult {
  scoreResult: QRAMMScoreResponse | null
  complianceRows: QRAMMComplianceMapRow[] | null
  loading: boolean
  error: string | null
}
```

**Cancellation guard + state init pattern** (`useScanData.ts` lines 11–16):
```typescript
export function useScanData(): UseScanDataResult {
  const { selectedScanId } = useSelectedScan()
  const [data, setData] = useState<ScanLatestResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
```

**Fetch body pattern — sequential with early return** (`useScanData.ts` lines 17–55):
```typescript
useEffect(() => {
  let cancelled = false

  async function fetchData() {
    try {
      setLoading(true)
      setError(null)
      const resp = await fetch(url)
      if (!resp.ok) {
        if (resp.status === 404) {
          setError("No scan data available. Run a scan first: quirk scan <target>")
        } else {
          setError(`API error: ${resp.status} ${resp.statusText}`)
        }
        return
      }
      const json: ScanLatestResponse = await resp.json()
      if (!cancelled) {
        setData(json)
      }
    } catch (err) {
      if (!cancelled) {
        setError(err instanceof Error ? err.message : "Failed to load scan data")
      }
    } finally {
      if (!cancelled) {
        setLoading(false)
      }
    }
  }

  fetchData()
  return () => {
    cancelled = true
  }
}, [selectedScanId])

return { data, loading, error }
```

**Adaptation for `useQRAMMPrintData`:**

The fetch chain is three-step with an intermediate filter:

1. `GET /api/qramm/sessions` → `QRAMMSessionSummary[]`
2. Find `list[i]` where `status === "scored"` (server sets `status = "scored"` on score_json persist — confirmed in `qramm.py` line 391). The first matching entry is most-recent-scored.
3. Parallel fetch: `GET /api/qramm/sessions/{id}/score` + `GET /api/qramm/sessions/{id}/compliance-map` via `Promise.all`.

When no scored session exists (`list` is empty or no entry has `status === "scored"`), set `scoreResult: null, complianceRows: null` and `loading: false` — do NOT set `error`. This is the no-session placeholder path (D-04/D-05).

Reference for session list endpoint shape (`qramm.py` lines 427–458):
- `GET /api/qramm/sessions` returns `List[SessionSummary]` ordered most-recent first.
- `SessionSummary` has `session_id`, `org_name`, `created_at`, `status`, `answers_count`.
- Status value `"scored"` is set by the score endpoint (`qramm.py` line 391).

Reference for existing session-list fetch (from `useQRAMMSession.ts` lines 28–43 — pattern only, do NOT copy the context/answer seeding):
```typescript
const listResp = await fetch("/api/qramm/sessions")
if (!listResp.ok) {
  setError(`API error: ${listResp.status} ${listResp.statusText}`)
  return
}
const list: QRAMMSessionSummary[] = await listResp.json()
if (cancelled) return

if (list.length === 0) {
  setSession(null)
  // ... (for print hook: just return with null scoreResult/complianceRows)
  return
}
const latest = list[0]
```

Score endpoint response shape (`api.ts` lines 219–224):
```typescript
export interface QRAMMScoreResponse {
  overall: number
  maturity: string
  dimensions: Record<string, { score: number; weighted: number }>
  profile_multiplier: number
}
```
Note: `dimensions` keys are `"CVI" | "SGRM" | "DPE" | "ITR"`. The `score` sub-field is the raw 0.0–4.0 dimension score (not `weighted`). This distinction matters for the radar polygon computation (divide by 4 to normalize to 0–1 for radius calculation).

Compliance-map row shape (`api.ts` lines 228–236):
```typescript
export interface QRAMMComplianceMapRow {
  practice_number: string   // e.g. "1.1-NIST_PQC"
  practice_area: string     // e.g. "1.1"
  dimension: string         // "CVI" | "SGRM" | "DPE" | "ITR"
  framework: string         // one of 8 FRAMEWORK_KEYS
  static_weight: number
  relevance_score: number | null   // null when session has no score yet
  scanner_informed: boolean
}
```
96 rows total (12 practice areas × 8 frameworks). Framework display names live in `compliance_map.py` `FRAMEWORK_DISPLAY_NAMES` dict — the hook does NOT need to know them; print.tsx maps them via a local constant mirroring that dict.

---

### `src/dashboard/src/pages/print.tsx` (component, extend)

**Analog:** itself — extend existing sub-component and CSS patterns

**PRINT_CSS extension pattern** (`print.tsx` lines 6–31):
```typescript
const PRINT_CSS = [
  "body,html{background:#fff!important;color:#0a0a0a!important;...}",
  ".print-section{break-before:page;padding-top:24px}",
  ".print-section:first-child{break-before:avoid}",
  // ... severity/qs badge classes ...
  ".badge{display:inline-block;padding:1px 6px;border-radius:4px;font-size:11px;font-weight:600}",
].join("")
```

New QRAMM entries must be appended to this array before `.join("")`. Pattern: plain CSS string, no Tailwind, no CSS variables. Badge class names follow the existing `.sev-*` / `.qs-*` convention — use `.tier-scanner` and `.tier-manual` for the coverage-tier badges (matching Phase 55 dashboard label convention):

```typescript
// Append to PRINT_CSS array:
".tier-scanner{background:#2563eb;color:#fff}",
".tier-manual{background:#71717a;color:#fff}",
".qramm-radar{display:block;margin:16px auto}",
".qramm-dim-label{font-size:11px;fill:#52525b}",
```

**`data-ready` gate pattern** (`print.tsx` lines 151–158):
```typescript
useEffect(() => {
  if (data) {
    document.body.setAttribute('data-ready', 'true')
  }
  return () => {
    document.body.removeAttribute('data-ready')
  }
}, [data])
```

This must be extended to gate on BOTH hooks resolving. Replace single `data` dependency with a combined condition:
```typescript
useEffect(() => {
  if (data && !qrammLoading) {
    document.body.setAttribute('data-ready', 'true')
  }
  return () => {
    document.body.removeAttribute('data-ready')
  }
}, [data, qrammLoading])
```
Where `qrammLoading` comes from `const { scoreResult, complianceRows, loading: qrammLoading } = useQRAMMPrintData()`.

**Sub-component shape pattern** (`print.tsx` lines 33–55 — `PrintFindings` as template):
```typescript
function PrintFindings({ findings }: { findings: FindingItem[] }) {
  if (!findings.length) return <p className="meta">No findings recorded.</p>
  return (
    <table>
      <thead><tr><th>...</th></tr></thead>
      <tbody>
        {findings.map((f, i) => (
          <tr key={i}>
            <td><span className={`badge sev-${f.severity}`}>{f.severity}</span></td>
            ...
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

`PrintQRAMM` follows the same signature: `function PrintQRAMM({ scoreResult, complianceRows }: { scoreResult: QRAMMScoreResponse | null; complianceRows: QRAMMComplianceMapRow[] | null })`.

**No-data placeholder pattern** (seen in all sub-components):
```typescript
if (!findings.length) return <p className="meta">No findings recorded.</p>
```

For `PrintQRAMM` no-session case (D-05):
```typescript
if (!scoreResult || !complianceRows) {
  return <p className="meta">No QRAMM assessment completed — run an assessment from the dashboard to populate this section.</p>
}
```

**Section insertion pattern** (`print.tsx` lines 253–258):
```tsx
{/* Section 6: Migration Roadmap */}
<div className="print-section">
  <h2>Migration Roadmap</h2>
  <PrintRoadmap nodes={roadmap.nodes} />
</div>
```

QRAMM section appended immediately after, as Section 7:
```tsx
{/* Section 7: QRAMM Governance Assessment */}
<div className="print-section">
  <h2>QRAMM Governance Assessment</h2>
  <PrintQRAMM scoreResult={scoreResult} complianceRows={complianceRows} />
</div>
```

**Inline SVG radar pattern** (no analog in codebase — from D-01 spec):

The QRAMM radar is a pure SVG element, not from recharts. Compass layout on 200×200 viewBox, center at (100, 100), radius 80. Axis endpoints:
- CVI: top → `(100, 20)`
- SGRM: right → `(180, 100)`
- DPE: bottom → `(100, 180)`
- ITR: left → `(20, 100)`

Point computation: `score / 4 * radius` along each axis vector from center. For dimension score `s` (0–4):
```typescript
const r = 80
const cx = 100, cy = 100
const pts = {
  CVI:  [cx,        cy - (scoreResult.dimensions["CVI"].score / 4) * r],
  SGRM: [cx + (scoreResult.dimensions["SGRM"].score / 4) * r, cy],
  DPE:  [cx,        cy + (scoreResult.dimensions["DPE"].score / 4) * r],
  ITR:  [cx - (scoreResult.dimensions["ITR"].score / 4) * r,  cy],
}
const polygon = Object.values(pts).map(([x, y]) => `${x},${y}`).join(" ")
```

SVG structure:
```tsx
<svg viewBox="0 0 200 200" width={200} height={200} className="qramm-radar">
  {/* Axis lines */}
  <line x1={100} y1={100} x2={100} y2={20}  stroke="#e4e4e7" strokeWidth={1} />
  <line x1={100} y1={100} x2={180} y2={100} stroke="#e4e4e7" strokeWidth={1} />
  <line x1={100} y1={100} x2={100} y2={180} stroke="#e4e4e7" strokeWidth={1} />
  <line x1={100} y1={100} x2={20}  y2={100} stroke="#e4e4e7" strokeWidth={1} />
  {/* Score polygon */}
  <polygon points={polygon} fill="#2563eb" fillOpacity={0.25} stroke="#2563eb" strokeWidth={2} />
  {/* Axis labels + scores */}
  <text x={100} y={14}  textAnchor="middle" className="qramm-dim-label">CVI</text>
  <text x={190} y={104} textAnchor="start"  className="qramm-dim-label">SGRM</text>
  <text x={100} y={196} textAnchor="middle" className="qramm-dim-label">DPE</text>
  <text x={10}  y={104} textAnchor="end"    className="qramm-dim-label">ITR</text>
</svg>
```

**Grouped rendering pattern** (`print.tsx` lines 121–146 — `PrintRoadmap`):
```typescript
const grouped: Record<string, RoadmapNode[]> = {}
for (const n of nodes) {
  const tf = n.timeframe ?? "Unknown"
  if (!grouped[tf]) grouped[tf] = []
  grouped[tf].push(n)
}
return (
  <div>
    {Object.entries(grouped).map(([tf, items]) => (
      <div key={tf} style={{ marginBottom: 16 }}>
        <h3>{tf}</h3>
        ...
      </div>
    ))}
  </div>
)
```

Use this grouping pattern for the per-framework practice detail block. Group `complianceRows` by `framework`, then iterate `FRAMEWORK_KEYS` order (from compliance_map.py) to render `<h3>` per framework followed by its practice table. Framework display names mirror `FRAMEWORK_DISPLAY_NAMES` from `compliance_map.py` — declare a local const in `print.tsx` rather than importing from Python:
```typescript
const FRAMEWORK_DISPLAY: Record<string, string> = {
  NIST_PQC: "NIST PQC Standards", NSM10: "NSM-10", CNSA2: "CNSA 2.0",
  ISO27001: "ISO 27001:2022", ETSI_QS: "ETSI Quantum-Safe",
  PCI_DSS: "PCI-DSS v4.0", CC: "Common Criteria", BSI_TR: "BSI TR-02102",
}
const FRAMEWORK_ORDER = ["NIST_PQC","NSM10","CNSA2","ISO27001","ETSI_QS","PCI_DSS","CC","BSI_TR"]
```

**monospace cell pattern** (`print.tsx` lines 77–80):
```tsx
<td style={{ fontFamily: "monospace", fontSize: 11 }}>{subjectCN}</td>
```

Use for `practice_area` column values in the compliance detail table.

---

## Shared Patterns

### Static CSS-only in print.tsx
**Source:** `src/dashboard/src/pages/print.tsx` lines 6–31
**Apply to:** All new CSS classes added in Phase 56 (`.tier-scanner`, `.tier-manual`, `.qramm-radar`, `.qramm-dim-label`)

Rule: Every CSS rule is a plain string element in the `PRINT_CSS` array. No Tailwind utility classes, no CSS custom properties (`var(--...)`), no dynamic string interpolation. The array is joined with `""` to produce a single style string injected via `createElement("style", null, PRINT_CSS)`.

### `data-ready` Gate
**Source:** `src/dashboard/src/pages/print.tsx` lines 151–158
**Apply to:** The `useEffect` in `PrintPage()` that sets `data-ready`

Both `useScanData()` and `useQRAMMPrintData()` must have `loading === false` before `data-ready` is attributed. The existing gate checks `if (data)` (truthy scan data); the extended gate checks `if (data && !qrammLoading)` so headless PDF capture waits for both data sets.

### Cancellation Guard
**Source:** `src/dashboard/src/hooks/useScanData.ts` lines 17–55
**Apply to:** `useQRAMMPrintData.ts`

The `let cancelled = false` / `if (!cancelled)` / `return () => { cancelled = true }` pattern is mandatory in all data-fetching hooks to prevent React state updates on unmounted components. Copy verbatim from `useScanData.ts`.

### Error Handling in Fetch Hooks
**Source:** `src/dashboard/src/hooks/useScanData.ts` lines 27–46
**Apply to:** `useQRAMMPrintData.ts`

```typescript
catch (err) {
  if (!cancelled) {
    setError(err instanceof Error ? err.message : "Failed to load scan data")
  }
} finally {
  if (!cancelled) {
    setLoading(false)
  }
}
```

For the QRAMM hook, replace the fallback string with `"Failed to load QRAMM data"`. The no-scored-session path is NOT an error — return `{ scoreResult: null, complianceRows: null, loading: false, error: null }` from the normal `fetchData()` flow.

### Badge Class Naming Convention
**Source:** `src/dashboard/src/pages/print.tsx` lines 17–25
**Apply to:** Coverage-tier badges in compliance summary table

Existing pattern: `.sev-CRITICAL`, `.qs-Safe`, etc. — class name encodes the category prefix + value. New QRAMM tier badges follow the same prefix pattern: `.tier-scanner` (blue, matches Phase 55 dashboard "Scanner-informed" color), `.tier-manual` (gray, matches "Manual only"). The CSS badge base class `.badge` is already defined (line 16) and applies sizing/border-radius.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| Inline SVG radar in `PrintQRAMM` | component fragment | — | No SVG polygon charts exist in codebase; recharts is not used in print.tsx (D-01). Construct from scratch per D-01 spec. |

---

## API Response Shapes (Reference for hook + component)

These are confirmed from live code — no inference needed.

**`GET /api/qramm/sessions` response item** (`qramm.py` lines 96–101, `api.ts` lines 197–203):
```typescript
{ session_id: number; org_name: string|null; created_at: string|null; status: string|null; answers_count: number }
// status === "scored" when score_json is populated (qramm.py line 391)
```

**`GET /api/qramm/sessions/{id}/score` response** (`api.ts` lines 219–224, `qramm.py` lines 382–395):
```typescript
{
  session_id: number
  overall: number          // 0–100 overall score
  maturity: string         // e.g. "Level 2 – Developing"
  dimensions: {
    CVI:  { score: number; weighted: number; practices: Record<string, number> }
    SGRM: { score: number; weighted: number; practices: Record<string, number> }
    DPE:  { score: number; weighted: number; practices: Record<string, number> }
    ITR:  { score: number; weighted: number; practices: Record<string, number> }
  }
  profile_multiplier: number
}
// IMPORTANT: use dimensions[dim].score (raw 0.0–4.0), NOT .weighted, for radar (Phase 55 RESEARCH Pitfall 2)
```

**`GET /api/qramm/sessions/{id}/compliance-map` response** (`api.ts` lines 228–236, `qramm.py` lines 575–644):
```typescript
// 96 rows, sorted by practice_area then iterated by FRAMEWORK_KEYS order
{
  practice_number: string   // "1.1-NIST_PQC"
  practice_area: string     // "1.1" .. "4.3"
  dimension: string         // "CVI"|"SGRM"|"DPE"|"ITR"
  framework: string         // one of 8 FRAMEWORK_KEYS
  static_weight: number
  relevance_score: number|null   // null if session not scored
  scanner_informed: boolean      // true only for CVI (SCANNER_COVERAGE["CVI"]=1.0)
}
```

---

## Metadata

**Analog search scope:** `src/dashboard/src/hooks/`, `src/dashboard/src/pages/`, `quirk/dashboard/api/routes/`, `quirk/qramm/`, `src/dashboard/src/types/`
**Files scanned:** 7
**Pattern extraction date:** 2026-05-08
