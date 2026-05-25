---
phase: 101-notification-fan-out-security-foundation
verified: 2026-05-24T12:00:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 10/11
  gaps_closed:
    - "Email fan-out passes DriftSummary (not a pre-built string) to _channel_send_email — AttributeError bug fixed"
    - "Dead _deliver helper removed from dispatcher.py"
    - "New regression test test_dispatch_email_channel_reaches_transport exercises real _channel_send_email wrapper through stubbed transport"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Slack live delivery end-to-end"
    expected: "After a scheduled scan with new HIGH findings or score regression, a Slack message arrives in the configured channel with score band, delta, finding counts, and dashboard link"
    why_human: "Requires a live Slack workspace + incoming-webhook URL; unit tests use mocked WebhookClient transport"
  - test: "Email live delivery end-to-end"
    expected: "After triggering a scheduled scan, an email arrives at the configured recipients with subject and body matching the drift summary"
    why_human: "Requires a live SMTP server or test mailbox; unit tests use monkeypatched smtplib"
  - test: "Generic webhook live delivery with HMAC verification"
    expected: "Webhook endpoint receives a POST with X-QUIRK-Signature header; body contains only whitelisted aggregate fields, no host/port/protocol"
    why_human: "Requires a live HTTP endpoint; unit tests mock urlopen"
  - test: "Scheduler integration: notification fires after a real scheduled scan"
    expected: "With QUIRK_CONFIG_PATH set and a notification config present, running a scheduled scan that produces new HIGH findings results in an IntegrationDelivery row and a delivery attempt"
    why_human: "Requires the full scheduler subprocess loop plus a live DB and config file; not exercised in the unit test suite"
---

# Phase 101: Notification Fan-Out + Security Foundation Verification Report

**Phase Goal:** Scheduled-scan drift events are delivered to operators — Slack summary, email, and generic webhook — with all integration security primitives locked in so downstream phases inherit a safe, isolated delivery layer.
**Verified:** 2026-05-24
**Status:** human_needed
**Re-verification:** Yes — after gap closure (email fan-out AttributeError bug)

---

## Re-verification Summary

Previous status: `gaps_found` (10/11 — email channel fan-out broken).

**Gap closed:** `dispatch_notifications` at line 224 now calls `_channel_send_email(notify_cfg.email, summary)` passing the `DriftSummary` object, not a pre-built string. The redundant inline subject/body construction that previously preceded the call is gone. The dead `_deliver` helper (lines 132-160 in the original) has been removed entirely — `grep -n 'def _deliver' quirk/notify/dispatcher.py` returns no output. The new test `test_dispatch_email_channel_reaches_transport` exercises the real `_channel_send_email` wrapper through a stubbed transport and confirms a `"ok"` delivery row is written.

Full test suite: **106 passed, 1 deselected** (up from 105 in initial verification).

All security invariants re-confirmed below.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | safe_str() scrubs Slack xoxb- tokens, hooks.slack.com webhook URLs, and SMTP connection strings | VERIFIED | Three regexes confirmed in `quirk/util/safe_exc.py` lines 41-47; 5 TDD tests pass |
| 2 | init_db creates an integration_deliveries table with the agreed 7-column schema | VERIFIED | `IntegrationDelivery` model at `quirk/models.py:245`; `_ensure_integration_deliveries_table` called from `quirk/db.py:403`; schema test passes |
| 3 | pip resolving quirk-scanner[all] includes slack-sdk | VERIFIED | `pyproject.toml` line 88 + 104; CI guard test passes |
| 4 | load_notifications_config reads from QUIRK_CONFIG_PATH, never the scheduler --config DB path | VERIFIED | `grep -c 'config_path' quirk/notify/config.py` = 0; `grep -c 'config_path' quirk/notify/dispatcher.py` = 0; `QUIRK_CONFIG_PATH` at line 172; binary-file → None test passes |
| 5 | Secrets are stored as env-var NAMES in NotifyCfg, never as literal values | VERIFIED | `SlackNotifyCfg.slack_webhook_env`, `EmailNotifyCfg.smtp_password_env`, `WebhookNotifyCfg.url_env` / `hmac_key_env` — all are NAME fields; 15 tests pass |
| 6 | to_integration_payload() excludes host/port/protocol/new_findings_sample | VERIFIED | Returned dict keys confirmed by AST analysis: 12 aggregate-only keys; no topology keys; test with populated SampleFindingItem fixtures passes |
| 7 | Slack channel delivers one summary via lazy WebhookClient; skips with WARNING when slack_sdk absent | VERIFIED | `find_spec` gate at line 37; `from slack_sdk.webhook import WebhookClient` at line 64 confirmed inside `send_slack` by AST inspection; 6 channel tests pass |
| 8 | Email channel sends via stdlib smtplib with mandatory timeout to one or more recipients | VERIFIED | `timeout=cfg.timeout_seconds` on both SMTP and SMTP_SSL paths; SSRF check on SMTP host; 7 channel tests pass; dispatcher call site now correctly passes DriftSummary |
| 9 | Webhook channel POSTs JSON via stdlib urllib with HMAC-SHA256 X-QUIRK-Signature and SSRF check | VERIFIED | `X-QUIRK-Signature` header at line 68; `validate_external_url` at line 47; `urlopen` with `timeout=`; 9 webhook tests + 21 SSRF parametrized tests pass |
| 10 | The scheduler hook is wrapped in try/except so a delivery failure never corrupts the scan record | VERIFIED | `quirk/cli/scheduler_cmd.py` lines 168-177: deferred import + try/except wraps entire dispatch call; test `test_scheduler_dispatch_raises_scan_record_unaffected` passes |
| 11 | After a scheduled scan completes, dispatcher fans out to all enabled channels (including email) when trigger fires | VERIFIED | `dispatch_notifications` line 224 now calls `_channel_send_email(notify_cfg.email, summary)` — DriftSummary passed correctly. Dead `_deliver` helper removed. New test `test_dispatch_email_channel_reaches_transport` runs the real wrapper with stubbed transport: confirms `"2 new HIGH"` in subject and `status="ok"` delivery row. 106 tests pass. |

