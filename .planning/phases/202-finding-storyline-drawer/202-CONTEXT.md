# Phase 202: Finding Storyline Drawer - Context

**Gathered:** 2026-09-12
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — grey areas proposed from codebase evidence, operator decided
each one. All four decisions below are OPERATOR-CONFIRMED, not Claude's discretion.

<domain>
## Phase Boundary

Operator can open a per-finding storyline drawer from the dashboard findings table that narrates the
finding's quantum-risk story and its score-lift attribution, reusing the existing Phase-99 narrative
catalogs rather than forking a new one.

IN scope: the drawer surface on the dashboard findings table; one new read-only API endpoint feeding
it; score-lift attribution framed at the remediation-theme level; an a11y baseline capture for the
drawer's open/close/focus behavior.

OUT of scope: changing how score-lift is COMPUTED (Phase 201 owns that, and `int(delta)` truncation
is a tracked follow-up in `201-.../deferred-items.md` item 4 — do not "fix" it here); adding the
drawer to the print/PDF surface (it is an interactive affordance, not a report section); any new
narrative generator; persisting anything about drawer state.
</domain>

<decisions>
## Implementation Decisions

### D-01 — Score-lift attribution is THEME-framed, with the finding's share shown (STORY-02)

**This is the phase's load-bearing decision and it overrides a literal reading of the ROADMAP's
success criterion 3.** Criterion 3 says the drawer "displays the finding's score-lift attribution,
consuming Phase 201's LIFT-01 per-item number." Taken literally that is not implementable honestly,
because the number is not per-finding:

