# Decision: P2b third-instrument measurement — NONE OF 212's CANDIDATES IS SUPPORTED; THE DATA POINT TO A NEW TWO-PART SHAPE, EFFORT L (SCORE-08)

**Status: RECORDED 2026-10-27.** This is the Phase 233 deliverable for SCORE-08. Measurement only.
No scoring or evidence code changed in this phase (§12).

## 1. Status and verdict

**Verdict: none of Phase 212's three candidates (distinct hosts, absolute exposure, scan-scope
normalisation) is supported, and no ceiling-shaped candidate can be.** The measured dilution has
three separable components, not one. The first is the endpoint denominator E
(`assessable_endpoint_count`, 32 of the 35 ratio terms). The second is the certificate denominator
C (`certs_observed`, 3 terms). The third is the agility **key-type branch**, which awards a step of
up to 12 raw points the moment one ECDSA certificate is observed. All three of 212's candidates act
on E at most. On the primary reading (rows_ecdsa), C and the key-type branch together account for
9 of R5's +12 computed points at +20. On R2 they account for all of its +6, because the endpoint
component on R2 is 0. **The data point to a new two-part shape:** (a) a denominator-free,
absolute-count penalty at the ratio sites, covering both E and C, and (b) a key-type rule that
does not reward a single healthy observation. That is a hypothesis the tables point to. It is not
a measured result, because no implementation of it was run. **Effort: L.**

**Gate for Phase 234 (D-20).** Phase 234 gates on re-running `python -m scripts.p2b_instrument`
across all five rungs (R1-R5) and every reading (rows_ecdsa primary, rows_rsa, rows_certless, and
the mutator_212 continuity reading), and diffing the result against §4-§5 of this record. The xfail
test alone is not the gate: it uses the 212 mutator, which moves only E. A denominator-only fix
could turn it green while rows_rsa and rows_ecdsa still rise.
`test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints` is still `xfail(strict=True)`
and still registered (§12).

---

## 2. Measured at

| Item | Value |
|---|---|
| HEAD sha | `2571917018452c10d595d35700b830a7678d0438` (`provenance.head_sha`) |
| `quirk/intelligence/scoring.py` blob | `25f0f7912202dd5192a5634ac3b2f04578608912` (`provenance.scoring_blob`) |
| `quirk/intelligence/evidence.py` blob | `73c48a36bb9e057d1e3f61732568d816ac3440ee` (`provenance.evidence_blob`) |
| Python | 3.14.10 (`provenance.python`) |
| Date | 2026-10-27, run at 16:42 UTC |
| Commands | `.venv/bin/python -m scripts.p2b_instrument --json` and `--markdown` (ladder + sweep); `.venv/bin/python -m scripts.p2b_instrument --real-db quirk-output/quirk.db --real-json quirk-output/intelligence-20260914-142606.json --json` and `--markdown` (real estate, §9) |
| Raw outputs (untracked) | `.planning/phases/233-p2b-measurement-instrument/233-measurement.{json,md}`, `233-real-estate.{json,md}` |

Both blob hashes equal the blobs at the phase base `e0064b02`.
`git diff e0064b02..HEAD -- quirk/intelligence/scoring.py quirk/intelligence/evidence.py | wc -l`
printed `0`. **The model measured here is the phase-base model.** The sweep `results` array in
`233-real-estate.json` is identical to the one in `233-measurement.json`: two separate process runs
produced the same 80 points.

---

## 3. Method and independence

**Row-layer entry (D-01).** For each rung, `scripts/p2b_instrument.py` builds synthetic endpoint
rows plus finding dicts and assembles them through `build_evidence_summary(..., reference_utc=REF)`.
It then appends N healthy rows and scores with `compute_readiness_score`. Both of Phase 212's
instruments entered at the **evidence-dict** layer: (a) the calibration ladder dicts read for
regression, and (b) the three-field dict mutator read through `_computed_score()`. Neither one could
see anything that happens while rows are assembled into evidence. This instrument enters one layer
earlier, where the 228-230 evidence changes live.

**Three values per point (D-02).** At every point the instrument records:

- the emitted score;
- the computed (pre-ceiling) score;
- the winning ceiling's source and value (`consequence`, `pqc_readiness` or `none`);
- the losing ceilings.

It also checks the ceiling identity `emitted == round(c x computed / 100)`. That identity held at
all 80 points (`results[*].ceiling_identity_holds`). This meets the third-instrument specification
Phase 212 set out (212 record `:135-146`, `:206-212`):

> "A third instrument — reading the EMITTED score under a fixture where the existing consequence
> ceiling is deliberately not binding, or instrumenting the ceiling-selection call site directly
> rather than reading `total_score` — is needed to evaluate ceiling-shaped candidates"

> "...or instruments the ceiling-selection call site directly (e.g. logging which candidate ceiling
> won at each sweep point, not just the final `total_score`)."

It meets the **second** branch: it identifies the winning and losing ceilings at every point. It
does not meet the first branch, because no fixture was engineered to unbind the consequence
ceiling. The ladder fixtures were not edited (D-07). §10 shows the second branch is enough to rule
on ceiling-shaped candidates.

