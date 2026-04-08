# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v3.9 — Gap Closure

**Shipped:** 2026-04-04
**Phases:** 11 | **Plans:** 40+ | **Commits:** 263

### What Was Built

- **Full cryptographic scanner surface:** sslyze TLS deep scan, ssh-audit KEX/hostkey/MAC enumeration, API/JWT scanner with JWKS fetch, Syft container scanner, semgrep source code scanner, AWS + Azure cloud connectors — all wired to a single SQLite persistence layer
- **CycloneDX CBOM pipeline:** classifier (50+ NIST PQC entries), builder, writer producing JSON+XML per scan run; dashboard CBOM viewer renders bipartite component graph with quantum-safety labels
- **FastAPI + React dashboard:** executive summary with 4-subscore gauges, findings table, certificate inventory, CBOM viewer, PDF export via Playwright — all served from `quirk serve` with correct db_path and port propagation
- **6-profile chaos lab expansion:** jwt, registry, source, storage, ssh-weak, ldaps — full Docker Compose lab for validating every new scanner surface against realistic targets
- **7-guide documentation suite:** getting started, installation, configuration, connector setup, report interpretation, CBOM compliance guide, chaos lab operator guide
- **v4.0.0 packaging and polish:** pip-installable wheel with bundled React static assets, `quirk init` wizard, HTML/PDF report templates, QU.I.R.K. visual identity, `quirk banner` rich CLI UX
- **E2E dashboard wiring fixes (Phase 11):** closed GAP-INT-01 (db_path default mismatch), GAP-INT-02 (PDF port env var not propagated), GAP-INT-03 (SSH algorithms missing from CBOM viewer)

### What Worked

- **Phase-gated verification:** Every phase produced a VERIFICATION.md with observable truths and behavioral spot-checks before marking complete. This caught the packaging gap (PACKAGE-01) and quantum safety label type confusion (MISMATCH-01) before they shipped.
- **Gap closure phases (10 + 11):** Explicitly scheduling gap-closure phases at the end of the milestone — rather than trying to fix defects inline — kept primary phases clean and gave defects first-class planning treatment.
- **Integration audit before milestone close:** The `audit-milestone` workflow running the `gsd-integration-checker` agent as a final gate found INT-01 and INT-02 after all phase verifications passed. Without this, the dashboard scoring profile gap and orphaned `scorecard.py` would have shipped silently.
- **3-source requirements cross-reference:** Mapping REQ-IDs across VERIFICATION.md + REQUIREMENTS.md traceability + SUMMARY.md frontmatter identified 7 requirements with incomplete SUMMARY coverage — surfaced as Nyquist debt rather than silent gaps.
- **Tech debt backlog (BACK-xx):** Tracking found-but-deferred issues (BACK-60, BACK-61, BACK-62) as first-class backlog entries with phase directory stubs means they won't be forgotten between milestones.

### What Was Inefficient

- **Nyquist VALIDATION.md hygiene:** 9 of 11 phases have stale VALIDATION.md files (`nyquist_compliant: false`); 2 phases (02, 08) are missing VALIDATION.md entirely. These were never updated post-execution. Updating them should be a required exit step for every plan execution, not a backlog item.
- **Phase 1 not structured as sub-plans:** Phase 1 (Foundation Fixes) appears to have no discoverable `01-xx-PLAN.md` files (the plan glob returned only phases 02–11). Large phases benefit from the same sub-plan breakdown structure used in later phases.
- **SUMMARY.md frontmatter inconsistency:** 7 SUMMARY.md files were missing `requirements-completed` frontmatter fields (SCAN-01, LAB-04, DOC-05, DOC-07, BRAND-01, BRAND-02, BRAND-03). The gsd-tools `summary-extract` command returned empty output for all files because of this. Frontmatter field completeness should be validated at plan-complete time.
- **Documentation + Obsidian sync deferred:** Guide syncs to the Obsidian vault were skipped in most phase executions. This creates drift between the planning system and the knowledge base. Per memory: all phase plans must include explicit docs update and Obsidian sync tasks.

### Patterns Established

