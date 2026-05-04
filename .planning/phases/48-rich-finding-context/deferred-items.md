# Phase 48 — Deferred Items (out-of-scope discoveries)

## Pre-existing test failures (not caused by Phase 48)

### tests/test_cbom_schema_validation.py — 19 failures

**Discovered during:** Plan 48-01 baseline `pytest tests/ -m 'not slow'` run.

**Status:** Pre-existing on `QUIRK-v4` branch before Plan 48-01 changes. Verified
by stashing 48-01's working-tree edits and running the same test — failures
reproduce without any Phase 48 modifications.

**Root cause:** docker-compose.yml profile `tls-cert-defects` (introduced by
Phase 46 Plan 46-03) is not registered in `tests/_cbom_profiles.py`
PROFILE_ENDPOINTS, so:

- `test_parametrize_set_matches_docker_compose_profiles` fails directly with
  `In compose but not parametrize: ['tls-cert-defects']`.
- 13 per-profile `test_cbom_validates_against_cyclonedx_1_6[<profile>]` cases
  fail (cascading) because the synthesizer wiring is incomplete for the new
  profile.
- 5 additional related cases fail in the same module for related reasons.

**Scope:** Out of scope for Plan 48-01 (CBOM synthesizer wiring + chaos lab
profile registration; not finding-construction work). Belongs to a follow-up
chaos-lab/CBOM phase.

**Action:** Log here and continue. Do not fix in 48-01.
