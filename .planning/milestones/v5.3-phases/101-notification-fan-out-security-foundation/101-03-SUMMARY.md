---
phase: 101-notification-fan-out-security-foundation
plan: "03"
subsystem: notify/channels
tags: [security, notify, channels, slack, email, webhook, ssrf, isec, tdd]
dependency_graph:
  requires: [101-02]
  provides: [quirk.notify.channels.slack, quirk.notify.channels.email, quirk.notify.channels.webhook]
  affects: [101-04-dispatcher, 103-siem, 104-jira, 105-servicenow]
tech_stack:
  added: []
  patterns: [find_spec-lazy-import, smtplib-timeout, urllib-hmac-signing, delivery-time-ssrf]
key_files:
  created:
    - quirk/notify/channels/__init__.py
    - quirk/notify/channels/slack.py
    - quirk/notify/channels/email.py
    - quirk/notify/channels/webhook.py
    - tests/test_notify_slack.py
    - tests/test_notify_email.py
    - tests/test_notify_webhook.py
    - tests/test_notify_ssrf.py
  modified: []
decisions:
  - "send_slack: find_spec gate + lazy WebhookClient import INSIDE dedicated helper (shadow-trap-safe); advisory WARNING on missing slack_sdk, never ImportError (ISEC-04)"
  - "SSRF via validate_external_url at DELIVERY time on every channel before connecting — Slack webhook URL, SMTP host (as https://host:port form), webhook URL (ISEC-01)"
  - "Email uses stdlib smtplib with mandatory timeout on BOTH SMTP and SMTP_SSL paths — no blocking-forever (Pitfall 3)"
  - "Webhook body is the caller-provided dict (to_integration_payload output) — no topology fields POSTed (ISEC-03); HMAC signing is optional and toggles on key presence"
  - "find_spec patched at module namespace (quirk.notify.channels.slack.find_spec) not importlib.util.find_spec to avoid module-cache race conditions in tests"
metrics:
  duration: "~18 minutes"
  completed_date: "2026-05-25"
  tasks_completed: 3
  tasks_total: 3
  files_created: 8
  files_modified: 0
  tests_added: 43
---

# Phase 101 Plan 03: Delivery Channels — Slack, Email, Webhook Summary

**One-liner:** Three self-isolated delivery channels — Slack (lazy slack_sdk + find_spec skip), Email (stdlib smtplib, mandatory timeout, SSRF on SMTP host), Webhook (stdlib urllib, HMAC-SHA256 signing, SSRF) — each validated at delivery time before connecting (ISEC-01).

## What Was Built

### Task 1: Slack Channel — lazy import + SSRF + graceful skip (NOTIFY-03, ISEC-01, ISEC-04)

**`quirk/notify/channels/__init__.py`** — Package marker. Import channels individually.

**`quirk/notify/channels/slack.py`** — `send_slack(cfg: SlackNotifyCfg, summary: DriftSummary)`:

1. `find_spec("slack_sdk") is None` → advisory WARNING containing `pip install quirk[notify]` + return (ISEC-04, never ImportError).
2. `os.environ.get(cfg.slack_webhook_env, "")` empty → WARNING with env-var name + return.
3. `validate_external_url(url)` → `ValueError("SSRF blocked ...")` on failure (ISEC-01).
4. Lazy `from slack_sdk.webhook import WebhookClient` — placed AFTER find_spec gate, inside `send_slack` only (shadow-trap-safe).
5. `client.send(text=_format_slack_text(summary))` → `RuntimeError` on non-200.
6. `_format_slack_text()` formats human-readable Slack text from DriftSummary fields (score band, delta, new-finding counts, dashboard URL if set).

**Tests (6 GREEN):** graceful skip, env-var unset skip, loopback SSRF, metadata SSRF, happy path (1 send call with `text=` kwarg), non-200 RuntimeError.

### Task 2: Email Channel — stdlib smtplib with timeout + SMTP-host SSRF (NOTIFY-04, ISEC-01)

**`quirk/notify/channels/email.py`** — `send_email(cfg: EmailNotifyCfg, subject, body)`:

