---
phase: 145-liveness-pre-pass
plan: 03
subsystem: docs
tags: [nmap, liveness-probe, docs, uat, human-verify, bugfix]

# Dependency graph
requires:
  - phase: 145-liveness-pre-pass (plan 01)
    provides: NmapHostStatus, parse_nmap_host_status(), run_nmap_liveness_check() primitives
  - phase: 145-liveness-pre-pass (plan 02)
    provides: _is_privileged(), _emit_liveness_fallback_advisory(), batch-loop wiring
affects: [146-progress-scaling-disclosure (Phase 146 consumes liveness_skip rows for undetermined-host disclosure)]
provides:
  - "docs/operators-guide.md § 10 Discovery Liveness Pre-Pass"
  - "docs/report-interpretation.md liveness_skip / privilege_fallback row interpretation"
  - "docs/UAT-SERIES.md Series 145 (UAT-145-01/02/03), UAT-145-03 PASSED"
  - "quirk/discovery/nmap_parser.py::parse_nmap_run_summary() — <runstats> completion accounting"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Trust a run's <runstats> summary (exit=success AND total==len(targets)) before inferring absence-as-down; otherwise fail open exactly like a RuntimeError"

key-files:
  created: []
  modified:
    - docs/operators-guide.md
    - docs/report-interpretation.md
    - docs/UAT-SERIES.md
    - quirk/discovery/nmap_parser.py
    - quirk/discovery/nmap_provider.py
    - tests/test_nmap_parser.py
    - tests/test_nmap_provider.py

key-decisions:
  - "D-06 human-UAT gate genuinely caught a real defect (not just rubber-stamped): real nmap -sn -PS subnet sweeps emit <host> elements only for hosts they can positively report on — non-responsive hosts get NO individual <host state=\"down\"> element, only an aggregate <runstats><hosts total up down/> count. run_nmap_liveness_check()'s down-host set was built exclusively from explicit down elements, so on every real subnet sweep the exclude-set stayed empty and 100% of hosts were swept regardless of liveness — DISC-03 silently did nothing in its primary target scenario (segmented networks with mostly-dead hosts)."
  - "Fix trusts <runstats> only when exit=\"success\" AND total==len(targets) reconciles with the batch; any mismatch or missing summary falls back to the pre-existing fail-open behavior (sweep everyone), preserving the D-03 reliability-first principle that a live host must never be wrongly marked dead."
  - "Verified the fix against the user's own real bugged-run XML file (not just synthetic fixtures) before shipping — parse_nmap_run_summary() correctly reconstructs total=255/up=2/down=253 from the exact artifact that exposed the bug."

requirements-completed: [DISC-03]

duration: ~90min (docs + human-UAT round-trip + mid-verification bugfix)
completed: 2026-08-10
---

# Phase 145 Plan 03: Docs + D-06 Human-UAT Checkpoint Summary

**Documented the liveness pre-pass for operators and report readers, added UAT Series 145, and completed the D-06 non-root human-verification gate — which surfaced and led to fixing a real defect where the pre-pass filtered zero hosts on any actual subnet sweep.**

## Performance

- **Duration:** ~90 min (2 doc tasks + human-UAT checkpoint + live bugfix + re-verification)
- **Completed:** 2026-08-10
- **Tasks:** 3/3 (2 automated, 1 human-verify checkpoint)
- **Files modified:** 7 (3 docs, 2 production code, 2 test files) plus 3 Obsidian vault notes

