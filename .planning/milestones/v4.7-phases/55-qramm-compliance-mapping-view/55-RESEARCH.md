# Phase 55: QRAMM Compliance Mapping View - Research

**Researched:** 2026-05-08
**Domain:** QRAMM compliance view (FastAPI endpoint + React 6th tab) + CLI staleness subcommand + CI pytest gate
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Relevance scores = static weight × session dimension score. `QRAMM_COMPLIANCE_WEIGHTS` in `quirk/qramm/compliance_map.py` holds 0.0–1.0 float weights per practice→framework pair. Endpoint multiplies each practice's weight by the session's dimension score.
- **D-02:** When no active session or session not yet scored, endpoint returns the full framework×practice table with `relevance_score: null` for every entry (HTTP 200 — never 404/409). Frontend shows a banner.
- **D-03:** Endpoint returns `relevance_score: null` (HTTP 200 with nulls) when session scores are absent — NOT 404 or 409.
- **D-04:** All framework data lives server-side in `quirk/qramm/compliance_map.py`: `QRAMM_COMPLIANCE_WEIGHTS` and `SCANNER_COVERAGE`. No TS constants file for weights.
- **D-05:** New endpoint `GET /api/qramm/sessions/{id}/compliance-map` in `quirk/dashboard/api/routes/qramm.py`. Server multiplies weights × dimension scores and caps with SCANNER_COVERAGE before returning. Frontend renders returned data directly.
- **D-06:** Response row shape: `{practice_number, practice_area, dimension, framework, static_weight, relevance_score, scanner_informed}` — `scanner_informed` is a boolean derived from `SCANNER_COVERAGE[dimension] > 0`.
- **D-07:** `SCANNER_COVERAGE = {"CVI": 1.0, "SGRM": 0.0, "DPE": 0.0, "ITR": 0.0}`. Compliance-map endpoint caps `relevance_score = min(relevance_score, SCANNER_COVERAGE[dimension] × static_weight)`.
- **D-08:** UI shows tier badges ("Scanner-informed" / "Manual only"), not percentages. Footnote: "Coverage reflects QUIRK scanner findings for CVI only — SGRM, DPE, ITR require manual assessment." No "fully compliant" badge ever rendered.
- **D-09:** Compliance Map is the 6th tab in `/qramm/assessment`: `[ CVI ] [ SGRM ] [ DPE ] [ ITR ] [ Scorecard ] [ Compliance Map ]`. No new route or sidebar entry.
- **D-10:** `quirk qramm status` follows the exact same intercept pattern as `quirk compliance status` in `run_scan.py:main()`. `if len(sys.argv) > 2 and sys.argv[1] == "qramm" and sys.argv[2] == "status"` before the main argparse block.
- **D-11:** `qramm_cmd.py` reads `QRAMM_MODEL` from `quirk.qramm.model_meta` and `STALENESS_THRESHOLD_DAYS` (90). Output matches `compliance status` table format: `qramm_version`, `last_verified`, `days_remaining`, `verdict` (FRESH / STALE). Exits code 0 if within 90 days, code 1 if stale.
- **D-12:** Pytest CI gate: `tests/test_qramm_staleness.py` — asserts `QRAMM_MODEL["last_verified"]` within 90 days of today. Supports `QUIRK_CI_STALENESS_OVERRIDE_DATE` env var (ISO date string) for CI boundary testing.

### Claude's Discretion

- **D-09** (view placement confirmed): 6th tab in the existing `/qramm/assessment` page.

### Deferred Ideas (OUT OF SCOPE)

