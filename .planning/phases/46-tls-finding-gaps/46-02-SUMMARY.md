---
phase: 46-tls-finding-gaps
plan: 02
subsystem: risk-engine
tags: [risk-engine, severity, tls, findings, d-02, d-04]
status: complete
type: execute
wave: 2
requires:
  - "Plan 46-01 (CryptoEndpoint.chain_verified column)"
provides:
  - "TLS-FIND-01 expired-cert CRITICAL severity"
  - "TLS-FIND-02 self-signed-cert HIGH severity (split branch)"
  - "TLS-FIND-03 untrusted-CA MEDIUM severity (new dedicated branch)"
  - "TLS-FIND-04 RSA<2048 HIGH severity (independent per D-02)"
  - "TLS-FIND-05 EC<256 HIGH severity (independent per D-02)"
  - "_chain_verified() direct-column-first lookup"
  - "D-04 mutual exclusivity between self-signed and untrusted-CA"
  - "D-02 multi-defect independence (no rollup)"
affects:
  - "quirk/engine/risk_engine.py"
  - "tests/test_risk_engine.py"
  - "tests/test_risk_engine_cert_defects.py"
tech_stack:
  added: []
  patterns:
    - "Sentinel-object getattr() probe so direct column 'False' is distinguishable from 'unset'"
    - "Mutually exclusive if/elif within an independent block (D-04 inside D-02)"
key_files:
  created:
    - "tests/test_risk_engine_cert_defects.py"
    - ".planning/phases/46-tls-finding-gaps/46-02-SUMMARY.md"
  modified:
    - "quirk/engine/risk_engine.py"
    - "tests/test_risk_engine.py"
decisions:
  - "[46-02] _chain_verified() uses _SENTINEL = object() to distinguish a column value of None (indeterminate) from a missing attribute (legacy pre-Phase-46 ORM row); only after both attribute-presence and not-None checks does the helper return bool — preserves tri-state semantics from Plan 46-01"
  - "[46-02] D-04 implementation chose if/elif (not two independent ifs) within a single block: when issuer == subject, the untrusted-CA branch is structurally unreachable, eliminating any mutual-exclusivity bug surface"
  - "[46-02] D-02 multi-defect independence enforced by leaving the cert-trust if/elif block separate from the expired/RSA/EC branches above and below it — the four cert-defect classes share NO control-flow"
  - "[46-02] Test A6 (EC<256) uses cert_pubkey_alg='ECDSA' to match the engine's existing branch (alg.strip().upper() == 'ECDSA'); the plan's draft snippet used 'ec' which would not have triggered the branch — used the ECDSA spelling to actually exercise live code"
metrics:
  duration: "~10 minutes"
  completed: 2026-05-03
---

# Phase 46 Plan 02: Risk-Engine Cert-Defect Severity & Branch Split Summary

**One-liner:** Bumps expired-cert severity to CRITICAL and self-signed to HIGH, splits the legacy combined `(issuer==subject) OR cv is False` finding into two mutually exclusive branches (HIGH self-signed + MEDIUM untrusted-CA) per D-04, and upgrades `_chain_verified()` to read the new `ep.chain_verified` column from Plan 46-01 (legacy `tls_capabilities_json` blob retained as fallback). Closes TLS-FIND-01..05 finding logic; D-02 multi-defect independence preserved (a cert with three defects emits three findings, never a rollup).

## What Was Built

### 1. Severity bumps (`quirk/engine/risk_engine.py`)

| Branch | Before | After | Line (post-edit) |
|--------|--------|-------|------------------|
| Expired cert (TLS-FIND-01) | HIGH | CRITICAL | 364 |
| Self-signed cert (TLS-FIND-02) | MEDIUM (combined) | HIGH (dedicated branch) | 397 |
| Untrusted CA (TLS-FIND-03) | MEDIUM (combined) | MEDIUM (dedicated branch) | 410 |

### 2. D-04 branch split (`quirk/engine/risk_engine.py:386-425`)

The legacy `if (cert_issuer == cert_subject) or cv is False:` single-finding branch
was replaced with two mutually exclusive branches:

```python
is_self_signed = bool(cert_issuer and cert_subject and cert_issuer == cert_subject)
if is_self_signed:
    findings.append({"severity": "HIGH",
                     "title": "TLS certificate is self-signed",
                     ...})
elif cert_issuer and cert_subject and cert_issuer != cert_subject and cv is False:
    findings.append({"severity": "MEDIUM",
                     "title": "TLS certificate issued by untrusted CA",
                     ...})
```

The if/elif structure is intentional — when `issuer == subject` is true, the
untrusted-CA branch is structurally unreachable, so D-04 mutual exclusivity is
guaranteed at the language level rather than relying on dynamic state.

The block as a whole is independent of the expired (line 364) and RSA/EC
(lines 442+) branches, preserving D-02 multi-defect independence (no shared
control-flow, no rollup).

### 3. `_chain_verified()` direct-field-first upgrade (`quirk/engine/risk_engine.py:136-159`)