- `score_lift` lives on `RoadmapNode` (`quirk/dashboard/api/schemas.py:501`), joined by `slug`.
- A `slug` identifies a remediation THEME, not a finding — `build_phased_roadmap()` builds items from
  a fixed baseline of ~12 theme titles ("Disable legacy TLS versions", "Replace expired
  certificates", …), not one per finding.
- `item_progress()` (`quirk/intelligence/remediation.py`) proves the cardinality: it returns
  `(closed_count, total_count)` of "constituent fingerprint rows" per slug, its own docstring giving
  "6 of 8 verified closed".

So one theme's `+4 pts` is shared across N findings. Rendering it as a per-finding number would tell
the operator that resolving THIS finding yields 4 points, when 4 points requires resolving the theme.

**The drawer therefore renders:** the owning theme's title, the theme's lift with its condition
stated ("+4 pts when all 8 constituent findings are resolved"), this finding's position in the theme
("1 of 8", with the closed count from `item_progress()`), and an explicit line that the number is
not an individual contribution.

**Explicitly REJECTED — do not implement:** dividing `theme_lift / constituent_count` to manufacture
a per-finding share. It fabricates a number the scorer never computed, and lifts are not linear in
constituent count so the shares would not sum back to the theme lift. This is the same class of
defect as Phase 194's IN-02 (a compute failure fabricating `score=0/POOR`) and runs directly against
Phase 201's non-additivity design. A reviewer finding a division here should treat it as a blocker.

**Honest absence is inherited, not re-invented:** when `score_lift` is `None` the drawer shows no
number and says why — `None` must NEVER render as `0`, per the contract already documented at
`schemas.py:496-501`.

### D-02 — Narrative arrives via ONE new lazy per-finding endpoint (STORY-01)

`GET /api/findings/{id}/storyline` (auth-gated like every other route), returning the narrative plus
the D-01 theme attribution, assembled SERVER-SIDE from the existing catalogs.

Forced by a real constraint, not preference: `ALGO_IMPACT_MAP` / `REMEDIATION_CATALOG` are
Python-only (`quirk/engine/findings_evaluator.py`, `quirk/reports/*`) with **zero** references
anywhere under `quirk/dashboard/` — the TS dashboard cannot read them, so the narrative must cross
the API. And `FindingItem` (`schemas.py:131-152`) carries `description`/`remediation`/`quantum_risk`
but nothing from those catalogs and no join key.

Lazy-fetch-on-open chosen over widening the findings-list payload: only opened findings cost
anything, and `GET /api/scan/latest` already carries every finding in the scan — inflating it with
per-finding narrative for data needed only on a drawer open is the wrong trade.

### D-03 — Reuse the existing `Sheet` primitive; do NOT add a drawer library

`src/dashboard/src/components/ui/sheet.tsx` already exists (shadcn Sheet, alongside `dialog.tsx`).
No `vaul` or other drawer dependency is to be introduced. "Drawer" in this phase's language means a
Sheet, and the a11y behavior in D-04 is asserted against that primitive's real focus handling.

### D-04 — Extend the EXISTING a11y harness with a drawer capture (success criterion 4)

The "existing WCAG AA discipline" criterion 4 refers to is concrete and already wired:
`src/dashboard/tests/a11y/run-a11y.mjs`, `src/dashboard/tests/a11y/pinned-deps.test.ts`, and
`@axe-core/puppeteer` pinned at `4.11.3` in `src/dashboard/package.json`.

Add a drawer capture to that harness, structured the way current captures are, covering open, close,
focus trap, Esc-to-close, and focus returning to the triggering row. No new tooling, no new runner.

### D-05 — No fourth narrative generator (success criterion 2, locked by the ROADMAP)

The drawer's narrative MUST be sourced from the Phase-99 `ALGO_IMPACT_MAP` / `REMEDIATION_CATALOG`
catalogs so the live dashboard and the deliverable tell the same story for the same finding. If a
plan finds the catalogs insufficient for some finding class, the correct move is to surface that gap
explicitly (an honest absence in the drawer), NOT to write new narrative text in the dashboard layer.

### Claude's Discretion

Component file layout and naming, the endpoint's exact response field names, test file organisation,
and how the theme-attribution block is visually arranged within the drawer (subject to the UI-SPEC
that `gsd-ui-phase` will produce before planning).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `src/dashboard/src/components/ui/sheet.tsx` — the drawer primitive (D-03).
- `src/dashboard/src/pages/findings.tsx` (257 lines) — the host surface; the drawer opens from here.
- `quirk/intelligence/remediation.py` — `slug_for_title()` (exact-match only, no fuzzy fallback, by
  design) and `item_progress()` (the `closed/total` constituent counts D-01 needs).
- `quirk/engine/findings_evaluator.py`, `quirk/reports/content_model.py` — the Phase-99 catalogs.
- `src/dashboard/src/lib/utils.ts` — `formatScoreNumber()`, added in Phase 201's UI-review round;
  reuse it for any lift number the drawer renders so the drawer cannot drift from roadmap.tsx/print.tsx.
- `src/dashboard/tests/a11y/run-a11y.mjs` — the harness to extend (D-04).

### Established Patterns

- Auth-gated routers are constructed `APIRouter(dependencies=[Depends(require_auth)])` — the pattern
  `config.py`'s `effective_router` and Phase 193's `connectors.py` both use.
- Unrecognized request keys are rejected with 422 via an allowlist (Phase 193/194 connector and
  advanced-field gates). A read-only GET has less surface, but path params still need validation.
- A 500 handler must return a FIXED detail string, never `str(exc)` — Phase 193's 201-04 precedent,
  to avoid leaking filesystem paths.
- `None` means honest absence everywhere in this codebase and must never render as `0` or a dash
  styled as a value.

### Integration Points

- `quirk/dashboard/api/routes/` — new route module registered under `/api` beside the existing ones.
- `quirk/dashboard/api/schemas.py` — response model for the storyline payload.
- `src/dashboard/src/types/api.ts` — TS mirror. Phase 201's UI review established that these fields
  should be required `number | null` rather than optional `?:`, so `undefined` is not admitted; follow
  that for any nullable numeric added here.
</code_context>

<specifics>
## Specific Ideas

- The drawer must not require leaving the findings view (criterion 1) — that is why D-01 shows the
  attribution inline rather than linking out to the roadmap page.
- `.tsx` changes REQUIRE `npm run build && npm run lint && npm run test` from `src/dashboard/`, and
  the rebuilt statics under `quirk/dashboard/static/` must be committed with the source. A phase-201
  plan shipping un-rebuilt statics produced a false "no badge appears" defect report; Phase 195 hit
  the same thing.
- Colors come from design-system tokens, never hardcoded hex. If any value ever reaches a canvas,
  resolve it via `getComputedStyle` — a `var(--…)` string silently falls back to a default there
  (a real Phase 195 defect).
</specifics>

<deferred>
## Deferred Ideas

- Per-finding score-lift as a genuinely computed number (rather than D-01's theme framing) would
  require the scorer to model single-finding resolution. Not in scope; would need its own design.
- Drawer content in the PDF/print surface — rejected as out of scope above; a drawer is an
  interactive affordance, not a report section.
- `int(delta)` lift truncation (`quirk/intelligence/score_lift.py:164`) — tracked at
  `.planning/phases/201-score-lift-roadmap-re-frame/deferred-items.md` item 4. Do NOT address here;
  it moves an operator-approved displayed number on four surfaces.
</deferred>

---

# AMENDMENTS — 2026-09-12, post-research (operator-confirmed)

`202-RESEARCH.md` (commit `009e2f9d`) falsified parts of D-01 and D-02. All three amendments below
were put to the operator with evidence and confirmed. **D-06/D-07/D-08 supersede the conflicting
clauses in D-01/D-02 above; where they disagree, the amendment wins.** The original text is retained
unedited as the record of what was believed before research ran.

## D-06 — The storyline endpoint is keyed by `(endpoint id, title)`, NOT by id alone (supersedes D-02's route shape)

**D-02's `GET /api/findings/{id}/storyline` cannot work as written.** `FindingItem.id` is
`CryptoEndpoint.id`, not a finding id: `_derive_findings()` emits multiple `FindingItem`s per endpoint
inside one `for ep in endpoints:` loop (`quirk/dashboard/api/routes/scan.py:129`), every one carrying
`id=ep.id`. Verified by direct read — there are 9 such assignments in that loop, and one TLS endpoint
routinely yields 2-4 findings sharing a single `id`. Keying by id alone would return the wrong
finding's storyline, silently and plausibly.

**Resolution:** `GET /api/findings/{id}/storyline?title=<finding title>` — `title` is REQUIRED. The
`(endpoint id, title)` pair is unique, and the client already holds both from the row the operator
clicked, so no schema change or migration is needed.

**A title-translation layer is required and is in scope.** The dashboard's finding titles
(`_derive_findings` in `routes/scan.py`) and the CLI pipeline's titles (`evaluate_endpoints` in
`quirk/engine/findings_evaluator.py`) are two independently-maintained vocabularies for the same
conditions, and `RemediationItemFingerprint` rows are written only from the CLI vocabulary
(`run_scan.py:4071,4118`). Research reports ~5 of 9 TLS classes diverge (HTTP, legacy-TLS,
weak-cipher, cert-expired, cert-expiring) with 3 matching verbatim (self-signed, untrusted-CA,
undersized-RSA) — **the planner must re-verify this mapping class by class rather than trusting the
count**, since a wrong translation yields a confidently wrong theme. The route translates the
dashboard title to the CLI canonical title, then computes
`TicketingChannel.compute_fingerprint({host, port, title})` in memory. No re-scan, no DB write.

Note for the planner: `FindingItem.id` being non-unique is a latent trap for ANY future per-finding
feature, not just this one. Giving findings a genuinely unique identifier was considered and
deliberately NOT chosen here — it is a wider blast radius than Phase 202 needs. Worth filing as
backlog after this phase.

## D-07 — Absent narrative is the COMMON case and is accepted as faithful to success criterion 2

The Phase-99 catalogs are keyed by **crypto-algorithm keyword** (RSA/ECC/ECDSA/DH/DSA/hash
weaknesses), matched by case-insensitive substring search over title+description+category+check_id
(`quirk/reports/content_model.py:690-710`) — NOT by finding title. So the highest-volume finding
classes (plaintext HTTP, legacy TLS, expired/expiring certs, self-signed, untrusted CA) carry no
algorithm keyword and resolve to **absence case A5**. Narrative is the exception, not the rule:
RSA/ECDSA-key findings and named-weak-cipher findings (RC4/DES/MD5/SHA1 appearing in description
text) get narrative; most others do not.

**Operator decision: accept this, do not paper over it.** The reasoning is that criterion 2's intent
is "do not fork a generator — keep the deliverable and the dashboard telling the SAME story for the
same finding." The report has no narrative for those classes either, so rendering honest absence IS
that consistency, not a failure of it. D-05 stands unrelaxed: **no new narrative content is to be
written in this phase**, and the catalogs are not to be extended.

Consequence the planner must design for, not treat as an edge: the drawer's reliable value is the
**theme attribution block** (theme name, conditioned lift, closure progress) plus the finding's own
facts. A5 must therefore be a first-class, well-worded state — not a thin fallback — because
operators will see it more often than they see narrative. The UI-SPEC's S6 state (narrative absence
must NOT suppress the attribution block) is load-bearing for exactly this reason.

