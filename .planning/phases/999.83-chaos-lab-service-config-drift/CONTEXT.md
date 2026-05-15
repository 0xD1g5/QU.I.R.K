# Phase 999.83: Chaos Lab Service Config Drift - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Source:** Promoted from BACK-90 with full root-cause analysis already captured. No discuss-phase needed — every bug has confirmed log evidence and a proposed fix path.

<domain>
## Phase Boundary

Fix 4 pre-existing service config drift bugs in `quantum-chaos-enterprise-lab/` that prevent `./lab.sh all` from producing a fully healthy lab. Each bug is in a separate service (`gitea`, `minio-seed`, `vault-seed`, `mysql-ssl-off`) and unrelated to the others. Out of scope: the deferred kerberos host-port remap (tracked separately as BACK-89), the `lab.sh` bash 3.2 / kerberos-skip / vault healthcheck fixes (already landed in commit `9cdd7e3`), and any new chaos lab services or scanner changes.

The phase is purely chaos-lab maintenance — no QUIRK Python code changes are expected except potentially seed scripts. The CLAUDE.md chaos-lab maintenance rule applies: any compose change must update README.md and the relevant `expected_results_*.md` oracle in the same commit.

</domain>

<decisions>
## Implementation Decisions

### Bug 1 — Gitea root-user crash (profile: source)

**Locked**: Image stays at `gitea/gitea:1.21` or later. No downgrade. Fix is achieved by no longer running gitea as root.

**Locked**: Admin user creation moves out of the compose `command:` block and into `source/seed.sh` (which already runs after gitea becomes healthy). The seed script uses the Gitea API or `docker exec` to create the admin user before its existing repo-creation logic.

**Locked**: The custom bash wrapper `bash -c "gitea web && gitea admin user create ..."` in `docker-compose.yml:630-636` is removed entirely. The image's default entrypoint runs gitea as the `git` user automatically.

**Claude's Discretion**: Exact mechanism for admin creation in seed.sh — either (a) `curl` to Gitea's POST /api/v1/admin/users (requires bootstrapping initial admin via env var `GITEA__security__INSTALL_LOCK` + a one-time API call), or (b) `docker exec chaoslab-gitea-1 gitea admin user create ...` from inside the seed container (needs docker socket mounted — risky), or (c) set `GITEA__service__DEFAULT_ADMIN_USERNAME` / `_PASSWORD` env vars on the gitea service so admin is provisioned on first start without any imperative call. Recommend option (c) — cleanest, no socket mount, no API bootstrap dance.

### Bug 2 — Minio-seed KMS auto-encryption (profile: storage-s3)

**Locked**: Fix preserves a server-side-encrypted bucket as a scan target (this is what `expected_results_v4.md` profile `storage-s3` rows depend on). Pure-removal of the encryption setup is allowed ONLY if oracle rows for encrypted-bucket findings can be removed in the same change with documented rationale.

**Claude's Discretion**: Choice between (a) configuring the minio service with `MINIO_KMS_SECRET_KEY=lab-key:<base64-32-bytes>` and `MINIO_KMS_AUTO_ENCRYPTION=on` env vars so the seed's auto-encryption call succeeds, vs (b) restructuring the seed to set bucket-level SSE-S3 encryption without a KMS dependency (`mc encrypt set sse-s3 ...`). Option (a) is closer to a production-realistic config; option (b) is simpler. Pick whichever is cleaner once you read `storage/seed.sh`.

### Bug 3 — Vault-seed rsa-1024 (profile: storage, **deprecated** per README.md row 33)

**Open question for plan**: Is the deprecated `storage` profile worth keeping at all? README.md row 33 marks it `**deprecated** — see database / storage-s3 / vault`. If its findings are fully covered by the v4.3+ replacement profiles, the cleanest fix is to remove the profile entirely (and the `vault` + `vault-seed` services that belong to it — NOT the `vault-30` + `vault-30-seed` which are under the active `vault` profile).

**Claude's Discretion**: If keeping the profile, use `rsa-2048` in `vault/seed.sh` (Vault transit accepts this and QRAMM still flags sub-3072 RSA per the model). If removing, update README.md row 33, `expected_results_v4.md` profile-storage section, and any `config.yaml` references.

**Recommend**: Remove the deprecated `storage` profile entirely. It exists only as a v4.1 leftover; the v4.3 DAR work split its concerns into `database` (postgres-pgcrypto moved there) / `storage-s3` (minio moved there) / `vault` (vault-30 replaced it). Simpler lab = better.

### Bug 4 — MySQL 8.4 `--skip-ssl` removed (profile: database)

