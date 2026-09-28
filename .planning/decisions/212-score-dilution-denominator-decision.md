# Decision: P2b healthy-endpoint dilution — RECOMMEND NONE (DILUTE-01)

**Status: DECIDED 2026-09-28.** This is the Phase 212 deliverable. DILUTE-01 is satisfied by this
written decision, not by the harness that produced it.

**Verdict, stated up front: RECOMMEND NONE.** None of the three candidates the todo names cleared
both measurement axes on the evidence gathered this phase. The defect is **DEFERRED, NOT FIXED**.
`test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints` remains
`xfail(strict=True)` at this phase's close, **by design** — that is the correct outcome, not a
failure. No production code was shipped in this phase (confirmed in the provenance appendix and
`212-CRITERIA-EVIDENCE.md`).

---

## 1. The defect, in client terms first

**The evidence model cannot distinguish "there is more infrastructure" from "we looked harder,"
and the score rewards both identically.** Six plaintext endpoints is the same exposure whether
they sit among 38 services or 538 — the attacker needs one.
(`.planning/todos/pending/p2b-healthy-endpoints-dilute-the-readiness-score.md`)

**The masking point, which is what makes this worth continued attention rather than a shrug:** the
dilution surfaces at full size on any estate the consequence ceiling does not bind — every estate
with fewer than one open CRITICAL and some post-quantum coverage, i.e. exactly the healthier
clients. **The masking is strongest where the defect matters least, and absent where it matters
most.** A client whose infrastructure is genuinely improving (fewer CRITICALs, more PQC coverage)
is exactly the client for whom scanning deeper will still silently inflate the number, because
there is no ceiling left to mask it.

---

## 2. The control, and what it establishes

Transcribed verbatim from `212-CONTROL.md` (measured 2026-09-28, against `quirk/intelligence/scoring.py`
and `tests/test_score_properties.py` at commit `d3f14aa4`, two separate process runs, byte-identical):

| Instrument | Figure |
|---|---|
| Ladder scores (axis a), R1-R5 | `100, 78, 46, 24, 18` |
| Axis (a) verdict | 5/5 in band, monotonic, spread 82, saturation 15/30 |
| P2b computed sweep (axis b, pre-ceiling) | `71 -> 74 -> 78 -> 82` |
| P2b emitted sweep (axis b, post-ceiling) | `18 -> 18 -> 20 -> 20` |
| Axis (b) verdict | FAIL (rose) |

**AGREE, exactly, on all four numbers on both axes** with the documented 2026-09-14 xfail-reason
figures and the todo's own table — no reconciliation was needed. Phase 211's `legacy_tls_count`
endpoint-derivation (landed since those figures were first measured) did not move either sweep, as
expected: P2b's mutator adds only healthy TLS endpoints and never touches `legacy_tls_count`.

**This phase's control target is `[100, 78, 46, 24, 18]` / `71->74->78->82` / `18->18->20->20` —
the ladder and sweep as they stand on `main` today.** 999.115's historical ladder table
`[100, 95, 91, 85, 87]` is **HISTORICAL MOTIVATION ONLY** and was never used as a comparison
target: it predates six landed model changes (P8, PQC-gate-as-ceiling, the consequence ceiling C,
the non-linear ratio curve D, dropping `agility_high_impact_ratio`) plus Phase 211's DENOM-*
corrections. Judging a Phase 212 candidate against `[100, 95, 91, 85, 87]` would produce a
nonsensical regression verdict against a model that no longer exists.

---

## 3. The method, and its known blindness

**Two axes, and why one is not enough.** The calibration ladder's fixtures
(`_base_estate()`, `tests/test_score_properties.py:254-268`) pin `assessable_endpoint_count: 40`
for every rung R1-R4 by construction — *"Every rung shares ONE estate SHAPE: 40 assessable
endpoints, 40 observed certificates … Only the WEAKNESSES vary"*
(`tests/test_score_properties.py:240-245`). A denominator candidate rescales all four graded rungs
together; it cannot produce a differential signal on the ladder alone, because the ladder never
varies the population size. **The ladder measures calibration REGRESSION only.** Axis (b), the P2b
sweep on the PRE-ceiling computed score, is the only instrument that varies
`assessable_endpoint_count` while holding weaknesses fixed — the exact shape of the defect — and
is therefore **the only efficacy instrument**.

