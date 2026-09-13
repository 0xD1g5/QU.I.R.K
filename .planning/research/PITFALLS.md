# Pitfalls Research

**Domain:** Adding operator-controlled report templating/branding, score-lift roadmap
framing, and per-finding narrative drawers to an existing multi-renderer report pipeline in a
security/consulting product (QU.I.R.K. v5.23 Deliverable Experience).
**Researched:** 2026-09-11
**Confidence:** HIGH on codebase-verified items (file:line cited), MEDIUM on general SSTI/
templating-ecosystem claims (verified against Jinja2 docs knowledge, not re-fetched live),
LOW flagged explicitly where noted.

## Critical Pitfalls

### Pitfall 1: Autoescape hardens *data*, not *template source* — operator templates are a new SSTI/RCE surface, not a repeat of the v4.10 XSS class

**What goes wrong:**
The v4.10 hardening (`tests/test_report_injection_hardening.py`, `test_report_sanitization.py`)
proved that adversary-controlled *scan data* (e.g. a certificate CN containing
`<script>alert(1)</script>`) is escaped when rendered into the HTML report. Verified:
`html_renderer.py:1006` sets `autoescape=select_autoescape(["html", "j2"])` on the Jinja2
`Environment`. That is real and does its job. But 999.105 introduces a fundamentally different
threat: an **operator-supplied template file** loaded via `FileSystemLoader` pointed at a
custom directory (the IDEA.md's own proposed Tier 1 mechanism, `html_renderer.py:899-904` /
1004-1006 as verified). Autoescaping only affects how *variables* are escaped when interpolated
into HTML — it does nothing to stop the *template syntax itself* from executing arbitrary
Python. Verified: no `SandboxedEnvironment` or `ImmutableSandboxedEnvironment` import exists
anywhere in `quirk/` (`grep -rn "SandboxedEnvironment" quirk/` returns nothing) — the engine in
use is the plain `jinja2.Environment`, which is explicitly documented upstream as unsafe for
untrusted template *authors* (as opposed to untrusted template *data*). A hostile or
compromised template file can reach `{{ ''.__class__.__mro__[1].__subclasses__() }}`-style
object-graph walks to obtain OS/subprocess access, read arbitrary files via the loader, or exfil
`config.yaml` secrets rendered into other reports in the same process.

**Why it happens:**
The v4.10 fix and its regression tests were scoped to "data flowing through an existing fixed
template," so the team's mental model of "we already hardened injection" is anchored on that
narrower threat. Extending the *template loader's search path* to an operator-writable directory
silently swaps the threat actor from "scan target" to "whoever can edit a file the operator
points at" (which in a consulting engagement could be a client-supplied branding pack, or a
shared template library between engagements) — a much higher-trust boundary than the v4.10 model
assumed, but the code changes required to add it look identical (`FileSystemLoader(new_dir)`).

**How to avoid:**
- Use `jinja2.sandbox.SandboxedEnvironment` (or `ImmutableSandboxedEnvironment`) for any
  `Environment` instantiated with an operator/config-supplied `searchpath`, not the plain
  `Environment` already used for the stock template.
- Treat "template source" and "template data" as two separate trust domains in design docs and
  tests — do not let a green `test_report_injection_hardening.py` run stand in for template-
  source safety; it currently only exercises the data axis.
