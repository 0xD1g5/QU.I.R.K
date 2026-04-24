# Phase 24: Scan-Session Timestamp Isolation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 24-scan-session-timestamp
**Areas discussed:** Parameter design, Kerberos tzinfo normalization, Fix scope,
Test plan count, SAML internal threading, session_start timing, Test placement, ISSUE-3 test scenario

---

## Parameter Design

| Option | Description | Selected |
|--------|-------------|----------|
| Optional, default=None | `session_start=None`; fallback to `datetime.now()` inside scanner. Existing tests pass unchanged. | ✓ |
| Required parameter | All callers must supply it. Enforces correctness but breaks existing tests. | |
| Claude's discretion | Claude picks approach minimizing test churn. | |

**User's choice:** Optional with default=None — backward-compatible fallback inside scanner
**Notes:** Existing tests that call scanner functions without session_start continue to pass.

---

## Kerberos tzinfo Normalization

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — normalize to match | `scanned_at = session_start.replace(tzinfo=None)`. Brings kerberos in line with DNSSEC/SAML. | ✓ |
| No — leave tzinfo as-is | Pass session_start through without stripping. Leave inconsistency for later. | |

**User's choice:** Yes — normalize. kerberos will use `.replace(tzinfo=None)` consistently.

---

## Fix Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Identity scanners only | Surgical fix. TLS/SSH/JWT/container/source scanners not involved in scan-window issue. | ✓ |
| All scanners (hardening) | Pass session_start to every scanner. Larger diff, more existing tests to update. | |

**User's choice:** Identity scanners only — minimal diff.

---

## Test Plan Count

| Option | Description | Selected |
|--------|-------------|----------|
| 2 plans: RED + GREEN | Consistent with phases 17–23. Plan 01 writes failing tests; Plan 02 implements fix. | ✓ |
| 1 plan combined | Single plan for test + implementation. Faster for small fix. | |

**User's choice:** 2-plan TDD structure.

---

## SAML Internal Function Threading

| Option | Description | Selected |
|--------|-------------|----------|
| Compute now in scan_saml_targets, pass it down | `scan_saml_targets` computes `now`, passes as keyword arg to `_parse_saml_metadata` and `_parse_oidc_discovery`. 3 signatures change. | ✓ |
| Pass session_start down to each private function | Each private function receives `session_start=None` and computes `now` themselves. Deeper propagation. | |

**User's choice:** Compute `now` in the public function, pass it down.

---

## session_start Timing

| Option | Description | Selected |
|--------|-------------|----------|
| Just before DNSSEC block | Creates `session_start` at ~line 462, immediately before first identity scanner. Semantically precise. | ✓ |
| Reuse started_utc from run_stats | Derive from existing `run_stats["started_utc"]` at line 165. May be minutes earlier. | |

**User's choice:** Just before DNSSEC block — represents identity scan start specifically.

---

## Test Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Existing scanner test files | session_start unit tests in test_kerberos_scanner.py, test_saml_scanner.py, test_dnssec_scanner.py. | ✓ |
| New test_scan_session_timestamp.py | All ISSUE-3 tests in one focused file. | |
| test_identity_surface.py (integration) | Add alongside IDENT-02/IDENT-03 tests. | |

**User's choice:** Spread across existing scanner test files.

---

## ISSUE-3 Regression Test Scenario

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed session_start stamp check | Pass fixed past datetime to all 3 scanners; assert every endpoint has that exact scanned_at. | |
| API window integration test | TestClient + in-memory DB; insert endpoints with spread scanned_at; call GET /api/scan/latest; assert all 3 protocols appear. | ✓ |
| Claude's discretion | Leave test scenario to planner. | |

**User's choice:** API window integration test — validates full chain from scan → DB → API response.

---

## Claude's Discretion

- Exact test fixture setup style (pytest fixtures vs setUp/tearDown) — follow existing pattern in test_identity_surface.py
- Whether kerberos `now` is computed once at top of function vs inline at each of the 3 endpoint creation sites

## Deferred Ideas

None — discussion stayed within phase scope.