- **GAP closure phase naming:** `NN-v{version}-gap-closure` and `NN-{feature}-wiring-fixes` as dedicated end-of-milestone phases for closing audit findings
- **3-source requirements cross-reference table** in milestone audit as standard coverage gate
- **BACK-xx backlog entries with phase directory stubs** for tech debt that can't be closed in the current milestone
- **`<details>` collapse in ROADMAP.md** for archived milestone phase lists — keeps the roadmap scannable as phases accumulate
- **Milestone archival to `.planning/milestones/`** as authoritative historical record, with ROADMAP.md/REQUIREMENTS.md kept clean for next milestone

### Key Lessons

1. **Verification without integration testing is incomplete.** All 11 phases passed individual VERIFICATION.md checks, but the integration audit still found 2 wiring gaps (INT-01, INT-02). Unit-level verification and cross-phase integration are separate quality gates — both are necessary.
2. **Packaging is easy to forget and hard to notice.** PACKAGE-01 (React static assets missing from pip wheel) would have been invisible until someone ran `pip install` in a fresh virtualenv. Packaging verification must be part of phase exit criteria whenever pyproject.toml or build artifacts change.
3. **Documentation debt compounds.** 9 stale VALIDATION.md files + 7 incomplete SUMMARY.md files + deferred Obsidian syncs = a documentation state that drifts far from the code. Treating docs as a first-class task in every plan execution (not a post-milestone cleanup) prevents this accumulation.
4. **Type confusion bugs survive code review.** MISMATCH-01 (passing a string directly to `quantum_safety_label()` instead of the NIST level it expects) was a semantic type mismatch that Python's dynamic typing couldn't catch. The regression tests in `test_gap_closure.py` are the right fix — ensure classifiers have unit tests that assert output types, not just no-exception execution.

### Cost Observations

- Model mix: Sonnet 4.6 primary throughout milestone
- Sessions: Multiple multi-hour sessions; 263 commits across the milestone
- Notable: Gap closure phases (10, 11) required approximately the same planning and execution effort as primary phases despite targeting only 3 defects — defects in integration wiring are not cheaper to fix than features

---

## Milestone: v4.1 — Foundation Polish

**Shipped:** 2026-04-08
**Phases:** 5 (12–16) | **Plans:** 10 | **Files changed:** 80 (+10,261 / -638)

### What Was Built

- **CLI correctness sweep:** Fixed generated config field names, replaced `[owner]` placeholder with dev-install workflow, bumped all 5 version string locations to 4.1.0 including pyproject.toml (caught by gap-closure phase)
- **Interactive mode rewrite:** Fully replaced interactive_config() — auto-detected timezone, hardcoded 17-port consulting TLS defaults, profile selection menu (quick/standard/deep), JWT/container/source scanner prompts, targets-first prompt order, unified data classification menu
- **Scoring end-to-end correctness:** Calibration profile (strict/balanced/lenient) now correctly applied in compute_readiness_score(); dashboard reads calibration.profile from intelligence JSON; validate.py no longer flags non-existent artifacts; migration_advisor pattern strings now match risk_engine finding titles
- **Dead code elimination:** Legacy connector stubs (aws_stub.py, azure_stub.py, windows_adcs_stub.py) deleted; orphaned scorecard.py + test removed; SSH cfg.scan mutations moved inside try block; 14 VALIDATION.md files updated to nyquist_compliant: true
- **Flow C closure (Phase 16):** Two one-line fixes that audit found — pyproject.toml version and interactive.py output dir default — closed the E2E gap from interactive wizard to dashboard profile display

### What Worked

- **Audit-then-gap-closure pattern established in v3.9 paid off immediately.** The v4.1 audit found CLI-04 and SCORE-04 as two precise, actionable gaps (not ambiguous issues). Phase 16 closed both in a single plan with 4 targeted edits. The pattern of audit → gap-closure phase → milestone close is now validated across two milestones.
- **TDD RED-first discipline caught real bugs.** Every plan pair (N-01 scaffold, N-02 implementation) proved the bug existed before fixing it. Phase 16 specifically used importlib.metadata.version() inspection to distinguish the installed egg-info version from the runtime __version__ — a gap that code inspection alone would have missed.
- **Phase 15 (VALIDATION.md hygiene)** closing 14 stale files in a single plan means the next milestone starts with an accurate Nyquist baseline — the v3.9 retrospective specifically called this out as debt. Fixed and won't compound.

