# Phase 72 Plan Check

**Checked:** 2026-05-15
**Plans verified:** 72-01..72-05
**Mode:** Goal-backward, adversarial

## Summary

| Dimension | Verdict |
|-----------|---------|
| context_compliance (D-01..D-25) | PASS |
| success_criteria_coverage (5 ROADMAP rows) | PASS |
| audit_row_coverage (24 WR rows) | PASS |
| research_concern_handling (C-1..C-4) | PASS |
| dependency_ordering (05 → 04) | PASS-with-caveat |
| commit_atomicity (D-04 snapshot, D-05 rename) | PASS |
| task_completeness (auto-fields + tdd shape) | PASS |
| scope_sanity (tasks/files per plan) | WARN |

**Overall:** PASS with 3 WARN findings, 0 BLOCKERs.

---

## Dimension 1 — context_compliance (D-01..D-25)

Coverage map (decision → plan/task):

| Decision | Plan | Task | Coverage |
|----------|------|------|----------|
| D-01 (GCP KMS MAX_KMS_PAGES per-loop) | 72-03 | T1 Part A | Full; explicit per-loop counter + ≥3 acceptance grep |
| D-01a (per-loop default) | 72-03 | T1 Part A | Honored — acceptance asserts `page_count = 0` ≥3 times |
| D-02 (`_user_set_fields` sidecar + populate) | 72-05 | T3 Part A | Full; covers ConnectorsCfg dataclass + config.py populate |
| D-02a (sidecar naming) | 72-05 | T3 Part A | Default `_user_set_fields` selected |
| D-03 (standard branch no-op suppression) | 72-05 | T3 Part C | Full; inventory + per-site comment marker |
| D-04 (severity_rank, title, host, port) | 72-05 | T2 Part A | Full; explicit C-4 adjudication mapping `finding_id`→`title` |
| D-04a (`_SEVERITY_RANK` private) | 72-05 | T2 Part A | Default private; test asserts |
| D-05 (git mv + 2-line shim + docstring) | 72-05 | T1 | Full; shim shape + docstring quoted verbatim |
| D-05a (atomic 6-caller migration) | 72-05 | T1 | Full; commit message specifies atomicity; 6 callers enumerated |
| D-06 (profiles.py EOF verification) | 72-04 | T2 | Full; py_compile + git log + wc + visual diff + `# eof` marker |
| D-07 (AWS _scan_acm empty-ARN guard) | 72-01 | T1 Part B | Full |
| D-08 (AWS _scan_kms state skip) | 72-01 | T1 Part C | Full; 4-state frozenset module-scope |
| D-09 (AWS S3 as_completed) | 72-01 | T2 | Full; C-1 adjudication explicit |
| D-10 (AWS EKS multi-entry) | 72-01 | T1 Part D | Full; per-provider finding emit + dedup compatibility |
| D-11 (ThreadPoolExecutor module import) | 72-01 | T1 Part A | Full |
| D-12 (Azure key_size per-type) | 72-02 | T1 | Full; RSA/EC/OCT/unknown branches all enumerated |
| D-13 (K8s cluster_name colon strip) | 72-02 | T2 Part A | Full |
| D-14 (K8s Counter None exclude) | 72-02 | T2 Part B | Full; Pitfall-4 acknowledged |
| D-15 (K8s dat_scan_json fresh dict) | 72-02 | T2 Part C | Full; explicit "no key_name" comment |
| D-16 (GCP UNSPECIFIED+UNKNOWN raw-string skip) | 72-03 | T1 Part B | Full; Pitfall-2 distinguishes raw vs post-map check |
| D-17 (GCP Cloud SQL service_detail) | 72-03 | T2 | Full; C-3 verify-first adjudication explicit |
| D-18 (cache _read_json malformed JSON) | 72-04 | T1 Part A | Full; returns None + forensic-preserve |
| D-19 (cache scope_hash connectors) | 72-04 | T1 Part B | Full; defensive `pop('_user_set_fields')` |
| D-20 (db password=None omit kwarg) | 72-05 | T4 Part A | Full; if/elif/else for None / "" / nonempty |
| D-21 (db safe_str mysql/rds) | 72-05 | T4 Part B | Full; narrowed per C-2 to mysql/rds only |
| D-22 (vault token=None ValueError) | 72-05 | T5 Part A+B | Full; connector raises + run_scan.py migrates env read |
| D-23 (load_pem_x509_certificates) | 72-05 | T5 Part C | Full; AttributeError fallback documented |
| D-24 (tuple(findings) snapshot) | 72-05 | T2 Part B | Full; C-2 hypothetical-risk note preserved |
| D-25 (do-not-touch list) | All plans | All tasks | Honored via per-task "Per D-25" notes |

