# Architecture Research — v5.23 Deliverable Experience

**Domain:** Brownfield integration — reporting engine (999.105 Tier 1), score-lift roadmap
re-frame (999.101 + BACK-51), finding storyline drawer (999.102) — into QU.I.R.K.'s existing
report/scoring/dashboard architecture.
**Researched:** 2026-09-11
**Confidence:** HIGH (all claims verified against live source at the file:line level, not
training-data assumption)

## Current Architecture (verified, not invented)

```
┌───────────────────────────────────────────────────────────────────────┐
│  Scan pipeline (run_scan.py) → endpoints, findings, evidence           │
└───────────────────┬─────────────────────────────────────────────────────┘
                     │
         quirk/intelligence/scoring.py::compute_readiness_score()
         (exclude-and-rescale, SCORE_WEIGHTS, single producer of the score)
                     │
     ┌───────────────┼────────────────────────────┐
     │               │                            │
quirk/intelligence/  quirk/intelligence/           quirk/cbom/
roadmap.py           severity_bands.py             build_cbom()
build_phased_roadmap()  (single producer of         │
(evidence+scoring →      severity band labels)      │
 NOW/NEXT/LATER items,                               │
 driver reasons)                                     │
     │                                               │
     └──────────────┬────────────────────────────────┘
                     │
       quirk/reports/writer.py::write_reports(cfg, endpoints, findings,
                                                run_stats, closure_counters)
                     │
       quirk/reports/content_model.py::build_exec_content()
       (ExecContent: narrative, top_risks, roadmap_items[RoadmapItem],
        subscores, key_reuse, congruence guard)
                     │
     ┌───────────────┼────────────────┬─────────────────────┐
     │               │                │                     │
technical.py    html_renderer.py  docx_renderer.py    (CLI JSON dump,
(markdown)      (Jinja2, FileSystem  (imperative        findings-*.json)
                 Loader over          python-docx)
                 templates/*.j2)
                     │
              writer.py::categorize_waves(findings)
              (SEPARATE severity-bucketed NOW/NEXT/LATER —
               the BACK-51 duality; feeds only the CLI console table,
               not ExecContent.roadmap_items)

FastAPI dashboard (quirk/dashboard/api/):
  - routes/scan.py: /api/scan/latest → FindingItem[], RoadmapNode/Edge,
    ScanLatestResponse (independently re-derives findings/roadmap from
    CryptoEndpoint rows — NOT the same code path as write_reports())
  - schemas.py: delta-only overlay pattern — ScanSubmitRequest.connectors /
    AdvancedScanFields carry ONLY user-set deltas, validated by
    validate_connectors_overlay(), merged over resolved QuirkCfg with
    _user_set_fields precedence (config_preview.py)
  - config.py: dataclass-per-section (AssessmentCfg, ScanCfg, ConnectorsCfg,
    ...), report_owner/logo_path already live in AssessmentCfg (Phase 100/D-01)

React dashboard (src/dashboard/src/):
  - components/ui/sheet.tsx: existing drawer/sheet primitive (shadcn) —
    already used for a findings-table row-click surface
  - lib/verticals.ts + /api/config: runtime vertical selection pattern,
    the closest existing precedent for "operator-selectable presentation mode"
```

### Component Responsibilities (current)

| Component | Responsibility | Notes for this milestone |
|-----------|-----------------|---------------------------|
| `quirk/intelligence/scoring.py` | SOLE producer of the readiness score and per-driver point attribution (`_apply_weighted_impacts`, `score_cap=25.0` per subscore) | Must remain the only place a "lift" number is computed — see Score-Firewall section |
| `quirk/intelligence/severity_bands.py` | SOLE producer of severity band labels | Do not add a second band-derivation for the drawer or roadmap |
| `quirk/intelligence/roadmap.py::build_phased_roadmap()` | Evidence-driven roadmap items with `phase`/`priority`/`effort`, keyed by title via `slug_for_title()` | Score-lift join target (999.101) |
| `quirk/reports/writer.py::categorize_waves()` | Severity-bucketed NOW/NEXT/LATER, CLI-console-only | BACK-51 duality — candidate for retirement in favor of `build_phased_roadmap()`'s NOW/NEXT/LATER if 999.101 touches this code |
| `quirk/reports/content_model.py::build_exec_content()` | Builds `ExecContent`, the ONE model all three renderers consume | New score-lift field and storyline-narrative fields attach here, not per-renderer |
| `technical.py` / `html_renderer.py` / `docx_renderer.py` | Three independent renderers over `ExecContent` | 999.105 Tier 1 changes template loading (HTML) + branding tokens (all three); Tier 2/3 (section composition, DOCX templating) explicitly OUT of this milestone per IDEA.md |
| `quirk/dashboard/api/schemas.py` (overlay pattern) | Delta-only YAML overlay validated against `ConnectorsCfg`/`AdvancedScanFields`, precedence via `_user_set_fields` | The proven pattern for where report-composition config should live if it needs a dashboard-editable surface |
| `routes/scan.py` (`_derive_findings`, `/api/scan/latest`) | INDEPENDENT re-derivation of findings/roadmap for the dashboard — NOT the same code as `write_reports()` | Storyline drawer must source from this path (or a shared helper), since the dashboard never calls `write_reports()` |

