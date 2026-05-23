---
phase: 97-v5-1-tech-debt-cleanup
plan: "04"
subsystem: test/docs
tags: [credentials, sentinel-leak, test-honesty, coverage-gap, uat-series, obsidian, TD-01, WR-05]
dependency_graph:
  requires: []
  provides: [real-path-sentinel-test, pdf-coverage-gap-annotation, uat-series-97, obsidian-phase-note]
  affects:
    - tests/test_credential_leakage.py
    - docs/UAT-SERIES.md
tech_stack:
  added: []
  patterns: [real-path-mock-injection, unittest.mock.patch, tls-scanner-exception-path, coverage-gap-annotation]
key_files:
  created: []
  modified:
    - tests/test_credential_leakage.py
    - docs/UAT-SERIES.md
decisions:
  - "D-04/WR-05: Routed test_sentinel_not_in_scan_error_json through real _scan_one_fallback exception path via socket.create_connection mock — safe_str applied by production code (tls_scanner.py:465), not test body"
  - "PDF coverage-gap annotation: test_sentinel_not_in_pdf_export_surface now explicitly states it is a DOCUMENTED COVERAGE GAP — no live Playwright render, not mechanical coverage of the PDF renderer"
  - "UAT-97 series: 4 test cases added (scheduler fail-closed, JWT param reject, fuzzer cascade, sentinel real-path)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 97 Plan 04: Sentinel real-path test + PDF coverage-gap + docs sync Summary

**One-liner:** Real-path sentinel test routes SENTINEL through the actual TLS scanner exception handler (safe_str applied by production code, would fail if scrubbing regressed); PDF test annotated as documented coverage gap; UAT-97 series added and Obsidian phase note + vault sync complete.

## What Was Built

### Task 1: Route ≥1 sentinel surface through the real scrub path; annotate PDF as coverage gap (D-04 / WR-05)

**File modified:** `tests/test_credential_leakage.py`

**Real-path test (`test_sentinel_not_in_scan_error_json`):**

Replaced the pre-scrubbed version of `test_sentinel_not_in_scan_error_json` (lines 145-158)
with a genuine real-path test. The prior version called `safe_str` in the test body before
constructing the `CryptoEndpoint`, meaning it asserted on data the test itself had already
scrubbed — it could not catch a regression in the production scrub path.

The new version:
1. Uses `unittest.mock.patch("socket.create_connection", side_effect=sentinel_exc)` to inject
   an `OSError` whose message is `"TLS handshake failed: Authorization: Bearer SENTINEL"` (matching
   the `_SENSITIVE_PATTERNS` bearer-shape regex in `safe_str`).
2. Calls the real `_scan_one_fallback("example.com", 443, 1, False)` — this is the actual
   production scanner function.
3. The production `except Exception as e:` block at `tls_scanner.py:462-465` sets
   `ep.scan_error = f"{cat}: {safe_str(e)}"` — `safe_str` is applied by production code.
4. Asserts `SENTINEL not in json.dumps({"scan_error": ep.scan_error})`.
5. Does NOT call `safe_str` in the test body — the scrub is applied exclusively by production code.

**Why this has teeth:** If `safe_str` were removed from `tls_scanner.py:465`, the exception
message containing the SENTINEL would flow directly into `ep.scan_error`, and the assertion
`SENTINEL not in dumped` would FAIL. This is the distinguishing property vs. the prior test.

**PDF coverage-gap annotation (`test_sentinel_not_in_pdf_export_surface`):**

Added explicit "DOCUMENTED COVERAGE GAP (D-04 / WR-05)" paragraph at the top of the docstring,
stating:
- No live Playwright PDF render is performed
- A live PDF render requires a running server + Playwright Chromium — not mechanically verified
- This test is NOT coverage of the PDF renderer — it is an upstream-linkage assertion only

This prevents the "11 surfaces" coverage claim from overstating what is mechanically verified.

**Verification:** `python -m pytest tests/test_credential_leakage.py -q` — 25 passed.

**Commit:** `4ba0dc3`

### Task 2: Mandatory phase-completion docs sync — UAT-SERIES.md + Obsidian phase note + UAT vault sync

