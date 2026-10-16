---
type: todo
created: 2026-10-15
source: Phase 228 code review (.planning/phases/228-cross-surface-score-parity/228-REVIEW.md), WR-03
priority: medium
area: quirk/engine/findings_evaluator.py:1330-1344 (derive_report_findings), quirk/merge/scan.py, quirk/intelligence/trends.py
status: pending
resolves_phase: null
owner: "999.136"
---

# Merge and notify score derivation ignores the operator's `scan.tls_designated_ports`

`derive_report_findings(endpoints)` with no cfg fabricates `tls_designated_ports=[]`, so only `WELL_KNOWN_TLS_PORTS` are designated. The per-scan report rewrites `Plaintext HTTP service detected` on an operator-designated port to `HTTP on TLS-designated port` HIGH (or MEDIUM/INFO variants); the merge and notify defaults do not, so their ceiling input differs from the report for the same rows. The notify dispatcher already loads config from `QUIRK_CONFIG_PATH` and could pass it; the CLI merge could too.

Deferred by the operator at Phase 228 close (2026-10-15): CR-01, WR-07 fixed in-phase (dab89ffc, 3b1d286c);
this item was triaged out of Phase 228's scope. Full evidence and the suggested fix are in the review section named
in `source`.
