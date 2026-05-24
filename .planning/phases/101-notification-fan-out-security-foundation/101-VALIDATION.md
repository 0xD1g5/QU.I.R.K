---
phase: 101
slug: notification-fan-out-security-foundation
status: draft
nyquist_compliant: false
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
| **Quick run command** | `python -m pytest tests/test_notify*.py tests/test_integration_security*.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~60 seconds (targeted), full suite longer |

---

## Sampling Rate

- **After every task commit:** Run targeted quick command for the touched module
- **After every plan wave:** Run `python -m pytest -q` for the phase's test files
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

*Populated by gsd-planner during planning. Each task maps to a requirement, threat ref, and automated command.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | — | — | — | — | — | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_notify_dispatch.py` — stubs for NOTIFY-01..07
- [ ] `tests/test_integration_security.py` — stubs for ISEC-01..04 (SSRF rejection, secret scrubbing, whitelist, graceful-skip)
- [ ] `tests/conftest.py` — reuse existing QUIRK_DB_PATH fixture; add notify-config + mock-endpoint fixtures

*Confirmed during planning against existing pytest infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Slack message appears in real channel | NOTIFY-03 | Requires a real incoming-webhook URL | Configure QUIRK_SLACK_WEBHOOK, run a scheduled scan that triggers drift, confirm message in channel |
| Live SMTP email delivery | NOTIFY-04 | Requires a real SMTP server + credentials | Configure SMTP env vars, trigger drift, confirm email received |

*Network sends are unit-tested with mocked transports; live delivery is human-UAT.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
