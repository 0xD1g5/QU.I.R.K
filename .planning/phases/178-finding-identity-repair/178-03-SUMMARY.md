---
phase: 178-finding-identity-repair
plan: 03
subsystem: testing
tags: [pytest, fingerprint, ticketing, findings, identity, documentation]

# Dependency graph
requires: []
provides:
  - "docs/reviews/178-derivation-path-divergence.md — the written, bounded divergence record required by CONTEXT.md decision 12 (D-178-A wording, D-178-B detection-coverage)"
  - "tests/test_finding_engine_parity.py::TestIdentityParity — fingerprint-equality agreement tests + machine-readable _KNOWN_IDENTITY_DIVERGENCES allowlist"
affects: [179, 180, 181]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Machine-readable allowlist (_KNOWN_IDENTITY_DIVERGENCES frozenset) cross-references a prose divergence document by ID (D-178-A) so drift between code and doc is itself test-detectable."
    - "Fingerprint-equality identity contract is deliberately narrower than full field parity — proves TicketingChannel.compute_fingerprint agrees, not that every finding attribute matches, to avoid re-implementing the excluded RVW-002 merge."

key-files:
  created:
    - docs/reviews/178-derivation-path-divergence.md
  modified:
    - tests/test_finding_engine_parity.py

key-decisions:
  - "Measured reality confirmed the planner's interfaces exactly: 2 of 3 shared conditions (undersized RSA, self-signed) are byte-identical and therefore already fingerprint-equal with zero code change; only the expired-certificate title diverges."
  - "Did not touch quirk/engine/findings_evaluator.py or quirk/dashboard/api/routes/scan.py — the divergence is reported and bounded (allowlisted + documented), not silently reconciled, per CONTEXT.md decision 12."
  - "Kept D-178-A (wording divergence, both paths detect the condition, titles differ) and D-178-B (detection-coverage gap, dashboard never detects quantum-vulnerable-RSA at all) as two distinct, separately labeled findings rather than merging them into one entry — conflating them would misrepresent a coverage gap as an identity failure."
  - "Named two candidate resolutions for D-178-A in the divergence doc (align dashboard literal to report literal, or add a cross-engine synonym alias distinct from TITLE_PREFIX_ALIASES) without applying either — resolution is a future-phase decision."

requirements-completed: []  # IDENT-03 spans plans 03/06/07 — NOT closed by this plan. Do not mark complete.

# Metrics
duration: 25min
completed: 2026-09-02
---

# Phase 178 Plan 03: Derivation-Path Identity Agreement Summary

**Proved the two findings-derivation paths (report engine, dashboard engine) agree on fingerprint identity for 2 of 3 shared conditions with zero code change, and bounded the one real divergence — an expired-certificate title mismatch — in a written record plus a machine-readable allowlist guard that has been demonstrated to fail RED when the allowlist is wrong.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-02 (session start)
- **Completed:** 2026-09-02
- **Tasks:** 2 completed
- **Files modified:** 1 new (`docs/reviews/178-derivation-path-divergence.md`), 1 modified (`tests/test_finding_engine_parity.py`)

## Accomplishments

