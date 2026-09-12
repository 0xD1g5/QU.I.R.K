# Project Research Summary

**Project:** QU.I.R.K. — v5.23 "Deliverable Experience" milestone
**Domain:** Brownfield feature addition to a consulting-grade security-assessment reporting
pipeline — customizable report branding/templating (999.105 Tier 1), a score-lift-framed
migration roadmap (999.101 + BACK-51), and a per-finding narrative drawer (999.102), plus a
Wave A correctness drain
**Researched:** 2026-09-11
**Confidence:** HIGH

## Executive Summary

QU.I.R.K. already has a mature, single-source-of-truth reporting architecture: one scoring
function (`compute_readiness_score()`), one content model (`ExecContent`), and three renderers
(CLI/HTML+PDF/DOCX) that pass a large presence-based parity test suite. This milestone extends
that architecture in three directions that experts building consulting-report tooling (PlexTrac,
Dradis) already treat as table stakes — branding customization, prioritized/quantified
remediation framing, and richer per-finding narrative — but QUIRK's specific differentiator is
tying the roadmap's priority framing to a **quantified, real readiness-score delta** rather than
generic severity/EPSS ranking. No competitor in the PQC space does this today.

The recommended approach requires **zero new runtime dependencies** for the milestone's committed
scope (999.105 Tier 1): Jinja2's `FileSystemLoader`, python-docx's `Document`/`styles` API, and
the existing `ExecContent` schema-extension pattern are all sufficient. The real work is
architectural discipline, not new tooling: (1) score-lift must be computed as a pure,
side-channel re-invocation of the real scoring function — never a forked formula, never persisted
next to the live score, and never additive across items past the existing 25-point subscore cap;
(2) the storyline drawer must read the same `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG`/key-reuse data
the reports already use, not fork a second narrative source; (3) any operator-supplied template
directory is a **new code-execution trust boundary**, not a repeat of the already-hardened
scan-data-XSS class, and needs `SandboxedEnvironment` plus its own SSTI test — the existing
`test_report_injection_hardening.py` green run does not cover this axis at all.

The single most important resolved fact for sequencing: 999.98 (SPKI fingerprint persistence),
which 999.102's own IDEA.md declared a hard blocker for the drawer's "where this crypto lives"
beat, **shipped in v5.21 Phase 191** (SPKI-01/02, closed 2026-09-08, per HORIZON.md's Open-Item
Ledger). The storyline drawer is therefore unblocked — the ARCHITECTURE.md researcher flagged
this as an open question needing verification at roadmap time; that verification is done, and no
further gate is needed before scoping 999.102's plans. Remaining risks are all process/design
risks (score-lift credibility, template-source sandboxing, parity-test scoping for the storyline
drawer as a fourth, previously-uncovered report surface) rather than technical feasibility risks.

## Key Findings

### Recommended Stack

No new dependencies for the committed v5.23 scope. Jinja2 3.1.6, python-docx 1.2.0, Playwright
1.60.0, and rich are already installed and already do everything Tier 1/opportunistic-Tier-2 need.
New work is entirely **schema, not packages**: a `report.template_dir` config field (mirrors the
existing `assessment.logo_path` precedent) widens the HTML renderer's `FileSystemLoader` to a
`ChoiceLoader`/search-path list with the operator directory tried first and the stock template as
fallback; a `report.branding` sub-table (accent color, footer text, cover subtitle) threads new
defaulted fields through `ExecContent` into all three renderers. `docxtpl` is explicitly a
Tier-3-only, not-this-milestone consideration, carrying a real SSTI/RCE caveat the library's own
docs acknowledge.

**Core technologies:**
- Jinja2 (existing) — HTML/PDF templating — already the engine; Tier 1 is a loader-scope change, not a new dependency
- python-docx (existing) — DOCX rendering/branding — `Document(template_path)` + `styles` API covers Tier 1 branding without templating
- Playwright (existing) — HTML→PDF — inherits branding for free via the shared HTML template
- rich (existing) — CLI rendering — text-token interpolation only, no templating library needed

### Expected Features

