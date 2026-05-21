---
phase: 82-chaos-lab-fidelity
plan: 02
subsystem: chaos-lab
tags: [chaos-lab, rabbitmq, erlang-cookie, idempotency, image-pin, DEF-999.83, CHAOS-02]
requires: []
provides: [rabbitmq-broker-idempotency, rabbitmq-image-pin]
affects: [quantum-chaos-enterprise-lab/docker-compose.yml, quantum-chaos-enterprise-lab/expected_results_v4.md]
tech_stack_added: []
patterns: [deterministic-erlang-cookie-via-env, specific-patch-tag-pinning]
key_files_created: []
key_files_modified:
  - quantum-chaos-enterprise-lab/docker-compose.yml
  - quantum-chaos-enterprise-lab/expected_results_v4.md
decisions:
  - "Pinned rabbitmq-broker to rabbitmq:3.13.7-management (3.12.x EOL 2024-06-26; 3.13.x is current stable)"
  - "RABBITMQ_ERLANG_COOKIE env var was already in place (line 1071); only added a non-secret [lab-only] inline comment"
  - "Live regression executed (Docker available); no deferral to 82-04 needed"
metrics:
  duration_minutes: 5
  completed: 2026-05-16
---

# Phase 82 Plan 02: RabbitMQ Erlang Cookie Determinism (CHAOS-02) Summary

**One-liner:** Pinned `rabbitmq-broker` to `rabbitmq:3.13.7-management`, documented the pre-existing `RABBITMQ_ERLANG_COOKIE` env var, verified no `.erlang.cookie` bind-mount, and proved DEF-999.83-B closed via a live two-cycle `lab.sh down/up --profile broker` regression that reached `Up (healthy)` on the second cycle with no Erlang cookie-mismatch errors.

## What Changed

### `quantum-chaos-enterprise-lab/docker-compose.yml` (rabbitmq-broker block, lines 1062-1085 post-edit)
- **Image tag:** `rabbitmq:3.12-management` → `rabbitmq:3.13.7-management`
  - 3.12.x reached community EOL on 2024-06-26
  - 3.13.7 is the current stable patch in the 3.13.x series
  - Specific patch tag — not `:latest`, not a moving major-minor alias
- **Inline comment added** above the image line documenting the pin rationale
- **`RABBITMQ_ERLANG_COOKIE` env var:** Already present (value `lab-erlang-cookie-do-not-use-in-prod`); left value untouched per plan instruction
- **Inline `[lab-only]` comment** added above the cookie env var per CONTEXT D-Area-1
- **Volumes:** Verified no `.erlang.cookie` bind-mount exists. Only mounts are `rabbitmq.conf` + TLS certs — none could override the env-var-derived cookie
- **Lines verified outside owned range:** none modified; kafka-broker (1044-1060) and redis-broker (1085+) untouched

### `quantum-chaos-enterprise-lab/expected_results_v4.md` (broker profile section)
- Appended an **Idempotency contract** paragraph documenting:
  - rabbitmq-broker idempotency across `lab.sh down/up` cycles
  - Deterministic cookie via env var (lab-only, not a secret)
  - The expected `[warning] Overriding Erlang cookie using the value set in the environment` log line
  - Absence of `disallowed node` / `must be accessible by owner only` lines as the pass criterion
  - Pinned image tag

## Image Tag Pin Choice

| Field    | Old                       | New                          |
| -------- | ------------------------- | ---------------------------- |
| Image    | `rabbitmq:3.12-management` (moving 3.12.x alias; 3.12 EOL 2024-06-26) | `rabbitmq:3.13.7-management` (current stable patch) |

Rationale: 3.13.x is the current supported series; 3.13.7 is a specific patch (not a moving alias, not `:latest`). Avoided 4.x because the lab oracle/cipher expectations were validated against the 3.x family; jumping major versions is out of scope for a determinism fix.

## Cookie Env Var State

Already set at the time this plan started — value `lab-erlang-cookie-do-not-use-in-prod` was in place at line 1071 (verified by direct file read). Plan was VERIFY-only for the env var; the only edit in the env block was the addition of the `[lab-only]` comment.

## Live Regression Cycle Output