```python
_SENTINEL = object()

def _chain_verified(ep):
    cv_direct = getattr(ep, "chain_verified", _SENTINEL)
    if cv_direct is not _SENTINEL and cv_direct is not None:
        return bool(cv_direct)
    # legacy tls_capabilities_json blob fallback (unchanged)
    ...
```

The `_SENTINEL` guard distinguishes "attribute missing" (legacy ORM row written
before Plan 46-01) from "column present but None" (Phase 46 row where the
verify pre-pass got a network error). Only when the column is missing OR
explicitly None does the helper fall through to the JSON-blob fallback, which
keeps backward compat with old rows that were never re-scanned.

### 4. Test updates (`tests/test_risk_engine.py`)

| Old test | Action | New severity / title |
|----------|--------|----------------------|
| `test_expired_cert_produces_high_finding` | renamed → `test_expired_cert_produces_critical_finding` | CRITICAL |
| `test_self_signed_issuer_eq_subject_produces_medium` | renamed → `test_self_signed_issuer_eq_subject_produces_high` | HIGH; new title `"TLS certificate is self-signed"`; D-04 negative-assert on untrusted-CA |
| `test_chain_unverified_false_produces_medium` | unchanged name; updated title to `"TLS certificate issued by untrusted CA"`; added D-04 negative-assert on self-signed |
| `test_chain_verified_true_no_finding` | updated to assert NEITHER new title fires |
| `test_different_issuer_subject_no_caps_no_finding` | updated to assert NEITHER new title fires |
| `test_empty_issuer_subject_no_finding` | updated to assert NEITHER new title fires |
| `test_expired_self_signed_rsa1024_all_fire` | severity assertions added: expired CRITICAL, self-signed HIGH, RSA HIGH; D-04 negative-assert on untrusted-CA |
| `test_expired_beats_expiring_soon` | comment updated (HIGH → CRITICAL) |

### 5. New sentinel suite (`tests/test_risk_engine_cert_defects.py`)

10 new tests covering A1-A10:

| # | Test | Asserts |
|---|------|---------|
| A1 | `test_expired_cert_emits_critical` | Expired → CRITICAL |
| A2 | `test_self_signed_emits_high` | issuer == subject → HIGH self-signed |
| A3 | `test_untrusted_ca_emits_medium_via_direct_column` | issuer != subject AND `chain_verified=False` → MEDIUM untrusted-CA |
| A4 | `test_d04_self_signed_does_not_also_emit_untrusted_ca` | D-04: only HIGH self-signed fires when both conditions met |
| A5 | `test_rsa_1024_emits_high` | RSA<2048 → HIGH |
| A6 | `test_ecdsa_192_emits_high` | ECDSA<256 → HIGH |
| A7 | `test_d02_multi_defect_emits_three_findings_no_rollup` | expired + self-signed + RSA-1024 → exactly 3 cert-defect findings |
| A8a | `test_chain_verified_prefers_direct_column` | `_chain_verified()` returns column value when set |
| A8b | `test_chain_verified_direct_column_wins_over_json_blob` | column True overrides JSON-blob False |
| A9 | `test_chain_verified_falls_back_to_json_when_column_none` | column None → JSON blob consulted |
| A10 | `test_chain_verified_none_does_not_fire_untrusted_ca` | indeterminate `cv=None` does NOT trigger untrusted-CA |

## Test Results

```
$ python -m compileall quirk tests
(clean)

$ python -m pytest tests/test_risk_engine.py tests/test_risk_engine_cert_defects.py -x -q
34 passed in 0.04s

$ python -m pytest tests/ -x -q --ignore=tests/test_cbom_schema_validation.py
739 passed, 2 skipped, 17 deselected, 70 warnings in 5.47s
```

`test_cbom_schema_validation.py` excluded per Plan 46-01 SUMMARY.md note: pre-existing
`MissingOptionalDependencyException` for `cyclonedx-python-lib[json-validation]`,
unrelated to this plan.

## Acceptance Criteria

| Criterion | Result |
|-----------|--------|
| `grep -v '^#' quirk/engine/risk_engine.py | grep -c "Self-signed or untrusted"` returns 0 | **0** ✅ |
| `grep -c "TLS certificate is self-signed"` returns ≥ 1 | **1** ✅ |
| `grep -c "TLS certificate issued by untrusted CA"` returns ≥ 1 | **1** ✅ |
| `grep -c "_SENTINEL = object"` returns 1 | **1** ✅ |
| Expired branch contains "CRITICAL" | ✅ (line 364) |
| `pytest tests/test_risk_engine.py -x -q` passes | ✅ (24 passed) |
| `pytest tests/test_risk_engine_cert_defects.py -x -q` passes 10+ tests | ✅ (10 passed) |
| Full suite no NEW regressions vs baseline | ✅ (739 passed; baseline was 728+11 from Plan 46-01) |
| `python -m compileall quirk/engine/risk_engine.py` exits 0 | ✅ |

## Deviations from Plan