**Closed form (D-03).** `scripts/p2b_closed_form.py` re-derives the score from the same evidence
dict without importing `quirk`. Its independence is enforced by
`tests/test_p2b_instrument.py::test_closed_form_is_independent`, in four parts:

1. **Stdlib-only import allowlist:** `__future__`, `math`, `typing`, `collections`, `dataclasses`.
2. **Banned names:** `exec`, `eval`, `compile`, `open`, `__import__`, `importlib`,
   `__builtins__`, `getattr`, `globals`, `vars`, `__loader__`, `__spec__`.
3. **No `quirk` or `scoring` strings:** no string constant outside a docstring may name either.
4. **A fresh subprocess** imports only the closed form, scores R3 from JSON on stdin, and asserts
   that no `quirk*` module appears in `sys.modules`.

Term probes cover both bases. R3 has E = C = 40, and R5 has E = 38 and C = 17, so E != C there.
Each probe perturbs one numerator per ratio term. Further branch probes cover terms the ladder
leaves at zero. 233-02 ran 395 probes and 0 disagreed.

**Where the closed form's spec came from.** It came from RESEARCH Q4, which was read from
`quirk/intelligence/scoring.py` at `e0064b02`, and from the research prototype ported into
`scripts/p2b_closed_form.py`. **Its independence is of mechanism (it shares no code at run time),
not of origin.**

- **What agreement shows:** the instrument reads the scorer correctly (computed score, ceiling
  source and value). It also shows that D-12's arithmetic model (ratio curve, per-domain clamp,
  rescale, linear squeeze) matches the code.
- **What agreement cannot show:** whether the code departs from its intent. The spec was derived
  from the code, so a defect in intent would be copied into the spec (memory
  `feedback_measure_with_a_method_independent_of_the_audited_code`).

**Points (D-04):** +0, +20, +100 and +500 healthy endpoints on all five rungs. These are comparable
with 212's `71 -> 74 -> 78 -> 82`.

**Healthy row (D-05).** Each added endpoint is a row on TLS port 443 with:

- TLS 1.3 and an AEAD cipher;
- a distinct host (`healthy-<i>.p2b.example`);
- a certificate valid for 400 more days;
- for the primary reading, a certificate key of ECDSA P-256 with sha256 (`tls_scanner`'s own
  labels).

No weakness rows are added. `test_healthy_rows_are_healthy` asserts that the healthy rows produce
no CRITICAL or HIGH finding. They do produce **one MEDIUM finding per certificate-bearing row**
("TLS certificate uses quantum-vulnerable ECDSA key", or the RSA equivalent; §6).

**Readings (D-06, D-18):**

| Reading | Role | What one added endpoint carries |
|---|---|---|
| `rows_ecdsa` | **primary** (D-05) | E +1, C +1, ECDSA key +1 |
| `rows_rsa` | sub-reading | E +1, C +1, RSA key +1 |
| `rows_certless` | sub-reading | E +1 only |
| `mutator_212` | **continuity** (D-06), not the independent measurement | 212's three-field dict edit: `assessable_endpoint_count`, `totals.endpoints`, `protocol_counts.TLS` +1 each |

**Correction to CONTEXT D-09's wording.** Phase 212's own harness was not lost. It survives,
untracked, at `.planning/milestones/v5.25-phases/212-score-dilution-decision-only/scratch/harness.py`
(present on disk at this writing, next to `candidates_denominator.py` and
`candidate_absolute_exposure.py`). The harness 212's D-04 called lost was 999.115's.

---

## 4. Pre-change ladder at +0 (D-07)

Measured at the sha in §2 (`ladder_at_zero.<R>`). Subscores are listed in the order hygiene /
modern_tls / identity_trust / agility_signals / data_at_rest / data_in_motion.

| Rung | Emitted | Computed | Winning ceiling | Losing ceilings | Subscores |
|---|---|---|---|---|---|
| R1 | 100 | 100 | none | none | 25 / 25 / 25 / 25 / 25 / 25 |
| R2 | 78 | 93 | pqc_readiness 84 | none | 25 / 25 / 23 / 17 / 25 / 25 |
| R3 | 46 | 85 | consequence 54 | pqc_readiness 84 | 22 / 23 / 16 / 17 / 25 / 25 |
| R4 | 24 | 72 | consequence 34 | pqc_readiness 84 | 15 / 18 / 11 / 16 / 23 / 25 |
| R5 | 18 | 71 | consequence 25 | pqc_readiness 84 | 13 / 15 / 12 / 16 / 25 / 25 |

The measured values equal the RESEARCH hypothesis (emitted 100/78/46/24/18, computed
100/93/85/72/71) and Phase 212's control ladder `100, 78, 46, 24, 18`. The row rebuild reproduces
each rung's emitted score, computed score and subscores at +0
(`test_rows_reproduce_dict_ladder_at_zero`). **The ladder fixtures in
`tests/test_score_properties.py` and `tests/test_score_denominator_999_113.py` were not edited, and
no R6 was added.**

---

## 5. Sweep tables

