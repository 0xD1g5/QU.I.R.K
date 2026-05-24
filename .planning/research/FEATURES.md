# Feature Research — v5.3 Adoption & Integration Surface

**Domain:** Outbound integrations for a Python CLI crypto-scanner + FastAPI dashboard
**Researched:** 2026-05-24
**Confidence:** HIGH (drift/scheduler infrastructure already built and read directly; integration patterns from official docs + verified community sources)

---

## Existing Infrastructure — What v5.3 Builds On

These are NOT new work. v5.3 wires into them:

| Piece | Where It Lives | What v5.3 Needs From It |
|-------|---------------|------------------------|
| `TrendReport` dataclass | `quirk/intelligence/trends.py` | Drift delta: `new_high`, `new_medium`, `new_low`, `score_delta`, `new_findings_sample`, `resolved_*` — already computed |
| `ScheduledRun` ORM row | `quirk/models.py` (Phase 63) | Post-run hook point: `status`, `completed_at`, `scan_id` all set by `_dispatch_schedule()` before returning |
| `ScheduledScan` ORM row | `quirk/models.py` (Phase 63) | Per-schedule notification routing config — currently has no notification columns; schema must grow additively |
| `_dispatch_schedule()` in `scheduler_cmd.py` | `quirk/cli/scheduler_cmd.py` | Call-site for the post-run hook; returns `ScheduledRun`; the gap is there is NO call to `compute_trend_report()` here |
| `require_auth` / bearer token | `quirk/dashboard/api/middleware/auth.py` (Phase 58) | Single-user bearer already ships; v5.3 auth work is additive only (X-API-Key header + rotation CLI) |
| Finding model + QRAMM evidence | `quirk/engine/findings_evaluator.py` + `quirk/qramm/evidence_bridge.py` | Jira/SIEM export reads individual findings + QRAMM maturity dimension scores |
| `ExecContent` / `build_exec_content` | `quirk/reports/exec_content.py` (Phase 98) | `score_total`, `score_band`, subscores, top risks — canonical content model to pull score data from |

**Critical gap confirmed by code inspection:** `scheduler_cmd.py::_dispatch_schedule()` completes a `ScheduledRun`, commits to DB, and returns. There is no subsequent call to `compute_trend_report()`. The `TrendReport` dataclass and delta computation exist but are never invoked from the scheduler loop. This is the "half-built" state HORIZON describes — the data model is done, delivery is absent.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a tool of this class must provide. Missing any makes the milestone feel incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Drift-triggered Slack notification | Any scheduling tool that runs silently is invisible. Slack is the de facto SecOps async channel in enterprise and consultancy settings | MEDIUM | Incoming Webhook URL is the standard surface — no OAuth app, no bot token, no workspace admin approval. Block Kit `attachments` give structured layout with color coding by severity. |
| Drift-triggered email notification | Required for orgs without Slack; SMTP is universally available and often required by security policy for compliance-relevant events | MEDIUM | Python stdlib `smtplib` + `ssl.create_default_context()` — zero new pip deps; configurable SMTP host/port/TLS mode/auth |
| "Do nothing when nothing changed" behavior | Firing on every scan regardless of findings is alert fatigue by design; teams will mute the channel within a week | LOW | Gate delivery on `new_high > 0 OR new_medium > 0 OR score_delta <= threshold`; skip silently when nothing is actionable |
| Per-finding Jira ticket creation | Security teams expect a remediation loop; a finding that lives only in QUIRK's reports is often never acted on | HIGH | Jira REST API `POST /rest/api/3/issue`; dedup against existing open tickets by label fingerprint |
| Notification credentials in config / env vars | Webhook URLs, SMTP passwords, Jira API tokens must be configurable without code changes | LOW | Follow existing `QUIRK_API_TOKEN` env-var pattern from Phase 58; add `[notifications]` TOML section |
| Dashboard API-key header variant | Teams using `curl` or scripts want `X-API-Key: <token>` without the `Authorization: Bearer` boilerplate | LOW | Two-line addition to `auth.py`; same constant-time compare, same `QUIRK_API_TOKEN` value |
| `quirk token rotate` CLI | Static shared tokens need a rotation mechanism so a compromised token can be invalidated and replaced | LOW | Generate cryptographically random 32-byte base64url token, print once to stdout, update `quirk.toml` |

### Differentiators (Competitive Advantage)

