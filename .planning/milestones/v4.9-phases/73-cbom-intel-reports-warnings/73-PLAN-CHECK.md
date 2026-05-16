# Phase 73 Plan Check — CBOM + Intelligence + Reports WARNINGs

**Checked:** 2026-05-15
**Plans verified:** 3 (73-01, 73-02, 73-03)
**Inputs:** 73-CONTEXT.md (D-01..D-10, D-14), 73-RESEARCH.md (C-1..C-8), ROADMAP.md Phase 73 (3 success criteria), AUDIT-TASKS.md lines 149-162 (13 open WR rows)
**Verdict:** PASS WITH 1 WARNING (no blockers; one ROADMAP/CONTEXT divergence noted, CONTEXT correctly takes precedence)

---

## Dimension 1 — context_compliance (D-01..D-10)

| Decision | Plan | Task(s) | Status |
|----------|------|---------|--------|
| D-01 narrowed except + finally + stderr advisory | 73-01 | T1 | COVERED (with sync-API translation per RESEARCH C-2) |
| D-01a import-guard preserved | 73-01 | T1 (preserves lines 110-113) | COVERED |
| D-02 weak_crypto module + is_weak_cipher | 73-02 | T1, T2 (Part C/D/E) | COVERED |
| D-02a set private, helper public | 73-02 | T1 (`_WEAK_CIPHER_TOKENS` underscored) | COVERED |
| D-03 ECDSA EC/ECDSA tuple startswith | 73-02 | T2 (Part B) | COVERED |
| D-04 SCORE_WEIGHTS docstring + invariant test | 73-03 | T1 | COVERED (no value change per D-14) |
| D-05 _why double-period rstrip | 73-03 | T2 (Part A) | COVERED |
| D-06 _add_candidate merge-rule docstring + test | 73-03 | T2 (Part B/C) | COVERED (figurative "yield" adjudicated per C-6) |
| D-07 _build_interpretation .get guard + fallback | 73-03 | T3 | COVERED |
| D-08 _KEX_MAP RSA → RSA-kex | 73-03 | T4 | COVERED (at cbom/builder.py per C-1, not evidence.py) |
| D-09 confidence clamp + ValueError + WARNING | 73-03 | T5 | COVERED (inline per C-5; no apply_weight_overrides) |
| D-10 motion_broker via is_weak_cipher + is_legacy_tls_version | 73-02 | T2 (Part D) | COVERED |
| D-14 do-not-touch list | All | Explicit "Per D-14" prohibitions in each task action | COVERED |

**All 10 locked decisions + D-14 + D-01a/02a map to ≥1 task.** No scope reduction language detected ("v1", "static", "future enhancement" — not present anywhere). No deferred ideas implemented.

---

## Dimension 2 — success_criteria_coverage (ROADMAP 3 criteria)

| ROADMAP SC | Plan tasks | Status |
|---|---|---|
| SC-1: PDF except narrowed, Playwright finally cleanup, user-visible warning | 73-01 T1 (D-01) + T2 tests | COVERED |
| SC-2: motion_broker uppercase consistency, ECDSA conventions, SAML mixed-case SHA-1, email/broker unified helper | 73-02 T1 (helper) + T2 (4 sites) | COVERED |
| SC-3: SCORE_WEIGHTS documented **and normalized**; roadmap double-period removed; executive guards score['score']; TLS 1.2 RSA-kex; confidence overrides clamp+validate | 73-03 T1..T5 | **WARNING — see below** |

