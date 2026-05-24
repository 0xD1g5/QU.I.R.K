# Stack Research — v5.3 Adoption & Integration Surface (ADDITIONS ONLY)

**Domain:** Outbound integrations for an existing Python 3.11+ crypto-scanner + FastAPI dashboard — notification fan-out, SIEM export, ticketing, and single-tenant dashboard auth
**Researched:** 2026-05-24
**Confidence:** HIGH (all versions verified against live PyPI JSON API; integration points confirmed from source files; auth patterns confirmed from existing quirk/dashboard/api/middleware/auth.py)

> This file covers ONLY stack additions/changes for v5.3. The full existing stack
> (sslyze, FastAPI + HTTPBearer auth, SQLite, React + shadcn/ui, cyclonedx-python-lib,
> croniter scheduler, TrendReport dataclass, etc.) is documented in PROJECT.md Key Decisions
> and is NOT repeated here.

---

## TL;DR — New Dependency Budget

| Extra group | New pip deps | Core impact |
|---|---|---|
| `[notify]` | `slack-sdk>=3.42.0` | ZERO — stdlib handles email + webhook |
| `[siem]` | none (stdlib only) | ZERO |
| `[tickets]` | `jira>=3.10.5` | ZERO |
| Dashboard auth | none (already shipped) | ZERO |

**Three new optional extras, one library each for Slack and Jira. Everything else is stdlib.**

---

## 1. Notification Fan-Out

### 1a. Slack

**Recommendation: `slack_sdk.webhook.WebhookClient` from `slack-sdk>=3.42.0`**

Use incoming webhooks (not the bot-token Web API) because:
- An incoming webhook URL is the only credential the operator needs — no Slack app OAuth dance, no workspace scopes, no bot user.
- `WebhookClient` wraps the single `POST https://hooks.slack.com/services/…` call with retry logic and Block Kit support. The raw call is 8 lines of `urllib`; the SDK adds nothing architecturally except Block Kit builder helpers and response assertion sugar.
- The alternative — bot token (`slack_sdk.WebClient`) — requires creating a Slack app, granting `chat:write` scope, and distributing an `xoxb-…` token. That is the right model when you need dynamic channel selection or multi-workspace support; neither applies here.
- Classic Incoming Webhooks (legacy, pre-2016 app model) are being sunset; the SDK's `WebhookClient` targets the current Slack app Incoming Webhook URL format, which is stable.

**Version:** `slack-sdk==3.42.0` (latest as of 2026-05-24, verified against `https://pypi.org/pypi/slack-sdk/json`)

**Auth:** Incoming webhook URL embeds a token — stored in `quirk.yml` under a new `notifications.slack_webhook_url` field. No separate header token. Treat it as a secret: never log it, redact with `safe_str()`.

**Optional extra:** `[notify]` — `slack-sdk>=3.42.0`

**Integration point:** Post-dispatch hook inside `_dispatch_schedule()` in `quirk/cli/scheduler_cmd.py`. After a scheduled run completes and `compute_trend_report()` returns a `TrendReport`, a `quirk.notify.slack` module serializes the report to a Block Kit message and calls `WebhookClient.send()`. If the webhook URL is not configured, the call is a no-op (graceful skip).

**DO NOT** pull in `slack-bolt` (event handling framework — irrelevant) or `slackclient` (legacy, deprecated).

---

### 1b. Email

**Recommendation: stdlib `smtplib` + `email` (Python 3.11 standard library) — ZERO new deps**

Why stdlib is sufficient:
- SMTP send is a straightforward `SMTP_SSL` or `SMTP` + `starttls()` + `login()` + `sendmail()` call with `email.mime.multipart.MIMEMultipart` for the message body. Python's `ssl.create_default_context()` gives TLS cert validation for free.
- Third-party libraries like `yagmail`, `flanker`, or `sendgrid` add features QU.I.R.K. does not need (templating engines, DKIM signing, campaign tracking). They would expand the minimal install for zero functional gain.
- Attachment support (appending an HTML report PDF) is handled by `email.mime.application.MIMEApplication` — no external dep.

**Auth:** SMTP username + password (or app password), stored as `notifications.email.smtp_user` / `notifications.email.smtp_password` in `quirk.yml`. For Office 365 / Google Workspace, the operator uses an app-specific password rather than account password.

**Ports / TLS:** `SMTP_SSL` for port 465; `SMTP` + `STARTTLS` for port 587 (recommended default). Both via stdlib. No STARTTLS stripping risk since QU.I.R.K. is the client, not the server.

