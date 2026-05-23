# Phase 98: Executive Narrative + Score Transparency - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich the **executive layer** of QU.I.R.K.'s report so a consultant can hand a CISO a client-ready deliverable. Across all three output surfaces (CLI markdown, HTML, PDF) the report must:

1. Open the executive section with a plain-language readiness **narrative** (overall posture + what it means for the org) before any finding table (EXEC-01).
2. Surface **top prioritized risks framed by business impact**, not raw finding rows (EXEC-02).
3. Include a **prioritized remediation roadmap** — ordered actions with rationale + relative effort/impact (EXEC-03).
4. Show the **six-pillar subscore decomposition** (each /25) and the **÷1.5 rollup formula** so the headline number is defensible (TRANS-01, TRANS-02).
5. Render the **same narrative content across CLI/HTML/PDF** — format-appropriate presentation, identical story (EXEC-04).
6. Guarantee the **exec headline rating language is consistent with the detail findings tables** — no "GOOD" over "7 CRITICAL" (TRANS-03).

Requirements: EXEC-01, EXEC-02, EXEC-03, EXEC-04, TRANS-01, TRANS-02, TRANS-03.

**Explicitly OUT of scope (deferred — see Deferred Ideas):**
- PDF visual layout / typography / branding → **Phase 100** (backlog 999.2).
- Rich per-finding quantum-risk "so what" + remediation guidance → **Phase 99** (backlog 999.72).
- Code-signing cert expiry as a finding → Phase 99 (WR-05).

The HORIZON risk for this milestone is "scope creep into endless visual polish." Anchor on narrative + roadmap + transparency + consistency as the must-ship core; presentation quality is a later phase.

</domain>

<decisions>
## Implementation Decisions

### Narrative generation (EXEC-01, EXEC-02)
- **D-01: Deterministic templating — NO LLM.** The readiness narrative is produced by rule-based composition from the existing score/findings data: a rating-band lead sentence plus score-driver / finding-derived clauses. Fully offline, reproducible, air-gap-safe — consistent with QUIRK's current deterministic design. An LLM enrichment path was explicitly rejected (network dependency + nondeterminism unacceptable for a consulting deliverable).
- **D-02: Top-risks business framing via an algorithm-class → impact-band static map.** EXEC-02's "business impact" sentences are derived from a maintained map keyed on the finding's crypto class + severity (e.g. RSA/ECC → "harvest-now-decrypt-later exposure", weak-hash → "integrity risk"). This keeps Phase 98 at the **executive summary tier** — it does NOT build the rich per-finding "so what" content, which is Phase 99 (999.72). Hold this 98/99 line firmly.

### Cross-surface content parity (EXEC-04, success criterion 6)
- **D-03: Shared structured content model; format-specific rendering.** Build the narrative / top-risks / remediation-roadmap / score-decomposition **once** as a structured content object (dataclasses/dicts). Both the CLI-markdown emitter (`executive.py`) and the HTML/Jinja renderer (`html_renderer.py` + template) consume that single source; PDF stays HTML-derived (Playwright). This eliminates drift **at the source** rather than only testing for it — format controls presentation only, never content. A markdown→HTML conversion approach and a "keep separate + parity test" approach were both rejected in favor of the shared model.
- **D-03a (Claude discretion):** A cross-surface parity test is still worthwhile as corroboration, but with the shared model it is belt-and-suspenders, not the primary guarantee. Planner decides test shape.

### Remediation roadmap structure (EXEC-03)
- **D-04: Impact×effort priority ordering, within the existing time-horizon grouping.** Order actions by an impact×effort priority score (high impact / low effort first), presented inside the now/next/later time-horizon buckets `writer.py` already produces. Reuses current structure; adds defensible within-bucket prioritization. (Pure severity×quantum-agility ranking was rejected because it ignores effort and can bury quick wins.)
- **D-05: Relative effort/impact values come from a static per-finding-type map.** A maintained lookup keyed on finding type / crypto class → (effort, impact) bands. Deterministic and reviewable. This map is conceptually aligned with D-02's algorithm-class→impact map — the planner may co-locate / share them. (Deriving effort heuristically from severity+score-weights was rejected as too coarse.)

### Score↔severity consistency (TRANS-03, success criterion 5)
- **D-06: Single computed summary source + reconciliation guard.** Derive BOTH the exec headline rating language AND the detail-table severity counts from one computed summary object so they cannot structurally diverge, AND add a congruence guard that asserts the headline band is compatible with the worst-severity counts (e.g. cannot report "GOOD" while CRITICAL findings are open). The guard fails the report build / a test on violation — it prevents a contradictory report from being generated at runtime, not just in CI.

