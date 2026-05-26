# Requirements: QU.I.R.K. v5.5 — Distributed Hardening + Stabilization

**Defined:** 2026-05-26
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable and quantum-readiness score that a consultant can hand to a client in under two hours — now hardened for production distributed deployment across a segmented enterprise network.

**Milestone goal:** Harden the v5.4 distributed scanner into production shape — per-sensor authentication, automatic merge, and a clean re-runnable lab — while sweeping the defects the live distributed E2E surfaced. Honors the 2:1 stabilization breather that v5.4 deliberately deferred.

**Locked constraints (apply to every requirement below):**

- **Single-tenant only.** No `tenant_id`, no per-tenant isolation. SaaS multi-tenancy stays PARKED (unchanged from v5.4).
- **No new heavy infra.** No Celery, Redis, RabbitMQ, MQTT, Postgres. SQLite stays the store; FastAPI stays the server.
- **Additive schema only.** New columns/tables must be nullable/independent; existing single-host and v5.4 distributed scans keep working unchanged.
- **Reuse v5.3/v5.4 primitives.** `require_auth`, the `sensor_tokens` SHA-256 hash table, the `IntegrationDelivery` delivery-audit table, `safe_str()` scrubbing, and the SSRF URL allowlist are reused, not reinvented.
- **OS-agnostic sensor↔console contract.** Unchanged from v5.4; the Windows packaging spike must not bake POSIX assumptions into the wire contract.
- **Public-repo cutover is OUT of scope.** Repo stays private; `windows-sensor-smoke` stays non-blocking CI. Enforcing it as a required status check is deferred to the public-repo launch decision (ops decision 2026-05-26).
- **Full Windows frozen-binary build is OUT of scope.** WINPKG is a spike/sizing phase only; the full build splits to v5.6 if the spike finds it deep.

---

## v1 Requirements (v5.5)

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Per-Sensor Authentication (AUTH) — *replaces the v5.4 shared-token model (TD-1)*

- [ ] **AUTH-01**: Each sensor authenticates to the console with its own per-sensor token (not a single shared console token); the console identifies which sensor a push came from based on the presented token.
- [ ] **AUTH-02**: A console operator can revoke an individual sensor's token (e.g. `quirk console revoke-sensor <id>`) so a compromised or decommissioned sensor is immediately rejected at ingestion, with no effect on any other enrolled sensor's ability to push.
- [ ] **AUTH-03**: Enrollment issues a per-sensor token bound to the sensor UUID; the raw token is never persisted (SHA-256 hash only, reusing the existing `sensor_tokens` table and `token_cmd.py` hashing pattern).
- [ ] **AUTH-04**: A revoked or unknown per-sensor token returns 401 at `POST /api/sensor/push` (gating test); migration off the v5.4 shared-token model is backward-compatible and documented in the operators guide.

### Automatic Merge (AUTOMERGE) — *106 D-06 carry-forward*

- [ ] **AUTOMERGE-01**: The console automatically merges pushed results into one CBOM + one quantum-readiness score once all enrolled sensors have checked in (poll-on-full-check-in or equivalent trigger), without requiring a manual `quirk sensor merge`.
- [ ] **AUTOMERGE-02**: Auto-merge is configurable — it can be enabled/disabled and its trigger condition selected (e.g. all-sensors-in vs cadence-window) — and a merge failure never blocks, fails, or rolls back an in-flight sensor push.
- [ ] **AUTOMERGE-03**: The manual `quirk sensor merge` command still works and coexists with auto-merge with no regression to v5.4 merge behavior (Option-A union scoring, `coverage_warning`, sensor-local `scanned_at` preserved).

### Live-UAT Stabilization (STAB) — *999.86 / 999.87 / 999.88 / 999.89*

- [ ] **STAB-01**: `quirk console enroll` is idempotent — re-running it for an already-provisioned console/sensor succeeds (no error, no duplicate rows) so `lab.sh distributed e2e` is re-runnable without `docker compose down -v`. (999.86)
- [ ] **STAB-02**: `cmvp_cache.json` ships inside the installed package (declared as package data), eliminating the repeated "CMVP cache unavailable" warning on merge in an installed (non-source-tree) environment. (999.87)
- [ ] **STAB-03**: `quirk scheduler` no longer passes unsupported `--output` / `--target` arguments to `run_scan`; scheduled scans complete with exit code 0, guarded by a regression test in the same class as the fixed `sensor`/`_run_local_scan` bug. (999.88)
- [ ] **STAB-04**: The stray `scanned_at=None` / port-0 `email_scanner` / `broker_scanner` rows that appear in the console DB after the distributed e2e are root-caused and eliminated, so merged output contains no phantom endpoints. (999.89)

### Distributed Lab Testability (LAB) — *999.85*

- [ ] **LAB-01**: The distributed chaos lab includes a weak-crypto target in a non-default segment so the Phase 111 per-segment score/filter can be exercised end-to-end (previously blocked Test 7); `lab.sh distributed`, the `expected_results_*.md` oracle, and the chaos-lab README are all updated in the same change per the CLAUDE.md no-drift rule.

### Windows Packaging Spike (WINPKG) — *106 D-05, spike-only*

- [ ] **WINPKG-01**: A spike phase produces a written feasibility and sizing assessment for packaging the sensor as a PyInstaller frozen EXE hosted as a Windows Scheduled Task (or Service), validated against the existing `windows-latest` CI runner, ending in a go/no-go recommendation and effort estimate for the full build in v5.6. No production packaging artifact ships in v5.5.

---

## Future Requirements (deferred)

- **Full Windows frozen-binary packaging build** — the production PyInstaller EXE + Windows Scheduled Task/Service host + installer, gated on the WINPKG-01 spike outcome. → v5.6 fast-follow if the spike finds it deep.
- **Public-repo cutover + required-status-check enforcement** — make the repo public, enable branch protection, enforce `windows-sensor-smoke` as a required check, re-run UAT-112-03 item 3. → deferred to the public-repo launch decision.
- **19 v5.3 live-delivery human-UAT items** (Slack/email/webhook/syslog/Jira/ServiceNow against real servers) — parked; no test environment.

## Out of Scope (v5.5)

- **SaaS multi-tenancy / per-tenant isolation** — gated on a business-model signal that does not yet exist. Different problem, larger lift.
- **New scanner families or detection coverage** — v5.5 is hardening/stabilization, not capability breadth.
- **New heavy infrastructure** (Celery/Redis/RabbitMQ/MQTT/Postgres) — forbidden by the locked constraints.

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | _TBD (roadmap)_ | pending |
| AUTH-02 | _TBD (roadmap)_ | pending |
| AUTH-03 | _TBD (roadmap)_ | pending |
| AUTH-04 | _TBD (roadmap)_ | pending |
| AUTOMERGE-01 | _TBD (roadmap)_ | pending |
| AUTOMERGE-02 | _TBD (roadmap)_ | pending |
| AUTOMERGE-03 | _TBD (roadmap)_ | pending |
| STAB-01 | _TBD (roadmap)_ | pending |
| STAB-02 | _TBD (roadmap)_ | pending |
| STAB-03 | _TBD (roadmap)_ | pending |
| STAB-04 | _TBD (roadmap)_ | pending |
| LAB-01 | _TBD (roadmap)_ | pending |
| WINPKG-01 | _TBD (roadmap)_ | pending |

*Traceability filled by the roadmapper — every requirement maps to exactly one phase.*