**ROADMAP Success Criterion 1 names only the ladder.** Read literally, this would have produced a
vacuous comparison in which all three candidates score identically on axis (a) alone — none of
them changes any rung's population, only what that fixed population means. **This phase satisfied
criterion 1 AND added axis (b), as a measurement-correctness fix rather than scope creep.** Without
axis (b), this phase could not have distinguished any candidate from any other, and criterion 2's
requirement for a measured comparison could not have been met at all.

**The two maskers finding.** `_computed_score()` bypasses only the outer `_consequence_ceiling()`;
the inner per-domain 25-point clamp still applies, and Phase 211-01 measured it saturating on this
very reference estate (+11.59 absorbed on the Agility domain,
`211-01-SUMMARY.md`). Per-domain subscores were logged (0 and 500 sweep points) specifically so a
flat reading could be told apart from an absorbed one. What the log showed, transcribed from
`212-CONTROL.md`'s "P2b sweep detail" table:

| Domain | extra=0 | extra=500 | Delta | Read |
|---|---|---|---|---|
| hygiene | 13 | 22 | +9 | genuinely diluting, room left before 25-clamp |
| modern_tls | 15 | 22 | +7 | genuinely diluting, room left before 25-clamp |
| identity_trust | 12 | 12 | 0 | flat because divides by `cert_denom`, which P2b's mutator does not touch — NOT clamp saturation |
| agility_signals | 16 | 17 | +1 | small but genuine |
| data_at_rest | 25 | 25 | 0 | pre-saturated at extra=0 — flat reading is AMBIGUOUS by construction, cannot be read as evidence either way |
| data_in_motion | 25 | 25 | 0 | pre-saturated at extra=0 — same ambiguity |

Without this per-domain log, the control's emitted headline movement (`18 -> 18 -> 20 -> 20`)
alone would read as "barely anything happened," when two domains are diluting by +9/+7 points
apiece, unmasked, underneath a ceiling this specific estate happens not to fully saturate.

---

## 4. The three candidate rows

**A note on comparability before the table: the three rows are verdict-comparable but NOT
cost-comparable.** Absolute exposure is a model-shape change (a new ceiling position, monkeypatched
into `_consequence_ceiling`), not a denominator swap (a fixture-level divisor redirect). Reading the
three rows as three equivalently-priced options distinguished only by their measured verdicts would
misstate the price of the third row — see its cost detail below the table.

| Candidate | Axis (a) — regression | Axis (b) — efficacy | Measured effect, reference case | Combined verdict |
|---|---|---|---|---|
| **Scan-scope normalisation** `[ASSUMED]` | 5/5 in band, monotonic — but a structural NO-OP vs CONTROL (every rung delta +0); does not independently discriminate | `[ASSUMED] / CONDITIONAL` — PASS (`71->71->71->71` flat) only under the "deeper look, same request" reading (requested scope held fixed); **FAILS, matching CONTROL exactly (`71->74->78->82`)**, under the todo's own literal wording ("scanning more ports on the same hosts") | Fixed-scope reading: flat. Growing-scope reading (the todo's own definition): identical to CONTROL, i.e. zero mitigation | **CONDITIONAL, not a clean PASS** |
| **Distinct hosts** `[ASSUMED]` | 5/5 in band, **NOT monotonic** (R4=13 < R5=17, an ordering VIOLATION traced to the `[UNCONSTRAINED]` R1-R4 single-host assumption) | `[ASSUMED] / TAUTOLOGICAL` — host_count is asserted at a constant (31), never derived from any per-row `.host` field (none exists); no input to the sweep can make this row fail | Flat `68->68->68->68`, but the row carries zero evidentiary weight — a result no input could falsify | **TAUTOLOGICAL — not a PASS. Not recommendable on this evidence.** |
| **Absolute exposure** (model-shape, not a denominator swap) | 5/5 in band, monotonic (R4 moves 24->18, a genuine, non-trivial effect the ladder CAN see because this candidate is not a denominator change) | `STRUCTURALLY UNINFORMATIVE` — the candidate patches `_consequence_ceiling()`, which runs AFTER all six domain scores are computed AND summed; axis (b) reads the PRE-ceiling value, strictly upstream of where this candidate lives. It can never move that instrument by construction — not "no effect," but "never positioned to reach the instrument at all" | Identical to CONTROL cell-for-cell on both axis (b) sweeps (`71->74->78->82` / `18->18->20->20`); isolation reading (severity zeroed) shows R3 rising outside its FAIR band, 4/5 hit rate | **Neither a PASS nor a FAIL on axis (b) — a THIRD outcome: structurally unmeasured by this method** |

