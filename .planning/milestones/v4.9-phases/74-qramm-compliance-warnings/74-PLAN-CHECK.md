# Phase 74 Plan-Check

**Date:** 2026-05-15
**Plans checked:** 74-01, 74-02, 74-03
**Verdict:** PASSED

---

## Coverage Matrix

### Decision Coverage (D-01..D-12, D-14)

| Decision | Plan(s) | Site | Status |
|----------|---------|------|--------|
| D-01 (WR-02 fail-loud ValueError + `practice_id` param) | 74-01 Task 1+2 | `scoring.py::compute_practice_score` | COVERED — exact error string `out of range [0, 4]` in truths + acceptance grep |
| D-02 (WR-04 discovery_factor log10 curve) | 74-01 Task 1+2 | `evidence_bridge.py:78-87` via `_discovery_factor` helper | COVERED — log10 formula, `total_endpoints` source per RESEARCH C-1, parametrized curve test |
| D-02a (curve discretion) | 74-01 | log10 default selected | COVERED (discretion exercised) |
| D-03 (WR-05 `vuln_pct=None` + 'Indeterminate' sibling) | 74-01 Task 2 | `scoring.py::_maturity_label` widened to `float \| None`; `evidence_bridge.py` vuln_pct block | COVERED — `if score is None: return "Indeterminate"` arm + sentinel propagation |
| D-04 (WR-06 ≥4.0 reachable) | 74-01 Task 2 | `scoring.py:67` threshold `>= 3.95` | COVERED — path (a) per RESEARCH C-2; parametrized test 3.99 + 4.0 |
| D-05 (WR-01 TZ-safe date compare) | 74-02 Task 2 | `evidence_bridge.py:43-50` invariant comment + `datetime.date.fromisoformat` for any Python-side compare | COVERED — RESEARCH C-3 path (a) with regression test asserting SQL filter symmetry |
| D-06 (WR-03 idempotent UPDATE + WR-07 commit handler) | 74-02 Task 2 | `evidence_bridge.py:114-127` + `db.commit()` wrap | COVERED — pre-query skip + `SQLAlchemyError` wrap with locked log string |
| D-07 (WR-08 AttributeError logged) | 74-02 Task 2 | `operator_context.py:85, 94` | COVERED — narrowed `except AttributeError` + fallback `except Exception: ... raise` (RESEARCH Pitfall 4 / C-7 + user override) |
| D-08 (WR-09 word-boundary + synonyms) | 74-03 Task 2 (commit 1) | `migration_advisor.py` adds `CANONICAL_ALG_SYNONYMS` + `_matches` + word-boundary title checks | COVERED — RESEARCH C-4 path (a); title-driven advisor retained per C-8 |
| D-09 (WR-10 non-keyed string scan) | 74-03 Task 2 (commit 2) | `evidence_bridge.py:165-204` third dict-arm | COVERED — `_matches` reuse pattern per Pitfall 6 |
| D-10 (WR-11 coverage_status) | 74-03 Task 2 (commit 3) | `compliance_map.py` `SCANNER_COVERAGE_STATUS` parallel dict + `qramm.py:598-663` consumer | COVERED — RESEARCH C-5 path (a); rollup skip for pending/n_a + half-weight partial |
| D-10a (rollup partial-weight) | 74-03 Task 2 | half-weight (0.5×) default | COVERED (discretion exercised per D-10a default) |
| D-11 (WR-12 staleness helper) | 74-03 Task 2 (commit 4) | `model_meta.py::is_qramm_model_stale` with nested `QRAMM_MODEL["last_verified"]` | COVERED — RESEARCH C-6; default `today=None` branch; boundary test at 90/91 days |
| D-12 (WR-13 stale TODO removal) | 74-03 Task 3 | `quirk/compliance/__init__.py:3` | COVERED — RESEARCH C-9 + Pitfall 8; no deferred-items.md (target doc exists) |
| D-14 (do-not-touch list) | All 3 plans | guardrails called out per task + grep negation checks | COVERED — `questions.py`, 5-band scale, `tests/test_compliance_freshness.py`, `migration_planner.py` all explicitly excluded; acceptance includes `grep -cE "score >= 4\.0"` == 0 negative check |

**Decision coverage: 14/14 (100%).**

### ROADMAP Success Criteria (3)

| SC | Plan(s) | Status |
|----|---------|--------|
| SC-1 — `compute_practice_score` raises validation error; Practice 1.1 incorporates endpoint count; vuln_pct guarded; ≥4.0 reachable | 74-01 | COVERED via D-01..D-04 |
| SC-2 — Evidence bridge `datetime.date` + TZ-safe; idempotent; commit handled; `attach_context` AttributeError logged | 74-02 | COVERED via D-05..D-07 |
| SC-3 — Migration advisor false positives reduced; `_walk_json_for_alg_strings` extended; coverage disambiguated; `is_qramm_model_stale()` added; stale TODO removed | 74-03 | COVERED via D-08..D-12 |

### Audit Row Coverage (13 WR rows)

| Row | Plan | Audit-flip Task | Status |
|-----|------|-----------------|--------|
| WR-01 | 74-02 | Task 3 | COVERED |
| WR-02 | 74-01 | Task 3 | COVERED |
| WR-03 | 74-02 | Task 3 | COVERED |
| WR-04 | 74-01 | Task 3 | COVERED |
| WR-05 | 74-01 | Task 3 | COVERED |
| WR-06 | 74-01 | Task 3 | COVERED |
| WR-07 | 74-02 | Task 3 | COVERED |
| WR-08 | 74-02 | Task 3 | COVERED |
| WR-09 | 74-03 | Task 4 | COVERED |
| WR-10 | 74-03 | Task 4 | COVERED |
| WR-11 | 74-03 | Task 4 | COVERED |
| WR-12 | 74-03 | Task 4 | COVERED |
| WR-13 | 74-03 | Task 4 | COVERED |

