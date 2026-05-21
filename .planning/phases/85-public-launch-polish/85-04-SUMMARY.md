---
phase: 85
plan: 04
subsystem: examples
tags: [examples, cbom, fixtures, chaos-lab, launch, launch-05]
requires: [85-01]
provides: [examples/cbom/, examples/README.md, scripts/generate_cbom_fixtures.sh]
affects: [docs/cbom-guide.md (cross-linked, not modified)]
tech_stack:
  added: []
  patterns: [in-process CBOM generation via build_cbom(), jq post-processing for determinism]
key_files:
  created:
    - examples/cbom/tls-only.cbom.json
    - examples/cbom/identity.cbom.json
    - examples/cbom/data-at-rest.cbom.json
    - examples/cbom/data-in-motion.cbom.json
    - examples/README.md
    - scripts/generate_cbom_fixtures.sh
  modified: []
decisions:
  - In-process generation via tests/_cbom_profiles.PROFILE_ENDPOINTS instead of live docker-compose scans (Docker daemon unavailable in worktree + synthesizers ARE the drift-locked ground truth)
  - Profile-name reconciliation per <interfaces> table: tls-only ← phaseA, identity ← identity+pki, data-at-rest ← database, data-in-motion ← phaseA+email+broker
  - Determinism via jq normalization of three non-deterministic fields (metadata.timestamp, serialNumber, metadata-component BomRef)
metrics:
  duration_minutes: 3.4
  completed: 2026-05-21
  tasks: 2
  files_created: 6
  fixtures_size_bytes: 45853
requirements_closed: [LAUNCH-05]
---

# Phase 85 Plan 04: Sample CBOM Fixtures Summary

Four deterministic CycloneDX 1.6 CBOM fixtures (TLS-only, identity, data-at-rest, data-in-motion) checked into `examples/cbom/`, generated in-process from the Phase 42 synthesizer map, normalized via `jq` to be byte-identical across regenerations.

## What was built

- **`examples/cbom/tls-only.cbom.json`** (10,006 bytes, 14 components) — `phaseA` profile synthesizer. Weak ciphersuites, sub-2048 RSA keys, expired / missing-intermediate certs, with a modern-TLS baseline.
- **`examples/cbom/identity.cbom.json`** (8,668 bytes, 12 components) — `identity` + `pki` synthesizers combined. S/MIME LDAP discovery, AD-CS / Step-CA template enumeration, PKI hierarchy.
- **`examples/cbom/data-at-rest.cbom.json`** (1,212 bytes, 1 component) — `database` synthesizer. Narrow advisory fixture for PostgreSQL at-rest crypto.
- **`examples/cbom/data-in-motion.cbom.json`** (25,967 bytes, 39 components) — `phaseA` + `email` + `broker` combined. TLS + SMTP-STARTTLS + IMAP/POP3-STARTTLS + AMQP-TLS + Kafka-TLS, the densest fixture.
- **`examples/README.md`** (101 lines) — fixture index table, regeneration procedure, determinism note, cross-links to `docs/cbom-guide.md`, `docs/getting-started.md`, `docs/chaos-lab.md`.
- **`scripts/generate_cbom_fixtures.sh`** — idempotent regeneration script (jq + python3 only; no Docker dependency).

## Commits

| Task | Commit | Files |
| --- | --- | --- |
| 1: Generate 4 CBOM fixtures | `8522f43` | 4 × `.cbom.json` + `scripts/generate_cbom_fixtures.sh` |
| 2: examples/README.md | `0adbe2f` | `examples/README.md` |

## Determinism check

Regenerated the four fixtures twice; both runs are byte-identical:

```
DETERMINISTIC: tls-only.cbom.json       md5=8830926a40bc94a6d7c9b53f36b1ef83
DETERMINISTIC: identity.cbom.json       md5=ad5b065baef568662a1e7a80d38d96a9
DETERMINISTIC: data-at-rest.cbom.json   md5=affb2949cf03c3b92d2af354779b3bf3
DETERMINISTIC: data-in-motion.cbom.json md5=0cd48aa83d079afbaba38760b80b3993
```

All four files share the same fixed `metadata.timestamp` (`2026-01-01T00:00:00+00:00`) and `serialNumber` (`urn:uuid:00000000-0000-0000-0000-000000000000`).

## Verification gates

Task 1 automated gate (per plan):

```
OK examples/cbom/tls-only.cbom.json       (10006 bytes, 14 cryptographic-asset components)
OK examples/cbom/identity.cbom.json       ( 8668 bytes, 12 cryptographic-asset components)
OK examples/cbom/data-at-rest.cbom.json   ( 1212 bytes,  1 cryptographic-asset component)
OK examples/cbom/data-in-motion.cbom.json (25967 bytes, 39 cryptographic-asset components)
```

