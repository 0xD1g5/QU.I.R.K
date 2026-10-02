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

## Resolution (Phase 220)

**Closed 2026-10-01 by Phase 220 (CITRUTH-02), plans 220-02, 220-03 and 220-07. Option 3 chosen:
MinIO replaced.** Operator decision D-01R (2026-10-01) superseded the original choice (option 1,
GHCR mirror, D-01, 2026-09-30). The mirror was abandoned because its only source, the two cached
images (`14cea493d9a3`, `993e8c454a7e`), was gone from Docker Desktop on resume, and every upstream
channel was closed: Docker Hub 404, quay.io 401, dl.min.io **410** for both pinned releases. Building
from source (option 2) would have made the project an AGPLv3 binary publisher and the owner of a
multi-arch Go build.

- **Fix (220-03, `bc389a44` / `1911a241`):** the four services `minio`, `minio-seed`,
  `mh-storage-archive` and `mh-storage-seed` run `motoserver/moto:5.2.3` (Apache-2.0, Docker Hub,
  amd64+arm64). Seeding is one boto3 script, `storage/s3-seed.py`, run from the same image. Both
  mc shell scripts were deleted. The endpoints (`:29000`, `10.80.0.50:9000`), the `minio` service
  names and the `minioadmin` creds are kept (rename tracked in `261001-rename-chaos-lab-minio-services-to-s3.md`).
  The scanner needs only `list_buckets`, `get_bucket_encryption` and
  `ServerSideEncryptionConfigurationNotFoundError`, all verified against moto.
- **Honest skip (220-02, D-04, `0cf2eb35`):** `test_profile_re_up_is_idempotent` skips only when the
  first `up` fails with a registry `unauthorized`/`denied`/`not found` pull error naming the image AND
  an anonymous control probe (`library/alpine:3.20` on docker.io) succeeds. Any other failure still
  fails. The skip did not fire in either proof below.
- **Cache-less proofs:** `220-diag/MOTO-PROOF.md` (220-03: `docker rmi`, empty `docker images`, then
  `2 passed` with an anonymous client config) and `220-diag/CACHELESS.md` (220-07, re-run at the
  pre-push tree: same steps, `2 passed in 68.00s`, re-pulled digest
  `sha256:91fd602a21f49cf9eb82fdf474015a3c131d40104c8297ea6a2ca920708ae32c`, identical to 220-03's).
- **Observed behaviour change:** MinIO's `:9001` console is gone, so the multihost `.50` HIGH count
  is 1 (observed by a scoped scan), not 2. The full-estate aggregate 14 -> 13 HIGH is marked DERIVED in
  `expected_results_v4.md`.
- **Docs touched:** `docker-compose.yml` comments, `quantum-chaos-enterprise-lab/README.md`,
  `expected_results_v4.md`, `labs/storage/expected_results.md`, `docs/chaos-lab.md` (+ vault
  `Chaos-Lab.md`), `docs/UAT-SERIES.md` (UAT-28-01 reworded; Series 220 UAT-220-02/03; the two
  "permanently withdrawn" notes annotated), and CLAUDE.md. `lab.sh` references no image and was not
  edited. The "environmental" label on these nodes in `STATE.md`'s v5.25 Deferred Items row was
  annotated as superseded.

**This todo is closed on local cache-less evidence, not on CI.** The CI leg (both nodes `passed`, not
skipped, on the branch's `Linux Full Suite` dispatch) is recorded by 220-08 in
`220-diag/CI-EVIDENCE.md` and `220-VERIFICATION.md`; the "green on `main`" leg can only be checked
after the PR merges. **If 220-08's CI leg fails or skips either node, move this file back to
`.planning/todos/pending/`** (`git mv`) and record the run id and the reason here.