- PDF export of compliance mapping (Phase 56)
- Evidence bridge for SGRM/DPE/ITR (QRAMM-F01 — v4.8)
- New sidebar entry or route for the compliance view
- Coverage percentages in the UI (replaced by tier badges)
- `quirk qramm status --format json`

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QRAMM-05 | `QRAMM_MODEL` in `quirk/qramm/model_meta.py` carries `qramm_version`, `last_verified`, `source_url` — already provisioned in Phase 51; Phase 55 adds CLI surface | `model_meta.py` already correct; only CLI + test need adding |
| QRAMM-06 | CI pytest gate fails when `QRAMM_MODEL.last_verified` > 90 days old; supports `QUIRK_CI_STALENESS_OVERRIDE_DATE` env var | Pattern: `test_compliance_freshness.py`; override var is new for Phase 55 |
| QRAMM-07 | `quirk qramm status` CLI subcommand — version, last_verified, days remaining, verdict; exits non-zero when stale | Exact intercept pattern already in `run_scan.py` for `compliance status` and `doctor`; `qramm_cmd.py` mirrors `doctor_cmd.py` structure |
| QRAMM-15 | Dashboard QRAMM Compliance Mapping view — 8-framework table, per-practice relevance scores from active session, no "fully compliant" badge, no coverage % above scanner ceiling | New `compliance_map.py` module + FastAPI endpoint + 6th React tab |

</phase_requirements>

---

## Summary

Phase 55 delivers two fully independent work streams. The first adds a 6th tab to the existing `/qramm/assessment` page: a compliance-mapping table that shows per-practice relevance scores across 8 governance frameworks, derived by multiplying static weights (server-side `QRAMM_COMPLIANCE_WEIGHTS`) by the session's dimension scores. The second adds the `quirk qramm status` CLI subcommand and its corresponding pytest CI gate, completing the staleness enforcement loop that was pre-provisioned in `model_meta.py` during Phase 51.

Both streams are low-risk because they add new code rather than modifying existing logic. The compliance-map endpoint follows the established inline-Pydantic-model pattern from the QRAMM router. The CLI intercept follows the existing `compliance status` and `doctor` patterns in `run_scan.py`. The React tab follows the `ScorecardTab` component shape. No existing endpoints, models, or routing logic need modification.

The only design decision with meaningful complexity is the `QRAMM_COMPLIANCE_WEIGHTS` data structure — the planner must define reasonable float weights for 12 practice areas × 8 frameworks (96 cells). The CONTEXT.md provides the practice area taxonomy and the correct framework short-name keys; the planner must assign weights based on QRAMM framework relevance and document the rationale.

**Primary recommendation:** Implement in three plans — (1) Python backend: `compliance_map.py` + endpoint + `qramm_cmd.py` + `run_scan.py` intercept, (2) pytest gates: `test_qramm_staleness.py` + `test_qramm_compliance_map.py`, (3) React: `ComplianceMapTab.tsx` + 6th tab wiring + API type.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| QRAMM compliance weight table | API / Backend | — | Server is single source of truth (D-04); no weight data in browser |
| Relevance score computation | API / Backend | — | Server multiplies weights × scores and applies SCANNER_COVERAGE ceiling before returning (D-05) |
| Coverage tier badge logic | Frontend Server (SSR) | — | `scanner_informed` boolean delivered by API (D-06); React just reads it |
| 6th tab UI rendering | Browser / Client | — | Standard React tab component pattern; purely client-side rendering |
| CLI staleness check | API / Backend | — | `qramm_cmd.py` reads from `model_meta.py`, outputs to stdout, exits |
| CI pytest gate | API / Backend | — | Test imports `QRAMM_MODEL` directly from the module |

---

## Standard Stack

### Core (all verified in existing codebase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (installed) | New GET endpoint in QRAMM router | Already used for all QRAMM endpoints [VERIFIED: existing routes] |
| Pydantic v2 | (installed) | Inline response model for compliance-map endpoint | Phase 51 D-11 established inline-model pattern [VERIFIED: qramm.py] |
| SQLAlchemy | (installed) | Read `score_json` from `qramm_sessions` row | Already used in all QRAMM router endpoints [VERIFIED: qramm.py] |
| pytest | 9.0.2 | Two new test files | Project standard [VERIFIED: `pytest --version`] |
| React + shadcn/ui | (installed) | `ComplianceMapTab.tsx` component | Entire dashboard stack [VERIFIED: existing components] |
| Radix Tabs | (installed) | 6th tab trigger + content | Already used for 5-tab layout in `qramm-assessment.tsx` [VERIFIED: source] |
| shadcn Table | (installed) | 8-framework coverage table | Used in `ScorecardTab.tsx` [VERIFIED: source] |
| shadcn Badge | (installed) | "Scanner-informed" / "Manual only" tier badges | Used in `ScorecardTab.tsx` [VERIFIED: source] |

