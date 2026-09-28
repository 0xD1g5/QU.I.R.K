# Decision: cross-surface finding-title/severity vocabulary is a scoring input (211)

**Status:** DECIDED 2026-09-28
**Decider:** operator, via `211-05-PLAN.md`'s `checkpoint:human-verify` sign-off ("Approved, but
tear the lab down first.")
**Supersedes:** nothing. **Completes:** the Phase 210 residual — Success Criterion 5 ("identical
headline score across both pipelines") — left NOT MET at Phase 210 close, tracked at
`.planning/todos/pending/260928-hygiene-moderntls-subscores-diverge-report-vs-dashboard.md`.
**Relates to:** `.planning/decisions/999.113-denominator-semantics.md` (DENOM-01..03), which this
record does NOT touch, extend, or reopen — see "What this decision is not" below.

---

## The problem, with the measured mechanism

Phase 210 closed with the two client-facing pipelines (the CLI/report generator and the dashboard
API) emitting a different headline readiness score for the identical `scan_run_id`: **17/100
(report) vs 18/100 (dashboard)**, isolated entirely to two of six subscore categories — Hygiene
(17 vs 21) and Modern TLS (17 vs 21) — with the other four categories byte-identical.

Re-derived live at execution time (not copied from a planning doc), two scoring inputs in
`quirk/intelligence/evidence.py` were keyed off finding **titles** or finding **severity labels**
rather than endpoint fields — the only two such inputs in the file:

- **Leg 1 — Hygiene.** `_finding_targets()` (`quirk/intelligence/evidence.py:97`) matches finding
  dicts by an exact-string `title` comparison. Three call sites at `:511-513` feed
  `plaintext_http_count`, `http_on_tls_port_count`, and part of `mtls_present_count`. The CLI
  generator (`quirk/engine/findings_evaluator.py`) and the dashboard generator
  (`quirk/dashboard/api/routes/scan.py`) are two **independently maintained** finding-title
  vocabularies by deliberate design — `quirk/dashboard/api/schemas.py:126-129` carries an explicit
  "DO NOT UNIFY" comment predating this phase. `_finding_targets` was comparing against the
  CLI-canonical title string only, so a dashboard-vocabulary title for the identical underlying
  condition never matched, and `plaintext_http_count` measured **10 on the report side, 0 on the
  dashboard side** for the same scan (`scan_run_id 2026-09-28T01:41:30.088508+00:00`, from
  `.continue-here.md`'s carried record).
- **Leg 2 — Modern TLS.** `legacy_tls_count` (pre-fix, `quirk/intelligence/scoring.py:448`) was
  `sev.get("LOW", 0)` — a raw count of every LOW-severity finding of ANY class, not specifically
  legacy-TLS findings. The dashboard's finding-derivation path emits no LOW-severity findings at
  all, so this proxy was a **structural zero** on that pipeline regardless of the underlying TLS
  posture, while the CLI side happened to have exactly one LOW finding matching this specific scan
  (any other LOW-severity finding class would have silently inflated it — see "the proxy was also
  wrong on the CLI side" below).

Both legs feed exactly Hygiene and Modern TLS and no other category, which is why those two
categories diverged and the other four — all derived from endpoint fields that round-trip
faithfully through SQLite — matched byte-identically. This also explains the Data-in-Motion
discriminator D-07 posed (13 = 13 despite sharing `domain_denom = endpoint_denom` and a large
0.1987 ratio): Data-in-Motion's counters come from different `evidence.py` accumulators that were
never on either broken code path.

## The two hypotheses that were REFUTED, and how (D-07)

D-07 posed two grounded hypotheses plus a discriminator before the mechanism above was known. Per
this project's standing rule (D-06/D-07: a negative result is a first-class, valuable outcome and
must survive in the record, never be dropped once the real cause is known), both are recorded here
as REFUTED, with the measurement that refuted each:

- **H1 — `scan_error_rate` differs between the pipelines.** REFUTED. Live re-measurement
  (`211-05`, `scan_run_id 2026-09-28T13:16:55.319715+00:00`), via an independent DB re-derivation
  that bypassed the running dashboard server entirely and called `build_evidence_summary()`
  directly against `CryptoEndpoint` rows: `scan_error.count` = 542 and `scan_error.rate` = 0.6994,
  identical on both pipelines. This matched at unit-fixture scale in `211-02`/`211-03` before the
  live confirmation.
- **H2 — the two pipelines score different endpoint populations.** REFUTED. Same live
  re-derivation: `assessable_endpoint_count` = 216 on both sides, exactly.
- **Discriminator** (Data in Motion matched 13=13 despite sharing `domain_denom = endpoint_denom`
  and carrying a large `motion_email_plaintext_ratio = 0.1987`): consistent with both refutations.
  A pure denominator delta would have moved every ratio sharing that denominator; Data-in-Motion's
  ratio inputs were simply never on the title/severity-proxy code paths that were actually broken.
- **Actual mechanism**: a THIRD mechanism, exactly as D-07 explicitly permitted ("Both hypotheses
  may be wrong; a third mechanism is permitted and a negative result on both is a valid, valuable
  outcome") — the finding-title vocabulary split (leg 1) and the severity-proxy structural zero
  (leg 2) described above.

## Decision A, as the operator chose it: extend the existing bridge, not unify the vocabularies

**Chosen:** route every title `_finding_targets()` compares through the existing
`quirk/dashboard/api/finding_title_bridge.py::canonical_cli_title()` translation, with an identity
fallback (`canonical_cli_title(raw_title) or raw_title`) so an untranslated title degrades to its
own literal value rather than raising or silently matching nothing.

**Rationale accepted:**
- Smallest diff — one import, one wrapped comparison at the single shared call site all three
  title-matched counters route through (`evidence.py:511-513`).
- In-repo precedent — `finding_title_bridge.py` already existed and was already the mechanism used
  elsewhere to reconcile the two vocabularies; this extends its established role rather than
  inventing a new mechanism.
- Respects the Phase 202 "DO NOT UNIFY" decision (`schemas.py:126-129`) — the two generators keep
  independent vocabularies; only the scoring consumer gains a translation step.

**Risk explicitly accepted, and its mitigation:** a mapping table is only as good as its coverage.
This repo has been bitten by hand-maintained lists drifting from the real set at least six
documented times (CLAUDE.md's TOOL-01..05 history). The mitigation actually built, not merely
proposed: **`tests/test_evidence_scoring_title_coverage.py`** (`211-04`), a run-time AST/regex
source-scan gate that re-extracts, from installed source at every test run, the exact set of CLI
titles `_finding_targets` looks up and the exact set of titles the CLI generator emits (both the
kwarg form and the `f["title"] = "..."` rewrite form, via two independently-maintained extractors
per the 210-02 anti-pattern of unifying deliberately-independent walkers), and fails in either
direction — a new undispositioned lookup, or a dispositioned title disappearing from the generator
— rather than trusting a hand-written list. Both falsification directions were proven red and
reverted (`211-04-SUMMARY.md`).

## The leg-2 shape, and why the bridge could not fix it

A title bridge cannot repair `legacy_tls_count`, because the defect is not a vocabulary mismatch —
it is a **severity proxy**, and severity is assigned independently by each generator. No mapping
table reconciles "count of LOW findings" across two generators that emit different finding classes
at different severity levels by design.

**Chosen shape:** derive `legacy_tls_count` directly from endpoint TLS fields, via a new shared
predicate `quirk.util.weak_crypto.has_legacy_tls_versions_signal(tls_version,
tls_supported_versions)`, extracted from and now delegated-to by
`findings_evaluator._has_legacy_tls_versions` (a 3-line thin wrapper, so no caller needed to move).
`evidence.py` accumulates the counter directly inside its existing single pass over `endpoint_list`
(`evidence.py:220-242`), and `scoring.py:459` reads
`evidence.get("legacy_tls_count", sev.get("LOW", 0))` — the severity proxy demoted to a
provably-unreachable fallback, guarded the same way `assessable_endpoint_count`'s own fallback is
guarded at `scoring.py:412`.

**Rejected alternatives, and why:**
- **Bridge the severities.** Rejected — severity is a per-generator judgement call (what counts as
  LOW vs MEDIUM), not a vocabulary translation; there is no canonical mapping to bridge, only two
  independent policies.
- **Change the dashboard generator's severities to match the CLI's.** Rejected — this would
  silently violate the Phase 202 "DO NOT UNIFY" boundary from the other side, coupling the two
  generators' severity policy instead of their title strings, and would need to be redone every
  time either generator's severity policy legitimately diverges for a good reason.
- **Leave it and defer.** Rejected — this is exactly the Phase 210 Success Criterion 5 residual
  this phase exists to close; deferring it would ship Phase 214's tag with two different headline
  scores, which D-09 explicitly names as the outcome to avoid.

**The proxy was also wrong on the CLI side, on its own terms**, independent of the dashboard defect:
`sev.get("LOW", 0)` counts every LOW-severity finding of ANY class as if it were a legacy-TLS
finding, not just legacy-TLS ones. Any new LOW-severity finding class added to the CLI generator in
the future would have silently inflated `legacy_tls_count` and, downstream, the Modern TLS penalty,
with no test able to distinguish "more legacy TLS" from "more of some unrelated LOW finding." The
endpoint-derived counter removes this latent defect on the CLI side too, not only the dashboard
structural-zero.

## The residual: the one unbridgeable title

One CLI finding title, **`"HTTP on TLS-designated port"`** (`findings_evaluator.py:433`,
consumed at `evidence.py:512`), has **no dashboard-side emission site at all** — confirmed by grep
across `quirk/dashboard/api/routes/scan.py` for any title naming "TLS-design" or "designated"
anything, zero hits. It is dispositioned `unbridgeable-latent-divergence` in
`quirk/dashboard/api/finding_title_bridge.py::SCORING_TITLE_DISPOSITIONS` (`211-04`), with the
residual tracked at
`.planning/todos/pending/211-http-on-tls-designated-port-has-no-dashboard-equivalent.md`.

**Tag-blocking verdict: NO.** It measures 0 on the reference estate today (no plaintext HTTP was
found on a TLS-designated port in either the 210 baseline or the 211-05 live re-scan), so it is not
a currently-wrong number the way the two active legs were. It **must be disclosed** in Phase 214's
release notes, because the defect mechanism — a title-matched counter with no cross-generator
coverage guarantee — is identical to the two legs this decision fixes, just currently dormant. The
coverage gate (`211-04`) will fail loudly the moment either side's vocabulary shifts in a way that
makes this title newly reachable or newly unreachable, so the dormancy is monitored, not merely
assumed.

## What this decision is not

This record does **not** touch, extend, or reopen `999.113-denominator-semantics.md`'s three
denominators (`cert_denom`, `endpoint_denom`, `domain_denom`) — those are proven correct by
citation and live measurement (see `211-DENOM-EVIDENCE.md`, `211-01-SUMMARY.md`), not by any change
in this plan or its predecessors (211-02/211-03). D-01 in `211-CONTEXT.md` explicitly forbids
re-implementing them, and no task in `211-02`/`211-03`/`211-04` touched `scoring.py:404-422`.

## Acceptance evidence (D-08)

**A green unit test alone was explicitly insufficient** (per D-08 and this repo's own Phase 210
lesson: a cross-surface `A == B` unit assertion passed once while the shared code path was
sabotaged). The acceptance evidence is a fresh **live** multihost scan, read from both pipelines
independently, recorded in full in `.planning/phases/211-denominator-correctness/211-LIVE-MEASUREMENT.md`:

- **`scan_run_id: 2026-09-28T13:16:55.319715+00:00`**
- Headline score: **report 18/100, dashboard 18/100 — EQUAL.**
- All six subscores matched exactly (Hygiene 17/25, Modern TLS 20/25, Identity 9/25, Agility 25/25,
  Data at Rest 22/25, Data in Motion 13/25), the cap reason string matched verbatim, CRITICAL 6=6,
  certificates 20=20.
- Cross-checked by an independent DB re-derivation (not a second read of the same JSON): 13 of 13
  evidence counters matched exactly, including `legacy_tls_count` (1=1) and `plaintext_http_count`
  (10=10) — the two counters this decision's fixes directly targeted.

**Non-vacuity of the equality is itself evidenced, not assumed** (per this project's standing
suspicion of bare `A == B` claims): the identical comparison method, on the identical two
surfaces, read **17 vs 18 — NOT EQUAL** eleven hours earlier at the Phase 210 baseline
(`scan_run_id 2026-09-28T01:41:30.088508+00:00`) — proving the instrument detects a real
difference when one exists, rather than always reading "equal." Separately, the headline is
monotone in the pre-cap computed score, not a flat cap value: Scan A's cap reason was "limited to
18 (**computed 71**)" while a second same-session scan at a different port width read "limited to
20 (**computed 78**)" — so an equal headline between report and dashboard on Scan A implies
near-equal COMPUTED values on both sides, not merely a coincidentally-shared cap floor.

## The score movement

Phase 214 freezes whatever number ships, so this client-visible score change belongs in this
ledger, not only in a plan SUMMARY.

| | Before (Phase 210 baseline, `scan_run_id 2026-09-28T01:41:30`) | After (`211-05`, `scan_run_id 2026-09-28T13:16:55`) |
|---|---|---|
| Report headline | 17/100 | 18/100 |
| Dashboard headline | 18/100 | 18/100 |
| Hygiene (report/dashboard) | 17/17 | 17/17 |
| Modern TLS (report/dashboard) | 17/21 | 20/20 |

The report side moved from 17 to 18 (the inflated `sev.get("LOW", 0)` proxy previously
over-penalizing Modern TLS on the report side by coincidence of matching a LOW finding that is not
actually the legacy-TLS condition being measured, corrected once `legacy_tls_count` became
endpoint-derived). Equality, not the specific pre-fix value 17, is this decision's acceptance
criterion — the pre-fix report-side 17 was itself never a correct number, only a number that
happened to differ from the dashboard's.

**Note:** the two `scan_run_id`s above are drawn from different sessions (Phase 210's baseline scan
and 211-05's live re-scan against a freshly rebuilt lab), so this before/after table compares two
different scan runs against the same estate, not a single run re-scored — consistent with how the
divergence was originally discovered (Phase 210) and then closed (Phase 211).

## If NOT EQUAL — not applicable here

211-05 measured **EQUAL**. This clause is retained per this plan's own instruction: had the live
measurement come back NOT EQUAL, this record would need to say so plainly and name a residual owner
phase rather than imply resolution. It does not apply — the residual named above (the one
unbridgeable title) is the only surviving gap, and it is explicitly NOT part of the EQUAL/NOT EQUAL
acceptance criterion because it measures 0 on the reference estate.