**Locked**: Image gets an explicit version pin (no floating `:8.4` tag). Either pin to `mysql:8.0` (preserves `--skip-ssl`) or pin to `mysql:8.4` with `--require-secure-transport=OFF` replacement. Either way, the QUIRK scanner must continue to detect the service as SSL-off / plaintext.

**Recommend**: Pin to `mysql:8.0`. Rationale: (a) the chaos lab's purpose is to expose insecure-by-default behavior, and MySQL 8.0 is what most enterprises still run in 2026; (b) `--skip-ssl` is the documented insecure config consultants would actually find in the wild; (c) pinning to 8.4 with the replacement option means tracking yet another moving target as MySQL evolves.

### Cross-cutting

**Locked**: Image pins are made explicit on all four affected services (no `:latest`, no floating major-version tags). This phase formalizes the pin policy for the lab going forward — capture in README.md.

**Locked**: Per CLAUDE.md, any compose change updates `lab.sh` if profile/port/service membership changes, `README.md` port/service table, and `expected_results_v4.md` oracle. For this phase, no new profiles are added (and possibly one deprecated profile removed), so `lab.sh ALL_PROFILES` derivation is unaffected — but README + oracle updates are mandatory wherever services change.

**Locked**: UAT criterion is the same single command everywhere: `./lab.sh down && ./lab.sh all` on macOS produces zero `Exited (1/2)` and zero `unhealthy` containers after a 60s settle window. The phase isn't done until this passes.

</decisions>

<canonical_references>
## Canonical References

### Phase entries
- `.planning/ROADMAP.md` — Phase 999.83 section (goal, 6 success criteria, provenance)
- `.planning/milestones/v4.8-ROADMAP.md` — BACK-90 row (full bug-by-bug log evidence + proposed fixes)

### Files in scope
- `quantum-chaos-enterprise-lab/docker-compose.yml` — primary target (gitea ~line 609, vault ~line 690, mysql-ssl-off, minio)
- `quantum-chaos-enterprise-lab/source/seed.sh` — gitea admin user creation may move here
- `quantum-chaos-enterprise-lab/storage/seed.sh` — minio + vault legacy seed scripts (rsa-1024 lives in vault/seed.sh)
- `quantum-chaos-enterprise-lab/vault/seed.sh` — referenced by `vault-seed` and `vault-30-seed` services
- `quantum-chaos-enterprise-lab/README.md` — port/service table, deprecated-profile column
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — scanner finding oracle (profile-source, profile-storage-s3, profile-storage, profile-database sections)
- `quantum-chaos-enterprise-lab/lab.sh` — only touched if profile membership changes (e.g., if `storage` profile is removed, the BACK-89 hotfix's profile-derivation logic auto-handles it)
- `quirk/config_template.yaml` — only touched if scanner needs to know about a port/service rename

### Prior context
- Commit `9cdd7e3` (BACK-89 hotfix) — establishes the working `lab.sh all` baseline this phase builds on
- Phase 40 (chaos lab parity) — sets the README/oracle pattern for chaos lab service entries
- Phase 47 (BACK-87 fix) — earlier `.env` / PROFILE_ARGS bug fix in `lab.sh`, useful precedent for lab.sh changes

### CLAUDE.md rules
- "Chaos Lab Maintenance" section — `lab.sh` ALL_PROFILES + README.md + expected_results_*.md update together when compose changes
- "Code Standards" section — PEP 8 (n/a here, no Python), keep diffs minimal, `python -m compileall` after Python changes (n/a unless config_template.yaml needs touching)

</canonical_references>

<specific_ideas>
## Specific Ideas

- The 4 fixes are independent and could parallelize cleanly across 4 plans, but they share UAT (one `./lab.sh down && all` run validates all 4). Suggest: 4 plans for the fixes + 1 plan for the cross-cutting README/oracle/UAT.
- Each fix has a "remove vs config" alternative — the planner needs to make the calls (or punt them as decisions in the plan) using the Claude's Discretion guidance above.

</specific_ideas>

<deferred_ideas>
## Deferred Ideas

- **BACK-89 (kerberos host-port remap)** — explicitly out of scope for this phase. That's a scanner-side change requiring its own planning round.
- **Image-pin enforcement via CI** — adding a lint/grep check that all chaos lab images carry explicit version tags is a good idea but out of scope. File as follow-up backlog if discovered during execution.
- **Migrating deprecated `storage` profile cleanups elsewhere** — if we remove `storage`, any other docs (UAT-SERIES.md, getting-started guides) that mention it may need cleanup. Audit during execution; defer to a follow-up if the scope grows past trivial.

</deferred_ideas>
