# 999.119 — CI and chaos-lab hygiene carried out of Phase 220

**Filed:** 2026-10-01 (Phase 221, gap closure of v5.26-MILESTONE-AUDIT INT-01)
**Priority:** P2 (raised from P3 by Phase 227, D-10)
**Horizon entry:** `HORIZON.md` Open-Item Ledger, row `999.119`.

## Why this exists

Two todos named Phase 220 (CI Instrument Truth) as owner or hand-off and were left ownerless when it closed.
Neither is an accessibility item, so they do not belong in 999.118.

## Scope

| # | Todo | What |
|---|---|---|
| 11 | `260929-windows-sensor-e2e-empty-api-token-on-branch-dispatch.md` | Windows Sensor E2E gets an empty `--api-token` on a branch `workflow_dispatch`; the parse step's guard accepts an empty token and the failure surfaces two steps later as an argparse error |
| 12 | `261001-rename-chaos-lab-minio-services-to-s3.md` | The chaos lab's S3 services run moto but keep MinIO-era names, hostname and credentials (Phase 220 D-03R kept them deliberately) |
| 13 | `261012-doc224-chaos-lab-oracle-readme-comment-drift.md` | Oracle (`expected_results_hwcompat.md`, `expected_results_v4.md`), README and compose comments disagree with the code (confidence grades, finding wording, fuzz-target tags). Priority P3 (low). |
| 14 | `261012-doc224-chaos-lab-profile-certs-not-generated-by-lab-sh.md` | `lab.sh` `ensure_profile_certs` generates only the email and grpc-tls certs; postgres-tls, redis-tls and kafka-tls bind-mount missing cert files and Docker creates directories. Priority P2 (medium). |
| 15 | `261012-doc224-chaos-lab-scanner-cannot-reach-fixtures.md` | hwcompat-http (20222), ldaps code-signing (636 vs plaintext 389), email, fuzz-target and DNSSEC fixtures sit on host ports the scanner never probes. Priority P2 (medium). |

Rows 13-15 were added by Phase 227 (2026-10-15, D-09; owner `999.119` in each todo's frontmatter). Priority raised P3→P2 by Phase 227 (D-10): two new members are medium.

## Feasibility & Effort

| Item | Feasibility | Size | Unknowns | Spike? |
|---|---|---|---|---|
| 11. Empty `--api-token` | **CONFIRMED** — `$raw_token` is consumed at `.github/workflows/python-ci.yml:350` (`--api-token $raw_token`) and read from `$env:RUNNER_TEMP\e2e_token.txt` per the todo (cites `:326`); the fix is an `IsNullOrWhiteSpace` assertion at the point of reading plus finding why the console-enroll step wrote an empty file on branch dispatch | S for the guard, UNKNOWN for the root cause | Why only branch dispatches see an empty token (main is green) | YES, one dispatch with debug output |
| 12. Rename minio to s3 | **CONFIRMED** — names live at `quantum-chaos-enterprise-lab/docker-compose.yml:986` (`minio`), `:1020` (`minio-seed`), `:1031` (`http://minio:9000`), `:2236-2237` (`minioadmin` creds), with the explanatory comment at `:998-1001` | M (many references, oracle files) | Scanner oracle strings that embed `minio` | no |
| 13. Oracle/README/comment drift | **CONFIRMED** (re-grepped 2026-10-15) — `quantum-chaos-enterprise-lab/expected_results_v4.md:878` still says "Kafka plaintext listener detected" while `quirk/engine/findings_evaluator.py:937` emits "Plaintext Kafka listener detected" | S-M (text edits across several oracle files) | Whether every cited drift item is still live; recheck each against code | no |
| 14. Profile certs not generated | **CONFIRMED** — `quantum-chaos-enterprise-lab/lab.sh:134` `ensure_profile_certs` handles email only in the first block; the only `postgres-tls`/`redis-tls`/`kafka-tls` mentions in lab.sh are help text at `:34-35` (the todo says count 0; it is now 2, both usage prose, no generation) | S | Whether to call `make -C labs/<profile> certs` or generate inline | no |
| 15. Scanner cannot reach fixtures | **CONFIRMED** — `quirk/scanner/hardware_scanner.py:35` `_HTTP_MGMT_PORTS = (443, 8443, 8080, 80)` vs `docker-compose.yml:1355` `"20222:80"`; `quirk/scanner/codesign_scanner.py:268` builds `ldap3.Server(host, port=...)` with no `use_ssl` | M (compose port mappings plus scanner/lab oracle decisions across 5 fixtures) | Per-fixture choice: lab remap vs scanner change | YES for the ldaps case |

Constraints:

- Any fix to rows 13-15 must update `quantum-chaos-enterprise-lab/lab.sh`, the lab `README.md` and the `expected_results_*.md` oracle together (CLAUDE.md §Chaos Lab Maintenance).

- CLAUDE.md §Chaos Lab Maintenance applies to #12: `quantum-chaos-enterprise-lab/lab.sh`, the lab `README.md` and the `expected_results_*.md` oracle must change in the same change as the compose rename.
- CLAUDE.md §CITRUTH-03 names `DISPATCH_ADVISORY_JOBS` as demoting Windows Sensor E2E on branch dispatch because of todo 260929. That exception must be removed when #11 closes. Do not rename or move the 260929 todo file; CLAUDE.md references it by name.

### Sequencing

#11 first (it blocks treating a branch dispatch as fully green); #12 can fold into the next chaos-lab phase.

### Costs not visible in the site count

- #11's root cause may sit in the console-enroll step, not the sensor step the todo names.
- #12 touches every oracle that mentions the old names; regenerate expected results against a live lab run.