## Feature-by-Feature Integration Plan

### 999.105 Tier 1 — Customizable reporting engine (template/branding overrides)

**What's new:**
- A `report` config section (new dataclass, e.g. `ReportCfg` in `quirk/config.py`, parallel to
  `AssessmentCfg`) carrying: `template_dir: str | None`, and extended branding tokens (accent
  color, footer text, cover subtitle) — additive to the existing `report_owner`/`logo_path`
  fields already on `AssessmentCfg`. Do NOT duplicate `logo_path` into the new section; extend
  `AssessmentCfg` for branding, keep `template_dir` in the new section since it's a filesystem
  capability, not an identity field.
- `html_renderer.py`'s `FileSystemLoader(_TEMPLATES_DIR)` (line ~1005) becomes
  `FileSystemLoader([operator_template_dir, _TEMPLATES_DIR])` when `template_dir` is set — Jinja2
  natively supports a loader search-path list, falling back to the stock template if the
  operator's override doesn't define a given block. This is additive and requires no
  `write_reports()` signature change beyond threading `cfg.report` through to
  `render_html_report()`.
- Branding tokens flow into `ExecContent` (new fields, defaulted) so `technical.py` and
  `docx_renderer.py` can render token-level branding (footer text, accent color reference)
  without full templating — matches the IDEA.md Tier 1 scope explicitly ("DOCX/markdown get
  token-level branding only, not full templating").

**What's modified:**
- `quirk/config.py`: new `ReportCfg` dataclass + wiring into `QuirkCfg`.
- `quirk/reports/writer.py::write_reports()`: thread `cfg.report` (or the relevant fields) to
  `render_html_report()`, `build_exec_content()`.
- `quirk/reports/content_model.py`: add branding fields to `ExecContent` with safe defaults so
  existing engagements produce byte-identical output when the new config section is absent
  (avoids breaking `test_report_render_parity.py` / `test_cross_surface_parity.py`).
- `quirk/reports/html_renderer.py`: loader change (~line 1005).

**Config location decision:** config.yaml only for this milestone, NOT the dashboard overlay.
Rationale: report composition is a per-engagement, pre-scan authoring decision made by the
consultant in their config file (like `report_owner`/`logo_path` already are), not a per-scan-job
runtime toggle like connector enable flags. Mirroring the delta-overlay pattern here would be
premature — there is no dashboard scan-submission form field this maps to, and `template_dir`
pointing at an arbitrary filesystem path is exactly the class of setting Tier 4 (server-side
config editing) was explicitly deferred over (PARITY-T4, still OUT). Section composition
(Tier 2, also OUT this milestone) would be the natural point to revisit a dashboard-facing
overlay, once a section-registry exists to select from.

**Anti-pattern to avoid:** do not let template overrides bypass the existing parity gates
(`test_key_reuse_render_parity.py`, `test_report_render_parity.py`, `test_cross_surface_parity.py`)
silently. Since Tier 1 only touches template *tokens*, not section *presence*, these gates should
continue to pass unmodified — that is itself the acceptance signal that Tier 1 stayed in scope
and did not silently drift into Tier 2 territory.

### 999.101 — Score-lift migration-roadmap re-frame (+ BACK-51 fold-in)

**The score-firewall constraint, stated precisely:** ADVISORY-01 (`tests/test_remediation_advisory_guard.py`,
`tests/test_cve_score_guard.py`) enforces that *closure/remediation state* (whether an item has
been fixed) never feeds back into `compute_readiness_score()`. That is a **temporal/causal**
firewall (state observed after the fact must not retroactively move the score). Score-lift is a
**different but related** hazard: it must compute "what would the score become IF this item's
underlying findings were resolved" — a **hypothetical forward projection**, not a scoring input.
The two guards below both apply and must both hold:

1. **Never write a simulated score to the score field itself, or to any evidence counter
   `compute_readiness_score()` reads.** The lift computation must be a read-only, side-channel
   call: build a synthetic evidence mapping with the relevant counters decremented (e.g. zero out
   `finding_severity_counts["CRITICAL"]` contributions attributable to that roadmap item's
   findings), call `compute_readiness_score()` a second time against that synthetic mapping, diff
   the two `total_score` values, and attach the diff to the `RoadmapItem` as a `projected_lift`
   field. This literally reuses `compute_readiness_score()` as pure — it does not touch
   `scoring.py` at all, so `tests/test_score_weights_invariant.py` and the SCORE_WEIGHTS contract
   are untouched.
2. **The per-item lift is provably non-additive** (per IDEA.md unknown #3, confirmed by reading
   `_apply_weighted_impacts`'s `score_cap=25.0` clamp at `scoring.py:158-166`): two items in the
   same subscore domain do not sum linearly once the subscore approaches its 25-point cap, and
   `total_score = sum(assessed subscores)/(domains_assessed*25)*100` compounds that at the
   top level. **Do not compute an aggregate "projected 79" by summing per-item lifts.** Compute
   it the same way: build ONE synthetic evidence mapping with ALL NOW-tier items' findings
   removed, call `compute_readiness_score()` once, and use that single re-scored total as the
   aggregate projection. Per-item lifts are for display ordering/prioritization only; the
   header-ribbon aggregate must be its own independent computation, not a sum of the per-item
   numbers.

**The driver→roadmap-item join (the real work, per IDEA.md):** `build_phased_roadmap()`
(`roadmap.py:99`) and `scoring.py`'s `_apply_weighted_impacts` drivers are keyed by different
vocabularies (roadmap item titles/slugs vs. driver label strings like `"Expired certificates"`).
This needs either (a) a mapping table in the style of `remediation.py`'s existing
`REMEDIATION_KIND_SLUGS` closed-candidate-set pattern (verified as the codebase's established
idiom — no fuzzy matching, explicit unmapped state), with a run-time-derived gate proving it stays
total across every title `build_phased_roadmap()` can emit (matching the project's now-repeated
"derive the check set from source, don't hand-maintain a list" convention — see CLAUDE.md TOOL-04
lesson, directly applicable here), or (b) restructuring `build_phased_roadmap()` to carry the
underlying evidence-counter keys it already reads (endpoints, cert_obs, sev, etc. — visible at
`roadmap.py:109-157`) as a first-class field on each emitted item, so the synthetic-evidence
zeroing in guard #1 above can target exactly the counters that item's own construction used,
with no separate mapping table at all. **(b) is architecturally cleaner and avoids inventing a
second closed-candidate-set alongside `REMEDIATION_KIND_SLUGS`** — recommend it, but flag as a
roadmapper decision since it touches `build_phased_roadmap()`'s output schema (consumed by
`content_model.py::_enrich_roadmap_item()` and `remediation_persist.py`).

**BACK-51 fold-in:** `categorize_waves()` (`writer.py:293`) is a severity-only bucketing (CRITICAL
→ NOW, HIGH → NEXT, else → LATER) that feeds ONLY the CLI console table — a different, cruder
NOW/NEXT/LATER than `build_phased_roadmap()`'s evidence-driven phases, which already reach
`ExecContent.roadmap_items`. If 999.101 is retrofitting a score-lift onto roadmap phases, the
CLI console table using a *different* phase assignment than the HTML/DOCX/report roadmap for the
same scan would visibly contradict the score-lift-per-phase narrative (e.g. an item shown as NOW
in HTML with "+14 score" but appearing in NEXT on the CLI table). Recommend: replace
`categorize_waves()`'s call site with `build_phased_roadmap()`'s output (already computed earlier
in `write_reports()` for `ExecContent`) so the CLI table renders the SAME phase assignment. This
closes BACK-51 as a byproduct rather than a separate refactor, matching the milestone's own
framing ("in scope if the 999.101 re-frame touches that code anyway").

**What's new:** `projected_lift: int` (or `Optional[int]`, honest-absence when the mapping can't
resolve) field on `RoadmapItem`; a new pure function (suggest `quirk/intelligence/score_lift.py`)
housing the synthetic-evidence-and-rescore logic; a new test file mirroring
`test_remediation_advisory_guard.py`'s structure asserting the lift computation never mutates the
real evidence mapping in place and never writes to the persisted score.

