# Phase 37: Gap Closure and v4.4.0 Release - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 37-gap-closure-and-v4-4-0-release
**Areas discussed:** [motion] extras structure, INFRA-03 Nyquist coverage scope, VALIDATION.md backfill strategy, Release artifacts beyond version bump

---

## [motion] extras structure

| Option | Description | Selected |
|--------|-------------|----------|
| Meta-extra | motion pulls in flat sub-extras (email, broker, kafka). pip install quirk[motion] gets everything. | ✓ |
| Flat — all deps inline in motion | Every direct dep listed in motion; drop the kafka sub-extra. | |
| Per-protocol only — no motion bundle | Drop motion entirely; expose only [email], [broker], [kafka]. | |

**User's choice:** Meta-extra (Recommended).
**Notes:** Meta-extra preserves both single happy-path install and granular per-protocol installs. Mirrors Python ecosystem norms.

| Option | Description | Selected |
|--------|-------------|----------|
| Whatever scanners actually import | Researcher greps scanner files for non-stdlib imports; pin those. | ✓ |
| Match Phase 32/33 plan-declared deps | SUMMARY.md tech-stack.added is the canonical list. | |
| Empty (motion = []) | Scanners use stdlib only; document why. | |

**User's choice:** Whatever scanners actually import.
**Notes:** Ground truth lives in the imports, not in plan documents that might have drifted.

---

## INFRA-03 Nyquist coverage scope

| Option | Description | Selected |
|--------|-------------|----------|
| Audit existing, add only what's missing | Build a coverage matrix; write only the missing scenarios. | |
| Write all 18 fresh in a phase-37 test module | New tests/test_infra03_nyquist_coverage.py with 18 explicit cases. | ✓ |
| Document mapping only — no new tests | Map existing test names in a coverage doc. | |

**User's choice:** Write all 18 fresh in a phase-37 test module.
**Notes:** Single auditable artifact for INFRA-03 outweighs the duplication cost.

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in each phase's VALIDATION.md | Per-phase 'Nyquist scenarios' subsection pointing at test names. | ✓ |
| One central doc in phase 37 | 37-INFRA03-COVERAGE.md with the full matrix. | |
| Both — per-phase plus a phase-37 rollup | Per-phase authoritative + phase-37 index. | |

**User's choice:** Inline in each phase's VALIDATION.md (Recommended).
**Notes:** Each phase owns its audit trail. Phase 37 verifies the trail is complete.

---

## VALIDATION.md backfill strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Re-run plan-checker per phase | Authoritative validator output; fix gaps before flipping flags. | ✓ |
| Hand-write VALIDATION.md from current state | Faster but no independent verification. | |
| Re-run for missing (35), hand-edit flag flips for 34/36 | Pragmatic middle ground. | |

**User's choice:** Re-run plan-checker per phase (Recommended).
**Notes:** No rubber-stamping. Honest audit trail over speed.

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 36 VERIFICATION.md + UAT.md sign-off | Trust existing artifacts plus a clean test run. | ✓ |
| Re-run UAT-36-01..05 in phase 37 | Treat UAT as not transferable across phases. | |
| Just flip it — phase was approved | Trust the roadmap status. | |

**User's choice:** Phase 36 VERIFICATION.md says approved + UAT.md sign-off (Recommended).
**Notes:** UAT artifacts already exist and were approved on 2026-04-28. Re-running risks environment drift.

---

## Release artifacts beyond version bump

| Option | Description | Selected |
|--------|-------------|----------|
| CHANGELOG.md entry for 4.4.0 | Append 4.4.0 section sourced from phase SUMMARY.md files. | ✓ |
| docs/release-notes/4.4.0.md | Standalone narrative release-notes doc. | ✓ |
| Git tag v4.4.0 | Create annotated tag in this phase. | |
| quirk --version output verification test | tests/test_version.py asserting __version__ and CLI string. | ✓ |

**User's choice:** CHANGELOG entry + release notes doc + version test. Git tag deferred.
**Notes:** Git tag belongs to milestone close, not feature close.

| Option | Description | Selected |
|--------|-------------|----------|
| Stop after VALIDATION + UAT sign-off | Phase 37 atomic; milestone close is separate. | ✓ |
| Auto-trigger /gsd-complete-milestone | One-shot release in the final wave. | |

**User's choice:** Stop after VALIDATION + UAT sign-off (Recommended).
**Notes:** Preserves the human gate for milestone-level review.

---

## Claude's Discretion

- Plan partitioning (single plan vs. multi-wave structure) — planner decides; each plan must remain atomic and reversible.
- Exact prose of CHANGELOG entries and release notes — sourced from phase SUMMARY.md files; framed for end-user audience by planner/executor.
- Order of operations within Wave 1 — version bump (INFRA-01) and extras structure (INFRA-02) are independent.

## Deferred Ideas

- Git tag v4.4.0 → milestone close.
- /gsd-complete-milestone invocation → manual user step after phase 37.
- Centralized INFRA-03 coverage rollup doc → per-phase inline tables chosen instead.
- Re-running manual UAT-36 cases → trust existing UAT.md sign-off; revisit only if environment-drift becomes a concern.