**No new dependencies required.** All libraries already installed.

---

## Architecture Patterns

### System Architecture Diagram

```
QRAMM Assessment Page (/qramm/assessment)
  [CVI] [SGRM] [DPE] [ITR] [Scorecard] [Compliance Map]  ← new 6th tab
                                               ↓
                                    ComplianceMapTab.tsx
                                               ↓
                              GET /api/qramm/sessions/{id}/compliance-map
                                               ↓
                              qramm.py router (compliance_map endpoint)
                              reads:  QRAMM_COMPLIANCE_WEIGHTS  ←── compliance_map.py
                                      SCANNER_COVERAGE          ←── compliance_map.py
                                      score_json from DB row
                              multiplies: weight × dimension_score
                              caps: min(score, SCANNER_COVERAGE[dim] × weight)
                                               ↓
                              [{practice_number, practice_area, dimension,
                                framework, static_weight, relevance_score,
                                scanner_informed}, ...]

CLI path:
  quirk qramm status   →   run_scan.py:main() intercept
                        →   qramm_cmd.py:run_qramm_status()
                            reads QRAMM_MODEL from model_meta.py
                            computes days remaining
                            prints table, exits 0/1

CI gate:
  pytest tests/test_qramm_staleness.py
    reads QRAMM_MODEL["last_verified"]
    optionally reads QUIRK_CI_STALENESS_OVERRIDE_DATE env var
    asserts age <= STALENESS_THRESHOLD_DAYS (90)
```

### Recommended Project Structure

```
quirk/qramm/
├── compliance_map.py     # NEW: QRAMM_COMPLIANCE_WEIGHTS + SCANNER_COVERAGE
├── model_meta.py         # EXISTS: QRAMM_MODEL (Phase 51)
├── questions.py          # EXISTS: QRAMM_QUESTIONS catalog
├── scoring.py            # EXISTS: scoring engine
└── evidence_bridge.py    # EXISTS: CVI auto-population

quirk/cli/
├── qramm_cmd.py          # NEW: run_qramm_status() (mirrors doctor_cmd.py)
├── doctor_cmd.py         # EXISTS
└── ...

quirk/dashboard/api/routes/
└── qramm.py              # EXTEND: add GET /qramm/sessions/{id}/compliance-map

tests/
├── test_qramm_staleness.py       # NEW: QRAMM-05/06 CI gate
└── test_qramm_compliance_map.py  # NEW: endpoint smoke + weight structure tests

src/dashboard/src/
├── components/qramm/
│   └── ComplianceMapTab.tsx      # NEW: 6th tab component
├── pages/qramm-assessment.tsx    # EXTEND: add 6th tab
└── types/api.ts                  # EXTEND: QRAMMComplianceMapRow interface
```

### Pattern 1: QRAMM Router Endpoint (inline Pydantic, Phase 51 D-11)

**What:** New GET endpoint on the existing QRAMM router. Response model defined inline as a Pydantic class (not in `schemas.py`). Reads `score_json` from the session row, multiplies weights, caps with SCANNER_COVERAGE.

**When to use:** All new QRAMM endpoints follow this pattern.