Each cell is `emitted/computed [winning ceiling source value]`, transcribed from `results[]`
filtered by `reading`, `rung` and `extra`.

### rows_ecdsa (primary)

| Rung | +0 | +20 | +100 | +500 |
|---|---|---|---|---|
| R1 | 100/100 [none] | 100/100 [none] | 100/100 [none] | 100/100 [none] |
| R2 | 78/93 [pqc_readiness 84] | 83/99 [pqc_readiness 84] | 83/99 [pqc_readiness 84] | 84/100 [pqc_readiness 84] |
| R3 | 46/85 [consequence 54] | 50/93 [consequence 54] | 51/95 [consequence 54] | 52/97 [consequence 54] |
| R4 | 24/72 [consequence 34] | 28/82 [consequence 34] | 30/89 [consequence 34] | 32/93 [consequence 34] |
| R5 | 18/71 [consequence 25] | 21/83 [consequence 25] | 22/89 [consequence 25] | 24/95 [consequence 25] |

### rows_rsa (sub-reading)

| Rung | +0 | +20 | +100 | +500 |
|---|---|---|---|---|
| R1 | 100/100 [none] | 100/100 [none] | 100/100 [none] | 100/100 [none] |
| R2 | 78/93 [pqc_readiness 84] | 79/94 [pqc_readiness 84] | 79/94 [pqc_readiness 84] | 80/95 [pqc_readiness 84] |
| R3 | 46/85 [consequence 54] | 47/87 [consequence 54] | 48/89 [consequence 54] | 50/92 [consequence 54] |
| R4 | 24/72 [consequence 34] | 26/76 [consequence 34] | 28/83 [consequence 34] | 30/88 [consequence 34] |
| R5 | 18/71 [consequence 25] | 19/77 [consequence 25] | 21/83 [consequence 25] | 22/89 [consequence 25] |

### rows_certless (sub-reading)

| Rung | +0 | +20 | +100 | +500 |
|---|---|---|---|---|
| R1 | 100/100 [none] | 100/100 [none] | 100/100 [none] | 100/100 [none] |
| R2 | 78/93 [pqc_readiness 84] | 78/93 [pqc_readiness 84] | 78/93 [pqc_readiness 84] | 78/93 [pqc_readiness 84] |
| R3 | 46/85 [consequence 54] | 46/86 [consequence 54] | 47/87 [consequence 54] | 47/87 [consequence 54] |
| R4 | 24/72 [consequence 34] | 25/74 [consequence 34] | 27/78 [consequence 34] | 28/81 [consequence 34] |
| R5 | 18/71 [consequence 25] | 18/74 [consequence 25] | 20/78 [consequence 25] | 20/82 [consequence 25] |

### mutator_212 (continuity)

| Rung | +0 | +20 | +100 | +500 |
|---|---|---|---|---|
| R1 | 100/100 [none] | 100/100 [none] | 100/100 [none] | 100/100 [none] |
| R2 | 78/93 [pqc_readiness 84] | 78/93 [pqc_readiness 84] | 78/93 [pqc_readiness 84] | 78/93 [pqc_readiness 84] |
| R3 | 46/85 [consequence 54] | 46/86 [consequence 54] | 47/87 [consequence 54] | 47/87 [consequence 54] |
| R4 | 24/72 [consequence 34] | 25/74 [consequence 34] | 27/78 [consequence 34] | 28/81 [consequence 34] |
| R5 | 18/71 [consequence 25] | 18/74 [consequence 25] | 20/78 [consequence 25] | 20/82 [consequence 25] |

R5 under mutator_212 reads computed `71 -> 74 -> 78 -> 82` and emitted `18 -> 18 -> 20 -> 20`. That
is Phase 212's control exactly, and it matches the xfail reason text.

### Per-rung deltas (emitted / computed)

| Rung | ecdsa +0→+20 | ecdsa +0→+500 | rsa +0→+20 | rsa +0→+500 | certless +0→+20 | certless +0→+500 | mutator_212 +0→+20 | mutator_212 +0→+500 |
|---|---|---|---|---|---|---|---|---|
| R1 | +0 / +0 | +0 / +0 | +0 / +0 | +0 / +0 | +0 / +0 | +0 / +0 | +0 / +0 | +0 / +0 |
| R2 | +5 / +6 | +6 / +7 | +1 / +1 | +2 / +2 | +0 / +0 | +0 / +0 | +0 / +0 | +0 / +0 |
| R3 | +4 / +8 | +6 / +12 | +1 / +2 | +4 / +7 | +0 / +1 | +1 / +2 | +0 / +1 | +1 / +2 |
| R4 | +4 / +10 | +8 / +21 | +2 / +4 | +6 / +16 | +1 / +2 | +4 / +9 | +1 / +2 | +4 / +9 |
| R5 | +3 / +12 | +6 / +24 | +1 / +6 | +4 / +18 | +0 / +3 | +2 / +11 | +0 / +3 | +2 / +11 |

### Subscore movement (+0 → +20 → +500)

These locate each component. Only the domains that move are shown. data_in_motion is 25 throughout
on every rung and reading, and R1 is 25 everywhere.

