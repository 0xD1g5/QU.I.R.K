---
phase: 109
slug: console-ingestion-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-25
---

# Phase 109 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (FastAPI `TestClient`) |
| **Config file** | pyproject.toml / pytest.ini (existing) |
| **Quick run command** | `pytest tests/ -k "sensor_push or console_enroll or ingest" -q` |
| **Full suite command** | `pytest tests/ -q && python -m compileall quirk run_scan.py` |
| **Estimated runtime** | ~60 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Filled by the planner per task. Every requirement maps to at least one automated test.

| Requirement | Secure Behavior | Test Type | Automated Command | Status |
|-------------|-----------------|-----------|-------------------|--------|
| CONSOLE-01 | `POST /api/sensor/push` exists, 200 on valid authenticated push | route test | `pytest tests/ -k "sensor_push and valid"` | ⬜ pending |
| CONSOLE-02 | Unauthenticated push → 401 (anti-bypass gating test) | auth gate | `pytest tests/ -k "sensor_push and unauth"` | ⬜ pending |
| CONSOLE-03 | 413 oversize, 409 replay payload_id, 422 outside ±15min with console_utc | route test | `pytest tests/ -k "sensor_push and (size or replay or skew)"` | ⬜ pending |
| CONSOLE-04 | IntegrationDelivery row per attempt (success + all failures), safe_str scrubbed; AST gate covers module | unit + AST gate | `pytest tests/ -k "audit or safe_str_gate"` | ⬜ pending |
| CONSOLE-05 | extra='ignore' + schema_version graceful (no 422/500 on version skew) | unit | `pytest tests/ -k "version_skew or extra_ignore"` | ⬜ pending |
| (provisioning) | `quirk console enroll` writes sensors + sensor_tokens rows, emits bearer token | CLI test | `pytest tests/ -k "console_enroll"` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Reuse the existing `dashboard_client` / TestClient + auth fixtures (no new framework)
- [ ] Reuse the `QUIRK_DB_PATH` conftest fixture for DB-touching ingest/enroll tests
- [ ] No new pip dependencies (all primitives already present)

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live end-to-end enroll→push against `quirk serve` | CONSOLE-01/02 | Real running server + real sensor push | Deferred to UAT/chaos-lab (Phase 112) |

*All other phase behaviors have automated verification via TestClient.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
