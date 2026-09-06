---
type: todo
status: resolved
resolves_phase: "184.4"
resolved: 2026-09-06
created: 2026-09-05
source: phase-184.2 UAT-184.2-05 chaos-lab human verification
supersedes: BACK-89
priority: high
---

# A single CRITICAL finding can make report generation impossible

> **This is a re-discovery of BACK-89, not a new defect.** BACK-89
> ("[P2 — UI] Executive Summary score vs severity-bar consistency",
> `.planning/milestones/v5.0-ROADMAP.md:845`) recorded the identical
> contradiction on 2026-05-21 during UAT-85-08: `Overall Readiness: 100`
> rendered alongside non-zero CRITICAL/HIGH severity bars from the same scan.
> It was never cited in any REQUIREMENTS file, never reached `HORIZON.md`, and
> its backlog dir `.planning/backlog/999.82-executive-summary-score-vs-severity-consistency/`
> contains only an empty `.gitkeep`. It went unseen for ~3.5 months.
>
> **Severity has increased since it was filed.** BACK-89 was triaged P2 and
> explicitly "not a security-correctness bug" — a misleading gauge. Phase 98
> then added the fail-closed congruence guard, converting the same underlying
> contradiction into a hard halt that emits **no report at all**. Treat this
> as P1 now. BACK-89's investigation questions (a)–(d) remain the right
> framing for the fix and should be read alongside this entry.

`quirk/intelligence/scoring.py::_rating()` and
`quirk/reports/content_model.py::_check_congruence()` assert contradictory
invariants, and the contradiction resolves as an uncaught halt with **zero
report artefacts**.

- `scoring.py:95` — `_rating()` maps score to band on numeric thresholds alone
  (`>=85 EXCELLENT`, `>=70 GOOD`, `>=55 MODERATE`, `>=35 FAIR`, else `POOR`).
  There is **no CRITICAL floor**: nothing forces the band down when CRITICAL
  findings exist.
- `content_model.py:469` — `_BAND_CRITICAL_THRESHOLD` asserts that
  `EXCELLENT` / `GOOD` / `MODERATE` permit **zero** CRITICAL findings, and
  `_check_congruence()` raises `ReportCongruenceError` otherwise.

Any scan scoring >= 55 with >= 1 CRITICAL finding therefore produces **no
report at all** — not a warning, not a degraded report. The scan itself
succeeds and `findings-*.json` / `technical-findings-*.md` are written; only
the exec-headline path dies, taking HTML/PDF/DOCX/CBOM/scorecard with it.

**Why it matters:** this is the worst possible failure shape for a consulting
deliverable — a complete, successful scan that yields nothing handable to a
client, surfacing only at the final reporting step.

Severity does feed the score (`scoring.py:155` folds `HIGH + CRITICAL` into one
weighted, per-category-capped agility input), but the contribution is far too
small to cross a band threshold: the observed run scored **89/100 EXCELLENT**
with one CRITICAL open.

**Reproduced 2026-09-05** during Phase 184.2's chaos-lab human verification
(UAT-184.2-05), scanning `127.0.0.1` with the shipped 17-port
`CONSULTING_TLS_PORTS` default against the full chaos lab:

```
error: Report generation halted: executive headline 'EXCELLENT' is
inconsistent with 1 CRITICAL finding(s). Review findings before generating
the report.
```

The CRITICAL was `TLS certificate expired` on port 9443 (a chaos-lab fixture);
a HIGH `TLS certificate is self-signed` on 10443 accompanied it.

**Not caused by Phase 184.2, and not newly reachable.** A client with an
expired certificate on plain 443 hits the identical wall under the *old*
3-port `[443, 8443, 4443]` default. Phase 184.2's port widening only raises
the likelihood of meeting it — 17 ports across a real estate turn up a bad
certificate far more often than 3. The phase's six plans touch neither
scoring nor reporting.

**Guard is correct; the producer is not.** Do not weaken or remove
`_check_congruence()` — Phase 98 built it fail-closed deliberately (see
`tests/test_congruence_guard.py`, TRANS-03 / D-06) so a "GOOD over 7 CRITICAL"
headline is structurally impossible. The fix belongs on the scoring side: give
`_rating()` a severity floor so a CRITICAL cannot coexist with an
EXCELLENT/GOOD/MODERATE band, making the guard unreachable in normal
operation rather than load-bearing.

**How to apply:** add the floor in `_rating()` (or wherever the band is
finalised), with regression tests covering the exact reproduction above —
score >= 85 with one CRITICAL must yield a band the congruence guard accepts,
and a report must be produced. A test asserting the two contracts agree across
the full band/severity matrix would keep them from drifting apart again.

Related: `[[project_validation_status_row_gap]]` is unrelated; this is a
producer/consumer invariant mismatch, not a tracking-file gap.


---

## RESOLVED — Phase 184.4 (Rating Band Severity Floor), 2026-09-06

Every item this entry asked for was delivered. Point by point:

- **"add the floor in `_rating()` (or wherever the band is finalised)"** — done in
  `quirk/intelligence/scoring.py`, reading `evidence['finding_severity_counts']` already in scope
  so nothing was plumbed onto the hot path. The floor caps the BAND only; the numeric score for a
  given evidence dict is byte-identical before and after (same evidence scored 97/100 with six
  identical subscores; only `rating` moved).
- **"regression tests covering the exact reproduction above"** —
  `tests/test_score_severity_floor_regression.py`, written RED-first and proven to fail against
  unmodified code with the verbatim `ReportCongruenceError` captured before any fix landed. It
  drives the real `compute_readiness_score()` through `write_reports()`, not a mock.
- **"a test asserting the two contracts agree across the full band/severity matrix"** —
  `tests/test_band_severity_matrix_gate.py`, which derives BOTH tables from the shared module at
  test run time rather than hand-copying them.
- **"Do not weaken or remove `_check_congruence()`"** — honored and proven: `git diff` on
  `quirk/reports/content_model.py`'s guard bodies is empty. Only the SOURCE of the threshold values
  moved, into the new stdlib-only `quirk/severity_bands.py`.

Beyond what was asked: the second live band producer (`html_renderer.py::_score_band()`) was
deleted outright, and an AST gate now regenerates the set of band-producing functions from source
on every test run — so a future clone fails with no list edit. That gate immediately found a
previously-undocumented fourth scale (`quirk/notify/payload.py::_score_to_band()`).

**Verified live 2026-09-06**, not just in tests: the operator re-ran the original chaos-lab
reproduction. The scan scored 86/100 — still above the EXCELLENT threshold of 85, so the numeric
band was EXCELLENT and the floor capped it to FAIR. All report artifacts generated, where this
same scan previously halted with zero. See `184.4-HUMAN-UAT.md`.

BACK-89's investigation questions (a)-(d) are each answered or dispositioned in ROADMAP SC #6, and
its orphaned backlog dir `999.82` is resolved — closing the ~3.5-month invisibility this entry
called out.