### Score transparency (TRANS-01, TRANS-02)
- **D-07: Extend, do not rebuild.** `executive.py:166-194` already renders a "Score Decomposition" table (/25 per subscore) and the `÷1.5` rollup line (D-07/SCORE-XPARENCY-01 from a prior phase). Phase 98 surfaces this **identically across HTML and PDF** via the D-03 shared content model — the markdown already has it; the gap is parity into the other surfaces. Do not re-derive the decomposition logic.

### Claude's Discretion
- Exact narrative wording/templates, the structure of the content-model dataclasses, the precise band thresholds in the algorithm-class and effort/impact maps, and test shapes — all planner/implementer discretion within the decisions above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` (Phase 98 block) — goal + the 6 success criteria that gate verification.
- `.planning/REQUIREMENTS.md` — EXEC-01..04, TRANS-01..03 row definitions.
- `.planning/HORIZON.md` §"v5.2 — Consulting-Grade Reporting" — milestone intent, the narrative exec report as North Star, and the scope guardrail (branding=Phase 100 / per-finding=Phase 99).

### Existing report rendering code (the surfaces being enriched)
- `quirk/reports/executive.py` — current CLI exec markdown; **already** renders Score Decomposition + ÷1.5 rollup (lines ~166-194) and `_build_interpretation` bullet logic. Refactor target for the shared content model.
- `quirk/reports/html_renderer.py` — `render_html_report` (Jinja) + `render_pdf_report` (Playwright, with `pdf_ok` fallback when Playwright is absent). Second renderer that must consume the shared model.
- `quirk/reports/writer.py` — orchestration: `write_reports`, `_roadmap_markdown` (existing time-horizon buckets — extend per D-04), `_scorecard_markdown`.
- `quirk/reports/technical.py` — technical (detail) markdown; severity counts source for the D-06 consistency guard.
- `quirk/reports/templates/report.html.j2` — HTML template.
- `quirk/reports/_md_escape.py` (`md_cell`) — Phase 78/HARDEN-01: scanner-controlled cells MUST be wrapped; any new narrative/roadmap cells that include finding-derived text must use it.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `executive.py` Score Decomposition table + rollup line (TRANS-01/02 largely done in markdown — extend to other surfaces, don't rebuild).
- `writer.py:_roadmap_markdown` — existing time-horizon roadmap sections; base for D-04 impact×effort ordering.
- `html_renderer.py:render_pdf_report` — Playwright PDF path already exists with graceful fallback; PDF parity comes "for free" once HTML consumes the shared model.
- `_md_escape.md_cell` — mandatory wrapper for scanner-controlled cell content (HARDEN-01).

### Established Patterns
- Deterministic, offline rendering (no network/LLM at report time) — D-01 stays within this.
- Decision-tag convention (`D-NN / WR-NN`) in code comments for traceability — continue.
- Optional-extra dependencies are lazy-imported (Playwright/pypdf) — keep new deps, if any, out of the hot import path.

### Integration Points
- New shared content model sits between scoring/findings data and the two renderers (`executive.py`, `html_renderer.py`), with `writer.py:write_reports` as the orchestration seam.
- D-06 consistency guard sits where headline rating language and detail severity counts are both computed (writer/executive boundary).

</code_context>

<specifics>
## Specific Ideas

- The motivating contradiction to prevent (TRANS-03): exec summary saying "GOOD" while the body lists "7 CRITICAL". The guard must make this impossible to emit.
- The defensibility test for transparency (criterion 4): a client asking "how did you get 72?" must find the complete answer (subscores /25 + ÷1.5 rollup) in the document itself.

</specifics>

<deferred>
## Deferred Ideas

- **LLM narrative enrichment** — rejected outright (offline determinism is a hard constraint for the deliverable).
- **PDF visual layout / typography / cover / branding** — Phase 100 (backlog 999.2). Presentation polish, not content.
- **Rich per-finding quantum-risk "so what" + actionable remediation guidance** — Phase 99 (backlog 999.72). Phase 98's impact framing stays at the exec-summary tier (D-02).
- **Code-signing certificate expiry as a finding** — Phase 99 (WR-05 carry-in).
- **DOCX editable export** — Phase 100 deliverable.

</deferred>

---

*Phase: 98-executive-narrative-score-transparency*
*Context gathered: 2026-05-23*