- **Task 1 — `docs/reviews/178-derivation-path-divergence.md` (121 lines).** Documents scope
  (fingerprint-equality only, RVW-002 merge remains excluded), method (three fixture endpoints,
  `TicketingChannel.compute_fingerprint`), the 2-of-3 agreement result, D-178-A (wording
  divergence: `"TLS certificate expired"` at `quirk/engine/findings_evaluator.py:593` vs.
  `"Certificate expired"` at `quirk/dashboard/api/routes/scan.py:185`, with operator-facing dedup
  consequence and two named candidate resolutions), D-178-B (detection-coverage gap: the report
  emits `"TLS certificate uses quantum-vulnerable RSA key"` on 10.0.0.2 and 10.0.0.3, the
  dashboard emits it on neither — a coverage gap, not an identity failure), enforcement
  (cross-references the test file's allowlist), and status (`open — bounded, carried into the
  v5.18 backlog`).
- **Task 2 — `tests/test_finding_engine_parity.py::TestIdentityParity`** (3 new tests, GREEN on
  first run as specified):
  - `test_shared_condition_titles_yield_identical_fingerprints` — proves the undersized-RSA and
    self-signed conditions fingerprint identically across both paths.
  - `test_expired_certificate_divergence_is_bounded_not_silent` — proves the D-178-A pair
    fingerprints differently AND is present in `_KNOWN_IDENTITY_DIVERGENCES`.
  - `test_no_unbounded_identity_divergence` — catch-all guard: any shared-condition fingerprint
    mismatch not on the allowlist fails the suite.
  - Added `_SHARED_CONDITION_NEEDLES`, `_KNOWN_IDENTITY_DIVERGENCES` (module-level, one entry:
    `("TLS certificate expired", "Certificate expired")`, cross-referencing D-178-A and the
    divergence doc path), and a `_title_for()` helper alongside the existing `_severity_for()`.
- **Test counts:** `tests/test_finding_engine_parity.py` went from 6 passed (baseline) to
  **9 passed, 0 failed**. `TestIdentityParity` alone: **3 passed**.
- **Negative control (mandatory, executed and recorded verbatim):** temporarily set
  `_KNOWN_IDENTITY_DIVERGENCES = frozenset()` and reran the file. Result: **3 failed, 6 passed**
  — all three `TestIdentityParity` tests failed, with `test_no_unbounded_identity_divergence`'s
  assertion naming the offending pair exactly:
  ```
  AssertionError: IDENT-03: unbounded identity divergence(s) found — add to
  _KNOWN_IDENTITY_DIVERGENCES and docs/reviews/178-derivation-path-divergence.md, or fix the
  underlying titles: [('10.0.0.3', 'TLS certificate expired', 'Certificate expired')]
  ```
  Restored the allowlist immediately after; the suite returned to 9 passed, 0 failed. This proves
  the guard is a real guard, not a tautology.

## Measured Result (load-bearing, matches the planner's INTERFACES exactly)

| Condition | Report title | Dashboard title | Fingerprint agreement |
|---|---|---|---|
| undersized RSA (10.0.0.1:443) | `TLS certificate uses undersized RSA key` | `TLS certificate uses undersized RSA key` | equal — no code change needed |
| self-signed (10.0.0.2:443) | `TLS certificate is self-signed` | `TLS certificate is self-signed` | equal — no code change needed |
| expired cert (10.0.0.3:443) | `TLS certificate expired` | `Certificate expired` | **differs — D-178-A, bounded not fixed** |
| quantum-vulnerable RSA (10.0.0.2/3:443) | `TLS certificate uses quantum-vulnerable RSA key` | (not emitted) | not comparable — **D-178-B, coverage gap** |

## Deviations from Plan

None — plan executed exactly as written. The measured 2-of-3 agreement matched the planner's
pre-measured INTERFACES block exactly; no adjustment to the allowlist or the divergence doc's
conclusions was needed.

## Verification

```
$ .venv/bin/pytest tests/test_finding_engine_parity.py -q
.........                                                                [100%]
9 passed in 0.56s

$ .venv/bin/pytest "tests/test_finding_engine_parity.py::TestIdentityParity" -q
...                                                                      [100%]
3 passed in 0.37s
```

`git diff --name-only` across both commits: `docs/reviews/178-derivation-path-divergence.md`
(new) and `tests/test_finding_engine_parity.py` (modified) only. Neither
`quirk/engine/findings_evaluator.py` nor `quirk/dashboard/api/routes/scan.py` was touched.

## What This Does NOT Do

- Does not merge the two derivation paths (RVW-002, excluded since v5.16).
- Does not pick a winner between `"TLS certificate expired"` and `"Certificate expired"` — two
  candidate resolutions are named in the divergence doc for a future phase.
- Does not add quantum-vulnerable-RSA detection to the dashboard path (D-178-B) — recorded as a
  coverage gap, not resolved.
- Does not mark IDENT-03 complete — IDENT-03 spans plans 03/06/07; `requirements mark-complete`
  was intentionally not invoked (see CLAUDE.md / memory: over-flipping multi-phase requirements
  is a known repo gotcha).

## Self-Check: PASSED

- `docs/reviews/178-derivation-path-divergence.md` — FOUND (121 lines, contains `D-178-A` x5,
  `D-178-B` x4, `TLS certificate expired` x3, `RVW-002` x1).
- `tests/test_finding_engine_parity.py` — FOUND, contains `_KNOWN_IDENTITY_DIVERGENCES` x7,
  `178-derivation-path-divergence` x6, `compute_fingerprint` (imported and called).
- Commit `f5cdf6e3` — FOUND in `git log --oneline`.
- Commit `d8996cc7` — FOUND in `git log --oneline`.
