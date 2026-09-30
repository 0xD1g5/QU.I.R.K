# MinIO images are no longer publicly pullable — `storage-s3` and `multihost` chaos-lab profiles cannot come up in CI

**Filed:** 2026-09-30, while diagnosing PR #40's red `Linux Full Suite` (runs `36656847737` attempts 1 and 2).
**Priority:** P1 — the required-adjacent `Linux Full Suite` is permanently red on `main` and every PR
until this is fixed, which trains everyone to read red as "the usual flake".
**Owner:** unassigned — a quick task, or Phase 220 (CI Instrument Truth). Operator to choose the fix option.

## The finding

`tests/test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent[multihost]` and `[storage-s3]`
fail with `Error response from daemon: unauthorized: access to the requested resource is not
authorized`. The refused pulls are only the MinIO services (`minio`, `minio-seed`,
`mh-storage-seed`, `mh-storage-archive`), which pin:

- `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z`
- `quay.io/minio/mc:RELEASE.2024-11-21T17-21-54Z`

(`quantum-chaos-enterprise-lab/docker-compose.yml`, services at ~:986, :1012, :1697, :1722.)

**Evidence (2026-09-30, anonymous registry-v2 token + manifest HEAD):**

| Probe | Result |
|-------|--------|
| quay `prometheus/node-exporter:latest` (control — a known-public repo) | **200** |
| quay `minio/minio` pinned tag, and `:latest` | **401** |
| quay `minio/mc` pinned tag, and `:latest` | **401** |
| quay repo API `minio/minio`, `minio/mc` | 401 |
| Docker Hub `minio/minio`, `minio/mc` | 404 (withdrawn earlier; see compose comment dated 2026-09-13) |

The control probe returning 200 rules out the probe method: the MinIO repositories went private.
Any tag fails, so this is not a pinned-tag deletion.

## This is the SECOND misdiagnosis of the same failure

Before 2026-09-13 it was carried as a "Docker Hub rate limit" flake; the compose comment records
that the images had in fact been removed. After the move to quay.io, the same two nodes were again
carried as "environmental / Docker registry unauthorized" — in the v5.25 close Deferred Items, in
PR #39's and #40's descriptions, and in Phase 217's close-out. It is not intermittent: these nodes
can never pass in a cache-less CI runner. (PR #39's run passing them is unexplained — likely a
runner-side image cache hit — and should not be read as the registry recovering.)

**Why it hides locally:** the operator's Docker has both pinned images cached (image IDs
`14cea493d9a3`, `993e8c454a7e`), so every local lab run succeeds.

## Fix options (operator decision)

1. **Mirror to GHCR** — `docker save` the cached images (or retag/push) to the project's own
   `ghcr.io/<owner>/…` and repoint compose. Smallest change, byte-identical images; MinIO is AGPLv3,
   which permits redistribution. The project then owns that mirror.
2. **Build from source** — a lab Dockerfile building a pinned MinIO release from GitHub. No
   registry dependency; slower builds, a Go toolchain to maintain.
3. **Replace MinIO** with an S3-compatible server that is still openly published. Most durable,
   but changes scanner-observed behaviour.

Any option touching the lab triggers CLAUDE.md § Chaos Lab Maintenance: update `lab.sh`,
`quantum-chaos-enterprise-lab/README.md`, `docs/chaos-lab.md`, and `expected_results_v4.md` (the
oracle that mentions MinIO) in the same change. Re-verify with a **cache-less** pull
(`docker rmi` the images first, or rely on the CI run), not a local `lab.sh up`.

## Also correct when fixing

- The compose comment at ~:986 ("quay.io, NOT Docker Hub … Verified 2026-09-13") — true then, stale now.
- Every "environmental" label on these two nodes, so the next red run is not waved through.