**Optional extra:** none — ships inside core `[notify]` behaviour with zero additional deps.

---

### 1c. Generic Webhook (HTTP POST)

**Recommendation: stdlib `urllib.request` — ZERO new deps**

Why `urllib` not `requests`:
- A single outbound `POST` with a JSON body and `Authorization: Bearer <token>` header is 10 lines of `urllib.request.urlopen`. The existing codebase already uses `urllib` patterns (SSRF allowlist, HEC probe).
- Adding `requests` as a core or `[notify]` dep would bloat every install. The project's pattern is stdlib-first; `requests` is not currently a dependency.
- If the project ever adds `requests` for other reasons, the webhook module can trivially be rewritten — the interface stays the same.

**Auth:** Configurable. Common patterns: `Authorization: Bearer <token>`, `X-API-Key: <key>`, or `X-Signature-256: hmac-sha256(body)` (GitHub-style webhook verification). All are trivial with `urllib` and `hmac`.

**Optional extra:** none — zero new deps.

---

## 2. SIEM / Observability Export

**Recommendation: Splunk HEC via stdlib `urllib.request` — ZERO new deps**

Reasoning for choosing Splunk HEC over Elastic:
- Splunk HEC is a single HTTPS POST to `https://<host>:8088/services/collector/event`. The entire integration is `urllib.request.urlopen` with `Authorization: Splunk <token>` header and a JSON body. There is no pagination, no index management, no schema negotiation.
- The `elasticsearch` Python client (v9.4.0, verified) is a 400KB+ dependency that adds connection pooling, sniffing, and retry logic designed for high-volume indexing. For QU.I.R.K.'s use case — posting ≤hundreds of findings per scan — this is architectural overengineering.
- Splunk is overwhelmingly the dominant SIEM in enterprise security teams, which is QU.I.R.K.'s primary user segment.
- Generic Elastic export via the Elasticsearch REST API (`POST /<index>/_doc`) uses the same `urllib` pattern; a `[siem]` module can expose both Splunk HEC and Elastic bulk-index behind a unified `SiemExporter` interface with no new deps.

**Splunk HEC specifics:**
- Endpoint: `POST https://<host>:8088/services/collector/event`
- Auth: `Authorization: Splunk <hec-token>` header (HEC token, not a username/password)
- Payload: `{"time": <epoch>, "host": "<scanner host>", "sourcetype": "quirk:finding", "event": {...finding dict...}}`
- Batch endpoint: `POST .../services/collector` with newline-delimited JSON events for multi-finding flushes

**Elastic specifics (secondary path):**
- Endpoint: `POST https://<host>:9200/<index>/_doc` or bulk `/_bulk`
- Auth: `Authorization: ApiKey <base64(id:key)>` or `Authorization: Basic <base64(user:pass)>`
- No SDK required; same `urllib` pattern

**Syslog + CEF (tertiary path):**
- stdlib `logging.handlers.SysLogHandler` provides UDP/TCP syslog transport — zero deps.
- CEF formatting is a string template (`CEF:0|Vendor|Product|Version|SignatureID|Name|Severity|extension`). Implementing a `CefFormatter(logging.Formatter)` subclass is ~30 lines. No external CEF library needed — `syslogcef` / `cefevent` PyPI packages are not worth the dep.

**Optional extra:** none — stdlib only. A `[siem]` extras group is not needed. If the operator wants to use the Splunk or Elastic export, they configure the endpoint + token in `quirk.yml`; no additional `pip install` required.

---

## 3. Ticketing Integration

**Recommendation: `jira>=3.10.5` behind a `[tickets]` optional extra — ONE new dep**

Why the `jira` library over raw `urllib` REST:
- Jira Cloud REST API (v3) uses Basic auth with a user email + API token (not password). The `jira` library handles the `basic_auth=('user@domain.com', 'api_token')` contract, pagination, error surfacing, and `create_issue()` / field mapping cleanly. The raw REST equivalent requires constructing field maps, handling Jira's nested `{"project": {"key": "…"}, "issuetype": {"name": "…"}, …}` payload structure, and dealing with 400 error bodies that enumerate field validation failures — all repetitive boilerplate.
- The library is actively maintained (v3.10.5 released 2025-07-28, verified). It has no transitive conflicts with the existing dep tree (pure Python, no cryptography downgrade risk).
- For ServiceNow: ServiceNow's Table REST API (`POST /api/now/table/incident`) is straightforward enough that raw `urllib` is the right choice — no ServiceNow SDK needed. Auth is Basic (`Authorization: Basic base64(user:pass)`) or OAuth 2.0 bearer. Start with Basic since the operator is already managing API tokens for QU.I.R.K.

