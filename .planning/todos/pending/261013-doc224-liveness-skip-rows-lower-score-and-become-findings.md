---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-R05; ledger rows DCL-REPORTINT-0122 / 0813 / 0814 (docs/report-interpretation.md §12 "excluded from the readiness score and from every severity-ranked findings table")
priority: medium
area: quirk/intelligence/evidence.py (scan_error_count / rate), quirk/engine/findings_evaluator.py (generic scan_err branch)
status: pending
resolves_phase: null
owner: "999.131"
---

# Liveness pre-pass rows lower the readiness score and become INFO findings

Phase 145 designed `liveness_skip` / `privilege_fallback` rows as normal outcomes, not failures
(`run_scan.py:2270-2278`: kept out of `error_endpoints` until after the discovery partial-failure
snapshot "so normal liveness skips ... never mark discovery as partially failed"). The report
pipeline does not honour that intent:

- The rows carry `scan_error` (`run_scan.py:2387` `"scan_error": "liveness pre-pass: no response"`,
  `run_scan.py:531` for `privilege_fallback`) and are merged into `error_endpoints`
  (`run_scan.py:2497`), which joins the report endpoint list (`run_scan.py:4071`).
- `quirk/intelligence/evidence.py:244-246` counts every endpoint with `scan_error`, including
  `protocol="ADVISORY"` rows, and `:525` divides by all endpoints to get the scan-error rate.
  `_NON_ASSET_PROTOCOLS` (`:40`, `:249`) only gates the coverage counters, not this one.
- `quirk/intelligence/scoring.py:494` and `:501` subtract the rate from hygiene and modern-TLS.
- `quirk/engine/findings_evaluator.py:461` special-cases only `missing_extra` ADVISORY rows; every
  other row with `scan_error` falls to the generic branch (`:521-534`) and becomes an INFO
  "Informational protocol observation" finding.

Probe (isolated HOME): one clean TLS 1.3 endpoint scores 75; adding 10 `liveness_skip` rows and one
`privilege_fallback` row drops it to 63 (driver `Scan error rate -6`) and adds 11 INFO findings.
So a sparse range (most addresses down) scores worse than a dense one with identical services.

- [ ] Exclude `liveness_skip` / `privilege_fallback` (or all `ADVISORY` rows) from `scan_error_count`
      and the rate denominator in `build_evidence_summary`.
- [ ] Skip them in `evaluate_endpoints` (as `missing_extra` is skipped) or emit a distinct advisory.
- [ ] Test: adding liveness rows leaves score and findings unchanged.
- [ ] Revert the §12 doc caveat in docs/report-interpretation.md once fixed.

## Same defect: unreached-broker-target ADVISORY rows (report-interpretation.md §20)

Merged here from a duplicate filed the same day (R05 chunk F). The unreached-broker ADVISORY row takes the
same path: it counts toward `scan_error`, lowers the score, and becomes an INFO report finding the dashboard
does not show.

```
evaluate_endpoints(cfg, build_unreached_target_advisories([("broker.internal", 29099)], []))
  -> [("INFO", "Informational protocol observation", detail "Configured broker target broker.internal:29099 did not respond to any probe")]
dashboard _derive_findings(same rows) -> []
compute_readiness_score, 5-endpoint severity-floor fixture, without / with the advisory row -> 34 / 33
  (hygiene 25 -> 24, modern_tls 25 -> 24; evidence scan_error count 0 -> 1, rate 0 -> 0.1667)
```

(`.venv/bin/python`, isolated HOME/XDG, fixtures from `tests/test_score_severity_floor_regression.py`.)

- `quirk/intelligence/evidence.py:245` counts every row with a `scan_error`, BEFORE the `_NON_ASSET_PROTOCOLS`
  check at :250 that excludes ADVISORY/CLOSED from the coverage counters. `quirk/intelligence/scoring.py:494` and
  `:501` then penalise hygiene and modern-TLS by the scan-error rate.
- `quirk/engine/findings_evaluator.py:521-535` turns any non-`missing_extra` ADVISORY row with a `scan_error` into
  an INFO "Informational protocol observation" finding, which the HTML All Findings and DOCX Findings tables list.
  The dashboard's `findings_for_endpoint` emits nothing for the same row, so report and dashboard disagree.
- The unreached-target row is produced at `quirk/scanner/broker_scanner.py:136-143` and folded into the RabbitMQ
  endpoint list at `run_scan.py:3988`.

Same root cause as `261013-doc224-liveness-skip-rows-lower-score-and-become-findings.md` (liveness pre-pass ADVISORY rows); fix them together.

The doc now states the real behaviour. If this is fixed, restore the "excluded from the score" wording in §20 (and
re-check the §12 claim about every ADVISORY row, which is not in this chunk).

- [ ] Fix for ALL ADVISORY producers at once (liveness pre-pass, privilege fallback, unreached broker target),
      and revert the §20 caveat ("Advisory, but not invisible to the score") along with the §12 one.

## Feasibility & Effort

- **CONFIRMED** defect path: `evidence.py:244-246,525`, `scoring.py:494,501`,
  `findings_evaluator.py:461,521-533`, `run_scan.py:2387,2497,4071` read directly; behaviour
  reproduced with `evaluate_endpoints` + `build_evidence_summary` + `compute_readiness_score`.
- **LIKELY** effort **S**: two filters plus tests. Changes scores on any estate with down hosts, so
  it interacts with `SCORING_VERSION` disclosure (`scoring.py:29`): decide whether it needs a bump.
- **UNKNOWN**: whether `discovery_exception` rows (`protocol="ERROR"`, `run_scan.py:2416-2424`)
  should also stop counting; they are real failures, so probably keep. No spike needed.
