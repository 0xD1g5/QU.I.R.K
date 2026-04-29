---
phase: 37
slug: gap-closure-and-v4-4-0-release
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
updated: 2026-04-29
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for v4.4.0 gap-closure + release phase.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_version.py tests/test_infra03_nyquist_coverage.py -x -q` |
| **Full suite command** | `python -m pytest -x -q` |
| **Estimated runtime** | ~1s quick / ~6s full |

---

## Sampling Rate

- **After every task commit:** Run quick command (Phase 37 owned tests)
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirements | Test Type | Automated Command | Status |
|---------|------|------|--------------|-----------|-------------------|--------|
| 37-01-01 | 01 | 1 | INFRA-01 | grep gate | `grep -r '"4.3.0"' quirk/__init__.py pyproject.toml quirk/cbom/builder.py quirk/reports/writer.py quirk/config.py \| wc -l \| grep -q '^[[:space:]]*0$'` | ✅ green |
| 37-01-02 | 01 | 1 | INFRA-01 | unit | `python -m pytest tests/test_version.py -x -q` | ✅ green (5 passed) |
| 37-02-01 | 02 | 1 | INFRA-02 | TOML parse | `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert d['project']['optional-dependencies']['motion'] == ['quirk[email]', 'quirk[broker]', 'quirk[kafka]']"` | ✅ green |
| 37-02-02 | 02 | 1 | INFRA-02, STRUCT-02, STRUCT-03 | collect | `python -m pytest --collect-only -q` | ✅ green (652 tests collected) |
| 37-03-01 | 03 | 2 | INFRA-03 | unit | `python -m pytest tests/test_infra03_nyquist_coverage.py -x -q` | ✅ green (18 passed) |
| 37-03-02 | 03 | 2 | INFRA-03, STRUCT-01 | grep gate | `grep -c 'session_start=SESSION_START' tests/test_infra03_nyquist_coverage.py \| awk '$1>=18'` | ✅ green (19 occurrences) |
| 37-04-01 | 04 | 4 | INFRA-03 (D-04) | grep gate | `grep -c "Nyquist Scenarios — INFRA-03" .planning/phases/32-email-scanner/32-VALIDATION.md .planning/phases/33-broker-scanner/33-VALIDATION.md` | ✅ green (1+1) |
| 37-04-02 | 04 | 4 | D-05 | file gate | `test -f .planning/phases/35-cbom-integration/35-VALIDATION.md && grep '^nyquist_compliant: true' .planning/phases/34-motion-intelligence/34-VALIDATION.md .planning/phases/35-cbom-integration/35-VALIDATION.md` | ✅ green |
| 37-04-03 | 04 | 4 | D-06 | checkpoint:human-verify | gating checks (VERIFICATION.md status, UAT.md sign-off, pytest -x -q) | ⚠️ DEFERRED — see Manual-Only Verifications |
| 37-04-04 | 04 | 4 | D-06 | grep gate | `grep '^wave_0_complete: true' .planning/phases/36-dashboard-motion-tab/36-VALIDATION.md` | ⏸️ deferred (gated on 37-04-03) |
| 37-04-05 | 04 | 4 | (this file) | file gate | `test -f .planning/phases/37-gap-closure-and-v4-4-0-release/37-VALIDATION.md` | ✅ green |
| 37-05-01 | 05 | 5 | INFRA-04 (release) | grep gate | `grep -c "## \[4\.4\.0\]" CHANGELOG.md \| grep -q '^1$'` | ⬜ pending (Plan 37-05 not yet executed) |
| 37-05-02 | 05 | 5 | INFRA-04 | file gate | `test -f docs/release-notes/4.4.0.md` | ⬜ pending |
| 37-06-01 | 06 | 6 | CLAUDE.md mandatory completion | file gate | `test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-37-Gap-Closure-and-v4-4-0-Release.md` | ⬜ pending (Plan 37-06 not yet executed) |
| 37-06-02 | 06 | 6 | CLAUDE.md mandatory completion | gate | UAT-SERIES.md updated + synced to vault + committed | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ deferred · ⏸️ gated*

---

## Wave 0 Requirements

- [x] `tests/test_version.py` — created by Plan 37-01 (5 regression tests for v4.4.0)
- [x] `tests/test_infra03_nyquist_coverage.py` — created by Plan 37-03 (18 INFRA-03 tests)
- [x] `pyproject.toml` `[motion]` meta-extra — restructured by Plan 37-02
- [x] `.planning/phases/35-cbom-integration/35-VALIDATION.md` — created by Plan 37-04 Task 2

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Phase 36 wave_0_complete gating (D-06) | INFRA-03 | `checkpoint:human-verify` task — requires inspection of three artifacts outside the test harness | 1) `grep '^status:' .planning/phases/36-dashboard-motion-tab/36-VERIFICATION.md` → `approved`; 2) `grep -i 'sign.?off' .planning/phases/36-dashboard-motion-tab/36-UAT.md` → present; 3) `python -m pytest -x -q` → 0 failures. **DEFERRED 2026-04-29:** Check 1 returns `human_needed`; Check 3 shows 1 unrelated SAML scan-window regression (pre-existing, ISSUE-3 from Phase 24). User authorized skipping the flip; phase 36 wave_0_complete remains `false` pending its own gap-closure ticket. |
| CHANGELOG entry for 4.4.0 reads cleanly | INFRA-04 | Markdown narrative quality is editorial, not testable | Render CHANGELOG.md and confirm 4.4.0 section reads well, lists all six plans' outputs, and links to release notes |
| Obsidian Phase 37 note renders with backlinks | CLAUDE.md ritual | Obsidian rendering is a UI concern | Open Digs vault → 20_Dev-Work/QUIRK/Phases/Phase-37-Gap-Closure-and-v4-4-0-Release.md and confirm `[[Roadmap]]`, `[[_QUIRK-Hub]]` resolve |

---

## Deferred Gaps

The following gaps surfaced during Plan 37-04 execution and are NOT closed by Phase 37:

1. **Phase 36 dashboard-motion-tab `wave_0_complete: false`** — gating Check 1 (VERIFICATION.md status) and Check 3 (pytest green) failed. UAT.md is signed off, but VERIFICATION.md remains `human_needed` and one unrelated pre-existing test fails. Resolution requires (a) re-running `/gsd-verify-work 36` to advance VERIFICATION to `approved`, and (b) closing the SAML scan-window regression below.
2. **`/api/scan/latest` `identity_findings` missing SAML/OIDC protocols** — `tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols` failing on main. Pre-existing regression (ISSUE-3 from Phase 24), unrelated to v4.4.0 release scope. Requires its own gap-closure phase.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are flagged as `checkpoint:human-verify`/manual
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (Plan 37-04 Task 3 is the only gap and is explicit)
- [x] Wave 0 covers MISSING references — Plans 37-01 + 37-02 + 37-03 + 37-04 created the necessary harness files
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-29 (with documented deferred gaps in section above)