## D-08 — Multi-theme tie-break: prefer the specific theme over the `high-impact-findings` catch-all (closes a D-01 gap)

D-01 says "the owning theme" (singular). That is **not a data-model invariant**: verified live against
`./quirk-output/quirk.db`, **28 of 67 distinct fingerprints (41%) belong to 2+ themes**. The pattern is
uniform — every single multi-theme case pairs the `high-impact-findings` severity catch-all with one
specific title-based theme (`plaintext-http-exposure` ×21, `self-signed-certificates` ×5,
`expired-certificates` ×2).

**Resolution:** when a finding maps to more than one slug, display the **specific title-based theme**
and never the `high-impact-findings` catch-all. One rule, deterministic, explainable to an operator,
and it resolves 28 of 28 observed cases.

**A hand-ordered `_SLUG_PRIORITY` list was considered and REJECTED.** It is more general, but a
hand-maintained list of sites is this repo's documented recurring failure mode — CLAUDE.md records
four instances in the GSD toolchain, the staleness catalog list was found incomplete on 2026-09-12,
and the a11y harness's `HOOK_TARGETS` is a fifth. Do not introduce a sixth. If a future overlap
appears that is NOT the severity catch-all, that is the trigger to revisit — and it should be caught
by a test that derives the overlap set from data, not by a list someone remembers to update.

