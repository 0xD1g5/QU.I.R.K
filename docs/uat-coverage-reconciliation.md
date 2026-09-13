# UAT Coverage Reconciliation (COV-03)

**Regenerate this document's numbers with:**

```bash
.venv/bin/python -m scripts.uat_corpus reconcile
```

Every number below was produced by that command against the live `docs/UAT-SERIES.md` and
`docs/uat-disposition-ledger.jsonl` in the same session that wrote this file. Do not trust any
number in this document without re-running that command first — this file, `204-CONTEXT.md`, and
`ROADMAP.md` have each carried at least one stale or wrong count during Phase 204 alone.

---

## 1. Authoritative source

**`docs/UAT-SERIES.md` is the single authoritative source going forward.** The ledger
(`docs/uat-disposition-ledger.jsonl`) is retained as **historical evidence** for how the 12
document/ledger discrepancies below were resolved — it is not a live input to the COV-01
generator (wave 3 of this phase) or to any future count.

Both halves of this reasoning are load-bearing, not just the winning half:

- The **ledger** is authoritative on a distinction the document's own checkbox grammar cannot
  express. `scripts/uat_disposition_apply.py` renders both a verified substitute (`DEFERRED`) and
  an honest absence (`GAP`) as the same checked `SKIP` box; only the ledger's `outcome` field
  disambiguates them. But the ledger **structurally cannot cover series 164+** — it was built for
  Phase 168's series 1–100 and Phase 169's series 101–163, and extending it forward would mean
  hand-maintaining a second list alongside the document, the exact failure mode this project has
  now named five separate times (see `CLAUDE.md` §"GSD `state.*` Verb Integrity" and this phase's
  own ID-regex correction in `204-CONTEXT.md`).
- The **document** covers every series, including 164+, and is the artifact the standing
  zero-undispositioned gate (`tests/test_uat_zero_undispositioned_gate.py`, `UATREC-04`) already
  parses **directly** — deliberately never consulting the ledger (`CLAUDE.md` §"UAT Corpus
  Integrity Gate"). But its checkbox grammar alone is lossy on the DEFERRED-vs-GAP distinction.

Picking either source as a permanent winner would institutionalize the ambiguity. Instead, the 12
document/ledger discrepancies (decomposed in §3) are resolved **into** the document in plan
204-02, collapsing the ambiguity at its origin rather than managing two sources forever.

## 2. Which count the drain is measured against

**The drain is measured against the document's own `GAP` dispositions across ALL series,
recomputed at run time by `python -m scripts.uat_corpus reconcile`.** Not the ledger's 57
(structurally bounded to series ≤163, misses everything newer) and not a naive
numeric-series-only count (misses alpha-prefixed, decimal, backlog, and three-segment IDs — the
exact class this phase's own scouting parser dropped; see `204-CONTEXT.md`'s correction notice).

### The GAP-attribution rule, and why it is NOT "any GAP string in the case's span"

The live count is **attribution-rule-dependent**, and this is the central finding this task had to
adjudicate (surfaced in `204-PREFLIGHT-MEASUREMENT.md` before this plan executed). Three
defensible rules give three different answers:

| Attribution rule | Live count |
|---|---|
| GAP on the case's own `**Result:**` line only | **54** |
| GAP on the case's own `**Result:**` **or** `**Notes:**` line | **66** |
| Any GAP string anywhere in the case's section span (heading to next heading) | **70** |

**`docs/uat-coverage-reconciliation.md` adopts the middle rule: GAP on the case's own `**Result:**`
line, OR (a checked `SKIP` with no `**Result:**`-line annotation) whose own `**Notes:**` line
carries the GAP string.** This is `scripts/uat_corpus.py::CaseRecord.is_gap`. The live re-derived
drain target under this rule is **66**, not 70.

Both rejected alternatives were re-run and instrumented, not assumed wrong:

- **Result-line-only (54) under-counts by 12.** Twelve real, honestly-GAP cases carry a checked
  `SKIP` box with **no** parenthetical annotation on the Result line at all — their GAP string
  lives only on the case's own `**Notes:**` line (e.g. the Phase 185/186 "Recorded honestly..."
  cases such as `UAT-185-*` and `UAT-186-*`). A Result-line-only rule would silently drop these 12
  from the drain, which is the exact under-reporting failure mode `hw_cve.py`-style staleness
  catalogs and this phase's own ID-regex bug both already demonstrated: a confident wrong count
  that neither crashes nor warns.
