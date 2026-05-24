# Phase 101: Notification Fan-Out + Security Foundation - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the notification delivery layer for completed scheduled scans —
Slack summary, email (stdlib SMTP), and generic outbound webhook — wired into the
existing scheduler seam (`_dispatch_schedule`, `quirk/cli/scheduler_cmd.py:162`, after
the scan subprocess completes and `db.commit()` runs). As the v5.3 ANCHOR phase, it
also ships ALL seven integration-security primitives (SSRF validation, secret
scrubbing, outbound field whitelist, delivery isolation, notification-storm
suppression, optional-extra lazy import, route-coverage discipline) so every
downstream integration phase (SIEM, Jira, ServiceNow) inherits a safe, isolated
delivery layer rather than retrofitting it.

In scope: NOTIFY-01..07, ISEC-01..04.
Out of scope: per-schedule notification routing (global config only, v5.3-D-07),
SIEM/ticketing backends (Phases 103–105), delivery retry/backoff.
</domain>

<decisions>
## Implementation Decisions

### Notification Config Shape
- Global `[notifications]` config block lives in the existing scan config file loaded via `--config` (no separate notify.yaml)
- Secrets are referenced by env-var NAME in config (e.g. `slack_webhook_env = "QUIRK_SLACK_WEBHOOK"`), resolved at dispatch time — never literal values, never persisted (NOTIFY-06)
- A channel is enabled by the presence of its config block (Slack / email / webhook each independently optional)
- Fan-out: when multiple channels are configured, dispatch delivers to all of them in one pass

### Trigger & Message Content
- Default trigger (NOTIFY-02): a new HIGH/CRITICAL finding OR a score regression beyond a configurable floor (default −5); never fires on MEDIUM-only or on every scan
- Slack delivery is one summary message per scan (score band, delta, finding counts, dashboard link) — NOT one message per finding (NOTIFY-03)
- Dashboard link comes from a configurable `dashboard_base_url`; if unset, the link is omitted gracefully
- A shared `build_drift_summary()` content model feeds channel-specific formatters (Slack blocks, email text, webhook JSON) — mirrors the v5.2 one-content-model → many-renderers pattern

### Delivery Isolation & Observability
- `integration_deliveries` table schema: `scan_id, finding_hash, destination, status, attempted_at, error_summary` (per STATE.md pending todo)
- Failure handling (NOTIFY-07): per-channel catch-all → log at WARNING via `safe_str`, record a failed delivery row, continue; the scan/report run is never aborted or corrupted
- No retry/backoff in v5.3 — record + log only; retry is explicitly future work
- Dispatch logic lives in a new `quirk/notify/dispatcher.py`, called from `_dispatch_schedule` after line 162 (post scan completion + commit)

### Security Primitives (ISEC-01..04)
- SSRF (ISEC-01): every user-configured outbound URL is validated at DELIVERY time (not only config-load), rejecting loopback / internal / metadata (169.254.169.254) / link-local targets
- Outbound whitelist (ISEC-03): a single `to_integration_payload()` allowlist module defines exactly which finding/cert/drift fields are safe to send; everything else is redacted before any payload is built — downstream phases reuse this one whitelist
- Secret scrubbing (ISEC-02): reuse the existing `safe_str` discipline (`quirk/util/safe_exc.py`) for all log/error output; Slack `xoxb-`/webhook URLs, SMTP auth, HMAC keys never appear in logs
- Optional-extra (ISEC-04): lazy import inside the dispatcher; a missing `[notify]` extra (slack-sdk absent) degrades with an advisory WARNING and skips that channel — never an ImportError on minimal install
- `[notify]` extra contains `slack-sdk` only; email uses stdlib `smtplib`, generic webhook uses stdlib `urllib` — no `requests` dependency

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/util/safe_exc.py::safe_str()` — established secret-scrubbing discipline (used in credentials, analyze_token, doctor, scan routes); reuse for ISEC-02
- `_dispatch_schedule()` in `quirk/cli/scheduler_cmd.py:109` — the dispatch seam; scan runs as subprocess, completes at L155-162, then `db.commit()`. Notification hook goes after L162
- `ScheduledRun` / `ScheduledScan` SQLAlchemy models — `run.scan_output_path` holds the finished scan JSON the drift summary reads from
- v5.2 shared-content-model → many-renderers pattern (CLI/HTML/PDF/DOCX) — mirror it for build_drift_summary → Slack/email/webhook formatters
- TrendReport drift computation (Phase 63/64) already exists — emits drift events but never delivered (the gap NOTIFY-01 closes)

### Established Patterns
- Optional extras with lazy import + CI guard (e.g. `[identity]` excluded from `[all]`, `tests/test_install_all_excludes_impacket.py`) — follow this for `[notify]`
- `[project.optional-dependencies]` in pyproject.toml (line 34) — add `notify` extra here
- List-form subprocess (no shell=True) and env-var-resolved secrets are existing security norms in scheduler_cmd

### Integration Points
- pyproject.toml `[project.optional-dependencies]` — new `notify = ["slack-sdk>=..."]` extra; decide whether `[notify]` joins `[all]` at plan time
- Scan config loader (the file passed to `--config`) — add `[notifications]` parsing
- New table `integration_deliveries` — needs a migration/init-db hook consistent with existing schema management

</code_context>

<specifics>
## Specific Ideas

- Confirm exact line number of the `_dispatch_schedule()` seam before planning — verified at scheduler_cmd.py:162 (post db.commit) during discuss.
- Define `integration_deliveries` schema at plan time — minimum agreed: scan_id, finding_hash, destination, status, attempted_at, error_summary.
- `to_integration_payload()` whitelist and `integration_deliveries` table are explicitly designed as shared primitives consumed by Phases 103 (SIEM), 104 (Jira), 105 (ServiceNow) — build for reuse, not just notifications.

</specifics>

<deferred>
## Deferred Ideas

- Per-schedule notification routing (requires scheduled_scans schema change) — v5.3-D-07, deferred to v5.3.x
- Delivery retry / backoff — out of scope for v5.3
- Splunk HEC endpoint — deferred per milestone scope (SIEM = syslog/CEF in Phase 103)

</deferred>
