# Phase 98: Executive Narrative + Score Transparency — Research

**Researched:** 2026-05-24
**Domain:** Python report rendering — shared content model across CLI markdown / Jinja2 HTML / Playwright PDF
**Confidence:** HIGH (all findings verified against live codebase source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Deterministic templating — NO LLM. Rule-based composition from existing score/findings data. Fully offline, reproducible, air-gap-safe. LLM path explicitly rejected.
- **D-02:** Top-risks business framing via an algorithm-class → impact-band static map keyed on crypto class + severity. Phase 98 stays at executive-summary tier; rich per-finding "so what" is Phase 99.
- **D-03:** Shared structured content model; format-specific rendering. Build narrative/top-risks/roadmap/score-decomposition ONCE as a structured content object (dataclasses/dicts). Both `executive.py` (CLI) and `html_renderer.py` + template (HTML/PDF) consume that single source. PDF stays HTML-derived (Playwright). Eliminates drift at the source, not just via tests.
- **D-03a:** A cross-surface parity test is still worthwhile as corroboration (belt-and-suspenders), planner decides shape.
- **D-04:** Impact×effort priority ordering WITHIN the existing now/next/later time-horizon buckets that `writer.py:_roadmap_markdown` already produces. Reuse current structure; add within-bucket prioritization.
- **D-05:** Relative effort/impact values from a static per-finding-type/crypto-class map. May co-locate/share with D-02's map.
- **D-06:** Single computed summary source + reconciliation guard. Derive BOTH exec headline rating language AND detail-table severity counts from one computed summary object, AND add a congruence guard that fails the report build / a test when the headline band is incompatible with worst-severity counts.
- **D-07:** Extend, do not rebuild. `executive.py:166-194` already renders Score Decomposition table (/25 per subscore) and the ÷1.5 rollup line. Gap is surfacing this identically across HTML and PDF via the D-03 shared model.

### Claude's Discretion

- Exact narrative wording/templates, the structure of the content-model dataclasses, the precise band thresholds in the algorithm-class and effort/impact maps, and test shapes.

### Deferred Ideas (OUT OF SCOPE)

- LLM narrative enrichment — rejected outright.
- PDF visual layout / typography / cover / branding — Phase 100 (backlog 999.2).
- Rich per-finding quantum-risk "so what" + actionable remediation guidance — Phase 99 (backlog 999.72).
- Code-signing certificate expiry as a finding — Phase 99 (WR-05 carry-in).
- DOCX editable export — Phase 100 deliverable.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXEC-01 | Reader sees an executive summary that opens with a plain-language readiness narrative (overall posture + what it means) before any finding tables | Narrative prose block added via shared content model; positioned before score card in HTML; before Score Drivers in CLI markdown |
| EXEC-02 | Executive summary surfaces the top prioritized risks framed by business impact, not as raw finding rows | D-02 static crypto-class → impact-band map produces top-N risk sentences; rendered as `.risks-list` in HTML, bullet list in CLI |
| EXEC-03 | Report includes a prioritized remediation roadmap — ordered actions with rationale and relative effort/impact | Extend `writer.py:_roadmap_markdown` and `roadmap_now/next/later` template vars with effort/impact metadata from D-05 static map |
| EXEC-04 | The executive narrative renders with consistent content across CLI markdown, HTML, and PDF | D-03 shared content model: single `ExecContent` object consumed by both `executive.py` and `html_renderer.py`; PDF is HTML-derived |
| TRANS-01 | Reports show the six-pillar subscore decomposition against budget that feeds the overall readiness number | Already present in CLI markdown (lines 177-194) and HTML template (lines 155-171); gap is wiring shared model so both surfaces source from same object |
| TRANS-02 | Reports explain how the overall score is computed (subscore weighting + ÷1.5 rollup) so the number is defensible | Rollup formula text block below decomposition table; already in CLI, needs parity in HTML via shared model |
| TRANS-03 | Executive summary headline score and severity language consistent with detailed findings tables | D-06 congruence guard: single computed `SummaryRecord` + `_check_congruence()` function that raises/blocks report on contradiction |
</phase_requirements>

---

## Summary

Phase 98 enriches QU.I.R.K.'s executive report layer across all three output surfaces (CLI markdown, HTML, PDF). The work is almost entirely a refactoring + extension of existing code — all required data already exists; the gaps are (1) a new shared content model to prevent CLI/HTML drift, (2) a narrative prose block derived from the existing `_build_interpretation` logic, (3) a top-risks section derived from a new static crypto-class → impact map, (4) impact×effort metadata injected into the existing roadmap structure, and (5) a congruence guard ensuring the headline band cannot contradict severity counts.

The TRANS-01/TRANS-02 requirements are largely satisfied in the CLI surface already: `executive.py:177-194` renders the Score Decomposition table and `÷1.5` rollup line, and `report.html.j2:155-171` renders the same decomposition table with `subscores.values() | sum ÷ 1.5` inline. The parity gap (D-07) is routing these through a shared content object so both surfaces are structurally guaranteed to carry the same data, not incidentally matching. The HTML template currently does NOT render narrative prose before the score card, does NOT have a top-risks list, and does NOT have effort/impact labels on roadmap items — these are the net-new additions.

The D-06 congruence guard is the most structurally significant addition: both headline rating language and severity counts must derive from a single `SummaryRecord` computed once, with an assertion that a "GOOD"/"EXCELLENT" band cannot co-exist with open CRITICAL findings. This guard must fail at report-build time (not just in CI) so a contradictory report is never emitted.

**Primary recommendation:** Introduce `quirk/reports/content_model.py` as a new module containing the `ExecContent` dataclass and builder function (`build_exec_content`). This module is the seam between scoring/findings data and both renderers. `executive.py:build_exec_markdown` and `html_renderer.py:render_html_report` each receive an `ExecContent` instance and extract what they need for format-specific rendering.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Readiness narrative prose (EXEC-01) | `quirk/reports/content_model.py` builder | Renderers consume, do not generate | Rule-based composition belongs in a single builder, not in each renderer |
| Top-risks business framing (EXEC-02) | `quirk/reports/content_model.py` (static map + selector) | Renderers present items | Static crypto-class → impact-band map is data; selection logic is a single function |
| Roadmap priority ordering (EXEC-03) | `quirk/intelligence/roadmap.py` items + D-05 static map | `writer.py` / template present sorted items | Roadmap items are already built in `roadmap.py`; effort/impact metadata is a co-located static map |
| Cross-surface content parity (EXEC-04) | `quirk/reports/content_model.py` (single source) | Tests corroborate | The shared model is the guarantee; tests are belt-and-suspenders |
| Score decomposition display (TRANS-01/02) | Already in both surfaces; shared model formalises the link | — | `executive.py:177-194` and `report.html.j2:155-171` both already render this; Phase 98 wires them to the same content object |
| Congruence guard (TRANS-03) | `quirk/reports/content_model.py:_check_congruence()` | Called by `writer.py:write_reports` before any renderer | Must fire at build time — must be in the orchestration seam, not inside a renderer |
| HTML rendering | `quirk/reports/html_renderer.py` + `report.html.j2` | — | Jinja2 template is the format layer |
| PDF rendering | `quirk/reports/html_renderer.py:render_pdf_report` (Playwright) | pypdf for metadata post-processing | PDF is HTML-derived; no separate PDF content logic |
| CLI markdown rendering | `quirk/reports/executive.py:build_exec_markdown` | — | Markdown text assembly |
| md_cell escaping | `quirk/reports/_md_escape.py:md_cell` | All markdown table cells | HARDEN-01 mandate; any finding-derived text in new narrative cells must be wrapped |

---

## Standard Stack

No new external packages are introduced in Phase 98. All work uses the existing stack.

### Core (already installed)

| Library | Version | Purpose | Role in Phase 98 |
|---------|---------|---------|-----------------|
| Python dataclasses (`@dataclass`) | stdlib | Structured content model | `ExecContent` dataclass in `content_model.py` |
| Jinja2 | installed (html_renderer.py already uses it) | HTML template rendering | Template extended with narrative, risks, rollup formula blocks |
| Playwright (lazy import) | installed optional | PDF via headless Chromium | PDF is HTML-derived; no change to `render_pdf_report` |
| pypdf (lazy import) | installed optional | PDF metadata injection | No change to `_inject_pdf_metadata` |
| `quirk/reports/_md_escape.py:md_cell` | project code | GFM table cell escaping | All new finding-derived narrative/roadmap cells must be wrapped |

### No New Dependencies

Phase 98 adds zero new pip dependencies. The static maps (D-02/D-05) are plain Python dicts. The `@dataclass` decorator is stdlib. The narrative template strings are Python f-strings or simple string joins.

**Package Legitimacy Audit:** Not applicable — no new packages installed.

---

## Architecture Patterns

### System Architecture Diagram

```
                         write_reports() [writer.py]
                               |
                  compute_readiness_score() ──► score_raw (has: score, rating,
                  build_phased_roadmap()          subscores, drivers)
                  build_evidence_summary()        roadmap_raw (has: items[])
                               |
                    ┌──────────▼──────────┐
                    │  build_exec_content() │  ← NEW: quirk/reports/content_model.py
                    │  (ExecContent)        │
                    │  · _check_congruence()│  ← D-06 guard (raises ReportCongruenceError)
                    │  · narrative prose    │  ← D-01 rule-based
                    │  · top_risks[]        │  ← D-02 static map
                    │  · roadmap_items[]    │  ← D-04/D-05 with effort/impact
                    │  · score_decomp{}     │  ← D-07 pass-through
                    └─────────┬──────────┘
                               │ ExecContent instance
                    ┌──────────┴──────────────────────────┐
                    │                                      │
         build_exec_markdown()                   render_html_report()
         [executive.py]                          [html_renderer.py]
         CLI .md file                            Jinja2 → .html
                                                      │
                                               render_pdf_report()
                                               Playwright → .pdf
                                               _inject_pdf_metadata()
                                               pypdf → /Title /Author
```

**Data flow:** `write_reports` computes the canonical score and roadmap once, passes both to `build_exec_content()` which applies the D-01 narrative rules, D-02 risk map, D-04/D-05 priority ordering, and D-06 congruence check. The resulting `ExecContent` object flows into both renderers. Neither renderer generates content; both only format it.

### Recommended Project Structure

```
quirk/reports/
├── __init__.py
├── _md_escape.py          # existing — md_cell, no changes
├── content_model.py       # NEW — ExecContent dataclass + build_exec_content()
│   ├── ALGO_IMPACT_MAP    # D-02 static crypto-class → impact-band map
│   ├── EFFORT_IMPACT_MAP  # D-05 static finding-type → (effort, impact) map
│   ├── ExecContent        # @dataclass
│   ├── build_exec_content()
│   └── _check_congruence()
├── executive.py           # MODIFIED — build_exec_markdown receives ExecContent
├── html_renderer.py       # MODIFIED — render_html_report receives ExecContent
├── technical.py           # existing — no changes
├── writer.py              # MODIFIED — orchestrates build_exec_content() call
└── templates/
    └── report.html.j2     # MODIFIED — new .narrative-block, .risks-list, rollup, priority-label
```

### Pattern 1: ExecContent Dataclass (D-03 shared content model)

**What:** A single `@dataclass` produced once by `build_exec_content()` and consumed by both renderers. Contains all executive-layer content as Python objects (strings, lists of dicts). Renderers format; they do not derive content.

**When to use:** Any time Phase 98 content (narrative, top-risks, roadmap priority) needs to appear in a renderer.

```python
# Source: project convention — existing codebase uses plain dicts; dataclass is appropriate
# here because the shape is fixed and needs type clarity for two consumers.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class RiskItem:
    """One row in the top-risks list (EXEC-02)."""
    risk_label: str        # e.g. "Harvest-now-decrypt-later exposure"
    impact_sentence: str   # e.g. "adversaries may already be archiving..."
    severity: str          # "CRITICAL" | "HIGH" | "MEDIUM"

@dataclass
class RoadmapItem:
    """Roadmap item with D-05 effort/impact metadata injected (EXEC-03)."""
    phase: str             # "NOW" | "NEXT" | "LATER"
    title: str
    why: str
    owner_placeholder: str
    timeframe: str
    effort: str            # "LOW" | "MEDIUM" | "HIGH"
    impact: str            # "HIGH" | "MEDIUM" | "LOW"
    priority_score: int    # computed: IMPACT_RANK * EFFORT_RANK for within-bucket ordering

@dataclass
class ExecContent:
    """Single structured content object consumed by both renderers (D-03)."""
    # EXEC-01: narrative
    narrative_lead: str            # band-specific opening sentence
    narrative_drivers: List[str]   # score driver clauses
    # EXEC-02: top risks
    top_risks: List[RiskItem]
    # EXEC-03: roadmap with effort/impact
    roadmap_items: List[RoadmapItem]   # sorted within each phase bucket
    # TRANS-01/02: score transparency (pass-through from score_raw)
    score_total: int
    score_band: str
    subscores: Dict[str, Any]      # {hygiene: int, modern_tls: int, ...}
    raw_sum: int                   # sum(subscores.values())
    # TRANS-03: severity counts for congruence check (already computed)
    sev_counts: Dict[str, int]     # {"CRITICAL": n, "HIGH": n, ...}
```

**Key insight:** Renderers receive an `ExecContent` and call `.narrative_lead`, `.top_risks`, etc. They do not re-derive anything.

### Pattern 2: Congruence Guard (D-06)

**What:** A function called in `write_reports()` before any renderer runs. Raises `ReportCongruenceError` if the headline band is incompatible with the severity count facts.

**When to use:** Always — called unconditionally from `write_reports`.

```python
# Incompatibility rules (based on D-06 contract):
# "EXCELLENT" or "GOOD" band with any CRITICAL finding → congruence failure
# "MODERATE" band is allowed with HIGH but not CRITICAL
# "FAIR" or "POOR" bands are always compatible with any severity mix
_BAND_CRITICAL_THRESHOLD = {
    "EXCELLENT": 0,   # zero CRITICAL allowed with EXCELLENT
    "GOOD": 0,        # zero CRITICAL allowed with GOOD
    "MODERATE": 0,    # zero CRITICAL allowed with MODERATE
    "FAIR": None,     # no restriction
    "POOR": None,     # no restriction
}

class ReportCongruenceError(ValueError):
    """Raised when exec headline band contradicts severity counts (D-06/TRANS-03)."""
    pass

def _check_congruence(band: str, sev_counts: Dict[str, int]) -> None:
    """D-06 / TRANS-03: fail-fast if headline band contradicts finding severity counts.

    Raises ReportCongruenceError with message matching the UI-SPEC copy:
      "Report generation halted: executive headline '{band}' is inconsistent
       with {n} CRITICAL finding(s). Review findings before generating the report."
    """
    threshold = _BAND_CRITICAL_THRESHOLD.get(band)
    if threshold is None:
        return  # FAIR / POOR — no restriction
    n_critical = sev_counts.get("CRITICAL", 0)
    if n_critical > threshold:
        raise ReportCongruenceError(
            f"Report generation halted: executive headline '{band}' is inconsistent "
            f"with {n_critical} CRITICAL finding(s). Review findings before generating the report."
        )
```

### Pattern 3: Writer Orchestration Seam (D-03 integration point)

**What:** `write_reports()` is the single call site that must be modified to insert `build_exec_content()` and pass the result to both renderers.

**Where in writer.py:** Between step 3 (intelligence outputs) and step 3b (HTML report). Currently `render_html_report` receives raw `score`, `conf`, and `roadmap_items` dicts. After Phase 98, it additionally receives an `ExecContent` object.

```python
# In write_reports(), after score_raw / roadmap_raw are computed:
from quirk.reports.content_model import build_exec_content, ReportCongruenceError

exec_content = build_exec_content(
    score_raw=score_raw,
    findings=findings,
    roadmap_items=roadmap_items,
)
# D-06: guard fires before any file is written
# The error message matches UI-SPEC copywriting contract

# Then pass exec_content to both renderers:
exec_md = build_exec_markdown(cfg, endpoints, findings, exec_content=exec_content)
render_html_report(..., exec_content=exec_content)
```

### Pattern 4: Narrative Lead Sentences (D-01)

**What:** Four band-keyed lead sentences. Bands are derived from `_score_band()` in `html_renderer.py` (which already exists and is the canonical band function). The CLI path uses `score_raw['rating']` from `compute_readiness_score` (which uses `_rating()` in `scoring.py`).

**Critical gap to close:** `_score_band()` in `html_renderer.py` and `_rating()` in `scoring.py` use DIFFERENT band labels for the SAME score values. `_rating()` returns `"EXCELLENT"/"GOOD"/"MODERATE"/"FAIR"/"POOR"`; `_score_band()` in `html_renderer.py` returns `"EXCELLENT"/"GOOD"/"MODERATE"/"FAIR"/"POOR"` with the same thresholds. These happen to match. However, the UI-SPEC copy uses `"GOOD"/"FAIR"/"POOR"/"CRITICAL"` as band names, with "CRITICAL" not present in either current function. The UI-SPEC `## Copywriting Contract` table has 4 bands: GOOD, FAIR, POOR, CRITICAL — but the current codebase has 5: EXCELLENT, GOOD, MODERATE, FAIR, POOR. Phase 98's narrative map should use the codebase's 5-band system (EXCELLENT → GOOD lead, MODERATE → FAIR lead, etc.) or collapse — this is Claude's discretion.

**Recommendation:** Map the 5 codebase bands to the 4 UI-SPEC narrative leads:
- `"EXCELLENT"` → use the GOOD narrative lead (strong posture)
- `"GOOD"` → use the GOOD narrative lead
- `"MODERATE"` → use the FAIR narrative lead (gaps requiring attention)
- `"FAIR"` → use the POOR narrative lead (significant exposure)
- `"POOR"` → use the CRITICAL narrative lead (immediate remediation)

This collapses 5 scoring bands into 4 narrative tones, which is appropriate since narrative tone differences between EXCELLENT and GOOD are not meaningfully distinct.

### Pattern 5: D-02 Static Algorithm-Class → Impact-Band Map

**What:** A dict keyed on `(crypto_class, severity)` tuples (or just `crypto_class`) mapping to a `RiskItem` prototype. This map is new to Phase 98.

**Where it lives:** `quirk/reports/content_model.py` — co-located with the ExecContent dataclass. May share the module with D-05's effort/impact map (planner discretion).

**Key entries to include** (from UI-SPEC copywriting contract):
```python
ALGO_IMPACT_MAP = {
    # crypto_class → (risk_label, impact_sentence) — severity determines inclusion threshold
    "RSA":      ("Harvest-now-decrypt-later exposure",
                 "adversaries may already be archiving encrypted traffic for future decryption."),
    "ECC":      ("Harvest-now-decrypt-later exposure",
                 "adversaries may already be archiving encrypted traffic for future decryption."),
    "WEAK_HASH":("Integrity risk",
                 "weak hashing algorithms undermine tamper-evidence guarantees."),
    "WEAK_KEY_EXCHANGE": ("Authentication exposure",
                 "weak key exchange allows credential interception."),
    # … expand per Claude's discretion
}
```

**Finding → crypto class mapping:** Findings carry `title`, `description`, and optionally `category`/`check_id` fields. The risk selector function inspects finding severity and title keywords to choose from the map. Keep it simple — this is Phase 98 executive-tier framing, not per-finding "so what" (Phase 99).

### Pattern 6: D-05 Static Effort/Impact Map for Roadmap Items

**What:** A dict keyed on roadmap item `title` (or a title keyword) mapping to `(effort_band, impact_band)` strings.

**Where it lives:** `quirk/reports/content_model.py` — may share the map module with D-02.

**Ordering algorithm:** Within each phase bucket (NOW/NEXT/LATER), sort items by `priority_score = IMPACT_RANK[impact] * (3 - EFFORT_RANK[effort])` descending, so high-impact/low-effort items sort first. Tie-break by original roadmap `_priority` field.

```python
EFFORT_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
IMPACT_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
```

**Roadmap items produced by `build_phased_roadmap`:** The existing `roadmap.py` produces items with keys: `phase`, `title`, `why`, `owner_placeholder`, `dependencies`, `timeframe`, `_priority`. The D-05 map enriches each item by looking up its title (or title-prefix) in the static map to attach `effort` and `impact` bands. Items not found in the map receive `effort="MEDIUM", impact="MEDIUM"` as safe defaults.

### Anti-Patterns to Avoid

- **Generating narrative inside a renderer:** Renderers must only format `ExecContent` fields; they must not call scoring functions or derive content from `findings` directly. The seam is `content_model.py`.
- **Two independent severity-count computations:** `build_exec_content()` must compute `sev_counts` once and inject it into `ExecContent`. The HTML renderer and the CLI renderer must both read `exec_content.sev_counts`, not recount independently. The D-06 guard must use the same `sev_counts` that the renderers display.
- **Calling `_score_band()` inside the template:** The Jinja template currently calls `_score_band(total_score)` via the Python side to produce `score_band`. This is already correct; do not duplicate band logic in the template.
- **Using `md_cell()` for HTML template content:** `md_cell` is for GFM markdown table cell escaping only. HTML template content uses the existing `| sanitize` Jinja filter (from `quirk/util/sanitize.py`). New HTML template narrative content must pipe scanner-derived strings through `| sanitize`.
- **Adding an unconditional top-level import of Playwright or pypdf:** Both are already lazy-imported inside their respective functions. Do not add them at module scope.

---

## Current State Audit: What Exists vs. What Is Missing

### TRANS-01/02: Score Decomposition + Rollup Formula

**CLI markdown (`executive.py:177-194`):** [VERIFIED: read source]
```
### Score Decomposition
| Category | Score | Budget |
|----------|-------|--------|
| Hygiene  | 20    | /25    |
...
**Rollup:** 121 ÷ 1.5 = **80 / 100**
```
Status: COMPLETE in CLI. No gaps.

**HTML template (`report.html.j2:155-171`):** [VERIFIED: read source]
```jinja
{% if subscores %}
<h3>Score Decomposition</h3>
<table>...</table>
<p><strong>Rollup:</strong>
  {{ subscores.values() | sum }} &divide; 1.5 = <strong>{{ total_score }} / 100</strong>
</p>
{% endif %}
```
Status: PRESENT in HTML. However, this is currently rendered from the raw `subscores` dict passed directly to `template.render()`, not from a shared content object. D-07 says extend, not rebuild — Phase 98 must wire this through `ExecContent.subscores` to guarantee structural identity, but the table itself does not need to change.

**Gap:** `subscores` in the template context is populated at `html_renderer.py:207` as `subscores=score.get("subscores", {})`. After Phase 98, this must come from `exec_content.subscores` to fulfill D-03. The rendering HTML is already correct; only the data path changes.

### EXEC-01: Narrative Prose Block

**CLI markdown:** No standalone prose block exists. `_build_interpretation()` produces bullet points (not prose paragraphs) appended under `## Interpretation` — AFTER the score/roadmap content. Per EXEC-01, the narrative must appear BEFORE finding tables.

**Current `executive.py` section order:**
1. `## Executive Summary` (metadata)
2. `## Quantum Readiness Score` (score + drivers + **Score Decomposition**)
3. `## Confidence & Coverage`
4. `## Discovery and Coverage`
5. `## Algorithm Inventory`
6. `## Findings Overview (Executive-Relevant)` ← finding severity counts
7. `## Interpretation` ← bullet narrative (currently here — WRONG position for EXEC-01)
8. `## Transition Roadmap`
9. `## Recommended Migration Paths`
10. `## Recommended Next Actions`

**Required order after Phase 98:**
1. `## Executive Summary` (metadata)
2. **NEW: Readiness Assessment** narrative prose block (EXEC-01 — before any finding table)
3. `## Quantum Readiness Score` (score card + **Score Decomposition** + rollup formula)
4. **NEW: Priority Business Risks** (EXEC-02)
5. `## Confidence & Coverage`
6. `## Discovery and Coverage`
7. `## Algorithm Inventory`
8. `## Findings Overview (Executive-Relevant)` ← finding severity counts
9. `## Transition Roadmap` (with effort/impact ordering per EXEC-03)
10. ...

**HTML template current section order (executive-summary section):**
1. Meta table
2. Score card
3. Score Decomposition table
4. Findings Breakdown (severity badges)
5. Score Drivers
6. Top Findings table
7. Transition Roadmap

**Required HTML order after Phase 98:**
1. **NEW: narrative prose block** (`.narrative-block` div — before score card)
2. Score card
3. Score Decomposition table + rollup formula
4. **NEW: Priority Business Risks** (`.risks-list`)
5. Findings Breakdown (severity badges)
6. Score Drivers
7. Top Findings table
8. Transition Roadmap (with `.priority-label` spans)

### EXEC-02: Top-Risks Section

**CLI:** Not present. Must be added as a new section using bullet list formatting from `ExecContent.top_risks`.

**HTML:** Not present. Must be added as a `.risks-list` `<ul>` element (UI-SPEC CSS already defined; no new CSS colors needed).

### EXEC-03: Roadmap Effort/Impact Priority

**CLI (`executive.py:259-268`):** Renders roadmap items as `- **title** — why` per phase bucket. No effort/impact metadata.

**HTML (`report.html.j2:211-223`):** Renders `<div class="roadmap-item">` per item with title + why. No effort/impact metadata.

**`_roadmap_markdown` in `writer.py:113-129`:** Renders the standalone roadmap markdown file. No effort/impact.

**All three surfaces need:** `.priority-label` span / text appended to each roadmap item showing effort + impact bands. The roadmap items array (`roadmap_raw["items"]`) does not currently carry effort/impact fields — these are added by `build_exec_content()` from the D-05 static map.

### TRANS-03: Congruence Guard

**Current state:** Does not exist. The HTML renderer's `_score_band()` and the executive markdown's `score_raw['rating']` are derived independently and from the same underlying score, so they do not currently contradict each other. However, there is no guard preventing a band like "GOOD" from appearing alongside "7 CRITICAL" in findings — the score and findings are independent signals.

**What to add:** `_check_congruence(band, sev_counts)` called in `write_reports()` before any renderer.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML output escaping | Custom HTML entity encoder | Jinja2 `autoescape` + `| sanitize` filter (already in html_renderer.py) | Autoescape is already active for .j2 templates; sanitize strips embedded tags/URLs |
| GFM table cell escaping | String replace ad hoc | `md_cell()` from `quirk/reports/_md_escape.py` | HARDEN-01 mandate; handles pipe, newline, CRLF, control chars |
| Score band computation | New band function | `_score_band()` in html_renderer.py (for HTML path) / `_rating()` in scoring.py (for CLI path) — Phase 98 unifies via ExecContent.score_band | Both already exist and are tested |
| Roadmap item structure | Custom roadmap builder | Extend output of `build_phased_roadmap()` in `quirk/intelligence/roadmap.py` | Already produces NOW/NEXT/LATER bucketed items with title/why/phase/priority |
| PDF rendering | New PDF library | `render_pdf_report()` already wraps Playwright with graceful fallback | Playwright path already exists; PDF parity is free once HTML consumes ExecContent |

**Key insight:** All required data already flows through the codebase. Phase 98 is primarily a refactoring to assemble a shared content object and route it to both renderers, plus adding the static maps and the congruence guard.

---

## Common Pitfalls

### Pitfall 1: Score Key Name Mismatch (`score` vs. `total`)

**What goes wrong:** `executive.py:build_exec_markdown()` calls `compute_readiness_score()` directly and accesses `score_raw['score']` (the canonical key). `writer.py:write_reports()` wraps that result as `score = {"total": score_raw["score"], ...}` and passes `score.get("total")` to `html_renderer.py`. If `build_exec_content()` is called from `write_reports()` and receives the writer's wrapped `score` dict, it must use `score.get("total")`. If called from within `executive.py` (which calls `compute_readiness_score()` independently), it uses `score_raw.get("score")`.

**Root cause:** Two different dict shapes in flight at the same time — the canonical scoring engine output (`score`, `rating`, `subscores`, `drivers`) vs. the writer compat wrapper (`total`, `subscores`, `drivers`).

**How to avoid:** `build_exec_content()` should accept the canonical scoring engine output (`score_raw`) — i.e., be called from within the `write_reports()` path BEFORE the compat wrapper is created, or accept both shapes via a normalisation step. The recommended approach: call `build_exec_content(score_raw=score_raw, ...)` from `write_reports()` immediately after `score_raw = compute_readiness_score(...)`, before the compat wrapper.

**Warning signs:** `ExecContent.score_total` is `None` or 0 despite a valid scan.

### Pitfall 2: Congruence Guard Placement

**What goes wrong:** If the guard is placed inside a renderer (e.g., inside `build_exec_markdown`), then the HTML report is still generated before the guard fires, or the guard fires for CLI but not HTML. The guard must be the FIRST action after `build_exec_content()` in `write_reports()`, before any file I/O.

**How to avoid:** Place `_check_congruence()` call in `writer.py:write_reports()` immediately after `exec_content = build_exec_content(...)`. The `ReportCongruenceError` propagates to the caller (CLI command) which surfaces the UI-SPEC error message.

### Pitfall 3: HTML Template `subscores.values() | sum` with Empty Dict

**What goes wrong:** The current template at line 169 calls `{{ subscores.values() | sum }}`. If `subscores` is an empty dict (edge case: scan produced no evidence), `sum` returns 0, which is safe. However, when `ExecContent.subscores` replaces the raw dict, if the dataclass carries a typed `Dict[str, int]` with default `None` subscores filled as `0`, the sum will be `0 ÷ 1.5 = 0` rather than `—`. This is acceptable but should be tested.

**How to avoid:** Pass `subscores=exec_content.subscores or {}` to the template; keep the `{% if subscores %}` guard already in the template.

### Pitfall 4: Narrative Placed After Finding Table in CLI

**What goes wrong:** The existing `_build_interpretation()` bullets appear under `## Interpretation` AFTER `## Findings Overview`. EXEC-01 requires the narrative to appear BEFORE any finding table. Moving the section requires careful re-ordering of `lines.append()` calls in `build_exec_markdown()`.

**How to avoid:** The narrative block (from `ExecContent.narrative_lead + narrative_drivers`) must be appended to `lines` immediately after the `## Executive Summary` header block — before the `## Quantum Readiness Score` section. The old `## Interpretation` section with bullet points can be removed or preserved as a secondary detail; the new narrative block is the primary EXEC-01 deliverable.

### Pitfall 5: `| sanitize` vs. `md_cell` Confusion

**What goes wrong:** `md_cell` is for GFM markdown table cells. New narrative prose in the Jinja template must use `| sanitize` — not `md_cell` (which is a Python function imported only in `.py` files). Applying `md_cell` to template variables is a Python-level step (before template rendering) not a Jinja filter.

**How to avoid:** In `html_renderer.py`, narrative content derived from finding-derived text (e.g., risk sentences that embed finding titles) should be sanitized via `sanitize_scanner_text()` before being placed in `ExecContent`. In the template, all `ExecContent`-derived text that comes from scanner input should be piped through `| sanitize`. Static strings (the narrative lead, the rollup formula prose) are template-static and do not need sanitization.

### Pitfall 6: `_build_interpretation` Partial Overlap With New Narrative

**What goes wrong:** `_build_interpretation()` currently produces bullets that partially overlap with the new `ExecContent.narrative_lead` and `narrative_drivers`. After Phase 98, if both the old `## Interpretation` bullets AND the new `## Readiness Assessment` narrative prose exist in the CLI output, the report contains duplicate/redundant content.

**How to avoid:** The planner must decide: (a) replace `## Interpretation` with the new narrative section entirely, or (b) keep `## Interpretation` as a detail section and add the narrative before it. Given the EXEC-01 requirement that narrative appears before finding tables, option (a) is cleaner. The `_build_interpretation()` function can be removed from the CLI path, with its bullet content subsumed by `ExecContent.narrative_drivers`.

---

## Code Examples

### Current Score Decomposition in CLI (lines 177-194 — do not rebuild)

```python
# Source: quirk/reports/executive.py:177-194 [VERIFIED: read source]
_SUBSCORE_LABELS = [
    ("hygiene",         "Hygiene"),
    ("modern_tls",      "Modern TLS"),
    ("identity_trust",  "Identity"),
    ("agility_signals", "Agility"),
    ("data_at_rest",    "Data at Rest"),
    ("data_in_motion",  "Data in Motion"),
]
subscores = score_raw.get("subscores") or {}
lines.append("### Score Decomposition")
lines.append("")
lines.append("| Category | Score | Budget |")
lines.append("|----------|-------|--------|")
for key, label in _SUBSCORE_LABELS:
    lines.append(f"| {label} | {subscores.get(key, '—')} | /25 |")
raw_sum = sum(subscores.get(k, 0) for k, _ in _SUBSCORE_LABELS)
lines.append("")
lines.append(f"**Rollup:** {raw_sum} ÷ 1.5 = **{score_raw['score']} / 100**")
```

After Phase 98: same logic, but `subscores` and `score_raw['score']` sourced from `exec_content.subscores` and `exec_content.score_total`.

### Current HTML Score Decomposition (lines 155-171 — do not rebuild)

```jinja
{# Source: quirk/reports/templates/report.html.j2:155-171 [VERIFIED: read source] #}
{% if subscores %}
<h3>Score Decomposition</h3>
<table>
  <thead><tr><th>Category</th><th>Score</th><th>Budget</th></tr></thead>
  <tbody>
    <tr><td>Hygiene</td><td>{{ subscores.get('hygiene', '—') }}</td><td>/25</td></tr>
    ...
  </tbody>
</table>
<p><strong>Rollup:</strong>
  {{ subscores.values() | sum }} &divide; 1.5 = <strong>{{ total_score }} / 100</strong>
</p>
{% endif %}
```

After Phase 98: `subscores` passes `exec_content.subscores`; no structural change.

### Current Roadmap Item Rendering (HTML — needs `.priority-label` span added)

```jinja
{# Source: report.html.j2:211-223 [VERIFIED: read source] #}
{% for item in items %}
<div class="roadmap-item">
  <strong>{{ item.get('title','') | sanitize }}</strong><br>
  <span>{{ item.get('why','') | sanitize }}</span>
</div>
{% endfor %}
```

After Phase 98 (add priority-label inside roadmap-item):
```jinja
<div class="roadmap-item">
  <strong>{{ item.title | sanitize }}</strong><br>
  <span>{{ item.why | sanitize }}</span>
  <span class="priority-label">{{ item.effort }} EFFORT &nbsp;·&nbsp; {{ item.impact }} IMPACT</span>
</div>
```

### writer.py Integration Seam

```python
# Source: quirk/reports/writer.py:212-224 [VERIFIED: read source — current state]
# After Phase 98 modification:
from quirk.reports.content_model import build_exec_content, ReportCongruenceError

# ... after score_raw and roadmap_raw are computed ...
exec_content = build_exec_content(
    score_raw=score_raw,
    findings=findings,
    roadmap_items=roadmap_raw.get("items", []),
)
# D-06 guard: ReportCongruenceError propagates to CLI before any file is written

exec_md = build_exec_markdown(cfg, endpoints, findings, exec_content=exec_content)
# ...
render_html_report(
    path=html_path,
    cfg=cfg,
    endpoints=endpoints,
    findings=findings,
    score=score,
    conf=conf,
    roadmap_items=roadmap_items,
    exec_content=exec_content,   # new kwarg
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No subscore decomposition displayed | 6-pillar /25 decomposition + ÷1.5 rollup in CLI and HTML | Phase 88 (D-07/SCORE-XPARENCY-01) | TRANS-01/02 partially satisfied in CLI; HTML template also has it |
| Separate assessment/readiness_score.py engine | Single canonical `compute_readiness_score()` in scoring.py | Phase 88 / v5.0 Stabilization | Single scoring engine; data parity guaranteed at source |
| Roadmap items without merge-dedup | `_add_candidate()` merge rule: earlier-phase/higher-priority wins | Phase 73 (D-06/WR-08) | Deterministic roadmap regardless of candidate insertion order |
| No score↔severity consistency guard | Currently no guard exists | — | Phase 98 adds `_check_congruence()` |
| Narrative as bullet list under `## Interpretation` (post-findings) | Phase 98 moves narrative to prose block before findings | Phase 98 | EXEC-01 compliance |

**Deprecated/outdated:**
- `quirk/assessment/readiness_score.py`: Deleted in v5.0 stabilization. Do not reference.
- `quirk/engine/migration_planner.py`: Deleted in Phase 83/CLEAN-01. `categorize_waves()` is now inlined in `writer.py`.

---

## Validation Architecture

> `workflow.nyquist_validation` not set to `false` in config — section included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pytest.ini` (exists — verified by presence of existing test runs) |
| Quick run command | `python -m pytest tests/test_exec_content_model.py tests/test_congruence_guard.py tests/test_exec_narrative_ordering.py tests/test_cross_surface_parity.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEC-01 | Narrative prose block appears before any finding table in CLI output | unit | `pytest tests/test_exec_narrative_ordering.py::test_narrative_before_findings_cli -x` | ❌ Wave 0 |
| EXEC-01 | Narrative prose block appears before `<table>` in HTML output | unit | `pytest tests/test_exec_narrative_ordering.py::test_narrative_before_table_html -x` | ❌ Wave 0 |
| EXEC-02 | Top-risks list present in CLI output with business-impact sentences | unit | `pytest tests/test_exec_content_model.py::test_top_risks_populated -x` | ❌ Wave 0 |
| EXEC-02 | `.risks-list` element present in HTML output with at least one item when findings exist | unit | `pytest tests/test_exec_narrative_ordering.py::test_risks_list_in_html -x` | ❌ Wave 0 |
| EXEC-03 | Roadmap items carry effort/impact metadata; items within a bucket are sorted high-impact-first | unit | `pytest tests/test_exec_content_model.py::test_roadmap_priority_ordering -x` | ❌ Wave 0 |
| EXEC-03 | Priority labels appear in HTML roadmap items | unit | `pytest tests/test_exec_narrative_ordering.py::test_priority_labels_in_html_roadmap -x` | ❌ Wave 0 |
| EXEC-04 | CLI narrative lead and HTML narrative lead are identical strings | unit | `pytest tests/test_cross_surface_parity.py::test_narrative_content_parity -x` | ❌ Wave 0 |
| EXEC-04 | CLI top-risks and HTML top-risks carry identical item count and labels | unit | `pytest tests/test_cross_surface_parity.py::test_top_risks_parity -x` | ❌ Wave 0 |
| TRANS-01 | `ExecContent.subscores` dict passes all six pillar keys | unit | `pytest tests/test_exec_content_model.py::test_subscores_all_keys_present -x` | ❌ Wave 0 |
| TRANS-01 | Score decomposition table present in HTML (already exists — regression gate) | unit | `pytest tests/test_score_transparency.py -x` | ✅ exists |
| TRANS-02 | Rollup formula text present in HTML output | unit | `pytest tests/test_exec_narrative_ordering.py::test_rollup_formula_in_html -x` | ❌ Wave 0 |
| TRANS-03 | `_check_congruence("GOOD", {"CRITICAL": 3})` raises `ReportCongruenceError` | unit | `pytest tests/test_congruence_guard.py::test_good_band_with_critical_raises -x` | ❌ Wave 0 |
| TRANS-03 | `_check_congruence("FAIR", {"CRITICAL": 5})` does NOT raise | unit | `pytest tests/test_congruence_guard.py::test_fair_band_with_critical_ok -x` | ❌ Wave 0 |
| TRANS-03 | `write_reports()` raises/surfaces error message before writing any output file when guard fires | integration | `pytest tests/test_congruence_guard.py::test_guard_blocks_report_generation -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_exec_content_model.py tests/test_congruence_guard.py tests/test_exec_narrative_ordering.py tests/test_cross_surface_parity.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_exec_content_model.py` — covers ExecContent dataclass, `build_exec_content()` shape, top-risks population, roadmap priority ordering, subscores pass-through (EXEC-02, EXEC-03, TRANS-01)
- [ ] `tests/test_congruence_guard.py` — covers `_check_congruence()` all band cases, `ReportCongruenceError` message format matching UI-SPEC copy, `write_reports()` blocking on guard fire (TRANS-03)
- [ ] `tests/test_exec_narrative_ordering.py` — covers CLI narrative-before-findings ordering, HTML narrative-before-table ordering, risks-list in HTML, priority labels in HTML roadmap, rollup formula in HTML (EXEC-01, EXEC-02, EXEC-03, TRANS-02)
- [ ] `tests/test_cross_surface_parity.py` — covers narrative content identity across CLI/HTML (EXEC-04)

**Existing tests that must continue to pass (regression gates):**

- `tests/test_score_transparency.py` — Score Decomposition in CLI and scorecard (TRANS-01/02) — currently passing
- `tests/test_score_render_parity.py` — Single scoring engine identity (RENDER-CLI-01) — currently passing
- `tests/test_executive_score_guard.py` — `_build_interpretation()` score dict guard — currently passing
- `tests/test_html_report.py` — HTML report structure (wordmark, self-contained CSS, sections) — currently passing

---

## Security Domain

> `security_enforcement` not set to `false` — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase 98 is report rendering only |
| V3 Session Management | No | No session state |
| V4 Access Control | No | No new endpoints or auth gates |
| V5 Input Validation | **Yes** | `md_cell()` for CLI markdown; `| sanitize` Jinja filter for HTML; Playwright CSP + offline mode for PDF |
| V6 Cryptography | No | No new crypto operations |

### Known Threat Patterns for Report Rendering

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| GFM table cell injection (pipe, newline in finding-derived text) | Tampering | `md_cell()` from `_md_escape.py` — HARDEN-01 mandate; wrap all finding-derived narrative/roadmap text |
| HTML injection in template (finding title/description in narrative) | Tampering | Jinja2 `autoescape` (active for .j2 files) + `| sanitize` filter on all scanner-derived content |
| CSS injection via `--surface` / `--accent` variable values | Tampering | Variables are template-static hex values; no scanner input feeds CSS variables in Phase 98 |
| PDF metadata injection | Spoofing | `_inject_pdf_metadata()` uses locked constants `PDF_TITLE`/`PDF_AUTHOR` — no scanner input |

**HARDEN-01 obligation for Phase 98:** Any new narrative or roadmap text cells in `executive.py` that include finding-derived strings (e.g., finding titles embedded in risk sentences, driver reason text in narrative clauses) must be wrapped with `md_cell()`. Static narrative template strings (the lead sentence, rollup formula text) do not need wrapping. In the HTML template, scanner-derived text (from `exec_content` fields that carry finding-derived strings) must pipe through `| sanitize`.

---

## Environment Availability

Step 2.6: SKIPPED (no external tool dependencies — Phase 98 is pure Python code/config changes using the existing installed stack: Playwright and pypdf are already lazy-imported optional extras; no new tools are needed).

---

## Open Questions (RESOLVED)

1. **`_build_interpretation()` retention vs. removal**
   - What we know: currently produces bullet points under `## Interpretation` (post-findings). EXEC-01 requires narrative before findings.
   - What's unclear: whether the new `ExecContent.narrative_drivers` entirely replaces `_build_interpretation()` bullets, or whether both coexist (narrative prose before + old bullets after).
   - **RESOLVED (plan 98-02):** Remove the `## Interpretation` section from the CLI output path and subsume its content into `ExecContent.narrative_drivers`, rendered as the "Readiness Assessment" narrative block before the score section. The helper logic may be reused inside `build_exec_content()` but must not emit a separate post-findings section.

2. **Band label mapping (5 scoring bands → 4 UI-SPEC narrative leads)**
   - What we know: `_rating()` in `scoring.py` produces 5 bands (EXCELLENT/GOOD/MODERATE/FAIR/POOR). The UI-SPEC has 4 narrative leads (GOOD/FAIR/POOR/CRITICAL).
   - What's unclear: whether EXCELLENT should get its own narrative lead or share GOOD's.
   - **RESOLVED (plan 98-01, Claude's discretion per CONTEXT.md):** EXCELLENT → GOOD lead, MODERATE → FAIR lead, POOR → CRITICAL lead.

3. **D-06 guard severity threshold granularity**
   - What we know: The UI-SPEC error message is triggered when headline is `GOOD`/`EXCELLENT` while CRITICAL findings exist.
   - What's unclear: whether `MODERATE` + CRITICAL should also be blocked (the table in Pattern 2 above proposes yes).
   - **RESOLVED (plan 98-01 `_BAND_CRITICAL_THRESHOLD`, Claude's discretion per CONTEXT.md):** Block EXCELLENT/GOOD/MODERATE when any CRITICAL findings are open; allow FAIR/POOR with any severity mix.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_rating()` in `scoring.py` and `_score_band()` in `html_renderer.py` use the same thresholds | Architecture Patterns - Pattern 4 | Band mismatch between CLI and HTML headline ratings; would need a single band function |
| A2 | The 5-to-4 band mapping (EXCELLENT→GOOD lead, MODERATE→FAIR lead, POOR→CRITICAL lead) is acceptable | Architecture Patterns - Pattern 4 | Incorrect narrative tone for edge-band scores; low risk since planner has discretion |

**Verification of A1:** Both `_rating()` (scoring.py:96-105) and `_score_band()` (html_renderer.py:20-29) have been read directly. Both use identical thresholds: ≥85=EXCELLENT, ≥70=GOOD, ≥55=MODERATE, ≥35=FAIR, else POOR. [VERIFIED: read source] — A1 is confirmed, not assumed.

**If this table is nearly empty:** All primary claims are VERIFIED against the live codebase. A2 is the only genuine assumption, and it is planner/implementer discretion by CONTEXT.md.

---

## Sources

### Primary (HIGH confidence — verified by reading live source files)

- `quirk/reports/executive.py` — full file read; lines 1-309; score decomposition at 177-194, `_build_interpretation` at 17-104, `build_exec_markdown` at 111-308
- `quirk/reports/html_renderer.py` — full file read; `render_html_report` signature at 145-211, `render_pdf_report` at 239-291, `_score_band` at 20-29
- `quirk/reports/writer.py` — full file read; `write_reports` at 132-291, `_roadmap_markdown` at 113-129, compat wrapper at 166-177
- `quirk/reports/technical.py` — full file read; no severity count computation (counts are in executive.py and writer.py)
- `quirk/reports/templates/report.html.j2` — full file read; score decomposition at 155-171, roadmap items at 211-223
- `quirk/reports/_md_escape.py` — full file read; `md_cell` function signature and escaping rules
- `quirk/intelligence/scoring.py` — partial read; `_rating()` at 96-105, `SCORE_WEIGHTS` at 20-63, `compute_readiness_score` at 119+
- `quirk/intelligence/roadmap.py` — partial read; `build_phased_roadmap` at 99+, `_add_candidate` merge rule at 54-96
- `tests/test_score_transparency.py` — full read; existing gate for CLI/scorecard decomposition
- `tests/test_score_render_parity.py` — full read; existing single-engine parity gate
- `tests/test_executive_score_guard.py` — full read; existing `_build_interpretation` score-guard tests
- `.planning/phases/98-executive-narrative-score-transparency/98-CONTEXT.md` — full read; locked decisions D-01 through D-07
- `.planning/phases/98-executive-narrative-score-transparency/98-UI-SPEC.md` — full read; CSS classes, copy, color palette, typography constraints

### Secondary (MEDIUM confidence)

- `.planning/ROADMAP.md` — Phase 98 block, success criteria
- `.planning/REQUIREMENTS.md` — EXEC-01..04, TRANS-01..03 row definitions
- `.planning/HORIZON.md` — v5.2 milestone framing, scope guardrails
- `.planning/STATE.md` — accumulated decisions, v5.2-D-01 through D-07

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules read directly from live codebase
- Architecture: HIGH — data flow traced through all five modules; seam locations confirmed
- Pitfalls: HIGH — identified from actual key-name discrepancies and section-ordering analysis in live code
- Current state gaps: HIGH — verified by reading actual HTML template and executive.py against requirements

**Research date:** 2026-05-24
**Valid until:** 2026-06-24 (stable codebase; this research covers specific line numbers — re-verify if report modules are touched independently)