**Jira auth:** `basic_auth=('user@atlassian.net', '<api_token>')` where the API token is a Jira API token from `id.atlassian.com/manage-profile/security/api-tokens`, NOT the user password. Store in `quirk.yml` under `integrations.jira.api_token`.

**ServiceNow auth (if chosen as the one ticketing integration):** `Authorization: Basic base64(user:pass)` via `urllib`. Service account with `incident_manager` role minimum. Store credentials in `quirk.yml`.

**Which one to ship first:** Jira. It is more common in the security-team segment than ServiceNow, and the `jira` library eliminates the field-mapping boilerplate that makes ticket creation fragile. ServiceNow can be the "second ticketing integration" if adoption surfaces demand.

**Optional extra:** `[tickets]` — `jira>=3.10.5`. Zero `[all]` impact (add to `[all]` is fine — no transitive conflicts). QRAMM evidence attaches to the ticket body as structured text (finding dict + `evidence_summary` from `build_evidence_summary()`).

**Version:** `jira==3.10.5` (latest, PyPI-verified 2026-05-24)

---

## 4. Dashboard Team Auth

**Recommendation: NO new dependency — already fully shipped in Phase 58**

The bearer token auth required for v5.3 is already implemented:

- `quirk/dashboard/api/middleware/auth.py` — `require_auth()` FastAPI `Depends()` using `HTTPBearer(auto_error=False)` with constant-time `hmac.compare_digest()` comparison.
- Configured via `QUIRK_API_TOKEN` env var or `security.api_token` in `quirk.yml`.
- Applied as a router-level dependency to all `/api/…` routes.

The v5.3 work for "dashboard team auth" is therefore **documentation + UX**, not new code:
- Document the token-sharing workflow (`QUIRK_API_TOKEN=<shared-token> quirk serve`) in the operators guide.
- Add a `quirk token generate` CLI subcommand (uses `secrets.token_urlsafe(32)` — stdlib) to make token generation discoverable.
- Optionally add API key header support (`X-API-Key`) as an alternative to `Authorization: Bearer` for clients that can't set bearer headers (e.g., some webhook validators). `APIKeyHeader(name="X-API-Key")` from `fastapi.security` is a stdlib-equivalent zero-dep addition.

**Do NOT** add session cookies, JWT issuance, refresh tokens, or user tables. Those belong to the SaaS multi-tenant milestone (v5.4+), not single-tenant v5.3.

---

## 5. Optional Extras — Updated Grouping

```toml
[project.optional-dependencies]
# (existing extras unchanged — shown for context)
# ... dashboard, cloud, db, motion, email, broker, kafka, cbom, docx, identity, adcs, api ...

# NEW in v5.3:
notify = [
    "slack-sdk>=3.42.0",   # Slack incoming webhook delivery
    # email uses stdlib smtplib — no extra dep
    # generic webhook uses stdlib urllib — no extra dep
]

tickets = [
    "jira>=3.10.5",        # Jira Cloud + Server issue creation
    # ServiceNow uses stdlib urllib — no extra dep
]

# siem has ZERO new deps — Splunk HEC, Elastic, syslog/CEF all via stdlib
# No [siem] extras group needed; export is configured not installed

all = [
    # ... existing entries ...
    "quirk-scanner[notify]",   # safe to add — slack-sdk has no conflict risk
    "quirk-scanner[tickets]",  # safe to add — jira has no conflict risk
    # [api] remains excluded from [all] per v5.1-D-05
    # [identity] remains excluded from [all] per v4.6 D-01
]
```

---

## What NOT to Add

