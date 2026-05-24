# Project Research Summary

**Project:** QU.I.R.K. v5.3 — Adoption & Integration Surface
**Domain:** Outbound integration layer on an existing Python CLI crypto-scanner + FastAPI dashboard
**Researched:** 2026-05-24
**Confidence:** HIGH

## Executive Summary

QU.I.R.K. v5.3 adds the outbound integration surface that turns a silent scheduled scanner into an operationally visible tool: drift-triggered notifications (Slack, email, generic webhook), SIEM findings export (Splunk HEC), per-finding ticket creation (Jira), and dashboard API-key auth polish. All four researchers converge on the same architectural anchor: the gap in `scheduler_cmd.py::_dispatch_schedule()` (line 162, post-`db.commit()`) where `compute_trend_report()` is never called after a scheduled run completes. Closing this gap is the load-bearing first move of the milestone — every downstream integration phase inherits the `NotificationChannel` ABC, the `NotificationCfg` config dataclasses, and the security primitives (`safe_str` extension, `validate_external_url()` at delivery time, `to_integration_payload()` whitelist, `integration_deliveries` idempotency table) that must be established here.

The dependency budget is deliberately minimal: `slack-sdk>=3.42.0` for the `[notify]` extra, `jira>=3.10.5` for the `[tickets]` extra, and stdlib (`smtplib`, `urllib.request`, `logging.handlers.SysLogHandler`) for everything else. The `elasticsearch` Python client is explicitly rejected as over-engineered for this use case; Splunk HEC requires no new dep. Dashboard auth is ~90% already shipped (Phase 58 `HTTPBearer` + `hmac.compare_digest`); v5.3 adds `X-API-Key` header support, a `quirk token generate/rotate` CLI, and a React login form — additive polish, not a new mechanism.

The primary execution risk is the constellation of security pitfalls that must all be locked in at Phase 101 rather than retrofitted: SSRF via operator-configured delivery URLs (DNS-rebinding gap exists between config-load and delivery), secret leakage via exception messages into `scan_error` columns (`safe_str` patterns need extension for Splunk/Slack/SMTP token shapes), sensitive finding data exfiltration (a `to_integration_payload()` field whitelist must gate all integration serializers), notification storms (one summary per scan, not per finding; `integration_deliveries` idempotency table from day one), optional-extra import trap (lazy imports only — the `pypdf` v4.10 post-ship breakage is the reference failure), and delivery failure isolation (integration calls must never abort a scan or corrupt a `ScheduledRun` record). All seven pitfalls must be designed in at Phase 101; none can be retrofitted without high risk.

---

## Key Findings

### Recommended Stack

The v5.3 stack is nearly zero-delta from the existing platform. Three optional extras are added: `[notify]` (one dep: `slack-sdk>=3.42.0`), `[tickets]` (one dep: `jira>=3.10.5`), and no extra at all for SIEM (Splunk HEC is a stdlib `urllib.request` POST). Dashboard auth needs no new dep — `fastapi.security.APIKeyHeader` is already in the pinned `fastapi>=0.128.8`. The decision not to add `requests`, `elasticsearch-py`, `celery`, or `sendgrid` is as important as what is added: each would introduce blast radius with no functional gain for this single-tenant consulting-deploy model.

**Core technology additions:**
- `slack-sdk>=3.42.0` (`[notify]` extra) — `WebhookClient` for Slack incoming webhooks; no bot-token OAuth dance; Block Kit message builder; PyPI-verified 2026-05-24
- `jira>=3.10.5` (`[tickets]` extra) — Jira Cloud REST v3 issue create + JQL search; `basic_auth=(email, api_token)` pattern; no transitive dep conflicts; PyPI-verified 2026-05-24
- `stdlib smtplib + email` — zero deps; `SMTP_SSL` (port 465) or `SMTP + STARTTLS` (port 587); `ssl.create_default_context()` for cert validation
- `stdlib urllib.request` — generic webhook POST; Splunk HEC POST; already used in existing SSRF allowlist code
- `stdlib logging.handlers.SysLogHandler` — CEF/syslog tertiary SIEM path; zero deps; 30-line `CefFormatter` subclass
- `fastapi.security.APIKeyHeader` — `X-API-Key` header alternative to `Authorization: Bearer`; already in pinned fastapi dep
- `secrets.token_urlsafe(32)` (stdlib) — `quirk token generate/rotate` CLI

