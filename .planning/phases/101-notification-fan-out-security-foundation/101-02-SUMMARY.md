---
phase: 101-notification-fan-out-security-foundation
plan: "02"
subsystem: notify
tags: [security, notify, config, payload, isec, tdd]
dependency_graph:
  requires: [101-01]
  provides: [quirk.notify.config, quirk.notify.payload, NotifyCfg, DriftSummary, to_integration_payload]
  affects: [103-siem, 104-jira, 105-servicenow]
tech_stack:
  added: []
  patterns: [env-var-name-secrets, whitelist-payload, content-model-once, QUIRK_CONFIG_PATH-pattern]
key_files:
  created:
    - quirk/notify/__init__.py
    - quirk/notify/config.py
    - quirk/notify/payload.py
    - tests/test_notify_config.py
    - tests/test_notify_payload_whitelist.py
  modified: []
decisions:
  - "load_notifications_config resolves via QUIRK_CONFIG_PATH env var, never from the scheduler --config DB path (Pitfall 1 guard)"
  - "NotifyCfg stores env-var NAMES only — secrets resolved at delivery time, never persisted (NOTIFY-06)"
  - "to_integration_payload is the single canonical outbound whitelist — downstream phases 103/104/105 MUST call it before building any payload (ISEC-03)"
  - "DriftSummary mirrors ExecContent pattern — built once, formatters consume; no re-derivation from raw TrendReport"
  - "Binary/SQLite files passed to load_notifications_config return None silently — scheduler --config DB path must never crash the notification loader"
metrics:
  duration: "~8 minutes"
  completed_date: "2026-05-25"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 0
  tests_added: 40
---

# Phase 101 Plan 02: Notify Config + Payload Primitives Summary

**One-liner:** `quirk/notify/` package with env-var-name NotifyCfg loader (QUIRK_CONFIG_PATH, binary-file-safe) + DriftSummary content model + to_integration_payload topology-exclusion whitelist (ISEC-03).

## What Was Built

### Task 1: NotifyCfg Dataclasses + load_notifications_config (NOTIFY-06)

Created the `quirk/notify/` package with three modules:

**`quirk/notify/__init__.py`** — Package marker re-exporting the public API (`NotifyCfg`, `load_notifications_config`, `DriftSummary`, `build_drift_summary`, `to_integration_payload`).

**`quirk/notify/config.py`** — Four dataclasses and a config loader:
- `SlackNotifyCfg(slack_webhook_env, dashboard_base_url)` — env-var NAME only
- `EmailNotifyCfg(smtp_host, smtp_port, smtp_from, recipients, smtp_user, smtp_password_env, use_ssl, timeout_seconds)` — `smtp_password_env` is the env-var NAME, never the password literal
- `WebhookNotifyCfg(url_env, hmac_key_env, timeout_seconds)` — env-var NAMEs only
- `NotifyCfg(trigger_score_floor=-5, slack=None, email=None, webhook=None)` — top-level config
- `load_notifications_config(path=None)` — resolves `path or os.environ.get("QUIRK_CONFIG_PATH")`, returns None when unresolvable, absent, non-YAML (binary/SQLite), or missing `[notifications]` key. Wrapped in `try/except` — notification config failure NEVER aborts a scan (Pitfall 1 / T-101-05).

Acceptance criteria verified:
- `grep -c 'QUIRK_CONFIG_PATH' quirk/notify/config.py` = 4 (≥1 required)
- `grep -c 'config_path' quirk/notify/config.py` = 0 (never reads the scheduler DB-path arg)

Tests: 15 test cases all GREEN (RED → GREEN TDD).

### Task 2: DriftSummary + to_integration_payload Whitelist (ISEC-03)

**`quirk/notify/payload.py`** — Full implementation:

- `DriftSummary` dataclass — shared content model (mirrors v5.2 ExecContent). Fields: `current_score`, `previous_score`, `score_delta`, `score_band`, `new_high`, `new_medium`, `new_low`, `scan_id`, `dashboard_url`. Built once; all channel formatters consume this instance.
- `_score_to_band(score)` — maps int/None → `"CRITICAL"` (≤30 or None) | `"HIGH"` (≤50) | `"MEDIUM"` (≤65) | `"LOW"` (≤79) | `"GOOD"` (≥80).
- `build_drift_summary(report, dashboard_base_url, scan_id)` — builds DriftSummary once from TrendReport. `dashboard_url` is None when `dashboard_base_url` is unset; appends `/trends` to the base URL when set.
- `to_integration_payload(report)` — canonical outbound whitelist returning ONLY 12 safe aggregate fields. Module docstring explicitly mandates that Phases 103/104/105 call this before any outbound payload. `new_findings_sample` and `resolved_findings_sample` (which carry `host`/`port`/`protocol`) are excluded via `# EXCLUDED:` comment (per spec: comments referencing the exclusion are allowed; the topology fields never appear in the returned dict construction).

Topology exclusion proven by test fixture with 3 populated `SampleFindingItem` entries (each carrying `host="10.0.0.1"`, `port=443`, `protocol="TLS"`) — the returned dict contains none of these fields.

Tests: 25 test cases all GREEN (RED → GREEN TDD).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] payload.py stub required before config tests could run**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `quirk/notify/__init__.py` imports from both `config.py` and `payload.py`. With `payload.py` missing, `from quirk.notify.config import load_notifications_config` triggered `ModuleNotFoundError: No module named 'quirk.notify.payload'` in Task 1 tests.
- **Fix:** Created a minimal stub `payload.py` (raising `NotImplementedError`) to unblock Task 1 tests. Task 2 then replaced the stub with the full implementation.
- **Files modified:** `quirk/notify/payload.py`
- **Commit:** 06387d7

**2. [Rule 1 - Bug] SampleFindingItem fixture had incorrect `title` field**
- **Found during:** Task 2 RED tests
- **Issue:** The test fixture called `SampleFindingItem(title=..., host=..., port=..., protocol=..., severity=...)` but `SampleFindingItem` in `quirk/intelligence/trends.py` has no `title` field — it has only `host`, `port`, `protocol`, `severity`.
- **Fix:** Removed `title` from the fixture, reordered kwargs to match the actual dataclass field order.
- **Files modified:** `tests/test_notify_payload_whitelist.py`
- **Commit:** 7fa0b0f

## Threat Surface Scan

All files created are internal-only modules with no network endpoints, auth paths, file access patterns, or schema changes. `config.py` reads a local YAML file (path already gated by `os.path.isfile`). `payload.py` is a pure transform function — no I/O. No new threat surface beyond what is already documented in the plan's threat model (T-101-03, T-101-04, T-101-05).

## Known Stubs

None. All placeholder behavior from the Task 1 stub payload.py was replaced by full implementations in Task 2.

## Self-Check: PASSED

All 5 created files exist on disk. All 4 task commits verified in git log (c467808, 06387d7, 7fa0b0f, 797b0a4).