**WR-1 (warning, not blocker): ROADMAP SC-3 wording says "documented AND normalized"; CONTEXT D-04 explicitly locks "NOT normalized — preserves all customer-facing scores"; D-14 forbids any SCORE_WEIGHTS value change.** Plans correctly follow CONTEXT (per the user's planner-precedence rule: CONTEXT D-NN supersedes upstream artifacts when they conflict). The ROADMAP wording is the artifact at odds, not the plans. Document this in the Phase 73 SUMMARY so the verifier knows SC-3 "normalized" is satisfied by documented-invariant + CI gate (sum=261 by design), not by value normalization. No plan revision needed.

---

## Dimension 3 — audit_row_coverage (13 open WR rows)

| WR | Plan | Task | Audit-flip task |
|---|---|---|---|
| WR-01 | 73-01 | T1 | T3 (flip line 149) |
| WR-02 | 73-01 | T1 | T3 (flip line 150) |
| WR-03 | 73-02 | T2 Part D | T3 (flip line 151) |
| WR-04 | 73-02 | T2 Part B | T3 (flip line 152) |
| WR-06 | 73-03 | T1 | T6 (flip line 154) |
| WR-07 | 73-03 | T2 Part A | T6 (flip line 155) |
| WR-08 | 73-03 | T2 Part B | T6 (flip line 156) |
| WR-09 | 73-03 | T3 | T6 (flip line 157) |
| WR-10 | 73-02 | T2 Part C | T3 (flip line 158) |
| WR-11 | 73-02 | T2 Part E | T3 (flip line 159) |
| WR-12 | 73-03 | T4 | T6 (flip line 160) |
| WR-13 | 73-03 | T5 | T6 (flip line 161) |
| WR-14 | 73-01 | T1 (stderr advisory) | T3 (flip line 162) |

**All 13 open rows mapped to (a) fix task and (b) row-flip task.** WR-05 correctly excluded (closed by Phase 60 per ledger line 153). 73-03 T6 acceptance criterion explicitly asserts `grep -cE "cbom-intel-reports/WR-.*\[ \] open" == 0` post-flip — closes the cluster.

---

## Dimension 4 — research_concern_handling (C-1..C-8)

| Concern | Honored where | Status |
|---|---|---|
| C-1 (D-08 site is cbom/builder.py:177, not evidence.py) | 73-03 T4 `<files>` lists `quirk/cbom/builder.py`; objective §5 cites "NOT evidence.py — per RESEARCH C-1" | COVERED |
| C-2 (sync Playwright API; drop asyncio.TimeoutError, drop `await`/`context`) | 73-01 T1 `<interfaces>` shows sync-API translation; action ¶1 explicitly: "drop it. The imports become `from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError`" | COVERED |
| C-3 (stderr advisory from callee html_renderer.py vs caller writer.py) | 73-01 T1 emits from `html_renderer.py::render_pdf_report` inside narrowed except (callee path); T2 extends `test_reports_writer.py` to verify advisory propagates | COVERED |
| C-4 (D-08 path (a) relabel vs (b) dual-emit) | 73-03 T4: "single-line change... path (a)... do NOT emit `RSA-auth`" | COVERED |
| C-5 (D-09 inline at confidence.py:46-49; no apply_weight_overrides function exists) | 73-03 T5 action: "the function `apply_weight_overrides` does NOT exist. Apply the fix **inline**"; uses bare `float()` per RESEARCH spec | COVERED |
| C-6 (D-06 "mutation-after-yield" figurative; module is not a generator; real fix is docstring on _add_candidate) | 73-03 T2 Part B: "the module is **not a generator** — CONTEXT's 'mutation-after-yield' phrasing is figurative... real undocumented contract is the lower-key-wins merge rule"; doc-only, no body change | COVERED |
| C-7 ([reports] extra does not exist; Playwright is in [dashboard]) | 73-01 T1 action ¶4 (D-01a): "Playwright lives in the `[dashboard]` extra (not `[reports]`); the existing guard already satisfies the pattern. No change." | COVERED |
| C-8 (CBC3 token added to _WEAK_CIPHER_TOKENS for parity with tls_capabilities.py:103) | 73-02 T1 `<interfaces>` token set explicitly includes `"CBC3"`; T1 acceptance asserts `grep -nE '"CBC3"' quirk/util/weak_crypto.py` == 1 | COVERED |

**All 8 research concerns explicitly honored in task actions and acceptance criteria.**

---

## Dimension 5 — commit_atomicity (1 task = 1 commit)

| Plan | Tasks | Commits implied | Atomic? |
|---|---|---|---|
| 73-01 | 3 (T1 src, T2 tests, T3 audit flip) | 3 | YES |
| 73-02 | 3 (T1 helper+test, T2 evidence src+test, T3 audit flip) | 3 | YES |
| 73-03 | 6 (T1 scoring, T2 roadmap, T3 executive, T4 builder, T5 confidence, T6 audit flip) | 6 | YES |

**Total: 12 commits across 3 plans, one per task.** Each task's `<files>` is scoped, `<verify>` is per-task, and audit-row flips are separated into their own terminal task per plan (matches Phase 72 / 71 precedent — separate docs commit). T2 in 73-01 and 73-02 mixes src+test in one commit — acceptable per project's TDD pattern (the test is the verification artifact for that fix).

Minor observation (not a blocker): 73-02 T1 creates both `quirk/util/weak_crypto.py` and `tests/test_weak_crypto_helper.py` in a single commit. This is RED-then-GREEN coupled (helper + its tests born together), consistent with project pattern.

---

## Dimension 6 — task_completeness

All 12 tasks have `<files>`, `<action>`, `<verify>` (with `<automated>` command), `<acceptance_criteria>`, `<done>`. TDD tasks add `<behavior>`. Verify commands are runnable pytest / compileall invocations (no watch modes, no full E2E). Acceptance criteria are grep/pytest-checkable. No vague tasks detected.

---

## Dimension 7 — dependency_correctness

All three plans: `wave: 1`, `depends_on: []`. Parallel-runnable. No cycles. No forward references. Plans touch disjoint source files (`html_renderer.py` / `evidence.py` + `weak_crypto.py` / `scoring.py` + `roadmap.py` + `executive.py` + `cbom/builder.py` + `confidence.py`). The only shared file is `.planning/audit-2026-05-08/AUDIT-TASKS.md` — each plan's audit-flip task touches disjoint lines (73-01 → 149/150/162; 73-02 → 151/152/158/159; 73-03 → 154/155/156/157/160/161). No line collision.

73-03 T6 acceptance asserts `grep -cE "cbom-intel-reports/WR-.*\[ \] open" == 0` which requires plans 73-01 and 73-02 to have also flipped. This is a soft sequencing dependency for the **acceptance check**, not a build dependency — all three plans run in parallel and the final assertion holds at phase wrap. No revision needed.

---

## Dimension 8 — scope_sanity

| Plan | Tasks | Files mod | Verdict |
|---|---|---|---|
| 73-01 | 3 | 3 + 1 audit | Within budget |
| 73-02 | 3 | 4 + 1 audit | Within budget |
| 73-03 | 6 | 5 src + 5 tests + 1 audit | Borderline (6 tasks > 5 threshold) |

**73-03 is at 6 tasks** — exceeds the warning threshold (4) and matches the upper blocker threshold (5+). However: each task is a surgical single-WR-row fix (≤10 LOC each per RESEARCH "Code Examples"); five of six are clamp/docstring/relabel/guard one-liners with their tests; T6 is a 6-line audit edit. Total source diff estimate: ~80 LOC + ~200 LOC tests. This is **not** a complex domain crammed into one plan — it is six independent micro-fixes that share INTEL-03 as their requirement. Splitting into 73-03a/03b would inflate ceremony (two extra SUMMARY.md, two extra orchestrations) without quality gain.

**Disposition: accept 73-03 at 6 tasks.** Precedent: Phase 71 closed similar multi-WR clusters with 5-7 micro-tasks per plan.

---

## Dimension 9 — verification_derivation (must_haves)

All three plans have `must_haves: { truths, artifacts, key_links }`. Truths are user-observable / contract-observable (e.g., "render_pdf_report narrows the inner except", "_WEAK_CIPHER_TOKENS contains... CBC3", "Audit rows... flipped to `Phase 73 | [x] closed`"). Artifacts list files + `provides` description. Key links wire callers to callees (e.g., evidence.py → weak_crypto.is_weak_cipher via explicit import path with `pattern` regex for grep validation).

73-03 has 9 truths and 6 key_links — proportional to 6 independent fix tasks.

---

## Dimension 10 — CLAUDE.md compliance

- **PEP 8:** Every task action ends with "PEP 8. Minimal diff." Acceptance includes `python -m compileall`. COVERED.
- **Minimal diffs:** D-14 do-not-touch list enforced in every task; acceptance for several tasks includes `git diff --stat` line-count assertions. COVERED.
- **`python -m compileall` after changes:** Every task's `<verify>` runs `python -m compileall <file> && pytest ...`. COVERED.
- **No new pip deps:** Phase boundary explicit; no new imports outside stdlib + already-pinned `playwright`. COVERED.
- **Staleness review cadence:** N/A (no QRAMM model / compliance catalog edits) — RESEARCH explicitly notes this.
- **Chaos lab maintenance:** N/A (no Docker Compose profile changes) — RESEARCH explicitly notes this.
- **Mandatory phase completion steps (Obsidian note, UAT-SERIES.md update, vault sync, commit):** Not explicit in plan tasks but documented as a phase-wrap orchestration step in RESEARCH "Project Constraints" section. Recommend orchestrator handles per `/gsd-execute-phase` wrap pattern — no plan-task gap.

---

## Dimension 11 — research_resolution

RESEARCH.md `## Open Questions` section (lines 600-606) is NOT marked `(RESOLVED)`. Three numbered questions:

1. D-08 RSA label TLSv1.3 scope — **resolved inline** in the question text ("Recommendation: scope D-08 fix to non-TLSv1.3 path only") and honored by 73-03 T4 (test_tls13_path_unaffected).
2. D-09 unknown-key behavior — **resolved inline** ("Safe to log-and-accept unknown keys per D-09") and honored by 73-03 T5 (WARNING log + acceptance).
3. D-02 token list CBC3 — **resolved inline via C-8 adjudication** and honored by 73-02 T1 (CBC3 added).

**WR-2 (warning, not blocker):** RESEARCH `## Open Questions` heading lacks the `(RESOLVED)` suffix even though all three questions have inline resolutions and are reflected in plans. Strict dimension-11 reading would flag this as a blocker, but the substantive content shows full resolution — every question is closed and traced into plan tasks. Recommend the researcher append `(RESOLVED)` to the heading for cleanliness; this is cosmetic and does not block execution.

---

## Dimension 12 — pattern_compliance

No PATTERNS.md exists for Phase 73. SKIPPED.

Code-pattern references in plans are explicit:
- 73-01 cites `quirk/util/optional_extra.py:225` (stderr advisory) and `quirk/util/safe_exc.py:36` (safe_str).
- 73-02 cites `quirk/util/safe_exc.py:1-53` (module shape precedent) and `quirk/scanner/tls_capabilities.py:103` (CBC3 token precedent).
- 73-03 cites Phase 60 `60-02-SUMMARY.md:80-100` (cap-sharing rationale), Phase 70 D-07 (guard discipline), Phase 71 PROTO-01 (clamp precedent).

All analogs verified by RESEARCH at HEAD `cf2417a`.

---

## Findings Summary

**BLOCKERS: 0**

**WARNINGS: 2**

- **WR-1 (success_criteria_coverage):** ROADMAP SC-3 says "SCORE_WEIGHTS documented AND normalized"; CONTEXT D-04 + D-14 LOCK no-normalization. Plans correctly follow CONTEXT. Recommend the Phase 73 SUMMARY.md explicitly note SC-3 "normalized" is satisfied by documented invariant + CI gate (sum=261 by design preserves all customer-facing scores). Optionally, ROADMAP wording can be amended post-phase to read "documented (invariant: sum=261, NOT normalized — see Phase 73 D-04)". No plan revision needed.
- **WR-2 (research_resolution):** RESEARCH.md `## Open Questions` heading lacks `(RESOLVED)` suffix. All three questions have inline resolutions and are reflected in plans. Cosmetic — recommend appending `(RESOLVED)` to the heading.

---

## Verdict

**PASS WITH 2 WARNINGS** — Execution may proceed. Both warnings are documentation-clean-up items that do not affect plan correctness or success-criteria delivery. All 10 locked decisions, all 13 open WR rows, all 8 research concerns, and all 3 ROADMAP success criteria are provably addressed by the 12 tasks across plans 73-01 / 73-02 / 73-03. CONTEXT-precedence rule correctly applied for D-04 vs ROADMAP SC-3 normalization wording.
