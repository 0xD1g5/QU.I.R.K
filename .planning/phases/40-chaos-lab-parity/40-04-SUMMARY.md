---
phase: 40-chaos-lab-parity
plan: "04"
subsystem: chaos-lab-docs
tags: [readme, navigation, documentation, chaos-lab, oracle-links]
dependency_graph:
  requires: ["40-02", "40-03"]
  provides: [chaos-lab-readme-navigation-surface]
  affects: [quantum-chaos-enterprise-lab/README.md]
tech_stack:
  added: []
  patterns: [markdown-navigation-surface, per-row-oracle-anchor-links]
key_files:
  modified:
    - quantum-chaos-enterprise-lab/README.md
decisions:
  - Anchor format: GitHub slug convention (lowercase, colons stripped, spaces to dashes) — e.g. profile-storage-s3
  - SAML row uses port 8080 (docker-compose.yml is source of truth, not v3 oracle's 8880)
  - kerberos privileged ports (88, 389) called out explicitly in Notes column
  - Historical Reference preserved both in Documentation link block AND as standalone H2 at end (D-08 §4 + §6)
  - 19 rows total (core + 18 named profiles)
metrics:
  duration: "~8 minutes"
  completed: "2026-04-29T21:41:20Z"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Phase 40 Plan 04: Chaos Lab README Navigation Surface Summary

README.md rewritten as a compact navigation surface with 19-row Profile Summary Table linking into the v4 oracle, replacing the 28-line stub.

## What Was Built

### Task 1: Rewrite README.md with navigation structure + Profile Summary Table

Replaced the existing 28-line stub with a structured navigation surface (approx 70 lines) following D-08/D-09/D-11 exactly:

**§1 Title + intro** — one paragraph covering 18 named profiles + core baseline with links to oracle and guide.

**§2 Quick Start** — four command examples: `./lab.sh up` (baseline only), `./lab.sh all` (all profiles), `PROFILE_ARGS="--profile identity" ./lab.sh up` (single profile), `./lab.sh profiles` (discovery).

**§3 Profile Summary Table** — 19 rows ordered by version era:

| Era | Profiles |
|-----|---------|
| v4.0 core (always-on) | core |
| v4.0 named | phaseA, cloud, identity, pki |
| v4.1 | jwt, registry, source, storage (deprecated), ssh-weak, ldaps |
| v4.2 | dnssec, saml, kerberos |
| v4.3 DAR | database, storage-s3, vault |
| v4.4 | email, broker |

Each row contains: Profile name | Services shipped | Published ports | `[Expected Findings](expected_results_v4.md#profile-<name>)` link | Notes (era, caveats, deprecation).

**Anchor link pattern used:** GitHub slug convention — `## Profile: storage-s3` in the oracle becomes `#profile-storage-s3` (lowercase, colon stripped, spaces to dashes). All 19 anchors verified against actual H2 headings in `expected_results_v4.md`.

**§4 Documentation link block** — `docs/chaos-lab.md`, `expected_results_v4.md`, `CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md`.

**§5 Phase C** — `scripts/phaseC_stepca_issue.sh` invocation preserved verbatim.

**§6 Historical Reference** — pointer to `CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` preserved verbatim.

## Commits

| Task | Commit | Files | Description |
|------|--------|-------|-------------|
| 1 | 7a14936 | quantum-chaos-enterprise-lab/README.md | Rewrite README as navigation surface with 19-row Profile Summary Table |

## Verification Results

All 20 automated checks passed:
- H1 `# QU.I.R.K. Chaos Lab` present
- `## Quick Start` with `./lab.sh up`, `./lab.sh all`, `./lab.sh profiles`
- 19 `expected_results_v4.md#profile-` link occurrences (1 per row, ≥ 18 required)
- All v4.3 anchors: `#profile-database`, `#profile-storage-s3`, `#profile-vault`
- All v4.4 anchors: `#profile-email`, `#profile-broker`
- All v4.3+v4.4 ports: 28200, 25432, 23306, 29000, 29001, 30025, 29092, 25672, 26379
- SAML row uses port 8080 (not 8880 from v3 oracle)
- Historical reference pointer preserved
- Phase C `phaseC_stepca_issue.sh` content preserved

## Deviations from Plan

None — plan executed exactly as written. The 19-row count (vs 18-row minimum stated in acceptance criteria) is correct: the plan's table example shows 19 rows (core + 18 named) and the acceptance criterion says "at least 18 `expected_results_v4.md#profile-` link occurrences."

## Known Stubs

None. All table rows link to actual H2 headings verified to exist in `expected_results_v4.md`.

## Threat Flags

None. Documentation-only change; no runtime attack surface introduced.

## Self-Check: PASSED

- [x] `quantum-chaos-enterprise-lab/README.md` exists and is rewritten
- [x] Commit 7a14936 confirmed in git log
- [x] No file deletions in commit
- [x] All 19 oracle anchor links point to verified H2 headings in expected_results_v4.md
