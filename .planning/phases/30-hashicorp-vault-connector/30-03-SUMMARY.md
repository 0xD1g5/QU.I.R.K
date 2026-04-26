---
phase: 30-hashicorp-vault-connector
plan: "03"
subsystem: vault-intelligence-cbom-chaos
tags: [vault, intelligence, scoring, cbom, chaos-lab, docs, uat-series, obsidian, evidence, dar]
dependency_graph:
  requires:
    - phase: 30-02
      provides: [vault_connector.py, scan_vault_targets, VAULT_TRANSIT_KEY_MAP, AUTH_RISK_MAP, vault-scanning-block]
  provides: [dar_vault_weak_count, dar_vault_weak_ratio, dar_vault_weak_ratio-weight-8.0, CBOM-Pass2-VAULT-skip, CBOM-Pass3-VAULT-skip, vault-chaos-profile, vault-seed-sh, labs-vault-expected-results, UAT-30-entries, obsidian-phase-note]
  affects: [quirk/intelligence/evidence.py, quirk/intelligence/scoring.py, quirk/cbom/builder.py, docker-compose.yml, docs/UAT-SERIES.md]
tech_stack:
  added: []
  patterns: [D-11 HIGH-only counter pattern (mirrors dar_k8s pattern), D-14 Pass-1-unmodified guard for transit key algorithm registration, D-15 Pass-2/3 VAULT skip for cert/protocol components, dedicated --profile vault docker block at port 28200]
key_files:
  created: [tests/test_dar_vault_scoring.py, quantum-chaos-enterprise-lab/vault/seed.sh, labs/vault/expected_results.md]
  modified: [quirk/intelligence/evidence.py, quirk/intelligence/scoring.py, quirk/cbom/builder.py, quantum-chaos-enterprise-lab/docker-compose.yml, docs/UAT-SERIES.md]
  obsidian_written: [/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-30-HashiCorp-Vault-Connector.md, /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md]
key-decisions:
  - "D-11: dar_vault_weak_count increments ONLY on HIGH-severity VAULT endpoints (MEDIUM exportable transit + userpass do NOT increment)"
  - "D-12: dar_vault_weak_ratio weight = 8.0 in SCORE_WEIGHTS (between storage_unencrypted 12.0 and k8s_unencrypted 10.0)"
  - "D-13: vault impact appended as 7th entry to existing dar_impacts list; NUM_SUBSCORES stays 5"
  - "D-14: CBOM Pass 1 NOT modified for VAULT — transit keys must register algorithms via default else clause"
  - "D-15: CBOM Pass 2 + Pass 3 skip VAULT — no X.509 cert properties or TLS protocol component for VAULT endpoints"
  - "D-07: Dedicated --profile vault Docker Compose block at port 28200 (NOT extending storage profile)"
  - "D-08: seed.sh seeds 4 RED finding paths: transit RSA-2048, exportable RSA-2048, PKI RSA-2048 root CA, userpass auth (token always present in dev mode)"
metrics:
  duration: "~7 min"
  completed: "2026-04-26"
  tasks: 4
  files_created: 3
  files_modified: 5
---

# Phase 30 Plan 03: HashiCorp Vault Intelligence + CBOM + Chaos Lab + Docs Summary

**Intelligence, scoring, CBOM skip-lists, chaos lab, and docs wired: dar_vault_weak_count (HIGH-only, D-11) + weight 8.0 (D-12) + 7-entry dar_impacts (D-13) + VAULT in Pass 2/3 skip (D-15, Pass 1 untouched per D-14) + dedicated vault chaos profile at port 28200**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-04-26T18:02:03Z
- **Completed:** 2026-04-26T18:09:14Z
- **Tasks:** 4
- **Files modified:** 5 (plus 3 created, 2 Obsidian writes)

## Accomplishments

### Task 1: Intelligence + Scoring + Tests

- `quirk/intelligence/evidence.py`: Added `"VAULT"` to `_PROTOCOL_KEYS`, `dar_vault_weak_count` accumulator, `proto == "VAULT"` HIGH-only branch, and `dar_vault_weak_count`/`dar_vault_weak_ratio` in return dict
- `quirk/intelligence/scoring.py`: Added `"dar_vault_weak_ratio": 8.0` to `SCORE_WEIGHTS`, `dar_vault_weak` extraction, and 7th tuple `("Vault weak crypto posture", ...)` to `dar_impacts` list
- `tests/test_dar_vault_scoring.py`: 10 tests covering the count/ratio/scoring path — all pass

### Task 2: CBOM Builder Skip Lists

- `quirk/cbom/builder.py`: Added `"VAULT"` to Pass 2 cert skip tuple and Pass 3 protocol skip tuple
- Pass 1 (`elif ep.protocol in ("POSTGRESQL", ..., "KUBERNETES"):`) deliberately NOT modified (D-14) — transit keys flow through default `else` clause to register algorithms via `_register_algorithm`

### Task 3: Chaos Lab

- `quantum-chaos-enterprise-lab/docker-compose.yml`: New `vault-30` + `vault-30-seed` services under `profiles: ["vault"]` at port 28200 (storage profile vault at 20009 unchanged)
- `quantum-chaos-enterprise-lab/vault/seed.sh`: Executable seed script; 4 RED finding paths (transit RSA-2048, exportable RSA-2048, PKI RSA-2048 root CA, userpass auth; token always present in dev mode)
- `labs/vault/expected_results.md`: 71 lines documenting 5 expected findings + scoring + CBOM impact

### Task 4: Docs + Obsidian Sync

