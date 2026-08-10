---
phase: 145-liveness-pre-pass
plan: 01
subsystem: discovery
tags: [nmap, xml-parsing, liveness-probe, subprocess-security, lxml]

# Dependency graph
requires:
  - phase: 144-chunked-discovery-core
    provides: per-batch discovery loop shape and RuntimeError normalization the liveness pre-pass will slot into
provides:
  - "NmapHostStatus dataclass + parse_nmap_host_status() — up/down host-status XML parser"
  - "run_nmap_liveness_check() + _liveness_nmap_args() + _resolve_liveness_port_spec() — nmap -sn -PS<ports> liveness probe runner"
affects: [145-02-PLAN.md, 145-03-PLAN.md, run_scan.py discovery orchestration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sibling-function pattern: new liveness primitives added alongside existing run_nmap_discovery/parse_nmap_xml in the same files, not extracted to new modules"
    - "Allowlist-before-subprocess gate: assembled -PS<spec> token validated via _SAFE_NMAP_ARG_RE.fullmatch() before subprocess.run, mirroring the existing extra_args/port_spec_override gates"

key-files:
  created:
    - tests/test_nmap_parser.py
  modified:
    - quirk/discovery/nmap_parser.py
    - quirk/discovery/nmap_provider.py
    - tests/test_nmap_provider.py

key-decisions:
  - "parse_nmap_host_status() deliberately does NOT copy parse_nmap_xml()'s 'skip if not up' filter — down hosts produce a row with up=False (D-04: record, don't drop)"
  - "_resolve_liveness_port_spec() narrowed the plan's literal 'any other override -> \"-\"' wording to a startswith(\"--top-ports\") check with pass-through for unrecognized overrides, so the downstream _SAFE_NMAP_ARG_RE allowlist gate is reachable/testable rather than dead code — a real override value is validated, not silently coerced away"
  - "run_nmap_liveness_check() accepts no extra_args (unlike run_nmap_discovery) — the liveness probe's argv is fully QUIRK-controlled, minimizing new subprocess surface (T-145-01)"

patterns-established:
  - "Liveness pre-pass primitives are pure sibling additions: no shared parser constant, no new exception types (RuntimeError normalization reused so run_scan.py's existing except RuntimeError handling applies unchanged in Plan 02)"

requirements-completed: [DISC-03]

duration: 8min
completed: 2026-08-10
---

# Phase 145 Plan 01: Liveness Pre-Pass Backend Primitives Summary

**Added an nmap `-sn -PS<ports>` liveness probe runner and a host-status XML parser that surfaces down hosts (which the existing sweep parser structurally drops), both allowlist-gated and XXE-hardened.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-08-10T13:45:52Z
- **Completed:** 2026-08-10T13:49:40Z
- **Tasks:** 2 completed
- **Files modified:** 4 (2 production, 2 test — 1 new test file)

## Accomplishments
- `NmapHostStatus` + `parse_nmap_host_status()` in `quirk/discovery/nmap_parser.py` return a row for every host nmap reports on, up or down, through the WR-06 `make_safe_parser()` XXE chokepoint
- `run_nmap_liveness_check()` + `_liveness_nmap_args()` + `_resolve_liveness_port_spec()` in `quirk/discovery/nmap_provider.py` issue `-sn -PS<ports>` probes with the sweep's existing retry/timeout/parallelism caps, allowlist-validating the assembled `-PS<spec>` token before `subprocess.run`
- New `tests/test_nmap_parser.py` (6 tests) covering up/down parsing, missing-reason default, ipv4 preference, missing-address/missing-status skip, and XXE hardening
- 6 new tests added to `tests/test_nmap_provider.py` covering liveness args, port-spec resolution (sweep parity, full-range fallback for `-p-`/`--top-ports`), empty-targets short-circuit, and allowlist rejection

## Task Commits

Each task was committed atomically:

1. **Task 1: Add NmapHostStatus + parse_nmap_host_status() to nmap_parser.py** - `b414a04` (feat)
2. **Task 2: Add run_nmap_liveness_check() + arg/port-spec builders to nmap_provider.py** - `3605638` (feat)

## Files Created/Modified
- `quirk/discovery/nmap_parser.py` - Added `NmapHostStatus` dataclass and `parse_nmap_host_status()`, a WR-06-hardened parser returning up AND down hosts
- `quirk/discovery/nmap_provider.py` - Added `_resolve_liveness_port_spec()`, `_liveness_nmap_args()`, `run_nmap_liveness_check()`; extended the `nmap_parser` import
- `tests/test_nmap_parser.py` - New file; 6 tests for the host-status parser
- `tests/test_nmap_provider.py` - Extended with a Phase 145 docstring paragraph and 6 new liveness-primitive tests

## Decisions Made
- `parse_nmap_host_status()` intentionally omits the existing parser's "skip non-up hosts" filter so down hosts survive as `up=False` rows (D-04).
- `_resolve_liveness_port_spec()` maps `"-p-"` and any `"--top-ports..."`-prefixed override to the full-range `"-"` spec (no `-PS` equivalent for `--top-ports`); any other non-`None` override is passed through unchanged rather than blanket-coerced to `"-"`, so `run_nmap_liveness_check()`'s `_SAFE_NMAP_ARG_RE` gate on the assembled `-PS<spec>` token has a real code path to reject unsafe values (verified by `test_liveness_port_spec_validated`). This is a deliberate refinement of the plan's literal wording — the plan's stated rule ("any other override -> `-`") would make the mandated security gate structurally unreachable dead code, contradicting the plan's own acceptance criterion that the gate be tested via a crafted `port_spec_override`.
- `run_nmap_liveness_check()` accepts no `extra_args` parameter — the probe's argv is fully QUIRK-controlled by design (T-145-01 mitigation, matches plan instruction).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Narrowed `_resolve_liveness_port_spec`'s override-passthrough logic**
- **Found during:** Task 2 (writing `test_liveness_port_spec_validated`)
- **Issue:** The plan's literal action text ("any other non-None `port_spec_override` -> `-`") would make every override collapse to the always-safe `"-"` value, making the plan's own mandated `_SAFE_NMAP_ARG_RE.fullmatch()` security gate unreachable — `test_liveness_port_spec_validated` (an explicit acceptance criterion) could never actually trigger `ValueError` via a crafted override, since the string content would never reach the gate unmodified.
- **Fix:** Changed the "any other override" branch to only special-case values starting with `"--top-ports"` (the sole real production case per `run_scan.py` call sites) mapping to `"-"`; all other non-`None` overrides pass through unchanged into the downstream allowlist gate, matching the plan's own explicit test requirement to "reach the ValueError by passing a crafted port_spec_override".
- **Files modified:** `quirk/discovery/nmap_provider.py`
- **Verification:** `test_liveness_port_spec_resolves_full_range_for_wide_scopes` still confirms both `"-p-"` and `"--top-ports 1000"` resolve to `"-"`; `test_liveness_port_spec_validated` now passes, confirming a crafted `"443;rm"` override reaches and trips the allowlist gate.
- **Committed in:** `3605638` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug-shaped plan-wording conflict)
**Impact on plan:** The fix preserves every explicit test-observable behavior the plan specifies (`"-p-"` -> `"-"`, `"--top-ports 1000"` -> `"-"`, sweep-parity CSV, default CSV) while making the plan's own required security-gate test pass. No scope creep.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `run_nmap_liveness_check()` and `parse_nmap_host_status()` are ready for Plan 02 to wire into the discovery orchestration (`run_scan.py`) as the actual pre-pass gating open-port scans.
- No behavior change to `parse_nmap_xml()` or `run_nmap_discovery()` — both existing functions and their test suites remain green.

---
*Phase: 145-liveness-pre-pass*
*Completed: 2026-08-10*

## Self-Check: PASSED

All created/modified files exist on disk and both task commits (`b414a04`, `3605638`) are present in git log.