```python
# Source: quirk/dashboard/api/routes/qramm.py (existing pattern from Phase 51)
class ComplianceMapRow(BaseModel):
    practice_number: str
    practice_area: str
    dimension: str
    framework: str
    static_weight: float
    relevance_score: Optional[float]
    scanner_informed: bool

@router.get("/qramm/sessions/{session_id}/compliance-map", response_model=List[ComplianceMapRow])
def get_compliance_map(session_id: int, db: Session = Depends(get_db)) -> List[ComplianceMapRow]:
    session = _get_session_or_404(db, session_id)
    score_data: Optional[Dict[str, Any]] = None
    if session.score_json:
        try:
            score_data = json.loads(session.score_json)
        except (TypeError, ValueError):
            score_data = None
    # Build rows from QRAMM_COMPLIANCE_WEIGHTS x SCANNER_COVERAGE
    ...
```

[VERIFIED: existing pattern in `qramm.py`]

### Pattern 2: CLI Subcommand Intercept (run_scan.py:main)

**What:** `if len(sys.argv) > 2 and sys.argv[1] == "qramm" and sys.argv[2] == "status"` block added in `run_scan.py:main()` before the main argparse block. Delegates to `quirk/cli/qramm_cmd.py`.

**When to use:** Every QUIRK CLI subcommand uses this pattern.

```python
# Source: run_scan.py (existing compliance + doctor pattern — verified)
# --- qramm subcommand: intercept before scan argparse (Phase 55 QRAMM-07) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "qramm":
    if len(_sys.argv) > 2 and _sys.argv[2] == "status":
        from quirk.cli.qramm_cmd import run_qramm_status
        run_qramm_status()
        return
```

Insert this block after the `doctor` intercept and before the main `argparse.ArgumentParser(...)` call. [VERIFIED: `run_scan.py` lines 246-250]

### Pattern 3: Staleness Gate with Override Env Var (new pattern for Phase 55)

**What:** pytest test that reads `QRAMM_MODEL["last_verified"]`, checks age against `STALENESS_THRESHOLD_DAYS = 90`, and supports `QUIRK_CI_STALENESS_OVERRIDE_DATE` env var to inject a fake "today" date for CI boundary testing.

**When to use:** Any QUIRK module that carries a `last_verified` date.

```python
# Source: tests/test_compliance_freshness.py (base pattern)
# Extended with QUIRK_CI_STALENESS_OVERRIDE_DATE (new in Phase 55)
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

[ASSUMED: override pattern is new — no existing test uses `QUIRK_CI_STALENESS_OVERRIDE_DATE`; modeled after how CI override env vars work in similar tools]

### Pattern 4: React Tab with Async Data Fetch (ScorecardTab analog)

**What:** Self-contained tab component that reads `sessionId` from `QRAMMContext`, fetches from `GET /api/qramm/sessions/{id}/compliance-map`, renders a table with Badge components.

**When to use:** All QRAMM tab components follow this shape.

```tsx
// Source: src/dashboard/src/components/qramm/ScorecardTab.tsx (existing shape)
// ComplianceMapTab.tsx mirrors this self-contained pattern
import { useState, useEffect, useContext } from "react"
import { QRAMMContext } from "@/context/QRAMMContext"
import { Table, TableBody, TableCell, ... } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"

export function ComplianceMapTab() {
  const ctx = useContext(QRAMMContext)
  const [rows, setRows] = useState<QRAMMComplianceMapRow[]>([])
  const [loading, setLoading] = useState(false)
  const [hasScore, setHasScore] = useState(false)

  useEffect(() => {
    if (!ctx.sessionId) return
    // fetch /api/qramm/sessions/{ctx.sessionId}/compliance-map
    ...
  }, [ctx.sessionId, ctx.scoreResult])
  ...
}
```

[VERIFIED: ScorecardTab.tsx and QRAMMContext.tsx shape confirmed]

### Pattern 5: QRAMM_COMPLIANCE_WEIGHTS Structure

**What:** Nested dict in `compliance_map.py`. Outer key = practice area string matching `QRAMM_QUESTIONS[*].practice_area` (e.g., `"1.1"`, `"2.3"`). Inner key = 8 framework short names. Value = 0.0–1.0 float.

```python
# Source: 55-CONTEXT.md <specifics>
FRAMEWORK_KEYS = ("NIST_PQC", "NSM10", "CNSA2", "ISO27001", "ETSI_QS", "PCI_DSS", "CC", "BSI_TR")