1. Constructs `https://{smtp_host}:{smtp_port}` and calls `validate_external_url()` → `ValueError("SSRF blocked ...")` on failure (ISEC-01). Covers metadata IP, loopback, RFC1918.
2. Resolves password from `os.environ.get(cfg.smtp_password_env or "", "")` at delivery time.
3. Builds `MIMEMultipart("alternative")` + `MIMEText(body, "plain")`.
4. Branches on `cfg.use_ssl`:
   - `True` → `smtplib.SMTP_SSL(host, port, context=context, timeout=cfg.timeout_seconds)`
   - `False` → `smtplib.SMTP(host, port, timeout=cfg.timeout_seconds)` + ehlo + starttls
5. `login()` only called when `cfg.smtp_user` is set.
6. `sendmail(from, recipients_list, msg)` — multi-recipient.

Both paths have `timeout=` (grep count = 2, meets acceptance criteria ≥2).

**Tests (7 GREEN):** metadata/loopback/RFC1918 SSRF; STARTTLS timeout+recipients; SSL path timeout; no-login when smtp_user=None; source `timeout=` count assertion.

### Task 3: Webhook Channel — stdlib urllib + HMAC signing + SSRF (NOTIFY-05, ISEC-01)

**`quirk/notify/channels/webhook.py`** — `send_webhook(cfg: WebhookNotifyCfg, payload: dict)`:

1. Resolves URL from `os.environ.get(cfg.url_env, "")` → `ValueError` if empty.
2. `validate_external_url(url)` → `ValueError("SSRF blocked ...")` on failure (ISEC-01).
3. JSON-encodes payload (caller passes `to_integration_payload()` output — whitelisted aggregates, no topology).
4. Builds `urllib.request.Request` with `method="POST"` and `Content-Type: application/json`.
5. HMAC signing: when `cfg.hmac_key_env` is set AND the env var is non-empty, computes `hmac.new(key, body, sha256).hexdigest()` and adds `X-QUIRK-Signature: sha256=<hexdigest>`. Absent when key env var is unset or empty.
6. `urlopen(req, timeout=cfg.timeout_seconds)` — mandatory timeout (Pitfall 3).
7. `RuntimeError` on non-2xx (200/201/202/204 are accepted).

**`tests/test_notify_ssrf.py`** — Cross-channel parametrized SSRF tests: 7 SSRF addresses (loopback IPv4/IPv6, RFC1918 A/B/C, metadata AWS/GCP label) × 3 channels = 21 parametrized test cases, all GREEN.

**Tests (9 webhook + 21 SSRF = 30 GREEN):** URL-unset ValueError; loopback/metadata SSRF; no HMAC header when key absent; HMAC header correct value when key set; HMAC absent when key env empty; body has no topology keys; non-2xx RuntimeError; source assertion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test local-import shadow trap in test_notify_slack.py**
- **Found during:** Task 1 RED phase
- **Issue:** First draft of `test_graceful_skip_missing_slack_sdk` used `import importlib.util` inside a function where `importlib` was also imported at module scope, triggering `UnboundLocalError: cannot access local variable 'importlib'` — the exact shadow trap we were guarding against in production code.
- **Fix:** Moved all `import importlib` and `import importlib.util` to module scope and used them directly; no re-import inside functions.
- **Files modified:** `tests/test_notify_slack.py`

**2. [Rule 1 - Bug] Patching wrong find_spec namespace**
- **Found during:** Task 1 RED→GREEN transition
- **Issue:** Tests patched `importlib.util.find_spec` but `slack.py` does `from importlib.util import find_spec` at module top, so the module already holds a direct reference. Patching `importlib.util.find_spec` had no effect on the already-imported name.
- **Fix:** Tests patch `quirk.notify.channels.slack.find_spec` (the name in the module's namespace), which correctly intercepts all calls from within `send_slack`.
- **Files modified:** `tests/test_notify_slack.py`
- **Commit:** d89f406

## Known Stubs

None. All three channels are fully implemented with real logic. No hardcoded empty values or placeholder text.

## Threat Surface Scan

No new network endpoints or auth paths introduced. The three channel senders are library code called by the dispatcher — they open outbound connections only, and only after SSRF validation. The `X-QUIRK-Signature` header adds a signing surface but uses stdlib `hmac` with no external dependency. No schema changes in this plan (schema is Plan 01 scope). No new threat surface beyond what is documented in the plan's threat model (T-101-06 through T-101-09).

## Self-Check: PASSED
