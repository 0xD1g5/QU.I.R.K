---
phase: 113-per-sensor-authentication
plan: "03"
subsystem: sensor-auth
tags: [auth, test-cutover, docs, phase-completion, AUTH-03, AUTH-04]
dependency_graph:
  requires:
    - require_sensor_auth middleware (113-02)
    - sensor_push_router split (113-02)
    - revoke-sensor CLI (113-02)
  provides:
    - test_sensor_ingest.py push tests updated to per-sensor auth (all GREEN)
    - test_console_enroll.py AUTH-03 revoked_at=NULL assertion
    - enrollment printout corrected (token IS push credential)
    - operators-guide §8.1.1 per-sensor migration section
    - expected_results_distributed.md oracle updated
    - UAT Series 113 (UAT-113-01..05)
    - Obsidian Phase-113 note
  affects:
    - tests/test_sensor_ingest.py
    - tests/test_console_enroll.py
    - quirk/cli/console_cmd.py
    - quirk/cli/sensor_cmd.py
    - docs/operators-guide.md
    - quantum-chaos-enterprise-lab/expected_results_distributed.md
    - docs/UAT-SERIES.md
tech_stack:
  added: []
  patterns:
    - _seed_token helper (sha256 hash only, secrets.token_urlsafe(32))
    - monkeypatch.delenv(QUIRK_API_TOKEN) on push tests (per-sensor path)
    - Per-sensor migration doc pattern (what changed, steps, lost-token recovery, unaffected tokens)
key_files:
  created: []
  modified:
    - tests/test_sensor_ingest.py
    - tests/test_console_enroll.py
    - quirk/cli/console_cmd.py
    - quirk/cli/sensor_cmd.py
    - docs/operators-guide.md
    - quantum-chaos-enterprise-lab/expected_results_distributed.md
    - docs/UAT-SERIES.md
decisions:
  - test_push_422_replay_window: seed real sensor+token with stale pushed_at (auth check happens before replay window)
  - test_audit_row_written failure path: seed second sensor+token for 422 sub-path (same auth-first constraint)
  - test_unknown_sensor_id_4xx: comment-only update (401 satisfies 400<=status<500; no token row → 401)
  - operators-guide §8.1.1 fully replaced (no dual-accept, D-10 clean cutover model)
  - lab.sh ALL_PROFILES unchanged: no compose profile/port/service added in Phase 113
metrics:
  duration: "22m"
  completed: "2026-05-26"
  tasks: 4
  files: 7
---

# Phase 113 Plan 03: Test Cutover, Docs, Phase Completion Summary

**One-liner:** Push tests updated to per-sensor Bearer tokens (20/20 green), enrollment printout corrected, operators-guide §8.1.1 per-sensor migration, lab oracle updated, UAT-113-01..05 + Obsidian note

## What Was Built

### Task 1: Update existing push tests + enroll test for per-sensor auth

Added `_seed_token(TestingSession, sensor_id, raw_token=None, revoked=False)` helper to
`tests/test_sensor_ingest.py` (same pattern as `test_sensor_auth_per_sensor.py`; mints
`secrets.token_urlsafe(32)`, writes SHA-256 hex digest, supports `revoked=True`).

Updated 7 tests that previously sent `Authorization: Bearer test-token`:

| Test | Fix Applied |
|------|-------------|
| `test_push_413_body_too_large` | Seed any sensor+token; update header; 413 fires before body processing |
| `test_push_409_duplicate_payload` | Seed "sensor-dedup-01" + token; update header |
| `test_push_422_replay_window` | Seed "sensor-replay-01" + token; stale pushed_at triggers 422 after auth |
| `test_push_200_accepted` | Seed "sensor-ok-01" + token; update header |
| `test_audit_row_written` | Success path: seed+token; failure path: seed "sensor-audit-stale-01"+token with stale pushed_at for 422 |
| `test_extra_fields_ignored` | Seed "sensor-extra-01" + token; update header |
| `test_version_skew_graceful` | Seed "sensor-skew-01" + token; update header |

`test_unknown_sensor_id_4xx`: comment-only update explaining 401 is the expected status (no token row → `require_sensor_auth` returns 401; `400 <= status < 500` assertion still holds).