QRAMM_COMPLIANCE_WEIGHTS: Dict[str, Dict[str, float]] = {
    # CVI dimension practices
    "1.1": {"NIST_PQC": 0.9, "NSM10": 0.8, "CNSA2": 0.9, "ISO27001": 0.7,
            "ETSI_QS": 0.8, "PCI_DSS": 0.5, "CC": 0.4, "BSI_TR": 0.7},
    "1.2": {...},
    "1.3": {...},
    # SGRM, DPE, ITR practices (2.x, 3.x, 4.x)
    ...
}

SCANNER_COVERAGE: Dict[str, float] = {
    "CVI": 1.0, "SGRM": 0.0, "DPE": 0.0, "ITR": 0.0
}
```

The planner is responsible for defining the actual weight values. Use QRAMM model expertise: quantum-focused frameworks (NIST_PQC, NSM10, CNSA2, ETSI_QS) get high weights on CVI practices; governance frameworks (ISO27001, PCI_DSS, CC, BSI_TR) get moderate weights on SGRM/governance practices.

[ASSUMED: specific weight values are editorial judgment — no external standard dictates exact float values; the CONTEXT.md leaves this to planner discretion]

### Anti-Patterns to Avoid

- **Importing risk_engine from compliance_map.py:** Phase 51 D-09 prohibits any qramm module from importing `quirk.engine.risk_engine`. `compliance_map.py` is pure data (dicts and constants only) — no engine imports possible or needed. [VERIFIED: model_meta.py and questions.py confirm the no-import pattern]
- **datetime.utcnow() in qramm_cmd.py:** DEBT-01 requires `datetime.now(timezone.utc)` throughout. [VERIFIED: existing code in qramm.py uses `datetime.now(timezone.utc)` via `_now_iso()` helper]
- **Hardcoded hex/hsl colors in ComplianceMapTab.tsx:** Use CSS variable tokens (`hsl(var(--accent))` etc.) per Phase 54 pattern. [VERIFIED: ScorecardTab.tsx uses no hardcoded colors]
- **Coverage percentage display:** D-08 explicitly prohibits percentages; tier badges replace them entirely.
- **404 or 409 when session not scored:** D-03 locks HTTP 200 with `relevance_score: null`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table rendering | Custom HTML table | `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableCell` from `@/components/ui/table` | Already in codebase, used by ScorecardTab [VERIFIED] |
| Badge styling | Custom span with inline style | `Badge` from `@/components/ui/badge` with `variant="default"` / `variant="secondary"` | Consistent with existing badge usage [VERIFIED] |
| Staleness date arithmetic | Manual timedelta string parsing | `datetime.date.fromisoformat()` + subtraction | Standard library; matches existing compliance test pattern [VERIFIED] |
| Response model validation | Manual dict validation | Pydantic `BaseModel` inline in router | Phase 51 D-11 pattern; already established [VERIFIED] |

---

## Common Pitfalls

### Pitfall 1: QRAMM_COMPLIANCE_WEIGHTS key mismatch with QRAMM_QUESTIONS practice_area

**What goes wrong:** `QRAMM_COMPLIANCE_WEIGHTS` uses practice area strings like `"1.1"` but the iteration code tries a different key format (e.g., integer or `"PA_1_1"`), producing KeyError or empty rows.

**Why it happens:** `QRAMM_QUESTIONS` uses strings `"1.1"` through `"4.3"` (verified in `questions.py`). If the weight dict uses a different key format, the multiplication loop silently skips rows.

**How to avoid:** Enumerate `QRAMM_COMPLIANCE_WEIGHTS` keys directly from `QRAMM_QUESTIONS[*].practice_area` — the 12 unique values are `"1.1"`, `"1.2"`, `"1.3"`, `"2.1"`, `"2.2"`, `"2.3"`, `"3.1"`, `"3.2"`, `"3.3"`, `"4.1"`, `"4.2"`, `"4.3"`. Test: assert `set(QRAMM_COMPLIANCE_WEIGHTS.keys()) == set(q["practice_area"] for q in QRAMM_QUESTIONS)`. [VERIFIED: questions.py structure]

**Warning signs:** Endpoint returns 96 rows but all `relevance_score` values are null even when session is scored.

### Pitfall 2: session.score_json dimension key format mismatch

**What goes wrong:** The endpoint reads `score_json` and tries `score_data["dimensions"]["CVI"]["score"]` but the actual JSON shape is `score_data["dimensions"]["CVI"]["score"]` with a nested `weighted` key.

**Why it happens:** The `score_session` endpoint stores `dim_breakdown[dim] = {"score": ..., "weighted": ..., "practices": {...}}`. The compliance-map endpoint must read the `score` key not the `weighted` key for per-dimension scores.

**How to avoid:** Read `score_data["dimensions"][dim]["score"]` — this is the raw dimension score (0.0–4.0 scale). [VERIFIED: `score_session` endpoint response structure in `qramm.py` lines 357-377]

**Warning signs:** Relevance scores outside the expected 0.0–1.0 range after multiplication.

### Pitfall 3: SCANNER_COVERAGE cap applied before multiplication

**What goes wrong:** `relevance_score = min(weight, SCANNER_COVERAGE[dim]) * dimension_score` instead of `min(weight * dimension_score, SCANNER_COVERAGE[dim] * weight)`.

**Why it happens:** The CONTEXT.md formula is `min(relevance_score, SCANNER_COVERAGE[dimension] × static_weight)` — cap is applied after the product, not before.

**How to avoid:** Compute `raw = weight * dimension_score`, then `capped = min(raw, SCANNER_COVERAGE[dim] * weight)`. For SGRM/DPE/ITR where `SCANNER_COVERAGE == 0.0`, capped always becomes 0.0 × weight = 0.0 — which matches the design intent. [VERIFIED: D-07 formula in CONTEXT.md]

### Pitfall 4: sys.argv qramm intercept position in run_scan.py

**What goes wrong:** Adding the `qramm status` intercept AFTER the main `argparse.ArgumentParser(...)` call causes argparse to consume `["qramm", "status"]` as positional args and error before the intercept runs.

**How to avoid:** Insert the qramm intercept block immediately after the `doctor` intercept (line 250) and before `parser = argparse.ArgumentParser(...)` (line 252). The pattern is consistent: `init` → `serve` → `compliance` → `doctor` → [new: `qramm`] → main argparse. [VERIFIED: `run_scan.py` lines 179–252]

### Pitfall 5: Tab value collision with existing Radix tabs

**What goes wrong:** Adding `<TabsTrigger value="compliance">` fails if `"compliance"` conflicts with another value in the same `<Tabs>` component.

**How to avoid:** Existing values are `"cvi"`, `"sgrm"`, `"dpe"`, `"itr"`, `"scorecard"`. Use `value="compliance"` — no conflict. [VERIFIED: `qramm-assessment.tsx` lines 247–253]

### Pitfall 6: ComplianceMapTab fetches on every scoreResult context update

**What goes wrong:** Using `ctx.scoreResult` in the `useEffect` dependency array causes a refetch on every score calculation, but the compliance-map endpoint always re-derives from `score_json` anyway. This is acceptable but must not cause infinite loops.

**How to avoid:** Fetch when `ctx.sessionId` changes OR when `ctx.scoreResult` changes (to pick up newly computed scores). No state mutations in the effect that would re-trigger it. The effect sets local `rows` state — `rows` must not be in the dependency array. [VERIFIED: ScorecardTab.tsx useEffect patterns]

---

## Code Examples

### `compliance_map.py` skeleton

```python
# Source: CONTEXT.md D-04/D-07 (structure decision)
from __future__ import annotations
from typing import Dict

