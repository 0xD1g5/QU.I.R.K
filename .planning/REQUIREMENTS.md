# Requirements: QU.I.R.K. — v5.26 Accessibility & Instrument Truth

**Defined:** 2026-09-28
**Core Value:** A consulting-grade cryptographic inventory whose findings a consultant can hand to a
client without qualification — which includes the dashboard being usable by the people who have to
read it, and the gates that police it actually measuring what they claim.

**Milestone goal:** Drain the dashboard's WCAG-AA badge-contrast debt as one unit, and repair the
instruments that let 45 real violations sit behind three green gates — including the CI gates that
report green on a required job without measuring it.

**This is a reopening of `BACK-A11Y-01`** (filed 2026-05-22, v5.0 Phase 87; lost at that milestone's
archive; rediscovered a **third** time on 2026-09-28 by a red CI gate rather than by anyone reading
the ledger). The reopening is recorded deliberately: a milestone that closes this debt without
recording why it was invisible has scheduled the fourth rediscovery.

**Operator scoping constraint (2026-09-28):** worked **as one unit** — explicitly not drained
piecemeal across phases that each happen to touch a page.

**Sequencing constraint:** the RATCHET category lands **first**. It fixes nothing; it converts an
unbounded, invisible liability into a drainable number, and every FIX requirement is verified
against it.

---

## Boundary verifications — read these before planning

Three checks run at the milestone boundary (2026-09-28) against live source, not against
`HORIZON.md`'s prose. Each makes the recorded sizing **optimistic rather than wrong**.

1. **`auditedFiles()` exists twice.** `src/dashboard/src/components/__tests__/hardcoded-color-audit.test.tsx:86`
   and `theme-token-vocabulary.test.ts:41`, the second annotated *"Copied verbatim from
   hardcoded-color-audit.test.tsx's auditedFiles()."* It returns `src/pages/*.tsx` (26) +
   `components/sidebar.tsx` = **27 of 76** non-test `.tsx` files. Widening it means widening two
   hand-synced copies — the enumeration-vs-derivation defect living inside the gate built to catch
   enumeration defects. This is why RATCHET-03 says *derive once and delete the copy* rather than
   *widen the glob*.

2. **`run-a11y.mjs` has no theme dimension at all.** Its `VARIANT` is a *fixture* variant
   (`default` / `empty` / `loading`); `data-theme`, `.dark`, `classList` and `prefers-color-scheme`
   all return **zero** hits in that file. HORIZON's "sweeps the dark variant only" is true in effect
   but reads like a flag is mis-set. There is no flag. HARNESS-01 is new harness capability — size
   it at the top of M, not the bottom.

3. **The 29-site L-risk is confirmed, not hypothetical, and the obvious fix is wrong.**
   `src/index.css` already carries a Phase 213 "light overrides" block that **deepened**
   `--status-warning` (50% → 32%, 4.84:1 on white) and `--chart-tls` (68% → 40%, 6.26:1)
   specifically so they pass as *text on a light surface*. That is precisely why the same tokens now
   fail as *badge backgrounds with black text* (4.34 and 3.35). Phase 213 optimised the text use
   case and the badge use case was collateral — so simply reverting those values would re-break what
   213 fixed. FIX-02's spike exists to settle whether the answer is a new badge-specific token, and
   it must run before any bulk edit.

---

## v5.26 Requirements

### Instrument Ratchet

- [ ] **RATCHET-01**: A contrast guard covers every dashboard page and both themes, deriving its
      badge-pair set from source at run time rather than from a hand-maintained list
- [ ] **RATCHET-02**: The 45 known failures are recorded as a shrink-only baseline — a new failure
      fails CI, a fixed one requires a baseline update, and the count can never silently grow
- [ ] **RATCHET-03**: `auditedFiles()` is derived once and covers all 76 non-test `.tsx` files; the
      verbatim copy in `theme-token-vocabulary.test.ts` is deleted, not re-synced
- [ ] **RATCHET-04**: The guard proves it can fail — a mutation probe shows it going red on an
      injected sub-AA pair, demonstrated rather than asserted

### A11y Harness

- [ ] **HARNESS-01**: `run-a11y.mjs` sweeps both light and dark themes, with per-theme baselines
- [ ] **HARNESS-02**: The axe sweep no longer reports PASS on a route whose fixture omits the failing
      element — `/certificates` and `/hardware` are the proof cases
- [ ] **HARNESS-03**: The `data-at-rest` baseline's render-dependent rule uses a tolerance instead of
      an exact count, and stops disagreeing between macOS and CI

### Contrast Violations

- [ ] **FIX-01**: The 11 zero-design-input swaps are applied — 7 × `--risk-badge-high` + white
      (2.85) to its existing `-foreground` sibling (5.97), 4 × `--qs-node-safe` + white (2.30) to
      `--status-safe-deep` (4.83/6.79)
- [ ] **FIX-02**: A spike on 3–4 of the 29 `text-black` sites classifies each as badge-background vs
      text-on-white use and returns a recorded plan shape before any bulk edit