**Must have (table stakes, per FEATURES.md):**
- Logo/cover branding, footer/accent customization, and cross-format branding consistency — already partially shipped (Phase 100), extended in Tier 1
- A remediation roadmap that reads as prioritized, not a flat list (QUIRK already has this; 999.101 sharpens it)
- Per-finding "so what" narrative (already exists via Phase 99's `ALGO_IMPACT_MAP`; 999.102 surfaces it interactively)

**Should have (competitive differentiators):**
- Score-lift-framed NOW/NEXT/LATER roadmap — QUIRK's unique, defensible "fixing this moves you from 62 to 71" framing, with no direct competitor
- Storyline drawer with a quantum-risk narrative arc (Wiz/Orca "attack story" pattern applied to crypto findings)
- Executive vs. technical section-composition profiles (999.105 Tier 2) — high market demand, but explicitly a spike-gated stretch, not committed floor

**Defer (out of v5.23/v5.24):**
- 999.105 Tier 3 (full operator-authored templating engine, `docxtpl`) — UNKNOWN/L, milestone-sized, needs its own threat model
- Named, reusable "house style" report profiles — natural Tier 2 extension, not yet scoped, flag to PM for a future backlog item

### Architecture Approach

All three new features attach to QUIRK's existing single-producer architecture rather than
introducing parallel paths: branding/template changes are additive `ExecContent` fields and a
loader-scope widening; score-lift is a read-only second call into
`compute_readiness_score()` against a synthetic evidence mapping, attached to `RoadmapItem`, never
a forked scoring formula; the storyline drawer projects existing report-side data
(`key_reuse`, HNDL labels, `slug_for_title()`/`item_progress()`) onto new optional `FindingItem`
fields rather than recomputing anything.

**Major components:**
1. `quirk/intelligence/scoring.py::compute_readiness_score()` — remains the sole score producer; score-lift calls it a second time, read-only, never mutates its inputs
2. `quirk/reports/content_model.py::build_exec_content()` / `ExecContent` — the single content model all three renderers consume; new branding, score-lift, and (if extended) narrative fields attach here first
3. `quirk/intelligence/roadmap.py::build_phased_roadmap()` vs. `quirk/reports/writer.py::categorize_waves()` — the BACK-51 duality; recommend retiring `categorize_waves()` in favor of the evidence-driven builder's output if 999.101 touches this code, closing BACK-51 as a byproduct
4. `quirk/dashboard/api/routes/scan.py::_derive_findings()` — the dashboard's independent finding/roadmap re-derivation path; the storyline drawer's new fields (`linked_assets`, `roadmap_slug`) attach here, sourced from the same functions the report path already calls

### Critical Pitfalls

1. **Operator template loading is a new SSTI/RCE surface, not a repeat of the hardened XSS class** — autoescape protects interpolated *data*, not template *source*; use `jinja2.sandbox.SandboxedEnvironment` for any operator-supplied search path and add a dedicated SSTI payload test, not just a green `test_report_injection_hardening.py`.
2. **`logo_path`'s dashboard-exclusion is tribal knowledge, not a reusable guard** — any new filesystem-path-shaped branding field must be routed through the same restriction (or a documented, deliberate exception), or it risks silently landing on the dashboard via the 999.104 parity push's default "expose everything" instinct.
3. **Score-lift can silently cross the score firewall or become an unfalsifiable promise** — must be a pure, non-persisted, non-additive (respects the 25-point subscore cap) re-invocation of the real scoring function, with its own ADVISORY-02-style guard test mirroring ADVISORY-01; never sum per-item lifts for an aggregate projection.
4. **Section composition (Tier 2) breaks the "every report has every section" assumption both the zero-CRITICAL congruence guard and the parity-test suite were built on** — needs an explicit profile-aware parity design (profile × renderer × section matrix) before renderers are refactored to iterate a section list.
5. **The storyline drawer is a fourth report surface the existing three-renderer parity discipline never covers** — must reuse `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG`/`content_model.py` narrative sources rather than forking a dashboard-only narrative computation, to avoid the deliverable and the live dashboard telling different stories for the same finding.

## Implications for Roadmap

Based on combined research, the suggested phase order (all four researchers converge on this
sequencing independently):

### Phase 1: Wave A Correctness Drain
**Rationale:** Gating per PROJECT.md; independent of the three features but touches
scoring-adjacent code (trends.py/merge.py int-coercion) that a reviewer will rightly ask about
once score-lift math lands on top of it. Do it first so it isn't carried as tech debt into new
scoring-adjacent code.
**Delivers:** int-coercion fix + overlay CI regression test.
**Avoids:** compounding an existing correctness bug with new score-lift math built on the same paths.

### Phase 2: 999.105 Tier 1 — Customizable Reporting Engine (branding/template overrides)
**Rationale:** Most isolated change — zero coupling to scoring, additive config + `ExecContent`
fields, de-risks the "add optional fields without breaking parity gates" pattern both later
features also need.
**Delivers:** `report.template_dir` + `report.branding` config (dataclass, config.yaml only —
not dashboard-exposed, per Anti-Pattern 3), widened HTML `FileSystemLoader`/`ChoiceLoader`
**wrapped in `SandboxedEnvironment`** for the operator search path, token-level branding in
DOCX/CLI.
**Uses:** Jinja2 (existing), python-docx `styles` API (existing).
**Avoids:** Pitfall 1 (unsandboxed template source) and Pitfall 2 (logo_path-guard drift) — both
must be closed in this phase, not deferred.

### Phase 3: 999.101 — Score-Lift Migration-Roadmap Re-Frame (+ BACK-51 fold-in)
**Rationale:** Scoring-adjacent and the highest credibility risk in the milestone; needs a short
spike first (per IDEA.md) to resolve the driver→roadmap-item join approach and confirm the
non-additive aggregate-projection design before renderer-facing code is written.
**Delivers:** `projected_lift` field on `RoadmapItem` via a new pure `score_lift.py` module
(synthetic-evidence rescoring), an ADVISORY-02-style guard test, and — if this phase touches
`categorize_waves()`/`build_phased_roadmap()` — retirement of the CLI table's separate severity
bucketing in favor of the evidence-driven builder (closing BACK-51 as a byproduct). Roadmapper
must explicitly decide (and record) whether the two builders serve the same or genuinely
different surfaces before implementation, per IDEA.md's own "roadmapper's call" framing.
**Addresses:** the milestone's core differentiator (score-lift framing) from FEATURES.md.
**Avoids:** Pitfall 3 (score-firewall crossing) and Pitfall 5 (BACK-51 fold-in resolving the
symptom but not the cause).

### Phase 4: 999.102 — Finding Storyline Drawer
**Rationale:** Benefits from 999.101 landing first (beat 4, "mapped to roadmap item NOW-1," is
more informative with phase+lift data available) and carries the highest a11y-review overhead
(new interactive drawer against Phase 185's a11y baselines), so it gets the most schedule slack
by going last. **999.98 is confirmed shipped (v5.21 Phase 191) — this phase is not blocked and
should proceed without a re-verification gate.**
**Delivers:** React drawer built on the existing `sheet.tsx` primitive; two new optional
`FindingItem` fields (`linked_assets`/`linked_asset_count`, `roadmap_slug`/`roadmap_phase`)
populated in `_derive_findings()` from the same `compute_key_reuse_clusters()` and
`slug_for_title()`/`item_progress()` functions the reports already use; a new a11y baseline
capture for the drawer's open/close/focus flow.
**Addresses:** per-finding narrative differentiator from FEATURES.md.
**Avoids:** Pitfall 6 (fourth-surface narrative drift) — reuse `ALGO_IMPACT_MAP`/
`REMEDIATION_CATALOG`, never fork.

### 999.105 Tier 2 (section composition profiles) — explicitly stretch/spike-gated, not a numbered phase
Per FEATURES.md and PITFALLS.md, this should only be folded in if 999.101 or another phase
touches the relevant renderer code anyway, and only after a short spike (prototype the section
registry on the markdown surface only) produces a written profile-aware parity/congruence design.
Treat as a P2 candidate for roadmap review, not a committed phase, unless the roadmapper decides
otherwise.

### Phase Ordering Rationale

- Wave A first because scoring-adjacent correctness bugs compound with new scoring-adjacent
  features (score-lift) if left unresolved.
- Tier 1 second because it's the lowest-risk, highest-reuse phase and establishes the
  `ExecContent`-schema-extension pattern (optional fields, parity-safe) both later phases depend on.
- Score-lift third because it is scoring-adjacent and highest-credibility-risk — sequencing it
  after Tier 1 means the config/branding plumbing pattern is already proven, and before the
  drawer means beat 4 of the drawer is richer.
- Drawer last because it has the most a11y review overhead and is now fully unblocked (999.98
  resolved), so no dependency forces it earlier.
- Tier 2 is deliberately NOT a numbered phase — both FEATURES.md and PITFALLS.md independently
  flag it as needing its own spike and explicit parity redesign before scope commitment.

### Research Flags

Needs research during phase planning:
- **Score-lift phase (999.101):** the driver→roadmap-item join approach (evidence-counter
  provenance vs. a closed-candidate mapping table) is a real open design question requiring a
  short spike before implementation, per ARCHITECTURE.md and PITFALLS.md.
- **Tier 2 (if folded in anywhere):** the profile-aware parity/congruence design is explicitly
  unresolved and needs its own spike output (not just a registry mechanism proof).

Phases with standard, well-documented patterns (skip `--research-phase`):
- **Wave A drain:** a known bug-fix pattern, no new architecture.
- **999.105 Tier 1:** the `logo_path`/`report_owner` precedent and Jinja2 loader-widening pattern
  are both fully verified against live source; the only non-standard element (sandboxing) is
  named precisely enough in PITFALLS.md to plan directly.
- **999.102 storyline drawer:** all four data beats map to already-shipped functions/fields;
  the only new work is two schema fields and a React component on an existing primitive.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified directly against installed package versions and live source file:line citations; zero training-data-only claims for the committed scope |
| Features | MEDIUM | Ecosystem competitive patterns (PlexTrac/Dradis) verified via WebSearch (multiple named sources); QUIRK-specific complexity/feasibility estimates are HIGH (sourced from IDEA.md file:line citations) |
| Architecture | HIGH | All claims verified against live source at file:line level; the one open question flagged (999.98 status) has since been resolved (see below) |
| Pitfalls | HIGH on codebase-verified items (file:line cited); MEDIUM on general Jinja2/SSTI ecosystem claims (training-data based, recommend a live doc check at Tier 1 implementation time) |

**Overall confidence:** HIGH

### Gaps to Address

- **999.98 status — RESOLVED during synthesis, not carried forward as an open question.**
  ARCHITECTURE.md flagged 999.98 (SPKI fingerprint persistence) as unverified/contradictory
  between the 999.102 IDEA.md (declared blocked, filed 2026-09-07) and PROJECT.md's v5.21 section
  (listed as a shipped target). Confirmed: 999.98 shipped in v5.21 Phase 191 (SPKI-01/02, closed
  2026-09-08, per `.planning/HORIZON.md`'s Open-Item Ledger). **999.102 is unblocked.** No
  further verification gate is needed before scoping the drawer's plans.
- **Whether 999.101's score-lift framing is report-surface-only or also dashboard-surface** —
  not resolved by any research file; needs an explicit roadmapper/PM decision, since it determines
  whether `routes/scan.py` needs its own synthetic-rescore wiring in addition to `writer.py`'s.
- **Whether BACK-51's fold-in belongs in 999.101's phase or is deferred again** — explicitly left
  as "roadmapper's call" by PROJECT.md and all four research files; must be a recorded decision
  before 999.101 implementation starts, not an accident of which builder function gets touched
  first.
- **Exact current click-handling behavior of the React findings table** — not verified in this
  research pass (component not read); verify before writing 999.102's plan to confirm row-click
  doesn't already trigger different behavior the drawer would need to replace or extend.
- **Live Jinja2 sandboxing API check** — PITFALLS.md's `SandboxedEnvironment` guidance is
  MEDIUM-confidence training-data knowledge; recommend a live docs check (Context7 or
  jinja.palletsprojects.com) at 999.105 Tier 1 implementation time to confirm no API changes.

## Sources

### Primary (HIGH confidence)
- Direct source reads: `quirk/reports/html_renderer.py`, `quirk/reports/docx_renderer.py`,
  `quirk/reports/writer.py`, `quirk/reports/content_model.py`, `quirk/config.py`,
  `quirk/intelligence/scoring.py`, `quirk/intelligence/roadmap.py`,
  `quirk/intelligence/remediation.py`, `quirk/dashboard/api/schemas.py`,
  `quirk/dashboard/api/config_preview.py`
- `.planning/backlog/999.105-customizable-reporting-engine/IDEA.md`,
  `.planning/backlog/999.101-roadmap-now-next-later-with-score-lift/IDEA.md`,
  `.planning/backlog/999.102-finding-storyline-drawer/IDEA.md`
- `.planning/PROJECT.md` (v5.23 milestone scope, phase history)
- `.planning/HORIZON.md` (Open-Item Ledger — 999.98 shipped status, v5.21 Phase 191)
- `pip show jinja2 python-docx playwright rich` against the active environment (2026-09-11)

### Secondary (MEDIUM confidence)
- [PlexTrac Custom Templates](https://plextrac.com/platform/custom-templates/) / [White Labeling docs](https://docs.plextrac.com/plextrac-documentation/product-documentation-1/account-management/account-admin/white-labeling)
- [Dradis vs PlexTrac comparison (2026)](https://dradis.com/compare/dradis-vs-plextrac.html)
- [The Modern Risk Prioritization Framework for 2026 - Safe Security](https://safe.security/resources/blog/the-modern-risk-prioritization-framework-for-2026/)
- [Orca Security — Detect and Respond](https://orca.security/platform/detect-and-respond/)
- [docxtpl PyPI](https://pypi.org/project/docxtpl/)
- Jinja2 sandboxing/SSTI general knowledge (training-data based, flagged for live re-verification)

### Tertiary (LOW confidence)
- None flagged — all lower-confidence claims above are explicitly marked MEDIUM with a stated
  verification recommendation, not left as unqualified LOW-confidence assertions.

---
*Research completed: 2026-09-11*
*Ready for roadmap: yes*
