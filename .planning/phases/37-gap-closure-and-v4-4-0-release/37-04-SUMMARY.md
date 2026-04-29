---
phase: 37
plan: 04
status: complete-with-deferrals
requirements: [INFRA-03]
created: 2026-04-29
---

# Plan 37-04 Summary — VALIDATION.md Backfill (32-37)

## Outcome

INFRA-03 partially satisfied with two documented deferrals (D-06 gate could not
be flipped due to pre-existing pytest red unrelated to Phase 37).

| Phase | Action | Result |
|-------|--------|--------|
| 32 | Append "Nyquist Scenarios — INFRA-03" matrix (3 email rows) | ✅ done |
| 33 | Append "Nyquist Scenarios — INFRA-03" matrix (15 broker rows) | ✅ done |
| 34 | Re-validated; flipped status:draft → approved, nyquist_compliant: false → true, wave_0_complete: false → true (15/15 motion tests green via `python -m pytest`) | ✅ done |
| 35 | Created 35-VALIDATION.md from scratch (file did not exist; 101 CBOM tests green) | ✅ done |
| 36 | wave_0_complete flip — gated on D-06 checks (`status: approved` + UAT sign-off + `pytest -x -q` green) | ⚠️ DEFERRED |
| 37 | Created 37-VALIDATION.md (this phase's own validation contract) | ✅ done |

## Task 1 — Phases 32 & 33 Nyquist Matrices

Appended `## Nyquist Scenarios — INFRA-03` section above `## Validation Sign-Off`
in both files. References the 18 test functions from
`tests/test_infra03_nyquist_coverage.py` (created by Plan 37-03):
- 32-VALIDATION.md: 3 email rows (`scan_email_targets` × happy/refused/plaintext_only)
- 33-VALIDATION.md: 15 broker rows (`scan_kafka_targets`, `scan_rabbitmq_targets`,
  `scan_redis_targets`, `azure_servicebus_probe`, `aws_sqs_probe` × 3 scenarios each)
- Both files: bumped `updated:` to 2026-04-29

Verified: `grep -c 'test_scan_email\|test_scan_kafka\|test_scan_rabbitmq\|test_scan_redis\|test_azure_servicebus\|test_aws_sqs'` → `3 + 15 = 18`.

## Task 2 — Phases 34 & 35 Re-validation (D-05)

The plan instructed `gsd-sdk query plan-checker.run --phase NN`. The SDK does
not currently expose that subcommand and spawning a subagent was not warranted
in interactive mode. Per D-05's "no rubber-stamping" rule, I instead re-ran
the actual validation evidence:

- **Phase 34**: `python -m pytest tests/test_motion_scoring.py -q` → 15 passed.
  All 15 tests trace 1:1 to plans 34-01..34-03. Frontmatter flipped to
  approved/nyquist_compliant:true/wave_0_complete:true. An audit-trail HTML
  comment documents the re-validation. Note: direct `pytest` invocation fails
  with `ModuleNotFoundError: No module named 'quirk'` due to PYTHONPATH;
  `python -m pytest` is the project standard.
- **Phase 35**: VALIDATION.md did not exist. Created with full Test
  Infrastructure / Sampling Rate / Per-Task Verification Map / Wave 0 / Manual /
  Sign-Off sections. Verified by `python -m pytest tests/test_cbom*.py -q`
  → 101 passed, 1 skipped.

## Task 3 — Phase 36 Gating Checks (D-06 Checkpoint)

Three gating checks for the `wave_0_complete: false → true` flip:

| Check | Result |
|-------|--------|
| `36-VERIFICATION.md status: approved` | ❌ `human_needed` |
| `36-UAT.md` sign-off marker | ✅ `[testing complete]` present |
| `python -m pytest -x -q` green on main | ❌ See cascade below |

### pytest cascade

A series of pre-existing reds surfaced. Three were stale Phase 37-01 oversights
(version sweep didn't reach `tests/`); one was a pre-existing real regression.

| Failure | Class | Resolution |
|---------|-------|------------|
| `tests/test_cli_correctness.py::test_version_consistency` (TARGET=4.2.0) | stale | Bumped to 4.4.0 in commit `5808f20` |
| `tests/test_cli_correctness.py::test_no_quirk_scan_references` (5 legacy CLI refs in UAT-SERIES.md) | stale | Replaced `quirk scan` → `quirk --config` on lines 1526, 3866, 4772, 4833, 4835 in commit `dfbe706` |
| `tests/test_packaging.py::test_version_is_4_2_0` | stale | Bumped to 4.4.0 in `dfbe706` |
| `tests/test_v41_gap_closure.py::test_pyproject_version_field_is_4_1_0` | stale | Bumped to 4.4.0 in `dfbe706` |
| `tests/test_v41_gap_closure.py::test_package_manifest_version_is_4_1_0` | stale | Resolved by `python -m pip install -e .` (egg-info refresh) |
| `tests/test_dashboard_wiring.py::test_deps_default_db_path` | environmental flake | Patched `os.path.isfile` to isolate fallback path in `dfbe706` |
| `tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols` | **real regression — DEFERRED** | `/api/scan/latest` returns only KERBEROS in `identity_findings`; SAML/OIDC missing. Predates Phase 37 (added Phase 24, ISSUE-3 from Phase 21). Out of scope for v4.4.0 release. |

After the sweep: `python -m pytest -q` → **662 passed, 7 skipped, 1 failed**
(only the SAML scan-window regression remains).

### User decision

Per AskUserQuestion checkpoint:
1. First decision: "Fix stale 4.2.0 test, then continue"
2. Second decision (after second red surfaced): "Fix UAT-SERIES.md 'quirk scan' refs + flip VERIFICATION"
3. Third decision (after SAML real-bug surfaced): "Skip phase 36 flip + Task 5 only"

**Tasks 3 and 4 deferred.** Phase 36 `wave_0_complete: false` retained.
Surfaced as Deferred Gap #1 in 37-VALIDATION.md.

## Task 5 — Phase 37 VALIDATION.md

Created `.planning/phases/37-gap-closure-and-v4-4-0-release/37-VALIDATION.md`
with all 6 required sections (Test Infrastructure, Sampling Rate, Per-Task
Verification Map, Wave 0 Requirements, Manual-Only Verifications, Validation
Sign-Off) plus an explicit "Deferred Gaps" section documenting the two gaps
that remain open after Phase 37 closes.

## Verification

- `grep -E '^(phase|nyquist_compliant|wave_0_complete):' .planning/phases/{32-email-scanner/32,33-broker-scanner/33,34-motion-intelligence/34,35-cbom-integration/35,37-gap-closure-and-v4-4-0-release/37}-VALIDATION.md` → all show `nyquist_compliant: true`, `wave_0_complete: true`
- `grep '^wave_0_complete:' .planning/phases/36-dashboard-motion-tab/36-VALIDATION.md` → `false` (deferred per user direction)
- `python -m pytest -q` → 662 passed, 7 skipped, 1 failed (SAML regression deferred)

## Commits

- `40a7e2a` — docs(37-04): backfill INFRA-03 Nyquist scenarios into 32/33 VALIDATION.md
- `7a8c161` — docs(37-04): re-validate phase 34 + create phase 35 VALIDATION.md (D-05)
- `5808f20` — fix(37-04): bump stale TARGET 4.2.0 -> 4.4.0 in test_version_consistency
- `dfbe706` — fix(37-04): sweep stale version pins + UAT-SERIES legacy CLI refs

## Deviations

1. **Tasks 3 + 4 deferred** — phase 36 `wave_0_complete: false → true` flip skipped
   per user direction after the SAML scan-window regression (out-of-scope) was
   surfaced. Documented as Deferred Gap #1 in 37-VALIDATION.md.
2. **Plan 37-01 cleanup** — discovered four additional stale version pins in
   `tests/` that the original Plan 37-01 grep missed (it only swept `quirk/`).
   Treated as corrective Plan 37-04 work since they blocked the D-06 pytest gate.
3. **Plan-checker invocation** — `gsd-sdk query plan-checker.run --phase NN`
   does not exist as a SDK subcommand. Substituted direct test execution as
   the authoritative validation evidence per D-05's no-rubber-stamping rule.