**Score:** 11/11 truths verified

---

## Anchor-Phase Security Invariants

All invariants re-verified directly against source:

| Invariant | Check | Result |
|-----------|-------|--------|
| `config_path` count in `config.py` | `grep -c 'config_path' quirk/notify/config.py` = 0 | PASS |
| `config_path` count in `dispatcher.py` | `grep -c 'config_path' quirk/notify/dispatcher.py` = 0 | PASS |
| Every channel calls `validate_external_url` at delivery time | `slack.py:54`, `email.py:38`, `webhook.py:47` — all import and call before connect | PASS |
| slack_sdk import is lazy and inside `send_slack` only | Line 64 confirmed inside `send_slack` function body; shadow-trap-safe | PASS |
| `to_integration_payload()` excludes host/port/protocol/new_findings_sample | Payload module comment + key-set confirmed; topology absent | PASS |
| Scheduler hook wrapped so delivery failure never corrupts scan record | Lines 168-177 confirmed; test passes | PASS |
| `should_notify` returns False when `score_delta` is None | `report.score_delta is not None and` guard at line 122; test `test_no_notify_on_first_scan` passes | PASS |
| `integration_deliveries.error_summary` always routed through `safe_str` | Lines 205, 208, 227, 230, 247, 250 — all six sites use `safe_str(exc)` | PASS |

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/util/safe_exc.py` | 3 new sensitive patterns (xoxb, hooks.slack.com, smtps://) | VERIFIED | Lines 41-47 confirmed |
| `quirk/models.py` | `class IntegrationDelivery` with 7-column schema | VERIFIED | Line 245; correct nullable/index constraints |
| `quirk/db.py` | `_ensure_integration_deliveries_table` called from `init_db` | VERIFIED | Definition at line 358; call at line 403 |
| `pyproject.toml` | `notify = ["slack-sdk>=3.33.0"]` + in `[all]` | VERIFIED | Lines 88 + 104 |
| `quirk/notify/__init__.py` | Package marker + re-exports | VERIFIED | Exists; re-exports public API |
| `quirk/notify/config.py` | `NotifyCfg` dataclasses + `load_notifications_config()` | VERIFIED | Full implementation; QUIRK_CONFIG_PATH path; config_path count = 0 |
| `quirk/notify/payload.py` | `DriftSummary` + `build_drift_summary()` + `to_integration_payload()` | VERIFIED | Full implementation; topology exclusion confirmed |
| `quirk/notify/channels/slack.py` | `send_slack` with find_spec gate + lazy import + SSRF | VERIFIED | All three controls confirmed; shadow-trap-safe |
| `quirk/notify/channels/email.py` | `send_email` via smtplib + timeout + SSRF | VERIFIED | Channel module correct; dispatcher call site now correct |
| `quirk/notify/channels/webhook.py` | `send_webhook` via urllib + HMAC + SSRF | VERIFIED | All controls present |
| `quirk/notify/dispatcher.py` | `dispatch_notifications`, `should_notify`, `_find_two_sessions` | VERIFIED | Email fan-out fixed (line 224: DriftSummary passed). Dead `_deliver` helper removed. All fan-out blocks use correct per-channel wrappers. |
| `quirk/cli/scheduler_cmd.py` | Notification hook after db.commit() in try/except | VERIFIED | Lines 168-177 confirmed |
| `tests/test_notify_dispatcher.py` | `test_dispatch_email_channel_reaches_transport` regression test | VERIFIED | New test confirmed at lines 265-328; exercises real wrapper through stubbed transport; asserts "2 new HIGH" in subject and status="ok" delivery row |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/db.py::init_db` | `_ensure_integration_deliveries_table` | chain call | WIRED | Line 403 confirmed |
| `pyproject.toml [all]` | `quirk-scanner[notify]` | extra inclusion | WIRED | Line 104 confirmed |
| `quirk/notify/config.py::load_notifications_config` | `os.environ QUIRK_CONFIG_PATH` | env-var path resolution | WIRED | Line 172 confirmed; config_path count = 0 |
| `quirk/notify/payload.py::to_integration_payload` | TrendReport aggregate fields | explicit field whitelist | WIRED | 12-key whitelist confirmed |
| `quirk/notify/channels/*.py` | `validate_external_url` | delivery-time SSRF gate | WIRED | All 3 channel files import and call it |
| `quirk/notify/channels/slack.py` | `slack_sdk.webhook.WebhookClient` | lazy import inside send_slack | WIRED | Line 64 inside function body confirmed |
| `quirk/cli/scheduler_cmd.py::_dispatch_schedule` | `dispatch_notifications` | deferred import + try/except after db.commit() | WIRED | Lines 168-177 confirmed |
| `dispatch_notifications` | email channel | `_channel_send_email(cfg, summary)` | WIRED | Line 224: passes DriftSummary correctly; AttributeError bug fixed |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `dispatch_notifications` | `notify_cfg` | `load_notifications_config()` via QUIRK_CONFIG_PATH | Yes (YAML file) | FLOWING |
| `dispatch_notifications` | `report` | `compute_trend_report(current_ts, previous_ts, db)` | Yes (DB query) | FLOWING |
| `dispatch_notifications` | `summary` | `build_drift_summary(report, ...)` | Yes (from real TrendReport) | FLOWING |
| `_channel_send_email` | `summary` argument | `dispatch_notifications` line 184 — shared `summary` DriftSummary object | Yes — correct type, attributes accessible | FLOWING |
| `integration_deliveries` rows | `error_summary` | `safe_str(exc)` | Yes — scrubbed | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `should_notify` returns False on first scan (score_delta=None, new_high=0) | `test_no_notify_on_first_scan` | PASS | PASS |
| `to_integration_payload` excludes topology keys | AST key-set check + payload whitelist tests | No host/port/protocol/sample keys | PASS |
| Email fan-out reaches transport with DriftSummary (not string) | `test_dispatch_email_channel_reaches_transport` — real wrapper, stubbed transport | subject contains "2 new HIGH"; delivery row status="ok" | PASS |
| Full phase test suite | `python -m pytest tests/test_notify*.py tests/test_integration_deliveries_schema.py tests/test_install_all_includes_notify.py -q` | 106 passed, 1 deselected | PASS |

