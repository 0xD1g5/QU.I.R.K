---
type: todo
created: 2026-10-12
source: Phase 224 plan 06 (docs/chaos-lab.md audit)
priority: medium
area: quantum-chaos-enterprise-lab/lab.sh (ensure_profile_certs), labs/{postgres-tls,redis-tls,kafka-tls}/
status: pending
resolves_phase: null
owner: "999.119"
---

# `lab.sh` does not generate the postgres-tls, redis-tls and kafka-tls certificates

**Filed:** 2026-10-12 (Phase 224 plan 06, docs/chaos-lab.md audit)
**Priority:** P2 — first `up` of three profiles silently mounts a directory where a certificate file is expected
**Status:** open
Frontmatter added by Phase 227 (D-02): priority derived from the body Priority line (P2 → medium).

## What happens

`lab.sh` materialises the mTLS CA/client pair and, via `ensure_profile_certs`, the `email` and `grpc-tls`
certificates (D-12/D-13). The `postgres-tls`, `redis-tls` and `kafka-tls` services bind-mount
`../labs/<profile>/certs/<profile>.{crt,key}`, which are gitignored and produced only by
`make -C labs/<profile> certs`. Nothing in `lab.sh` mentions those three profiles
(`grep -cE 'postgres-tls|redis-tls|kafka-tls' quantum-chaos-enterprise-lab/lab.sh` prints 0).

Evidence the failure mode is real: the working tree of the operator checkout has
`labs/{postgres-tls,redis-tls,kafka-tls}/certs/<name>.{crt,key}` as **directories**, the artefact Docker
creates when a bind-mount source is missing, which is exactly what `ensure_profile_certs`' own comment says
it exists to prevent.

`docs/chaos-lab.md` now tells the operator to run the `make certs` step first.

## Fix

Extend `ensure_profile_certs` with the three profiles' `openssl req` calls (their Makefile recipes are the
template), and add a regression check next to the existing cert tests. A pre-existing directory at the target
path needs handling (error out with the remedy rather than treat it as present).

## Feasibility & Effort

- Feasibility: CONFIRMED (lab.sh read in full; Makefile recipes read; directories observed on disk).
- Effort: S — roughly 30 lines of shell mirroring the grpc-tls block, plus a test.
- Unknowns: none material.
- Spike needed: no.
