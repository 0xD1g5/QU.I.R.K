---
phase: 55-qramm-compliance-mapping-view
type: context
status: active
source: /gsd-discuss-phase 55
updated: 2026-05-08
milestone: v4.7 Governance & Compliance Platform
requirements: [QRAMM-05, QRAMM-06, QRAMM-07, QRAMM-15]
---

# Phase 55: QRAMM Compliance Mapping View - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 55 delivers two parallel tracks:

1. **QRAMM Compliance Mapping View (QRAMM-15)** — A 6th tab (`[ Compliance Map ]`) added to the existing `/qramm/assessment` page (Phase 54's 5-tab layout). Shows an 8-framework coverage table (NIST PQC Standards, NSM-10, CNSA 2.0, ISO 27001:2022, ETSI Quantum-Safe, PCI-DSS v4.0, Common Criteria, BSI TR-02102) with per-practice relevance scores derived from the active assessment session. Never displays a "fully compliant" badge; coverage tier badges replace coverage percentages.

2. **QRAMM model staleness CLI + CI gate (QRAMM-05, QRAMM-06, QRAMM-07)** — `quirk qramm status` subcommand + pytest gate. `QRAMM_MODEL` already exists in `quirk/qramm/model_meta.py` (Phase 51). This phase adds the CLI surface and CI enforcement.

**In scope:**
- New `quirk/qramm/compliance_map.py` — `QRAMM_COMPLIANCE_WEIGHTS` dict (practice × framework float weights) + `SCANNER_COVERAGE` ceiling dict
- New `GET /api/qramm/sessions/{id}/compliance-map` FastAPI endpoint in `quirk/dashboard/api/routes/qramm.py`
- New 6th tab `[ Compliance Map ]` in `src/dashboard/src/pages/qramm-assessment.tsx`
- `quirk qramm status` CLI subcommand (intercept in `run_scan.py`, implementation in `quirk/cli/qramm_cmd.py`)
- Pytest CI staleness gate for `QRAMM_MODEL.last_verified` with `QUIRK_CI_STALENESS_OVERRIDE_DATE` env var

**Out of scope:**
- PDF export of compliance mapping (Phase 56)
- Evidence bridge for SGRM/DPE/ITR (QRAMM-F01 — v4.8)
- New sidebar entry or route for the compliance view (reuses `/qramm/assessment`)
- Coverage percentages in the UI (replaced by tier badges)

</domain>

<decisions>
## Implementation Decisions

### Relevance Score Formula

- **D-01:** Relevance scores = static weight × session dimension score. Pre-define a 0.0–1.0 float relevance weight for each practice→framework pair in `QRAMM_COMPLIANCE_WEIGHTS` in `quirk/qramm/compliance_map.py`. The endpoint multiplies each practice's weight by the session's dimension score (from the score result) to produce per-practice relevance scores per framework.

- **D-02:** When no active session exists (or session has not been scored yet), the compliance-map endpoint returns the full framework×practice table with `relevance_score: null` for every entry. Static weights are always returned so the view is useful even before an assessment is run. The frontend shows a banner: "Run and score a QRAMM assessment to see session-derived relevance scores."

- **D-03:** Endpoint returns `relevance_score: null` (HTTP 200 with nulls) when session scores are absent — NOT 404 or 409. This keeps the frontend simple: one render path handles both scored and unscored states.

### Framework Data Home

- **D-04:** All framework data lives server-side in `quirk/qramm/compliance_map.py`: `QRAMM_COMPLIANCE_WEIGHTS` (practice → framework → float weight, 0.0–1.0) and `SCANNER_COVERAGE` (dimension → float ceiling, e.g., `{"CVI": 1.0, "SGRM": 0.0, "DPE": 0.0, "ITR": 0.0}`). No TS constants file for weights — single source of truth in Python.

- **D-05:** New endpoint `GET /api/qramm/sessions/{id}/compliance-map` in `quirk/dashboard/api/routes/qramm.py`. Server multiplies `QRAMM_COMPLIANCE_WEIGHTS` × session dimension scores (from `qramm_sessions.score_json`) and caps results with `SCANNER_COVERAGE` before returning. Mirrors the pattern of `/api/qramm/sessions/{id}/score`. Frontend renders the returned data directly — no multiplication logic in React.

- **D-06:** Endpoint response shape (each row): `{practice_number, practice_area, dimension, framework, static_weight, relevance_score, scanner_informed}` where `scanner_informed` is a boolean derived from `SCANNER_COVERAGE[dimension] > 0`. Frontend uses `scanner_informed` to drive the coverage tier badge.

### Coverage Ceiling

- **D-07:** Per-dimension scanner coverage ceiling: `SCANNER_COVERAGE = {"CVI": 1.0, "SGRM": 0.0, "DPE": 0.0, "ITR": 0.0}` in `quirk/qramm/compliance_map.py`. The compliance-map endpoint caps `relevance_score = min(relevance_score, SCANNER_COVERAGE[dimension] × static_weight)` before returning. When the evidence bridge expands to SGRM/DPE/ITR in v4.8, only this dict needs updating.

- **D-08:** UI treatment — no coverage percentages in the view. Each framework row shows a coverage tier badge: "Scanner-informed" (at least one of the framework's relevant dimensions has `SCANNER_COVERAGE > 0`) or "Manual only" (all relevant dimensions are scanner-blind). A footnote below the table reads: "Coverage reflects QUIRK scanner findings for CVI only — SGRM, DPE, ITR require manual assessment." No "fully compliant" badge is ever rendered.

### View Placement (Claude's Discretion)

- **D-09:** Compliance Map is the **6th tab** in the existing `/qramm/assessment` page: `[ CVI ] [ SGRM ] [ DPE ] [ ITR ] [ Scorecard ] [ Compliance Map ]`. No new route or sidebar entry. This keeps all QRAMM workflow under one URL and avoids sidebar clutter. The 6th tab is always accessible (same as Scorecard tab in Phase 54).

### QRAMM Status CLI (QRAMM-07)

- **D-10:** `quirk qramm status` follows the exact same intercept pattern as `quirk compliance status` in `run_scan.py:main()`. Add: `if len(sys.argv) > 2 and sys.argv[1] == "qramm" and sys.argv[2] == "status"` before the main argparse block, delegating to `quirk/cli/qramm_cmd.py`.

- **D-11:** `qramm_cmd.py` reads `QRAMM_MODEL` from `quirk.qramm.model_meta` and `STALENESS_THRESHOLD_DAYS` (90). Computes days remaining. Output matches the `compliance status` table format: columns `qramm_version`, `last_verified`, `days_remaining`, `verdict` (FRESH / STALE). Exits code 0 if within 90 days, code 1 if stale.

- **D-12:** Pytest CI gate: `tests/test_qramm_staleness.py` asserts `QRAMM_MODEL["last_verified"]` is within 90 days of today. Supports `QUIRK_CI_STALENESS_OVERRIDE_DATE` env var (ISO date string) for CI boundary testing — mirrors the compliance staleness gate pattern from Phase 49.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 55 Requirements
- `.planning/REQUIREMENTS.md` §QRAMM-05, QRAMM-06, QRAMM-07, QRAMM-15 — locked requirements
- `.planning/ROADMAP.md` §"Phase 55: QRAMM Compliance Mapping View" — goal, success criteria, dependency chain

### Foundation Phases (MUST READ)
- `.planning/phases/51-qramm-core-infrastructure/51-CONTEXT.md` — ORM models, router design, scoring engine decisions; D-09 (no risk_engine imports from any qramm module)
- `.planning/phases/53-qramm-evidence-bridge/53-CONTEXT.md` — evidence bridge decisions; SESSION_BRACKET; CVI-only coverage
- `.planning/phases/54-qramm-assessment-ui-scorecard/54-CONTEXT.md` — 5-tab assessment layout, QRAMMContext shape, routing decisions (D-13/D-14)

### Compliance Staleness Pattern (mirror for QRAMM)
- `quirk/compliance/__init__.py` — `status_report()`, `STALENESS_THRESHOLD_DAYS`, `_pci()/_hipaa()/_soc2()/_iso()` builder pattern; `quirk qramm status` mirrors `quirk compliance status` CLI pattern exactly
- `.planning/phases/52-compliance-uplift-health-check/52-CONTEXT.md` — D-10: CLI subcommand intercept pattern in run_scan.py; D-13: staleness reuses existing status_report() shape

### Live Implementation
- `quirk/qramm/model_meta.py` — `QRAMM_MODEL` dict + `STALENESS_THRESHOLD_DAYS = 90` (pre-provisioned Phase 51; CLI surface is Phase 55)
- `quirk/qramm/questions.py` — `QRAMM_QUESTIONS` (120 entries); use to enumerate all practice areas for the compliance weight table
- `quirk/dashboard/api/routes/qramm.py` — existing QRAMM FastAPI router; new compliance-map endpoint goes here
- `src/dashboard/src/pages/qramm-assessment.tsx` — existing 5-tab assessment page; add 6th `[ Compliance Map ]` tab here
- `src/dashboard/src/context/QRAMMContext.tsx` — `QRAMMContext` shape; `sessionId` needed to call `/api/qramm/sessions/{id}/compliance-map`

### Frontend Patterns
- `src/dashboard/src/components/ui/table.tsx` — shadcn Table; use for the 8-framework coverage table
- `src/dashboard/src/components/ui/badge.tsx` — Badge component; use for "Scanner-informed" / "Manual only" tier badges
- `src/dashboard/src/components/ui/tabs.tsx` — existing Radix Tabs; 6th tab wires in exactly like the Scorecard tab

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/compliance/__init__.py:status_report()` — CLI output format pattern; `qramm_cmd.py` produces same column layout (version / last_verified / days_remaining / verdict)
- `quirk/qramm/model_meta.py:QRAMM_MODEL` — already has `qramm_version`, `last_verified`, `source_url`, `STALENESS_THRESHOLD_DAYS = 90`; the pytest gate and CLI just read this dict
- `src/dashboard/src/components/qramm/ScorecardTab.tsx` — closest analog for the 6th tab component; compliance map tab follows same self-contained component shape
- `src/dashboard/src/components/ui/table.tsx` — Table, TableHeader, TableBody, TableRow, TableCell — use for the framework coverage table
- `src/dashboard/src/components/ui/badge.tsx` — variant prop allows "Scanner-informed" (e.g., `variant="default"`) vs "Manual only" (e.g., `variant="secondary"`) styling

### Established Patterns
- **CLI intercept in run_scan.py:** `if len(sys.argv) > 2 and sys.argv[1] == "<subcommand>" and sys.argv[2] == "status"` → delegate to `quirk/cli/<subcommand>_cmd.py`. Phase 52 added `doctor_cmd.py`; Phase 55 adds `qramm_cmd.py`.
- **No risk_engine imports from qramm modules** (Phase 51 D-09): `compliance_map.py` must not import `quirk.engine.risk_engine` or any scanner module.
- **`datetime.now(timezone.utc)`** throughout — Phase 51 DEBT-01 replaced all `datetime.utcnow()` calls; staleness calculation in `qramm_cmd.py` must use `datetime.now(timezone.utc)`.
- **Pydantic response models inline in router** (Phase 51 D-11): define the compliance-map response model as an inline Pydantic class in `qramm.py` route file, not in `schemas.py`.
- **CSS variable color tokens** — all new React components use `hsl(var(--accent))` etc.; no hardcoded hex/hsl.

### Integration Points
- `quirk/dashboard/api/routes/qramm.py` — add `GET /api/qramm/sessions/{id}/compliance-map` endpoint; reads `QRAMM_COMPLIANCE_WEIGHTS` and `SCANNER_COVERAGE` from `compliance_map.py`, reads `score_json` from `qramm_sessions` row
- `quirk/run_scan.py:main()` — add `qramm status` intercept (follows `compliance status` intercept above it)
- `src/dashboard/src/pages/qramm-assessment.tsx` — add 6th `<TabsTrigger value="compliance">Compliance Map</TabsTrigger>` and corresponding `<TabsContent>` with the new `ComplianceMapTab` component
- `src/dashboard/src/context/QRAMMContext.tsx` — `sessionId` from context feeds the `GET /api/qramm/sessions/{id}/compliance-map` call in the tab component

</code_context>

<specifics>
## Specific Ideas

- **`QRAMM_COMPLIANCE_WEIGHTS` structure:** `Dict[str, Dict[str, float]]` where outer key = practice area (e.g., `"1.1"`, `"1.2"`, ..., `"4.3"`), inner key = framework short name (e.g., `"NIST_PQC"`, `"NSM10"`, `"CNSA2"`, `"ISO27001"`, `"ETSI_QS"`, `"PCI_DSS"`, `"CC"`, `"BSI_TR"`), value = 0.0–1.0 float. Planner defines the actual weight values based on QRAMM framework relevance.
- **Footnote text:** "Coverage reflects QUIRK scanner findings for CVI only — SGRM, DPE, ITR require manual assessment." Fixed string; not dynamic.
- **Badge labels:** "Scanner-informed" (green/default) for frameworks with CVI-mapped practices; "Manual only" (muted/secondary) for frameworks with no CVI exposure.
- **No "fully compliant" badge** — the requirements text is absolute; no success/compliant state is ever rendered for any framework, regardless of score.
- **`quirk qramm status` output columns:** `QRAMM Version`, `Last Verified`, `Days Remaining`, `Status` (FRESH ✓ / STALE ✗). Exit code mirrors `compliance status` — 0 = FRESH, 1 = STALE.

</specifics>

<deferred>
## Deferred Ideas

- **Evidence bridge expansion to SGRM/DPE/ITR** (QRAMM-F01) — When v4.8 extends the bridge, only `SCANNER_COVERAGE` in `compliance_map.py` needs updating (set SGRM/DPE/ITR to > 0). The compliance-map endpoint and UI are already structured to handle it.
- **Coverage percentage display** — User chose tier badges over percentages for this phase. A future phase could add capped % alongside badges once the coverage model is more mature.
- **`quirk qramm status --format json`** — Not needed in v4.7; exit code is the machine-readable signal. Could be added in a future enhancement phase.

</deferred>

---

*Phase: 55-qramm-compliance-mapping-view*
*Context gathered: 2026-05-08*