---

## Probe Execution

Step 7c: SKIPPED — no `probe-*.sh` scripts declared for this phase.

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| NOTIFY-01 | 101-04 | Drift events dispatched on trigger | SATISFIED | Dispatcher wired and working; email fan-out fixed; all three channels exercise correctly; 106 tests pass |
| NOTIFY-02 | 101-04 | Conservative trigger; never fires on first scan or MEDIUM-only | SATISFIED | `should_notify` logic confirmed; `score_delta is None → False` guard at line 122; test passes |
| NOTIFY-03 | 101-03 | Slack delivery, one summary per scan | SATISFIED | `send_slack` + `find_spec` gate + lazy import confirmed; 6 tests pass |
| NOTIFY-04 | 101-03 | Email delivery via stdlib SMTP | SATISFIED | `send_email` channel module correct; dispatcher now passes DriftSummary to `_channel_send_email`; new regression test confirms no AttributeError |
| NOTIFY-05 | 101-03 | Generic webhook JSON POST | SATISFIED | `send_webhook` + HMAC + SSRF confirmed; 9 tests pass |
| NOTIFY-06 | 101-02 | Global env-var-name config, secrets never persisted | SATISFIED | `NotifyCfg` stores only `*_env` names; `QUIRK_CONFIG_PATH` resolution confirmed; 15 tests pass |
| NOTIFY-07 | 101-01, 101-04 | Delivery failure isolated; scan record unaffected; audit rows | SATISFIED | Scheduler try/except confirmed; all error_summary sites use `safe_str`; test confirms scan record unaffected |
| ISEC-01 | 101-03 | Delivery-time SSRF on every channel | SATISFIED | All 3 channels call `validate_external_url` before connect; 21 parametrized SSRF tests pass |
| ISEC-02 | 101-01, 101-04 | safe_str scrubs integration secrets from logs + error_summary | SATISFIED | 3 new patterns in `safe_exc.py`; all 6 `error_summary` / logger assignment sites use `safe_str`; 5 scrubbing tests pass |
| ISEC-03 | 101-02 | Single outbound field whitelist; topology excluded | SATISFIED | `to_integration_payload` confirmed; topology keys absent; 25 tests pass |
| ISEC-04 | 101-03 | Optional-extra lazy import; graceful skip | SATISFIED | `find_spec` gate + lazy `from slack_sdk.webhook import WebhookClient` inside `send_slack`; shadow-trap-safe (AST-confirmed); skip test passes |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| No blockers or warnings found | — | — | — | — |

