---
phase: 36
slug: dashboard-motion-tab
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python). **No frontend test framework** — defer to v4.5 polish per CONTEXT.md D-07. |
| **Config file** | `pyproject.toml` (pytest section) + `tests/conftest.py` |
| **Quick run command** | `pytest tests/test_dashboard_api.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~10s quick / ~90s full |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_dashboard_api.py -x`
- **After every plan wave:** Run `pytest tests/ -x` plus `cd src/dashboard && tsc -b`
- **Before `/gsd-verify-work`:** Full suite green + `tsc -b` green + manual UAT-36-01..05 sign-off in `docs/UAT-SERIES.md`
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 1 | DASH-05 | — | `motion_findings` field present on `/api/scan/latest` response | unit | `pytest tests/test_dashboard_api.py::test_motion_findings_endpoint -x` | ❌ W0 | ⬜ pending |
| 36-01-02 | 01 | 1 | DASH-04 | — | `subscores.data_in_motion` reaches the API response (fixes Pitfall 1) | unit | `pytest tests/test_dashboard_api.py::test_data_in_motion_subscore -x` | ❌ W0 | ⬜ pending |
| 36-01-03 | 01 | 1 | DASH-05 | — | `_derive_motion_findings` emits HIGH for `KAFKA-PLAIN` | unit | `pytest tests/test_dashboard_api.py::test_derive_motion_findings_plaintext -x` | ❌ W0 | ⬜ pending |
| 36-01-04 | 01 | 1 | DASH-05 | — | `starttls_warning=true` only on port-25 SMTP-STARTTLS | unit | `pytest tests/test_dashboard_api.py::test_derive_motion_findings_starttls -x` | ❌ W0 | ⬜ pending |
| 36-01-05 | 01 | 1 | DASH-05 | — | `AMQPS/Azure-ServiceBus` slash preserved verbatim | unit | `pytest tests/test_dashboard_api.py::test_derive_motion_findings_azure -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dashboard_api.py` — extend with 5 new test cases above. Reuse `dashboard_client` fixture from `tests/conftest.py:75`.
- [ ] `tests/conftest.py` — add `seed_motion_endpoints(db)` helper if needed to seed `CryptoEndpoint` rows for email/broker protocols.
- [ ] `docs/UAT-SERIES.md` — add UAT-36-01..05 cases (per D-11). New series block dated 2026-04-29 or later.
- [ ] No Vitest install — explicitly out of scope per D-07.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/motion` route loads in production build | DASH-01 | No frontend test framework | `cd src/dashboard && npm run build && quirk serve`, open `http://localhost:8000/motion`, confirm no console errors and both sections render |
| Email per-port table + STARTTLS badge on port 25 | DASH-02 | DOM-level visual verification | Run `docker compose --profile email up` from `labs/email/`, scan `localhost`, open `/motion`, confirm Email section shows port 25 with amber `⚠ STARTTLS` badge |
| Broker grouped sections + plaintext red badge | DASH-03 | DOM-level visual verification | Run `docker compose --profile broker up` from `labs/broker/`, scan `localhost`, open `/motion`, confirm Kafka/AMQP/Redis subsections render and plaintext rows show orange `☠ PLAINTEXT` badge |
| Executive summary shows 6 ScoreGauges | DASH-04 | Visual layout check | Open `/executive`, count ScoreGauges = 6, confirm "Data in Motion" appears last in the flex-wrap row |
| Empty-state cards render when no email/broker findings | DASH-01 (UX gap D-05) | Negative-path visual check | Scan a host with neither email nor broker endpoints, open `/motion`, confirm both sections render their muted empty-state copy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