The drawer displays ONE theme. It does NOT hint that a finding also belongs to another theme —
showing two conditioned lift numbers side by side would make D-01's non-additivity point
substantially harder to convey, which is the whole problem D-01 exists to solve. Record this
simplification in the phase SUMMARY.

## D-09 — When `high-impact-findings` is a finding's ONLY theme, it IS rendered (closes a D-08 gap)

**Operator-confirmed 2026-09-12**, after the planner flagged this as an interpretation rather than
silently adopting it. D-09 is now a decision, not an interpretation — plans may cite it directly.

D-08's text governs the multi-theme **tie**: "when a finding maps to more than one slug… never the
catch-all." It is silent on a finding whose *only* theme is `high-impact-findings`. That case is real,
not hypothetical: `TLS certificate uses undersized RSA key` is `severity="HIGH"`
(`quirk/dashboard/api/routes/scan.py:240-241`) and appears in **no** `REMEDIATION_CONSTITUENCY`
fingerprint tuple, so the severity catch-all is its single genuine theme — with a genuine lift.

`REMEDIATION_CONSTITUENCY` (verified live, 14 slugs): 6 `fingerprint` slugs carrying explicit title
tuples, 7 `evidence_only` slugs with empty tuples, and `high-impact-findings` as the lone `severity`
matcher. Any HIGH-severity finding outside every title tuple therefore constitutes exactly one theme.

**Resolution: render the catch-all theme in that branch.** A literal "never the catch-all" reading
would route it to absence case A1 — telling the operator the finding maps to no remediation theme when
it demonstrably does, and withholding a real lift number. That is a **fabricated absence**, the exact
failure class D-01 and D-07 exist to prevent, pointed backwards. D-08's prohibition is about
preferring the specific theme when one competes with the catch-all; when nothing competes, the
catch-all is simply the truth.

The contrast case needs no interpretation and stays A1: `TLS certificate issued by untrusted CA` is
MEDIUM (`scan.py:292-293`) and in no constituency, so it genuinely belongs to no theme.

**Fencing (keep all of it).** The planner's handling is retained even though this is now a confirmed
decision: the branch is locked by a dedicated catch-all-only test in 202-05, surfaced in the 202-01 and
202-05 SUMMARYs, and documented in 202-08 — three independent places a future reader meets it, so
changing it later is a visible, deliberate edit rather than a silent drift.

**Not adopted:** labelling the catch-all in the UI as severity-derived ("Grouped by severity: …").
Considered and declined — it would add a sixth distinct attribution wording to maintain for a
precision gain the theme title ("Triage high-impact findings") already mostly conveys.