**What's modified:** `roadmap.py::build_phased_roadmap()` (carries evidence-counter provenance
per item, if approach (b)); `content_model.py::RoadmapItem`/`_enrich_roadmap_item()` (new field);
`writer.py` (categorize_waves call site, if BACK-51 folded in); HTML/DOCX/markdown renderers
(display the lift + aggregate projection); dashboard `/api/scan/latest` roadmap serialization
(`RoadmapNode`/`RoadmapEdge` in schemas.py) if the dashboard is expected to show the same
score-lift framing — check with the roadmapper whether 999.101 is report-surface-only or also
dashboard-surface, since `routes/scan.py` independently re-derives roadmap data and would need
the identical synthetic-rescore call wired in separately to avoid drift between report and
dashboard framings.

### 999.102 — Finding storyline drawer

**Status per IDEA.md: blocked on 999.98 (SPKI fingerprint) for step 2** ("where this crypto
lives" — key-reuse cross-referencing). Verify 999.98's status before starting this feature; if
still unshipped, the drawer must ship with step 2 degraded to an honest absence state, not
fabricated cross-references.

**Data sourcing — no new backend model needed for 3 of 4 beats:**
- **Beat 1 (DETECTED):** `FindingItem` (`schemas.py:131`) already carries `title`, `protocol`,
  `description`, `severity` — zero new fields.
- **Beat 2 (WHERE THIS CRYPTO LIVES):** requires the key-reuse cluster data QUIRK already
  computes for the HTML report (`content_model.py`'s `key_reuse` field, populated by
  `writer.py::_load_key_reuse()` from `compute_key_reuse_clusters()` — confirmed live and used
  by the report today, NOT gated on a separate 999.98 backend build; the IDEA.md's "blocked"
  framing should be re-verified against current source, since key-reuse clustering may have
  shipped since the IDEA.md was filed 2026-09-07 — check `quirk/cbom/bridge.py` /
  `compute_key_reuse_clusters()`'s call sites and `git log` for 999.98 before treating this as
  still blocked). The dashboard's `/api/scan/latest` does not currently surface `key_reuse` in
  `FindingItem` — this is the actual new work: add a `linked_asset_count` / `linked_assets: []`
  field to `FindingItem`, populated in `routes/scan.py::_derive_findings()` by joining against
  the same `key_reuse` clustering the report already uses.
- **Beat 3 (WHY IT MATTERS):** HNDL risk labels already exist (`findings_evaluator.py:181,688,708,764`
  per IDEA.md) — reuse verbatim. Asset-role ("customer + partner traffic") and retention-period
  prose are explicitly NOT modeled (`config.py`'s `data_classification` is engagement-level only)
  — IDEA.md's own recommendation to degrade honestly to the HNDL sentence and drop invented
  asset-role prose is correct and should be followed; do not author per-asset-role heuristics as
  a side effect of this feature.
- **Beat 4 (REMEDIATION):** `slug_for_title()` (`remediation.py:151`) + `item_progress()`
  (`remediation.py:161`) already exist and already have honest-absence semantics ("No fuzzy
  matching... an unmapped title must be visibly unmapped"). Reuse directly — the drawer's
  "no mapped roadmap item" state is not new design work, it is the existing `None` return path.

**What's new:**
- React: a drawer/panel component built on the existing `components/ui/sheet.tsx` primitive
  (already present — do not introduce a second drawer/modal library), triggered from a findings-
  table row click, rendering the 4-beat structure.
- Backend: `linked_asset_count`/`linked_assets` field on `FindingItem` (dashboard schema only —
  report side already has this via `key_reuse`), and a `roadmap_slug` / `roadmap_phase` field on
  `FindingItem` so beat 4 can render "Mapped to roadmap item NOW-1" client-side without a second
  API round-trip. Both are read-only projections of existing computed data — no new scoring or
  persistence.

**What's modified:** `quirk/dashboard/api/schemas.py::FindingItem` (2 new optional fields);
`routes/scan.py::_derive_findings()` (populate them from existing key-reuse + remediation-slug
logic); React findings-table component (row click → open drawer instead of, or in addition to,
current behavior — check current click handler in the findings table component before assuming
none exists).

**a11y note (IDEA.md unknown #3, correctly flagged):** Phase 185 rebuilt per-state a11y baselines
(`DRIFT-03` context in PROJECT.md). A new drawer/sheet interaction needs its own baseline capture
and keyboard-trap/focus-return check — budget this explicitly in the plan, do not treat it as
free because `sheet.tsx` already exists (the primitive existing doesn't mean this specific
open/close/focus flow is already baselined).

## Suggested Build Order

1. **Wave A drain first (gating, per PROJECT.md)** — trends.py/merge.py int-coercion fix +
   overlay CI regression test. Independent of all three features; do first so it isn't carried
   as tech debt into new scoring-adjacent code (the score-lift feature in particular touches
   scoring-consumption paths, and an existing int-coercion bug in a sibling module is exactly the
   kind of thing a reviewer will (rightly) ask "did you check this doesn't also affect the new
   code" — better to have it closed first).
2. **999.105 Tier 1 (reporting engine template/branding)** — do second. It is the most isolated
   change (additive config + Jinja2 loader + `ExecContent` defaulted fields), has zero coupling
   to scoring, and de-risks the `ExecContent` schema-change pattern (adding new optional fields
   without breaking parity gates) that both other features also need. Also unblocks a decision
   the roadmapper flagged: if BACK-51's `categorize_waves()` retirement is folded into 999.101,
   confirm it doesn't collide with any Tier-1 CLI-table template change first.
3. **999.101 (score-lift roadmap re-frame, + BACK-51 fold-in)** — do third, with the recommended
   short spike (per IDEA.md, "Recommended pre-work: a short spike on unknowns 1 and 3") resolved
   as a first plan: prove the driver→roadmap-item join approach (recommend option (b) above —
   carry evidence-counter provenance on `RoadmapItem` rather than a second closed-candidate-set
   mapping) and confirm the non-additive aggregate-projection approach (independent rescore, not
   summed lifts) before writing renderer-facing code. This is scoring-adjacent and must be
   reviewed against ADVISORY-01's test suite shape before merge — reuse
   `test_remediation_advisory_guard.py`'s structure for the new score-lift guard test.
4. **999.102 (storyline drawer)** — do last. It depends on re-verifying 999.98's actual status
   (may already be unblocked — check before treating as blocked) and benefits from 999.101 being
   done first since beat 4 ("Mapped to roadmap item NOW-1") is more informative once roadmap
   items carry phase + score-lift framing. It is also the highest a11y-review overhead
   (new interactive drawer), so sequencing it last leaves the most schedule slack for that review.

**Cross-feature dependency graph:**
```
Wave A drain ──> 999.105 Tier 1 ──> 999.101 (+ BACK-51) ──> 999.102
                       │                    │
                       └── ExecContent field-add pattern reused by both
                                            │
                              999.98 (external, re-verify status) ──> 999.102 beat 2
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Summing per-item score-lift for the aggregate projection
**What:** Computing "projected 79" as `current_score + sum(item.projected_lift for item in NOW)`.
**Why bad:** `_apply_weighted_impacts`'s `score_cap=25.0` clamp and the top-level
exclude-and-rescale formula are both non-linear; a naive sum overstates the projection and
misleads a client-facing deliverable — this is the exact failure mode IDEA.md's unknown #3 flags.
**Instead:** independent single re-score call against a synthetic evidence mapping with ALL
relevant findings zeroed at once.

### Anti-Pattern 2: Introducing a second severity/phase classification for the CLI table
**What:** Leaving `categorize_waves()` (pure severity bucketing) untouched while
`build_phased_roadmap()` (evidence-driven) gains score-lift framing — the BACK-51 duality, made
worse.
**Why bad:** Same scan, same roadmap concept, two different NOW/NEXT/LATER answers depending on
which surface the client is looking at (CLI vs. HTML/DOCX). Score-lift numbers attached to one
classification but not the other actively invites a client to notice the inconsistency.
**Instead:** if 999.101 touches this code, retire `categorize_waves()` in favor of
`build_phased_roadmap()`'s phases for the CLI table too (BACK-51 fold-in).

### Anti-Pattern 3: Routing report-composition config through the dashboard delta-overlay
**What:** Mirroring the connectors/advanced-scan-fields overlay pattern for `template_dir`/
branding tokens because "that's how config gets exposed to the dashboard here."
**Why bad:** The overlay pattern exists for per-scan-job runtime knobs a consultant sets at
scan-submission time. Report template/branding is a per-engagement authoring decision made in
`config.yaml` before any scan runs — there's no scan-submission form field this maps to, and
`template_dir` is a filesystem path (the same class of setting Tier 4 config-editing was deferred
over for security-review reasons).
**Instead:** config.yaml only, following the existing `report_owner`/`logo_path` precedent
directly.

### Anti-Pattern 4: A second finding-derivation code path for the storyline drawer
**What:** Writing new logic in `routes/scan.py` (or a new module) to independently recompute
key-reuse clusters or HNDL risk labels for the drawer instead of reusing
`compute_key_reuse_clusters()` / `findings_evaluator.py`'s existing HNDL derivation.
**Why bad:** QUIRK's established pattern (severity_bands.py, scoring.py) is "single producer,"
enforced by tests and by hard-won incident history (SCORE-01..05). A second key-reuse derivation
for the dashboard drifting from the report's `key_reuse` field is the same class of bug as the
CBOM/dashboard/report drift this project has repeatedly had to fix (999.104 parity work).
**Instead:** the dashboard's `_derive_findings()` calls the SAME `compute_key_reuse_clusters()`
/ HNDL-label functions the report path already calls, projecting their output onto `FindingItem`
fields.

## Sources

- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/writer.py` (write_reports:443,
  categorize_waves:293, format_scan_completed_at) — HIGH confidence, read directly.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/intelligence/roadmap.py` (build_phased_roadmap:99) — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/intelligence/scoring.py` (SCORE_WEIGHTS,
  _apply_weighted_impacts:158, compute_readiness_score:200) — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/intelligence/remediation.py`
  (slug_for_title:151, item_progress:161, REMEDIATION_KIND_SLUGS pattern) — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/content_model.py`
  (ExecContent:56, RoadmapItem:38, _enrich_roadmap_item:723) — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/html_renderer.py`
  (FileSystemLoader loader, line ~1005) — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/config.py` (AssessmentCfg:19,
  ConnectorsCfg:249, _user_set_fields pattern) — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/dashboard/api/schemas.py`
  (FindingItem:131, RoadmapNode/RoadmapEdge:494-499, validate_connectors_overlay:828) — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/dashboard/api/config_preview.py`
  (delta-overlay merge pattern) — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/tests/test_remediation_advisory_guard.py`,
  `tests/test_cve_score_guard.py` (ADVISORY-01 enforcement) — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/backlog/999.105-customizable-reporting-engine/IDEA.md` — HIGH (primary source, PM-filed and dev-verified).
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/backlog/999.101-roadmap-now-next-later-with-score-lift/IDEA.md` — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/backlog/999.102-finding-storyline-drawer/IDEA.md` — HIGH.
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/PROJECT.md` (Current Milestone
  section, v5.23 scope) — HIGH.
- `src/dashboard/src/components/ui/sheet.tsx` — confirmed present, not read in full (existence
  only) — MEDIUM confidence on exact API surface, HIGH confidence on its existence as the
  reusable primitive.

## Gaps to Address (flag for phase-specific research)

- **999.98 (SPKI fingerprint) current status is unverified in this pass.** IDEA.md for 999.102
  was filed 2026-09-07 declaring it blocked; PROJECT.md's v5.21 section lists 999.98 as shipped
  ("SPKI fingerprint persistence... the hard prerequisite for key-reuse detection" — v5.21 Phase
  target list). This reads as ALREADY SHIPPED, which would mean 999.102 is not actually blocked
  today. **This needs a definitive check at the roadmap-creation stage** (grep
  `compute_key_reuse_clusters` call sites and confirm SPKI fingerprint columns are populated in
  the live DB) before scoping 999.102's plans — the IDEA.md's blocking claim may be stale.
- **Whether 999.101's score-lift framing is report-surface-only or also dashboard-surface** was
  not resolved by IDEA.md and needs a roadmapper/PM decision — it changes whether `routes/scan.py`
  needs its own synthetic-rescore wiring (dashboard) in addition to `writer.py`'s (report).
- **Whether BACK-51's fold-in belongs in 999.101's phase or is deferred again** is explicitly
  left as "roadmapper's call" by both PROJECT.md and this research — not resolved here.
- **Exact current click-handling behavior of the findings table** (does row-click already do
  something the drawer would replace?) was not verified — the React findings-table component
  itself was not read in this pass; verify before writing 999.102's plan.