Deferred ideas check: none of the Deferred Ideas (`migration_planner.py`, CR-03 K8s None-cred, DeprecationWarning, `_SEVERITY_RANK` public promotion, full split, wizard prompt) appear as tasks. Clean.

**Verdict: PASS** — every locked decision has at least one task; no contradictions; no deferred ideas leak into tasks.

---

## Dimension 2 — success_criteria_coverage

| Roadmap Success Criterion | Covered By | Status |
|---------------------------|------------|--------|
| 1. AWS ACM empty ARN / KMS disabled / S3 executor.map / EKS multi-entry | 72-01 T1+T2 (D-07/08/09/10) | PASS |
| 2. Azure key_size all types / K8s colon strip / Counter None excl / dat_scan_json key_name omit | 72-02 T1+T2 (D-12/13/14/15) | PASS |
| 3. GCP KMS pagination cap / UNSPECIFIED/UNKNOWN consistency / Cloud SQL service_detail | 72-03 T1+T2 (D-01/16/17) | PASS |
| 4. Cache _read_json malformed JSON / scope_hash connector flags / profiles.py verified | 72-04 T1+T2 (D-06/18/19) | PASS |
| 5. 10 misc fixes (rename, mutation guard, standard re-apply, VAULT_TOKEN, DB password, DB host strip, AWS executor module-level, Vault PEM, _postprocess safe, _dedupe stable) | 72-05 T1-T8 (D-02/03/04/05/11/20/21/22/23/24) | PASS — 11 items (10 listed in criterion + WR-12 standard re-apply) all mapped; the WR-19 module-level executor import appears in 72-01 T1 Part A but its evidence flips audit row in 72-01 T3 |

Note on cross-plan WR-19: ROADMAP criterion 5 names "AWS ThreadPoolExecutor module-level import" but that fix lives in 72-01 (D-11). This is fine — criterion 5 is a 10-item enumeration, not a plan boundary, and the WR-19 row flip is correctly handled in 72-01 T3.

**Verdict: PASS**

---

## Dimension 3 — audit_row_coverage (24 WR rows)

| WR row | Flipped in plan | Acceptance command checks |
|--------|-----------------|---------------------------|
| WR-01 | 72-01 T3 | ✓ grep `WR-(01\|02\|13\|14\|19).*Phase 72.*\[x\] closed` == 5 |
| WR-02 | 72-01 T3 | ✓ same |
| WR-03 | 72-02 T3 | ✓ grep `WR-(03\|06\|17\|20)` == 4 |
| WR-04 | 72-03 T3 | ✓ grep `WR-(04\|05\|22)` == 3 |
| WR-05 | 72-03 T3 | ✓ same |
| WR-06 | 72-02 T3 | ✓ |
| WR-07 | 72-05 T8 | ✓ grep `WR-(07\|08\|09\|10\|11\|12\|18\|23\|24)` == 9 |
| WR-08 | 72-05 T8 | ✓ |
| WR-09 | 72-05 T8 | ✓ |
| WR-10 | 72-05 T8 | ✓ |
| WR-11 | 72-05 T8 | ✓ |
| WR-12 | 72-05 T8 | ✓ |
| WR-13 | 72-01 T3 | ✓ |
| WR-14 | 72-01 T3 | ✓ |
| WR-15 | 72-04 T3 | ✓ grep `WR-(15\|16\|21)` == 3 |
| WR-16 | 72-04 T3 | ✓ |
| WR-17 | 72-02 T3 | ✓ |
| WR-18 | 72-05 T8 | ✓ |
| WR-19 | 72-01 T3 | ✓ |
| WR-20 | 72-02 T3 | ✓ |
| WR-21 | 72-04 T3 | ✓ |
| WR-22 | 72-03 T3 | ✓ |
| WR-23 | 72-05 T8 | ✓ |
| WR-24 | 72-05 T8 | ✓ |