| Reading | Rung | hygiene | modern_tls | identity_trust | agility_signals | data_at_rest |
|---|---|---|---|---|---|---|
| rows_ecdsa | R2 | 25→25→25 | 25→25→25 | 23→24→25 | **17→25→25** | 25→25→25 |
| rows_ecdsa | R3 | 22→23→24 | 23→23→24 | 16→18→23 | **17→25→25** | 25→25→25 |
| rows_ecdsa | R4 | 15→17→22 | 18→19→23 | 11→14→21 | **16→25→25** | 23→23→24 |
| rows_ecdsa | R5 | 13→16→22 | 15→17→22 | 12→16→23 | **16→25→25** | 25→25→25 |
| rows_rsa | R2 | 25→25→25 | 25→25→25 | 23→24→25 | 17→17→17 | 25→25→25 |
| rows_rsa | R3 | 22→23→24 | 23→23→24 | 16→18→23 | 17→17→17 | 25→25→25 |
| rows_rsa | R4 | 15→17→22 | 18→19→23 | 11→14→21 | 16→16→17 | 23→23→24 |
| rows_rsa | R5 | 13→16→22 | 15→17→22 | 12→16→23 | 16→16→17 | 25→25→25 |
| rows_certless | R2 | 25→25→25 | 25→25→25 | 23→23→23 | 17→17→17 | 25→25→25 |
| rows_certless | R3 | 22→23→24 | 23→23→24 | 16→16→16 | 17→17→17 | 25→25→25 |
| rows_certless | R4 | 15→17→22 | 18→19→23 | 11→11→11 | 16→16→17 | 23→23→24 |
| rows_certless | R5 | 13→16→22 | 15→17→22 | 12→12→12 | 16→16→17 | 25→25→25 |
| mutator_212 | R2-R5 | identical to rows_certless, cell for cell | | | | |

**identity_trust** rises only when C rises (rows_rsa and rows_ecdsa). It is flat under certless and
mutator_212. That reproduces 212's own finding that identity_trust is "flat because divides by
`cert_denom`, which P2b's mutator does not touch". **agility_signals** jumps by 8 or 9 points at +20
under rows_ecdsa only, and then stays at the 25 clamp. That is the key-type branch: one observed
ECDSA certificate moves it from RSA-only (-8) on R2-R4, or unreported-with-certs (-8) on R5, to
ECDSA (+4). It is a step, not a ratio, so it does not grow with N. Elsewhere agility moves by at
most +1 at +500, through its E-denominated terms. hygiene, modern_tls and
data_at_rest move in every reading: those are the E terms. R5's hygiene/modern_tls/identity_trust
values under mutator_212 at +0 and +500 (13→22, 15→22, 12→12) match 212's per-domain table.

---

## 6. What the readings separate

**Is 212's number reproduced from rows? Yes.** rows_certless equals mutator_212 in all 20 cells,
with the same emitted score, computed score, subscores and ceiling. 212's three-field mutator
neither inflated nor deflated the endpoint component. The fields where it differs from real rows
(`totals.endpoints`, the `protocol_counts.TLS` base, `assessed_crypto_count`) are ones the score
does not read.

**Approximate split.** The components interact through the per-domain 25 clamp, so this additive
split is approximate (RESEARCH A2). It is the difference between adjacent readings' computed
scores, from `results[]`.

| Point | Rung | E (certless − base) | C (rsa − certless) | key type (ecdsa − rsa) | total (ecdsa − base) |
|---|---|---|---|---|---|
| +20 | R2 | +0 | +1 | +5 | +6 |
| +20 | R3 | +1 | +1 | +6 | +8 |
| +20 | R4 | +2 | +2 | +6 | +10 |
| +20 | R5 | +3 | +3 | +6 | +12 |
| +100 | R2 | +0 | +1 | +5 | +6 |
| +100 | R3 | +2 | +2 | +6 | +10 |
| +100 | R4 | +6 | +5 | +6 | +17 |
| +100 | R5 | +7 | +5 | +6 | +18 |
| +500 | R2 | +0 | +2 | +5 | +7 |
| +500 | R3 | +2 | +5 | +5 | +12 |
| +500 | R4 | +9 | +7 | +5 | +21 |
| +500 | R5 | +11 | +7 | +6 | +24 |

The research hypothesis for R5 at +20 was ≈3 endpoint, ≈3 cert and ≈6 key-type. The measured
values match it.

**What the split shows:**

- **The key-type step is constant in N:** +5 or +6 from the first 20 rows onward. One healthy ECDSA
  observation is enough to earn it.
- **At +20 it dominates every graded rung.** A denominator-only fix leaves it untouched.
- **R2's whole movement is C plus key type.** Its E component is 0 at every point, because R2 has no
  E-denominated weakness numerator. So a fix aimed at E alone cannot move R2 at all: under
  rows_ecdsa, R2 would still go 93 → 99.

**R1 is pre-saturated.** It reads 100/100 with all six subscores at 25 in every cell, so under
212's two-maskers rule a flat R1 is ambiguous: it is neither evidence for nor against dilution.