**Explicit rejects:** `elasticsearch` Python client (400KB+, overkill for <=hundreds of findings), `requests` library (not currently a dep; 10-line urllib equivalent), `slack-bolt` (event handling, not outbound push), `celery`/`rq` (SaaS-milestone async queues, not v5.3).

---

### Expected Features

**Must have (table stakes):**
- Post-run hook wired in `_dispatch_schedule()` calling `compute_trend_report()` after every `ScheduledRun` commits — closes the documented "half-built" scheduler gap
- Trigger guard — no-op delivery when `new_high == 0 AND new_medium == 0 AND abs(score_delta) < threshold` (default: -5); fires on first new CRITICAL/HIGH
- Slack drift-event delivery — Block Kit message with score band + delta, finding counts by severity, dashboard link; one summary per scan, never per finding
- Email drift-event delivery — `smtplib` STARTTLS; zero new deps; plaintext + HTML MIME
- Generic outbound webhook — JSON POST with `X-QUIRK-Signature: sha256=<HMAC>` authentication header
- Splunk HEC export — per-finding JSON events batched per scan; `sourcetype: quirk:finding`; zero new deps
- Jira auto-ticket — one ticket per `(finding_category, host, port)` tuple; SHA256 label fingerprint dedup; JQL search before create; QRAMM evidence in description
- Dashboard `X-API-Key` header support — additive to Phase 58 bearer auth; same constant-time compare; same `QUIRK_API_TOKEN` value
- `quirk token generate` + `quirk token rotate` CLI — `secrets.token_urlsafe(32)`, print-once to stdout

**Should have (differentiators):**
- Score band + subscore delta in Slack messages (`Readiness: 62 FAIR (-8 from last scan)`) — leaders recognize regression immediately
- QRAMM maturity evidence in Jira ticket description — governance-ready context a security team can cite in a sprint
- `X-QUIRK-Signature` HMAC-SHA256 on generic webhook — allows consumers to verify authenticity
- Configurable trigger threshold per schedule (`notify_threshold` column) — mirrors Alertmanager severity-routing conventions
- `GET /api/notifications/status` + `POST /api/notifications/test` dashboard routes — show configured state without exposing secrets
- React login form for token-gated dashboard — replaces silent 401 on unauthenticated access
- `GET /api/auth/status` unprotected endpoint — lets SPA decide whether to show login prompt

**Defer to v5.3.x or v5.4+:**
- Configurable per-schedule threshold (add after first user reports notification fatigue)
- Retry with `ScheduledRun.notify_status` delivery log (at-least-once guarantee)
- Jira auto-close/comment-on-resolve
- ServiceNow ticketing (after Jira validates the ticketing pattern)
- Elastic/OpenSearch SIEM export (after Splunk HEC validates the SIEM pattern)
- Multi-channel fan-out per schedule
- SQLite dead-letter queue for failed deliveries
- Inbound webhook from SIEM (bidirectional sync) — SaaS milestone
- Session cookies, JWT issuance, user tables — v5.4+ SaaS multi-tenant

**Confirmed anti-features (do not implement):**
- Notify on every scan completion (heartbeat-as-notification leads to alert fatigue within days)
- One Jira ticket per scan (no assignee, no acceptance criteria, no done condition)
- Real-time websocket push (incompatible with local/offline consulting-deploy model)
- Store raw webhook payloads or response bodies in SQLite (credential leakage risk)

---

### Architecture Approach