- If Tier 1 ships branding-token substitution only (per IDEA.md's stated floor: "config keys for
  a custom HTML template dir + extended branding tokens... DOCX/markdown get token-level
  branding only, not full templating"), scope the actual shipped surface tightly — token
  substitution into fixed placeholders is a much smaller, auditable surface than a full
  operator-authored Jinja2 template tree. Don't let the floor tier quietly grow into the Tier 3
  full-templating threat model without the sandboxing decision IDEA.md itself flags as open
  ("template-security consideration... operator-supplied Jinja templates execute in-process —
  sandboxing decision required").
- Constrain the template directory itself: resolve it through the same path-traversal-safe
  pattern already established for `logo_path` (see Pitfall 2) rather than inventing a new one.

**Warning signs:**
- A PR adds a config field like `custom_template_dir` and points `FileSystemLoader` at it
  without any accompanying test that tries to load a template containing Jinja2 SSTI payloads
  (e.g. `{{ config.__class__ }}`, `{% for x in ().__class__.__base__.__subclasses__() %}`).
- Code review approves the change by pointing at `test_report_injection_hardening.py` passing,
  without a new test file specifically for template-*source* trust.
- No `SandboxedEnvironment` appears anywhere in a diff that adds operator-controlled template
  paths.

**Phase to address:**
The 999.105 Tier 1 phase itself, at design time — before any `FileSystemLoader` path becomes
operator-configurable. This is a go/no-go gate, not a follow-up.

---

### Pitfall 2: `logo_path`'s existing path-traversal posture gets accidentally inherited — or accidentally forgotten — by the new branding/template surface

**What goes wrong:**
`quirk/config.py:24` already carries `logo_path: str | None` (Phase 100 / D-01), and it is
verified as deliberately excluded from the dashboard: `quirk/dashboard/api/schemas.py:991`
explicitly documents `assessment.logo_path` as a field the dashboard does not expose, presumably
because it is a local-filesystem path read at report-build time with no client-facing validation
boundary. 999.105 Tier 1's "extended branding tokens (colors, footer text, cover fields)" and a
"custom HTML template dir" are the same *shape* of field — a string that resolves to a
filesystem path or is interpolated into rendered output — and both risks (path traversal via a
crafted directory string; injection via unescaped footer/cover text making it into HTML/DOCX/PDF
outside the already-escaped content-model fields) can be silently reintroduced if the new fields
are wired through ad hoc rather than through whatever guard currently keeps `logo_path` CLI-only.

**Why it happens:**
`logo_path`'s CLI-only restriction is *tribal knowledge encoded as an absence* (it's simply not
in the dashboard schema) rather than a named, reusable validator function. A developer adding
"one more branding field" next to it has no code-level signal telling them to route it through
the same restriction — they'll naturally add it to whatever surface is easiest (often the
dashboard form, since that's where 999.104's parity work just made every other config field
visible).

**How to avoid:**
- Before adding any new branding/template config field, locate (or, if genuinely absent, write)
  the actual guard function that keeps `logo_path` off the dashboard, and route every new
  path-like or filesystem-resolving branding field through the identical function — don't
  re-derive a parallel check.
- Any new *text* branding field (footer, cover fields) that flows into the content model must go
  through the same escaping boundary already used for scan-data-derived fields — verify with a
  parametrized extension of `test_report_injection_hardening.py`'s XSS_PAYLOAD fixture pattern,
  not a new ad hoc test.
- Explicitly decide, and document, whether the new template-dir field is dashboard-exposed or
  CLI/config-file-only — 999.104's parity ethos ("every config field should be reachable from
  the dashboard") is in direct tension with `logo_path`'s deliberate exclusion, and 999.105 must
  not resolve that tension by default/omission.

**Warning signs:**
- A new branding config field appears in `quirk/dashboard/api/schemas.py` without an explicit
  code-review note explaining why it's safe to expose there when `logo_path` is not.
- A new field's value is passed straight to `open()`, `Path()`, or a Jinja2 loader constructor
  without going through a canonicalization + allowlist-root check.

**Phase to address:**
999.105 Tier 1, same phase as Pitfall 1 — these two are the same class of new attack surface and
should be gated together.

---

### Pitfall 3: A "score-lift" number on a roadmap item gets treated as ground truth or silently crosses the score firewall

**What goes wrong:**
999.101 wants each migration-roadmap item framed by "expected score movement" (a projected
delta if the item is remediated). ADVISORY-01 is machine-enforced today specifically to keep
*closure/advisory* data (remediation-tracking state) from feeding the readiness score — verified
via the existing guard test surface (`tests/test_remediation_advisory_guard.py`,
`tests/test_score_render_parity.py`, `tests/test_cve_score_guard.py`). A per-item "score-lift"
projection is a **new, different** hazard from the one ADVISORY-01 currently guards: it's not
closure data leaking backward into the live score, it's a *hypothetical future score* being
computed and then risking (a) being read by a consultant or client as a promise/guarantee
("fixing this gets you to 87"), or (b) being wired, even accidentally, into the same
`compute_readiness_score()` path that produces the actual live score, or (c) drifting from the
real score algorithm over time if it's computed by a separate, unmaintained code path (weight
constants, band thresholds, subscore rollup) that isn't kept in lockstep with
`intelligence/scoring.py` changes.

