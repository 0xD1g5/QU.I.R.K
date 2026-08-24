# Third-Party Functional Review of QU.I.R.K. — Review Charter

**Date:** 2026-08-24
**Reviewed version:** v5.15 Lifecycle Tail Drain (in progress), HEAD `49f9094`
**Reviewer posture:** Independent third party. No prior assumption that any documented
claim is true.
**Mandate:** Determine whether the shipped code performs as defined in the project's
development documents, and produce a trackable action plan for every gap found.

---

## 1. Mandate and Boundaries

### In scope

- All 460 unique requirement IDs across 26 archived milestone requirement documents
  plus the active `.planning/REQUIREMENTS.md`.
- The Python backend (`quirk/`), the React dashboard (`src/dashboard/`), the CLI, the
  report generators, and the FastAPI surface.
- The chaos lab (`quantum-chaos-enterprise-lab/`) and its expected-results oracles.
- Frontend behaviour verified by driving a real browser, not only by unit tests.

### Out of scope — deliberate, stated up front

- **No fixes.** This engagement produces findings and an action plan. Not a single
  defect is repaired as part of it, including trivial ones. Remediation is a separate
  decision for the project owner.
- **No harness construction.** Building the ongoing automated verification layer is a
  follow-on engagement. The Pass 1 analysis script is throwaway review tooling written
  to a scratchpad, not product code, and is not committed to the repository.
- Security penetration testing, performance benchmarking, and dependency CVE auditing.
  Each is a distinct discipline and none is what "does it work as documented" asks.

---

## 2. Source-of-Truth Hierarchy

When documents disagree with each other, the reviewer resolves in this order. A
disagreement between any two of these is itself a reportable finding.

1. `.planning/REQUIREMENTS.md` and `.planning/milestones/*-REQUIREMENTS.md` — what the
   product promised to do.
2. `docs/UAT-SERIES.md` — the project's own declared gating document; what it claims
   was proven and how.
3. `.planning/ROADMAP.md` and `.planning/milestones/*-ROADMAP.md` — which phase owned
   which requirement.
4. Phase artifacts under `.planning/milestones/*-phases/**/` — `PLAN.md`, `SUMMARY.md`,
   `VERIFICATION.md`.
5. User-facing documentation under `docs/` — what a customer is told the product does.
6. `CLAUDE.md` — project-specific process rules that are themselves auditable
   (staleness cadences, chaos-lab maintenance, per-phase documentation checklist).

The code is never a source of truth about intent. Where code and documents disagree,
the document defines the requirement and the code is the thing under review.

---

## 3. Evidence Model

The project records verification evidence unevenly across its history. Measured
directly at the start of this review:

| Evidence source | Measured coverage | Strength |
|---|---|---|
| `SUMMARY.md` frontmatter `requirements-completed:` + `key-files:` | 133 of 491 summaries, covering 107 of 460 requirements | **A — strongest.** Names exact implementation and test files. |
| `docs/UAT-SERIES.md` "Closes XXX-NN" declarations | Recent milestones (v5.7 onward) | **B.** Names a UAT case, not a test file. |
| `*-ROADMAP.md` phase-to-requirement mapping | All 27 milestones | **C.** Phase-level only. |
| Requirement ID grepped inside `tests/` | 89 of 369 test files (24%) | **D — weak.** High false-negative rate. |

The structured-frontmatter convention began in the v5.x era. Approximately 350 older
requirements therefore have no machine-readable link to a test. **This is a finding
about verification debt, not an obstacle to the review, and not in itself a claim that
those requirements are broken.**

Consequently every verdict in this review is stamped with the evidence tier it rests
on, so any individual call can be challenged on its evidence rather than on its
conclusion.

---

## 4. Method

### Pass 1 — Mechanical traceability sweep

Build one row per requirement ID:

```
req_id | milestone | doc_claim_state | phase | evidence_tier | named_files |
files_still_exist | uat_case | uat_result | verdict
```

Verdicts, assigned from the **best available** evidence tier:

