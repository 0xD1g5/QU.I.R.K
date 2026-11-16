---
phase: 236-score-divergence-closure
plan: 02
subsystem: scoring
tags: [decision, divergence, census]
requires: [236-01]
provides: ["operator decision per census extra"]
affects: []
key-files:
  created: [.planning/phases/236-score-divergence-closure/236-02-SUMMARY.md]
  modified: []
key-decisions:
  - "Census extra 'Unencrypted HTTP service' (HTTP + MTLS_REQUIRED sibling): KEEP dispositioned (operator, 2026-11-16)"
requirements-completed: []
duration: 5min
completed: 2026-11-16
---

# Phase 236 Plan 02: Census-extras operator decision Summary

Plan 01's census (33 families, 10 residuals) found one score-moving divergence outside the D-19
known set. The operator kept it dispositioned. No gap-closure plan is required.

## Census extras

Copied from 236-01-SUMMARY.md § Census extras. Known-set keys (Legacy TLS, Weak cipher suites,
undersized ECDSA, End-of-life, Severely outdated Python cryptography, Kerberos weak etype, DNSSEC)
were dropped per D-19.

| Key | Side | Families | Measured score (report / dashboard) | Todo (exists) |
|---|---|---|---|---|
| Unencrypted HTTP service | dashboard_only | http_on_tls_port_with_mtls_pair | 84 / 66 | `.planning/todos/pending/261115-http-mtls-pair-dashboard-only-score-divergence.md` |

Cause: the report's `_postprocess_findings` (`quirk/engine/findings_evaluator.py`) rewrites
plaintext HTTP to INFO "mTLS required" when a sibling TLS row on the same host:port carries
`tls_blocker_reason == MTLS_REQUIRED`. The dashboard's `findings_for_endpoint` judges each row in
isolation and keeps HIGH.

## Operator decisions

| Key | Decision | Consequence |
|---|---|---|
| Unencrypted HTTP service | **keep** | Stays in `SEVERITY_DIVERGENCES` (score_moving True) with its todo and LEDGER row; disclosed in 5.29.0 under the generic "other findings may also differ" clause (D-17, Phase 240). |

No "Gap-closure plan required:" line: no extra was marked fix.

## Deviations from Plan

None. Executed inline by the orchestrator (no code, no shared tracked file edited), and the
decision was collected with a blocking question.

## Self-Check

- todo file exists (`test -f`): yes
- Kerberos / DNSSEC not re-asked: yes