The integration layer attaches to a single seam: `_dispatch_schedule()` in `quirk/cli/scheduler_cmd.py` at line 162 (post-`db.commit()`). A `NotificationChannel` ABC (in `quirk/notifications/__init__.py`) defines the contract; `drift_helper.py` wraps `compute_trend_report()` for the scheduler; pluggable backends implement `send_drift_event(report, schedule)` with a strict "catch all, log at WARNING, never raise" contract. SIEM export gets a second method `send_findings_export(findings, scan_meta)` on the same ABC. Ticketing gets a separate `TicketingChannel` in `quirk/integrations/` with `open_ticket_for_finding(finding, qramm_evidence)`. Config follows the `BrokerCredential.pass_env` precedent — YAML holds env-var names, secrets resolve at dispatch time, never persisted to SQLite or scan JSON.

**Major components:**
1. `quirk/notifications/__init__.py` — `NotificationChannel` ABC; no imports from scanner or dashboard
2. `quirk/notifications/drift_helper.py` — `_compute_post_run_trend()` wrapper; owns session-timestamp resolution logic
3. `quirk/notifications/{slack,email,webhook}_channel.py` — concrete backends; stdlib only; Phase 101
4. `quirk/notifications/siem_channel.py` — Splunk HEC + Elastic + syslog/CEF; Phase 103
5. `quirk/integrations/ticketing_channel.py` — Jira (`jira>=3.10.5`); fingerprint dedup; Phase 104
6. `quirk/config.py` additions — `NotificationCfg` / `SlackNotifCfg` / `EmailNotifCfg` / `WebhookNotifCfg` / `SIEMCfg` / `TicketingCfg`; `pass_env` secret indirection
7. `quirk/dashboard/api/routes/notifications.py` — status + test endpoints; auth-gated; Phase 102
8. `integration_deliveries` SQLite table — idempotency key per `(scan_id, finding_hash, destination)`; Phase 101
9. Dashboard React login form + `GET /api/auth/status` — Phase 102

**Key patterns to follow:**
- Lazy import guard (`importlib.util.find_spec` probe) for all optional extras — never top-level import of `slack_sdk` or `jira`
- `validate_external_url()` at delivery time (not only at config load) — closes DNS-rebinding SSRF window
- `safe_str(exc)` wrapping all integration exception paths — extend `_SENSITIVE_PATTERNS` for Splunk/Slack/SMTP token shapes
- `to_integration_payload(finding, *, include_host=False)` canonical field whitelist for all integration serializers
- `integration_deliveries` table for idempotency (Jira dedup + delivery-failure audit trail)
- Fan-out loop post-scan, never inside `_wrapped_phase()` — delivery failure must never abort or corrupt a `ScheduledRun`
- Route-coverage CI test enumerating all FastAPI routes against `PUBLIC_ROUTES` allowlist

---

### Critical Pitfalls

1. **SSRF via operator-configured delivery URLs** — `validate_external_url()` must be called at delivery time, not only at config load; DNS rebinding is a real attack path; `--allow-internal-targets` must never apply to integration URLs; enforce `https://` only for webhook/HEC/Jira

2. **Secret leakage via exception messages into `scan_error` / logs** — `safe_str(exc)` must wrap all integration exception paths; extend `_SENSITIVE_PATTERNS` for Splunk `Authorization: Splunk\s+\S+`, Slack `xoxb-`/`xoxp-` prefixes, SMTP `SMTPAuthenticationError` text; Slack incoming webhook URL contains token in path — store and display as `[configured]`, never log raw

3. **Optional-extra import trap breaking minimal install** — never top-level import `slack_sdk`, `jira`, or any optional dep; use `importlib.util.find_spec` probe + lazy import; the `pypdf` v4.10 post-ship breakage is the project's reference failure; add minimal-install smoke test to CI

4. **Delivery failure corrupting scan records** — all integration delivery calls must execute outside `_wrapped_phase()` in a strictly isolated `try/except`; `ScheduledRun.status = 'completed'` must be committed before any delivery attempt; delivery timeout <=5s; a failed delivery writes to `integration_deliveries`, never to `scan_error` with exception class

5. **Notification storm + Jira duplicate tickets** — deliver one drift summary per scan, not per finding; `integration_deliveries` idempotency table with `(scan_id, finding_hash, destination)` key; exponential backoff with jitter on 429; Jira JQL dedup check before create; batch Splunk HEC events per scan