**Every `[ASSUMED]` label above is carried forward from the measurement files, not softened.** See
Section 8 (Label-Survival Audit) below for the mechanical check that confirmed this.

### Why absolute exposure is a distinct third outcome, not a failure

Axis (b)'s instrument (`_computed_score()`, reading `total_score` strictly before any ceiling
touches it — `scoring.py:727`, assigned before `:684-695`) is **structurally blind to any
ceiling-shaped candidate by construction**, independent of whether that candidate has a real
effect. This is not the candidate failing to close the defect; it is the METHOD lacking the
instrument to see whether it did. A second, independent masking reason compounds this on the
specific P2b fixture: `_multihost_evidence()` fixes `CRITICAL=5` (already at C's own severe-tier
threshold), `plaintext_http_count=6`, and `expired_count=5` (already at this candidate's own two
severe-tier thresholds) at every sweep point — three independent ceiling sources are already tied
at the same value before the sweep starts, so even a hypothetical instrument reading past the
ceiling would find no movement on THIS specific fixture. An isolation reading (zeroing CRITICAL/HIGH
to remove C's own ceiling from the competition) shows this candidate DOES have an independent
effect — R3 moves from 46 to 59, outside its FAIR band — confirming the candidate is not inert, only
that the P2b sweep as built cannot see it.

**THE METHOD FINDING, first-class:** CONTEXT D-01's two-axis design is adequate for
DIVISOR-SWAP candidates (both axes measure quantities those candidates can move) but
**structurally inadequate for CEILING-SHAPED candidates** (axis (b) is defined to read the
PRE-ceiling value specifically so `_consequence_ceiling()` cannot mask the defect from its own
test — the same property that makes it blind to any OTHER ceiling-shaped term, including a
candidate fix). A third instrument — reading the EMITTED score under a fixture where the existing
consequence ceiling is deliberately not binding, or instrumenting the ceiling-selection call site
directly rather than reading `total_score` — is needed to evaluate ceiling-shaped candidates like
absolute exposure on their own merits. This is a first-class result of this spike, not a footnote:
it means the todo's three named candidates were never evaluable by one harness design, and any
future implementation phase must build (or reuse) a different instrument for this specific
candidate shape before ruling it in or out.

### Cost detail — absolute exposure is not a peer of the other two rows

- **Injection mechanism:** required a monkeypatched wrapper around `_consequence_ceiling`, a
  teardown proof, and an isolation-reading harness (~230 lines). The two denominator candidates
  needed only fixture-dict edits handed to `evidence_mutator=` (no monkeypatching, no teardown
  proof).
- **Free parameters:** 2 new (`DEEP_PLAINTEXT_COUNT`, `DEEP_EXPIRED_COUNT`), against the existing
  ceiling machinery's 1 (`DEEP_CRITICAL_CEILING`) — 3 total in the combined ceiling-selection list,
  against the "four to one" collapse the todo cites as the standard the existing ceiling work set.
  Both new thresholds were sourced from R5 alone (the same rung that already sources
  `DEEP_CRITICAL_COUNT`), concentrating three of five ladder observations' worth of fitting
  pressure onto a single rung.
- **Blast radius if shipped:** does NOT touch `endpoint_denom`/`domain_denom`/`cert_denom` or any
  `_ratio()` call site at all — a single function's call site (`_consequence_ceiling`'s ~12-line
  call at `scoring.py:684-695`), two new constants, a disclosure-string update, and golden-fixture
  regeneration. This is categorically smaller than either denominator candidate's blast radius (see
  Section 6), independent of the candidate's measured verdict.

