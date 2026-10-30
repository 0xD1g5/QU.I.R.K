# 999.139 — Score-truth residuals after Phase 234 (successor to 999.120)

**Filed:** 2026-10-27 (Phase 234, plan 234-08)
**Priority:** P2 (each member is a disclosed limit, not a regression; none moves a released score today)
**Horizon entry:** `HORIZON.md` Open-Item Ledger, row `999.139`.

## Why this exists

Phase 234 closed 999.120: scoring 4.0 (`23ef422875071113ca33e81c9eb63ce35d2db4de`) stops healthy endpoints from
raising the readiness score, and SCORE-10 stops the QRAMM overall from counting a Not-assessed dimension as 0. The
re-measurement record `.planning/decisions/234-p2b-fix-and-ladder-remeasurement.md` §10 ("Properties this change does
NOT claim") lists what is still true of the score that a reader might not expect. Each has a todo here so it has an
owner the backlog gates can see, instead of living only in a decision record.

## Members

| Todo | What |
|------|------|
| `261027-score-newly-assessed-domain-step-is-coverage-credit.md` | O-6: the first clean row of a not-yet-assessed domain raises the headline (R4 22/66 -> 24/72); deliberate and pinned, needs an operator decision |
| `261027-scan-error-count-includes-closed-and-advisory-rows.md` | D-19: CLOSED/ADVISORY scan-error rows lower the score (R3 46/85 -> 42/78 at +100 closed rows) |
| `261027-tls-scanner-ml-dsa-leaf-raises-unknown-key-type.md` | D-20: ML-DSA leaf keys (OIDs 2.16.840.1.101.3.4.3.17/18/19, RFC 9881) raise "Unknown key type", so the PQC certificate bucket is dormant on real scans |
| `261027-qramm-stale-detection-compares-counts-not-values.md` | D-21: re-answering a question with a different value does not mark the QRAMM score stale |
| `261027-qramm-scorecard-legacy-recalculate-branch-unreachable.md` | Residual (b), review IN-07: only print reads the saved QRAMM score, so the scorecard's Recalculate branch is unreachable live |
| `261027-doc-claim-ledger-source-line-cites-drift.md` | About 441 doc-claim-ledger evidence cites point at moved source lines; the gate checks file existence only |

Not a member: RESEARCH Pitfall 8 (the legacy-TLS lift is 0 on live evidence) is already owned by
`261012-doc224-legacy-tls-roadmap-and-lift-still-use-low-severity-proxy.md` under 999.131.

## Feasibility & Effort

| Item | Feasibility | Size | Unknowns | Spike? |
|---|---|---|---|---|
| O-6 newly-assessed-domain step | **CONFIRMED** (record §10 measurement; pinned by `tests/test_score_newly_assessed_domain.py`) | S-M | Operator decision: keep as coverage credit, neutral entry value, or a minimum population; any change re-measures every rung | No — decision first |
| D-19 assessable-only scan-error count | **CONFIRMED** (record §10; `quirk/intelligence/evidence.py:300-302` counts every `scan_error` row) | S | Changes scores, so it needs a scoring-version note, a spec-first closed-form change and a ladder re-measurement | No |
| D-20 ML-DSA OID fallback in `tls_scanner._pubkey_info` | **CONFIRMED** (record §10, D-20) | M | Needs an ML-DSA test certificate (OpenSSL 3.5+) and a scanner-level fixture; SLH-DSA OIDs if a cert is available | Small spike to produce the test certificate |
| D-21 QRAMM answers digest | **CONFIRMED** (`quirk/qramm/assessment_state.py:101` compares counts) | S | Fallback for scores saved before the digest; one new shared-contract case | No |
| Scorecard legacy branch (residual b) | **CONFIRMED** (`QRAMMProvider.tsx:18` initialises `scoreResult` to null) | S | UX decision: load the saved score into the scorecard, or remove the branch | No |
| Doc-claim-ledger cite drift | **CONFIRMED** by 234-07's scripted count | M | Tolerance rule for quoted text spanning lines; recount before and after | No |