Features that distinguish QU.I.R.K. from generic scanners sending plain-text alerts.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Score band + subscore delta in Slack messages | Show `Readiness: 62 FAIR (−8 from last scan)` with finding bucket counts — not just "N new findings". Security leaders recognize score regression immediately | LOW | `ExecContent.score_total` + `score_band` already built; format as Block Kit section fields |
| QRAMM maturity evidence in Jira tickets | A Jira ticket from most scanners carries only a CVE reference. A QUIRK ticket carries the QRAMM dimension score (e.g., "Algorithm Agility: 1.2/4.0 INITIAL") — actionable governance context a security team can cite in a sprint | MEDIUM | `evidence_bridge.py` already exposes dimension scores; map selected QRAMM fields into ticket description body |
| Splunk HEC export — one SIEM push | Puts QUIRK findings directly in the security team's primary triage surface; reduces "check yet another tool" friction for enterprise customers | HIGH | Single POST endpoint, per-finding JSON events batched per scan; `sourcetype: quirk:finding`; one extra pip dep (`requests` already present via sslyze/httpx) |
| Generic outbound webhook | Any downstream system that speaks JSON-over-HTTPS (PagerDuty, Teams, Opsgenie, custom SIEM) can receive drift events — extends reach without maintaining N individual integrations | MEDIUM | Standard `POST` with `Content-Type: application/json`; HMAC-SHA256 `X-QUIRK-Signature` header so consumers can verify authenticity |
| Configurable trigger threshold | Notify only when `score_delta <= -5` or `new_high >= 1` — mirrors Alertmanager severity routing conventions; gives operators control over signal vs. noise | LOW | Per-schedule `notify_threshold` column; sensible defaults (CRITICAL/HIGH always fire; MEDIUM and LOW off by default) |
| Finding fingerprint dedup for Jira | Prevents "100 tickets for the same weak TLS cipher after 100 scheduled scans" — the failure mode that makes security teams disable auto-ticketing everywhere | MEDIUM | Fingerprint = SHA256(`host:port:protocol:finding_category`); store as Jira label `quirk-fp-<hash>`; JQL search before creating |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Notify on every scan completion (not just drift) | "I want to know QUIRK ran" | Creates a heartbeat-disguised-as-notification channel; alert fatigue in days; security teams mute it | Use the dashboard `/schedules` page and `ScheduledRun.status` for heartbeat visibility; reserve notifications for meaningful drift |
| One Jira ticket per scan (not per finding) | "Keep it simple" | A single ticket for "30 findings across 8 hosts" has no assignee, no acceptance criteria, no done condition | One ticket per `(finding_category, host, port)` tuple, deduped; a scan-level summary comment on existing tickets |
| ServiceNow as the first/only ticketing integration | "We use ServiceNow" | ServiceNow REST API requires a live instance for dev/test (no public sandbox), complex OAuth2 + refresh flow, and custom table configuration — high first-phase cost with no testable target | Ship Jira first (free cloud sandbox, simpler auth, wider adoption in security teams); ServiceNow as a v5.4 backlog item |
| Real-time websocket push on scan findings | "I want live updates" | Requires persistent connection from QUIRK to external systems; incompatible with the local/offline consulting-deploy model | Poll-based or post-completion push from the scheduler hook is the right model for this single-tenant architecture |
| Multi-channel fan-out per event (Slack + email + webhook simultaneously) | "Notify everywhere" | Combinatorial config complexity; if one channel fails, partial-delivery semantics are confusing; every additional channel multiplies the test surface | Per-schedule single primary channel; a schedule owner can configure one channel; adding multi-channel fan-out is a v5.4 backlog item once v5.3 validates demand |
| SIEM bidirectional sync (pull findings from SIEM back into QUIRK) | "Close the loop from SIEM" | Requires inbound webhook or polling from SIEM to QUIRK; adds an inbound attack surface and depends on SIEM vendor cooperation | Push-only in v5.3; inbound event handling defers to v5.4/SaaS milestone |
| Store raw webhook payloads or response bodies in SQLite | "For debugging" | Payloads can contain Slack webhook URLs (secrecy-only auth model), SMTP passwords in error traces, or Jira API tokens | Log delivery status (delivered/failed/retried) and HTTP response status code only; never log payload body; follow the `safe_str()` pattern already in place |
| Elastic/OpenSearch as the v5.3 SIEM export | "We use Elastic" | Elastic requires an `elasticsearch-py` client dep, an index template + ILM policy, and cluster credentials with index write permission — significantly more setup than Splunk HEC for the same signal | Ship Splunk HEC first to validate the SIEM export pattern; Elastic export is a v5.4 add once HEC proves the shape |

