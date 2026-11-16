---
type: todo
created: 2026-11-15
source: Phase 236 plan 01 (behaviour-derived severity-divergence gate, census at HEAD 44c1955f); 236-CONTEXT D-19
priority: medium
area: quirk/dashboard/api/routes/scan.py (_derive_identity_findings, _DNSSEC_WEAK_MAP), quirk/engine/findings_evaluator.py
status: pending
resolves_phase:
owner: "999.132"
---

# DNSSEC findings exist on the dashboard only, so the two surfaces score one zone differently

`_derive_identity_findings` maps a DNSSEC row's `cert_pubkey_alg` through `_DNSSEC_WEAK_MAP` to variable severities
(RSASHA1/RSAMD5/DSA CRITICAL; NONE, SHA1-DS, DS-MISMATCH HIGH; NSEC MEDIUM). `derive_report_findings` has no DNSSEC evaluator,
so none of those findings reach the report.

Evidence (Phase 236 plan 01): fixture family `dnssec_none` gives a dashboard-only HIGH `DNSSEC: NONE`. Measured for that one
family alone: report 83, dashboard 68. The Pass A job in the Phase 235.4 walkthrough (replayed in plan 236-04) carries two
`DNSSEC: NONE` rows, which is part of the 42 vs 27 headline gap. The README/CHANGELOG known-defect text ("DNSSEC") stays until this is
fixed.

Dispositioned, not fixed, in Phase 236 per D-19 (`SEVERITY_DIVERGENCES["DNSSEC: "]`, `score_moving: True`, families
`["dnssec_none"]`; the MEDIUM `dnssec_nsec` family is clean today and is a mutation target of the gate).

## Open scoring question

Is a zone with no DNSSEC signing a HIGH readiness defect for a quantum-readiness report at all, and if so should the report carry it
(new evaluator, title, theme, compliance entry) or should the dashboard drop it? Operator decision.

## Feasibility & Effort

**Feasibility: LIKELY.** `_DNSSEC_WEAK_MAP` is a self-contained table; the SAML evaluator is the precedent for a shared one.
**Effort: M.** Same shape as the Kerberos todo (`261115-kerberos-weak-etype-dashboard-only-score-divergence.md`); the two can be
fixed together under one identity-evaluator extraction.