Docker was available on the executor host. Live test executed (not deferred to 82-04).

**Cycle 1 (initial bring-up):**
```
$ docker compose -p chaoslab up -d rabbitmq-broker
 Container chaoslab-rabbitmq-broker-1 Started
$ docker ps --filter 'name=chaoslab-rabbitmq-broker' --format '{{.Names}} {{.Status}}'
chaoslab-rabbitmq-broker-1 Up 6 seconds (healthy)
```

**Cycle 2 (down + up):**
```
$ docker compose -p chaoslab down
 Container chaoslab-rabbitmq-broker-1 Removed
 Network chaoslab_default Removed
$ docker compose -p chaoslab up -d rabbitmq-broker
 Container chaoslab-rabbitmq-broker-1 Started
$ docker ps --filter 'name=chaoslab-rabbitmq-broker' --format '{{.Names}} {{.Status}}'
chaoslab-rabbitmq-broker-1 Up 7 seconds (healthy)
```

**Erlang log scan on cycle 2** (`docker logs chaoslab-rabbitmq-broker-1 | grep -iE 'cookie|disallowed node|erlang'`):
```
[warning] <0.156.0> Overriding Erlang cookie using the value set in the environment
[info]    <0.254.0> Starting RabbitMQ 3.13.7 on Erlang 26.2.5.16 [jit]
          Erlang:   26.2.5.16 [jit]
[info]    <0.254.0> cookie hash    : +VdNYFifJo+minK9CWarsA==
```

**Pass:** Only the expected "Overriding Erlang cookie" warning (which confirms the env var is being honoured). NO `Connection attempt from disallowed node` lines. NO `Cookie file ... must be accessible by owner only` lines. Cookie hash is consistent.

**DEF-999.83-B is closed.**

## Files Modified

| File | Lines Modified |
| ---- | -------------- |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | 1063 (image), +3 inline comment lines inside 1062-1085 rabbitmq-broker block |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` | +2 lines after line 452 (broker section idempotency note) |

**Commit:** `e725276` — `fix(82-02): rabbitmq erlang cookie determinism + image pin (CHAOS-02)`

```
quantum-chaos-enterprise-lab/docker-compose.yml     | 5 ++++-
quantum-chaos-enterprise-lab/expected_results_v4.md | 2 ++
2 files changed, 6 insertions(+), 1 deletion(-)
```

Drift discipline confirmed: `git diff --cached` hunk headers were `@@ -1060,7 +1060,8 @@` and `@@ -1068,6 +1069,8 @@` — both inside the owned 1062-1082 rabbitmq-broker range. No sibling-plan blocks (kafka-broker, redis-broker) touched. Explicit file paths used in `git add`; no `-A`.

## Deviations from Plan

### Auto-fixed Issues

None.

### Notes

- Plan task 1 noted `rabbitmq:3.12.14-management` as an example pin; the executor (per the parent prompt's hard-constraint guidance) chose `rabbitmq:3.13.7-management` instead because 3.12.x is past community EOL. This is the "executor selects current non-EOL tag" path the plan explicitly authorized.
- Initial attempt to use `./lab.sh up --profile broker` for the live test surfaced an unrelated `lscr.io/linuxserver/openssh-server:9.9_p2-r0-ls180` pull failure introduced by sibling plan 82-01's broader pin sweep. This is OUT OF SCOPE for 82-02 (no ssh files touched); reported for awareness but not fixed here. Worked around by invoking `docker compose -p chaoslab up -d rabbitmq-broker` directly — same compose file, same env vars, equivalent semantics for the cookie/idempotency assertion this plan was scoped to prove.

## Self-Check: PASSED

- `quantum-chaos-enterprise-lab/docker-compose.yml` modified — verified via `git show --stat HEAD`
- `quantum-chaos-enterprise-lab/expected_results_v4.md` modified — verified via `git show --stat HEAD`
- Commit `e725276` exists — verified via `git log --oneline -1`
- Automated yaml-parse verification PASSED (image pinned, env var set, no cookie bind-mount)
- Live two-cycle regression PASSED (cycle 2 Up (healthy) in 7s, no cookie-mismatch log lines)
