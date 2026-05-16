# Phase 82: Chaos Lab Fidelity - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Three outstanding DEF-999.83 chaos-lab failures on macOS Docker Desktop are fixed;
every Docker Compose service uses a fully-qualified pinned image tag; the two new
v4.10 profiles (`smime`, `adcs`) integrate into the lab cleanly with idempotent
seeding; and `lab.sh` runtime profile-read continues to pass all parity tests
with the updated compose file.

Wave A for DEF-999.83 fixes + image pinning (CHAOS-01..03, CHAOS-05); Wave B gate
for new-profile integration (CHAOS-04, CHAOS-06 — complete after Phases 79+80
deliver the new profiles).

**v4.10 ship dependency:** Phase 83 (Integration Gate + Cleanup) is blocked until Phase 82 lands.

</domain>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 82 (6 success criteria)
- `.planning/REQUIREMENTS.md` — CHAOS-01 … CHAOS-06 verbatim
- `quantum-chaos-enterprise-lab/docker-compose.yml` — full lab definition
- `quantum-chaos-enterprise-lab/lab.sh` — runtime profile derivation (`_derive_all_profiles()` lines 58-70)
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — per-profile oracle
- `quantum-chaos-enterprise-lab/README.md` — Profile Summary
- `quantum-chaos-enterprise-lab/smime/` — Phase 79 profile (parity reference)
- `quantum-chaos-enterprise-lab/adcs/` — Phase 80 profile (parity reference)
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — DEF-999.83 ledger entries

</canonical_refs>

<decisions>
## Implementation Decisions

### Area 1 — DEF-999.83 fix strategy: migrate to known-good images
- **ldaps profile chown failure (CHAOS-01):** Migrate from `osixia/openldap` to `bitnamilegacy/openldap:2.6.10-debian-12-r4` — parity with smime + adcs profiles. (Already validated in Phase 79.)
- **rabbitmq Erlang cookie reset (CHAOS-02):** Pin `.erlang.cookie` to a deterministic value via `RABBITMQ_ERLANG_COOKIE` env var; remove any bind-mount of the cookie file that triggers reset across `lab.sh down/up` cycles.
- **gitea source profile 409 already-seeded (CHAOS-03):** Add a `git rev-parse HEAD` check (or equivalent existence check) inside the seed script — skip the org/repo create call if it's already present. Idempotent seeding pattern.

### Area 2 — Image pinning depth (CHAOS-05): version tags only
- Pin every image to a specific version tag (e.g., `postgres:16.4-alpine3.20`, `bitnamilegacy/openldap:2.6.10-debian-12-r4`).
- No `:latest`, no implicit-tag references.
- No SHA digests (operational reproducibility for ~6 month rebuild cycles; SHA pinning is over-engineering for the consultant-grade use case).
- New CI gate in `lab.sh`: `docker compose config | grep -E ":(latest|$)" && exit 1` (or equivalent parse check).

### Area 3 — Idempotency test scope (CHAOS-04): all profiles, gated by Docker availability
- `tests/test_chaos_lab_idempotency.py` — pytest module:
  - Discovers all profiles via `docker compose config --profiles`
  - For each profile: runs `./lab.sh up --profile <name>` twice; asserts both exit 0
  - Skip-cleanly if Docker daemon unreachable (uses `pytest.importorskip` or a custom skip-marker based on `docker info` exit code)
  - Covers the existing 13 profiles + smime + adcs = 15 total
- Test marked `slow` so default `pytest` runs fast; CI runs with `-m slow` matrix

### Area 4 — Wave-B integration (CHAOS-04, CHAOS-06)
- `smime` profile: already present from Phase 79 — verify `_derive_all_profiles()` picks it up; verify oracle section in expected_results_v4.md; verify README row exists. Phase 82 confirms parity only.
- `adcs` profile: same as smime — Phase 80 already delivered. Phase 82 verifies parity.
- Update `expected_results_v4.md` to reflect any final tweaks; same for README.md Profile Summary.

### Cross-cutting
- Every compose change must update `quantum-chaos-enterprise-lab/README.md` + `expected_results_v4.md` per CLAUDE.md chaos-lab-maintenance rule.
- `lab.sh` runtime profile read (`_derive_all_profiles()` lines 58-70) — preserve.
- Use explicit file paths in `git add` — NEVER `-A`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quantum-chaos-enterprise-lab/smime/` — Phase 79 reference (bitnamilegacy/openldap + `ldapadd -c` idempotency + exit-68 swallow)
- `quantum-chaos-enterprise-lab/adcs/` — Phase 80 reference (same OpenLDAP image; schema overlay via `LDAP_CUSTOM_SCHEMA_DIR`)
- `quirk/qramm/` staleness test pattern — applicable to a "compose image tag freshness" check if we want to be aggressive about pin currency

### Established Patterns
- `lab.sh` reads compose at runtime (Phase 40) — no script edits when adding profiles
- Per-profile oracle in expected_results_v4.md
- Profile Summary table in chaos-lab README.md
- Seed container = one-shot sidecar with idempotency via tool-specific flags

### Integration Points
- `quantum-chaos-enterprise-lab/docker-compose.yml` — image pin sweep
- `quantum-chaos-enterprise-lab/lab.sh` — add `_validate_pinned_tags()` function + CI gate
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — confirm smime + adcs sections
- `quantum-chaos-enterprise-lab/README.md` — Profile Summary parity
- `quantum-chaos-enterprise-lab/ldaps/` — likely needs deletion or rewrite (osixia migration)
- `quantum-chaos-enterprise-lab/broker/` — rabbitmq cookie fix
- `quantum-chaos-enterprise-lab/source/` — gitea seed-script idempotency
- `tests/test_chaos_lab_idempotency.py` — NEW, all-profile coverage
- `tests/test_chaos_lab_image_pinning.py` — NEW, AST-style compose parse + assert no `:latest`

</code_context>

<specifics>
## Specific Ideas

- ldaps profile migration: rename/replace the existing service block; keep host port 38636 to preserve oracle compatibility
- rabbitmq cookie env: `RABBITMQ_ERLANG_COOKIE=quirk_lab_cookie` (deterministic) — documented as `[lab-only]` non-secret
- gitea seed: `if curl -fsSL http://gitea:3000/api/v1/orgs/quirk-lab >/dev/null 2>&1; then echo "[seed] org already exists, skipping"; exit 0; fi`
- `tests/test_chaos_lab_image_pinning.py` — parses docker-compose.yml via yaml.safe_load, walks services, asserts every `image` field has explicit `:tag` (not `:latest`, not bare image)
- `tests/test_chaos_lab_idempotency.py` skip mechanism: `pytest.skip("Docker not available")` if `subprocess.run(['docker','info'], capture_output=True).returncode != 0`

</specifics>

<deferred>
## Deferred Ideas

- SHA digest pinning — over-engineering; v4.11 if needed
- Renovate/Dependabot for chaos-lab images — separate workflow scope, v4.11
- Profile lifecycle automation (auto-discover new profiles for the idempotency test) — already happens via `docker compose config --profiles`

</deferred>