Total: 24/24 rows have explicit row-flip task with grep-anchored evidence assertions in AUDIT-TASKS.md. Per-row evidence text is documented in each SUMMARY emit.

**Verdict: PASS**

---

## Dimension 4 — research_concern_handling

| Concern | Required handling | Found in plan |
|---------|-------------------|---------------|
| C-1 (D-09 `_classify` vs `_build_endpoint`) | Apply to actual `_build_endpoint` site | 72-01 T2 explicit: "the audit cite says `_classify` but current code uses `_build_endpoint` — apply the migration to the actual current call site name" |
| C-2 (D-24 hypothetical mutation) | Apply defensive snapshot anyway | 72-05 T2 Part B explicit: "Per RESEARCH C-2 the current code mutates fields in-place... D-24 mandates the snapshot regardless" |
| C-3 (D-17 service_detail already routed) | Verify-first; close as no-op if confirmed | 72-03 T2 explicit Step 1 verification + Step 2 no-op path + Step 3 corrective fallback |
| C-4 (D-04 finding_id → title) | Map to `title` column | 72-05 T2 Part A explicit: "the locked `finding_id` field has no current analog — map it to the existing `title` column"; inline comment in patch documents adjudication |

**Verdict: PASS** — every concern is acknowledged by name in task wording, with adjudication rationale preserved.

---

## Dimension 5 — dependency_ordering

PLAN 05 frontmatter: `depends_on: [72-04]`, `wave: 2`. PLANs 01-04: `wave: 1`, `depends_on: []`.

PLAN 05 objective body documents the wave-2 rationale: "PLAN 05 is wave 2 (depends on PLAN 04) because D-19 in PLAN 04 references `cfg.connectors._user_set_fields` (added here in D-02). PLAN 04 defensively pops the sidecar by key name so the dependency is loose..."

**Caveat — the directionality of the dependency is reversed.** The text reads "PLAN 04 references PLAN 05's sidecar." That makes 04 the dependent of 05, but the frontmatter says 05 depends on 04. The plan justifies the chosen direction by noting PLAN 04 does a defensive `pop('_user_set_fields', None)` which is a no-op without the sidecar, so PLAN 04 can in fact ship before PLAN 05's dataclass change lands. With that defensive pop, ordering 05-after-04 is correct (it allows 04 to merge first; 05 then adds the field that 04's pop was already prepared for).

The prompt's framing "PLAN 05 depends on PLAN 04 (D-19 needs D-02 sidecar first)" is itself the inverse of what is implemented — but the implemented ordering with defensive pop is sound.

**Verdict: PASS-with-caveat** — ordering is defensible and explicitly justified; the prompt's stated rationale ("D-19 needs D-02 first") would imply 04 depends on 05, which is NOT what the frontmatter says. The plan's actual rationale (defensive pop decouples the wave; pick an order to suppress interleaved-commit confusion) is sound. If the orchestrator strictly enforces the prompt-stated rationale, this is a documentation tension. No code consequence.

---

## Dimension 6 — commit_atomicity

| Requirement | Where addressed |
|-------------|-----------------|
| D-04 snapshot regen has its own commit | 72-05 T7 explicit: "This regeneration is a SEPARATE commit from the code changes in Tasks 1-5. Suggested commit message: `chore(72-snapshots): regen goldens for _dedupe_findings sort key change (D-04)`" + acceptance `git log --oneline -3` check |
| D-05 import migration is atomic | 72-05 T1 explicit: "Per D-05a default yes (atomic single commit)... Single atomic commit suggested: `refactor(72-rename): risk_engine.py → findings_evaluator.py + migrate 6 callers (WR-10)`" |
| Audit-row flips are docs-only commits | 72-01 T3, 72-02 T3, 72-03 T3, 72-04 T3, 72-05 T8 each says "single docs commit" |

