# Phase 36: Dashboard Motion Tab — Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 9 (1 NEW page, 5 MODIFIED source, 1 MODIFIED test, 1 MODIFIED docs, 1 NEW vault note)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| NEW `src/dashboard/src/pages/motion.tsx` | page component (React) | request-response (consumes JSON, renders tables) | `src/dashboard/src/pages/identity.tsx` | exact |
| MOD `src/dashboard/src/components/sidebar.tsx` | nav component | static config | self (existing `NAV_ITEMS`) | in-place |
| MOD `src/dashboard/src/App.tsx` | route registry | static config | self (existing `<Routes>` block) | in-place |
| MOD `src/dashboard/src/types/api.ts` | TS interface module | type contract | self (existing `IdentityFinding`, `SubScores`, `ScanLatestResponse`) | in-place |
| MOD `src/dashboard/src/pages/executive.tsx` | page component | data display | self (existing 5-gauge flex-wrap row) | in-place |
| MOD `quirk/dashboard/api/schemas.py` | Pydantic response model | type contract | `IdentityFinding` model in same file | exact |
| MOD `quirk/dashboard/api/routes/scan.py` | FastAPI route + derivation | request-response | `_derive_identity_findings` in same file | exact |
| MOD `tests/test_dashboard_api.py` | pytest contract test | unit / TestClient | existing `test_findings_endpoint` / `test_score_endpoint` | exact |
| MOD `docs/UAT-SERIES.md` | manual UAT documentation | docs | existing UAT-35-NN block | in-place |
| NEW `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-36-Dashboard-Motion-Tab.md` | Obsidian phase note | docs | `Phase-35-CBOM-Integration.md` | exact |

---

## Pattern Assignments

### NEW `src/dashboard/src/pages/motion.tsx` (page, request-response)

**Analog:** `src/dashboard/src/pages/identity.tsx` (entire file, 240 lines)

**Imports pattern** (identity.tsx lines 1-21) — copy verbatim, swap `IdentityFinding` for `MotionFinding`:
```tsx
import { useState, useMemo } from "react"
import {
  useReactTable, getCoreRowModel, getSortedRowModel, getFilteredRowModel,
  getPaginationRowModel, flexRender, type ColumnDef, type SortingState,
} from "@tanstack/react-table"
import { useScanData } from "@/hooks/useScanData"
import type { MotionFinding } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
```

**Severity styling pattern** (identity.tsx lines 23-29) — copy verbatim:
```tsx
const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH:     "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM:   "bg-[hsl(38_92%_50%)] text-black",
  LOW:      "bg-[hsl(213_94%_68%)] text-black",
  INFO:     "bg-[hsl(240_5%_46%)] text-white",
}
```

**Loading + error pattern** (identity.tsx lines 99-100):
```tsx
if (loading) return <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) =>
  <Skeleton key={i} className="h-10 w-full" />)}</div>
if (error) return <p className="text-muted-foreground text-sm">{error}</p>
```

**Page heading + section structure** (identity.tsx lines 102-104) — heading style locked at 20px/600:
```tsx
<div className="space-y-6">
  <h1 style={{ fontSize: 20, fontWeight: 600 }}>Data in Motion</h1>
  ...
</div>
```

**Per-protocol summary card pattern** (identity.tsx lines 107-131) — adapt for broker subsection headers (Family · N endpoints · M plaintext):
```tsx
<Card key={family}>
  <CardHeader className="pb-2">
    <CardTitle className="text-sm font-medium text-muted-foreground">
      {family}
    </CardTitle>
  </CardHeader>
  <CardContent>
    <div className="flex items-center justify-between">
      <span className="text-2xl font-bold">{count}</span>
      <Badge className={`${STATUS_BADGE_STYLES[label] ?? ""} text-xs`}>{label}</Badge>
    </div>
  </CardContent>
</Card>
```

**TanStack Table pattern** (identity.tsx lines 86-97, 154-188) — reuse exact `useReactTable` config and the table render block (cursor-pointer rows, `hover:bg-accent/5`, sortable headers via `onClick={h.column.getToggleSortingHandler()}`).

**Sheet detail drawer** (identity.tsx lines 192-237) — Claude's discretion per CONTEXT D-01; include only if ≤30 LOC. Width locked at 480px.

**Data filtering** — mirror identity.tsx line 64-66:
```tsx
const motionFindings = useMemo(() => data?.motion_findings ?? [], [data])
const emailFindings = useMemo(() => motionFindings.filter(f => isEmailProtocol(f.protocol)), [motionFindings])
const brokerFindings = useMemo(() => motionFindings.filter(f => getBrokerFamily(f.protocol ?? "") !== null), [motionFindings])
```