| Avoid | Why | Use Instead |
|---|---|---|
| `requests` library | Not currently a dep; adding it for webhook/HEC POST would bloat every install for 10 lines of code | `urllib.request` — already used for URL allowlist checks |
| `slack-bolt` | Slack event-handling framework; needed for slash commands / interactivity, not outbound notifications | `slack_sdk.webhook.WebhookClient` only |
| `slackclient` | Legacy v1 SDK, deprecated; PyPI page warns against use | `slack-sdk>=3.42.0` |
| `elasticsearch` Python client | 400KB+; connection pooling / sniffing overkill for ≤hundreds of findings per flush | `urllib.request` direct REST |
| `pyservicenow` / `servicenow-sdk` | Unofficial or early-stage ServiceNow Python wrappers; API surface unstable | `urllib.request` + Table REST API directly |
| JWT issuance / refresh tokens for dashboard auth | Implies server-side session state, token rotation, user model — SaaS scope, not single-tenant | Existing `HTTPBearer` + `QUIRK_API_TOKEN` (already shipped) |
| `sendgrid`, `yagmail`, `mailchimp-transactional` | Email API services with their own SaaS dependency; overkill for alert emails | `smtplib` + `ssl.create_default_context()` |
| `cefevent`, `syslogcef` PyPI packages | Thin wrappers around a string template; not worth a dep | 30-line `CefFormatter(logging.Formatter)` subclass using stdlib `logging.handlers.SysLogHandler` |
| `celery` / `rq` / `dramatiq` | Full async task queues; SaaS multi-tenant milestone scope, not v5.3 | Existing `quirk scheduler run` loop (`scheduler_cmd.py`) |

---

## Integration Points in the Existing Codebase

| v5.3 Feature | Hook Location | What Feeds It |
|---|---|---|
| Slack / email / webhook notifications | `_dispatch_schedule()` in `quirk/cli/scheduler_cmd.py` — post-run hook | `TrendReport` from `quirk/intelligence/trends.py` |
| SIEM export (Splunk/Elastic/CEF) | New `quirk export siem` CLI subcommand + optional post-scan hook in `run_scan.py` | `findings` dict + `ExecContent` from `build_exec_content()` |
| Jira ticket creation | New `quirk tickets create` CLI subcommand + optional post-scan flag | `findings` dict + `build_evidence_summary()` from `quirk/intelligence/evidence.py` |
| Dashboard API key auth (new `X-API-Key` path) | `quirk/dashboard/api/middleware/auth.py` — extend `require_auth()` to check `APIKeyHeader` | `QUIRK_API_TOKEN` env / `security.api_token` YAML (existing) |
| `quirk token generate` | New subcommand in `quirk/cli/` | `secrets.token_urlsafe(32)` (stdlib) |

---

## Version Compatibility

| Package | Version | Python | Conflict Risk |
|---|---|---|---|
| `slack-sdk` | `>=3.42.0` | 3.8+ | None — pure Python, no cryptography dep |
| `jira` | `>=3.10.5` | 3.10+ (matches project floor) | None — no pyOpenSSL/cryptography downgrade |
| `urllib.request` | stdlib | 3.11+ (project floor) | N/A |
| `smtplib` + `email` | stdlib | 3.11+ | N/A |
| `logging.handlers.SysLogHandler` | stdlib | 3.11+ | N/A |
| `fastapi.security.APIKeyHeader` | in `fastapi>=0.128.8` (already pinned in `[dashboard]`) | — | N/A |

---

## Sources

- `https://pypi.org/pypi/slack-sdk/json` — version 3.42.0 confirmed (HIGH confidence)
- `https://pypi.org/pypi/jira/json` — version 3.10.5 confirmed (HIGH confidence)
- `https://pypi.org/pypi/elasticsearch/json` — version 9.4.0 confirmed; rejected for this use case (HIGH confidence)
- Context7 `/slackapi/python-slack-sdk` — `WebhookClient` pattern confirmed (HIGH confidence)
- Context7 `/pycontribs/jira` — `JIRA(basic_auth=…).create_issue(…)` pattern confirmed (HIGH confidence)
- Context7 `/fastapi/fastapi` — `APIKeyHeader`, `HTTPBearer` security patterns confirmed (HIGH confidence)
- `https://docs.splunk.com/Documentation/Splunk/latest/Data/UsetheHTTPEventCollector` — HEC endpoint + `Authorization: Splunk <token>` header confirmed (HIGH confidence, last updated 2026-05-13)
- `https://docs.python.org/3/library/smtplib.html` — stdlib `smtplib` / `ssl.create_default_context()` confirmed (HIGH confidence)
- `https://docs.python.org/3/library/logging.handlers.html` — `SysLogHandler` UDP/TCP transport confirmed (HIGH confidence)
- `quirk/dashboard/api/middleware/auth.py` — Phase 58 bearer auth already complete; confirmed by source read (HIGH confidence)
- `quirk/pyproject.toml` — existing extras pattern (`[all]`, exclusion invariants) confirmed by source read (HIGH confidence)

---

*Stack research for: v5.3 Adoption & Integration Surface — outbound integrations additive to existing QU.I.R.K. Python scanner + FastAPI dashboard*
*Researched: 2026-05-24*