---

## Feature Dependencies

```
[scheduler: ScheduledRun.completed_at set] (EXISTING — scheduler_cmd.py:_dispatch_schedule)
    └──triggers──> [post-run hook: compute_trend_report(current_ts, previous_ts, db)] (NEW — wire in scheduler_cmd.py)
                       └──feeds──> [notification routing decision] (NEW)
                                       └──requires──> [notify_channel + notify_endpoint columns on ScheduledScan] (NEW — additive migration)
                                       └──requires──> [configured trigger threshold] (NEW — column or config default)
                                       └──routes to──> [Slack delivery: POST Incoming Webhook URL] (NEW)
                                       └──routes to──> [email delivery: smtplib SMTP/STARTTLS] (NEW)
                                       └──routes to──> [generic webhook delivery: POST JSON + HMAC sig] (NEW)
                       └──feeds independently──> [Splunk HEC export: batch per-finding POST] (NEW — separate from notification router)

[finding model: CryptoEndpoint rows for scan_id] (EXISTING)
    └──feeds──> [Jira ticket body builder] (NEW)
                    └──requires──> [finding fingerprint: SHA256(host:port:protocol:category)] (NEW)
                    └──requires──> [JQL dedup search: labels = quirk-fp-<hash> AND status != Done] (NEW)
                    └──attaches──> [QRAMM evidence: evidence_bridge dimension scores] (EXISTING)

[require_auth: QUIRK_API_TOKEN bearer check] (EXISTING — auth.py Phase 58)
    └──extends to──> [X-API-Key header accepted equivalently] (NEW — 2-line addition to auth.py)
    └──adds──> [quirk token generate / quirk token rotate CLI] (NEW — standalone)
```

### Dependency Notes

- **Post-run hook is the load-bearing seam.** `_dispatch_schedule()` already returns a `ScheduledRun`. Adding `compute_trend_report(current_ts=run.dispatched_at, previous_ts=<prior run's dispatched_at>, db=db)` immediately after the commit is the minimal wiring. `previous_ts` is derived by querying the most recent prior `ScheduledRun` for the same `schedule_id`.
- **Notification routing requires two new columns on `ScheduledScan`**: `notify_channel` (enum string: slack/email/webhook/splunk/none) and `notify_endpoint` (URL or email address). These are additive-only SQLite migrations matching the existing `additive-only` schema constraint in PROJECT.md.
- **Splunk HEC is intentionally separate from the notification router.** Notification fan-out is a per-drift-event async push; SIEM export is a per-scan per-finding batch push with different shape and trigger. Design them as independent delivery targets that can coexist.
- **Jira dedup has no native Jira-side idempotency key.** The label-fingerprint approach (store `quirk-fp-<sha256>` as a Jira label, JQL-search before creating) is the industry-standard pattern used by Rapid7 InsightVM and Harness STO. It adds one round-trip per finding but is the only reliable dedup path without a QUIRK-side ticket registry.
- **Dashboard auth extensions are independent of all other v5.3 features.** Neither blocks nor enables notification work; can be in any phase.

---

## Anchor: Notification Fan-Out — Minimal Must-Ship Core

HORIZON is explicit: finish notification fan-out first as the anchor before adding SIEM or ticketing breadth. This is the minimal shippable core:

**Must ship (anchor core — finish before anything else):**
1. Post-run hook in `scheduler_cmd.py` that calls `compute_trend_report()` after `_dispatch_schedule()` completes and the `ScheduledRun` row is committed
2. Trigger decision: fire if `new_high > 0` OR `new_medium > 0` OR `score_delta <= configured_threshold` (default: −5); skip (no-op) when nothing actionable
3. Slack delivery: `POST` to Incoming Webhook URL with a Block Kit message carrying schedule name, score delta, score band, new finding counts by severity, and a dashboard link
4. Config: `QUIRK_SLACK_WEBHOOK` env var (primary); `[notifications.slack] webhook_url` in `quirk.toml` (fallback); consistent with Phase 58 env-var-wins pattern
5. Dedup guard: store SHA256 of the last-delivered `TrendReport` summary in `ScheduledScan.last_notify_hash`; skip delivery if hash matches previous delivery (prevents double-fire when scheduler restarts)