---

### MOD `src/dashboard/src/components/sidebar.tsx` (nav config, in-place)

**Analog:** self — existing `NAV_ITEMS` at lines 19-27.

**Add icon to lucide imports** (extend lines 5-13):
```tsx
import {
  LayoutDashboard, AlertTriangle, Shield, Database, GitBranch,
  Fingerprint, TrendingUp, Activity,   // NEW — UI-SPEC chose `Activity`
} from "lucide-react"
```

**Insert NAV_ITEMS row** (lines 19-27) — between Identity and Certificates per CONTEXT D-01:
```tsx
const NAV_ITEMS = [
  { path: "/", label: "Executive Summary", Icon: LayoutDashboard },
  { path: "/findings", label: "Findings", Icon: AlertTriangle },
  { path: "/identity", label: "Identity", Icon: Fingerprint },
  { path: "/motion", label: "Motion", Icon: Activity },          // NEW
  { path: "/certificates", label: "Certificates", Icon: Shield },
  { path: "/cbom", label: "CBOM Viewer", Icon: Database },
  { path: "/roadmap", label: "Migration Roadmap", Icon: GitBranch },
  { path: "/trends", label: "Trends", Icon: TrendingUp },
]
```

No other changes — `min-h-[44px]`, Tooltip wrapper, active-link styling all carry forward unchanged.

---

### MOD `src/dashboard/src/App.tsx` (route, in-place)

**Analog:** self — existing `<Routes>` block at lines 27-36.

**Pattern** — flat sibling `<Route>` elements (Pitfall 4: react-router-dom v7 has no `<Outlet />` here, do not introduce nested routes):
```tsx
import { MotionPage } from "@/pages/motion"   // NEW import — alongside lines 7-13
...
<Routes>
  <Route path="/" element={<ExecutivePage />} />
  <Route path="/findings" element={<FindingsPage />} />
  <Route path="/identity" element={<IdentityPage />} />
  <Route path="/motion" element={<MotionPage />} />     {/* NEW — between identity and certificates */}
  <Route path="/certificates" element={<CertificatesPage />} />
  ...
</Routes>
```

---

### MOD `src/dashboard/src/types/api.ts` (TS contract, in-place)

**Analog:** self — `IdentityFinding` at lines 80-91, `SubScores` at lines 1-7, `ScanLatestResponse` at lines 99-108.

**Extend `SubScores`** (lines 1-7):
```ts
export interface SubScores {
  hygiene: number
  modern_tls: number
  identity_trust: number
  agility_signals: number
  data_at_rest: number
  data_in_motion: number     // NEW — Phase 36 D-06
}
```

**Add `MotionFinding`** (mirror IdentityFinding shape at lines 80-91):
```ts
export interface MotionFinding {
  host: string
  port: number
  severity: string
  title: string
  protocol?: string
  description?: string
  remediation?: string
  quantum_risk?: string
  source?: string
  tls_version?: string
  cipher_suite?: string
  cert_not_after?: string         // ISO date
  plaintext_exposed: boolean      // NON-OPTIONAL per D-02
  starttls_warning: boolean       // NON-OPTIONAL per D-02
}
```

**Extend `ScanLatestResponse`** (lines 99-108):
```ts
export interface ScanLatestResponse {
  // ... unchanged ...
  identity_findings: IdentityFinding[]
  motion_findings: MotionFinding[]   // NEW — defaults to [] from server
}
```

---

### MOD `src/dashboard/src/pages/executive.tsx` (gauge row, in-place)

**Analog:** self — flex-wrap gauge row at lines 128-151.

**Add 6th gauge** (after line 150):
```tsx
<ScoreGauge score={score.subscores.data_at_rest} label="Data at Rest" size={120} />
<ScoreGauge score={score.subscores.data_in_motion} label="Data in Motion" size={120} />  {/* NEW */}
```

**Update loading skeleton count** (lines 60-67) — change `length: 5` → `length: 6`:
```tsx
{Array.from({ length: 6 }).map((_, i) => (
  <Skeleton key={i} className="h-32 w-32 rounded-full" />
))}
```

The `flex flex-wrap justify-around gap-8` container at line 128 already accommodates 6 gauges — no layout change needed.

---

### MOD `quirk/dashboard/api/schemas.py` (Pydantic, in-place)

**Analog:** `IdentityFinding` at lines 80-90 (same file).