`test_push_requires_auth`: updated `monkeypatch.setenv` to `delenv` (QUIRK_API_TOKEN no longer used for push route); behavior unchanged (no header → 401).

Added AUTH-03 assertion to `test_console_enroll.py`:
```python
assert token_row.revoked_at is None, (
    f"New enrollment must have revoked_at=NULL (active token); got {token_row.revoked_at!r}"
)
```

**Verification:** `pytest tests/test_sensor_ingest.py tests/test_console_enroll.py tests/test_sensor_auth_per_sensor.py -q` — 20/20 passed.

**Commit:** `91f7e3b`

### Task 2: Correct enrollment printout + sensor-side credential semantics (D-11)

Replaced the v5.4 shared-token printout block in `quirk/cli/console_cmd.py` (L216-238):

- **Before:** "This enrollment token is NOT the push credential ... uses CONSOLE'S shared API token (QUIRK_API_TOKEN)"
- **After:** "Bearer token (copy now — shown once, never recoverable)" + NOTE stating token IS the per-sensor push credential, goes in `console_api_token` in `sensor.yaml`, lost=revoke+re-enroll

Added 4-line comment to `quirk/cli/sensor_cmd.py` at the `console_api_token` read (L574) explaining the v5.5 per-sensor model. Wire mechanism (`Authorization: Bearer`) unchanged.

**Verification:** Both files compile clean; `grep -v '^[[:space:]]*#' quirk/cli/console_cmd.py | grep -c "NOT the push credential"` → 0.

**Commit:** `647801e`

### Task 3: Operators-guide migration section + distributed-lab oracle (AUTH-04, no-drift)

Replaced `docs/operators-guide.md` §8.1.1 ("v5.4 shared-token authentication model") with a new
"v5.5 per-sensor authentication model (migration from v5.4)" section covering all four required
points (D-10/D-11):

1. **What changed:** per-sensor tokens replace shared QUIRK_API_TOKEN at POST /api/sensor/push; clean cutover (no dual-accept)
2. **Migration steps:** `quirk console enroll` per sensor, copy token, set `console_api_token` in `sensor.yaml` on sensor host
3. **Lost token recovery:** `quirk console revoke-sensor <sensor_id>` then re-enroll to mint fresh token + sensor_id
4. **QUIRK_API_TOKEN unaffected:** still governs operator/dashboard auth

Updated §8.2 and §8.5 (Windows) enrollment examples to remove `--api-token <console-QUIRK_API_TOKEN>` references and describe placing the per-sensor enrollment token in `sensor.yaml`.

Updated `quantum-chaos-enterprise-lab/expected_results_distributed.md` Authentication block:
- v5.4 shared-token model description replaced with v5.5 per-sensor token model
- Step table updated: `quirk console enroll` prints per-sensor token (not audit-only); `quirk sensor enroll` writes sensor.yaml without `--api-token`; sensor push steps explain per-sensor token validated via SHA-256
- CBOM/score expectations unchanged (no MERGE-03 impact)

**No compose profile / port / service changes:** `lab.sh ALL_PROFILES` and chaos-lab README are unchanged — CLAUDE.md no-drift rule satisfied.

**Verification:** `grep -ic "per-sensor" docs/operators-guide.md` → 12; `grep -iq "revoke-sensor" docs/operators-guide.md` exits 0.

**Commit:** `139ae89`

### Task 4: Mandatory phase-completion docs + Obsidian sync (CLAUDE.md)

**Obsidian phase note:** Created `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-113-Per-Sensor-Authentication.md` via the Write tool. Frontmatter (`status: complete`, `type: phase`); Goal; Requirements Covered AUTH-01..04; Success Criteria (5 items); What Was Built (one subsection per plan sourced from SUMMARY files); Quality Gates; Phase status table; `[[Roadmap]]` link.