- [ ] **FIX-03**: The 29 sites reach AA in both themes without regressing the text-on-white contrast
      Phase 213 established for `--status-warning` and `--chart-tls`
- [ ] **FIX-04**: The 5 genuine design calls are resolved with operator visual review, as 213-09 did
      — not auto-picked (`--destructive` + white 3.82 dark ×2, `--quantum-safe` + paired fg 3.87
      light ×2, `--badge-modbus` + white 2.86 dark ×1)
- [ ] **FIX-05**: Zero badge pair anywhere in the dashboard sits below 4.5:1 in either theme,
      verified by RATCHET-01 reporting an empty baseline

### Keyboard Access

- [ ] **KBD-01**: A keyboard user can scroll any table region independently —
      `components/ui/table.tsx` gains the `tabIndex`/`role` its own accepted-violation justification
      says it needs, and the `scrollable-region-focusable` acceptance is withdrawn rather than
      renewed

### CI Instrument Truth

- [ ] **CITRUTH-01**: `tests/test_uat_disposition_integrity.py::test_vitest_substitute_nodes_pass` is
      diagnosed and stabilised — the 14 nodes pass batched, repeatedly, not just standalone
- [ ] **CITRUTH-02**: `Python CI` is green on `main`, with
      `test_chaos_lab_idempotency[multihost]`/`[storage-s3]` either fixed or honestly skipped on
      unavailable-registry rather than failing
- [ ] **CITRUTH-03**: Phase verification consults its branch's CI state, so a phase cannot verify
      `passed` while its branch is red — closing the v5.25 gap where five phases verified `passed`
      and a release was tagged and published over a failing `main`

---

## Future Requirements

Deferred, tracked, not in this roadmap.

### Accessibility beyond contrast

- **A11Y-FUTURE-01**: Non-contrast axe rule classes not already accepted (heading order, landmark
  structure, form labelling) swept and baselined
- **A11Y-FUTURE-02**: Screen-reader walkthrough of the primary consulting deliverable path
  (scan → findings → roadmap → export)

### Score correctness tail (v5.25 filed, not fixed)

- **SCORE-FUTURE-01**: `readiness-score-denominator-is-probe-count-not-assessable-endpoints`
- **SCORE-FUTURE-02**: `p2b-healthy-endpoints-dilute-the-readiness-score`
- **SCORE-FUTURE-03**: `score-drivers-leak-from-domains-excluded-from-the-headline`
- **SCORE-FUTURE-04**: `saml-one-certificate-counted-twice-c-and-d`
- **SCORE-FUTURE-05**: `cli-dashboard-score-divergence-same-scan`
- **SCORE-FUTURE-06**: `r5-ladder-fixture-is-not-the-measurement-it-claims`
- **SCORE-FUTURE-07**: `211-http-on-tls-designated-port-has-no-dashboard-equivalent` (XSURF-04's
  ungated third divergence class)

---

## Out of Scope

Explicitly excluded for v5.26. Stated so each is deferred rather than forgotten.

| Feature | Reason |
|---------|--------|
| HORIZON Candidate A — Migration Execution | Its 3x sizing question (QUIRK feature vs Jira/ServiceNow deepening on the Phase 101–105 surface) is still unresolved; needs a shaping conversation first |
| HORIZON Candidate B — Detection breadth | Still no demand signal; HORIZON's own rule is not to open it without one |
| `999.104` PARITY-T4 — dashboard load/edit/save of `config.yaml` | Capability work; needs its own phase, unrelated to this milestone's thesis |
| `999.107` — Exposure Map Tier B | Build when an engagement asks for operator-declared reachability |
| `999.105` — customizable reporting engine | P3; three-tier shape still only in its IDEA.md |
| `999.110` — multi-host chaos-lab topology | P2 lab infrastructure, orthogonal |
| `999.111` — drawer vs roadmap score-lift disagreement | P2, operator-accepted blocker at v5.23 close; pinned by a characterization test |
| `999.112` — LIFT-05 equality holds only for unmodified templates | P3 |
| `999.116` — Windows-sensor boilerplate in 8 older release bodies | Release-history cosmetics, not a gate |
| The 7 score-correctness todos | Listed under Future Requirements; a scoring cycle, not an a11y one |
| SaaS multi-tenancy | Parked since v5.4 pending a business-model signal |

---

## Traceability

Filled during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RATCHET-01 | TBD | Pending |
| RATCHET-02 | TBD | Pending |
| RATCHET-03 | TBD | Pending |
| RATCHET-04 | TBD | Pending |
| HARNESS-01 | TBD | Pending |
| HARNESS-02 | TBD | Pending |
| HARNESS-03 | TBD | Pending |
| FIX-01 | TBD | Pending |
| FIX-02 | TBD | Pending |
| FIX-03 | TBD | Pending |
| FIX-04 | TBD | Pending |
| FIX-05 | TBD | Pending |
| KBD-01 | TBD | Pending |
| CITRUTH-01 | TBD | Pending |
| CITRUTH-02 | TBD | Pending |
| CITRUTH-03 | TBD | Pending |