- **Any-GAP-string-in-span (70) over-counts by 4.** Four cases — `UAT-193-10`, `UAT-199-06`,
  `UAT-200-11`, `UAT-202-12` — are each the **final case of their series**, immediately followed by
  a trailing series-summary paragraph that quotes a *different, earlier* case's GAP disposition in
  prose (e.g. `UAT-193-10`'s trailing paragraph says "`UAT-193-09` remains GAP — no substitute
  coverage", not a disposition of `UAT-193-10` itself). None of these four carries a GAP
  disposition of its own on either its Result or Notes line. A section-span rule attributes another
  case's GAP string to the wrong case purely by proximity — this is a second, independent
  demonstration of the same class of error as the trailing-summary hazard, pointed at attribution
  scope rather than ID grammar.

**Prior documents claimed / live parse says:**

| Document | Claimed doc-GAP count | Live re-derived count | Superseded by |
|---|---|---|---|
| `204-CONTEXT.md` (D-03) | 70 | **66** | This document, §2 above |
| `ROADMAP.md` | 70 | **66** | This document, §2 above |
| `204-PREFLIGHT-MEASUREMENT.md` | 70 (confirmed match, but flagged as attribution-rule-dependent) | **66** | This document adjudicates the rule that measurement explicitly left open |

This is recorded as a finding in the same shape `204-CONTEXT.md` used when it corrected its own
841/69 scouting-parser error: the disagreement is real, the arithmetic explains it exactly (66 = 70
− 4 over-count + 0, or equivalently 54 + 12 = 66), and neither prior document is "wrong" so much as
measured under a looser rule than the one this document adopts. `204-CONTEXT.md` is intentionally
left unedited — see `.planning/phases/204-worklist-truth-derivation/204-CONTEXT.md`'s own
instruction that corrections are recorded forward, not retrofitted into prose already marked
LOCKED.

## 3. The divergence, decomposed

Ledger `outcome: GAP` rows total **57**, bounded to series ≤163 (the ledger's own maximum,
recomputed live as **158**, since not every series in 1–163 has a GAP row). Document `GAP` cases
(the adjudicated §2 rule) total **66**, covering every series. The two numbers explain each other
across four causes; the arithmetic closes in both directions:

| # | Cause | Live count | Live case IDs | Nature |
|---|---|---|---|---|
| 1 | Doc-GAP in a series beyond the ledger's own maximum (158) — no ledger row exists | **21** | *(all doc-GAP cases in series >158; not itemized here — see the `reconcile()` output's `doc_gap_without_ledger_row` field)* | **Not a disagreement.** The ledger never covered these series in the first place; this is a coverage gap in the ledger, which is why the pre-204 worklist missed them entirely |
| 2 | Doc says `DEFERRED`, ledger says `GAP` | **8** | `UAT-11-02`, `UAT-41-03`, `UAT-47-04`, `UAT-5-18`, `UAT-5-19`, `UAT-85-08`, `UAT-89-01-01`, `UAT-96-08` | **A real per-case dispute**, resolved in plan 204-02 by checking whether the cited substitute actually exists and covers the case |
| 3 | Doc carries no GAP-attributable annotation at all (`SKIP_OTHER`, no own-Notes GAP string), ledger says `GAP` | **4** | `UAT-67-04`, `UAT-88-02`, `UAT-88-03`, `UAT-92-01` | Resolved in plan 204-02 — these get an explicit annotation, not silently inherited from the ledger |
| 4 | Ledger id matches no document heading at all | **0** | *(none)* | Would be a ledger data defect per §4's rule — none currently exists |