No `TBD`, `FIXME`, or `XXX` markers found in any phase-101 files.

The previously flagged BLOCKER (string passed as DriftSummary to `_channel_send_email`) is closed. The previously flagged WARNING (dead `_deliver` helper) is resolved — the function has been removed entirely.

---

## Human Verification Required

### 1. Slack Live Delivery

**Test:** Configure a scheduled scan with a Slack incoming-webhook URL in the YAML config. Trigger a scan that produces a new HIGH finding. Monitor the Slack channel.
**Expected:** One summary message arrives with score band, score delta, finding counts, and a dashboard link (when `dashboard_base_url` is set). No more than one message per scan.
**Why human:** Requires a live Slack workspace and webhook URL. Unit tests use a mocked `WebhookClient`.

### 2. Email Live Delivery

**Test:** Configure an SMTP email channel in YAML config and trigger a scheduled scan with new HIGH findings.
**Expected:** An email arrives at all configured recipients with a subject line matching the alert format ("QUIRK Alert: N new HIGH finding(s) — score X") and a body containing score, delta, and finding counts.
**Why human:** Requires a live SMTP server or test mailbox; unit tests mock `smtplib`.

### 3. Generic Webhook Live Delivery with HMAC

**Test:** Configure a webhook channel pointing at a request-capture endpoint (e.g., webhook.site). Set `QUIRK_WEBHOOK_HMAC_KEY` to a known key. Trigger a scan.
**Expected:** POST received with `Content-Type: application/json`, `X-QUIRK-Signature: sha256=<hexdigest>`, and body containing only aggregate fields (no host/port/protocol).
**Why human:** Requires a live HTTP endpoint; unit tests mock `urllib.request.urlopen`.

### 4. Scheduler Integration End-to-End

**Test:** Start the scheduler with `QUIRK_CONFIG_PATH` pointing at a YAML config with at least one notification channel enabled. Run a scheduled scan that triggers the notification threshold.
**Expected:** An `integration_deliveries` row appears in the DB with `status="ok"` and the scan record has `status="completed"` (not corrupted).
**Why human:** Requires the full scheduler subprocess loop and a live DB; not covered by the unit test suite.

---

## Gaps Summary

No gaps. The single BLOCKER from the initial verification is closed:

- `dispatch_notifications` line 224 now calls `_channel_send_email(notify_cfg.email, summary)` passing the `DriftSummary` object. The wrapper builds subject/body from `summary.new_high`, `summary.current_score`, etc. as designed.
- The dead `_deliver` helper has been removed from `dispatcher.py`.
- New test `test_dispatch_email_channel_reaches_transport` (lines 265-328 of `tests/test_notify_dispatcher.py`) runs the real `_channel_send_email` wrapper with only the transport stubbed, asserts `"2 new HIGH"` in the generated subject, and confirms a `status="ok"` IntegrationDelivery row.
- All 106 automated tests pass. Four live-endpoint delivery scenarios require human UAT.

---

_Verified: 2026-05-24_
_Verifier: Claude (gsd-verifier)_
