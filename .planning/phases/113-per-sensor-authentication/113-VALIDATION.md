---
phase: 113
slug: per-sensor-authentication
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-26
---

# Phase 113 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from 113-RESEARCH.md "Validation Architecture". The planner refines the
> Per-Task Verification Map once task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_sensor_auth_per_sensor.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q -m 'not slow'` |
| **Estimated runtime** | ~5 s quick / ~minutes full |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_sensor_auth_per_sensor.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q -m 'not slow'`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds (quick run)

---

## Per-Task Verification Map

> Requirement → behavior → automated command. Task IDs filled by planner; file
> existence reflects Wave 0 (new gating test file + updated existing push tests).

| Req | Behavior | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|-----|----------|------------|-----------------|-----------|-------------------|-------------|--------|
| AUTH-01 | Valid enrolled sensor token → 200; `request.state.sensor_id` matches enrolled sensor | — | Token resolves to exactly one sensor | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_valid_sensor_token_accepted -x` | ❌ W0 | ⬜ pending |
| AUTH-01 | Token-resolved `sensor_id` is authoritative (not envelope body's sensor_id) | T-113 spoofing | Body cannot override token identity | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_token_identity_is_authoritative -x` | ❌ W0 | ⬜ pending |
| AUTH-02 | `console revoke-sensor <id>` stamps `revoked_at`; next push → 401 | T-113 EoP | Compromised sensor cut off | unit (CLI+API) | `pytest tests/test_sensor_auth_per_sensor.py::test_revoked_token_returns_401 -x` | ❌ W0 | ⬜ pending |
| AUTH-02 | Revoking sensor A has no effect on sensor B | T-113 EoP | Revocation isolated to target | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_revoke_isolates_to_one_sensor -x` | ❌ W0 | ⬜ pending |
| AUTH-03 | Enroll writes correct SHA-256 hash; `revoked_at` NULL on new enrollment | T-113 info-disc | Raw token never persisted | unit (CLI) | `pytest tests/test_console_enroll.py -x` (update existing) | ✅ update | ⬜ pending |
| AUTH-04 | Unknown token (no matching hash) → 401 + IntegrationDelivery audit row | — | Reject + audit | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_unknown_token_returns_401 -x` | ❌ W0 | ⬜ pending |
| AUTH-04 | Revoked token → 401 + IntegrationDelivery audit row | — | Reject + audit | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_revoked_token_returns_401 -x` | ❌ W0 | ⬜ pending |
| AUTH-04 | Body sensor_id != token sensor_id → 403 + IntegrationDelivery audit row | T-113 spoofing | Reject impersonation + audit | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_sensor_id_mismatch_returns_403 -x` | ❌ W0 | ⬜ pending |
| AUTH-04 | All 4 branches write IntegrationDelivery rows | — | Every branch audited | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_all_branches_write_audit_rows -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Observable Signals Proving AUTH-01..04 Hold

- **AUTH-01:** `GET /api/sensor/registry` still returns 200 with operator Bearer token; `POST /api/sensor/push` with operator Bearer token returns 401 (wrong auth type); `POST /api/sensor/push` with valid per-sensor enrollment token returns 200 with `sensor_id` matching the enrolled sensor.
- **AUTH-02:** `sensor_tokens.revoked_at IS NOT NULL` after `quirk console revoke-sensor <id>`; next push from that sensor → 401; pushes from other sensors continue → 200.
- **AUTH-03:** new-enrollment `sensor_tokens` row has `revoked_at IS NULL` and `token_hash == SHA-256(raw).hexdigest()`.
- **AUTH-04:** HTTP 401 unknown / 401 revoked / 403 mismatch / 200 valid; `IntegrationDelivery` rows with `destination='sensor_push'`, `status='failed'`, distinct `error_summary` per case.

---

## Wave 0 Requirements

- [ ] `tests/test_sensor_auth_per_sensor.py` — new file, 8 test functions covering all AUTH-01..04 assertions above
- [ ] Update `tests/test_sensor_ingest.py` — existing push tests must seed a `SensorToken` row + use the enrollment token as the Bearer header after the auth swap (otherwise ALL existing push tests fail post-113)
- [ ] (Reused as-is) `tests/conftest.py` `QUIRK_DB_PATH` isolation, in-memory SQLite, `_app_with_db()` factory

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `lab.sh distributed e2e` stays green after auth cutover | AUTH-01/04 | Requires full multi-container distributed lab; not part of unit suite | Run `quantum-chaos-enterprise-lab/lab.sh distributed e2e`; confirm merged CBOM + score match `expected_results_distributed.md` |
| Operator migration off shared-token model | AUTH-04 | Doc-driven operator procedure; verified by following the updated guide | Follow `docs/operators-guide.md` migration section to re-point a sensor's `console_api_token` to its per-sensor token; confirm push succeeds |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
