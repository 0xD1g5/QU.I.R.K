# Phase 55: QRAMM Compliance Mapping View - Pattern Map

**Mapped:** 2026-05-08
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/qramm/compliance_map.py` | utility/data | transform | `quirk/compliance/__init__.py` | role-match (same static-dict + builder pattern) |
| `quirk/dashboard/api/routes/qramm.py` | route (extend) | request-response | `quirk/dashboard/api/routes/qramm.py` lines 232–377 | exact (same file, same inline-Pydantic endpoint pattern) |
| `quirk/cli/qramm_cmd.py` | utility/CLI | request-response | `quirk/cli/doctor_cmd.py` | role-match (CLI entrypoint, exit-code semantics) |
| `run_scan.py` (extend) | config (extend) | request-response | `run_scan.py` lines 223–250 | exact (same file, same intercept block pattern) |
| `tests/test_qramm_staleness.py` | test | request-response | `tests/test_compliance_freshness.py` | exact (same staleness gate structure) |
| `tests/test_qramm_compliance_map.py` | test | request-response | `quirk/dashboard/api/routes/qramm.py` test analogs | role-match (endpoint smoke tests) |
| `src/dashboard/src/components/qramm/ComplianceMapTab.tsx` | component | request-response | `src/dashboard/src/components/qramm/ScorecardTab.tsx` | exact (same self-contained tab shape) |
| `src/dashboard/src/pages/qramm-assessment.tsx` (extend) | component (extend) | request-response | same file lines 246–270 | exact (same TabsList/TabsContent wiring) |
| `src/dashboard/src/types/api.ts` (extend) | utility (extend) | transform | same file lines 185–225 | exact (same interface-append pattern) |

---

## Pattern Assignments

### `quirk/qramm/compliance_map.py` (utility, transform)

**Analog:** `quirk/compliance/__init__.py`

**Imports pattern** (lines 1–19 of analog):
```python
from __future__ import annotations
from typing import Any, Dict, FrozenSet, List
```

**Module-level constant pattern** — verified constants structure (`quirk/compliance/__init__.py` lines 22–93):
```python
# Phase constant and URL anchors lifted to module-level so refactors stay one-touch
_PHASE_49_VERIFIED: str = "2026-05-05"
_PCI_4_0_1_URL = "https://..."

# Builder functions return typed dicts — one per framework
def _pci(control: str) -> Dict[str, Any]:
    return {
        "framework": "PCI-DSS 4.0.1",
        "control": control,
        "version": "4.0.1",
        "last_verified": _PHASE_49_VERIFIED,
        "source_url": _PCI_4_0_1_URL,
    }