- `docs/UAT-SERIES.md`: Header updated with Phase 30 note; UAT-30-01/02/03 entries inserted before Series 6
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`: Synced from docs/UAT-SERIES.md with frontmatter
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-30-HashiCorp-Vault-Connector.md`: Created with `status: complete`, Goal, Requirements Covered, Success Criteria, What Was Built (3 plan subsections), Key Decisions, Deferred, Links

## Task Commits

1. **Task 1: Wire VAULT counter into evidence.py + scoring.py + write tests** - `41a9971` (feat)
2. **Task 2: Add VAULT to CBOM Pass 2 + Pass 3 skip lists** - `f67d7da` (feat)
3. **Task 3: Add --profile vault chaos lab + seed.sh + labs/vault/expected_results.md** - `e8341f9` (feat)
4. **Task 4: Update UAT-SERIES.md + Obsidian sync + Phase 30 note** - `25da7fd` (docs)

## Files Created/Modified

**Created:**
- `tests/test_dar_vault_scoring.py` — 10 tests for D-11/D-12/D-13 contracts
- `quantum-chaos-enterprise-lab/vault/seed.sh` — executable; seeds 4 RED finding paths
- `labs/vault/expected_results.md` — 71 lines; 5 expected findings + scoring/CBOM impact

**Modified:**
- `quirk/intelligence/evidence.py` — VAULT in _PROTOCOL_KEYS, dar_vault_weak_count counter + ratio
- `quirk/intelligence/scoring.py` — dar_vault_weak_ratio: 8.0 in SCORE_WEIGHTS; 7th dar_impacts entry
- `quirk/cbom/builder.py` — VAULT in Pass 2 + Pass 3 skip lists; Pass 1 unchanged
- `quantum-chaos-enterprise-lab/docker-compose.yml` — vault-30 + vault-30-seed services at port 28200
- `docs/UAT-SERIES.md` — header updated; UAT-30-01/02/03 inserted before Series 6

**Obsidian writes (filesystem direct, per CLAUDE.md):**
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-30-HashiCorp-Vault-Connector.md`
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`

## Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| `tests/test_dar_vault_scoring.py` | 10 | PASSED |
| `tests/test_vault_connector.py` | 22 | PASSED |
| Full suite (excl. 3 pre-existing failures) | 478 | PASSED |

## Decisions Honored

- **D-07**: Dedicated `--profile vault` Docker block, NOT extending `storage`
- **D-08**: seed.sh seeds 4 RED finding paths (transit rsa-2048, exportable rsa-2048, PKI rsa-2048, userpass auth)
- **D-11**: `dar_vault_weak_count` HIGH-only gate: `if sev == "HIGH": dar_vault_weak_count += 1`
- **D-12**: `"dar_vault_weak_ratio": 8.0` inserted between `dar_storage_aws_managed_ratio` and `dar_k8s_unencrypted_ratio`
- **D-13**: 7th entry appended to `dar_impacts`; `NUM_SUBSCORES` stays 5 (confirmed by `test_compute_readiness_score_subscores_count_unchanged`)
- **D-14**: Pass 1 in `builder.py` (the `elif ep.protocol in ("POSTGRESQL", ..., "KUBERNETES"):` branch) was NOT modified — transit keys flow through `else` clause and register algorithms
- **D-15**: Pass 2 + Pass 3 both include `"VAULT"` in their skip tuples

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all wiring complete. dar_vault_weak_count flows from evidence.py to scoring.py. Chaos lab seed.sh seeds all expected scenarios. No hardcoded empty values in production paths.

## Threat Surface Scan

No new threat surface beyond the plan's threat model:
- T-30-11 (dar_vault_weak_count tampering): Mitigated — explicit `if sev == "HIGH"` guard; tests `test_dar_vault_weak_count_medium_*_no_increment` prove only HIGH increments
- T-30-12 (dev token exposure): Accepted — chaos lab only, documented in labs/vault/expected_results.md
- T-30-13 (dar_impacts growth): Mitigated — `_apply_weighted_impacts` clamps to 25.0; D-13 test proves 5 subscores
- T-30-14 (CBOM Pass 1 omission risk): Mitigated — Pass 1 grep gate passes; `"KUBERNETES")` still ends the Pass 1 line
- T-30-15 (Obsidian timestamp): Mitigated — `updated: 2026-04-26` set in note frontmatter
- T-30-16 (UAT-Series sync): Mitigated — `source: docs/UAT-SERIES.md` in Obsidian frontmatter

## Self-Check: PASSED

- [x] `tests/test_dar_vault_scoring.py` exists and has 10 passing tests
- [x] `quirk/intelligence/evidence.py` has `"VAULT"` in `_PROTOCOL_KEYS` and `dar_vault_weak_count` in return dict
- [x] `quirk/intelligence/scoring.py` has `"dar_vault_weak_ratio": 8.0` and 7th `dar_impacts` entry
- [x] `quirk/cbom/builder.py` has `"VAULT"` in Pass 2 + Pass 3 skip lists; Pass 1 untouched
- [x] `quantum-chaos-enterprise-lab/vault/seed.sh` exists and is executable
- [x] `labs/vault/expected_results.md` exists (71 lines)
- [x] `docker-compose.yml` has `vault-30` at port 28200 with `profiles: ["vault"]` (2 services)
- [x] `docs/UAT-SERIES.md` has UAT-30-01/02/03 + Phase 30 header note
- [x] `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-30-HashiCorp-Vault-Connector.md` exists with `status: complete` and 5 required sections
- [x] `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` synced with frontmatter
- [x] Commit `41a9971` (Task 1) verified
- [x] Commit `f67d7da` (Task 2) verified
- [x] Commit `e8341f9` (Task 3) verified
- [x] Commit `25da7fd` (Task 4) verified
- [x] No modifications to STATE.md or ROADMAP.md

---
*Phase: 30-hashicorp-vault-connector*
*Completed: 2026-04-26*
