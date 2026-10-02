# 999.119 — CI and chaos-lab hygiene carried out of Phase 220

**Filed:** 2026-10-01 (Phase 221, gap closure of v5.26-MILESTONE-AUDIT INT-01)
**Priority:** P3
**Horizon entry:** `HORIZON.md` Open-Item Ledger, row `999.119`.

## Why this exists

Two todos named Phase 220 (CI Instrument Truth) as owner or hand-off and were left ownerless when it closed.
Neither is an accessibility item, so they do not belong in 999.118.

## Scope

| # | Todo | What |
|---|---|---|
| 11 | `260929-windows-sensor-e2e-empty-api-token-on-branch-dispatch.md` | Windows Sensor E2E gets an empty `--api-token` on a branch `workflow_dispatch`; the parse step's guard accepts an empty token and the failure surfaces two steps later as an argparse error |
| 12 | `261001-rename-chaos-lab-minio-services-to-s3.md` | The chaos lab's S3 services run moto but keep MinIO-era names, hostname and credentials (Phase 220 D-03R kept them deliberately) |

## Feasibility & Effort

| Item | Feasibility | Size | Unknowns | Spike? |
|---|---|---|---|---|
| 11. Empty `--api-token` | **CONFIRMED** — `$raw_token` is consumed at `.github/workflows/python-ci.yml:350` (`--api-token $raw_token`) and read from `$env:RUNNER_TEMP\e2e_token.txt` per the todo (cites `:326`); the fix is an `IsNullOrWhiteSpace` assertion at the point of reading plus finding why the console-enroll step wrote an empty file on branch dispatch | S for the guard, UNKNOWN for the root cause | Why only branch dispatches see an empty token (main is green) | YES, one dispatch with debug output |
| 12. Rename minio to s3 | **CONFIRMED** — names live at `quantum-chaos-enterprise-lab/docker-compose.yml:986` (`minio`), `:1020` (`minio-seed`), `:1031` (`http://minio:9000`), `:2236-2237` (`minioadmin` creds), with the explanatory comment at `:998-1001` | M (many references, oracle files) | Scanner oracle strings that embed `minio` | no |

Constraints:

- CLAUDE.md §Chaos Lab Maintenance applies to #12: `quantum-chaos-enterprise-lab/lab.sh`, the lab `README.md` and the `expected_results_*.md` oracle must change in the same change as the compose rename.
- CLAUDE.md §CITRUTH-03 names `DISPATCH_ADVISORY_JOBS` as demoting Windows Sensor E2E on branch dispatch because of todo 260929. That exception must be removed when #11 closes. Do not rename or move the 260929 todo file; CLAUDE.md references it by name.

### Sequencing

#11 first (it blocks treating a branch dispatch as fully green); #12 can fold into the next chaos-lab phase.

### Costs not visible in the site count

- #11's root cause may sit in the console-enroll step, not the sensor step the todo names.
- #12 touches every oracle that mentions the old names; regenerate expected results against a live lab run.