Task 2 automated gate: all four filenames referenced, "regenerat" substring present, "lab.sh" referenced, 101 lines (≥ 60 required) — PASS.

## Deviations from Plan

### 1. [Rule 3 - Blocker] Docker daemon unavailable; switched to in-process generation

- **Found during:** Task 1 setup
- **Issue:** The plan's primary path was `cd quantum-chaos-enterprise-lab && ./lab.sh up --profile <name>` followed by a live scanner run. The Docker daemon is not running in this worktree (`Cannot connect to the Docker daemon at unix:///Users/digs/.docker/run/docker.sock`), and standing it up + bringing seven profiles up sequentially is outside the worktree's risk envelope.
- **Fix:** Used the explicit fallback documented in the orchestrator prompt ("you may use saved fixture inputs OR generate a minimal-but-realistic CBOM by invoking `quirk run` against a controlled local fixture"). Specifically, invoked `quirk.cbom.builder.build_cbom()` in-process against `tests._cbom_profiles.PROFILE_ENDPOINTS[<profile>]()` — the same drift-locked synthesizer map already used by the Phase 42 schema-validation harness and Phase 35 motion-golden tests.
- **Why this is faithful:** The synthesizers ARE the ground truth for what the scanner emits per profile (drift-enforced against `docker-compose.yml` by `tests/test_cbom_schema_validation.py`). Building the BOM in-process exercises the exact same `build_cbom` → `JsonV1Dot6` codepath the live scanner uses; the only thing skipped is the network-discovery → `CryptoEndpoint` materialization, which is exactly what the synthesizers replace.
- **Files modified:** `scripts/generate_cbom_fixtures.sh` (new helper); fixtures themselves.
- **Commit:** `8522f43`

### 2. [Profile name reconciliation] Followed PLAN.md `<interfaces>` table over CONTEXT.md

- **Found during:** Task 1 planning
- **Issue:** CONTEXT.md named profiles `tls-weak`, `smime`, `adcs`, `dar-database`. Actual `docker-compose.yml` profile names are `phaseA` (for weak-TLS), `identity` (for S/MIME + identity), `pki` (for AD-CS-like Step-CA + PKI hierarchy), and `database` (for postgres at-rest). The PLAN's `<interfaces>` table already documented this, so I followed it.
- **Mapping applied:**
  - `tls-only` ← `phaseA` (the profile that actually owns the legacy TLS / weak-cipher / cert-defect services)
  - `identity` ← `identity` + `pki` (combined; the plan called for `smime` + `adcs`, neither of which exist as compose profile names; `identity` covers S/MIME LDAP + LDAPS, `pki` covers the Step-CA / AD-CS-template analog)
  - `data-at-rest` ← `database`
  - `data-in-motion` ← `phaseA` + `email` + `broker`
- **No re-decision required** — the plan explicitly told the executor to follow the `<interfaces>` table when CONTEXT.md and reality disagree.

### 3. [Helper script added] `scripts/generate_cbom_fixtures.sh`

- **Found during:** Task 1 implementation
- **Issue:** Pure deviation #1 (in-process generation) needed a documented regeneration path so future maintainers do not have to reverse-engineer the jq filter from a SUMMARY.
- **Fix:** Added `scripts/generate_cbom_fixtures.sh` (115 lines, executable). The plan's `<output_spec>` allowed `scripts/generate_cbom_fixtures.sh` as an optional helper. It documents the four fixture/profile mappings, the three non-deterministic fields it normalizes, and the jq filter used.
- **Commit:** `8522f43`

## Auto-fixed issues

None — no bugs, missing critical functionality, or blocking issues encountered beyond the Docker fallback noted above.

## Authentication gates

None.

## Known Stubs

None. All four fixtures contain real algorithm / certificate / protocol components from the production builder; the `data-at-rest` fixture is intentionally narrow (1 component) because the `database` synthesizer emits a single endpoint per the Phase 42 design (postgres at-rest crypto is not externally introspectable — the fixture correctly shows what the scanner records in that case).

## Threat Flags

None — fixtures expose static crypto findings for known chaos-lab targets; no new network surface, no new trust boundary, no schema change.

## Plan Status

All success criteria for plan 85-04 met. ROADMAP Phase 85 success criterion #5 (partial: `examples/` ≥ 4 sample CBOM JSON files, deterministic fixtures) is now satisfied. LAUNCH-05 ready to mark complete.

## Self-Check: PASSED

- examples/cbom/tls-only.cbom.json — FOUND
- examples/cbom/identity.cbom.json — FOUND
- examples/cbom/data-at-rest.cbom.json — FOUND
- examples/cbom/data-in-motion.cbom.json — FOUND
- examples/README.md — FOUND
- scripts/generate_cbom_fixtures.sh — FOUND
- Commit 8522f43 — FOUND
- Commit 0adbe2f — FOUND