```

**Core data structure pattern** (`quirk/compliance/__init__.py` lines 128–227):
```python
# Top-level dict: outer key is the lookup key; value is a list/dict of framework data
COMPLIANCE_MAP: Dict[str, List[Dict[str, Any]]] = {
    "Plaintext HTTP service detected": [
        _pci("4.2.1"), _hipaa("§164.312(e)(1)"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    ...
}
```

**For `compliance_map.py`, adapt this pattern as:**
```python
from __future__ import annotations
from typing import Dict

SCANNER_COVERAGE: Dict[str, float] = {
    "CVI": 1.0,
    "SGRM": 0.0,
    "DPE": 0.0,
    "ITR": 0.0,
}

# practice_area (e.g. "1.1") → framework_short_name → weight 0.0–1.0
QRAMM_COMPLIANCE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "1.1": {"NIST_PQC": ..., "NSM10": ..., ...},
    ...
}

FRAMEWORK_DISPLAY_NAMES: Dict[str, str] = {
    "NIST_PQC": "NIST PQC Standards",
    "NSM10":    "NSM-10",
    "CNSA2":    "CNSA 2.0",
    "ISO27001":  "ISO 27001:2022",
    "ETSI_QS":  "ETSI Quantum-Safe",
    "PCI_DSS":  "PCI-DSS v4.0",
    "CC":       "Common Criteria",
    "BSI_TR":   "BSI TR-02102",
}
```

**Anti-pattern:** Do NOT import `quirk.engine.risk_engine` or any scanner module. `compliance_map.py` is pure data — dicts and constants only. Confirmed by `model_meta.py` and `questions.py` which also have no engine imports.

---

### `quirk/dashboard/api/routes/qramm.py` — new compliance-map endpoint (route, request-response)

**Analog:** `quirk/dashboard/api/routes/qramm.py` (same file — inline Pydantic pattern from lines 42–86 and GET endpoint from lines 232–255)

**Inline Pydantic response model pattern** (lines 42–66 of qramm.py):
```python
# Per CONTEXT.md D-11: Pydantic models live inline (consistent with scan.py).
class SessionRead(BaseModel):
    session_id: int
    org_name: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    status: Optional[str]
    model_version: Optional[str]
    score: Optional[Dict[str, Any]] = None
    answers_count: int
```

**New response model for compliance-map** (define inline in the same file):
```python
class ComplianceMapRow(BaseModel):
    practice_number: str
    practice_area: str
    dimension: str
    framework: str
    static_weight: float
    relevance_score: Optional[float]
    scanner_informed: bool
```

**GET endpoint with session fetch + JSON parse pattern** (lines 232–255):
```python
@router.get("/qramm/sessions/{session_id}", response_model=SessionRead)
def read_session(session_id: int, db: Session = Depends(get_db)) -> SessionRead:
    session = _get_session_or_404(db, session_id)
    score: Optional[Dict[str, Any]] = None
    if session.score_json:
        try:
            score = json.loads(session.score_json)
        except (TypeError, ValueError):
            score = None
    return SessionRead(...)
```

**New endpoint follows this exact pattern:**
```python
@router.get("/qramm/sessions/{session_id}/compliance-map", response_model=List[ComplianceMapRow])
def get_compliance_map(session_id: int, db: Session = Depends(get_db)) -> List[ComplianceMapRow]:
    session = _get_session_or_404(db, session_id)
    score_data: Optional[Dict[str, Any]] = None
    if session.score_json:
        try:
            score_data = json.loads(session.score_json)
        except (TypeError, ValueError):
            score_data = None
    # Build rows: for each practice_area in QRAMM_COMPLIANCE_WEIGHTS,
    # for each framework in FRAMEWORK_KEYS, multiply weight × dimension_score,
    # then cap: min(raw, SCANNER_COVERAGE[dimension] × weight).
    # Returns relevance_score: None when score_data is None.
    ...
```

**score_json dimension key** — verified in lines 356–362:
```python
dim_breakdown[dim] = {
    "score": round(dimension_scores.get(dim, 0.0), 4),   # ← read this key
    "weighted": overall_block["dimensions"][dim],
    "practices": dim_to_practices.get(dim, {}),
}
```
Use `score_data["dimensions"][dim]["score"]` for the per-dimension raw score (0.0–4.0 scale).

**Helper pattern** — reuse existing helpers (lines 159–171):
```python
def _now_iso() -> datetime:
    return datetime.now(timezone.utc)

def _get_session_or_404(db: Session, session_id: int) -> QRAMMSession:
    session = db.get(QRAMMSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
```

---

### `quirk/cli/qramm_cmd.py` (utility/CLI, request-response)

**Analog:** `quirk/cli/doctor_cmd.py`

**Imports pattern** (lines 1–15 of doctor_cmd.py):
```python
from __future__ import annotations

import datetime
import sys
from typing import Tuple
```

**Exit-code semantics pattern** (lines 123–171):
```python
def run_doctor() -> None:
    """Phase 52 DOCS-05 entrypoint. Prints a Rich health table and exits 0 or 1."""
    ...
    failed = False
    # ... checks ...
    sys.exit(1 if failed else 0)
```

**For `qramm_cmd.py` — mirrors compliance status output format** (`quirk/compliance/__init__.py` lines 251–278):
```python
def status_report(format: str = "text") -> None:
    print(f"{'Framework':<20} {'Version':<14} {'Last Verified':<14} Source URL")
    print("-" * 100)
    for fw in sorted(seen):
        row = seen[fw]
        print(
            f"{row['framework']:<20} {row['version']:<14} "
            f"{row['last_verified']:<14} {row['source_url']}"
        )
```

**`qramm_cmd.py` adapts to:**
```python
from __future__ import annotations
import datetime
import sys
from quirk.qramm.model_meta import QRAMM_MODEL, STALENESS_THRESHOLD_DAYS

def run_qramm_status() -> None:
    today = datetime.date.today()
    last_verified = datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])
    age = (today - last_verified).days
    days_remaining = STALENESS_THRESHOLD_DAYS - age
    fresh = age <= STALENESS_THRESHOLD_DAYS
    verdict = "FRESH" if fresh else "STALE"
    print(f"{'QRAMM Version':<16} {'Last Verified':<14} {'Days Remaining':<16} Status")
    print("-" * 70)
    print(
        f"{QRAMM_MODEL['qramm_version']:<16} "
        f"{QRAMM_MODEL['last_verified']:<14} "
        f"{days_remaining:<16} "
        f"{verdict}"
    )
    sys.exit(0 if fresh else 1)
