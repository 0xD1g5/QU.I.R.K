# Phase 1: Foundation Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-03-28
**Phase:** 01-foundation-fixes
**Mode:** discuss
**Areas discussed:** sslyze integration scope, SSH data model, Scoring consolidation output, Rename scope

## Gray Areas Presented

| Area | Gray Area | Options Presented |
|------|-----------|-------------------|
| sslyze | Replace tls_scanner.py entirely vs primary+fallback vs augment | 3 options |
| SSH model | JSON blob vs typed columns vs mix | 3 options |
| Score output | Clean break vs keep field names + swap engine | 2 options |
| Rename scope | Full qcscan→quirk rename vs user-facing only | 2 options |

## Decisions Made

### sslyze integration scope
- **Decision:** sslyze primary + existing ssl/cryptography scanner as fallback
- **Rationale:** Preserves resilience for edge-case targets that sslyze's stricter probing can't reach. Existing scanner is well-tested and handles error classification cleanly.

### SSH data model
- **Decision:** JSON blob — single `ssh_audit_json TEXT` column
- **Rationale:** One additive schema change. Flexible for future ssh-audit output additions. Avoids rigid column schema for algorithm categories.

### Scoring consolidation output
- **Decision:** Clean break — remove legacy `assessment/readiness_score.py` call and output block
- **Rationale:** Dead code removed, no shim needed, output JSON is cleaner. `intelligence/scoring.py` already produces the authoritative score.

### Rename scope
- **Decision:** Full rename — `qcscan/` → `quirk/` now, all imports updated
- **Rationale:** Clean foundation for `pip install quirk` in Phase 7. Better to do it once in Phase 1 than after more code is written.

## No Corrections (all recommended options chosen or equivalent)

## Todos Reviewed
None — no matching todos found for Phase 1.