6. **Sensitive finding data exfiltrated to third-party SaaS** — `to_integration_payload()` whitelist in Phase 101; all integration serializers must call it; never `**finding.__dict__` or CBOM JSON blobs; raw cert PEM and internal PKI topology must never leave the operator's SQLite

7. **Dashboard auth gaps on new routes** — new routes must explicitly include `dependencies=[Depends(require_auth)]`; add route-coverage CI test in Phase 101; no `?token=` query params; `hmac.compare_digest()` in all new HMAC verification paths

---

## Implications for Roadmap

Based on combined research, a four-phase structure is well-supported and should be adopted directly. Phase 101 is the unambiguous anchor; it is load-bearing for the security posture of all downstream phases and must ship first.

---

### Phase 101 — Notification Fan-Out Foundation (ANCHOR)

**Rationale:** Closes the confirmed "half-built" gap in `_dispatch_schedule()`. Establishes the `NotificationChannel` ABC, `NotificationCfg` config schema, `drift_helper.py` seam, and all security primitives that downstream phases must inherit. All seven pitfalls must be addressed here — none can be retrofitted.

**Delivers:**
- `quirk/notifications/` package: ABC + `drift_helper.py` + Slack + email + generic webhook backends
- `NotificationCfg` family in `config.py` using `pass_env` secret indirection
- `_dispatch_schedule()` seam wired with fan-out loop and regression gate (score_delta <= -5 OR new_high > 0)
- `integration_deliveries` SQLite table (idempotency + delivery audit)
- `to_integration_payload()` field whitelist primitive
- `safe_str` extension for Splunk/Slack/SMTP token shapes
- `validate_external_url()` called at delivery time
- `REGISTRY` entries for `[notify]` extra with lazy import guards
- Route-coverage CI test for all FastAPI routes
- Minimal-install smoke test (integration extras absent)

**Addresses:** Drift-event Slack, email, webhook delivery (table stakes); trigger guard; notification-storm prevention; dedup guard via `last_notify_hash`

**Avoids:** All seven pitfalls — must be complete before Phase 102 begins

**Research flag:** Skip research phase. Seam location confirmed by direct code inspection; patterns confirmed by existing project precedents.

---

### Phase 102 — Dashboard Auth UX + Notification Management

**Rationale:** Independent of the notification delivery path. Can run in parallel with Phase 101 but is logically cohesive with the dashboard and UX surface. Small surface — Phase 58 already shipped 90% of the mechanism.

**Delivers:**
- `quirk token generate` + `quirk token rotate` CLI (stdlib `secrets.token_urlsafe`)
- `X-API-Key` header acceptance in `auth.py` (2-line additive change)
- `GET /api/auth/status` unprotected endpoint (SPA login prompt trigger)
- React login form (token stored in `localStorage.quirk_api_token`)
- `GET /api/notifications/status` + `POST /api/notifications/test` routes (auth-gated)

**Addresses:** Dashboard API-key header variant; `quirk token rotate` CLI; login UX

**Avoids:** JWT issuance, user tables, per-scope tokens, session cookies — v5.4 SaaS scope

**Research flag:** Skip research phase. All patterns well-documented (Phase 58 is the template).

---

### Phase 103 — SIEM Export (Splunk HEC)

**Rationale:** Semantically distinct from drift-event notifications — a per-scan, per-finding batch push to the security team's primary triage surface. Uses the `SIEMChannel` extension of the abstraction established in Phase 101. Zero new pip deps.

**Delivers:**
- `quirk/notifications/siem_channel.py` — Splunk HEC `sourcetype: quirk:finding` per-finding events batched per scan
- `quirk export --siem` CLI (on-demand + post-scheduled-scan trigger)
- `SIEMCfg` dataclass; `[siem]` optional extra (empty — stdlib only)
- `CryptoEndpoint` to Splunk HEC JSON event serializer using `to_integration_payload()` from Phase 101
- CEF/syslog tertiary path if capacity allows

**Addresses:** Splunk HEC export (enterprise table stakes); reduces "check yet another tool" friction

**Avoids:** `elasticsearch` client (explicitly rejected); Elastic export deferred to v5.4

