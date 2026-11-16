---
type: todo
created: 2026-11-15
source: Phase 236 plan 01 (behaviour-derived severity-divergence gate, census at HEAD 44c1955f); 236-CONTEXT D-19
priority: medium
area: quirk/dashboard/api/routes/scan.py (_derive_identity_findings), quirk/engine/findings_evaluator.py (derive_report_findings)
status: pending
resolves_phase:
owner: "999.132"
---

# Kerberos weak-etype findings exist on the dashboard only, so the two surfaces score one KDC differently

The dashboard derivation raises a HIGH/CRITICAL "Kerberos weak etype: <name>" finding from the severity token in a KERBEROS row's
`service_detail` (`etype:{id}:{name}:{severity}`, `_derive_identity_findings`). `derive_report_findings` composes
`evaluate_endpoints`, the email/broker/code-signing/bearer evaluators and `evaluate_identity_endpoints`, and the last of those handles
SAML only, so the report never lists the finding and its consequence ceiling never sees it.

Evidence (Phase 236 plan 01): the fixture family `kerberos_rc4` (`tests/fixtures/divergence_rows.py`, one row, etype 23
rc4-hmac HIGH) gives a dashboard-only HIGH at the KDC host:port. Measured for that one family alone through
`build_evidence_summary` + `compute_readiness_score`: report 82, dashboard 68. The README/CHANGELOG 5.28.0 known-defect text
("Kerberos weak-encryption") stays until this is fixed.

Dispositioned, not fixed, in Phase 236 per D-19 (`SEVERITY_DIVERGENCES["Kerberos weak etype: "]`, `score_moving: True`,
`tests/test_severity_divergence_behaviour.py`). No scoring model is decided as a side effect.

## Open scoring question

Which surface is right? Either the report gains a Kerberos finding (and a title, remediation theme and compliance-map entry), or the
dashboard stops scoring it. Both change a published score, so this is an operator decision (228 D-04 precedent).

## Feasibility & Effort

**Feasibility: LIKELY.** The report-side shape already exists: `evaluate_identity_endpoints` is the SAML precedent, and the
dashboard branch is a small adapter over the same `service_detail` token.
**Effort: M.** Move the Kerberos synthesis into a shared evaluator (about 30 lines), add the report title to the vocabulary,
`DASHBOARD_TITLE_BRIDGE`, `COMPLIANCE_MAP` and remediation theme, delete the `SEVERITY_DIVERGENCES` entry and the
`Kerberos weak-encryption` phrase from the known-defect text (Phase 240 REL-14), and add a parity fixture.