### What Was Inefficient

- **Two SUMMARY.md files missing `one_liner` frontmatter:** The `summary-extract` CLI returned empty for all 10 SUMMARY.md files — the field isn't being written by the execute-phase workflow. This means MILESTONES.md auto-generation falls back to verbose description strings rather than crisp one-liners. The frontmatter contract needs enforcement at plan-complete time.
- **Interactive mode tech debt (DEFAULT_TIMEZONE, _prompt_ports) deferred twice:** Deferred in Phase 13 to Phase 15; Phase 15 didn't address. Zero runtime impact but the dead code accumulates. These should have been deleted in Phase 15 alongside the scorecard cleanup — they're adjacent hygiene items.
- **Phase 16 could have been avoided:** CLI-04 (pyproject.toml version) and SCORE-04 (output dir default) were both identified by the milestone audit, meaning they slipped through all 4 phases of verification. Had test_packaging.py included `importlib.metadata.version()` verification from Phase 12, CLI-04 would have been caught immediately.

### Patterns Established

- **Two-edit gap-closure pattern:** A gap-closure phase targeting only 2 files with 2 targeted edits is valid and fast — avoid over-engineering the fix just because it has a phase to itself
- **importlib.metadata.version() vs __version__:** When testing package version consistency, inspect the installed package manifest (importlib.metadata) not just the module attribute — they can diverge with editable installs if pyproject.toml isn't updated
- **output dir alignment as integration contract:** Dashboard QUIRK_OUTPUT_DIR default and interactive_config() output dir default are a cross-component contract — both must agree for E2E profile passthrough to work; this should be a formal integration test

### Key Lessons

1. **GAP-closure phases scale down cleanly.** v4.1's gap-closure was 2 files / 4 lines vs v3.9's 3-defect Phase 11. The same planning structure (audit → gap-closure → milestone close) works at both scales — don't skip it for "small" gaps.
2. **Version consistency needs manifest-level verification.** Runtime __version__ and installed package version (importlib.metadata) are independent until pip install -e . is run. Test both, not just the module attribute.
3. **Deferred dead code has a shelf life.** DEFAULT_TIMEZONE and _prompt_ports() were deferred twice before this retrospective. They should have been deleted in Phase 15 — dead code that survives two milestones becomes permanent fixture.
4. **SUMMARY.md `one_liner` field needs enforced.** Auto-extraction from SUMMARY.md frontmatter is only useful if the field is actually populated. This is a workflow enforcement gap, not a content gap.

### Cost Observations

- Model mix: Sonnet 4.6 primary throughout milestone
- Sessions: Intensive 2-day execution (2026-04-06 → 2026-04-08)
- Notable: Correctness-only milestone with no new features — lowest code churn of any milestone; highest precision (22/22 requirements satisfied, 2/2 audit gaps closed)

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v3.9 Gap Closure | 11 | 40+ | First milestone to use audit-milestone + integration checker gate before close; established BACK-xx backlog and milestones/ archival patterns |
| v4.1 Foundation Polish | 5 | 10 | Correctness-only milestone — no new features; 22/22 requirements satisfied; audit-gap-closure pattern validated at small scale |

### Cumulative Quality

| Milestone | Tests | Notes |
|-----------|-------|-------|
| v3.9 | 199 | 199 tests green at ship; 9 stale Nyquist VALIDATION.md files (BACK-62) |
| v4.1 | 233 | 233 tests green at ship; all 14 VALIDATION.md files updated to nyquist_compliant: true; zero known tech debt |

### Top Lessons (Verified Across Milestones)

1. Schedule gap-closure phases explicitly at the end of milestones — defects found late deserve first-class planning treatment, not inline patches
2. Integration audit (`gsd:audit-milestone`) must run before `gsd:complete-milestone` — phase-level verification alone is insufficient to confirm cross-phase wiring is correct
3. Test package manifest version (importlib.metadata) separately from runtime __version__ — editable installs can make them diverge invisibly
4. Dead code deferred across two milestones becomes permanent — enforce dead code deletion in the phase that discovers it, not later