**Supplementary observation (not in the instrument's JSON).** This was derived at the same sha by
diffing `scripts.p2b_instrument.evidence_for(rung, reading, 0)` against `extra=500` and listing the
changed evidence keys. Each certificate-bearing healthy row adds one MEDIUM finding,
`TLS certificate uses quantum-vulnerable ECDSA key` (or `... RSA key`). Over +500 that is 500
MEDIUM findings, and they are not scored: the model reads CRITICAL and HIGH for the ceilings, and
LOW only as the legacy-TLS fallback.

So on a quantum-readiness score, the primary reading's "healthy" endpoint is itself a
quantum-vulnerable finding, and the key-type branch rewards observing it by up to 12 raw agility
points. Outside the unscored fields, the only evidence keys that change across the sweep are:

- E (`assessable_endpoint_count`);
- C (`certs_observed`);
- `cert_key_type_counts`;
- R4's evidence-side `dar_db_plaintext_ratio` (not read by the score: the scorer re-divides
  `dar_db_plaintext_count` by E).

The unscored fields that also change are `totals.*`, `protocol_counts.TLS`,
`assessed_crypto_count` and the MEDIUM counts. Every numerator is fixed.

---

## 7. Closed-form diff

- **Points agreeing:** 80 of 80 (`agreement.agree` / `agreement.total`), on emitted, computed,
  subscores and ceiling source. The 8 real-estate cells also agree (§9).
- **`KNOWN_DISAGREEMENTS`:** `{}` (`known_disagreements`). There are none, either sweep or probe.
- **Term-probe coverage:** 395 probes across both bases, 0 disagreeing (233-02). R3 has E = C; R5
  has E != C.

The probes cover 36 numerator paths × (6 R3 values + 5 R5 values), plus 10 R3 branch probes. Between
them, those exercise all 35 rows of `RATIO_TERMS`, the e-mail STARTTLS addend, the scan-error,
key-type and PQC branches, the HIGH tiers, and the unassessed rescale.

**Mutation table (from 233-02 and 233-03).** Each mutation was reverted afterwards and
byte-identity confirmed.

| Mutation | File | Red node(s) | Evidence |
|---|---|---|---|
| M1 `EXPONENT` 0.5 → 0.55 | closed form | test_closed_form_agrees (+ term_probes, is_independent) | 58 of 80 sweep points disagree; 395/395 probes disagree |
| M2 `TOP_GOOD` 84 → 85 | closed form | test_closed_form_agrees + test_ceiling_identification_consistent | 16 of 80 disagree (all R2 cells); silent on probes (84 always loses there) |
| M3 R3 expired 2 → 1 | instrument | test_rows_reproduce_dict_ladder_at_zero | `expired_count (2, 1)`; R3 computed 85 → 86 |
| M4 `from quirk import intelligence` | closed form | test_closed_form_is_independent | static leg: import outside the allowlist; dynamic leg loads `quirk*` |
| M4b `_SRC = "quirk/intelligence/scoring.py"` | closed form | test_closed_form_is_independent | non-docstring string naming the audited code |
| M5 self-signed weight 9 → 10 | closed form | test_closed_form_term_probes | 63/395 probes disagree |
| M6 `identity_weak_etype_count` denominator E → C | closed form | test_closed_form_term_probes | 4 disagree, all R5 (E != C), none R3 |

**Provenance and limit (repeating §3).** The spec came from RESEARCH Q4, which was read from
`scoring.py` at `e0064b02`, plus the ported prototype. So 80/80 agreement validates two things: the
instrument's reading of the scorer, and D-12's arithmetic model. It says nothing about whether the
scorer matches its intent.

---

## 8. Row-reproduction gaps (`projection_gaps`)

Each gap is listed as dict value vs row value at +0.

| Rung | Gaps |
|---|---|
| R1 | `protocol_counts.TLS` 40 vs 26; `totals.endpoints` 400 vs 40 |
| R2 | `protocol_counts.TLS` 40 vs 26; `totals.endpoints` 400 vs 40 |
| R3 | `protocol_counts.TLS` 40 vs 26; `totals.endpoints` 400 vs 40 |
| R4 | `protocol_counts.TLS` 40 vs 24; `totals.endpoints` 400 vs 40 |
| R5 | `protocol_counts.TLS` 40 vs 19; `totals.endpoints` 370 vs 38 |

None of these fields is read by the score, and the contract asserts that no gap falls on a
score-relevant path.

Two fidelity notes go with the gaps.

**40 certificates on 40 rows (R1-R4).** The dict asserts `certs_observed` 40 among 40 assessable
endpoints. Reproducing that from rows puts a certificate on non-TLS rows too (SSH, S3, K8S and
others), because any row with a datetime `cert_not_after` counts. Recorded as a fidelity note, and
accepted under CONTEXT discretion (RESEARCH Open Question 3).

**R5 `legacy_tls` is a LOW proxy.** The R5 dict has no `legacy_tls_count`, so the scorer falls back
to the LOW severity count, 16. The row rebuild reproduces that with 16 TLSv1.1 rows. The real
2026-09-14 rows carry **0** legacy-TLS endpoints (RESEARCH Q5). So R5's modern_tls 15 rests on a
proxy the real estate does not have (§9).