**Cause 2 is 8, not the 7 named in `204-CONTEXT.md`'s D-01 table.** `UAT-89-01-01` is a genuine
three-segment `### ` heading (`docs/UAT-SERIES.md:10574`) — a real case, not a ledger defect (see
`204-CONTEXT.md`'s own D-06 correction). Once the parser's ID grammar stops truncating
three-segment IDs, this case's document disposition (`DEFERRED`) and ledger disposition (`GAP`)
resolve to a genuine 8th conflict that the phase's earlier scouting pass, still bound by the
truncating regex, could not see. This is recorded as a finding, not silently absorbed into the
original count of 7.

**Arithmetic closes both directions** (see the `reconcile()` output's `arithmetic_detail` /
`arithmetic_ok` fields, asserted programmatically rather than eyeballed):

- Document direction: doc-GAP total (66) = has-a-ledger-row (45) + no-ledger-row/cause-1 (21).
- Ledger direction: ledger-GAP total (57) = has-a-matching-doc-GAP (45) + cause-2 (8) + cause-3 (4).

Both sums check out against the live totals above (45 + 21 = 66; 45 + 8 + 4 = 57).

## 4. Ledger data defects

**None found in this pass.** Every one of the 57 ledger `GAP` rows matches a real document
heading (`ledger_ids_absent_from_doc` is empty in the live `reconcile()` output). The one id that
an earlier draft of `204-CONTEXT.md` flagged as a malformed defect — `UAT-89-01-01` — was itself a
mis-measurement (the truncating regex, not a real ledger defect): it is a genuine three-segment
case heading and the ledger row is correct. `204-CONTEXT.md`'s D-06 already withdraws that finding;
this reconciliation independently confirms the withdrawal against the live corpus rather than
merely repeating it. No ledger id inflates any count in this document.

If a future re-run of `python -m scripts.uat_corpus reconcile` reports a non-empty
`ledger_ids_absent_from_doc`, record it here as a genuine data defect (with the most plausible
corrected id noted as a hypothesis) and do not invent a document case for it.

## 5. Provenance

- **Generated:** 2026-09-13, Phase 204 Plan 01, in the same session as `scripts/uat_corpus.py`.
- **Command:** `.venv/bin/python -m scripts.uat_corpus reconcile`
- **Live totals this document was generated against:**
  - Total case headings: **878**
  - Disposition counts: `PASS 683, SKIP_OTHER 89, DEFERRED 47, FAIL 5, GAP 54` (Result-line-scoped)
  - Doc-GAP (Result-line annotation): **54**
  - Doc-GAP (Notes-line only, no Result annotation): **12**
  - **Doc-GAP total (adjudicated rule, §2): 66**
  - Ledger rows: **378**; ledger `outcome: GAP`: **57**; ledger max series: **158**
  - Cause 1 (beyond ledger max series): **21**; Cause 2 (DEFERRED/GAP conflict): **8**;
    Cause 3 (unannotated/GAP conflict): **4**; Cause 4 (ledger id absent from doc): **0**
  - Arithmetic closes: **True**

**These totals drift.** The corpus grows every phase that adds UAT series. Re-run the command
above before citing any number from this document in a future plan, review, or milestone close —
never transcribe these numbers forward without recomputing them, exactly as this document itself
had to correct two prior documents' transcribed 70.

## Per-case verdicts (COV-03)

**Plan 204-02, Task 1.** Live `reconcile()` re-derivation before this task started confirmed
wave 1's 204-01-SUMMARY.md sets exactly: **8** cause-2 conflicts (doc `DEFERRED`, ledger `GAP`) and
**4** cause-3 unannotated cases (doc no GAP-attributable annotation, ledger `GAP`) — the same 12
ids `204-CONTEXT.md`'s D-01/D-05 named plus `UAT-89-01-01` (D-06's withdrawal). No reconciler
finding diverged from the wave-1 prediction this time.

**The single structural finding that resolved all 8 cause-2 conflicts identically:** none of the 8
`DEFERRED` annotations in the document ever cited a substitute node (no `covered by <node>` clause
anywhere in any of them). Every one of the 8 annotations *textually reads* `DEFERRED — no
substitute coverage; needs a ...` — i.e. the annotation's own content is GAP-shaped prose (openly
admitting no substitute exists) that was mechanically mislabeled with the `DEFERRED` token instead
of `GAP`. `scripts/uat_corpus.py::classify_annotation()` classifies purely on the leading token, so
it read these as `DEFERRED` even though the ledger's structured `outcome` field (and the sentence
right after the em-dash) always said `GAP`. There is no case here where "the substitute holds" —
every verdict is "no substitute was ever cited; ledger was right; rewrite `DEFERRED` to `GAP`,
same body text unchanged." Per critical rule 3 (`sensors-loading.test.tsx` standard): a citation
that resolves to nothing is not a substitute, and here there was never even a citation to resolve.

