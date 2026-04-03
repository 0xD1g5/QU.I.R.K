# Phase 8: Legacy Debt Cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the Q&A.

**Date:** 2026-04-02
**Phase:** 08-legacy-debt-cleanup
**Mode:** discuss
**Areas discussed:** validate.py, Interactive Mode, Dead Module Removal, assessment/ boundary

---

## Gray Areas Presented

| Area | Description |
|------|-------------|
| validate.py fate | §3.5: checks artifacts that don't exist, can never pass |
| Interactive mode depth | §2.1, §3.1, §3.2: label drift, ADCS prompt, missing Phase 3 prompts |
| Dead module removal scope | §1.1, §1.2, §1.6, §1.7, §1.4: how far to go beyond success criteria |
| assessment/ boundary | Phase 8 vs Phase 9 split for assessment/ directory |

User selected all four areas for discussion.

---

## validate.py

**Q:** What should happen to validate.py?
- Fix it (update to check real artifacts) ← selected
- Remove it
- Leave for Phase 9

**Q:** How thorough should the fix be?
- Minimal fix + add a test ← selected
- Minimal fix only

**Decision:** Fix validate.py to check real output artifacts. Add one integration test.

---

## Interactive Mode

**Q:** Windows ADCS — user clarification: considering implementing instead of removing.

**Recommendation presented:** Full ADCS implementation requires Kerberos/NTLM auth, LDAP/LDAPS
enumeration, CertSrv parsing — comparable complexity to the Azure connector. Deferred to v2 in
REQUIREMENTS.md. Phase 8 cannot absorb it without pushing 10 concrete bug-fixes. Recommended:
remove prompt, note for roadmap Phase 10.

**Q:** What should Phase 8 do with Windows ADCS?
- Remove prompt + note for roadmap ← selected
- Keep prompt, label "coming soon"
- Implement lightweight ADCS via LDAP

**Q:** Should Phase 8 also add JWT/Container/Source prompts?
- Yes — add all three ← selected
- No — defer to later phase

**Decision:** Fix AWS/Azure labels, remove Windows ADCS prompt + config field, add JWT/Container/Source prompts. Note ADCS for Phase 10 roadmap.

---

## Dead Module Removal Scope

**Q:** How aggressively should Phase 8 remove dead modules?
- Remove all confirmed dead code ← selected (driver_text.py, calibration.py, dead writer.py functions)
- Criteria-only (engine/rules.py and connectors/ only)
- Remove everything including schema.py and scorecard.py

**Clarification applied:** schema.py and scorecard.py left for Phase 9 — adjacent to scoring
consolidation. The "confirmed dead" set: driver_text.py, calibration.py, engine/rules.py,
connectors/ directory, 4 dead functions in writer.py (NOT _extract_cert_key_type which was fixed in Phase 1).

---

## assessment/ Boundary

**Q:** Phase 8 boundary for assessment/?
- Fix migration_advisor.py only ← selected
- Fix migration_advisor.py + remove interpretation_engine.py

**Decision:** Phase 8 fixes two string pattern bugs in migration_advisor.py. All other assessment/ files (readiness_score.py, confidence.py, transition_planner.py, interpretation_engine.py) are Phase 9 scope.

---

## No Corrections

All selections confirmed without revision.
