---
phase: 101
slug: notification-fan-out-security-foundation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-24
---

# Phase 101 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/conftest.py (QUIRK_DB_PATH fixture) |
| **Quick run command** | `python -m pytest tests/test_notify*.py tests/test_integration_deliveries_schema.py tests/test_install_all_includes_notify.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~60 seconds (targeted), full suite longer |

---

## Sampling Rate

- **After every task commit:** Run targeted quick command for the touched module
- **After every plan wave:** Run `python -m pytest tests/test_notify*.py -q` for the phase's test files
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-1 | 01 | 1 | ISEC-02 | T-101-01 | safe_str scrubs Slack tokens / webhook URLs / SMTP conn strings; no over-redaction | unit | `python -m pytest tests/test_notify_safe_str_secrets.py -x -q` | ❌ W0 | ⬜ pending |
| 01-2 | 01 | 1 | NOTIFY-07 | T-101-01 | integration_deliveries table created with 7-col schema | unit | `python -m pytest tests/test_integration_deliveries_schema.py -x -q` | ❌ W0 | ⬜ pending |
| 01-3 | 01 | 1 | (packaging) | T-101-02, T-101-SC | [notify] joins [all]; slack-sdk resolves; no httpx conflict | unit | `python -m pytest tests/test_install_all_includes_notify.py -x -q` | ❌ W0 | ⬜ pending |
| 02-1 | 02 | 1 | NOTIFY-06 | T-101-04, T-101-05 | env-var-name secrets; QUIRK_CONFIG_PATH only; binary file → None | unit | `python -m pytest tests/test_notify_config.py -x -q` | ❌ W0 | ⬜ pending |
| 02-2 | 02 | 1 | ISEC-03 | T-101-03 | to_integration_payload whitelist excludes host/port/protocol/samples | unit | `python -m pytest tests/test_notify_payload_whitelist.py -x -q` | ❌ W0 | ⬜ pending |
| 03-1 | 03 | 2 | NOTIFY-03, ISEC-01, ISEC-04 | T-101-06, T-101-07 | Slack lazy-import skip; delivery-time SSRF; one summary message | unit | `python -m pytest tests/test_notify_slack.py -x -q` | ❌ W0 | ⬜ pending |
| 03-2 | 03 | 2 | NOTIFY-04, ISEC-01 | T-101-06, T-101-09 | smtplib timeout; multi-recipient; SMTP-host SSRF | unit | `python -m pytest tests/test_notify_email.py -x -q` | ❌ W0 | ⬜ pending |
| 03-3 | 03 | 2 | NOTIFY-05, ISEC-01 | T-101-06, T-101-08, T-101-09 | urllib timeout; HMAC toggle; SSRF; body omits topology | unit | `python -m pytest tests/test_notify_webhook.py tests/test_notify_ssrf.py -x -q` | ❌ W0 | ⬜ pending |
| 04-1 | 04 | 3 | NOTIFY-01, NOTIFY-02, NOTIFY-07, ISEC-02 | T-101-11, T-101-12, T-101-13 | trigger discipline; fan-out isolation; safe_str audit rows | unit | `python -m pytest tests/test_notify_dispatcher.py -x -q` | ❌ W0 | ⬜ pending |
| 04-2 | 04 | 3 | NOTIFY-01, NOTIFY-07 | T-101-10 | scheduler hook after commit; dispatch error never corrupts scan record | unit | `python -m pytest tests/test_notify_dispatcher.py -x -q` | ❌ W0 | ⬜ pending |
| 04-3 | 04 | 3 | (docs) | — | configuration + UAT docs document notification surface | source | `grep -c 'QUIRK_CONFIG_PATH' docs/configuration.md` | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All notify test files are new — Wave 0 (first task of each plan, TDD RED) creates them:

- [ ] `tests/test_notify_safe_str_secrets.py` — ISEC-02 secret-pattern scrubbing (Plan 01)
- [ ] `tests/test_integration_deliveries_schema.py` — table/column schema (Plan 01)
- [ ] `tests/test_install_all_includes_notify.py` — [all] inclusion CI guard (Plan 01)
- [ ] `tests/test_notify_config.py` — NOTIFY-06 config loader (Plan 02)
- [ ] `tests/test_notify_payload_whitelist.py` — ISEC-03 whitelist (Plan 02)
- [ ] `tests/test_notify_slack.py` — NOTIFY-03/ISEC-04 lazy-import + SSRF (Plan 03)
- [ ] `tests/test_notify_email.py` — NOTIFY-04 smtplib timeout + SSRF (Plan 03)
- [ ] `tests/test_notify_webhook.py` — NOTIFY-05 HMAC + SSRF (Plan 03)
- [ ] `tests/test_notify_ssrf.py` — ISEC-01 delivery-time SSRF across all channels (Plan 03)
- [ ] `tests/test_notify_dispatcher.py` — NOTIFY-01/02/07 trigger + isolation (Plan 04)

Existing infra: `conftest.py` provides the QUIRK_DB_PATH isolation fixture; use `tmp_path` + `init_db` per `test_scheduler_cmd.py`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Slack message appears in real channel | NOTIFY-03 | Requires a real incoming-webhook URL | Configure QUIRK_SLACK_WEBHOOK + QUIRK_CONFIG_PATH, run a scheduled scan that triggers drift, confirm message in channel |
| Live SMTP email delivery | NOTIFY-04 | Requires a real SMTP server + credentials | Configure SMTP env vars, trigger drift, confirm email received |
| Live generic webhook receipt + HMAC verification | NOTIFY-05 | Requires a real receiving endpoint | Configure QUIRK_WEBHOOK_URL + HMAC key, trigger drift, confirm POST + valid X-QUIRK-Signature |

*Network sends are unit-tested with mocked transports; live delivery is human-UAT.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (planning)