Applying the project's standing anti-fabrication guard's own contract
(`tests/test_uat_disposition_integrity.py::test_ledger_matches_document`, which asserts the
ledger's `evidence` field is byte-identical to the document's own annotation for every id) meant
each of these fixes also required updating the corresponding `docs/uat-disposition-ledger.jsonl`
row's `evidence` field to match the corrected annotation — not to re-derive the outcome (the
`outcome: "GAP"` field was already correct and untouched) but to keep the ledger internally
consistent with its own `outcome` field, which its `evidence` prose had drifted from. This is a
ledger data-quality fix, not "extending the ledger forward" (D-02's rejected idea) — it edits an
existing row's free-text field to agree with that same row's structured field, for ids the ledger
already covers (series ≤158).

| Case | Prior doc annotation | Ledger outcome | Substitute checked | Verdict | Evidence |
|---|---|---|---|---|---|
| UAT-11-02 | `DEFERRED — no substitute coverage; needs a multi-run progressive-discovery integration test...` | GAP | None cited — annotation named no `covered by` node | **GAP** (ledger was right) | Annotation's own text already says "no substitute coverage"; token corrected DEFERRED→GAP, body unchanged |
| UAT-41-03 | `DEFERRED — no substitute coverage; needs a live docker-compose orphan-sweep integration test...` | GAP | None cited | **GAP** | Same pattern; body unchanged |
| UAT-5-19 | `DEFERRED — no substitute coverage; needs a pgcrypto column-level crypto detector...` | GAP | None cited | **GAP** | Same pattern; `grep -rn "pgp_sym_encrypt" quirk/` confirms no detector exists, matching the annotation's own claim |
| UAT-85-08 | `DEFERRED — no substitute coverage; needs a real browser screenshot capture...` | GAP | None cited | **GAP** | Same pattern; body unchanged |
| UAT-89-01-01 | `DEFERRED — no substitute coverage; needs a live docker-compose bring-up plus healthcheck...` | GAP | None cited | **GAP** | Same pattern; three-segment id confirmed real (D-06), not re-litigated |
| UAT-96-08 | `DEFERRED — no substitute coverage; needs a live docker-compose bring-up of the fuzz-target...` | GAP | None cited | **GAP** | Same pattern; body unchanged |
| UAT-67-04 | (unannotated: `frontend component test for ScannerStatusCard needed...`, no GAP/DEFERRED/OBSOLETE token) | GAP | N/A — cause 3, no citation ever present | **GAP** (D-05: explicit annotation established, not inherited silently) | `grep -rln "ScannerStatusCard"` under `src/dashboard/src/**/__tests__/` returns zero hits — no component test file exists at all, confirming the case's own claim |
| UAT-88-02 | (unannotated, generic HTML-render gap prose, no token) | GAP | N/A — cause 3 | **GAP**, rewritten to name the subscore set and isolation property for Phase 208 (per plan Task 1 instruction) | `grep -n "subscore" quirk/reports/templates/report.html.j2` shows the six-row table lives at **~lines 499-528** (`hygiene`, `modern_tls`, `identity_trust`, `agility_signals`, `data_at_rest`, `data_in_motion`), not the ledger's stale `409-420` citation (drift confirmed live, 2026-09-13) — isolation property: the rendered HTML output itself, uncovered by either `test_score_render_parity.py` (data-layer parity only) or `test_score_transparency.py` (markdown presence only) |
| UAT-88-03 | (unannotated, generic PDF-render gap prose, no token) | GAP | N/A — cause 3 | **GAP**, rewritten to reference UAT-88-02's now-named subscore set and state its own downstream isolation property | `grep -rln "playwright" tests/` was checked; no test exercises PDF generation of the decomposition table — isolation property: PDF-specific rendering fidelity, one layer downstream of UAT-88-02's HTML assertion |
| UAT-5-18 | `DEFERRED — no substitute coverage; needs a Vault Transit unit test for an rsa-1024 key type...` | GAP | None cited | **Retired, see Task 2** (D-11 COV-09 retirement — `rsa-1024` does not exist as a Vault Transit key type at all) | Left untouched in Task 1; resolved to `OBSOLETE` in Task 2 |
| UAT-47-04 | `DEFERRED — no substitute coverage; the interactive nmap y/N wizard prompt...no longer exists...` | GAP | None cited | **Retired, see Task 2** (D-11 — prompt superseded by `--discovery`) | Left untouched in Task 1; resolved to `OBSOLETE` in Task 2 |
| UAT-92-01 | (unannotated, one-time-historical-gate prose, no token) | GAP | N/A — cause 3 | **Retired, see Task 2** (D-11 — one-time v5.0.0 tag-creation event, not repeatable) | Left untouched in Task 1; resolved to `OBSOLETE` in Task 2 |

**Findings vs. CONTEXT.md's prediction:** none. The reconciler's live cause-2/cause-3 sets matched
wave 1's re-derivation exactly (8 and 4, with `UAT-89-01-01` in cause 2 per D-06's withdrawal) —
no case the reconciler flagged was unpredicted, and no predicted case went unflagged.

**Post-Task-1 live state** (9 of 12 cases resolved to `GAP`, 3 left for Task 2's `OBSOLETE`
retirement): `reconcile()` reports cause 2 = 2 (`UAT-47-04`, `UAT-5-18`) and cause 3 = 1
(`UAT-92-01`) — exactly the three COV-09 retirements, and nothing else. Arithmetic closes
(`arithmetic_ok: True`). `tests/test_uat_zero_undispositioned_gate.py`,
`tests/test_uat_series_format.py`, `tests/test_uat_corpus_parser.py`, and
`tests/test_uat_disposition_integrity.py` (except the documented pre-existing pytest 9.0.2 node)
all pass at this point.

## Retirements (COV-09)

See `204-02-SUMMARY.md` and `tests/test_uat_obsolete_grammar.py` for the three retirements
(`UAT-92-01`, `UAT-47-04`, `UAT-5-18`), their spot-checked reasons, and the OBSOLETE grammar that
keeps them out of the open-GAP count.
