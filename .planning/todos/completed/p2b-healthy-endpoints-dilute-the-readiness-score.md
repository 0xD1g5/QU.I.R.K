---
type: todo
created: 2026-09-14
source: 999.115 scoring-model work (task 22) — survived all six model changes
priority: P1
requirement: null
resolves_phase: 234  # was 212 (closed), then null with owner 999.120; v5.28 Phase 234 (2026-10-15)
status: completed
resolved: 2026-10-27
target: next milestone — the last open property in the P1-P8 suite
---

# P2b — observing more healthy endpoints still RAISES the readiness score

**Owner:** 999.120 (HORIZON.md ledger row).
**Re-pointed:** 2026-10-02 by the v5.26 re-audit. Phase 212 (decision-only) recommended NONE and handed implementation to an OPERATOR-RESERVED post-v5.25 phase that was never assigned.

Scanning more ports on the same hosts improves the client's grade without improving the
client's security. This is the one property in `tests/test_score_properties.py` that all six
of 999.115's model changes failed to close, and it is filed rather than fixed because it is a
**denominator** problem, not a model-shape problem — a different fix in a different place.

## What fails

`tests/test_score_properties.py::test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints`,
xfail(strict=True) at all three parameters. Re-measured 2026-09-14 on the 31-host reference
estate, holding **every weakness count identical** and adding only healthy assessable endpoints:

| added healthy endpoints | computed score | emitted score |
|---|---|---|
| base (38 assessable) | 71 | 18 |
| +20 | **74** | 18 |
| +100 | **78** | 20 |
| +500 | **82** | 20 |

The estate's absolute exposure — 6 plaintext endpoints, 5 expired certificates, 5 CRITICAL
findings — is unchanged across every row.

## Root cause

`endpoint_denom` (`quirk/intelligence/scoring.py:412`) reads
`evidence["assessable_endpoint_count"]`, and `domain_denom` is assigned from it at line 421.
Almost every ratio-shaped impact in the model divides by one of those two — plaintext HTTP,
HTTP-on-TLS-port, legacy TLS, unknown services, mTLS, and the whole identity/DAR/motion family
(`scoring.py:481-502`).

`assessable_endpoint_count` is incremented per endpoint row at
`quirk/intelligence/evidence.py:198`. It is a **strict improvement** over the `totals.endpoints`
probe count that 999.113 replaced — it excludes ADVISORY and CLOSED rows, so a scan that reached
nothing can no longer fabricate a 100 — and `scoring.py:418` already records it as an improvement
and *not* a fix. But it is still a count that rises when you scan more ports on the same hosts.

The honest statement of the defect: **the evidence model cannot distinguish "there is more
infrastructure" from "we looked harder", and the score rewards both identically.** A purely
proportional model has no way to say that six plaintext endpoints is the same amount of exposure
whether they sit among 38 services or 538. The attacker needs one.

## Why 999.115 did not close it

999.115 added `_consequence_ceiling()`, which carries high-consequence findings **absolutely**
rather than proportionally. That closed P1 and moved the whole calibration ladder, but it acts on
the *aggregate* after the fact. It does not change any ratio's denominator, so the dilution is
still computed — the ceiling merely **masks** it in the emitted number.

The mask is why this needs watching rather than shelving. With the ceiling in place the emitted
score only moves 18 → 20 across a 14× dilution, which reads almost like a fix. It is not one: the
computed score still rises at every step, and the dilution will surface at full size on any
estate the ceiling does not bind — which is every estate with fewer than one open CRITICAL and
some post-quantum coverage, i.e. exactly the healthier clients.

`test_p2b_...` now asserts the **pre-ceiling** value as well as the emitted one, via
`_computed_score()`, specifically so the ceiling cannot hide this defect from its own test. Do not
weaken that back to an emitted-score-only assertion.

## Feasibility & Effort

**Confidence: LIKELY. Size: M. Spike first: YES.**

- **CONFIRMED** — the denominator sites are exactly `endpoint_denom`/`domain_denom`
  (`scoring.py:412,421`) and their ~20 consumers at `scoring.py:481-502`. Read, not inferred.
- **CONFIRMED** — `assessable_endpoint_count` grows with scan depth; it is a per-row increment at
  `evidence.py:198` with no host-level or service-level deduplication.
- **CONFIRMED** — the ceiling does not address it; measured above, post-all-six-changes.
- **UNKNOWN** — what the right denominator actually is. Candidates, none validated:
  - **distinct hosts** rather than endpoints. Stable under deeper port scanning, but wrong for a
    single host exposing 40 services, and the estate's host count is not currently carried in
    evidence as a first-class counter.
  - **an absolute exposure term** for the plaintext/expired families, mirroring what
    `_consequence_ceiling()` did for findings. Consistent with 999.115's own conclusion that
    consequence must be absolute, but multiplies the free-parameter count the ceiling work
    deliberately collapsed from four to one.
  - **scan-scope normalisation** — divide by the ports actually requested rather than the rows
    returned. Makes the score comparable across scans of the same scope and incomparable across
    different scopes, which may be the honest trade.
