---
phase: 82-chaos-lab-fidelity
plan: 03
subsystem: chaos-lab
tags: [chaos-lab, idempotency, gitea, def-999.83, image-pinning]
status: complete
requires: []
provides: ["Idempotent gitea source seeding short-circuited by sentinel-repo probe"]
affects: ["quantum-chaos-enterprise-lab/source/seed.sh", "quantum-chaos-enterprise-lab/docker-compose.yml (gitea-seed block)", "quantum-chaos-enterprise-lab/expected_results_v4.md"]
tech_stack:
  added: []
  patterns: ["Top-level sentinel-existence short-circuit before any state-mutating API calls"]
key_files:
  created: []
  modified:
    - quantum-chaos-enterprise-lab/source/seed.sh
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/expected_results_v4.md
decisions:
  - "Sentinel-repo predicate (not org predicate) — seed.sh provisions repos under labadmin user, not under a Gitea organization"
  - "Sentinel = crypto-antipatterns-python (the first repo seed.sh creates today)"
  - "alpine:3.19 → alpine:3.20 for gitea-seed sidecar (parity with the two other alpine pins in compose; 3.19 EOL 2025-11)"
metrics:
  duration: "~5 min"
  completed: "2026-05-16"
  commit_sha: "fdded8e"
---

# Phase 82 Plan 03: Gitea Source Seed Idempotency Summary

Closes DEF-999.83-C / CHAOS-03 by adding a top-level sentinel-repo
short-circuit at the head of `quantum-chaos-enterprise-lab/source/seed.sh`,
making re-runs of `PROFILE_ARGS="--profile source" ./lab.sh up` against a
persisted `gitea_data` volume a clean no-op.

## Predicate Choice

**Chosen:** sentinel-repo existence probe at
`/api/v1/repos/labadmin/crypto-antipatterns-python`.

**Rationale:** End-to-end reading of `seed.sh` shows the script provisions
repos under the `labadmin` user via `POST /api/v1/user/repos` — there is
no organization in play. The CONTEXT D-3 example referenced
`/api/v1/orgs/quirk-lab`, but that doesn't match the script's actual
provisioning model. The right predicate is the canonical sentinel repo:
the first one the script attempts to create, `crypto-antipatterns-python`.
If it exists, the entire seed pass can short-circuit.

## seed.sh Diff Summary

Inserted a 12-line block between the Gitea readiness wait and the
`=== Creating repos ===` banner:

```sh
# ---- Idempotency short-circuit (CHAOS-03 / DEF-999.83-C) ----
if curl -fsSL -o /dev/null -u "${ADMIN_USER}:${ADMIN_PASS}" \
     "${GITEA_URL}/api/v1/repos/${ADMIN_USER}/crypto-antipatterns-python" 2>/dev/null; then
  echo "[seed] sentinel repo crypto-antipatterns-python already present; skipping seed"
  exit 0
fi
```

`set -e`-safe (the `curl ... 2>/dev/null` lives inside an `if`).
Per-repo `repo_exists` checks remain untouched as defense-in-depth for
partial-seed states.

## Image Pin

`gitea-seed`: `alpine:3.19` → `alpine:3.20`.

- `alpine:3.19` end-of-life is 2025-11-01 (already past at today's date
  2026-05-16).
- `alpine:3.20` matches the two other `alpine:3.20` pins already in the
  compose file (registry-build, container-build sidecars).
- The `gitea` and `gitea-init` services pin to `gitea/gitea:1.21.11` (a
  point release, no moving alias) — owned by Plan 82-01, not touched
  here, but confirmed pinned correctly.

## Live Re-Up Regression

Docker Desktop available on macOS. Ran the source profile via
`docker compose --profile source up -d gitea gitea-init gitea-seed`
(bypassing `./lab.sh up` because Plan 82-01's `lscr.io/linuxserver/openssh-server:9.9_p2-r0-ls180` tag
fails to resolve and blocks the full-lab pull — out-of-scope deviation
noted below).

**First run** (against a persisted `gitea_data` volume from prior work):

```
chaoslab-gitea-seed-1 Exited (0) Less than a second ago
=== Waiting for Gitea to be ready ===
[seed] sentinel repo crypto-antipatterns-python already present; skipping seed
```

**Second run** (`--force-recreate` of gitea-seed):

```
chaoslab-gitea-seed-1 Exited (0) Less than a second ago
=== Waiting for Gitea to be ready ===
[seed] sentinel repo crypto-antipatterns-python already present; skipping seed
```

**409 / error grep on second-run logs:** `NO_409_OR_ERRORS`.

**Repos intact across re-up cycles:**

```json
['crypto-antipatterns-python', 'crypto-antipatterns-go', 'crypto-antipatterns-java']
```

All three expected seed repos present and unchanged after two `up`
cycles.

## Files Modified

| File | Change |
|------|--------|
| `quantum-chaos-enterprise-lab/source/seed.sh` | +13 lines: sentinel short-circuit block |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | 1 line: `alpine:3.19` → `alpine:3.20` (gitea-seed block, line 671 only) |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` | +13 lines: source profile idempotency contract paragraph |

**Commit SHA:** `fdded8e`
**Commit subject:** `fix(82-03): gitea source seed idempotency + image pin (CHAOS-03)`
**Stat:** 3 files changed, 27 insertions(+), 1 deletion(-)

## Deviations from Plan

### Out-of-scope discoveries (not fixed, logged)

**1. [Out-of-scope] `lscr.io/linuxserver/openssh-server:9.9_p2-r0-ls180` tag not found on Docker Hub**

- **Found during:** Task 2 live regression — `./lab.sh up` pulls images for
  every service in the compose file (not just the active profile), and this
  pull failed before any container could start.
- **Root cause:** Introduced by Plan 82-01's broad pin sweep. The
  `linuxserver/openssh-server` image registry uses build-suffixed tags
  (`9.9_p2-r0-ls181`, etc.) that rotate over time; `ls180` is no longer
  published.
- **Workaround for THIS plan's live test:** bypassed `lab.sh` and ran
  `docker compose --profile source up -d gitea gitea-init gitea-seed`
  directly — this still exercises the full idempotency contract because
  Docker Compose only pulls images for the named services. Re-up
  regression succeeded; idempotency verified.
- **Not auto-fixed (scope boundary):** This is in a service block owned by
  82-01, not 82-03. Filed for follow-up — needs the `ssh-alt`/openssh-server
  tag re-pinned to a currently-published `lscr.io/linuxserver/openssh-server`
  build (e.g., `version-9.9_p2-r0-ls181` or the floating `latest` snapshot
  resolved to a digest).
- **Recommendation:** Open a Phase 82 follow-up task (or fold into 82-04
  idempotency test fix-ups) to repin `ssh-alt` to a current
  `linuxserver/openssh-server` tag.

### Auto-fixed issues

None — the plan executed as written, with the only adaptation being the
predicate choice (CONTEXT D-3 suggested org-existence, planner instructed
executor to verify; verification matched the planner's "sentinel-repo
fallback" guidance).

### Authentication gates

None.

## Self-Check: PASSED

- `quantum-chaos-enterprise-lab/source/seed.sh` — FOUND, contains
  `CHAOS-03` marker and `skipping seed` short-circuit, `sh -n` clean
- `quantum-chaos-enterprise-lab/docker-compose.yml` — FOUND, gitea-seed
  pinned to `alpine:3.20`
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — FOUND, source
  section includes idempotency contract paragraph
- Commit `fdded8e` — FOUND in `git log --oneline -1`
- Stat: exactly 3 files in the commit, all owned by this plan