## Accomplishments
- `docs/operators-guide.md` § 10 "Discovery Liveness Pre-Pass" documents what the pre-pass does, its port-scope rules (D-03), the privilege-fallback mechanism (D-01/D-02), and failure behavior — synced to `Guides/Operators-Guide.md`
- `docs/report-interpretation.md` documents the two new `scan_error_category` values (`liveness_skip`, `privilege_fallback`) with their exact row shapes — synced to `Guides/Report-Interpretation.md`
- `docs/UAT-SERIES.md` gained `## Series 145: Liveness Pre-Pass` with UAT-145-01 (automated, primitives), UAT-145-02 (automated, batch-loop wiring), and UAT-145-03 (human, D-06 non-root gate) — synced to `UAT-Series.md`
- **UAT-145-03 human-verification round-trip found a real bug live**, not a clean pass on the first try: the first non-root run reported `255 responsive, 0 skipped` in the batch summary despite nmap's own `<runstats>` showing `2 up, 253 down` — the pre-pass was filtering nothing on any real subnet sweep
- Root-caused and fixed: `quirk/discovery/nmap_parser.py` gained `parse_nmap_run_summary()` to read the `<runstats><hosts total up down/>` aggregate; `run_nmap_liveness_check()` in `nmap_provider.py` now synthesizes inferred-down `NmapHostStatus` rows for every batch target absent from the explicit up-results, but ONLY when the run summary proves full, successful accounting (`exit="success"` and `total == len(targets)`) — otherwise the pre-existing fail-open behavior is unchanged
- Added regression tests: `tests/test_nmap_parser.py` (3 new tests for `parse_nmap_run_summary`, including one reproducing the exact real-world XML shape that exposed the bug) and `tests/test_nmap_provider.py` (2 new tests: synthesis fires when trustworthy, does not fire when the summary doesn't reconcile)
- Re-verified live against the actual bug: post-fix non-root run correctly reported `2 responsive, 253 skipped`; DB confirmed 253 `liveness_skip` rows + 1 `privilege_fallback` row (`host='liveness-prepass'`); `sudo` re-run added zero new `privilege_fallback` rows and the console advisory did not print
- Added a backlog item (`.planning/ROADMAP.md` § Backlog → "Discovery & Scanning UX") to flip the interactive setup's `Run nmap port discovery first?` prompt default from `N` to `Y` — its current default caused two of the three verification attempts to silently skip the nmap discovery path entirely

## Task Commits

1. **Task 1: Document pre-pass in operators-guide/report-interpretation + vault sync** — `5c61562` (docs)
2. **Task 2: Add UAT Series 145 + vault sync** — `e133b3e` (docs)
3. **Mid-verification bugfix: infer down hosts from nmap runstats summary** — `c5290db` (fix)
4. **Record UAT-145-03 PASS after bugfix** — `ecc94a1` (docs)
5. Backlog item (nmap-discovery-first default) — `edcb140` (docs)

## Files Created/Modified
- `docs/operators-guide.md` — new § 10
- `docs/report-interpretation.md` — new `liveness_skip`/`privilege_fallback` entries
- `docs/UAT-SERIES.md` — Series 145 added, header date bumped, UAT-145-03 result recorded PASS
- `quirk/discovery/nmap_parser.py` — new `NmapRunSummary` dataclass + `parse_nmap_run_summary()`
- `quirk/discovery/nmap_provider.py` — `run_nmap_liveness_check()` now cross-checks the run summary and synthesizes inferred-down rows when trustworthy
- `tests/test_nmap_parser.py` — 3 new tests for `parse_nmap_run_summary`
- `tests/test_nmap_provider.py` — 2 new tests for the synthesis behavior (trustworthy vs. untrustworthy summary)
- `.planning/ROADMAP.md` — backlog item added (interactive nmap-discovery-first default)
- Vault: `Guides/Operators-Guide.md`, `Guides/Report-Interpretation.md`, `UAT-Series.md` all re-synced

## Decisions Made
- Fixed the bug immediately rather than deferring to a follow-up phase, since it defeated DISC-03's entire purpose in its primary target scenario (segmented networks) — shipping Phase 145 with this defect live would have meant the phase's success criteria were unmet in practice despite passing every automated test.
- Chose the conservative "trust runstats only when it fully reconciles with the batch" design over an unconditional flip to "absent = down", preserving the phase's D-03 reliability-first principle (never wrongly mark a live host dead) even though it means the fix stays inert on partial/truncated nmap output — matching the existing RuntimeError fail-open precedent exactly.

## Deviations from Plan
- **Deviation (justified, Rule 2 — codebase reality contradicted plan assumption):** The plan assumed the existing implementation (from Plans 01/02) correctly derived down-hosts from `parse_nmap_host_status()`'s explicit results. Live human-UAT proved that assumption wrong — real nmap doesn't emit per-host down elements for `-sn -PS` subnet sweeps. This required adding new production code (`parse_nmap_run_summary()` + the synthesis logic in `run_nmap_liveness_check()`) and regression tests beyond what Plan 03's original scope (docs + checkpoint only) called for. The fix was scoped narrowly to the exact defect and re-verified against the real bugged-run artifact before being accepted.

## Issues Encountered
- See Accomplishments/Decisions above — the liveness-filtering bug was the primary issue this plan surfaced and resolved.
- Two of three total interactive-setup scan attempts during verification silently skipped the nmap discovery path because the wizard's `Run nmap port discovery first?` prompt defaults to `N`; captured as a backlog item rather than fixed in-phase (out of DISC-03's scope).
- `[QRK-INSTALL-001]` advisories and a `ScanCfg.timeout_seconds` deprecation warning appeared in console output during verification — both pre-existing, unrelated to Phase 145 (confirmed via source read of `run_scan.py:1477`/`quirk/config.py:147` and `probe_missing_extras()`).
- A separate pre-existing report-generation guard (`executive headline 'EXCELLENT' is inconsistent with 1 CRITICAL finding(s)`, `quirk/reports/content_model.py:432`) halted report rendering on every verification scan; unrelated to this phase and did not block DB-level verification.

## User Setup Required
None beyond the verification steps already performed (chaos lab / non-root+sudo scan round-trip).

## Next Phase Readiness
- DISC-03 is now genuinely functional, not just test-covered: liveness-skipped hosts are actually excluded from the expensive full sweep on real subnet scans.
- `liveness_skip` and `privilege_fallback` CryptoEndpoint rows are confirmed end-to-end (code → DB → operator-facing docs) and ready for Phase 146's undetermined-host disclosure work (DISC-04..07).
- `parse_nmap_run_summary()` is a new, independently-testable primitive Phase 146 could reuse if it needs run-level accounting elsewhere.

## Verification

- `pytest tests/test_nmap_parser.py tests/test_nmap_provider.py tests/test_liveness_prepass.py tests/test_nmap_hardening.py tests/test_xml_safe.py tests/test_nmap_scope_args.py tests/test_jobs_nmap_scope_cap.py -q` — 72 passed
- `python -m compileall quirk/discovery/nmap_parser.py quirk/discovery/nmap_provider.py` — exit 0
- Live human-UAT (UAT-145-03): non-root run — `2 responsive, 253 skipped`; DB — 253 `liveness_skip` rows + 1 `privilege_fallback` row (`host='liveness-prepass'`); `sudo` re-run — 0 new `privilege_fallback` rows, advisory line absent from console
- Fix validated directly against the real bugged-run XML artifact (`quirk-output/nmap-liveness-20260810-143338.xml`) confirming `parse_nmap_run_summary()` reconstructs `total=255, up=2, down=253, exit=success` exactly

---
*Phase: 145-liveness-pre-pass*
*Completed: 2026-08-10*

## Self-Check: PASSED

All modified/created files exist on disk; all commits (`5c61562`, `e133b3e`, `c5290db`, `ecc94a1`, `edcb140`) present in git log; UAT-145-03 recorded PASS in `docs/UAT-SERIES.md` and synced to the vault.
