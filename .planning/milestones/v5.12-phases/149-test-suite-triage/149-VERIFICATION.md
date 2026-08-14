---
phase: 149-test-suite-triage
verified: 2026-08-12T06:01:07Z
status: passed
score: 3/3 must-haves verified
overrides_applied: 0
---

# Phase 149: Test Suite Triage Verification Report

**Phase Goal:** Every pre-existing full-suite test failure has an explicit, written disposition, so
the scope of the green-baseline work in Phase 150 is known rather than guessed
**Verified:** 2026-08-12T06:01:07Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every test failing in a clean full-suite run appears in a written triage ledger with fixed/quarantined-with-reason/deleted-as-obsolete | ✓ VERIFIED | `docs/test-triage-149.md` has 117 test-ID rows across 9 clusters (+ CR-01 addendum row). Disposition-column tally: 75 quarantined-xfail, 22 quarantined-skip, 2 deleted, 4 environment-fix-applied, 2 fixed, 1 not-reproducible, 1 environment-fix+xfail, and 10 "superseded by Plan 11" rows — 117 total, zero empty Disposition/Sub-reason cells (`awk` scan for empty pipe-fields returned none), zero duplicate test IDs (`sort \| uniq -d` empty). |
| 2 | The ledger's total failure count matches the actual full-suite run — no failure is left unclassified | ✓ VERIFIED | Ran `.venv/bin/python -m pytest -q -m ""` fresh (project's actual venv, not a global interpreter) end-to-end: **3087 passed, 42 skipped, 82 xfailed, 0 failed** in 306s — zero `FAILED` lines in output. This is the exact count the post-review fix commit (`d07b824`) predicted, and it corroborates the ledger's corrected "green modulo known intermittent classes" framing (not the earlier, review-flagged unconditional "0 failed" claim). |
| 3 | Quarantined tests are marked in a machine-checkable way (explicit skip/xfail referencing the ledger), not silently passing or invisibly excluded | ✓ VERIFIED | `tests/skip_registry.py` has 105 `pre_existing_triage_149` entries; `tests/test_skip_registry.py`'s AST walker enforces `pytest.skip`/`importorskip`/`@skipif`/`@skip`/`@xfail` via `TESTS_DIR.rglob("*.py")` (recursive — covers `tests/scanner/`). `pytest tests/test_skip_registry.py -q -m ""` → 1 passed (meta-gate green). 201 `TRIAGE-149:` reason-string occurrences found across `tests/*.py` + `tests/scanner/*.py`, each citing `docs/test-triage-149.md#<anchor>`. |

**Score:** 3/3 truths verified

### CR-01 Fix Verification (Critical Issue from 149-REVIEW.md)

The code review (`149-REVIEW.md`) found one CRITICAL issue: Plan 11's ledger claimed an
unconditional "0 failed" full-suite baseline, but `tests/test_dashboard_trends.py::test_trends_timeline_empty`
(same shared-cache SQLite root cause as Cluster 5) was an orphaned failure missed by the
reconciliation sweep. Follow-up commit `d07b824` (`fix(149): quarantine CR-01 orphaned
test_dashboard_trends.py flake`) addresses this:

| Check | Result |
|-------|--------|
| `xfail` marker added at `tests/test_dashboard_trends.py:347` on `test_trends_timeline_empty` | ✓ Confirmed — `reason="TRIAGE-149: shared in-memory SQLite cache pollution..."`, `strict=False` |
| `tests/skip_registry.py` entry added (line 217, `pre_existing_triage_149` category) | ✓ Confirmed — cites the same root cause as `test_sensor_push_id_revalidation.py` |
| Ledger gets a 117th row under Cluster 5 | ✓ Confirmed — row at `docs/test-triage-149.md:113`, cross-referenced with a `#reconciliation-cr-01-test_dashboard_trendspy-orphaned-flake` anchor |
| Reconciliation section's "0 failed" language corrected | ✓ Confirmed — `docs/test-triage-149.md:391-407` now reads "green modulo the known intermittent classes below" instead of an unconditional flat claim; "Net result" section (line ~511) reworded to match |
| Meta-gate (`test_skip_registry.py`) still green after the fix | ✓ Confirmed — ran directly, 1 passed |
| Fresh full-suite run reproduces 0 failed with the new marker live | ✓ Confirmed — independent run in this verification session: 3087 passed, 42 skipped, 82 xfailed, 0 failed |

**Ledger internal consistency (checked for other similar gaps beyond CR-01):**