---

## 9. Real estate (local-only, D-08)

These readings come from `quirk-output/`, which is absent in CI. They are a **local-only**
observation; no committed test depends on them. The DB was read only through `--real-db`, which
opens it with sqlite `mode=ro` and the `.backup` API into a temp dir. The DB sha256 was
`990366f8346a644bd576ef6543376d7d647fa783a3d5cf78ff13cca79677b946` before and after the runs, with
size and mtime unchanged, and the temp dir was left empty. Snapshot: 370 rows for run
`2026-09-14T14:25:49.899977+00:00`, reference_utc `2026-09-14T14:26:06.389430`
(`real.snapshot_db.{row_count,run_id,reference_utc}`). Only aggregate scores are recorded here.

| Reading | +0 | +20 | +100 | +500 |
|---|---|---|---|---|
| recorded_json + mutator_212 | 15/61 [consequence 25] | 16/65 [consequence 25] | 18/71 [consequence 25] | 19/76 [consequence 25] |
| snapshot_rows + rows_ecdsa | 17/69 [consequence 25] | 19/75 [consequence 25] | 21/83 [consequence 25] | 23/91 [consequence 25] |

In every cell the winning ceiling is consequence 25 (rule `deep-critical`), there are no losing
ceilings, 5 domains are assessed (data_in_motion is unassessed), and the closed form agrees.

**Re-derivation gap at +0: 15/61 recorded vs 17/69 from the rows at this sha.** These are the
measured differences, from `real.*.cells[0]`:

| Field | recorded_json | snapshot_rows |
|---|---|---|
| open CRITICAL count (from `rating_cap_reason`) | 5 | 7 |
| modern_tls | 10 | 19 |
| identity_trust | 10 | 11 |
| hygiene | 10 | 10 |
| agility_signals | 25 | 25 |
| data_at_rest | 21 | 21 |
| data_in_motion | unassessed | unassessed |

The modern_tls (+9) and identity_trust (+1) differences give the computed gap of +8 after the
rescale over 5 assessed domains (10 of 125 raw points). The field-level causes are
from RESEARCH Q5, not from this instrument's JSON:

- `legacy_tls_count` is 0 in the rows, against the LOW proxy of 16 in the pre-Phase-211 JSON;
- the CRITICAL count is 7 vs 5: 6 "TLS certificate expired" plus 1 SAML RSA-1024 from today's
  composer. **One of the six expired-certificate CRITICALs is a clock artifact, not a composer
  change** (corrected after code review WR-01, 2026-10-27). Real-estate mode builds evidence with
  `reference_utc` = the scan time (2026-09-14 14:26), but `derive_report_findings` checks expiry
  against the wall clock. Of the 17 certificates, 5 had expired at scan time and 6 have expired
  as of 2026-10-27; the extra one has notAfter 2026-09-15 14:20, one day after the scan. So
  against the scan's own clock there are 5 expired-certificate CRITICALs plus the SAML one (6
  CRITICALs, not 7). The score does not change, because `deep-critical` binds at 5 or more either
  way. This CRITICAL count **drifts with the date the instrument is run**: it grows as more of the
  17 certificates expire. The fix belongs in the evaluator (a `reference_utc` parameter), which is
  outside this phase's scope (no `quirk/` change), so it is recorded here and in the instrument's
  real-estate docstring instead;
- `saml_weak_signing_count` is 1 vs 2 (Phase 210 dedupe);
- one candidate cause not isolated: `derive_report_findings(cfg=None)` designates only the
  well-known TLS ports (RESEARCH A1).

The real estate already carries ECDSA certificates, and agility is 25 at +0, so **there is no
key-type flip on this estate**. Its rows_ecdsa rise (computed +22 at +500: hygiene 10→20,
identity_trust 11→22, modern_tls 19→23, data_at_rest 21→24) is E plus C. This bears on the R5
fidelity todo (`r5-ladder-fixture-is-not-the-measurement-it-claims`), which records R5's
`{RSA: 0, ECDSA: 0}` and the missing PQC-hybrid count against the real estate's
`{RSA: 18, ECDSA: 1}`.

---

## 10. Analytic ruling on ceiling-shaped candidates (D-12)