| Verdict | Meaning |
|---|---|
| `PROVEN` | Named test files exist, contain tests, and pass. |
| `STALE-EVIDENCE` | A summary claims test files that no longer exist, or that no longer contain matching tests. Highest-value finding class in a codebase with 161 phases of churn. |
| `UAT-ONLY` | A UAT case closes it; no test file is traceable. |
| `PHASE-ONLY` | Only a roadmap phase mapping exists. |
| `UNTRACED` | Marked complete with no evidence at any tier. |
| `HUMAN-PENDING` | Among the 28 items `UAT-SERIES.md` marks as requiring human eyes. |
| `OPEN` | Legitimately incomplete and honestly marked so. |
| `ORPHAN` | A UAT case or phase references a requirement ID that no requirements document defines. |

The purpose of Pass 1 is to separate **verified working** from **asserted working**.
`UNTRACED` means "no one can show me the proof", never "this is broken".

### Pass 2 — Hands-on functional verification

Everything in this pass is actually executed, and actual output is recorded — including
failures. No result is tuned until it is green.

**Backend**
- Full `pytest` run; record real pass / fail / skip / error counts.
- Audit `tests/skip_registry.py` — deliberately skipped tests are where "the suite
  passes" claims most often hide unproven behaviour.
- Targeted re-run of every test file named by a Tier-A requirement.
- Verify the four CI-gated staleness catalogs named in `CLAUDE.md` are within their
  declared cadences.

**Frontend**
- `npm run lint`, `npm test`, `npm run a11y:check`, `npm run e2e:smoke`.
- Confirm the committed `src/dashboard/output` bundle matches a fresh `npm run build`.
  A stale committed bundle would mean the E2E suite validates a frontend that is not
  the one shipped.

**Full-stack, driven as a user**
- Boot `quirk serve` and drive the application in a real Chrome browser across all 15
  SPA routes.
- Verify the core value claim in `PROJECT.md` end to end: run a scan, validate the CBOM
  against the CycloneDX schema, obtain a readiness score, export the report, and
  confirm the numbers rendered in the dashboard match the numbers the API returned.
- Cross-check dashboard-displayed values against their API responses. The existing E2E
  smoke test proves pages render without console errors; it does not prove the values
  are correct. That gap is the target here.

**Chaos lab**
- With Docker running, exercise lab profiles against their `expected_results_*.md`
  oracles.
- Audit the `CLAUDE.md` chaos-lab maintenance rule: every profile in
  `docker-compose.yml` must appear in `lab.sh`'s `ALL_PROFILES`.

**Code reading**
- For each flagged requirement, read the implementation and judge it against the quoted
  document text.

### Pass 3 — Findings report and action plan

Two deliverables, because they serve different readers.

**`docs/reviews/2026-08-24-functional-review-findings.md`** — the reviewer's report.
Every finding carries:

- A stable finding ID (`RVW-001`, …) that survives re-review.
- Severity: `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` / `OBSERVATION`.
- The affected requirement ID(s) and the **verbatim quoted** document claim.
- What the code actually does.
- The exact command or artifact that constitutes evidence.
- Evidence tier and verdict.

**`docs/reviews/2026-08-24-functional-review-action-plan.md`** — the trackable plan.
A checkbox table, one row per finding, ordered by severity, with columns for finding ID,
severity, one-line description, affected requirement, suggested remediation, effort
estimate, and status. Designed to be worked through and checked off directly, and to be
promotable into `.planning/` as a milestone's requirement set without rewriting.

The findings report is additionally published as an Artifact for sharing.

Both documents carry an explicit **Limitations** section stating what was not verified
and why.

---

## 5. Reporting Standards

- Every claim of a defect is accompanied by reproducible evidence. No finding rests on
  reading code alone unless it is labelled `OBSERVATION`.
- Severity reflects impact on the documented promise, not on code aesthetics.
- Where the reviewer cannot determine whether behaviour is correct, the finding says so
  rather than guessing.
- Passing results are reported as prominently as failures. A review that lists only
  problems misrepresents a codebase with 3,220 test files and an a11y baseline harness.
- The 28 `HUMAN-UAT` items are enumerated explicitly, not folded into prose.

---

## 6. Known Limitations of This Review

1. The review is conducted at a single commit. Behaviour on other branches or platforms
   (notably Windows, which has its own documented packaging gotchas) is not assessed.
2. Cloud connector paths (AWS, Azure, GCP KMS) require live credentials and are
   verified only to the extent their tests and mocks allow.
3. Evidence tiering involves reviewer judgment. Every verdict states its tier so it can
   be independently challenged.
4. Requirements from milestones predating the structured-frontmatter convention are
   assessed on weaker evidence, and this is recorded per finding rather than averaged
   away.