**Files modified:** `docs/UAT-SERIES.md`
**Files created (vault):**
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-97-v5.1-Tech-Debt-Cleanup.md`
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` (synced)

**UAT-SERIES.md updates:**
- Prepended Phase 97 to the `**Last Updated:**` line covering all D-01..D-06 changes (WR-02..WR-06/TD-02)
- Added UAT Series 97 section with 4 test cases:
  - UAT-97-01: Scheduler rejects authenticated config at unconventional path (D-05/WR-06)
  - UAT-97-02: JWT scanner rejects pre-existing api_key param (D-03/WR-04)
  - UAT-97-03: REST fuzzer cascade back-off fires against connection-only-failing host (D-06/TD-02)
  - UAT-97-04: Sentinel leak suite real-path test verification (D-04/WR-05)

**Obsidian phase note:** Written directly to vault filesystem at
`/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-97-v5.1-Tech-Debt-Cleanup.md` with:
- Frontmatter: `project: QU.I.R.K.`, `type: phase`, `status: complete`, `source`, `updated: 2026-05-23`
- Goal statement (v5.1 tech-debt cleanup, orthogonal to v5.2 report work)
- Requirements covered (TD-01, TD-02 with sub-items)
- Success criteria (5 items, all PASSED)
- What Was Built (one subsection per plan: 97-01 through 97-04)
- `[[Roadmap]]` link

**Vault UAT-Series.md sync:** Executed the printf-frontmatter + cat-append + cp pattern per
CLAUDE.md mandatory step 3. File written to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`.

**Commit:** `9561b79` (via gsd-tools commit helper per CLAUDE.md step 4)

## Verification

All acceptance criteria met:

- `python -m pytest tests/test_credential_leakage.py -q` — 25 passed
- `test_sentinel_not_in_scan_error_json` docstring contains "REAL-PATH TEST" — PASS
- No `safe_str` call in the test body for that surface — PASS
- `test_sentinel_not_in_pdf_export_surface` docstring contains "DOCUMENTED COVERAGE GAP" — PASS
- `docs/UAT-SERIES.md` `**Last Updated:**` shows 2026-05-23 with Phase 97 changes — PASS
- Obsidian phase note exists at vault path with `status: complete` frontmatter — PASS
- Vault UAT-Series.md exists and matches updated docs/UAT-SERIES.md — PASS
- `docs/UAT-SERIES.md` committed via gsd-tools commit helper — PASS

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 — real-path sentinel + PDF annotation | `4ba0dc3` | test(97-04): route scan_error sentinel through real scanner scrub path (D-04/WR-05) |
| 2 — UAT-SERIES.md + docs | `9561b79` | docs(phase-97): update UAT-SERIES.md |

## Deviations from Plan

**[Rule 2 - Implicit] Absolute-path safety (#3099):** Initial Edit calls targeted the main repo
path (`/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/tests/...`) instead of the worktree path.
Detected via `git status --short` returning no changes. Copied the corrected file from the main
repo to the worktree path before committing. No functional impact — the file content was correct,
only the target path was wrong initially.

## Known Stubs

None. The real-path test is fully wired to the production scanner path.

## Threat Flags

None. Plan 04 changes are test-honesty improvements and documentation sync:
- T-97-11 (Information Disclosure): strengthens verification of the existing scan_error scrub
  control — a future regression that removes safe_str from the production path would now be
  caught by CI. No control weakened.
- T-97-12 (Information Disclosure): docs/vault notes describe behavior only; no secrets, no
  SENTINEL value, no credential material written to docs or vault.

## Self-Check: PASSED

- `tests/test_credential_leakage.py` — modified, contains "REAL-PATH TEST" and "DOCUMENTED COVERAGE GAP"
- `docs/UAT-SERIES.md` — modified with 2026-05-23 date and UAT-97 series
- Commit `4ba0dc3` — confirmed in git log
- Commit `9561b79` — confirmed in git log
- 25 tests pass in test_credential_leakage.py
- Obsidian phase note at vault path confirmed
- UAT-Series.md vault sync confirmed
