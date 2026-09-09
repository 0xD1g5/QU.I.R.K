---
phase: 193-connector-credential-parity
plan: 01
subsystem: api
tags: [connectors, availability, optional-extra, fastapi, dashboard]

requires: []
provides:
  - "CONNECTOR_AVAILABILITY_MAP: 25-key frozen mapping from ConnectorsCfg.enable_* to a live probe source"
  - "probe_connector(flag) / probe_all_connectors() — the single availability helper plans 04 and 06 both call"
affects: [193-04, 193-06]

tech-stack:
  added: []
  patterns:
    - "Frozen-dataclass registry mirroring quirk/util/optional_extra.py's OptionalExtra shape"
    - "Live per-call probing (no caching) via importlib.import_module + getattr, matching optional_extra.py's find_spec/shutil.which idiom"
    - "Run-time-derived guard test deriving the expected flag set from dataclasses.fields(ConnectorsCfg) instead of a hand-written list"

key-files:
  created:
    - quirk/dashboard/api/connector_availability.py
    - tests/test_connector_availability_mapping.py
  modified: []

key-decisions:
  - "enable_gcp/enable_k8s/enable_vault each probe their OWN connector module's *_AVAILABLE flag (not optional_extra.REGISTRY's 'cloud' extra), because REGISTRY's cloud extra ANDs googleapiclient+kubernetes+hvac together and would falsely report e.g. GCP unavailable whenever only the unrelated Kubernetes/Vault SDK is missing"
  - "enable_db uses BOTH extra='db' AND module_flags=(PSYCOPG2_AVAILABLE, PYMYSQL_AVAILABLE) per explicit plan directive, which is stricter (AND) than run_scan.py's own OR-based gate — documented as a deliberate, plan-directed divergence in the module docstring"
  - "enable_smime/enable_adcs/enable_codesign each probe their own scanner module's independent LDAP3_AVAILABLE flag, not optional_extra.REGISTRY's 'identity' extra (which only gates impacket, not ldap3)"
  - "enable_kerberos uses extra='identity' since REGISTRY's impacket gate matches kerberos_scanner.IMPACKET_AVAILABLE exactly"

requirements-completed: [PARITY-02]

duration: 25min
completed: 2026-09-09
---

# Phase 193 Plan 01: Connector Availability Mapping Summary

**Built the single server-side availability helper mapping all 25 `ConnectorsCfg.enable_*` flags to live probe sources (optional-extra registry, per-scanner `*_AVAILABLE` flags, or a binary probe), so the upcoming GET route and job-submit gate can never disagree.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 completed
- **Files modified:** 2 (both new)

## Accomplishments
- `quirk/dashboard/api/connector_availability.py` maps all 25 `enable_*` flags with an explicit, grep-verified disposition — no omissions, no guesses.
- `tests/test_connector_availability_mapping.py` derives its expected flag set from `dataclasses.fields(ConnectorsCfg)` at run time (not a hand-written list) and locks the `always_available` bucket to exactly the two pure behavior toggles.
- Verified live: with the current dev environment (no optional extras installed), 11 of 25 connectors probe as unavailable with non-empty, informative reasons; all extra-gated unavailable entries carry the verbatim `optional_extra.REGISTRY` install hint.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the 25-flag availability mapping module** - `91a939b6` (feat)
2. **Task 2: Run-time-derived D-06 completeness guard test** - `89d56170` (test)

## Files Created/Modified
- `quirk/dashboard/api/connector_availability.py` - `AvailabilitySource`, `ConnectorAvailability`, `CONNECTOR_AVAILABILITY_MAP` (25 entries), `probe_connector`, `probe_all_connectors`
- `tests/test_connector_availability_mapping.py` - 6 run-time-derived guard tests (completeness, no-silent-omission, always_available lock, probe coverage, install_hint verbatim, category vocabulary)

## Decisions Made

See `key-decisions` in frontmatter above. In short: three families (cloud SDK trio, LDAP-based identity scanners, kerberos) needed disposition choices that deviate from a naive 1:1 REGISTRY lookup because the existing `optional_extra.REGISTRY` entries AND multiple unrelated modules together — using them directly would have produced false-unavailable results. All three are documented inline in the module docstring with the specific run_scan.py/scanner-module line evidence.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added an optional `binary` field to `AvailabilitySource`**
- **Found during:** Task 1
- **Issue:** `enable_container` (syft) and `enable_source` (semgrep) gate on external CLI binaries with no Python-importable flag and no `optional_extra.REGISTRY` entry. The plan's locked interface (`AvailabilitySource` with `extra`/`module_flags`/`always_available`/`category`/`label`) has no way to express this, and the guard test explicitly locks `always_available` to exactly `{enable_authenticated_mode, enable_recurring_otics}` — so these two flags could not be honestly dispositioned without either violating that lock or silently reporting "available" regardless of whether syft/semgrep are actually installed.
- **Fix:** Added an optional `binary: Optional[str] = None` field to `AvailabilitySource`, mirroring `OptionalExtra.binary` (Phase 47 / D-08's own precedent in `optional_extra.py`) — probed via `shutil.which(binary)` inside `probe_connector`, never cached. `enable_container`/`enable_source` are the only two entries that use it.
- **Files modified:** `quirk/dashboard/api/connector_availability.py`
- **Verification:** `enable_source` correctly probes `available=False` with reason `"'semgrep' binary not found on PATH"` in this dev environment (neither binary installed); `enable_container` probes `True` here since `syft` happens to be on PATH.
- **Committed in:** `91a939b6` (part of Task 1 commit)

## Threat Flags

None — the module stays within the plan's own threat register (T-193-01 through T-193-04); the added `binary` field follows the identical `shutil.which`-only probe pattern already covered by T-193-02 (DoS: accept, fixed microsecond-scale stdlib calls) and T-193-03 (info disclosure: reason strings never include `find_spec`/`which` return values, only the flag/module/binary name).

## Self-Check: PASSED

- FOUND: quirk/dashboard/api/connector_availability.py
- FOUND: tests/test_connector_availability_mapping.py
- FOUND commit: 91a939b6
- FOUND commit: 89d56170