```

**datetime rule:** Use `datetime.date.today()` for date-only staleness arithmetic (no timezone required). Use `datetime.now(timezone.utc)` only when storing timestamps. The `doctor_cmd.py` uses `datetime.date.today()` consistently for date comparisons (lines 47–55).

---

### `run_scan.py` — qramm intercept block (config, request-response)

**Analog:** `run_scan.py` lines 223–250 (compliance + doctor intercepts)

**Compliance intercept pattern** (lines 223–244):
```python
# --- compliance subcommand: intercept before scan argparse (Phase 49 D-05) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "compliance":
    comp_parser = argparse.ArgumentParser(
        prog="quirk compliance",
        description="Inspect QUIRK's compliance mapping data (PCI-DSS / HIPAA / FIPS 140-3)",
    )
    comp_sub = comp_parser.add_subparsers(dest="action", required=True)
    status_parser = comp_sub.add_parser(
        "status",
        help="Print per-framework version, last_verified date, and source URL",
    )
    comp_args = comp_parser.parse_args(_sys.argv[2:])
    if comp_args.action == "status":
        from quirk.compliance import status_report
        status_report(format=comp_args.format)
    return
```

**Doctor intercept pattern** (lines 246–250):
```python
# --- doctor subcommand: intercept before scan argparse (Phase 52 DOCS-05 / D-10) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "doctor":
    from quirk.cli.doctor_cmd import run_doctor
    run_doctor()
    return
```

**New qramm intercept — insert immediately after line 250, before line 252 (`parser = argparse.ArgumentParser(...)`):**
```python
# --- qramm subcommand: intercept before scan argparse (Phase 55 QRAMM-07) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "qramm":
    if len(_sys.argv) > 2 and _sys.argv[2] == "status":
        from quirk.cli.qramm_cmd import run_qramm_status
        run_qramm_status()
        return
```

**Position constraint:** MUST be inserted AFTER the `doctor` intercept (line 250) and BEFORE `parser = argparse.ArgumentParser(...)` (line 252). The intercept chain order is: `init` → `serve` → `compliance` → `doctor` → `qramm` → main argparse.

---

### `tests/test_qramm_staleness.py` (test, request-response)

**Analog:** `tests/test_compliance_freshness.py`

**Full analog file** (lines 1–26):
```python
"""Phase 49 D-04 gate 3 (COMPLY-07): no entry older than STALENESS_THRESHOLD_DAYS."""
from __future__ import annotations

import datetime

def test_no_entry_older_than_threshold():
    from quirk.compliance import COMPLIANCE_MAP, STALENESS_THRESHOLD_DAYS

    today = datetime.date.today()
    stale: list[tuple[str, str, int]] = []
    for title, entries in COMPLIANCE_MAP.items():
        for entry in entries:
            try:
                verified = datetime.date.fromisoformat(entry["last_verified"])
            except (KeyError, TypeError, ValueError):
                continue
            age = (today - verified).days
            if age > STALENESS_THRESHOLD_DAYS:
                stale.append((title, entry["last_verified"], age))
    assert not stale, (
        f"Stale compliance entries (>{STALENESS_THRESHOLD_DAYS} days): {stale}. "
        ...
    )
