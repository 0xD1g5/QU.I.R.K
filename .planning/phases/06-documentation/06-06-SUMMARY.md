---
phase: 06-documentation
plan: "06"
subsystem: documentation
tags: [chaos-lab, docker-compose, operator-guide, markdown]

requires:
  - phase: 04-chaos-lab-expansion
    provides: "All 10 Docker Compose profiles (core, phaseA, cloud, identity, pki, jwt, registry, source, storage, ssh-weak, ldaps) with verified port assignments"

provides:
  - "docs/chaos-lab.md — complete operator guide for all 10 chaos lab profiles with port matrices and config snippets"
  - "quantum-chaos-enterprise-lab/README.md — updated to link to docs/chaos-lab.md as authoritative reference"

affects:
  - "future documentation phases"
  - "consultant onboarding"
  - "scanner validation workflows"

tech-stack:
  added: []
  patterns:
    - "docs/ at repo root, plain Markdown, no build step (D-03)"
    - "Historical artifacts retained in lab dir; docs/ is authoritative going forward"

key-files:
  created:
    - docs/chaos-lab.md
  modified:
    - quantum-chaos-enterprise-lab/README.md

key-decisions:
  - "Vault port is 20009 (not 20008 as in CONTEXT.md D-14 — docker-compose.yml is the ground truth, RESEARCH.md corrected this)"
  - "Storage LocalStack (port 20007, SERVICES=kms) is independent of cloud LocalStack (port 24566, SERVICES=s3,sts,iam)"
  - "CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md retained as historical artifact; docs/chaos-lab.md is authoritative per D-15"

patterns-established:
  - "Per-profile subsection structure: start command, port matrix table, expected findings, config.yaml snippet"
  - "Complete port reference table sorted by port number covers all 38 lab ports across all profiles"

requirements-completed:
  - DOC-07

duration: 8min
completed: 2026-03-31
---

# Phase 6 Plan 6: Chaos Lab Operator Guide Summary

**Authoritative chaos lab operator guide covering all 10 profiles (core through ldaps) with per-profile port matrices, copy-pasteable start commands, and connector config snippets**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-31T22:05:00Z
- **Completed:** 2026-03-31T22:13:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `docs/chaos-lab.md` (425 lines) documenting all 10 chaos lab profiles with per-profile port matrices, expected findings, and start commands
- Documented all 38 lab ports in a complete sorted reference table covering core through ldaps
- Included connector config.yaml snippets for jwt, registry, and source profiles
- Updated `quantum-chaos-enterprise-lab/README.md` to link to the new authoritative guide per D-15

## Task Commits

Each task was committed atomically:

1. **Task 1: Write docs/chaos-lab.md** - `a583abd` (feat)
2. **Task 2: Update quantum-chaos-enterprise-lab/README.md** - `58fec4b` (docs)

**Plan metadata:** (final commit below)

## Files Created/Modified

- `docs/chaos-lab.md` — Complete operator guide: 7 sections covering Overview, Quick Start, all 10 Profile subsections (3.1–3.11), Multi-Profile startup, Complete Port Reference, Troubleshooting, and Historical Reference
- `quantum-chaos-enterprise-lab/README.md` — Documentation section updated: link to docs/chaos-lab.md added, historical artifact note for CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md

## Decisions Made

- Vault port documented as 20009 throughout — CONTEXT.md D-14 had a transcription error (said 20008); RESEARCH.md corrected this from docker-compose.yml ground truth
- Storage LocalStack (20007) explicitly noted as separate from cloud profile LocalStack (24566) to prevent operator confusion
- Troubleshooting section includes "Vault not reachable" entry with "port 20009 (not 20008)" to prevent the known pitfall

## Deviations from Plan

None — plan executed exactly as written. The port matrix content was taken from RESEARCH.md's verified Chaos Lab Complete Port Matrix section. The `<action>` block in the plan provided the complete document structure and content outline; no re-derivation from source files was needed.

## Issues Encountered

None. The 20008 reference that appeared in automated scanning of the output file was in the Troubleshooting section as a clarifying "not 20008" warning — this is intentional and correct per RESEARCH.md Pitfall 4.

## User Setup Required

None — no external service configuration required. The chaos lab is a local Docker Compose environment; operators follow the guide to start profiles.

## Next Phase Readiness

- Phase 6 plan 6 of 6 is complete. All documentation plans for Phase 6 are now done.
- `docs/chaos-lab.md` is ready for consultant use immediately
- Phase 7 (packaging/PyPI) can add a MkDocs skin over the docs/ structure without restructuring (D-03)

---
*Phase: 06-documentation*
*Completed: 2026-03-31*