**Extend `SubScores`** (lines 20-25):
```python
class SubScores(BaseModel):
    hygiene: int
    modern_tls: int
    identity_trust: int
    agility_signals: int
    data_at_rest: int = 0
    data_in_motion: int = 0   # NEW — Phase 36 D-06
```

**Add `MotionFinding` model** (mirror IdentityFinding pattern at lines 80-90):
```python
class MotionFinding(BaseModel):
    host: str
    port: int
    severity: str
    title: str
    protocol: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None
    source: Optional[str] = None
    tls_version: Optional[str] = None
    cipher_suite: Optional[str] = None
    cert_not_after: Optional[str] = None    # ISO string (NOT datetime — UI displays directly)
    plaintext_exposed: bool = False         # NON-OPTIONAL per D-02
    starttls_warning: bool = False          # NON-OPTIONAL per D-02
```

**Extend `ScanLatestResponse`** (lines 123-131):
```python
class ScanLatestResponse(BaseModel):
    ...
    identity_findings: List[IdentityFinding] = []
    motion_findings: List[MotionFinding] = []   # NEW
```

---

### MOD `quirk/dashboard/api/routes/scan.py` (FastAPI route + derivation, in-place)

**Analog:** `_derive_identity_findings` at lines 184-330 (same file).

**Pattern: derivation function** — mirror `_derive_identity_findings` structure (per-protocol branches, sorted by severity at the end). Add `_derive_motion_findings` directly below `_derive_identity_findings` (after line 330):

```python
def _derive_motion_findings(endpoints: list[CryptoEndpoint]) -> list[MotionFinding]:
    """Synthesize motion findings from email + broker CryptoEndpoints.

    Mirrors _derive_identity_findings (lines 184-330). Carries protocol labels
    verbatim — does NOT normalize "AMQPS/Azure-ServiceBus" (Phase 35 D-03).
    """
    EMAIL_PROTOS = {"SMTP-STARTTLS", "SMTPS", "IMAP-STARTTLS", "IMAPS",
                    "POP3-STARTTLS", "POP3S"}
    BROKER_PLAIN = {"KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN"}
    BROKER_TLS = {"KAFKA-TLS", "AMQPS", "AMQPS/Azure-ServiceBus",
                  "HTTPS/AWS-SQS", "REDIS-TLS"}
    MOTION_PROTOS = EMAIL_PROTOS | BROKER_PLAIN | BROKER_TLS

    results: list[MotionFinding] = []
    for ep in endpoints:
        proto = ep.protocol or ""
        if proto not in MOTION_PROTOS:
            continue
        plaintext = proto in BROKER_PLAIN
        starttls_warning = (ep.port == 25 and proto == "SMTP-STARTTLS")
        # severity rules per RESEARCH.md §"Pattern 2":
        #   plaintext broker → HIGH (mirrors risk_engine.py:539-559)
        #   port-25 STARTTLS → MEDIUM (EMAIL-08)
        #   TLS_legacy (TLSv1/1.1) → HIGH
        #   else → LOW/INFO (presence-only)
        # Use getattr() pattern (Pitfall 5) for cipher_suite / cert_not_after.
        results.append(MotionFinding(
            host=ep.host, port=ep.port,
            severity=...,        # planner derives per rules
            title=...,
            protocol=proto,      # verbatim, preserve "AMQPS/Azure-ServiceBus"
            tls_version=getattr(ep, "tls_version", None) or None,
            cipher_suite=getattr(ep, "cipher_suite", None) or None,
            cert_not_after=ep.cert_not_after.isoformat() if getattr(ep, "cert_not_after", None) else None,
            quantum_risk=...,
            plaintext_exposed=plaintext,
            starttls_warning=starttls_warning,
            source="motion",
        ))
    _severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    results.sort(key=lambda f: _severity_order.get(f.severity, 99))
    return results
```

**CRITICAL — Pitfall 1 fix at lines 595-601:** the existing `SubScores(...)` constructor silently drops `data_in_motion`. The same task that extends Pydantic `SubScores` MUST also extend this constructor:

**Current (lines 595-601):**
```python
subscores=SubScores(
    hygiene=subscores_raw.get("hygiene", 0),
    modern_tls=subscores_raw.get("modern_tls", 0),
    identity_trust=subscores_raw.get("identity_trust", 0),
    agility_signals=subscores_raw.get("agility_signals", 0),
    data_at_rest=subscores_raw.get("data_at_rest", 0),
),
```

