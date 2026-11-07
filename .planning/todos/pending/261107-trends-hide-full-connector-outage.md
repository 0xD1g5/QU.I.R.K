---
type: todo
created: 2026-11-07
title: Trends hide a full connector outage but show a partial one
source: Phase 235.3 code review B-WR-07 (deferred; 235.3-REVIEW.md)
priority: medium
area: quirk/intelligence/trends.py
status: pending
resolves_phase: null
owner: null
---

# Trends hide a full connector outage but show a partial one

## Observed

`quirk/intelligence/trends.py` (`_ADVISORY_ONLY_CATEGORIES`, ~line 39; used ~439-448). If one of four JWT targets
stops answering, a `target_unanswered` row appears and counts as a scan-error regression. If all four stop, the
result is one `targets_unreachable` ADVISORY, which trends treat as advisory-only and exclude, and JWT/SAML/DNSSEC
emit no in-band rows. `scan_errors_new_count` becomes 0, so the worse outcome reads as no regression.

The score is not affected: the skip rows count via `evidence.scan_error_count` (235.3 paired-scan proof). Only the
run-to-run trend signal is wrong.

## Why it was deferred

235.3 research decision P-02 made all coverage-skip categories advisory-only in trends by design. The review
found the split between environment facts and run-to-run regressions after that decision was locked.

## Fix sketch

Keep only the environment categories advisory-only in trends (`missing_extra`, `missing_binary`, arguably
`internal_target_refused`). Let `targets_unreachable`, `auth_failed` and `missing_credentials` count as regressions,
or count `len(failures)` for them so a full outage matches the partial case. Add a trends test: four of four
targets down regresses at least as much as one of four.

## Feasibility & Effort

Small. One category set in `trends.py`, plus a parametrized test. Check `sensor_cmd` and `findings_evaluator`,
which share `COVERAGE_SKIP_ADVISORY_CATEGORIES`, so the change does not widen beyond trends.

LEDGER row needed once `chore/master-ledger` merges (`.planning/LEDGER.md` is not on `v5282-open`).