SCANNER_COVERAGE: Dict[str, float] = {
    "CVI": 1.0,
    "SGRM": 0.0,
    "DPE": 0.0,
    "ITR": 0.0,
}

# practice_area (e.g., "1.1") → framework_short_name → weight 0.0–1.0
QRAMM_COMPLIANCE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "1.1": {"NIST_PQC": ..., "NSM10": ..., "CNSA2": ..., "ISO27001": ...,
            "ETSI_QS": ..., "PCI_DSS": ..., "CC": ..., "BSI_TR": ...},
    # ... 11 more practice areas
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

### `qramm_cmd.py` structure (mirrors `doctor_cmd.py`)

```python
# Source: quirk/cli/doctor_cmd.py (existing structural pattern)
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

    # Print table matching compliance status format
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

### 6th tab wiring in `qramm-assessment.tsx`

```tsx
// Source: existing qramm-assessment.tsx tab layout (lines 246-270)
// Extend TabsList with 6th trigger:
<TabsTrigger value="compliance">Compliance Map</TabsTrigger>

// Extend Tabs with 6th content:
<TabsContent value="compliance">
  <ComplianceMapTab />
</TabsContent>
```

### `QRAMMComplianceMapRow` type in `api.ts`

```typescript
// Source: CONTEXT.md D-06 response shape
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