**Required:**
```python
subscores=SubScores(
    hygiene=subscores_raw.get("hygiene", 0),
    modern_tls=subscores_raw.get("modern_tls", 0),
    identity_trust=subscores_raw.get("identity_trust", 0),
    agility_signals=subscores_raw.get("agility_signals", 0),
    data_at_rest=subscores_raw.get("data_at_rest", 0),
    data_in_motion=subscores_raw.get("data_in_motion", 0),   # NEW — fixes silent drop
),
```

**Wire motion_findings into response build** (lines 633-647) — mirror the `identity_findings=identity_findings` line:
```python
return ScanLatestResponse(
    meta=ScanMeta(...),
    score=score,
    confidence=confidence,
    findings=findings,
    certificates=certificates,
    cbom_components=cbom_components,
    roadmap=roadmap,
    identity_findings=identity_findings,
    motion_findings=_derive_motion_findings(endpoints),   # NEW
)
```

---

### MOD `tests/test_dashboard_api.py` (pytest unit, in-place)

**Analog:** existing `test_score_endpoint` (lines 35-44) and `test_findings_endpoint` (lines 47-54) — same file.

**Test pattern** — reuse `dashboard_client` fixture from `tests/conftest.py:75`; tolerate empty DB with `(200, 404)`:
```python
def test_motion_findings_endpoint(dashboard_client):
    """DASH-05: GET /api/scan/latest includes motion_findings list."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "motion_findings" in data
        assert isinstance(data["motion_findings"], list)


def test_data_in_motion_subscore(dashboard_client):
    """DASH-04: GET /api/scan/latest returns subscores.data_in_motion as int."""
    resp = dashboard_client.get("/api/scan/latest")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "data_in_motion" in data["score"]["subscores"]
        assert isinstance(data["score"]["subscores"]["data_in_motion"], int)
```

Plus three direct-call unit tests on `_derive_motion_findings` (no client) per RESEARCH.md §"Phase Requirements → Test Map":
- `test_derive_motion_findings_plaintext` — KAFKA-PLAIN endpoint → severity HIGH
- `test_derive_motion_findings_starttls` — port 25 SMTP-STARTTLS → `starttls_warning=True`; port 587 SMTP-STARTTLS → False
- `test_derive_motion_findings_azure` — `AMQPS/Azure-ServiceBus` slash preserved verbatim in output

---

### MOD `docs/UAT-SERIES.md` (manual UAT docs, in-place)

**Analog:** existing UAT-35-NN block (added in Phase 35 close-out).

Add 5 new cases UAT-36-01..05 per CONTEXT D-11:
- UAT-36-01: `/motion` route loads, both sections render
- UAT-36-02: port-25 STARTTLS warning badge renders against `labs/email/`
- UAT-36-03: plaintext broker shows `☠ PLAINTEXT` badge against `labs/broker/`
- UAT-36-04: executive summary shows 6 ScoreGauges including Data in Motion
- UAT-36-05: empty-state cards render when scanner profiles are off

Update `**Last Updated:**` header date to phase-completion date.

---

### NEW `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-36-Dashboard-Motion-Tab.md` (Obsidian phase note)

**Analog:** `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-35-CBOM-Integration.md` (60+ lines).

**Frontmatter pattern** (Phase-35 lines 1-7):
```yaml
---
project: QU.I.R.K.
type: phase
status: complete         # active during phase, complete at end
source: .planning/phases/36-dashboard-motion-tab/
updated: 2026-04-28
---
```

**Section structure** (Phase-35 lines 9-57):
1. `# Phase 36: Dashboard Motion Tab`
2. `## Goal` — one paragraph
3. `## Requirements Covered` — DASH-01..DASH-05 bullet list
4. `## Success Criteria` — numbered list (5 criteria from ROADMAP)
5. `## What Was Built` — one `### Plan 36-NN — Title` subsection per plan, sourced from each plan's SUMMARY.md
6. `## Out of Scope` — DEF-36-A..E
7. `## Links` — `[[Roadmap]]`, `[[Requirements]]`, `[[UAT-Series]]`, `[[_QUIRK-Hub]]`

**Write directly to vault filesystem** (CLAUDE.md mandate — file too large for `obsidian CLI content=`).

---

## Shared Patterns

### Severity-to-className mapping (UI)
**Source:** `src/dashboard/src/pages/identity.tsx:23-29`
**Apply to:** every severity Badge in motion.tsx; every motion-warning Badge inherits HSL values:
- STARTTLS warning reuses MEDIUM `bg-[hsl(38_92%_50%)] text-black`
- PLAINTEXT reuses HIGH `bg-[hsl(24_95%_53%)] text-white`
- Cloud chip reuses LOW `bg-[hsl(213_94%_68%)] text-black`