**Add after Slack validates the pattern:**
- Email delivery (SMTP; same trigger logic; stdlib-only)
- Generic outbound webhook (POST JSON; HMAC-SHA256 signature)
- Splunk HEC export (independent of notification fan-out; separate batch delivery target)
- Jira auto-ticket (highest complexity; gates on finding model access + dedup design)

**Explicitly not in anchor core:**
- Retry queue with SQLite persistence (use synchronous retry, 3 attempts, exponential backoff, log failure; full dead-letter queue is v5.4)
- Per-finding Slack threads (per-scan summary is the right notification granularity)
- ServiceNow integration
- Elastic/OpenSearch SIEM export

---

## Integration Behavior Reference

### Notification Fan-Out — Trigger Logic

**Trigger on:** any new CRITICAL or HIGH finding (not seen in previous session by match key), OR score delta <= configured floor (default: −5), OR new MEDIUM findings if `notify_medium: true` (default: false to avoid medium-noise fatigue)

**Do not trigger on:** score delta = 0 with no new findings of any severity; INFO-only findings; scan errors (already surfaced in the dashboard `ScannerStatusCard`); first-ever scan for a schedule (no previous session to compare against)

**Dedup guard:** SHA256 of `(schedule_id, current_session_ts.isoformat(), new_high, new_medium, new_low, score_delta)` stored in `ScheduledScan.last_notify_hash`; skip delivery if hash matches — prevents re-firing if scheduler restarts before the next scheduled run

