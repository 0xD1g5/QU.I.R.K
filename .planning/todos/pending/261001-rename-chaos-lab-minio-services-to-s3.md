# Rename the chaos lab's MinIO-era S3 services, hostname, creds and labels (they run moto now)

**Filed:** 2026-10-01, by plan 220-03 (Phase 220 D-03R).
**Priority:** P3. This is cosmetic and misleading-name debt, with no functional defect.
**Owner:** unassigned. A quick task, or fold it into the next chaos-lab phase.

## Why this exists

Phase 220 (D-01R) replaced MinIO with moto (`motoserver/moto:5.2.3`, Apache-2.0) in the four
chaos-lab S3 services, because MinIO's images became unpullable from every channel (Docker Hub
404, quay.io 401, dl.min.io 410, and the local cache lost on 2026-10-01). To bound the blast radius
of that change, D-03R **deliberately kept** the MinIO-era names:

- compose services `minio`, `minio-seed` (profile `storage-s3`) and `mh-storage-archive`,
  `mh-storage-seed` (profile `multihost`; these two names are already neutral)
- the `minio` hostname, used in the seed entrypoint `http://minio:9000`
- the `minioadmin` / `minioadmin` credentials, used in `mh-prober`'s env,
  `storage/s3-seed.py`'s defaults, `tests/test_chaos_storage.py` and `labs/storage/expected_results.md`
- test names `test_minio_*` in `tests/test_chaos_storage.py`, plus the matching
  `tests/skip_registry.py` rows (:77-78, reason text "Requires Docker + MinIO")
- the `test_cbom_motion_endpoints.py:670` docstring ("storage-s3 profile — MinIO S3")
- container names `chaoslab-minio-1` / `chaoslab-minio-seed-1`, cited in docs and UAT steps

Every one of these now names a server the lab no longer runs. Compose comments, README, and
`docs/chaos-lab.md` say so explicitly, but a reader skimming `docker ps` still sees "minio".

## Scope of the rename (do in ONE change)

1. Rename the services to e.g. `s3` / `s3-seed`. Update `depends_on` and the seed endpoint URL.
2. Change the creds to neutral values (e.g. `labaccess`/`labsecret`). Update `mh-prober` env,
   the `s3-seed.py` defaults, the live tests, and `labs/storage/expected_results.md`.
3. Rename `test_minio_*` and update `tests/skip_registry.py` in the same commit. It keys by
   `(filename, testname)`.
4. Update `docs/chaos-lab.md` + vault, `quantum-chaos-enterprise-lab/README.md`, and
   `expected_results_v4.md` (storage-s3 table "Service" column). Also update `docs/UAT-SERIES.md`
   UAT-28-01, which then needs a re-disposition check and a `docs/uat-coverage-gaps.md` regen if its
   Result changes.
5. Re-run `pytest tests/test_chaos_lab_idempotency.py -k "multihost or storage-s3" -m ""` and the
   live `QUIRK_RUN_DOCKER_IT=1 pytest tests/test_chaos_storage.py -m ""`. Confirm an `N passed`
   count.

## Do NOT rename

Product text that names MinIO as a **customer** target (`quirk/config.py`, `config_template.yaml`,
`ConnectorsPanel.tsx`, `docs/configuration.md`, `docs/connector-field-reference.md`,
`tests/test_s3_encryption.py`). The scanner still supports MinIO endpoints. Only the lab stopped
running one.
