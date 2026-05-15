# Phase 999.83 Deferred Items

Discovered during Plan 05 global UAT (`./lab.sh down && ./lab.sh all`, 60s settle, 2026-05-15).
These pre-existing macOS-host issues are unrelated to the four BACK-90 fixes and are out of
scope for this phase per the Scope Boundary rule.

## DEF-999.83-A — `chaoslab-ldaps-1` Restarting (1) on macOS
- **Symptom:** Container restart loop with `chown: ... Read-only file system` errors on `/container/service/slapd/assets/certs/...` paths.
- **Root cause:** `osixia/openldap:1.5.0` startup tries to chown bind-mounted cert files; Docker Desktop on macOS exposes them read-only.
- **Touched by Phase 999.83?** No. ldaps profile last modified in Phase 04-05 (2026-04). Not in BACK-90 scope.
- **Suggested follow-up:** New backlog ticket "ldaps macOS host-mount compat" — either switch the openldap image to one that doesn't chown bind-mounts, or copy certs into a named volume at start.

## DEF-999.83-B — `chaoslab-rabbitmq-broker-1` Exit on macOS
- **Symptom:** `Error when reading /var/lib/rabbitmq/.erlang.cookie: eacces` then kernel-pid crash.
- **Root cause:** RabbitMQ Erlang cookie file permission requirements clash with macOS Docker Desktop bind-mount uid/gid mapping.
- **Touched by Phase 999.83?** No. broker profile last modified in Phase 33-07 (2026-03). Not in BACK-90 scope.
- **Suggested follow-up:** New backlog ticket "rabbitmq-broker macOS erlang-cookie compat" — either set `RABBITMQ_ERLANG_COOKIE` via env (skipping the file), or use a named volume instead of bind-mount for `/var/lib/rabbitmq`.

## DEF-999.83-C — `chaoslab-gitea-seed-1` not idempotent on re-run
- **Symptom:** Exit 22 from `curl -sf` when `POST /api/v1/user/repos` returns 409 (repo already exists). `set -e` then kills the script.
- **Root cause:** `source/seed.sh` doesn't check if repos exist before creating them. Plan 01's verification wiped `chaoslab_gitea_data` first, so the issue was invisible.
- **Touched by Phase 999.83?** Plan 01 modified `source/seed.sh` for the labadmin rename, but did not introduce the idempotency gap (it was pre-existing).
- **Suggested follow-up:** Wrap each `POST /api/v1/user/repos` in `curl -sf ... || true` (or check existence first via `GET /api/v1/repos/{user}/{repo}`); same for the per-file `put_file` calls. Verified that repos and files DO exist after the first run — the seed effectively succeeded, just exits with 22 on re-runs.