**Retry behavior:** synchronous, 3 attempts, exponential backoff (1s, 4s, 16s) with ±20% jitter; on exhaustion write `notify_status = 'failed'` to `ScheduledRun`; do NOT raise — must not crash the scheduler loop; 4xx errors (except 429) are non-retriable (malformed payload or auth failure — retrying won't help)

### Slack Message Shape

Block Kit structure (use `attachments` with `color` for severity-coded sidebar):

- **Header:** `":warning: QUIRK Drift Alert — <schedule_name>"`
- **Score line:** `Readiness: <score> <band> (<+/−delta> from last scan)`
- **Finding fields:** `New HIGH/CRITICAL: N` | `New MEDIUM: N` | `Resolved: N`
- **Sample findings (up to 3):** `host:port — protocol — severity` (from `TrendReport.new_findings_sample`)
- **Actions block:** "View Trends" button linking to `<dashboard_base_url>/trends`
- `color` field: red for `new_high > 0` or `score_delta < −10`; yellow for `new_medium > 0` or `score_delta < 0`; green for all-resolved

**Not in the Slack message:** raw finding descriptions, QRAMM dimension scores, remediation text (those belong in the Jira ticket, not a channel notification; channel messages should be scannable in 5 seconds)

### Email Message Shape

- **Subject:** `[QUIRK] Drift alert — <schedule_name> — Readiness: <score> <band>`
- **Body:** plaintext summary matching Slack content; optional HTML MIME part reusing the executive summary layout from `ExecContent`
- No report attachments in the default path — attachment mode (PDF report) is a v5.4 differentiator

### Generic Outbound Webhook Payload

```json
{
  "event": "scan.drift",
  "schedule_name": "<name>",
  "scan_id": "<uuid>",
  "scanned_at": "<ISO-8601 UTC>",
  "score": { "current": 62, "previous": 70, "delta": -8, "band": "FAIR" },
  "findings_delta": { "new_high": 2, "new_medium": 1, "new_low": 0, "resolved_high": 0 },
  "new_findings_sample": [
    { "host": "10.0.0.1", "port": 443, "protocol": "TLS", "severity": "HIGH" }
  ],
  "dashboard_url": "<configured base URL>/trends"
}
```

**Signature header:** `X-QUIRK-Signature: sha256=<HMAC-SHA256(body, configured_secret)>` — allows consumers to verify authenticity; configured via `QUIRK_WEBHOOK_SECRET` env var or `[notifications.webhook] secret` in `quirk.toml`

### Splunk HEC Event Shape

Endpoint: `POST https://<splunk_host>:8088/services/collector/event`
Auth header: `Authorization: Splunk <HEC_TOKEN>`
Batching: all findings from one scan in one request body (newline-delimited JSON events); max 200 events per batch; split larger scans into multiple requests

Per-finding event:
```json
{
  "time": 1716556800.0,
  "sourcetype": "quirk:finding",
  "source": "quirk-scanner",
  "host": "<scanner hostname>",
  "event": {
    "schedule_name": "<name>",
    "scan_id": "<uuid>",
    "target_host": "<scanned host>",
    "port": 443,
    "protocol": "TLS",
    "severity": "HIGH",
    "finding_category": "weak-cipher",
    "finding_title": "Weak cipher suite accepted",
    "remediation": "Disable RC4 and 3DES; require TLS 1.2+ with ECDHE cipher suites",
    "quantum_safe": false,
    "qramm_maturity_band": "DEVELOPING"
  }
}
```

**CEF syslog alternative** (for orgs not using HEC): `CEF:0|QUIRK|quirk-scanner|<version>|<finding_category>|<finding_title>|<sev_int>|src=<host> spt=<port> proto=<protocol>` — only implement if an explicit user request surfaces; Splunk HEC is the primary path.

### Jira Ticket Shape

**Granularity:** one ticket per `(finding_category, host, port)` tuple — not per scan, not per severity bucket

**Dedup check before create:** JQL `project = <project_key> AND labels = "quirk-fp-<sha256(host:port:protocol:category)>" AND status NOT IN (Done, Resolved, Closed)` — if found, add comment "Rediscovered by QUIRK scan `<scan_id>` on `<YYYY-MM-DD>`"; do not create a new ticket

**Fields on create:**
- `summary`: `[QUIRK] <finding_title> — <host>:<port>`
- `description`: finding description + quantum-risk "so what" (from `ALGO_IMPACT_MAP`) + weakness-specific remediation (from `REMEDIATION_CATALOG`) + QRAMM maturity dimension score if available
- `priority`: CRITICAL → Highest, HIGH → High, MEDIUM → Medium, LOW → Low
- `labels`: `["quirk", "crypto-debt", "quirk-fp-<sha256>", "quirk-last-seen-<YYYYMMDD>"]`

**Auth model:** Jira API token via Basic auth (`email:api_token` base64-encoded); Jira Cloud REST v3 only in v5.3; Jira Server/DC and ServiceNow deferred

**Rate limiting:** Jira Cloud enforces per-user rate limits; send tickets serially (not in parallel); stay under 10 req/s to avoid 429

### Dashboard Auth Extensions (v5.3 scope)

The Phase 58 bearer token is already in production. v5.3 changes are strictly additive — no existing behavior changes:

1. `X-API-Key: <token>` accepted as equivalent to `Authorization: Bearer <token>` — constant-time compare against the same `QUIRK_API_TOKEN` value; two-line addition to `auth.py`
2. `quirk token generate` CLI: generate a cryptographically random 32-byte `secrets.token_urlsafe()` token, print once to stdout, write to `quirk.toml` `security.api_token`
3. `quirk token rotate` CLI: same as generate + update config; no dual-key grace period needed (single-user single-tenant; disrupting in-flight sessions is acceptable)

**Explicitly out of scope for v5.3 auth:** per-user API keys, per-scope tokens, token expiry, JWT-based session tokens — those belong to the SaaS multi-tenant milestone (v5.4+)

---

## MVP Definition for v5.3

### Launch With (Required for Milestone)

- [ ] Post-run notification hook wired in `scheduler_cmd.py` — triggers `compute_trend_report()` after every `ScheduledRun` completes
- [ ] Trigger guard — no-op when `new_high == 0 AND new_medium == 0 AND abs(score_delta) < threshold`
- [ ] Slack delivery — Block Kit message with score delta, band, finding counts by severity, dashboard link
- [ ] Email delivery — MIME plaintext+HTML via `smtplib`; configurable SMTP host/port/TLS/auth; zero new pip deps
- [ ] Generic outbound webhook delivery — JSON POST with HMAC-SHA256 signature header
- [ ] Splunk HEC export — per-finding JSON events batched per scan; `sourcetype: quirk:finding`
- [ ] Jira auto-ticket — one ticket per `(finding_category, host, port)`; fingerprint dedup via JQL; QRAMM evidence in description
- [ ] Dashboard `X-API-Key` header support — additive to Phase 58 bearer auth
- [ ] `quirk token generate` + `quirk token rotate` CLI commands

### Add After Validation (v5.3.x)

- [ ] Configurable per-schedule trigger threshold (`notify_threshold` column) — add after first user reports notification fatigue with defaults
- [ ] Retry with `ScheduledRun.notify_status` delivery log — add when at-least-once delivery guarantee becomes a stated requirement
- [ ] Jira auto-close / comment-on-resolve — add when security teams report needing remediation confirmation loop
- [ ] ServiceNow ticketing — add when v5.3 Jira validates the ticketing pattern and a ServiceNow user is identified

### Future Consideration (v5.4+)

- [ ] Elastic/OpenSearch SIEM export — Splunk HEC validates the SIEM pattern first
- [ ] Inbound webhook from SIEM (bidirectional sync) — requires inbound attack surface design; SaaS milestone
- [ ] Multi-channel fan-out per schedule — not validated by v5.3; adds config complexity
- [ ] SQLite-backed dead-letter queue for failed deliveries — SaaS-milestone-level reliability requirement

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Post-run hook + trigger guard | HIGH | LOW (wiring `compute_trend_report()` into existing call site) | P1 |
| Slack delivery | HIGH | LOW | P1 |
| Email delivery | HIGH | LOW (stdlib smtplib, zero new deps) | P1 |
| Generic webhook delivery | MEDIUM | LOW | P1 |
| Splunk HEC export | HIGH (enterprise users) | MEDIUM | P1 |
| Jira auto-ticket with fingerprint dedup | HIGH | HIGH | P1 |
| Dashboard X-API-Key header | MEDIUM | LOW (2-line auth.py change) | P1 |
| `quirk token rotate` CLI | MEDIUM | LOW | P1 |
| Configurable threshold | MEDIUM | LOW | P2 |
| SQLite-backed delivery log + retry | MEDIUM | MEDIUM | P2 |
| Jira auto-close on resolved | MEDIUM | MEDIUM | P2 |
| ServiceNow ticketing | LOW for v5.3 | HIGH | P3 |
| Elastic SIEM export | LOW for v5.3 | HIGH | P3 |

**Priority key:** P1 = must ship in v5.3; P2 = should ship v5.3.x after validation; P3 = backlog / v5.4+

---

## Sources

- Direct code inspection: `quirk/cli/scheduler_cmd.py`, `quirk/intelligence/trends.py`, `quirk/dashboard/api/middleware/auth.py`, `quirk/dashboard/api/routes/schedules.py`, `quirk/models.py`
- `.planning/HORIZON.md` v5.3 section — "finish notification fan-out first as the anchor"
- `.planning/PROJECT.md` v5.3 milestone scoping
- [Slack Incoming Webhooks — Official Docs](https://api.slack.com/incoming-webhooks) — HIGH confidence
- [Slack security best practices](https://api.slack.com/authentication/best-practices) — HIGH confidence
- [Guide to Slack Webhooks — Hookdeck](https://hookdeck.com/webhooks/platforms/guide-to-slack-webhooks-features-and-best-practices) — MEDIUM confidence
- [Format events for HTTP Event Collector — Splunk Docs](https://docs.splunk.com/Documentation/Splunk/latest/Data/FormateventsforHTTPEventCollector) — HIGH confidence (official, 2026-01)
- [CEF Introduction — Splunk Blog](https://www.splunk.com/en_us/blog/learn/common-event-format-cef.html) — HIGH confidence
- [Elastic Security ECS field reference](https://www.elastic.co/guide/en/security/8.19/siem-field-reference.html) — HIGH confidence
- [Jira Cloud REST API — Create Issue](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/) — HIGH confidence (official)
- [Auto-Triage and Deduplicate Security Findings — DefectDojo Blog](https://defectdojo.com/blog/auto-triage-and-deduplicate-security-findings-to-reduce-alert-fatigue) — MEDIUM confidence
- [Rapid7 InsightVM ticketing — rediscovery + comment pattern](https://docs.rapid7.com/insightvm/ticketing-integration-for-remediation-workflow-projects/) — HIGH confidence (official)
- [Webhook retry best practices — Hookdeck](https://hookdeck.com/outpost/guides/outbound-webhook-retry-best-practices) — MEDIUM confidence
- [HMAC secrets explained — GitGuardian](https://blog.gitguardian.com/hmac-secrets-explained-authentication/) — MEDIUM confidence
- [Python smtplib — Official Docs](https://docs.python.org/3/library/smtplib.html) — HIGH confidence

---
*Feature research for: QU.I.R.K. v5.3 Adoption & Integration Surface*
*Researched: 2026-05-24*