**Research flag:** Needs plan-time verification of Splunk HEC raw vs. event endpoint choice and batch payload size limits. HEC endpoint shape is confirmed; optimal batching strategy should be confirmed against current Splunk HEC docs at planning.

---

### Phase 104 — Ticketing Integration (Jira)

**Rationale:** Highest complexity of the four phases; depends on Phase 101 for the `to_integration_payload()` whitelist and `integration_deliveries` idempotency table. The fingerprint dedup design warrants deeper plan-time research.

**Delivers:**
- `quirk/integrations/ticketing_channel.py` — Jira Cloud REST v3 issue create + JQL dedup check
- `TicketingCfg` dataclass; `[tickets]` optional extra (`jira>=3.10.5`)
- Per-finding ticket with QRAMM `evidence_bridge.py` dimension scores in description
- `quirk ticket create / list / sync` CLI subcommands
- Label fingerprint dedup: `quirk-fp-<sha256(host:port:protocol:category)>` + `quirk-last-seen-<YYYYMMDD>`
- Rediscovery comment on existing open tickets (Rapid7 InsightVM pattern)

**Addresses:** Per-finding Jira ticket creation (table stakes); fingerprint dedup (differentiator); QRAMM evidence in tickets (differentiator)

**Avoids:** ServiceNow (deferred — no free sandbox, complex OAuth2); one-ticket-per-scan anti-pattern; parallel ticket creation (serial only, <=10 req/s Jira Cloud)

**Research flag:** Needs plan-time research. Jira Cloud REST v3 JQL label filter syntax, `jira>=3.10.5` `create_issue()` field map for priority + labels, and Jira Cloud vs Server/DC field schema differences should all be verified at planning time.

---

### Phase Ordering Rationale

- Phase 101 must come first: it is the only phase that can define the `NotificationChannel` ABC and security primitives that all subsequent phases inherit
- Phase 102 can run in parallel with Phase 101 but is grouped after because `POST /api/notifications/test` requires channel backends from Phase 101
- Phase 103 before Phase 104 because SIEM export is stdlib-only (zero risk of dep conflicts) and validates the `send_findings_export` pattern before Jira adds higher-complexity dedup logic
- Phase 104 last because it has the highest complexity (fingerprint dedup, JQL, QRAMM evidence threading, rate limiting) and benefits from Phase 101 delivery isolation and idempotency infrastructure

### Open Questions for Milestone Scoping

1. **Per-schedule vs. global notification config** — recommend global config in `quirk.toml` with per-schedule override columns as v5.3.x addition; confirm at Phase 101 planning
2. **Splunk HEC raw vs. event endpoint** — event endpoint (`/services/collector/event`) is simpler and more debuggable for <=hundreds of findings; confirm at Phase 103 planning
3. **httpx vs. urllib standardization** — research recommends `urllib.request` (already used in SSRF allowlist, no new dep); confirm at Phase 101 planning
4. **Jira vs. ServiceNow** — research clearly recommends Jira first; ServiceNow deferred to v5.4; confirm if there is an active ServiceNow customer commitment before Phase 104 planning

### Research Flags

Phases needing deeper research during planning:
- **Phase 103 (SIEM):** Splunk HEC raw vs. event endpoint batching strategy — verify against current Splunk docs
- **Phase 104 (Ticketing):** Jira Cloud REST v3 JQL label filter syntax; `jira>=3.10.5` `create_issue()` field map; Jira Cloud vs Server/DC schema differences

Phases with standard patterns (skip research phase):
- **Phase 101 (Anchor):** All patterns confirmed by direct source inspection; seam location pinned to line 162
- **Phase 102 (Auth UX):** Phase 58 is the template; `fastapi.security.APIKeyHeader` is in pinned dep

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions PyPI-verified 2026-05-24; integration points confirmed by direct source read; rejects confirmed by source analysis |
| Features | HIGH | Seam location confirmed by direct code inspection of `scheduler_cmd.py:109-163`; drift data model from `trends.py`; auth state from `auth.py` |
| Architecture | HIGH | All source files read directly; ABC design derived from existing `BrokerCredential.pass_env`, `optional_extra.py` REGISTRY patterns; no training-data inference |
| Pitfalls | HIGH | Every pitfall cross-referenced to existing project patterns and prior incidents (`pypdf` v4.10, Phase 59 LEAK-01) |

