---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS fork B1; ledger rows DCL-OPS-B-0089 and DCL-OPS-B-0094 (docs/operators-guide.md §8.4 "Merge into a unified CBOM")
priority: high
area: quirk/merge/scan.py (_assemble_union), quirk/dashboard/api/routes/merge.py (/api/merge/latest per-segment gauges)
status: completed
completed: 2026-10-15
resolves_phase: 229
owner: FIND-13
---

# `sensor merge` keeps exactly one endpoint row per sensor, not the sensor's latest push

`_assemble_union` (`quirk/merge/scan.py:98-153`) selects sensor rows with a subquery of
`(sensor_id, max(scanned_at), max(id))` and joins on BOTH `scanned_at == max_ts` AND `id == max_id`
(`quirk/merge/scan.py:110-131`). The comment says this "guarantees exactly one row per sensor", and it does: a sensor
that pushed N endpoints contributes ONE endpoint (the highest-id row) to the merged CBOM and score. If the highest-id row
does not also carry the max `scanned_at`, the sensor contributes zero rows.

Live probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc2-ops-b1-merge-union-probe.py`: one enrolled sensor,
`console import-results` of a .qpush with three TLS endpoints h0/h1/h2.internal, then `sensor merge`):

```
crypto_endpoints rows for sensor: 3 rows, 3 distinct hosts
merge_runs.endpoint_count: 1, sensor_count: 1
CBOM hosts: ['h2.internal']
```

The regression came from DIST-01 (commit f3476cc2, Phase 125, "merge tiebreak"), whose test
`tests/test_merge_scan.py::test_same_second_scanned_at_tie_returns_one_row_per_sensor` asserts exactly one row for two
different hosts pushed by one sensor in the same second, i.e. it pins the defect as intended behaviour. f3476cc2 is an
ancestor of v5.11.0 and every later release, so every released merge since then is affected. The dashboard's
`/api/merge/latest` (`quirk/dashboard/api/routes/merge.py:78`) calls the same `_assemble_union` for the Executive
page's per-segment gauges and live overall score, and the auto-merge path (`quirk/dashboard/api/routes/sensor.py:245`)
calls `merge_scan`, so both inherit it.

The operators-guide §8.4 now states the one-row-per-sensor behaviour and calls it a known defect.

- [x] Select every row of each sensor's latest push (e.g. by the push's payload/scan id, or all rows with the sensor's
      max `scanned_at`, tie-broken by payload rather than by row id).
- [x] Rewrite the DIST-01 test to assert all endpoints of the latest push are kept and older pushes are excluded.
- [x] Re-check `/api/merge/latest` per-segment gauges and the auto-merge path against the fix.
- [x] Remove the "known defect" sentence from docs/operators-guide.md §8.4.

## Feasibility & Effort

- **CONFIRMED** by the live probe above and by reading `quirk/merge/scan.py:110-131` and the f3476cc2 diff.
- **UNKNOWN**: whether pushed rows carry a payload/batch id the union can group on. `crypto_endpoints` rows are keyed by
  `sensor_id` and `scanned_at` (from the sensor's own scan, per-endpoint), so "latest push" may need a new column or a
  join through the ingest audit/payload table. Check `quirk/dashboard/api/routes/sensor.py` ingest and `quirk/models.py`
  before choosing. Effort **M** (query + likely schema/migration + test rewrite). A short spike on the grouping key is
  worthwhile.

## Resolution (Phase 229, 2026-10-15)

Closed by FIND-13. Fix commits:

- `e9cb48b6` (229-06): additive `crypto_endpoints.push_payload_id` column (D-12), the grouping key the UNKNOWN above asked for.
- `9bc820c8` (229-06): ingest stamps every endpoint with its push payload id.
- `054e0638` (229-07): `_assemble_union` keeps every endpoint of each sensor's latest push (D-13/D-14); the DIST-01 test that pinned one row per sensor is replaced by five tests (latest push, same-`received_at` tie, empty latest push, legacy same-second, forged-tag cross-sensor).
- `8b7c2374` (229-07): end-to-end `console import-results` -> `sensor merge --db` test, and the `/api/merge/latest` per-segment test.
- Docs: `4ce19f2b` (operators guide, "known defect" sentence removed; README line also corrected).

Proving nodes (UAT-229-08..10): `tests/test_sensor_merge_all_endpoints.py::test_one_sensor_qpush_three_hosts_merges_all_three`, `::test_two_sensors_multi_endpoint_cli_merge`; `tests/test_merge_scan.py`; `tests/test_dashboard_merge_latest.py::test_per_segment_scores_use_every_endpoint_of_latest_push`; `tests/test_db_migrations.py::test_phase229_push_payload_id_column_registered`; `tests/test_sensor_push_payload_id.py::test_ingest_stamps_every_endpoint_with_payload_id`.

A separate defect found while doing this (an out-of-order air-gap .qpush can become the latest push) is filed under HORIZON 999.134 as `261015-find-airgap-out-of-order-qpush-becomes-latest-push.md`.