### 1. [Process — parallel-staging race] Plan-02 file changes were captured by Plan 46-03's commit

- **Found during:** task commit step (after all code + tests were already verified-green).
- **Issue:** Plan 46-02 and Plan 46-03 were running in parallel in the same working
  copy. After I staged my three files (`risk_engine.py`, `test_risk_engine.py`,
  `test_risk_engine_cert_defects.py`) and just before I executed `git commit`, Plan
  46-03 ran its own `git add -A` (or equivalent broad add) and committed first as
  `386e1bd "feat(46-03): add tls-cert-defects compose profile + oracle/README
  updates"`. That commit therefore contains my Plan 46-02 changes alongside
  46-03's chaos-lab files, and my own follow-up `git commit` had nothing to commit.
- **Net effect:** All Plan 46-02 code and tests are present on the branch and the
  full test suite passes. Only the commit-message attribution is wrong: the work
  is on disk and in history, just under a 46-03 SHA.
- **Why I did NOT rewrite history:** The user instructions, the project CLAUDE.md
  policy, and `<destructive_git_prohibition>` all forbid `git reset --hard` /
  history rewrite — and rewriting `386e1bd` would also rewind 46-03's chaos-lab
  work, which was correctly authored. The acceptable cost is mis-attributed
  commit message, which this SUMMARY.md records explicitly.
- **Files modified by 46-02 inside `386e1bd`:** `quirk/engine/risk_engine.py`,
  `tests/test_risk_engine.py`, `tests/test_risk_engine_cert_defects.py`.
- **Recommendation for future:** When two plans in the same wave touch shared
  infrastructure (here both touched `quirk/engine/risk_engine.py` — 46-02 split
  the cert-trust branch, 46-03 did not but the orchestrator may not have known
  that), serialize them or run each in its own worktree.

### 2. [Engine reality vs plan draft] Test A6 uses `cert_pubkey_alg="ECDSA"` not `"ec"`

- The plan's behavior text said `cert_pubkey_alg="ec"` for Test A6, but the
  existing engine branch at the post-edit line 471 matches
  `cert_pubkey_alg.strip().upper() == "ECDSA"`. Using `"ec"` would have produced
  zero findings and the test would have failed for the wrong reason.
- This is not a plan revision — the engine matching for ECDSA was not in the
  plan's mutation scope (we were only changing severity / branch shape, not
  alg matching). Test was written to actually exercise the live branch.
- Recorded here per `<deviation_rules>` Rule 3 transparency.

### Pre-existing Issues (NOT fixed — out of scope)

- `tests/test_cbom_schema_validation.py` continues to fail on
  `MissingOptionalDependencyException` for `cyclonedx-python-lib[json-validation]`.
  Documented in 46-01-SUMMARY.md; out of scope for 46-02. Test run command excluded
  via `--ignore`.

## TDD Gate Compliance

This plan was authored as `tdd="true"` in a single landing rather than a
RED → GREEN split. The new test file (`test_risk_engine_cert_defects.py`) and
the engine edits ship together inside `386e1bd`. There is no separate `test(...)`
RED commit. Justification: the plan's scope is small and the existing
`test_risk_engine.py` already exercised the legacy code paths — those four tests
were the de-facto RED tests, failing immediately when the engine was edited
without test updates, hence the plan's explicit instruction to update them in
the SAME commit as the engine change.

## Self-Check: PASSED

- `quirk/engine/risk_engine.py:136-159` — `_chain_verified()` upgraded with
  `_SENTINEL` guard (verified: `grep -n "_SENTINEL" quirk/engine/risk_engine.py`
  returns lines 136 and 149).
- `quirk/engine/risk_engine.py:364` — expired severity is CRITICAL (verified).
- `quirk/engine/risk_engine.py:386-425` — D-04 branch split present with both
  HIGH self-signed and MEDIUM untrusted-CA titles (verified via grep).
- `tests/test_risk_engine.py` — 24 tests pass with renamed/updated assertions
  (verified: `pytest tests/test_risk_engine.py -q` → 24 passed).
- `tests/test_risk_engine_cert_defects.py` — file exists, 10 tests pass
  (verified: `pytest tests/test_risk_engine_cert_defects.py -q` → 10 passed).
- Commit `386e1bd` contains all three files (verified:
  `git show --stat 386e1bd -- quirk/engine/risk_engine.py tests/test_risk_engine.py tests/test_risk_engine_cert_defects.py`).
- Note: no Plan-46-02-attributed commit exists (see Deviation 1). Code is on
  branch under 46-03's SHA.

## Wave 2/3 Hand-off

Plan 46-04 (phase closing) can now mark TLS-FIND-01..05 logic complete in
REQUIREMENTS.md once Plan 46-03 lands its chaos-lab oracle and the end-to-end
scan against the new `tls-cert-defects` profile reproduces the four expected
findings (CRITICAL expired, HIGH self-signed, MEDIUM untrusted-CA, HIGH
RSA-1024) plus optional CRITICAL+HIGH+HIGH on the multi-defect endpoint.