## Runtime State Inventory

Not applicable. This phase adds new files and extends existing ones. No renames, refactors, or data migrations. No stored state requires updating:

- `qramm_sessions.score_json` is read-only by the new endpoint — no schema changes.
- `QRAMM_MODEL.last_verified` in `model_meta.py` already has value `"2026-05-05"` — within 90 days of research date (2026-05-08). No bump needed at phase start.

---

## Environment Availability

Step 2.6: SKIPPED (no new external dependencies — all libraries already installed; no external services required).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pytest.ini` / `pyproject.toml` (project root) |
| Quick run command | `pytest tests/test_qramm_staleness.py tests/test_qramm_compliance_map.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QRAMM-05 | `QRAMM_MODEL` has correct keys and types | unit | `pytest tests/test_qramm_staleness.py::test_qramm_model_shape -x` | ❌ Wave 0 |
| QRAMM-06 | Staleness gate fails when > 90 days; OVERRIDE_DATE env var works | unit | `pytest tests/test_qramm_staleness.py -x` | ❌ Wave 0 |
| QRAMM-07 | `quirk qramm status` exits 0 (FRESH) and exits 1 (STALE with override) | integration | `pytest tests/test_qramm_staleness.py::test_qramm_status_cli_smoke -x` | ❌ Wave 0 |
| QRAMM-15 | Compliance-map endpoint returns 200 with correct row structure | integration | `pytest tests/test_qramm_compliance_map.py -x` | ❌ Wave 0 |
| QRAMM-15 | Endpoint returns `relevance_score: null` for unscored session | unit | `pytest tests/test_qramm_compliance_map.py::test_compliance_map_unscored -x` | ❌ Wave 0 |
| QRAMM-15 | SGRM/DPE/ITR rows have 0.0 relevance_score even when dimension scored | unit | `pytest tests/test_qramm_compliance_map.py::test_scanner_coverage_ceiling -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_qramm_staleness.py tests/test_qramm_compliance_map.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_qramm_staleness.py` — covers QRAMM-05, QRAMM-06, QRAMM-07
- [ ] `tests/test_qramm_compliance_map.py` — covers QRAMM-15 endpoint behavior

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No new auth surface |
| V3 Session Management | no | Reads existing `qramm_sessions` row; no new session state |
| V4 Access Control | no | QUIRK dashboard has no per-user auth in v4.7 |
| V5 Input Validation | yes | Session ID path parameter validated by FastAPI/Pydantic int type |
| V6 Cryptography | no | No new crypto operations |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Session ID enumeration on compliance-map endpoint | Information Disclosure | FastAPI 404 via `_get_session_or_404` (existing pattern [VERIFIED]) |
| Injecting malformed `score_json` into DB | Tampering | `try/except json.loads` with fallback to `None` — same pattern as `read_session` [VERIFIED] |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Specific float values in `QRAMM_COMPLIANCE_WEIGHTS` are editorial judgment — no external standard dictates exact per-practice-per-framework weights | Code Examples | Low — weights are adjustable without breaking API contract; tests validate structure, not values |
| A2 | `QUIRK_CI_STALENESS_OVERRIDE_DATE` env var is a new addition in Phase 55 — no existing QUIRK test uses this pattern | Pattern 3 | Low — env var naming is straightforward; worst case is a rename if a standard emerges |

