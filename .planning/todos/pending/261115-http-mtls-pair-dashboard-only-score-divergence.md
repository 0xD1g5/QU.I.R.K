---
type: todo
created: 2026-11-15
source: Phase 236 plan 01 census extra (behaviour-derived severity-divergence gate, HEAD 44c1955f); 236-CONTEXT D-09
priority: medium
area: quirk/engine/findings_evaluator.py (_postprocess_findings), quirk/dashboard/api/routes/scan.py (findings_for_endpoint)
status: pending
resolves_phase:
owner: "999.132"
---

# An HTTP row next to an mTLS-required TLS row is HIGH on the dashboard and INFO in the report

Found by the Phase 236 behaviour gate, not previously listed. Two rows on one host:port: an `HTTP` row and a `TLS` row whose
`tls_blocker_reason` is `MTLS_REQUIRED`.

- Report: `evaluate_endpoints` emits `Plaintext HTTP service detected` (HIGH); `_postprocess_findings` then sees the TLS sibling for
  that (host, port) in `ep_map`, and when the port is TLS-designated rewrites the finding to `mTLS required` (INFO).
- Dashboard: `findings_for_endpoint` judges each row alone and keeps `Unencrypted HTTP service` HIGH.

Measured for that one family alone: report 84, dashboard 66. Same cross-endpoint class as
`261015-xsurf-default-report-deriver-drops-tls-designated-ports.md` (report-side `_postprocess_findings` has no dashboard
equivalent), but a different trigger (a sibling row, not the configured port list).

Dispositioned, not fixed, in Phase 236 (`SEVERITY_DIVERGENCES["Unencrypted HTTP service"]`, `score_moving: True`, family
`http_on_tls_port_with_mtls_pair`). Plan 02 asks the operator whether to fix it.

## Feasibility & Effort

**Feasibility: LIKELY.** `_postprocess_findings` is a pure function of (cfg, endpoints, findings).
**Effort: S to M.** Either run the dashboard's HTTP findings through the report's post-process, or factor the sibling-row check
into a shared helper both call. Then delete the entry and extend the parity fixtures.