**Why it happens:**
"How much would fixing X move the score" is naturally computed by re-running the same scoring
function with one finding hypothetically resolved — which means someone will be tempted to
literally call `compute_readiness_score()` (or a fork of it) inside the roadmap-building code
path (`quirk/intelligence/roadmap.py:build_phased_roadmap`), creating exactly the kind of
cross-module coupling ADVISORY-01's existing guards were built to prevent in the *other*
direction. The failure mode isn't "closure feeds score" (already guarded) — it's "roadmap
computes score" landing in report/CBOM/dashboard surfaces with no equivalent guard, because no
prior feature ever produced a second, hypothetical score value before.

**How to avoid:**
- Treat "score-lift" as a **new advisory-only surface** requiring its own explicit guard test
  (mirroring ADVISORY-01's pattern), not an extension of the existing one — file it as its own
  named invariant (e.g. ADVISORY-02) so a future auditor can find it the way ADVISORY-01 is found
  today.
- Compute score-lift via a **pure, read-only simulation** that calls the real scoring function
  with a modified findings set and discards the result immediately — never persist a projected
  score anywhere the real score is read from (DB column, cache, CBOM property), and add a test
  asserting the live score computation path takes zero inputs from roadmap/migration code.
  ("congruence guard"-style tests already exist at `tests/test_congruence_guard.py`,
  `test_scoring_orthogonal_contract.py` — model the new test on those.)
- Frame score-lift in all three renderers with visible "projected, not guaranteed" language and
  keep it visually and structurally distinct from the real score gauge/number — do not reuse the
  same UI component (`ScoreGauge`) without a clear "projected" state, given the project's own
  history of frontend/backend severity-band drift (backlog 999.92, noted as still open in
  PROJECT.md).
- Recompute score-lift from the *current* scoring function at render time rather than caching a
  value computed against a stale scoring version — otherwise a QRAMM/scoring-v2-style change
  (which has happened multiple times in this project's history) silently produces wrong
  projections nobody notices because the number isn't validated against anything.

**Warning signs:**
- Any new column/field named something like `projected_score` or `score_lift` appears in the
  same ORM model or CBOM property namespace as the real score, rather than being computed
  on-the-fly and kept out of persistence.
- The score-lift computation lives inside `quirk/reports/` or `quirk/intelligence/roadmap.py`
  and imports scoring internals directly rather than calling the same public
  `compute_readiness_score()` entrypoint the real score uses (import duplication risk = drift
  risk).
- No new test file mirrors the existing `test_*_advisory_guard.py` / `test_congruence_guard.py`
  pattern for the new field.

**Phase to address:**
999.101's own phase — the score-firewall guard must ship in the same phase as the score-lift
feature, not as a follow-up hardening pass.

---

### Pitfall 4: Section composition (hide/reorder) breaks the zero-CRITICAL reporting congruence guard and the three-renderer parity contract simultaneously

**What goes wrong:**
Verified: `quirk/reports/writer.py:307` and `:927` gate report generation behavior on whether
`CRITICAL` findings are present (the "zero-CRITICAL" congruence logic this milestone's own
context calls out, tied to the historical BACK-89/`rating-band-critical-floor-halts-reports`
defect). Separately, verified parity tests exist across at least
`test_cross_surface_parity.py`, `test_report_render_parity.py`, `test_score_render_parity.py`,
`test_key_reuse_render_parity.py`, `test_quantum_risk_render_parity.py`,
`test_finding_engine_parity.py`, `test_report_coverage_parity.py`, `test_score_parity.py` — a
large, presence-based (per CLAUDE.md/memory: "field PRESENCE not visual appearance") test
surface asserting the CLI/HTML/DOCX renderers agree. Both of these were built assuming **every
report contains every section, always**. 999.105 Tier 2 (section composition profiles per
IDEA.md) breaks that assumption on purpose. Two concrete failure shapes:
1. A profile that omits the findings table but a scan has CRITICAL findings — does the
   zero-CRITICAL congruence guard (built around "does this report exist at all") still apply
   sensibly to a report that never shows findings in the first place? If the guard isn't
   explicitly re-derived per profile, it may either false-block a legitimate "executive summary
   only" profile, or (worse) silently stop protecting the full profile if the composition
   refactor accidentally short-circuits before the guard runs.
2. Existing parity tests assert presence of fields/sections across all three renderers
   unconditionally. The moment one profile drops a section from HTML but the equivalent
   markdown/DOCX code path wasn't updated to match (or vice versa), CI either (a) breaks loudly
   for every profile including full — a false blocker that makes teams disable the gate — or
   (b) the gate is naively scoped to "only assert presence for the default profile," which
   silently reopens exactly the drift the parity suite was built to catch, but only for
   non-default profiles.

**Why it happens:**
IDEA.md itself names this precisely and honestly: "Requires the renderers to iterate a section
list instead of hardcoding order, and a decision on how parity gates apply to partial profiles" —
this is a known, not hidden, open design question, but open design questions have a track record
in this project of being resolved by omission under deadline pressure (see the BACK-89 zero-
CRITICAL defect's own history: invisible for ~3.5 months, escalated from P2 to hard blocker only
after Phase 98's guard surfaced it).

**How to avoid:**
- Before writing renderer changes, explicitly design (and write down, in the phase's CONTEXT.md
  or an ADR) what "parity" means for a non-full profile: e.g. "sections present in a profile must
  be field-identical across all three renderers; sections absent from a profile must be verified
  absent by an explicit test, not merely untested."
  This turns the parity contract from "always all sections" into "conditionally scoped but still
  asserted both ways" rather than leaving it unscoped.
- Extend (don't bypass) the existing zero-CRITICAL congruence guard to be profile-aware: decide
  explicitly whether an executive-only profile is exempt from the CRITICAL-floor block or must
  still surface a "CRITICAL findings present, see technical report" fallback banner rather than
  silently omitting the fact from a client-facing document.
- Add a parametrized test matrix (profile × renderer × section) rather than a single flat parity
  test — this is the direct lesson from Pitfall 3's advisory-guard modeling and from this
  project's own repeated pattern (per memory: "a written list of known sites is not a
  safeguard... only a scan that regenerates its occurrence set from source" — apply the same
  discipline to "which sections exist per profile" by deriving it from the section registry at
  test-run time, not hand-enumerating it).

**Warning signs:**
- A PR refactors renderers to a "section list" without touching
  `tests/test_cross_surface_parity.py` or its siblings at all — that's a sign the tests are
  either not exercising the new code path, or are about to start failing for unrelated reasons.
- The zero-CRITICAL guard's condition (`writer.py:307`/`:927`) is left keyed only to
  "report generated at all" with no profile parameter threaded through.

**Phase to address:**
999.105 Tier 2 phase (section composition) — this is the phase IDEA.md itself recommends a
"short spike... prototype a section registry for the markdown surface only" before committing;
that spike should specifically produce the profile-aware parity/congruence design, not just prove
the registry mechanism works.

---

### Pitfall 5: BACK-51's fold-in resolves the *symptom* (one roadmap reaching the operator) while leaving the *cause* (two divergent data models) intact under a single UI

**What goes wrong:**
Verified: `quirk/intelligence/roadmap.py:99` defines `build_phased_roadmap()` and
`quirk/reports/writer.py:293` defines `categorize_waves()` — two genuinely separate functions in
two separate modules, confirming BACK-51's premise. The risk named in the milestone context —
"re-framing one of the two systems without unifying may worsen the incoherence" — is concrete:
999.101's score-lift re-frame is exactly the kind of feature that's easy to bolt onto *one* of
the two builders (whichever one the phase's author happens to touch first) while leaving the
other producing roadmap items with no score-lift annotation at all. Because IDEA.md flags
BACK-51 as merely "opportunistic... in scope if the 999.101 re-frame touches that code anyway,"
there's a real chance the phase ships score-lift on `build_phased_roadmap()`'s output only, and
`categorize_waves()` (used in a different renderer/surface) keeps its old framing — meaning the
same underlying findings get *two different roadmap presentations* depending on which surface an
operator is looking at, one with score-lift and one without, which is worse than today's status
quo of "two roadmaps, same framing on both."

**Why it happens:**
The two functions likely serve genuinely different call sites (e.g. one feeds the HTML/DOCX
executive roadmap section, the other feeds a different aggregation used elsewhere — possibly the
dashboard or CLI table) that grew independently over multiple past phases, and nobody has yet
needed to reconcile them because neither one previously carried score-relevant framing that made
divergence visible to a consultant. Score-lift makes the divergence visible for the first time.

**How to avoid:**
- Before implementing 999.101, have the roadmapper (per IDEA.md: "roadmapper's call") explicitly
  answer: do `build_phased_roadmap()` and `categorize_waves()` feed the *same* rendered roadmap
  section across surfaces, or genuinely different UI concepts? If the former, unify before adding
  score-lift (BACK-51 done as a prerequisite, not opportunistically). If the latter, document why
  divergent framing is acceptable and make that an explicit written decision, not an accident of
  which function got touched first.
- Whichever choice is made, add a single cross-surface test asserting that every roadmap item
  visible anywhere in CLI/HTML/DOCX/dashboard carries the *same* score-lift value for the same
  underlying finding — reusing the parity-test pattern already established elsewhere in this
  codebase.

**Warning signs:**
- A diff modifies only one of `roadmap.py:build_phased_roadmap` or `writer.py:categorize_waves`
  to add score-lift fields, with no corresponding change (or explicit "N/A, different surface"
  comment) in the other.
- Two roadmap-shaped renders of the same scan show different item counts, ordering, or framing
  for what should be the same list.

**Phase to address:**
999.101's phase, gated on an explicit roadmapper decision recorded before implementation starts
— per IDEA.md's own "roadmapper's call" language, this must not be left implicit.

---

### Pitfall 6: The finding storyline drawer becomes a fourth report surface that the existing three-renderer parity discipline never covers

**What goes wrong:**
999.102's drawer is dashboard-only (React), not one of the three existing renderers
(CLI/HTML+PDF/DOCX). The project's parity discipline — and its own stated limitation, per
CLAUDE.md's milestone context item (4): "cross-surface parity tests assert field PRESENCE not
visual appearance; visual fidelity needs human UAT" — was built around exactly three renderers
sharing one content model. A narrative drawer that pulls per-finding "so what" / remediation
context (the `ALGO_IMPACT_MAP` / `REMEDIATION_CATALOG` data introduced in Phase 99, per
PROJECT.md's own history) risks either (a) duplicating that narrative logic in a new
dashboard-only code path that drifts from the report renderers' version over time, or (b) being
built against a *new* per-finding "storyline" field that never gets backfilled into the CLI/HTML/
DOCX reports at all — meaning the consulting deliverable (the actual PDF/DOCX handed to a client)
and the live dashboard view of the same scan tell two different stories for the same finding.

**Why it happens:**
The drawer is explicitly UI-only in scope ("Obsidian Pro design remnant... per-finding narrative
drawer on the dashboard" per PROJECT.md), so it's natural to implement it as a self-contained
React feature reading directly from `/api/scan/latest`'s existing finding fields, without routing
new narrative content back through the shared content model
(`quirk/reports/content_model.py`) that the three renderers already consume.

**How to avoid:**
- Reuse `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG` (Phase 99) as the single source of per-finding
  narrative content for the drawer rather than inventing a parallel narrative string — if the
  drawer needs more/richer narrative than what those catalogs provide today, extend the catalogs
  (which the reports already consume) rather than forking a dashboard-only equivalent.
  This keeps "the report IS the product" framing (HORIZON.md, cited in IDEA.md) honest: the
  deliverable and the live view should tell the same story, not two.
- If the drawer's storyline genuinely needs to be richer than what any current report shows,
  treat that as a new field on the content model itself, flowing to all three renderers even if
  only the dashboard exposes it in v5.23 — not a drawer-exclusive backend field.

**Warning signs:**
- A new API field (e.g. `finding.storyline`) is added to `/api/scan/latest` that is computed
  from data never referenced by `content_model.py`, `technical.py`, `html_renderer.py`, or
  `docx_renderer.py`.
- The remediation/impact text shown in the drawer for a given finding differs, even slightly in
  wording, from the same finding's text in the HTML/DOCX report.

**Phase to address:**
999.102's phase, at design time — the content-model reuse decision should be made before any
React component is scaffolded.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|-----------------|
| Ship Tier 1 branding as raw Jinja2 template override without sandboxing | Fast, small diff (`FileSystemLoader` swap already proven at `html_renderer.py:899`) | New RCE-class surface once any third party (client, subcontractor) can supply a template file | Never for full template override; acceptable ONLY for token-substitution into fixed placeholders (no new Jinja2 control-flow syntax reachable) |
| Compute score-lift by re-running the real scorer inline inside roadmap code | Simplest way to get an accurate number | Couples roadmap module to scoring internals; any future scoring refactor (this project has done several — scoring v2, QRAMM changes) silently breaks or drifts the projection | Acceptable only if wrapped in a single, tested, pure function called through the public scoring entrypoint, never a forked/duplicated formula |
| Scope parity tests to "default profile only" when adding section composition | Unblocks Tier 2 quickly without touching the whole parity suite | Silently reopens the exact drift class the parity suite exists to catch, but only for non-default profiles — which are the newest, least-tested code paths | Never as a permanent state; acceptable as a short-lived spike artifact only, must be closed out same phase |
| Build the storyline drawer directly off raw finding JSON instead of the shared content model | Faster to prototype in React alone | Second, independently-drifting narrative-text source for the same finding; violates "the report IS the product" | Acceptable for an internal spike/prototype only, must be replaced before the phase's SUMMARY.md is written |
| Leave `build_phased_roadmap()`/`categorize_waves()` unmerged and add score-lift to just one | Smaller diff, faster to ship 999.101 alone | Two divergent roadmap presentations for the same scan, now distinguishable by a client-visible number (score-lift), not just cosmetic ordering | Only acceptable if the roadmapper makes and documents an explicit, deliberate decision that the two functions serve genuinely different surfaces |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|--------------|----------------|-------------------|
| Jinja2 `FileSystemLoader` with operator-supplied path | Treating it as an extension of the already-hardened autoescape/XSS surface | Use `SandboxedEnvironment` for any environment whose search path includes operator/config input; keep the stock `Environment` only for the bundled, version-controlled template |
| `docxtpl` (if Tier 3 ever ships) | Assuming python-docx's imperative model and `docxtpl`'s Jinja-in-DOCX model share a security posture | `docxtpl` also executes Jinja2 template syntax embedded in `.docx` XML — same sandboxing decision applies, and IDEA.md already flags this as an open unknown requiring a spike |
| Score-lift projection vs. live score (`compute_readiness_score()`) | Forking or reimplementing scoring logic for the "what-if" projection | Call the real, single scoring entrypoint with a modified findings set; never persist the result anywhere the real score is read from |
| Dashboard `/api/scan/latest` vs. report content model | Adding a dashboard-only field for the storyline drawer that the reports never see | Route new per-finding narrative content through `content_model.py` so all consuming surfaces (report renderers included) can pick it up |
| Section-composition profiles vs. existing presence-based parity tests | Assuming the current parity suite "just works" once renderers iterate a section list | Explicitly redesign what parity means per-profile before refactoring renderers; add a profile×renderer×section test matrix |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Loading operator/config-supplied templates into a plain (non-sandboxed) Jinja2 `Environment` | Server-side template injection → arbitrary code execution in the process that also holds scan credentials and connector secrets | `SandboxedEnvironment`/`ImmutableSandboxedEnvironment`; restrict template directory to a canonicalized, allowlisted root |
| New branding/template path fields skipping the same restriction `logo_path` already has (dashboard exclusion) | Path traversal or SSRF-adjacent local file read, reachable from a network-exposed dashboard instead of only local CLI/config | Route every new filesystem-path-shaped config field through the same guard/exclusion `logo_path` uses; make an explicit, reviewed decision if a field is meant to break that pattern |
| Free-text branding fields (footer, cover text) bypassing the escaping boundary that scan-data fields already go through | Reopens the exact v4.10 XSS class, just via a different (operator-controlled rather than scan-controlled) input | Extend `test_report_injection_hardening.py`'s payload fixture to cover every new free-text branding field, not just scan-derived fields |
| Score-lift value computed by a path that isn't kept in lockstep with the real scoring formula | A client-facing document promises a specific score improvement that is provably wrong the next time scoring changes (this project has revised scoring multiple times: v2, QRAMM, band contracts) | Compute at render time from the live scoring function; never cache/persist a projected number tied to a scoring-formula version that can drift |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|------------------|
| Score-lift numbers presented with the same visual weight/component as the real readiness score | Consultant or client mistakes a projection for a guarantee, undermining the tool's "defensible" positioning (PROJECT.md's Core Value statement) | Visually and structurally distinguish projected vs. actual score (different component, explicit "projected" label, no shared gauge) |
| Section-composition profiles silently hide CRITICAL findings from an executive-only report with no acknowledgment | Client-facing document appears clean while CRITICAL issues exist, undermining the "defensible... deliverable" positioning and echoing the historical BACK-89/zero-CRITICAL defect's consequences (reports halting or misrepresenting posture) | Any profile that omits the findings detail must still surface a "CRITICAL findings exist — see technical report" banner rather than silent omission |
| Storyline drawer narrative text diverges from the shipped PDF/DOCX report's wording for the same finding | Client-facing inconsistency between the live dashboard demo and the delivered document erodes trust in "the report IS the product" | Single source of narrative content (`content_model.py` + `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG`) feeding both surfaces |

## "Looks Done But Isn't" Checklist

- [ ] **Template/branding override (999.105 T1):** Often missing a sandboxed Jinja2 environment
      — verify `SandboxedEnvironment` (not plain `Environment`) is used for any operator-supplied
      `FileSystemLoader` search path, and that an SSTI payload test exists alongside the existing
      XSS payload test.
- [ ] **Score-lift roadmap framing (999.101):** Often missing an explicit advisory-firewall test
      — verify a new guard test exists (named analogously to ADVISORY-01) proving the live score
      computation path takes zero inputs from the score-lift/roadmap code, and that no
      `projected_score`/`score_lift` value is persisted in the same store as the real score.
- [ ] **Section composition profiles (999.105 T2):** Often missing profile-aware parity —
      verify a profile×renderer×section test matrix exists, and that the zero-CRITICAL
      congruence guard (`writer.py:307`/`:927`) has an explicit, documented behavior for
      non-default profiles rather than being silently bypassed or silently blocking them.
- [ ] **BACK-51 fold-in (999.101 opportunistic):** Often missing full-surface consistency —
      verify score-lift (or any new roadmap framing) appears identically wherever
      `build_phased_roadmap()` and `categorize_waves()` output reaches an operator, or that a
      written decision explains why they may legitimately differ.
- [ ] **Storyline drawer (999.102):** Often missing content-model reuse — verify the drawer's
      narrative text is sourced from (or added to) `content_model.py`/`ALGO_IMPACT_MAP`/
      `REMEDIATION_CATALOG` rather than a parallel dashboard-only computation.
- [ ] **`logo_path`-adjacent new fields:** Often missing the existing dashboard-exclusion pattern
      — verify any new filesystem-path-shaped branding field is either explicitly excluded from
      `quirk/dashboard/api/schemas.py` like `logo_path`, or its dashboard exposure is a reviewed,
      written decision rather than an accident of the 999.104 parity push.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|-----------------|
| Operator template SSTI shipped unsandboxed | HIGH | Retrofit `SandboxedEnvironment`, audit any templates already deployed to engagements for exploitation attempts (log review), rotate any secrets that could have been read from the process environment during the exposure window |
| Score-lift leaks into or drifts from real score | MEDIUM | Add the missing advisory-firewall test retroactively; audit any already-delivered client reports for incorrect score-lift claims and consider a correction notice if numbers were materially wrong |
| Section profiles broke parity silently for non-default profiles | MEDIUM | Derive the section registry at test-run time (per this project's own established remediation pattern for undercounted defect classes) rather than trusting a hand-written list of "known" sections; re-run the full profile×renderer×section matrix |
| Two roadmap builders diverge visibly after 999.101 | LOW-MEDIUM | Add the cross-surface roadmap-item test late if needed; the fix is a genuine unification of `build_phased_roadmap()`/`categorize_waves()`, deferred but not abandoned |
| Storyline drawer text drifts from report narrative | LOW | Point the drawer at the shared catalog/content model in a follow-up phase; low blast radius since it's dashboard-only, not yet a client deliverable divergence until a report surface also shows storylines |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| Unsandboxed operator template SSTI | 999.105 Tier 1 phase | New test asserting `SandboxedEnvironment` (or equivalent restricted execution) is used for any config/operator-supplied Jinja2 search path; SSTI payload regression test alongside existing XSS payload test |
| `logo_path`-class field exposure drift | 999.105 Tier 1 phase | Explicit code-review checklist item + test asserting new path-like branding fields follow (or deliberately, documentedly diverge from) `logo_path`'s dashboard-exclusion pattern |
| Score-lift crossing the score firewall | 999.101 phase | New advisory-firewall guard test (ADVISORY-02-style) proving zero backward data flow from roadmap/score-lift code into `compute_readiness_score()`'s inputs; no persisted `projected_score` field co-located with the real score |
| Section-composition parity/congruence gaps | 999.105 Tier 2 phase | Profile×renderer×section test matrix; zero-CRITICAL congruence guard explicitly extended (not bypassed) for non-default profiles |
| Dual roadmap builder incoherence (BACK-51) | 999.101 phase, gated on explicit roadmapper decision | Cross-surface test asserting identical score-lift/framing for the same finding regardless of which builder's output reaches the operator, OR a written ADR explaining a deliberate divergence |
| Storyline drawer narrative drift from reports | 999.102 phase | Test or manual check confirming drawer narrative text is sourced from the same catalog (`ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG`/`content_model.py`) consumed by the three report renderers |

## Sources

- Direct codebase verification (HIGH confidence, cited inline by file:line):
  `quirk/reports/html_renderer.py` (Jinja2 `Environment`/`FileSystemLoader`/`autoescape`
  configuration, lines 9, 899-904, 1004-1006), `quirk/config.py` (lines 22-24, `logo_path`/
  `report_owner`), `quirk/dashboard/api/schemas.py:991` (`logo_path` dashboard exclusion),
  `quirk/reports/writer.py` (lines 293, 307, 927 — `categorize_waves`, zero-CRITICAL logic),
  `quirk/intelligence/roadmap.py:99` (`build_phased_roadmap`), and the test suite file listing
  under `tests/` (parity tests, `test_report_injection_hardening.py`,
  `test_remediation_advisory_guard.py`, `test_congruence_guard.py`,
  `test_scoring_orthogonal_contract.py`, `test_score_render_parity.py`).
- `.planning/backlog/999.105-customizable-reporting-engine/IDEA.md` — Tier 1/2/3 shape,
  feasibility notes, and the milestone's own named open questions (parity-per-profile,
  DOCX-templating/sandboxing decision).
- `.planning/PROJECT.md` — milestone framing (v5.23 Deliverable Experience), historical
  BACK-89/zero-CRITICAL congruence-guard defect precedent, ADVISORY-01 score-firewall
  precedent, Phase 99/100 branding and per-finding-context history, 999.104 parity-push context
  creating tension with `logo_path`'s exclusion.
- General Jinja2 sandboxing knowledge (MEDIUM confidence — training-data based, not re-verified
  against live Jinja2 docs in this session): `jinja2.sandbox.SandboxedEnvironment` is the
  documented mechanism for executing untrusted template *source*; plain `Environment` is
  explicitly documented upstream as unsafe for that purpose regardless of autoescape settings.
  Recommend a live doc check (Context7 or jinja.palletsprojects.com) at 999.105 Tier 1
  implementation time to confirm no API changes since training cutoff.

---
*Pitfalls research for: QU.I.R.K. v5.23 Deliverable Experience milestone*
*Researched: 2026-09-11*
