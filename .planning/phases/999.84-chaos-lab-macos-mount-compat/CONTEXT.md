# Phase 999.84: Chaos Lab macOS Host-Mount Compat - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Source:** Promoted from BACK-91 with deferred-items analysis already captured. No discuss-phase needed — every bug has confirmed log evidence and 2-3 candidate fixes documented.

<domain>
## Phase Boundary

Fix 3 macOS Docker Desktop bind-mount failures in `quantum-chaos-enterprise-lab/` that prevent `./lab.sh all` from producing a fully clean macOS lab. Each failure is in a separate service (`ldaps`, `rabbitmq-broker`, `gitea-seed`). Two share a root cause class (bind-mount permission semantics on macOS); the third is an idempotency gap surfaced by the same UAT.

Out of scope: a generic audit of all bind-mounts across the lab, BACK-89 (kerberos remap), any QUIRK Python code changes. Linux Docker hosts must not regress.

The phase is chaos-lab maintenance only. CLAUDE.md chaos-lab rule applies: any image swap (e.g. `osixia/openldap` → `bitnami/openldap`) requires README.md + `expected_results_v4.md` updates in the same commit.

</domain>

<decisions>
## Implementation Decisions

### Bug 1 — DEF-999.83-A: ldaps chown on read-only bind-mount

**Confirmed root cause:** `osixia/openldap:1.5.0` startup tries to chown bind-mounted cert files at `/container/service/slapd/assets/certs/...`; macOS Docker Desktop exposes these read-only.

**Locked:** ldaps service must still serve LDAPS on port 636 with the lab's CA-signed cert and remain in the `ldaps` profile. Findings from `expected_results_v4.md` profile-ldaps section must be preserved (or rationally adjusted with documented oracle deltas).

**Claude's Discretion (3 options):**
- (a) **Switch base image** — `bitnami/openldap` doesn't do startup chown; requires re-mapping a few env vars. Most invasive but cleanest long-term.
- (b) **Init container pattern** — keep `osixia/openldap` but add a one-shot init container that copies certs from bind-mount into a named volume; openldap then reads from the named volume.
- (c) **`KEEP_EXISTING_CONFIG=true` env** — `osixia/openldap` honors this to skip the chown step on subsequent restarts; works if the config can be pre-baked. Lightest touch if it works.

**Recommend:** Try (c) first (1-line env change, 5-min test). If it doesn't work because the chown happens before the env is checked, fall back to (a). Skip (b) — adds complexity without clear win over (a).

### Bug 2 — DEF-999.83-B: rabbitmq-broker erlang cookie eacces

**Confirmed root cause:** RabbitMQ requires `/var/lib/rabbitmq/.erlang.cookie` to be 0400 root:root; macOS Docker Desktop bind-mount uid/gid mapping breaks the permission requirement.

**Locked:** rabbitmq-broker must still expose AMQP listeners and remain in the `broker` profile. Oracle finding rows for the broker profile must be preserved.

**Claude's Discretion (3 options):**
- (a) **Set `RABBITMQ_ERLANG_COOKIE` env** — RabbitMQ skips reading the file entirely if the env is set. 1-line fix, no volume changes.
- (b) **Named volume** — replace bind-mount of `/var/lib/rabbitmq` with a named volume; macOS Docker volumes use proper uid/gid.
- (c) **Custom Dockerfile** — bake the cookie into the image at build time with correct perms. Most invasive.

**Recommend:** (a) — cleanest and standard practice for ephemeral broker instances. Generate a random cookie value (or use a fixed lab one like `lab-erlang-cookie-do-not-use-in-prod`).

### Bug 3 — DEF-999.83-C: gitea-seed idempotency

**Confirmed root cause:** `source/seed.sh` uses `curl -sf POST /api/v1/user/repos` which returns 409 (and curl exit 22) when the repo already exists; `set -e` then kills the script. Only visible when `gitea_data` named volume persists across runs.

**Locked:** seed.sh must remain a one-shot script that creates the 3 crypto-antipattern repos on first run AND completes cleanly (Exit 0) on subsequent runs without disturbing existing repo content.

