# Feature Research

**Domain:** Consulting-grade security assessment deliverables — report customization/branding
engine, score-lift-framed remediation roadmap, per-finding narrative drawer
**Researched:** 2026-09-11
**Confidence:** MEDIUM (ecosystem patterns verified across multiple named products; QUIRK-specific
complexity estimates HIGH confidence, sourced from `.planning/backlog/999.105-.../IDEA.md` file:line
citations)

## Feature Landscape

### Table Stakes (Users Expect These)

Consultants delivering paid pentest/readiness reports already use PlexTrac, Dradis, or
Word-template-based workflows. QU.I.R.K.'s reporting engine will be judged against that bar, not
against a blank slate.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Logo + cover-page branding | Every competing tool (PlexTrac white-labeling, Dradis, custom Word templates) supports at minimum a client/consultancy logo and cover page — QUIRK already has this (`report_owner`/`logo_path`, v5.2 Phase 100) | LOW | Already shipped; extending it is the differentiator, not the floor |
| Custom footer / header text, color accents | PlexTrac's "style guide" lets firms apply their brand palette across every export without touching markup — table stakes for a firm that reuses the tool across clients | LOW-MEDIUM | Token-level branding (999.105 Tier 1) — config keys flowing into all 3 renderers |
| Consistent branding across every export format | A client receiving both a PDF and a DOCX from the same engagement expects them to look like one deliverable, not two products | MEDIUM | Directly named as a risk in IDEA.md — parity gates must be respected or explicitly re-scoped per format |
| Executive vs. technical audience variants | PlexTrac and Dradis both ship methodology/audience templates (board-level exec summary vs. full technical appendix) — this is the single most-requested pentest reporting feature across the market | MEDIUM-HIGH | Maps to 999.105 Tier 2 (section composition profiles: `executive`/`technical`/`full`) |
| Section reordering / selection | Consultants tailor deliverables per client contract scope (e.g., omit a section the client didn't pay for, lead with findings instead of narrative) | MEDIUM-HIGH | Requires refactoring all 3 renderers from hardcoded section order to a section registry (IDEA.md Tier 2) |
| A remediation roadmap that reads as prioritized, not just listed | Every modern vuln-management tool (vendor research: EPSS, KEV-aware prioritization) frames remediation as ranked action, not a flat table — a flat "all findings, alphabetical" roadmap reads as amateur in 2026 | MEDIUM | QUIRK already has effort/impact roadmap (v5.2 Phase 98) and phased builders (999.101 re-frame layers score-lift on top) |
| Per-finding "so what" context | CNAPP tools (Wiz, Orca) and QUIRK's own existing per-finding context (v5.2 Phase 99, `ALGO_IMPACT_MAP`) both treat "here's a CVE ID" as insufficient — impact narrative is expected, not a bonus | LOW (partially shipped) | 999.102's storyline drawer extends existing per-finding context into an interactive UI surface |

### Differentiators (Competitive Advantage)

Features that set QUIRK's PQC-focused deliverable apart from generic pentest reporting tools —
none of PlexTrac/Dradis/Serpico are PQC-specialized, so QUIRK's differentiation is in framing
crypto-specific findings with business-credible narrative, not in generic template flexibility.

| Feature | Value Proposition | Complexity | Notes |
|---------|--------------------|------------|-------|
| Score-lift-framed NOW/NEXT/LATER roadmap | Standard vuln-prioritization literature (EPSS/KEV-style scoring) ranks by exploitability; QUIRK's unique angle is ranking by **quantified readiness-score movement** — "fixing this moves you from 62 to 71" is a concrete, defensible executive artifact competitors in the PQC space don't have | MEDIUM | 999.101; must derive from the same `compute_readiness_score()` path as the live score to avoid the credibility trap below — this is the single most important design constraint |
| Per-finding storyline drawer with quantum-risk arc | Wiz/Orca's "attack story" pattern (correlating raw signal into one narrative) applied to crypto findings: not just "TLS 1.0 detected" but a mini-narrative — what's exposed, why it matters post-quantum, what changes when fixed, tied back to the score-lift number | MEDIUM-HIGH | 999.102 (Obsidian Pro design remnant); depends on 999.101's per-finding score-lift attribution existing first if the drawer surfaces it |
| Operator-defined report profiles as reusable named configs | Beyond one-off toggles, letting a consulting firm save "Acme Corp House Style" as a named profile (branding + section selection) so every subsequent engagement report is one flag, not re-configuration — this is the MSSP-scale version of PlexTrac's white-labeling | MEDIUM | Not yet scoped in IDEA.md Tier 1/2 — flag as a candidate Tier 2.5 enhancement if time allows, defer otherwise |
| Custom section templates on every surface (full engine) | Full Jinja-on-DOCX-equivalent templating so an operator authors their own section content/wording, not just selects from provided ones | HIGH | IDEA.md Tier 3 — explicitly milestone-sized, correctly out of scope for v5.23. `docxtpl` new dependency + template-sandboxing decision (operator-supplied Jinja executing in-process) needed before scoping |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Fully free-form drag-and-drop report builder (arbitrary content blocks, not backed by the content model) | "Let me build any report I want" feels maximally flexible | Breaks the single-source-of-truth content model (`ReportContent`) that QUIRK's cross-surface parity gates depend on; an operator could construct a report showing a stale or internally-inconsistent score across sections, which is the exact defect class the parity gates (`test_cross_surface_parity.py` etc.) exist to prevent | Named section registry with fixed data bindings — operators choose *which* structured sections appear and *how they're branded*, never author raw content that bypasses the score/finding pipeline |
| Score-lift numbers computed ad hoc per roadmap item without re-running the real scoring engine | Fast to build — just estimate "this looks like a 5-point item" heuristically | This is the exact "score-lift roadmap as gimmick" failure mode: a number that doesn't trace to `compute_readiness_score()` is unfalsifiable and a sophisticated client (or a competing consultant auditing the same environment) can catch it, destroying credibility of the entire report | Derive score-lift by running the scoring function with-and-without the finding's contributing evidence (delta-scoring), the same machine-observed pattern QUIRK already uses for closure tracking (v5.18 ADVISORY-01) — advisory-only, never a second scoring path |
| Operator-uploadable arbitrary Jinja/DOCX templates with full code execution, shipped without a security review | Seems like the "give consultants total control" endgame of Tier 3 | Operator-supplied templates executing in-process is a real code-execution surface (IDEA.md already flags this) — for a tool that's had multiple SSRF/injection hardening passes (v5.7 Phase 123, v4.8 Phase 57-59), silently reopening a template-injection vector to hit a v5.23 deadline would be a regression against QUIRK's own security posture | Defer Tier 3 entirely (already IDEA.md's own recommendation); if ever built, sandbox template execution and treat it as its own threat-modeled milestone, not a fold-in |
| A storyline drawer that duplicates/forks finding narrative logic separately from the existing `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG` (Phase 99) | Building a fresh, more "narrative" text generator feels like it lets the drawer read more naturally | Two narrative sources for the same finding (one for reports, one for the dashboard drawer) will drift the way the migration_planner's dual roadmap builders already have (BACK-51, flagged in HORIZON) — a known, named QUIRK anti-pattern | Storyline drawer reads from the same per-finding context model the reports already consume; extend the model with drawer-specific fields (e.g., an ordered narrative arc) rather than forking it |
| Letting the score-lift roadmap re-sort itself live as findings are worked, without re-deriving from a real re-scan | Feels responsive / "live" | QUIRK's own closure-tracking design principle (ADVISORY-01, v5.18) is that state changes are machine-observed against real re-scans, never asserted client-side — a roadmap that reorders based on unconfirmed operator checkboxes would violate that same principle for score-lift claims | Score-lift is computed once per scan from real evidence; "done" status flows through the existing closure-tracking mechanism (VEX/burndown), not a separate live-reorder UI |

## Feature Dependencies

```
[999.105 Tier 1: branding/template overrides]
    └──enables──> [999.105 Tier 2: section composition profiles]
                       └──enables──> [999.101: NOW/NEXT/LATER score-lift roadmap as a selectable section]
                       └──enables──> [999.102: storyline drawer content reused in "full" report profile]

[Existing: ReportContent content model, per-finding context (Phase 99)]
    └──required-by──> [999.102: storyline drawer] (must read same model, not fork it)
    └──required-by──> [999.101: score-lift roadmap] (score-lift must derive from compute_readiness_score(), not heuristic)

[BACK-51: unify build_phased_roadmap() vs categorize_waves()]
    └──should-precede──> [999.101 re-frame] (IDEA.md: "should be unified BEFORE or WITHIN any composition engine")

[Existing: cross-surface parity gates (test_cross_surface_parity.py, test_report_render_parity.py)]
    └──constrains──> [999.105 Tier 2: section composition] (partial/profile reports need explicit parity re-scoping)

[999.105 Tier 3: full templating engine] ──conflicts-with-timeline──> [v5.23 scope]
    (explicitly deferred milestone-sized work per IDEA.md; do not fold into v5.23)
```

### Dependency Notes

- **999.105 Tier 1 must land before Tier 2:** branding/template overrides are additive
  (config → existing render path); section composition requires refactoring all three renderers
  to iterate a section list, a strictly larger change that benefits from Tier 1's config
  plumbing already existing.
- **999.101 and 999.102 are natural first customers of Tier 2, not blockers on it:** IDEA.md's
  own interaction note says to consider bundling — a roadmap re-frame and a storyline drawer both
  want the report to render as a distinct "section" that can be toggled/ordered, which is exactly
  what Tier 2 provides. If Tier 2 slips, 999.101/999.102 can still ship as fixed, non-optional
  additions to the existing report — the composition-selectability is the enhancement, not the
  prerequisite for the content itself to exist.
- **BACK-51 should precede or ride along with 999.101:** the roadmap has two competing builder
  functions (`build_phased_roadmap()` and `categorize_waves()`); building a score-lift frame on
  top of the wrong one (or both, inconsistently) bakes the duality into a now-more-visible,
  more-scrutinized artifact. This is a same-phase fold-in per PROJECT.md's own framing
  ("in scope if the 999.101 re-frame touches that code anyway — roadmapper's call"), not a
  separate dependency to sequence around.
- **Score-lift derivation is the credibility-load-bearing dependency**, not a nice-to-have: it
  must trace to the real `compute_readiness_score()` function via delta-scoring (score
  with-vs-without a finding's evidence), mirroring the machine-observed pattern QUIRK already
  established for closure tracking (v5.18). Any heuristic shortcut here is the single highest-risk
  anti-feature in this milestone (see Anti-Features table).
- **Storyline drawer conflicts with narrative-source duplication:** it must consume the same
  per-finding context model (`ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG`, Phase 99) that the existing
  reports use. Forking a second narrative generator for the dashboard would recreate the exact
  dual-source drift pattern already named as a defect elsewhere in this codebase (BACK-51).

## MVP Definition

### Launch With (v5.23, per PROJECT.md's committed scope)

- [ ] **999.105 Tier 1** (branding/template overrides) — CONFIRMED feasible, S-M effort, verified
  file:line hooks already exist (`html_renderer.py:899-900`, `config.py:22-24`)
- [ ] **999.101** (score-lift NOW/NEXT/LATER re-frame) — must derive score-lift from the real
  scoring function; fold in BACK-51's builder unification if 999.101 touches that code
- [ ] **999.102** (per-finding storyline drawer) — reuse existing per-finding context model,
  do not fork narrative logic
- [ ] Wave A gating drain (trends.py/merge.py int-coercion fix, overlay CI regression test) —
  named as a hard gate before the above three in PROJECT.md; not itself a "feature" but blocks
  correctness of any score-lift math built on top of coerced (non-fractional) scores

### Add After Validation (v5.23 stretch / early v5.24 candidate)

- [ ] **999.105 Tier 2** (section composition profiles: executive/technical/full) — LIKELY
  feasible, M effort, but requires a short spike (prototype section registry on the markdown
  surface only) before committing scope; explicitly a "should be shaped, not assumed" item per
  IDEA.md
- [ ] Named, reusable report profiles ("Acme Corp House Style") — natural extension once Tier 2's
  section registry exists; not currently scoped in any backlog item, worth flagging to the PM at
  roadmap creation

### Future Consideration (v2+ / explicitly deferred)

- [ ] **999.105 Tier 3** (full templating engine, `docxtpl`, operator-authored section templates) —
  UNKNOWN feasibility, L effort (milestone-sized per IDEA.md, "comparable to the Exposure Map
  arc"); requires its own threat model for operator-supplied template execution before any
  scoping work begins. Do not fold into v5.23 or v5.24 (PROJECT.md already commits v5.24 to
  UAT Coverage Drain).

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|----------------------|----------|
| 999.105 Tier 1 (branding/template overrides) | MEDIUM | LOW | P1 |
| 999.101 (score-lift roadmap re-frame) | HIGH | MEDIUM | P1 |
| 999.102 (storyline drawer) | HIGH | MEDIUM | P1 |
| BACK-51 (roadmap builder unification) | MEDIUM (risk-reduction, not user-visible alone) | LOW-MEDIUM | P1 (fold-in, not standalone) |
| 999.105 Tier 2 (section composition profiles) | HIGH | MEDIUM-HIGH | P2 |
| Named reusable report profiles | MEDIUM | MEDIUM | P3 |
| 999.105 Tier 3 (full templating engine) | MEDIUM (niche — only matters to firms wanting bespoke wording) | HIGH | P3 (deferred, milestone-sized) |

**Priority key:**
- P1: Committed v5.23 scope per PROJECT.md
- P2: Natural next rung, spike-gated
- P3: Explicitly deferred, future milestone

## Competitor Feature Analysis

| Feature | PlexTrac | Dradis | QUIRK's approach |
|---------|----------|--------|-------------------|
| Branding/white-labeling | Full white-labeling (MSSP multi-client labels) + no-code "style guide" applied across every export template | Basic — methodology templates, less branding depth | Tier 1: config-driven branding tokens flowing into all 3 existing renderers (additive, not a rebuild) |
| Section/template customization | Pre-built + custom (paid) templating service; templates swappable per engagement | Methodology templates (OWASP/PTES/HIPAA) drive structure | Tier 2: section registry with named composition profiles (executive/technical/full), derived from the existing structured content model rather than free text |
| Prioritization framing | Standard severity-based findings list; no PQC-specific or score-lift framing found | Kanban-style workflow for finding triage, not a scored roadmap | Differentiator: score-lift-quantified NOW/NEXT/LATER, traced to the live readiness-score function — no competitor found doing this for PQC or general crypto posture |
| Per-finding narrative depth | Standard finding template (description/impact/recommendation fields) | Similar structured finding fields | Differentiator: storyline drawer extends already-shipped per-finding "so what" context (Phase 99) into an interactive dashboard narrative, modeled on CNAPP "attack story" UX (Wiz/Orca) rather than static text |

## Sources

- [Custom Templates - PlexTrac](https://plextrac.com/platform/custom-templates/)
- [White Labeling | PlexTrac Documentation](https://docs.plextrac.com/plextrac-documentation/product-documentation-1/account-management/account-admin/white-labeling)
- [Dradis vs PlexTrac: Self-Hosted Pentest Reporting (2026)](https://dradis.com/compare/dradis-vs-plextrac.html)
- [Best Pentest Report Generators 2026: Self-Hosted vs Cloud](https://dradis.com/compare/pentest-report-generator-roundup.html)
- [The Modern Risk Prioritization Framework for 2026 - Safe Security](https://safe.security/resources/blog/the-modern-risk-prioritization-framework-for-2026/)
- [How To Prioritize Vulnerabilities For Remediation - PurpleSec](https://purplesec.us/learn/vulnerability-prioritization/)
- [Vulnerability Prioritization: A Complete Guide - Codacy](https://blog.codacy.com/vulnerability-prioritization)
- [Detect and Respond with Orca Security](https://orca.security/platform/detect-and-respond/)
- [From Findings to Fixes with Code Reachability, AppSec Triage Agent, and the AppSec Dashboard - Orca](https://orca.security/resources/blog/application-security-prioritization-remediation-triage/)
- [The Now-Next-Later Framework | Nalpeiron](https://nalpeiron.com/blog/now-next-later-framework/)
- Internal (HIGH confidence, file:line verified): `.planning/backlog/999.105-customizable-reporting-engine/IDEA.md`
- Internal (HIGH confidence): `.planning/PROJECT.md` (v5.23 milestone scope, BACK-51 interaction note, Phase 98/99/100 shipped baseline)

---
*Feature research for: QU.I.R.K. v5.23 Deliverable Experience*
*Researched: 2026-09-11*