**Anti-pattern:** Do NOT add new variants to `components/ui/badge.tsx` (CONTEXT D-04 forbids).

### Loading + error UI
**Source:** `src/dashboard/src/pages/identity.tsx:99-100`
**Apply to:** motion.tsx top-level branch; same `length: 5` skeleton, same `text-muted-foreground` error paragraph.

### Data fetch
**Source:** `src/dashboard/src/hooks/useScanData.ts` (cache-by-scanId, no invalidation)
**Apply to:** motion.tsx — reuse `useScanData()`, do NOT introduce a parallel `useMotionData` hook. `motion_findings` rides on the existing `ScanLatestResponse`.

### Findings derivation in API
**Source:** `quirk/dashboard/api/routes/scan.py:184-330` (`_derive_identity_findings`)
**Apply to:** `_derive_motion_findings` — same structure: per-protocol branches → append `Finding` records → sort by `_severity_order` at end. Use `getattr(ep, "<attr>", None)` for fields that may not exist on legacy CryptoEndpoint rows (Pitfall 5).

### Pydantic response model
**Source:** `quirk/dashboard/api/schemas.py:80-90` (`IdentityFinding`)
**Apply to:** `MotionFinding` — same field order conventions; `Optional[str] = None` for nullable, plain `bool = False` for the two non-optional motion booleans.

### TestClient contract test
**Source:** `tests/test_dashboard_api.py:35-44` (`test_score_endpoint`) + `:47-54` (`test_findings_endpoint`)
**Apply to:** `test_motion_findings_endpoint`, `test_data_in_motion_subscore` — `dashboard_client` fixture, `(200, 404)` tolerance, `assert "X" in data` + `isinstance(data["X"], list/int)`.

### Phase note (Obsidian)
**Source:** `Phase-35-CBOM-Integration.md`
**Apply to:** Phase-36 note — same frontmatter, same 7-section template, written via `Write` tool to vault filesystem path.

### React Router v7 flat routing
**Source:** `src/dashboard/src/App.tsx:27-36`
**Apply to:** new `/motion` route — flat `<Route>` sibling, no `<Outlet />`, no nested layout (Pitfall 4).

---

## CRITICAL: Pitfall 1 — Pydantic SubScores silent drop

**Site:** `quirk/dashboard/api/routes/scan.py:595-601`

This is **not** a pattern to copy — it is a pattern that needs **explicit correction** in Phase 36. The current `SubScores(...)` constructor lists 5 fields by keyword (`hygiene`, `modern_tls`, `identity_trust`, `agility_signals`, `data_at_rest`) and silently discards `data_in_motion` from `subscores_raw` — even though `quirk/intelligence/scoring.py:237` already returns the value.

**Why it's silent:** Pydantic does not warn on omitted-from-constructor source-dict keys; the manual `.get(...)`-per-field mapping has no field-coverage check.

**Required Phase 36 action:** PLAN.md MUST place these two edits in the **same task**:
1. Add `data_in_motion: int = 0` to the Pydantic `SubScores` model in `quirk/dashboard/api/schemas.py:20-25`.
2. Add `data_in_motion=subscores_raw.get("data_in_motion", 0),` as a 6th kwarg in the `SubScores(...)` constructor at `scan.py:595-601`.

If only step 1 ships, the `/api/scan/latest` response will return `data_in_motion: 0` regardless of scoring output. The Executive 6th `<ScoreGauge>` will read `0` instead of the real motion score, and the bug will not surface until manual UAT.

**Detection signal during UAT:** gauge displays `0` (or `100` for legacy scans per Phase 34 D-05) even when `compute_readiness_score()` returns a non-zero `motion_score` — which happens whenever email/broker scanner profiles ran and emitted endpoints.

---

## No Analog Found

None. Every Phase 36 file has a strong codebase analog. The phase is structurally a substitution exercise.

---

## Metadata

**Analog search scope:**
- `src/dashboard/src/pages/` (React pages — identity, executive)
- `src/dashboard/src/components/` (sidebar, ui primitives)
- `src/dashboard/src/types/api.ts`
- `src/dashboard/src/hooks/useScanData.ts`
- `quirk/dashboard/api/{schemas.py, routes/scan.py}`
- `tests/test_dashboard_api.py` + `tests/conftest.py`
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-35-CBOM-Integration.md`

**Files scanned:** 9 primary analog files + 2 cross-reference (executive.tsx, scoring.py reference).

**Pattern extraction date:** 2026-04-28