**Claude's Discretion (2 options):**
- (a) **Wrap in `|| true`** — append `|| true` to each `curl -sf POST` call. Simplest. Risk: legitimate errors (network down, auth failure) get silently swallowed too.
- (b) **Existence check** — `GET /api/v1/repos/{user}/{repo}` first; only POST if 404. Per-file `put_file` does same with `GET /api/v1/repos/{user}/{repo}/contents/{path}`. More code but preserves real-error visibility.

**Recommend:** (b) for the repo creation (cheap, makes intent explicit). For the per-file `put_file` loop, (a) is acceptable — files use deterministic content + commit messages, and a 409 truly means "already created with same content" in this seed context. Decision worth capturing in plan.

### Cross-cutting

**Locked:** No regression on Linux Docker hosts. Plans must specify how Linux behavior is preserved (env vars / named volumes / existence checks all work cross-platform, so this should be implicit, but call it out).

**Locked:** Per CLAUDE.md, any image swap (especially the ldaps base image if option (a) is chosen for Bug 1) updates `README.md` profile table and `expected_results_v4.md` in the same commit. `lab.sh` only touched if profile membership changes (none expected).

**Locked:** UAT runs on macOS Docker Desktop, the platform where the bugs exist. Don't fake-verify on Linux. The single UAT command is the same as 999.83: `./lab.sh down && ./lab.sh all && sleep 60 && docker compose -p chaoslab ps -a` — but now success means zero `Restarting / Exited (≠0) / unhealthy`, including ldaps + rabbitmq-broker + gitea-seed re-runs.

**Locked:** The gitea_data volume must NOT be wiped between the first `./lab.sh all` and the re-run UAT — that's precisely the regression scenario being verified.

</decisions>

<canonical_references>
## Canonical References

### Phase entries
- `.planning/ROADMAP.md` — Phase 999.84 section
- `.planning/milestones/v4.8-ROADMAP.md` — BACK-91 row (full per-bug detail)
- `.planning/phases/999.83-chaos-lab-service-config-drift/deferred-items.md` — original DEF-A/B/C captures with exact log evidence

### Files in scope
- `quantum-chaos-enterprise-lab/docker-compose.yml` — ldaps service (~line 793), rabbitmq-broker (search `rabbitmq-broker:`), gitea + gitea-init (already touched in Phase 999.83 Plan 01)
- `quantum-chaos-enterprise-lab/source/seed.sh` — modified in Phase 999.83 Plan 01 (admin user creation moved here); idempotency fix lives here
- `quantum-chaos-enterprise-lab/README.md` — profile/service/port table (row 34: ldaps, row 42: broker)
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — profile-ldaps + profile-broker + profile-source sections (oracle deltas if needed)
- Possibly: named volume definitions at the bottom of docker-compose.yml (for Bug 2 option b, if chosen)

### Prior context
- Phase 999.83 commits — establish current baseline:
  - `0fd8883` (gitea), `ab6d56e` (minio), `48c11af` (storage removed), `68b0a60` (mysql:8.0), `fc9c714` (docs), `e40374b` (UAT-SERIES), `900ed0b` (phase wrap)
- Phase 41-06 (`357344a`) — `lab.sh down` sweeps profile-tagged services; this UAT relies on that working

### CLAUDE.md rules
- Chaos lab maintenance — image/profile/port changes touch lab.sh + README + oracle together
- Code standards — minimal diffs, no unnecessary refactors

</canonical_references>

<specific_ideas>
## Specific Ideas

- The 3 bugs are independent and parallel-eligible logically, but they all touch `docker-compose.yml` (and Bug 3 touches `source/seed.sh`). Pattern from Phase 999.83 worked well: serialize plans within wave to avoid file conflicts, one atomic commit per plan, plus a wrap plan for docs/UAT.
- Suggest: 4 plans — Plan 01 (ldaps), Plan 02 (rabbitmq-broker), Plan 03 (gitea-seed idempotency), Plan 04 (cross-cutting README/oracle/UAT/UAT-SERIES/Obsidian).
- Bug 1 has 3 options with cascading fallback — capture the actual decision made in the plan (with rationale) before executing.

</specific_ideas>

<deferred_ideas>
## Deferred Ideas

- **Generic audit of all bind-mounts for macOS compat** — out of scope. Focus on these 3 specific services. Future backlog item if new failures surface.
- **Migration to Docker Compose `develop` configs or platform-specific overrides** — interesting but unrelated to BACK-91 scope.

</deferred_ideas>