- **UNKNOWN** — blast radius on the calibration ladder. Every rung's ratios divide by one of these
  two denominators, so any change re-scores all five and the ladder must be re-measured. That is
  the main reason this is M rather than S.

**Spike, do not plan straight to implementation.** The measurement harness that makes this
tractable already exists and should be reused rather than rebuilt: the ladder in
`tests/test_score_properties.py`, plus `probe.py`/`candidates.py` in the 999.115 session's
scratch directory (rebuildable from the Method sections of
`.planning/decisions/999.115-scoring-model-candidate-measurements.md`). Per 999.113 D5, choose the
denominator **by measurement against the ladder, not by argument** — and per that decision doc's
own standing caveat, verify the control reproduces the baseline before trusting any row.

## Standing rule this must not break

999.113 D5 — **never tune to a target.** Fitting to the operator's blind-set calibration bands is
the ladder's intended use; adjusting a denominator because a number demos well is not, and the two
are easy to confuse now that a fitting harness exists.

## Phase 233 note (2026-10-27)

Measured by a third, row-level instrument (`python -m scripts.p2b_instrument`, SCORE-08) at HEAD
`2571917018452c10d595d35700b830a7678d0438`. Record: `.planning/decisions/233-p2b-third-instrument-measurement.md`.

**Verdict line:** none of 212's candidates is supported (distinct hosts, absolute exposure, scan-scope
normalisation), and no ceiling-shaped candidate can be. The dilution has three components:

- the endpoint denominator E;
- the certificate denominator C;
- the agility key-type branch, which steps by up to 12 raw points on one observed ECDSA certificate.

On R5, primary ECDSA reading, at +20 the split is about 3 / 3 / 6 of +12 computed. On R2 the whole +6 is C and key
type. The data point to a new two-part shape, effort **L**: (a) denominator-free absolute-count penalties at the 35
ratio sites; (b) a key-type rule that does not reward a single healthy observation. That shape is unmeasured.

**Gate for Phase 234 (D-20):** re-run the instrument across all five rungs and all four readings (rows_ecdsa,
rows_rsa, rows_certless, mutator_212). Diff the result against the record's §4-§5. The fix passes only if computed
and emitted are non-increasing on R2-R5 in every reading. The xfail going green is necessary, not sufficient,
because it reads the 212 mutator only, which moves E alone.

## Resolution

Resolved 2026-10-27 by Phase 234 (SCORE-09), scoring 4.0, commit `23ef422875071113ca33e81c9eb63ce35d2db4de`.

- **The fix.** Every endpoint and certificate ratio penalty became an absolute-count curve, `min(1, count / 40) ** 0.5`
  with N_REF = 40 as a fixed anchor, so a weakness costs the same however many healthy endpoints are observed beside
  it (D-01/D-02). Scan errors are counted the same way (D-03). RSA, ECDSA and EdDSA certificate keys take one
  classical penalty and only a PQC certificate key or PQC key exchange earns agility credit, once (O-2, O-4, D-04).
  The code review then made the mTLS bonus a single presence credit (D-28, `e987c1e0`), the last channel through which
  healthy endpoints could raise a score.
- **The xfail is removed.** `tests/test_score_properties.py::test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints`
  passes at +20/+100/+500 (3 passed, 2026-10-27) with its assertions byte-identical, and its `known_open_defect` row
  is gone from `tests/skip_registry.py` (grep 0).
- **The instrument shows 0 rising series.** `python -m scripts.p2b_instrument` over 5 rungs x 5 readings
  (rows_ecdsa, rows_rsa, rows_certless, rows_mtls, mutator_212) x 4 points finds no rise in the emitted or computed
  score, gated by `tests/test_p2b_instrument.py::test_p2b_non_increase_all_rungs_all_readings`; the spec-first closed
  form agrees at 100/100 sweep cells and 647/647 term probes. The table above (computed 71 -> 74 -> 78 -> 82) is now
  flat at R5 18/74.
- **Record:** `.planning/decisions/234-p2b-fix-and-ladder-remeasurement.md` (`cfde8c90`, review section `5023507a`).
  UAT: UAT-234-01..13; UAT-233-07 and UAT-212-02 re-dispositioned as resolved (`b0f5451e`).
- **Owner closed:** HORIZON 999.120 is CLOSED in the same commit as this move. Disclosed residuals (O-6 domain step,
  D-19 closed-port scan errors, D-20 ML-DSA leaf keys, D-21 QRAMM answer values, the unreachable scorecard legacy
  branch, and stale doc-claim-ledger cites) are owned by the successor row 999.139.