**UAT-SERIES.md updates:**
- Version bumped to `5.5.0-dev`
- `Last Updated` header prepended with Phase 113 summary
- Added `## UAT Series 113 — Per-Sensor Authentication` section with 5 test items:
  - UAT-113-01: valid per-sensor token accepted (AUTH-01) — Automated
  - UAT-113-02: revoked token 401; isolation (AUTH-02) — Automated
  - UAT-113-03: enrollment revoked_at=NULL; hash only (AUTH-03) — Automated
  - UAT-113-04: sensor_id mismatch 403; unknown token 401 (AUTH-04) — Automated
  - UAT-113-05: full push suite green + operators-guide migration present — Automated

**Vault sync:** UAT-Series.md synced to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` via printf+cat recipe per CLAUDE.md.

**UAT-SERIES.md committed** via gsd-tools.cjs recipe with message `docs(phase-113): update UAT-SERIES.md`.

**Commit:** `039b774`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_push_422_replay_window failed with 401 before replay check**
- **Found during:** Task 1
- **Issue:** The test used `sensor_id="nonexistent-sensor"` with no seeded token. With per-sensor auth, `require_sensor_auth` rejected the request (401) before the replay-window check (422) could fire.
- **Fix:** Changed the test to seed a real sensor + token for "sensor-replay-01" and use a stale `pushed_at` — auth passes, replay window fires, status is 422.
- **Files modified:** `tests/test_sensor_ingest.py`
- **Commit:** `91f7e3b`

**2. [Rule 1 - Bug] test_audit_row_written failure path failed with 401 instead of 422**
- **Found during:** Task 1
- **Issue:** Same root cause — the 422 failure-path sub-test used `sensor_id="nonexistent-sensor"` with no token.
- **Fix:** Seeded a second sensor ("sensor-audit-stale-01") + token for the failure path; stale pushed_at still triggers 422.
- **Files modified:** `tests/test_sensor_ingest.py`
- **Commit:** `91f7e3b`

## Known Stubs

None. All tests fully wired to per-sensor auth. Operators-guide and lab oracle are definitive.

## Chaos Lab Maintenance

This phase does not add, rename, or reconfigure any Docker Compose profile. `lab.sh ALL_PROFILES`
and the chaos-lab `README.md` are **unchanged** — CLAUDE.md no-drift rule confirmed satisfied.
Only the push-credential semantics in `expected_results_distributed.md` were updated to reflect
the v5.5 per-sensor token model.

## Threat Flags

None. All STRIDE threat register items from the plan's `<threat_model>` are mitigated:

| Threat ID | Mitigation Implemented |
|-----------|------------------------|
| T-113-09 | Printout states token shown once / never recoverable; lost → revoke + re-enroll (D-08); raw token never persisted (SHA-256 hash only) |
| T-113-10 | operators-guide §8.1.1 documents the clean-cutover migration; operators update console_api_token before the upgrade activates per-sensor auth (D-10/D-11) |
| T-113-SC | No new npm/pip installs |

## Self-Check

### Files exist:
- tests/test_sensor_ingest.py — FOUND (_seed_token + updated push tests)
- tests/test_console_enroll.py — FOUND (revoked_at IS NULL assertion)
- quirk/cli/console_cmd.py — FOUND (per-sensor enrollment printout)
- quirk/cli/sensor_cmd.py — FOUND (per-sensor comment on console_api_token)
- docs/operators-guide.md — FOUND (per-sensor migration in §8.1.1)
- quantum-chaos-enterprise-lab/expected_results_distributed.md — FOUND (per-sensor oracle)
- docs/UAT-SERIES.md — FOUND (UAT Series 113 added, version 5.5.0-dev)
- /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-113-Per-Sensor-Authentication.md — FOUND

### Commits exist:
- 91f7e3b — feat(113-03): update push tests for per-sensor auth; assert revoked_at NULL on enroll
- 647801e — feat(113-03): correct enrollment printout and sensor credential semantics (D-11)
- 139ae89 — docs(113-03): operators-guide per-sensor migration section + distributed lab oracle (AUTH-04)
- 039b774 — docs(phase-113): update UAT-SERIES.md

### Test results:
- 20/20 push tests GREEN (test_sensor_ingest.py + test_console_enroll.py + test_sensor_auth_per_sensor.py)
- Full suite: 2580 passed, 42 pre-existing failures, no new failures

## Self-Check: PASSED