### The 999.115-C correction folded into this candidate's own framing

The plan's characterization of 999.115 candidate C as applying "per weakness family rather than to
the aggregate" was corrected during measurement (recorded here so the correction is not silently
absorbed): C applies to the AGGREGATE `total_score`, after all six domains sum — that position is
the load-bearing, clamp-surviving part of C's own shape (P7b: an additive term placed inside a
per-domain impacts list is absorbed whole by the domain's own 0-25 clamp, exactly as the +8.0 PQC
bonus was measured being absorbed). What "per weakness family" correctly distinguishes is C's
INPUT basis (one combined CRITICAL+HIGH pair) versus this candidate's two separate per-family
inputs (plaintext count, expired-certificate count) — both still land on the aggregate, same
position as C, for the same clamp-survival reason.

---

## 5. The recommendation

**RECOMMEND NONE.** No denominator was chosen because a number read well: verdicts were recorded
against the non-increasing predicate fixed before measurement (999.113 D5, "never tune to a
target"). On the evidence gathered this phase:

- Scan-scope normalisation's only passing axis-(b) reading depends on a scope reading ("deeper
  look, same request") that is NOT the todo's own literal wording ("scanning more ports"). Under
  the todo's own wording, it provides zero mitigation.
- Distinct hosts' axis-(b) reading is tautological — a result no input could falsify carries zero
  evidentiary weight, regardless of how clean the number looks.
- Absolute exposure was never measurable on axis (b) by this method, by construction. Its axis (a)
  behavior is genuine (R4 moves), but D-01 requires BOTH axes, and this candidate's axis (b) is
  neither a demonstrated PASS nor a demonstrated FAIL — it is unmeasured.

**What a fourth candidate — or a third measurement axis — would have to do:**

1. **For a denominator-swap candidate (distinct hosts or a variant):** the fixture family needs
   real per-row `(host, port)` data so `host_count` (or an equivalent stable population) can be
   DERIVED rather than asserted at a fixed constant. Until `quirk/intelligence/evidence.py` carries
   host identity as a first-class field, any host-based candidate's axis-(b) reading will remain
   tautological by the same mechanism found here.
2. **For scan-scope normalisation specifically:** the candidate needs to be measured under the
   "scanning more ports" reading as its PRIMARY reading, not as a follow-up discriminator — and on
   that reading it already failed. It would need a different mechanism entirely (not "hold
   requested scope fixed") to survive that reading.
3. **For a ceiling-shaped candidate (absolute exposure or a variant):** a third instrument is
   required — one that reads either the emitted score under a fixture engineered so the EXISTING
   consequence ceiling is provably not binding (so any movement can be attributed to the new
   ceiling alone), or instruments the ceiling-selection call site directly (e.g. logging which
   candidate ceiling won at each sweep point, not just the final `total_score`). Without that
   instrument, no future measurement pass can honestly rule this candidate shape in or out on axis
   (b).

Equally: **no candidate whose only passing axis was a row no input could falsify is recommended
here** — the tautological distinct-hosts axis-(b) row is explicitly NOT stretched into a
recommendation despite its clean-looking flat sweep.

Because RECOMMEND NONE is the verdict, the plan's conditional instruction ("if distinct-hosts is
recommended, name the host-counter work...") does not apply as a live recommendation — but the
cost is recorded anyway in Section 4's table and Section 6, since it remains relevant to any future
attempt at this candidate shape: `quirk/intelligence/evidence.py` carries no first-class host
counter today (`grep -nE "\bhost_count\b|distinct_host|\bhosts\b" quirk/intelligence/evidence.py`
returns nothing but an unrelated comment at `:192`), and a future implementation phase choosing
this candidate shape would need to add one before axis (b) could be measured against real variance
rather than an asserted constant.

---

## 6. Blast radius

**Three prior figures were in circulation for "how many consumers does a denominator change
touch," and they disagree — not by error, but because they answer different questions:**

| Source | Figure | Counting basis |
|---|---|---|
| Todo (`p2b-healthy-endpoints-dilute-the-readiness-score.md`) | "~20" | Estimate, superseded — predates both anchored re-measurements below |
| `212-RESEARCH.md` / re-derived here (basis 1) | **32** | `_ratio(numerator, endpoint_denom\|domain_denom)` call sites — the number relevant to judging a denominator candidate's blast radius on ratio BEHAVIOR |
| Orchestrator's binding constraints / re-derived here (basis 2) | **44** | ALL textual references to `domain_denom` (27) + `endpoint_denom` (11) + `cert_denom` (6) — includes the three symbols' own definition/assignment lines and comment references; broader and noisier than basis 1 |

Both 32 and 44 were re-derived live, twice each, by two independent instruments per basis (a shell
`grep -c` and a Python `re.findall`, both against a fresh read of `quirk/intelligence/scoring.py`
at commit `d3f14aa4`), and both instruments agreed with each other and with the prior figures each
time (`212-CONTROL.md`, "Blast radius" section). **Neither figure is adopted as "the" answer — they
are two correct answers to two different questions**, and this phase does not present a single
number as though the question had one answer. The todo's "~20" is simply superseded: it undercounts
basis 1 by 12 and predates both anchored measurements.

**The `_endpoints_assessed()` hazard, verified live, not assumed:** `scoring.py:630-631` assigns
`assessable_endpoints = endpoint_denom` and derives `endpoints_assessed = _endpoints_assessed(assessable_endpoints)`,
where `_endpoints_assessed()` (`scoring.py:344-350`) returns `endpoints > 0`. This is a **boolean
gate**, not a ratio call site, so it is counted in NEITHER of the two bases above — it is a third,
categorically different kind of consumer. A divisor-swap candidate that can reach 0 (e.g. an estate
with genuinely zero resolved hosts, for a host-count-based denominator) would silently mark
Hygiene, Modern TLS, and Agility as UNASSESSED as a side effect — not merely rescale their ratios,
but remove them from `domains_assessed`/`domains_total`, which feeds the headline rescale. None of
the three measured candidates in this phase tripped this hazard on the ladder's own fixtures (every
value written by every candidate stayed > 0), but it is a near miss for distinct hosts specifically
— its lowest written value (1, under the R1-R4 single-host convention) is still comfortably above
0, but a real implementation reaching a genuinely-zero host count would trip it. Any future
implementation phase must check this hazard per-rung and per-sweep-point, not assume it is safe
because the ratio math alone looks unchanged.

---

## 7. The 211 quarantine

Phase 211 (`211-LIVE-MEASUREMENT.md:262-306`) measured a live chaos-lab estate at two port-scan
widths and found the headline score **INVERTED** against history: wide (14-port) scored 18/100,
narrow (2-port) scored 20/100, against a historical pair where widening used to RAISE the score
(89 -> 91, `999.113-denominator-semantics.md:86`).

**This is a DIFFERENT experiment from anything measured in this document, and is not used to judge
either candidate above (D-09).** Phase 211 varied the number of ports scanned, which changes BOTH
the endpoint population AND the weakness count found (a wider scan discovers more plaintext
endpoints, more expired certificates, more findings on the newly-scanned ports). This phase's P2b
sweep holds every weakness count identical across all four sweep points and adds only HEALTHY
assessable endpoints — that is the entire point of the defect this phase measures. Conflating the
two would be a false discriminator: Phase 211's INVERTED result says nothing about whether a
denominator candidate resists PURE dilution, because Phase 211's own scans never held weaknesses
fixed while varying scope.

**Worth naming, without treating it as a discriminator substitute:** Phase 211's port-count sweep
IS an instance of the "scanning more ports" reading this phase's own scan-scope discriminator
measurement exercises — independent, real-infrastructure corroboration that the "scanning more
ports" scenario is not one where a naive scan-scope-style normalisation should be expected to hold
the score flat (both measurements show the wider-scan scenario MOVING the score, not flattening
it). The two measurements' magnitudes are still not compared against each other (D-09 stands) — the
qualitative agreement is recorded as corroborating context only.

---

## 8. Deferral, owner phase, and the label-survival audit

**Stated plainly: the defect is DEFERRED, NOT FIXED.** No production code implementing any
candidate shipped in this phase (`git status --porcelain -- quirk/ tests/` empty, `git diff --stat
main -- quirk/` empty — `212-CRITERIA-EVIDENCE.md`, Section 2).
`test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints` remains
`xfail(strict=True)` at this phase's close, and that is the correct, designed outcome — see
`212-CRITERIA-EVIDENCE.md`, Section 1, for the verbatim `24 passed, 3 xfailed` and the confirmation
that both the emitted-score and the pre-ceiling assertion lines are present and unchanged.

**Owner phase for implementation: a post-v5.25 phase in the next milestone.
OPERATOR-RESERVED — the operator confirms this at milestone close.** This is explicitly NOT Phase
214 (the Release Cut) — re-scoring every ladder rung inside a release phase would freeze an
unmeasured number into a tag. This document surfaces the recommendation but does not lock it: it
touches milestone structure and the version cut, which is not this document's call to make (D-06).

**What the implementation phase must budget:** re-measuring ALL FIVE ladder rungs, because every
rung's ratios divide by one of the two denominators — a denominator change rescales every rung
together (Section 3). It must also budget building the third measurement instrument named in
Section 4 (the method finding) if it intends to evaluate a ceiling-shaped candidate, and building
real per-row host-identity fixture data if it intends to re-attempt distinct hosts.

### Label-survival audit

**Method:** grep the two candidate measurement files for `[ASSUMED]`, `TAUTOLOG`, `UNMEASURABLE`,
`CONDITIONAL`, and `UNCONSTRAINED`, and confirm each recommendation-relevant occurrence has a
downstream counterpart in this document.

```
grep -noE "\[ASSUMED\]|TAUTOLOG[A-Z]*|UNMEASURABLE[-A-Z]*|CONDITIONAL|\[UNCONSTRAINED\]" \
  .planning/phases/212-score-dilution-decision-only/212-MEASUREMENTS-denominator.md \
  .planning/phases/212-score-dilution-decision-only/212-MEASUREMENTS-absolute-exposure.md
```

Result (labels found, source file, and their carry-forward status in this document):

| Label | Source file | Row | Carried into this document? |
|---|---|---|---|
| `[ASSUMED]` (candidate header) | MEASUREMENTS-denominator.md | Scan-scope normalisation | YES — Section 4 table header cell |
| `[ASSUMED]` (P2B_REQUESTED_SCOPE=38) | MEASUREMENTS-denominator.md | Scan-scope normalisation | YES — Section 4, "CONDITIONAL" cell text references the fixed-scope assumption |
| `CONDITIONAL` (combined verdict) | MEASUREMENTS-denominator.md | Scan-scope normalisation | YES — Section 4 table cell verbatim `[ASSUMED] / CONDITIONAL` |
| `[ASSUMED]` (candidate header) | MEASUREMENTS-denominator.md | Distinct hosts | YES — Section 4 table header cell |
| `[ASSUMED]` (P2B_HOST_COUNT=31) | MEASUREMENTS-denominator.md | Distinct hosts | YES — Section 4, axis (b) cell references the asserted constant |
| `[UNCONSTRAINED]` (R1-R4=1 host) | MEASUREMENTS-denominator.md | Distinct hosts | YES — Section 4 table, axis (a) cell names the ordering violation traced to this assumption |
| `TAUTOLOGICAL` (combined verdict) | MEASUREMENTS-denominator.md | Distinct hosts | YES — Section 4 table cell verbatim `[ASSUMED] / TAUTOLOGICAL`, and Section 5's recommendation text |
| `UNMEASURABLE-AS-POSED` (axis-b verdict) | MEASUREMENTS-denominator.md | Distinct hosts | YES — Section 4's "Why... is a distinct third outcome" prose paraphrases this for absolute exposure but for DISTINCT HOSTS specifically the exact phrase is captured here in this audit row rather than restated a second time in Section 4's cell (the cell uses `TAUTOLOGICAL`, the label the combined verdict itself uses) |
| `STRUCTURALLY UNINFORMATIVE` | MEASUREMENTS-absolute-exposure.md | Absolute exposure | YES — Section 4 table cell verbatim |

**Audit result: every recommendation-relevant label found upstream has a downstream counterpart in
Section 4's table or Section 5's recommendation text.** One label required a judgment call, recorded
honestly rather than silently: `UNMEASURABLE-AS-POSED` (distinct hosts' own axis-(b) verdict text)
is not repeated as a separate table cell alongside `TAUTOLOGICAL` — both labels describe the same
underlying finding (a row no input could falsify) in the same source document, and Section 4's cell
uses `TAUTOLOGICAL` because that is the label the source document's own "Combined verdict" section
uses as the one carried into its comparison table. This audit row exists specifically so that
choice is visible rather than silent.

---

## 9. What would falsify this recommendation

- **Scan-scope normalisation:** a demonstration that real scan-depth increases do NOT widen
  requested scope in lockstep with returned rows — i.e., that the "deeper look, same request"
  reading is the operationally common case, not scan-scope's convenient case. Phase 211's own
  live chaos-lab measurement (Section 7) argues the opposite (wider scans move the score), which is
  why this candidate is not recommended, but a different real-world scanning pattern could reopen
  it.
- **Distinct hosts:** real per-row host-identity data (`quirk/intelligence/evidence.py` carrying a
  `.host` field so `host_count` could be DERIVED instead of asserted) would let axis (b) be
  re-measured honestly. If that measurement then showed a non-increasing computed score under
  genuine host-count variance, this candidate would become recommendable. Nothing in this phase's
  evidence rules that out — it rules out only the tautological measurement attempted here.
- **Absolute exposure:** a third measurement instrument (Section 4, the method finding) that can
  read past `_consequence_ceiling()` or instrument its call site directly would let axis (b) be
  measured for real. Axis (a) already shows this candidate has a genuine, non-trivial effect (R4
  moves); if the new instrument showed non-increasing behavior on axis (b) too, this candidate
  would become the strongest of the three on the evidence gathered so far.
- **This document's own scope:** if a fourth candidate were proposed that is neither a
  denominator-swap nor a ceiling-shaped term, it would need its own measurement design before this
  document's verdict could be extended to it either way — nothing here rules a fourth shape in or
  out.

If the answer to "what would falsify this" were "nothing," RECOMMEND NONE would be an argument, not
a measurement. It is not: each candidate names a concrete, specific input that would change its
verdict.

---

## Provenance appendix (figure-by-figure transcription audit)

Every number-bearing claim in this document, its source file, and the source section/line it was
transcribed from. Built by opening each source file and confirming the number matches — not
softened into prose for any figure without a source.

| Figure | Source file | Source section/line |
|---|---|---|
| Ladder `100, 78, 46, 24, 18` (CONTROL) | `212-CONTROL.md` | "Run 1" / "Run 2" tables; "Ladder detail (axis a)" table |
| P2b computed `71 -> 74 -> 78 -> 82` (CONTROL) | `212-CONTROL.md` | "Run 1" / "Run 2" tables; "P2b sweep detail (axis b)" table |
| P2b emitted `18 -> 18 -> 20 -> 20` (CONTROL) | `212-CONTROL.md` | "Run 1" / "Run 2" tables |
| CONTROL axis (a) 5/5 in band, monotonic, spread 82, saturation 15/30 | `212-CONTROL.md` | "Run 1" / "Run 2" tables |
| Per-domain deltas (hygiene +9, modern_tls +7, identity_trust 0, agility_signals +1, DAR 0, DIM 0) | `212-CONTROL.md` | "P2b sweep detail (axis b)" table + "Two-masker disambiguation" prose |
| Phase 211 Agility clamp +11.59 absorbed | `211-01-SUMMARY.md` | (cited also in `212-CONTEXT.md` canonical_refs, "Phase 211's carried-forward evidence") |
| Scan-scope: axis (a) 5/5 in band, monotonic, every delta +0 | `212-MEASUREMENTS-denominator.md` | "Candidate 1 — scan-scope normalisation", "Axis (a)" table |
| Scan-scope: fixed-scope computed `71->71->71->71` | `212-MEASUREMENTS-denominator.md` | "Candidate 1", "Axis (b)" section |
| Scan-scope: growing-scope computed `71->74->78->82` (== CONTROL) | `212-MEASUREMENTS-denominator.md` | "Falsifiability audit — scan-scope axis (b)" section |
| Scan-scope: `[ASSUMED] / CONDITIONAL` combined verdict | `212-MEASUREMENTS-denominator.md` | "Combined verdict — scan-scope normalisation" |
| Distinct hosts: axis (a) `100, 78, 36, 13, 17`, NOT monotonic, spread 87, saturation 17/30 | `212-MEASUREMENTS-denominator.md` | "Candidate 2 — distinct hosts", "Axis (a)" table |
| Distinct hosts: axis (b) computed `68->68->68->68` | `212-MEASUREMENTS-denominator.md` | "Candidate 2", "Axis (b)" section |
| Distinct hosts: `[ASSUMED] / TAUTOLOGICAL` combined verdict | `212-MEASUREMENTS-denominator.md` | "Combined verdict — distinct hosts" |
| Blast radius basis 1 = 32, basis 2 = 44 | `212-CONTROL.md` | "Blast radius — re-derived at run time" section |
| `_endpoints_assessed()` hazard, `scoring.py:630-631`, `:344-350` | `212-CONTROL.md` | "The 33rd/45th-consumer hazard" section |
| Absolute exposure: axis (a) `100, 78, 46, 18, 18`, monotonic, spread 82, saturation 15/30 | `212-MEASUREMENTS-absolute-exposure.md` | "Axis (a) — REGRESSION" table |
| Absolute exposure: axis (b) identical to CONTROL, both sweeps | `212-MEASUREMENTS-absolute-exposure.md` | "Axis (b) — EFFICACY" section |
| Absolute exposure: isolation reading `100, 78, 59, 18, 18`, R3 out of band, 4/5 hit rate | `212-MEASUREMENTS-absolute-exposure.md` | "ISOLATION reading (supplementary...)" section |
| Absolute exposure: 2 new free params (`DEEP_PLAINTEXT_COUNT`, `DEEP_EXPIRED_COUNT`), 3 total vs "four to one" | `212-MEASUREMENTS-absolute-exposure.md` | "Task 1 — free-parameter cost" section |
| Absolute exposure: blast radius = single call site (`scoring.py:684-695`), not 32/44 | `212-MEASUREMENTS-absolute-exposure.md` | "Task 3 — cost profile" section |
| Phase 211 INVERTED: wide 18/100, narrow 20/100, historical 89/91 | `211-LIVE-MEASUREMENT.md:262-306`; `999.113-denominator-semantics.md:86` | cited verbatim in `212-MEASUREMENTS-denominator.md`, "QUARANTINE" section |
| `24 passed, 3 xfailed` (final re-run) | `212-CRITERIA-EVIDENCE.md` | Section 1a |
| `git status --porcelain -- quirk/ tests/` empty | `212-CRITERIA-EVIDENCE.md` | Section 2 |

**Final criterion re-check, run again after all writing was done:**

```
git status --porcelain -- quirk/ tests/
```
Result: empty (0 lines).

```
.venv/bin/python -m pytest tests/test_score_properties.py -q
```
Result (tail): `24 passed, 3 xfailed, 2 warnings in 0.21s`

Both confirm the state recorded in `212-CRITERIA-EVIDENCE.md` still holds after this document was
written — no figure or claim in this document caused, or required, any change under `quirk/` or
`tests/`.

### Scope audit

Confirmed: this document does not recommend, describe, or schedule any implementation work as part
of THIS phase. Every mention of implementation work (host-counter addition, third measurement
instrument, ladder re-measurement) is explicitly assigned to the OPERATOR-RESERVED future owner
phase in Section 8, not to this phase. The emitted-score movement figures (`18 -> 18 -> 20 -> 20`
for CONTROL; identical for absolute exposure) are stated alongside the computed-score figures every
time they appear, specifically so a skimming reader cannot mistake the small emitted movement for a
fix — Section 1 states the masking point explicitly, and Section 5's recommendation opens with
"RECOMMEND NONE" before any candidate detail, so the verdict cannot be missed by a reader who stops
partway through.