The ceiling is a linear squeeze: `emitted = round(c x computed / 100)`. That identity held at all 80
points. Wherever the winning ceiling's source and value stay constant across a rung's sweep, any
rise in computed passes through to emitted, scaled by c. Any ceiling whose inputs are absolute
counts (212's absolute exposure is one) stays constant across this sweep, because every weakness
count is fixed (§6). It therefore cannot reduce the computed rise. And because it acts after the
computed score, it cannot make `wider_computed <= base_computed` pass
(`tests/test_score_properties.py:646`) by construction.

Per rung, across all four readings and all four points (`results[*].ceiling_source`,
`ceiling_value`, `losing_ceilings`):

| Rung | Winning ceiling, all 16 cells | Losing ceilings, all 16 cells | Condition held? |
|---|---|---|---|
| R1 | none | none | Yes. No ceiling binds, and computed is flat at 100, so the case is vacuous. |
| R2 | pqc_readiness 84 | none | Yes. Emitted still rises 78 → 84 (rows_ecdsa), the squeeze passing computed 93 → 100 through. |
| R3 | consequence 54 | pqc_readiness 84 | Yes |
| R4 | consequence 34 | pqc_readiness 84 | Yes |
| R5 | consequence 25 | pqc_readiness 84 | Yes |

The same held on the real estate: consequence 25 in all 8 cells. **No ceiling-shaped candidate is
supported.** This closes 212's "structurally unmeasured" outcome for absolute exposure as a P2b fix.
It says nothing against absolute exposure as a consequence-calibration change: 212 measured R4 move
24 → 18 under it on the ladder.

---

## 11. Verdict (D-13, D-20)

**Support rule.** A candidate is supported only if, applied to the measured inputs, it would stop
the computed (and emitted) score from rising across the sweep on every graded rung (R2-R5), under
every reading (rows_ecdsa, rows_rsa, rows_certless, mutator_212).

| Candidate | Component it addresses | Components it leaves | Against the measured readings | Verdict |
|---|---|---|---|---|
| **Distinct hosts** (212) | E, and only when the added endpoints share existing hosts | C; key type | Every healthy row here is on a new host (`healthy-<i>.p2b.example`), so a host-count denominator grows by N exactly as E does: no change on any reading. Even on a same-host variant, rows_rsa and rows_ecdsa still rise through C and key type (R5 +3 C and +6 key type at +20; R2 +6 with E = 0). Evidence still carries no host counter (212 §5). | **Not supported** |
| **Absolute exposure** (212) | Aggregate, after the computed score (ceiling-shaped) | E, C and key type, all upstream of it | §10: the winning ceiling is constant on every rung, so computed rises pass straight through. | **Not supported** (ruled out analytically, and confirmed by the constant-winner tables) |
| **Scan-scope normalisation** (212) | E, and only under a fixed requested scope | C; key type | Under growing scope it equals the control (212). Under fixed scope it removes at most the E column of §6. rows_rsa and rows_ecdsa still rise, and R2 under rows_ecdsa still goes 93 → 99. | **Not supported** |
| **Any other ceiling-shaped term** | Post-computed | E, C and key type | §10 | **Not supported** |
| **Any E-only denominator fix** (would turn the mutator-based xfail green) | E | C (3 terms); key type | Leaves R5 +9 of +12 at +20 and +13 of +24 at +500, and all of R2's +6/+7, on rows_ecdsa | **Not supported** |
| **New shape the data point to** (RESEARCH Open Question 5, tested here as a hypothesis, not adopted): (a) denominator-free absolute-count penalties at the ratio sites, both E- and C-denominated; (b) a key-type rule that does not reward a single healthy observation, e.g. one driven by the presence of quantum-vulnerable keys rather than by the ECDSA/RSA mix | E, C and key type | none that this sweep varies | Across the sweep every numerator is fixed, and only E, C and `cert_key_type_counts` change among scored inputs (§6). So a model that reads none of the three in ratio or mix form would hold computed flat on all 80 points **by construction**. That is analytic. No implementation was run, so it is not a measured pass. | **The shape the data point to; unmeasured** |

**Verdict.** None of 212's three candidates is supported, and no ceiling-shaped candidate can be.
The data point to a new two-part shape, (a) + (b) above. It is the only shape examined that
addresses all three measured components. Its support is analytic, and Phase 234 must measure it
with this instrument before adopting it.

**Effort: L.** The basis:

- **35 ratio sites.** The closed form's `RATIO_TERMS` has 35 rows: 32 over E and 3 over C (one of
  the E rows is the positive mTLS term). Moving them to absolute counts means choosing a penalty
  curve, and its free parameters, for every family.
- **The key-type branch.** Its three outcomes (`KEY_TYPE_RSA_ONLY`, `KEY_TYPE_ECDSA`,
  `KEY_TYPE_UNREPORTED_WITH_CERTS` in the closed form) need a new rule in `scoring.py`'s agility
  domain.
- **Re-measuring all five rungs** against the operator's blind-set bands, without tuning to them
  (999.113 D5).
- **Updating the closed form in step.** `test_closed_form_agrees` goes red by design until it is.
- **Golden-fixture regeneration and the disclosure text.**
- **The `_endpoints_assessed()` boolean-gate hazard** (212 §6) must be re-checked if E stops being
  read.

**What Phase 234 must change, or decide first:**

1. Whether the key-type branch is in P2b's scope. The measurement says it has to be: on every graded
   rung at +20 it is the largest single component. A denominator-only fix leaves it in place.
2. Whether C is in scope. It is on every certificate-bearing reading, and it is all of identity_trust's
   movement.
3. The absolute-count penalty curve. This is the hard part, and it is where tuning to a target is
   easiest to slip into.
4. Whether an observation that is itself a quantum-vulnerable MEDIUM finding should ever raise a
   quantum-readiness score (§6).