- No other `TBD`/`FIXME`/`XXX` unreferenced debt markers found in `docs/test-triage-149.md` or `tests/skip_registry.py`.
- Deferred items noted mid-execution (`deferred-items.md`, 149-04's `test_no_quirk_scan_references` and 149-06's 6 `test_openapi_scanner.py` extras-gap failures) were cross-checked: `test_no_quirk_scan_references` **does** have a ledger row (Group D1, `docs/test-triage-149.md:309`) — it was picked up by a later plan, not left as a gap. The 6 `test_openapi_scanner.py` extras-availability failures noted as sandbox-specific/out-of-scope in `deferred-items.md` do not reproduce in the project's own `.venv` (confirmed: fresh full-suite run in `.venv` is 0 failed, consistent with those failures being an artifact of the discovery sandbox's package set, not this environment's).
- One methodological note for this verification: an initial full-suite run using a global `/opt/homebrew/bin/pytest` (wrong interpreter, not the project's `.venv`) surfaced 11 unrelated failures (`test_bacnet_scanner.py`, `test_modbus_scanner.py`, `test_openapi_scanner.py` — missing/mismatched optional extras in that global environment). This was an environment-selection error on the verifier's part, not a ledger gap; re-running via `.venv/bin/python -m pytest` (the project's actual toolchain) reproduced the ledger's claimed 0-failed result exactly.
- Review Warnings WR-01 (stale `optional_extra` doc comment), WR-02 (`otics` CBOM synthesizer gap — no tracked Phase 150 backlog ticket yet, only a doc cross-reference), and WR-03 (`test_route_coverage.py` exemption-set precedent) were **not** fixed post-review, but all three are already explicitly documented in the ledger with Phase-150-follow-up framing (e.g. `docs/test-triage-149.md:308` for WR-02, `:206` for WR-03) — consistent with the phase's "quarantined-with-reason" disposition option, not silent gaps. These remain open WARNING-level follow-ups for Phase 150 planning, not BLOCKERs to SUITE-01.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/test-triage-149.md` | Full ledger, one row per pre-existing failure, with reconciliation section | ✓ VERIFIED | 529 lines, 117 rows, 9 cluster headings, reconciliation + CR-01 addendum sections present |
| `tests/skip_registry.py` | `ALLOWED_SKIPS` with `pre_existing_triage_149` category entries for every quarantined test | ✓ VERIFIED | 105 `pre_existing_triage_149` entries; D-04 drift repaired (meta-gate green) |
| `tests/test_skip_registry.py` | AST walker enforcing skip/skipif/skip-mark/xfail-mark registration, recursive over `tests/` | ✓ VERIFIED | `rglob("*.py")` (covers `tests/scanner/`), walker checks `pytest.skip`/`importorskip` calls + `skipif`/`skip`/`xfail` decorators |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Quarantine markers (`xfail`/`skip` `reason=`) | `docs/test-triage-149.md` ledger anchors | `TRIAGE-149: ...; see docs/test-triage-149.md#<anchor>` string convention | ✓ WIRED | 201 `TRIAGE-149:` occurrences across `tests/*.py` + `tests/scanner/*.py`, each citing a ledger anchor |
| `tests/test_skip_registry.py` | `tests/skip_registry.py` | `ALLOWED_SKIPS` import + `_allowed()` line-tolerance match | ✓ WIRED | Meta-gate passes (`1 passed`), confirming every live marker resolves against a registry entry |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Meta-gate is green | `.venv/bin/python -m pytest tests/test_skip_registry.py -q -m ""` | `1 passed` | ✓ PASS |
| Fresh full-suite run matches ledger's claimed baseline | `.venv/bin/python -m pytest -q -m ""` | `3087 passed, 42 skipped, 82 xfailed, 0 failed` in 306s | ✓ PASS |
| No unregistered/undocumented debt markers in phase-touched files | `grep -n "TBD\|FIXME\|XXX" docs/test-triage-149.md tests/skip_registry.py` | (no matches) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SUITE-01 | All 11 plans (149-01 through 149-11) | Every pre-existing full-suite failure (~102, red since roughly Phase 97) has an explicit written disposition — fixed, quarantined with a reason, or deleted as obsolete | ✓ SATISFIED | 117-row ledger with zero empty dispositions; independently-reproduced 0-failed fresh full-suite run in the project's own `.venv`; REQUIREMENTS.md row already marked `Complete` and this verification confirms that status holds |

No orphaned requirements: REQUIREMENTS.md maps only SUITE-01 to Phase 149, and all 11 plans declare `requirements: [SUITE-01]`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found (no TBD/FIXME/XXX, no placeholder/stub patterns) in `docs/test-triage-149.md` or `tests/skip_registry.py` | — | — |

Non-blocking follow-ups carried over from `149-REVIEW.md` (WR-01/WR-02/WR-03, IN-01/IN-02) are
documented in the ledger itself as Phase-150-scoped follow-up items; they do not block SUITE-01's
own completion since the phase's disposition contract (fixed/quarantined-with-reason/deleted) does
not require production-code fixes for every quarantined item — only an explicit, evidence-backed
reason, which all three have.

### Human Verification Required

None. This phase's deliverable (a written triage ledger + machine-checkable quarantine markers) is
fully verifiable via ledger cross-referencing, registry inspection, and a live full-suite pytest run.

### Gaps Summary

No gaps. The one CRITICAL issue identified by code review (CR-01: orphaned
`test_dashboard_trends.py` flake missing from the ledger, contradicting an unconditional "0 failed"
claim) was fixed in a documented follow-up commit (`d07b824`) and independently re-verified in this
session: the xfail marker, skip_registry entry, and ledger row all exist and are internally
consistent, the meta-gate remains green, and a fresh full-suite run in the project's actual `.venv`
reproduces exactly the claimed 0-failed/3087-passed/42-skipped/82-xfailed result. No other orphaned
failures or unclassified tests were found during this verification's independent full-suite runs.

---

_Verified: 2026-08-12T06:01:07Z_
_Verifier: Claude (gsd-verifier)_