**Overall confidence: HIGH**

All four researchers read source files directly and cross-referenced against each other. Strong cross-researcher consensus on: Phase 101 as anchor, `NotificationChannel` ABC shape, `pass_env` secret indirection pattern, lazy import guard requirement, delivery isolation requirement, and Jira label-fingerprint dedup approach.

### Gaps to Address

- **Splunk HEC batching strategy** — event endpoint vs. raw endpoint; confirm at Phase 103 planning
- **Jira `create_issue()` field map** — labels + priority on Jira Cloud REST v3; confirm at Phase 104 planning via `jira>=3.10.5` docs
- **Per-schedule notify config scope** — confirm whether per-schedule overrides are in v5.3 or deferred to v5.3.x at Phase 101 planning
- **`integration_deliveries` table schema** — minimum fields: `scan_id`, `finding_hash`, `destination`, `status`, `attempted_at`, `error_summary`; define at Phase 101 plan time

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `quirk/cli/scheduler_cmd.py` lines 109-163 — seam location confirmed
- Direct code inspection: `quirk/intelligence/trends.py` — `TrendReport` dataclass + `compute_trend_report()` confirmed
- Direct code inspection: `quirk/dashboard/api/middleware/auth.py` — Phase 58 bearer auth + `hmac.compare_digest` confirmed
- Direct code inspection: `quirk/config.py` — `BrokerCredential.pass_env` secret pattern confirmed
- Direct code inspection: `quirk/util/optional_extra.py` — `REGISTRY`, lazy-import guard pattern confirmed
- `https://pypi.org/pypi/slack-sdk/json` — version 3.42.0 confirmed
- `https://pypi.org/pypi/jira/json` — version 3.10.5 confirmed
- `https://docs.splunk.com/Documentation/Splunk/latest/Data/UsetheHTTPEventCollector` — HEC endpoint confirmed
- `https://docs.python.org/3/library/smtplib.html` — stdlib SMTP confirmed
- Context7 `/slackapi/python-slack-sdk` — `WebhookClient` pattern confirmed
- Context7 `/pycontribs/jira` — `JIRA(basic_auth=...).create_issue(...)` pattern confirmed
- Context7 `/fastapi/fastapi` — `APIKeyHeader`, `HTTPBearer` confirmed
- Rapid7 InsightVM ticketing docs — Jira label fingerprint dedup (rediscovery + comment) pattern confirmed
- `src/dashboard/src/components/RegressionAlertChip.tsx` — regression threshold (score_delta <= -5 OR new_high > 0) confirmed

### Secondary (MEDIUM confidence)

- `https://api.slack.com/incoming-webhooks` — Slack incoming webhook URL format + rate limits
- `https://hookdeck.com/webhooks/platforms/guide-to-slack-webhooks-features-and-best-practices` — Block Kit `attachments` with `color` sidebar pattern
- `https://hookdeck.com/outpost/guides/outbound-webhook-retry-best-practices` — exponential backoff + jitter for webhook retry
- `https://defectdojo.com/blog/auto-triage-and-deduplicate-security-findings-to-reduce-alert-fatigue` — per-finding dedup strategy
- `https://community.developer.atlassian.com/t/rate-limiting-guide-for-jira-and-confluence/43360` — Jira Cloud rate limits (400 req/10 min)
- `https://blog.gitguardian.com/hmac-secrets-explained-authentication/` — HMAC-SHA256 webhook signature verification
- OWASP SSRF Prevention Cheat Sheet — DNS rebinding attack path
- Project memory: `feedback_optional_extra_import_trap.md` — `pypdf` v4.10 post-ship breakage (reference failure for Pitfall 5)
- Project memory: Phase 59 / LEAK-01 — credential leakage sweep; `safe_str()` origin

---
*Research completed: 2026-05-24*
*Ready for roadmap: yes*