```

**QRAMM staleness gate extends this with `QUIRK_CI_STALENESS_OVERRIDE_DATE` env var (new in Phase 55):**
```python
from __future__ import annotations
import datetime
import os

def test_qramm_model_not_stale():
    from quirk.qramm.model_meta import QRAMM_MODEL, STALENESS_THRESHOLD_DAYS
    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    today = (
        datetime.date.fromisoformat(override)
        if override
        else datetime.date.today()
    )
    last_verified = datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])
    age = (today - last_verified).days
    assert age <= STALENESS_THRESHOLD_DAYS, (
        f"QRAMM_MODEL.last_verified is {age} days old "
        f"(>{STALENESS_THRESHOLD_DAYS}). "
        f"Re-verify against https://qramm.org and bump last_verified."
    )
```

**QRAMM_MODEL shape to validate** (`quirk/qramm/model_meta.py` lines 16–22):
```python
QRAMM_MODEL = {
    "qramm_version": "1.0",
    "last_verified": "2026-05-05",
    "source_url": "https://qramm.org",
    "github_url": "https://github.com/csnp/qramm",
    "license": "MIT",
}
```
Add a `test_qramm_model_shape` test that asserts all required keys are present and `last_verified` is a valid ISO date string.

---

### `tests/test_qramm_compliance_map.py` (test, request-response)

**Analog:** `quirk/dashboard/api/routes/qramm.py` — read `score_session` and `read_session` for the test's expected response shapes.

**Test import/setup pattern** (matching the project's existing test structure):
```python
from __future__ import annotations
import pytest
from quirk.qramm.compliance_map import QRAMM_COMPLIANCE_WEIGHTS, SCANNER_COVERAGE

def test_compliance_weights_keys_match_questions():
    from quirk.qramm.questions import QRAMM_QUESTIONS
    expected_practice_areas = {q["practice_area"] for q in QRAMM_QUESTIONS}
    assert set(QRAMM_COMPLIANCE_WEIGHTS.keys()) == expected_practice_areas

def test_scanner_coverage_structure():
    assert set(SCANNER_COVERAGE.keys()) == {"CVI", "SGRM", "DPE", "ITR"}
    assert SCANNER_COVERAGE["CVI"] == 1.0
    assert SCANNER_COVERAGE["SGRM"] == 0.0
```

**Key structural assertion — weight values in range:**
```python
FRAMEWORK_KEYS = ("NIST_PQC", "NSM10", "CNSA2", "ISO27001", "ETSI_QS", "PCI_DSS", "CC", "BSI_TR")

def test_all_weight_values_in_range():
    for pa, fw_map in QRAMM_COMPLIANCE_WEIGHTS.items():
        assert set(fw_map.keys()) == set(FRAMEWORK_KEYS), f"Missing framework keys for {pa}"
        for fw, weight in fw_map.items():
            assert 0.0 <= weight <= 1.0, f"{pa}.{fw} weight {weight} out of range"