74-03 Task 4 has an end-of-phase invariant check: `grep -cE "qramm-compliance/WR-.*Phase 74.*\[x\] closed" ... == 13`. Strong.

**Audit row coverage: 13/13 (100%).**

### Research Concern Handling (C-1..C-9)

| Concern | Resolved by plan | How |
|---------|------------------|-----|
| C-1 (D-02 endpoint_count source) | 74-01 | Plan explicitly cites RESEARCH C-1 + user override; uses local `total_endpoints` at line 59, not `evidence_summary.endpoint_count`. Truths + objective state this verbatim. |
| C-2 (D-04 ceiling path) | 74-01 | Path (a) `>= 3.95` selected; one-line diff at `scoring.py:67`; acceptance includes negative grep for old `>= 4.0`. |
| C-3 (D-05 SQL filter already symmetric) | 74-02 | Path (a): keeps SQL filter; adds invariant comment + regression test asserting TZ-symmetry. Truth restates the C-3 decision. |
| C-4 (D-08 advisor matches titles) | 74-03 | Path (a): introduce `CANONICAL_ALG_SYNONYMS` + `_matches`; apply word-boundary to title checks. Closes WR-09 without re-opening D-08. |
| C-5 (D-10 weight=0.0 lives on SCANNER_COVERAGE) | 74-03 | Targets `SCANNER_COVERAGE` parallel dict (path a); leaves `QRAMM_COMPLIANCE_WEIGHTS` untouched per user override + minimal-diff. |
| C-6 (D-11 no LAST_VERIFIED constant) | 74-03 | Uses nested `QRAMM_MODEL["last_verified"]`; acceptance includes negative grep `^LAST_VERIFIED == 0`. |
| C-7 (D-07 bare except, not AttributeError) | 74-02 | Narrows BOTH bare `except Exception:` blocks; user-override safety net `except Exception: ... raise` preserves unexpected-error visibility. |
| C-8 (D-08 scope: cipher_suite/cert_pubkey_alg) | 74-03 | Explicitly deferred per RESEARCH C-8 ("do NOT add cipher_suite / cert_pubkey_alg inspection — Phase 75+"). |
| C-9 (D-12 target doc exists) | 74-03 | Task 3 acceptance: "No deferred-items.md created (per RESEARCH C-9)"; plan reads `docs/operators-guide.md:318-330` to verify §7 still exists. |

**All 9 research concerns explicitly adjudicated and resolved in plan content (not silently ignored).**

---

## Dimension Results

### Dimension: context_compliance
**PASS.** Every locked decision D-01..D-12 + D-14 has an implementing task with concrete file:line site, exact format strings, and acceptance grep. No deferred ideas leak into scope (no Indeterminate-as-numeric-tier, no synonym-YAML, no `quirk doctor` wiring, no per-framework granularity). Both discretion areas (D-02a, D-10a) explicitly select defaults per CONTEXT. No scope reduction language ("v1", "static for now", "simplified") found.

### Dimension: success_criteria_coverage
**PASS.** All 3 ROADMAP success criteria map cleanly onto the 3 QWARN-NN plans (1:1). Truths cover the user-observable behaviors for each SC.

### Dimension: audit_row_coverage
**PASS.** All 13 WR rows assigned. End-of-phase invariant grep (74-03 Task 4 acceptance: `qramm-compliance/WR-.*\[ \] open == 0` AND `Phase 74 .*\[x\] closed == 13`) provides post-execute closure verification.

### Dimension: research_concern_handling
**PASS.** Every one of the 9 CONTEXT↔code discrepancies surfaced in RESEARCH is named in a plan with the chosen path. Plans honor RESEARCH paths AND user input overrides (e.g., D-07 user override `except Exception: ... raise` fallback; D-10 `SCANNER_COVERAGE` target; D-11 nested access). The plans do NOT silently re-open locked decisions — they adjudicate the discrepancy as RESEARCH instructed.

### Dimension: commit_atomicity
**PASS.** Each plan follows RED → GREEN → audit-flip cadence:
- 74-01: 3 commits (test → feat → docs)
- 74-02: 3 commits (test → feat → docs)
- 74-03: 4+ commits (test → up to 4 feat commits one per decision → chore TODO removal → docs audit flip)

74-03 Task 2 explicitly allows D-08+D-09 collapse if the import chain demands atomic landing — a reasonable executor escape hatch. Audit-ledger flips are isolated `docs(...)` commits, preserving rollback granularity. No mixed feature+audit commits.

---

## Findings

None blocking. No warnings.

Minor observations (informational only, no severity):

1. **74-03 Task 1 D-08 test case `_matches("3DES", "TripleDES_v2") == True`** — the test acknowledges Python `\b` treats `_` as a word char (so the boundary at `TripleDES_v2` is between `2` and end-of-string, not between `S` and `_`). Plan defers to "researcher confirms expected semantics during read_first" — acceptable. RED-task discovers the right expectation before GREEN locks behavior.

2. **74-03 Task 2 D-10 consumer wiring at `qramm.py:598-663`** — the rollup half-weight contribution for `'partial'` is described in prose but not pinned to a specific arithmetic site. Acceptable for an autonomous executor (action says "multiply that dimension's ceiling contribution by 0.5"), but the executor should verify no double-application across the existing weight × coverage multiplication.

Neither warrants a blocker or warning under the dimensions requested.

---

## Verdict

PASSED — Phase 74 plans are ready for execution. All 14 decisions, all 3 ROADMAP success criteria, all 13 audit rows, all 9 research concerns, and commit atomicity are demonstrably covered.