**Gate (D-20).** Phase 234 gates on re-running `python -m scripts.p2b_instrument` across all five
rungs and all four readings (rows_ecdsa, rows_rsa, rows_certless, mutator_212), and diffing the
result against §4 and §5 of this record. A fix passes only if computed and emitted are
non-increasing across +0/+20/+100/+500 on R2-R5 in every reading. The xfail turning green is
necessary but not sufficient: it reads mutator_212 only.

**Inherited denominator.** The domain connector ratios inherit the same endpoint denominator. See
todo `999.113-domain-connector-ratio-denominator-is-approximate`. Any change to E reaches them too.

---

## 12. Invariants and open items

- **Criterion 4.** `test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints` is still
  `xfail(strict=True)` (`tests/test_score_properties.py:575-576`) and still registered in
  `tests/skip_registry.py:130` as `known_open_defect`. Re-run at the measured sha:
  `pytest tests/test_score_properties.py -k p2b` → `24 deselected, 3 xfailed`.
- **Criterion 3.** `git diff e0064b02..HEAD -- quirk/intelligence/scoring.py quirk/intelligence/evidence.py | wc -l`
  prints `0`. Neither file was touched in this phase.
- **Kerberos placeholder (D-15).** No rung carries a Kerberos placeholder row. Every rung's KERBEROS
  row has a real etype detail (`etype:18:aes256-cts-hmac-sha1-96:SAFE`), as asserted by
  `tests/test_p2b_instrument.py::test_healthy_rows_are_healthy`. Todo
  `261023-detect-kerberos-placeholder-rows-count-as-assessed` is not fixed here, because the fix
  moves scores. Its "before or in Phase 233" wording now means Phase 234.
- **R5 fidelity.** Open, and noted with §8-§9's measurements on its todo.

---

## 13. What would falsify this record

- **A disagreement between the instrument and the scorer at the recorded sha.** If re-running
  `python -m scripts.p2b_instrument --json` at
  `2571917018452c10d595d35700b830a7678d0438` produced any cell that differs from §4-§5, or a
  non-empty `KNOWN_DISAGREEMENTS`, the tables would be wrong.
- **A healthy-row definition that adds weakness.** If the healthy rows were shown to raise any scored
  weakness numerator, the sweep would not hold exposure fixed. §6's evidence diff says they raise
  none; their MEDIUM findings are unscored.
- **A ceiling that varies with N on fixed weaknesses.** A ceiling-shaped candidate whose value
  depended on E or C would not be ruled out by §10. But it would be a ratio again, and §11's E and C
  analysis would apply to it.
- **A measured implementation of the new shape that still rises.** That would falsify the claim
  that the shape addresses all three components. One input the sweep does not vary is a scan-error
  rate, which is 0 here.
- **The closed form copying a defect.** Its spec came from the code (§3), so agreement cannot show
  the code matches intent. A first-principles spec that disagreed would reopen §7, not §5.

---

## Provenance appendix

| Table / figure | Source | JSON key path |
|---|---|---|
| §2 sha, blobs, Python | `233-measurement.json` | `provenance.{head_sha,scoring_blob,evidence_blob,python}` |
| §4 ladder | `233-measurement.json` | `ladder_at_zero.<R1..R5>.{emitted,computed,ceiling_source,ceiling_value,losing_ceilings,subscores}` |
| §5 sweep tables (four) | `233-measurement.json` | `results[]` where `reading`, `rung`, `extra` match; fields `emitted`, `computed`, `ceiling_source`, `ceiling_value` |
| §5 deltas | `233-measurement.json` | `results[].{emitted,computed}` at `extra` 0, 20, 500 (subtracted) |
| §5 subscore movement | `233-measurement.json` | `results[].subscores` at `extra` 0, 20, 500 |
| §6 split | `233-measurement.json` | `results[].computed` across readings (subtracted) |
| §6 evidence-key diff, MEDIUM titles | not in JSON; `scripts.p2b_instrument.evidence_for(r, reading, 0 / 500)` and `_healthy(n, kind)` at the same sha | n/a (supplementary) |
| §7 agreement, `KNOWN_DISAGREEMENTS` | `233-measurement.json` | `agreement.{agree,total}`, `known_disagreements` |
| §7 probes, mutations | `233-02-SUMMARY.md`, `233-03-SUMMARY.md` | mutation tables |
| §8 gaps | `233-measurement.json` | `projection_gaps.<R1..R5>` |
| §9 real estate | `233-real-estate.json` | `real.recorded_json.cells[]`, `real.snapshot_db.cells[]`, `real.snapshot_db.{row_count,run_id,reference_utc}` |
| §9 field-level causes | `233-RESEARCH.md` Q5, A1 | n/a (research measurement) |
| §10 ceilings | `233-measurement.json` | `results[].{ceiling_source,ceiling_value,losing_ceilings,ceiling_identity_holds}` |
| §11 term counts | `scripts/p2b_closed_form.py` | `RATIO_TERMS` (35 rows: 32 `"E"`, 3 `"C"`), `KEY_TYPE_*` |
| DB sha256 before/after | `shasum -a 256 quirk-output/quirk.db` | n/a |