---

## Open Questions

1. **Weight values for `QRAMM_COMPLIANCE_WEIGHTS`**
   - What we know: 12 practice areas × 8 frameworks = 96 float cells required; CVI practices (1.x) map strongly to quantum-focused frameworks; governance practices (2.x SGRM) map more to ISO/CC
   - What's unclear: Exact weight values — these are substantive editorial judgments about QRAMM model relevance to each framework
   - Recommendation: Planner defines weights in the plan file with inline rationale. Reasonable defaults: NIST_PQC/NSM10/CNSA2/ETSI_QS get 0.8–1.0 on CVI; ISO27001/CC/BSI_TR get 0.6–0.8 on SGRM; PCI_DSS gets 0.4–0.6 (less quantum-focused). Values are defensible and adjustable post-deployment.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Phase 51 DEBT-01 | Must use `datetime.now(timezone.utc)` in `qramm_cmd.py` — no exceptions |
| Schemas in `schemas.py` | Inline Pydantic models in router | Phase 51 D-11 | `ComplianceMapRow` must be defined inline in `qramm.py`, not in a separate schemas file |

---

## Sources

### Primary (HIGH confidence)

- `quirk/dashboard/api/routes/qramm.py` — existing endpoint structure, inline Pydantic pattern, session read/score pattern [VERIFIED: direct read]
- `quirk/qramm/model_meta.py` — `QRAMM_MODEL` shape confirmed [VERIFIED: direct read]
- `quirk/qramm/questions.py` — 12 practice area keys (`"1.1"` through `"4.3"`) confirmed [VERIFIED: direct read]
- `quirk/compliance/__init__.py` — `status_report()`, builder pattern, staleness threshold [VERIFIED: direct read]
- `run_scan.py` (lines 179–252) — CLI intercept pattern for all subcommands [VERIFIED: direct read]
- `src/dashboard/src/pages/qramm-assessment.tsx` — 5-tab layout, TabsList/TabsTrigger/TabsContent pattern [VERIFIED: direct read]
- `src/dashboard/src/components/qramm/ScorecardTab.tsx` — self-contained tab component shape [VERIFIED: direct read]
- `src/dashboard/src/context/QRAMMContext.tsx` — `sessionId` availability in context [VERIFIED: direct read]
- `src/dashboard/src/components/ui/badge.tsx` — `variant` prop values (`default`, `secondary`) [VERIFIED: direct read]
- `tests/test_compliance_freshness.py` — base staleness gate pattern [VERIFIED: direct read]
- `.planning/phases/55-qramm-compliance-mapping-view/55-CONTEXT.md` — all locked decisions [VERIFIED: direct read]

### Secondary (MEDIUM confidence)

- Phase 51/52/53/54 CONTEXT.md files — established decisions carried forward [VERIFIED: cited from CONTEXT.md canonical refs]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in existing codebase, no new deps required
- Architecture: HIGH — all patterns verified against working Phase 51/52/53/54 code
- Pitfalls: HIGH — derived from direct code inspection of the intercept pattern, tab layout, and score_json shape
- Weight values: ASSUMED — editorial judgment, not researchable from external standards

**Research date:** 2026-05-08
**Valid until:** 2026-06-07 (30 days; stable codebase)
