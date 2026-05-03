---
phase: 40-chaos-lab-parity
plan: "01"
subsystem: infra
tags: [bash, lab.sh, docker-compose, chaos-lab, dynamic-parsing]

# Dependency graph
requires:
  - phase: none
    provides: n/a
provides:
  - "_derive_all_profiles() bash helper: derives all 18 compose profiles dynamically at runtime"
  - "profiles subcommand: ./lab.sh profiles prints sorted list of all profiles"
  - "all) arm rewritten: uses dynamic list, no hard-coded profiles"
affects:
  - 40-chaos-lab-parity (subsequent plans reference ./lab.sh profiles for verification)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dynamic profile derivation: grep/yq parser reads docker-compose.yml at runtime, eliminating hard-coded drift"
    - "yq-preferred with grep-fallback: graceful enhancement pattern for optional tooling"

key-files:
  created: []
  modified:
    - quantum-chaos-enterprise-lab/lab.sh

key-decisions:
  - "Extend character class to [a-zA-Z0-9_-] to handle phaseA (uppercase A in profile name) — plan snippet used [a-z0-9_-] which missed phaseA"
  - "Dynamic derivation replaces hard-coded ALL_PROFILES: structurally impossible to drift from docker-compose.yml"
  - "profiles) arm added before down) arm: ./lab.sh profiles lists all 18 sorted profiles"

patterns-established:
  - "Single source of truth: docker-compose.yml is authoritative; lab.sh reads it, never duplicates it"

requirements-completed: [LAB-01, LAB-02]

# Metrics
duration: 2min
completed: 2026-04-29
---

# Phase 40 Plan 01: Dynamic Profile Derivation in lab.sh

**lab.sh ALL_PROFILES replaced with _derive_all_profiles() bash parser reading docker-compose.yml at runtime, adding profiles subcommand, covering all 18 profiles including v4.3+v4.4 additions**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-29T21:29:41Z
- **Completed:** 2026-04-29T21:31:32Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Replaced hard-coded 13-profile ALL_PROFILES list (missing vault, database, storage-s3, email, broker) with `_derive_all_profiles()` helper that parses docker-compose.yml
- Added `profiles)` case arm: `./lab.sh profiles` now prints all 18 profiles alphabetically sorted, one per line
- Rewritten `all)` arm uses `mapfile` to consume parser output with a fail-fast empty-result guard
- Updated `usage()` heredoc with `profiles` entry in Commands block and example in Examples block
- Structural fix: lab.sh can no longer drift from docker-compose.yml by construction (D-14)

## Task Commits

1. **Task 1: Add _derive_all_profiles helper, rewrite all arm, add profiles arm, update usage** - `a1ec2f0` (feat)

**Plan metadata:** TBD (docs commit)

## Files Created/Modified
- `quantum-chaos-enterprise-lab/lab.sh` - Dynamic profile derivation helper + profiles subcommand + rewritten all arm + updated usage heredoc

## Decisions Made
- Extended grep character class from `[a-z0-9_-]` to `[a-zA-Z0-9_-]` to handle `phaseA` profile name (contains uppercase A); plan's verbatim snippet would have produced only 17 profiles — auto-fixed per Rule 1.
- yq preferred over grep (graceful enhancement): if yq is on PATH it handles both inline-array and YAML-list forms; grep fallback handles inline-array only (all that's present in docker-compose.yml today).
- No per-profile up shortcuts added per D-13 — PROFILE_ARGS env-var pattern remains the single scoping mechanism.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Extended character class to handle uppercase profile names**
- **Found during:** Task 1 verification (./lab.sh profiles | wc -l returned 17 instead of 18)
- **Issue:** Plan's verbatim `grep -oE '"[a-z0-9_-]+"'` pattern matched only lowercase letters. Profile `phaseA` has an uppercase `A` and was silently omitted, producing 17 profiles instead of 18.
- **Fix:** Changed character class to `[a-zA-Z0-9_-]` in the grep fallback. Updated comment from `[a-z0-9_-]` to `[a-zA-Z0-9_-]`.
- **Files modified:** `quantum-chaos-enterprise-lab/lab.sh`
- **Verification:** `./lab.sh profiles | wc -l` now returns 18; `./lab.sh profiles | grep -qx phaseA` passes.
- **Committed in:** `a1ec2f0` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Essential correctness fix. The plan's verbatim snippet had a character-class gap. Without the fix, `./lab.sh all` would have silently omitted phaseA from the lab startup. No scope creep.

## Verification Output

```
$ cd quantum-chaos-enterprise-lab && ./lab.sh profiles
broker
cloud
database
dnssec
email
identity
jwt
kerberos
ldaps
phaseA
pki
registry
saml
source
ssh-weak
storage
storage-s3
vault

$ ./lab.sh profiles | wc -l
18

$ bash -n lab.sh && echo OK
OK

$ grep -c '_derive_all_profiles' lab.sh
3
```

All 18 profiles present and sorted. All 5 v4.3+v4.4 profiles (vault, database, storage-s3, email, broker) confirmed. Hard-coded list removed. `_derive_all_profiles` appears 3 times (definition + all arm + profiles arm).

## Issues Encountered
None beyond the character-class auto-fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `./lab.sh profiles` is the foundation verification command for all subsequent 40-xx plans
- 40-02 (README rewrite) and 40-03 (expected_results_v4.md) can reference `./lab.sh profiles` output as canonical profile list
- 40-06 (smoke check / LAB-02) will use `./lab.sh all` which now correctly covers all 18 profiles

## Known Stubs
None. lab.sh is fully functional; `./lab.sh all` will attempt to start all 18 profiles. Actual Docker startup verification is deferred to plan 40-06 (LAB-02 manual smoke check) per the plan's done-criteria note.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: shell-injection-mitigated | quantum-chaos-enterprise-lab/lab.sh | `_derive_all_profiles` grep parser restricts parsed names to `[a-zA-Z0-9_-]`; yq path trusted via sort-u only. Both T-40-01-01 and T-40-01-03 mitigations implemented as specified in threat model. |

---
*Phase: 40-chaos-lab-parity*
*Completed: 2026-04-29*