```

---

### `src/dashboard/src/components/qramm/ComplianceMapTab.tsx` (component, request-response)

**Analog:** `src/dashboard/src/components/qramm/ScorecardTab.tsx`

**Imports pattern** (lines 1–22 of ScorecardTab.tsx):
```typescript
import { useState, useContext, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { QRAMMContext } from "@/context/QRAMMContext"
import type { QRAMMScoreResponse } from "@/types/api"
```

**For `ComplianceMapTab.tsx`, adapt imports to:**
```typescript
import { useState, useEffect, useContext } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { QRAMMContext } from "@/context/QRAMMContext"
import type { QRAMMComplianceMapRow } from "@/types/api"
```

**Context access pattern** (ScorecardTab.tsx lines 29–32):
```typescript
export function ScorecardTab({ qnToDim }: ScorecardTabProps) {
  const ctx = useContext(QRAMMContext)
  const [calculating, setCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)
```

**Async fetch pattern** (ScorecardTab.tsx lines 62–85 — `handleCalculate`):
```typescript
async function handleCalculate() {
  if (!ctx.sessionId) return
  setCalculating(true)
  setError(null)
  try {
    const resp = await fetch(`/api/qramm/sessions/${ctx.sessionId}/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_multiplier: ctx.profile?.multiplier ?? null }),
    })
    if (!resp.ok) {
      setError("Could not calculate score — check your connection and try again")
      return
    }
    const json: QRAMMScoreResponse = await resp.json()
    ctx.setScoreResult(json)
  } catch {
    setError("Could not calculate score — check your connection and try again")
  } finally {
    setCalculating(false)
  }
}
```

**`ComplianceMapTab` replaces the imperative fetch with `useEffect`:**
```typescript
export function ComplianceMapTab() {
  const ctx = useContext(QRAMMContext)
  const [rows, setRows] = useState<QRAMMComplianceMapRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!ctx.sessionId) return
    setLoading(true)
    fetch(`/api/qramm/sessions/${ctx.sessionId}/compliance-map`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then((data: QRAMMComplianceMapRow[]) => { setRows(data); setLoading(false) })
      .catch(() => { setError("Could not load compliance map"); setLoading(false) })
  }, [ctx.sessionId, ctx.scoreResult])
  ...
}
```

**Badge variant pattern** (ScorecardTab.tsx lines 250–254):
```typescript
<Badge className={MATURITY_BADGE_CLASS[maturityInt]}>
  {MATURITY_LABEL[maturityInt]}
</Badge>
```

**For coverage tier badges:**
```typescript
// scanner_informed comes from the API (D-06) — no computation in React
<Badge variant={row.scanner_informed ? "default" : "secondary"}>
  {row.scanner_informed ? "Scanner-informed" : "Manual only"}
</Badge>
```

**CSS token rule** — ScorecardTab.tsx uses `hsl(var(--border))`, `hsl(var(--muted-foreground))`, `hsl(var(--accent))` — no hardcoded hex/hsl in any component. Follow this convention.

**Table pattern** (ScorecardTab.tsx lines 214–265 — Dimension Summary table):
```typescript
<Table>
  <TableHeader>
    <TableRow>
      <TableHead className="text-xs font-semibold uppercase tracking-[0.08em]">
        Dimension
      </TableHead>
      ...
    </TableRow>
  </TableHeader>
  <TableBody>
    {DIMENSIONS.map((dim) => (
      <TableRow key={dim}>
        <TableCell className="text-sm">{dim}</TableCell>
        ...
      </TableRow>
    ))}
  </TableBody>
</Table>
```

**No-score banner pattern** (ScorecardTab.tsx lines 166–170):
```typescript
{!ctx.scoreResult && (
  <p className="text-xs text-muted-foreground mt-4 text-center max-w-[280px]">
    Answer questions across all dimensions, then click Calculate Score...
  </p>
)}
```
Adapt for compliance map: `"Run and score a QRAMM assessment to see session-derived relevance scores."`

---

### `src/dashboard/src/pages/qramm-assessment.tsx` — 6th tab wiring (component, request-response)

**Analog:** Same file, lines 245–270

**Existing 5-tab layout** (lines 245–270):
```typescript
{/* 5-tab assessment layout */}
<Tabs defaultValue="cvi">
  <TabsList>
    <TabsTrigger value="cvi">CVI</TabsTrigger>
    <TabsTrigger value="sgrm">SGRM</TabsTrigger>
    <TabsTrigger value="dpe">DPE</TabsTrigger>
    <TabsTrigger value="itr">ITR</TabsTrigger>
    <TabsTrigger value="scorecard">Scorecard</TabsTrigger>
  </TabsList>
  ...
  <TabsContent value="scorecard">
    <ScorecardTab qnToDim={qnToDim} />
  </TabsContent>
</Tabs>
```

**Add 6th tab trigger and content — insert after `<TabsTrigger value="scorecard">Scorecard</TabsTrigger>` (line 252) and after the scorecard `<TabsContent>` block (line 269):**
```typescript
// In TabsList — after line 252:
<TabsTrigger value="compliance">Compliance Map</TabsTrigger>

// After line 269 TabsContent scorecard block:
<TabsContent value="compliance">
  <ComplianceMapTab />
</TabsContent>
```

**Tab value constraint:** Existing values are `"cvi"`, `"sgrm"`, `"dpe"`, `"itr"`, `"scorecard"`. Use `value="compliance"` — no collision.

**Import to add at top of file:**
```typescript
import { ComplianceMapTab } from "@/components/qramm/ComplianceMapTab"
```

---

### `src/dashboard/src/types/api.ts` — QRAMMComplianceMapRow interface (utility, transform)

**Analog:** Same file, lines 185–225 (QRAMM interface block)

**Existing QRAMM interface append pattern** (lines 185–225):
```typescript
// ============== QRAMM (Phase 54) ==============

export interface QuestionItem { ... }
export type MaturityValue = 1 | 2 | 3 | 4
export interface QRAMMSessionSummary { ... }
export interface QRAMMAnswerRead { ... }
export interface QRAMMProfileResponse { ... }
export interface QRAMMScoreResponse {
  overall: number
  maturity: string
  dimensions: Record<string, { score: number; weighted: number }>
  profile_multiplier: number
}
```

**Append after line 225 (end of file):**
```typescript
// Phase 55: QRAMM Compliance Map
export interface QRAMMComplianceMapRow {
  practice_number: string
  practice_area: string
  dimension: string
  framework: string
  static_weight: number
  relevance_score: number | null
  scanner_informed: boolean
}
```

---

## Shared Patterns

### Inline Pydantic Models in Router
**Source:** `quirk/dashboard/api/routes/qramm.py` lines 42–127
**Apply to:** New `ComplianceMapRow` class in qramm.py
```python
# All response models defined at the top of the route file, before endpoint functions.
# Do NOT add to quirk/dashboard/api/schemas.py — that is the Phase 51 D-11 decision.
class MyModel(BaseModel):
    field: Type
    optional_field: Optional[Type]
```

### `_get_session_or_404` helper
**Source:** `quirk/dashboard/api/routes/qramm.py` lines 167–171
**Apply to:** New compliance-map endpoint
```python
def _get_session_or_404(db: Session, session_id: int) -> QRAMMSession:
    session = db.get(QRAMMSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
```

### `_now_iso()` datetime helper
**Source:** `quirk/dashboard/api/routes/qramm.py` lines 159–160
**Apply to:** Any new endpoint that stores timestamps (not needed in compliance-map endpoint since it is read-only)
```python
def _now_iso() -> datetime:
    return datetime.now(timezone.utc)
```

### score_json parse with fallback
**Source:** `quirk/dashboard/api/routes/qramm.py` lines 240–245
**Apply to:** New compliance-map endpoint
```python
score: Optional[Dict[str, Any]] = None
if session.score_json:
    try:
        score = json.loads(session.score_json)
    except (TypeError, ValueError):
        score = None
```

### CLI intercept in run_scan.py
**Source:** `run_scan.py` lines 246–250
**Apply to:** New qramm intercept block
```python
if len(_sys.argv) > 1 and _sys.argv[1] == "doctor":
    from quirk.cli.doctor_cmd import run_doctor
    run_doctor()
    return
```

### Staleness date arithmetic
**Source:** `tests/test_compliance_freshness.py` lines 14–22
**Apply to:** `test_qramm_staleness.py` and `qramm_cmd.py`
```python
today = datetime.date.today()
verified = datetime.date.fromisoformat(entry["last_verified"])
age = (today - verified).days
if age > STALENESS_THRESHOLD_DAYS:
    ...
```

### CSS variable color tokens in React
**Source:** `src/dashboard/src/components/qramm/ScorecardTab.tsx` lines 139–160
**Apply to:** `ComplianceMapTab.tsx`
```typescript
// Use hsl(var(--token)) — never hardcoded hex/hsl
stroke="hsl(var(--border))"
tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
stroke="hsl(var(--accent))"
```

---

## No Analog Found

All 8 files have strong analogs in the codebase. No files require falling back to RESEARCH.md patterns exclusively.

---

## Metadata

**Analog search scope:** `quirk/`, `quirk/cli/`, `quirk/dashboard/api/routes/`, `tests/`, `src/dashboard/src/`
**Files scanned:** 10 analog files read directly
**Pattern extraction date:** 2026-05-08