**Verdict: PASS**

---

## Dimension 7 — task_completeness

All `<task type="auto">` and `<task type="auto" tdd="true">` elements verified for: `<files>`, `<read_first>`, `<action>` or `<behavior>`, `<verify>` with `<automated>`, `<acceptance_criteria>`, `<done>`. Spot-check: every plan has 2-3 implementation tasks + 1 test/flip task; tdd tasks have behavior-first framing.

**Verdict: PASS**

---

## Dimension 8 — scope_sanity

| Plan | Tasks | Files modified | Verdict |
|------|-------|----------------|---------|
| 72-01 | 3 | 3 | OK |
| 72-02 | 3 | 5 | OK |
| 72-03 | 3 | 3 | OK |
| 72-04 | 3 | 4 | OK |
| 72-05 | **8** | **17** | WARN |

PLAN 05 has 8 tasks and 17 files (one git mv + 6 caller migrations + 4 module edits + 4 test files + snapshots + audit ledger). This exceeds the 2-3 tasks / 5-8 files target. The 8 tasks are: (T1) rename+migrate, (T2) sort+postprocess, (T3) sidecar+profiles, (T4) db_connector, (T5) vault+run_scan, (T6) tests, (T7) snapshot regen, (T8) audit flip. The cluster covers 9 audit rows.

**Mitigants:** each task is tightly scoped to a single decision pair; the work is genuinely related (it is the CLOUD-05 cluster); splitting further (e.g., 72-05a / 72-05b) would fragment the atomic rename commit. Context-budget risk exists but is manageable because tasks 4/5/8 are mechanical.

**Finding (WARN):**
- **F-1 (WARN, scope_sanity):** PLAN 05 has 8 tasks / 17 files modified. Exceeds the 2-3/5-8 target. Risk: executor quality may degrade mid-plan. Mitigation hint: consider splitting into 72-05 (rename + dedupe/postprocess + audit-flip-for-WR-10/23/24) and 72-06 (sidecar + db + vault + audit-flip-for-WR-07/08/09/11/12/18). Not blocker because every task is tightly bounded and CLOUD-05 is intentionally a sweep-cluster.

**Other warnings:**
- **F-2 (WARN, dependency_ordering):** PLAN 05's stated dependency direction is the inverse of the prompt's framing. Frontmatter says 05 depends on 04 (with defensive pop), but the natural read of D-02/D-19 is 04 depends on 05. The chosen direction is sound but the documentation tension may confuse the orchestrator if it strictly reads "D-19 needs D-02 sidecar first."
- **F-3 (WARN, test_coverage):** 72-05 T7 (snapshot regen) verifies via `pytest -x` (full suite) — this is correctly the gate but means PLAN 05 cannot complete until the full project test suite is green. If any unrelated test is flaky, executor may attempt to overwrite unrelated snapshots. Task body explicitly forbids this ("If `pytest -x` shows failures in unrelated modules, those are bugs introduced by Tasks 1-5") but executor discipline matters.

---

## Verdict

**Overall: PASS** with 3 WARN findings.

- 0 BLOCKERs
- 3 WARNs (F-1 PLAN-05 scope, F-2 dependency-direction wording, F-3 snapshot-regen executor-discipline)
- All 25 locked decisions covered
- All 5 ROADMAP success criteria provably mapped
- All 24 WR rows have flip tasks with anchored evidence
- All 4 RESEARCH concerns explicitly adjudicated in task wording
- Wave 1 (72-01..04) parallel-safe; PLAN 05 in wave 2 with documented (if inverted) rationale
- D-04 snapshot commit and D-05 atomic rename both explicit

Plans are ready for execution. Recommend tracking F-1 mid-execution: if PLAN 05 quality degrades after Task 4-5, pause and consider splitting before Tasks 6-8.
