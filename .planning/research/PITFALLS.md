# Pitfalls Research

**Domain:** Outbound notification/SIEM/ticketing integrations + dashboard auth on a Python CLI security scanner (QU.I.R.K. v5.3)
**Researched:** 2026-05-24
**Confidence:** HIGH — every pitfall verified against existing project code patterns and official sources

---

## Critical Pitfalls

### Pitfall 1: SSRF via User-Configured Outbound URLs (Webhook / Splunk HEC / Jira / SMTP Relay)

**What goes wrong:**
An operator configures a webhook URL, Splunk HEC endpoint, or Jira base URL pointing at an internal service (e.g., `http://169.254.169.254/latest/meta-data/`, `http://10.0.0.5:8080/admin`, or a hostname that DNS-resolves to RFC1918 space). When QU.I.R.K. fires a notification after a scheduled-scan drift event, the outbound HTTP client dutifully fetches that internal URL — exfiltrating cloud IAM credentials or probing internal APIs. This is the same attack class already hardened in v5.1 OpenAPI scanner (`$ref`-SSRF) and the SAML URL allowlist (Phase 57).

**Why it happens:**
Integration URLs are typically operator-supplied via the YAML config file (e.g., `notifications.webhook_url`, `siem.hec_url`, `ticketing.jira_base_url`). Without the same validation applied to scan targets, every new outbound fetch site is an SSRF entry point. DNS rebinding adds a second dimension: even a URL that passes allowlist validation at config-load time can be re-pointed to an internal IP by the time the HTTP request fires (TTL expiry between validate-time and fetch-time).

**How to avoid:**
Re-use `quirk.util.url_allowlist.validate_external_url()` — the existing function already handles RFC1918, loopback, link-local, and cloud metadata IPs (`169.254.169.254`, `fd00:ec2::254`). Call it at **two** points: (1) config validation at `quirk serve` / `quirk schedule` startup; (2) immediately before each outbound HTTP call. Do NOT rely solely on config-time validation — DNS rebinding between config load and delivery is a real attack path. The existing helper returns a typed `ValidationResult` — on `ok=False`, log only `result.redacted_preview`, never the raw URL, and abort the delivery attempt (not the scan run). For webhook/HEC/Jira, also enforce `https://` only (the existing `_ALLOWED_SCHEMES` frozenset handles this). Never follow HTTP redirects that lead to internal IPs — disable redirect following or re-validate each redirect target.

**Warning signs:**
- Any new `httpx.get(url)` / `requests.post(url)` call where `url` sources from config or user input without a preceding `validate_external_url()` call.
- A `SSRF_ALLOW_INTERNAL` or `--allow-internal-targets` flag being applied to integration URLs (that flag is for scanner targets, not notification delivery).
- Integration tests that hardcode `http://localhost` as the webhook URL without a test-mode bypass that is never activated in production.

**Phase to address:**
Phase 101 (notification fan-out) — must implement before the first outbound delivery call. Shared allowlist utility already exists; applying it is a wiring task.

---

### Pitfall 2: Secret Leakage — Bot Tokens, SMTP Creds, and HEC Tokens in Logs / Error Messages / Persisted State

**What goes wrong:**
A Slack bot token (`xoxb-...`), SMTP password, Splunk HEC token, or Jira API token appears in:
- A `scan_error` column in SQLite (if `str(exc)` includes the credential in the exception message from a failed HTTP call)
- A log line emitted before or after a failed delivery
- The `quirk doctor` health-check output that surfaces connection errors
- The persisted config YAML if the user pastes the token directly into `quirk.toml`

This is the same failure mode that drove the v4.8 Phase 59 credential leakage sweep: `safe_str()` was built precisely because exception messages from scanners like `hvac` and cloud SDKs were including auth tokens in their text.

**Why it happens:**
HTTP client libraries (httpx, requests, aiohttp) often include the full request URL (with query-param tokens), response headers, or auth headers in their exception text. `ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))` is safe; `HTTPError: 401 Unauthorized — URL: https://hooks.slack.com/services/T.../B.../xyz... — Headers: {Authorization: Bearer xoxb-...}` is not. The existing `safe_str()` regex battery already catches base64-shaped tokens ≥ 40 chars, `Authorization: Bearer` patterns, and `X-Api-Key` header shapes — but Splunk's `Authorization: Splunk <token>` header shape and SMTP `smtplib.SMTPAuthenticationError` messages (which embed `535 5.7.8 Username and Password not accepted`) need explicit coverage.

**How to avoid:**
- Extend `_SENSITIVE_PATTERNS` in `quirk/util/safe_exc.py` to cover: Splunk HEC token shape (`Authorization: Splunk\s+\S+`), SMTP auth failure messages embedding credentials, and Slack bot token prefix (`xoxb-`, `xoxp-`).
- Wrap every outbound delivery attempt in `safe_str(exc)` before writing to `scan_error` or any log sink — the same discipline as the Phase 59 scanner callsites.
- Integration tokens stored in the YAML config must be treated as credential material: when `quirk doctor` checks connectivity, it must never echo the token value — log `[configured]` vs `[not configured]` only.
- Store integration tokens via env var first (`QUIRK_SLACK_TOKEN`, `QUIRK_HEC_TOKEN`, etc.), YAML config second. The existing `_get_configured_token()` pattern in `auth.py` is the model to replicate for each integration.
- Never log the raw `webhook_url`, `hec_url`, or `jira_base_url` from config in debug output — these URLs often embed tokens as path components (Slack incoming webhooks embed the token in the URL path itself: `hooks.slack.com/services/T.../B.../secret`).

**Warning signs:**
- `scan_error` column contains a string ≥ 40 alphanumeric characters (existing AST gate looks for raw exception writes — same gate must cover integration delivery paths).
- The `quirk doctor` connectivity check prints the raw integration URL.
- A new `except Exception as e: log.error(str(e))` callsite in any integration module.

**Phase to address:**
Phase 101 (anchor: notification fan-out). Extend `safe_str` in the same phase. Do not defer secret-leakage hardening to a later phase — once tokens are in SQLite they are hard to redact.

---

### Pitfall 3: Sensitive Finding Data Exfiltrated to Third-Party Integrations

**What goes wrong:**
A Jira ticket created per-finding includes the raw cert PEM, private key material (if QU.I.R.K. ever surfaces one), full CBOM JSON blob, or internal hostnames / IP addresses of the scanned target in the ticket description. The same data lands in a Slack notification body or SIEM event. This data now lives in a third-party SaaS outside the operator's control — a problem if:
- The scanned organization is a QU.I.R.K. consulting customer (confidentiality obligation)
- Jira / Slack / Splunk is shared across teams or organizations
- The CBOM contains algorithm inventory details about internal PKI that are themselves sensitive

**Why it happens:**
When building a "rich" integration, developers include all available context to make tickets/alerts actionable. A `Finding` object in QU.I.R.K. carries `service_detail` (which can include `host:port:path` specifics), `raw_evidence` JSON, and sometimes cert chain data. Dumping the full object into a Jira description or Slack block is tempting and common.

**How to avoid:**
Define an explicit **integration payload schema** for each channel — a whitelist of fields that MAY be included. Safe to send: severity, finding category/title, recommendation text, score impact, scan timestamp, a local scan-ID reference (not the full CBOM). Requires care: target hostnames/IPs (operator must opt-in). Never send: raw certificate PEM or DER bytes, CBOM JSON blobs, internal PKI topology details, `tls_capabilities_json` raw data, full `raw_scan_json` columns, any field passing through `safe_str` scrubbing. Implement a `to_integration_payload(finding, *, include_host=False)` canonical method so all integrations pull from the same sanitized shape rather than each independently cherry-picking fields.

**Warning signs:**
- Any integration serializer doing `**finding.__dict__` or `finding.to_dict()` without field filtering.
- CBOM writer output being attached as a Jira attachment.
- Slack notification body exceeding ~500 characters (a sign more data than needed is included).

**Phase to address:**
Phase 102 (SIEM export) and Phase 103 (ticketing) — define `to_integration_payload()` in Phase 101 as a shared primitive and enforce its use in all subsequent integration phases.

---

### Pitfall 4: Notification Storm / No Throttling / Retry Amplification

**What goes wrong:**
QU.I.R.K. runs a scheduled scan against a target with 200 findings. All 200 fire as individual Slack messages or Jira tickets within 30 seconds. Slack rate-limits the bot (Tier 1: 1 msg/sec; Tier 2: 20 msg/min per channel); messages start getting 429 errors. The retry logic has no backoff and no jitter — it immediately requeues all 200 failed deliveries. Each retry batch triggers more 429s. Slack temporarily deactivates the webhook. Jira creates duplicate tickets on the next attempt because idempotency keys were not tracked.

**Why it happens:**
Notification integrations are commonly built "per-finding-event" without thinking about fan-out. Scheduled scans can produce large finding sets. API rate limits from Slack (tier-dependent), Jira (400 req/10 min for REST v2 cloud), and Splunk HEC (token-level throughput limits) are real operational constraints that are invisible until production traffic arrives.

**How to avoid:**
- Deliver **drift summaries, not per-finding blasts**: the scheduler already emits drift events (finding deltas since the last scan). A single "N new findings, M resolved" summary message with a link to the dashboard is correct for Slack/email. Individual findings are appropriate only for Jira ticket creation (one ticket per new finding), not for real-time notifications.
- Implement per-channel **token-bucket throttling** with configurable rate caps. Slack: max 1 message per channel per second. Jira: honor `Retry-After` headers on 429. Splunk HEC: batch events into a single POST rather than one POST per event.
- **Exponential backoff with full jitter** (not linear) on retry. Cap max retries at 3. Log delivery failure with `safe_str(exc)` and move on — do not loop indefinitely.
- **Idempotency keys for Jira tickets**: track `(scan_id, finding_hash)` in a lightweight table (`integration_deliveries`) so duplicate runs cannot create duplicate tickets.
- The `scheduled_scans`/`scheduled_runs` tables already exist — add an `integration_deliveries` table to track delivery status per destination per finding per scan run.

**Warning signs:**
- Integration delivery loop that calls the API inside the scanner's `_wrapped_phase()` path without a separate delivery queue or at-most-once guard.
- No `time.sleep` / backoff in the retry path.
- No `Retry-After` header inspection.
- No configured per-channel rate cap.

**Phase to address:**
Phase 101 (notification fan-out). Rate limiting and idempotency must be designed in from the start — retrofitting after a storm burns the Slack bot's reputation.

---

### Pitfall 5: Optional-Extra Import Trap — Integration Lib at Module Level Breaks Minimal Install

**What goes wrong:**
The Slack integration is implemented in `quirk/integrations/slack.py`. At the top of the file: `import slack_sdk`. `slack_sdk` is declared in `[notifications]` extras only. A user doing `pip install quirk-scanner` (no extras) runs `quirk scan ...`. Python imports `quirk.integrations.slack` transitively (even if Slack is not configured), crashes with `ModuleNotFoundError: No module named 'slack_sdk'`, and the entire scan aborts before any target is touched.

This is the exact failure mode documented in project memory under `feedback_optional_extra_import_trap.md` — specifically the `pypdf` module-level import that broke the minimal install post-v4.10 ship. The pattern cost a post-ship hotfix.

**Why it happens:**
Integration modules are imported at initialization time (e.g., in `__init__.py`, in the module-level `from quirk.integrations import slack, siem, ticketing`). Each integration depends on a third-party SDK (`slack_sdk`, `httpx` extras, `jira`, `splunk-sdk`). When these are in `[extras]`, they are absent on minimal installs.

**How to avoid:**
- **Never top-level import** integration SDK libraries. Use the same `importlib.util.find_spec()` probe pattern from `quirk/util/optional_extra.py`: check availability before importing.
- Each integration module must use **lazy imports inside the function that uses them**, wrapped in a `try/except ImportError` that emits an advisory finding (the existing `probe_missing_extras` / `missing_extra` scan_error_category pattern).
- Add each integration extra (`notifications`, `siem`, `ticketing`) to `REGISTRY` in `quirk/util/optional_extra.py` following the established `OptionalExtra` dataclass pattern — with `enabled_attrs` tied to the config flag that enables the integration (e.g., `enable_slack`, `enable_siem`).
- Add a CI guard (analogous to the existing `[api]` extras exclusion guard) that verifies the integration extras are **not** transitively imported by the minimal install path.
- Integration delivery paths must be gated by `if not is_extra_available("notifications"): return` before any SDK call.

**Warning signs:**
- Any `import slack_sdk`, `import jira`, `import splunk_sdk` at module top-level in a file that is transitively imported during `run_scan.py` startup.
- A new extras group not added to `REGISTRY`.
- `pip install quirk-scanner` + `quirk scan --targets 127.0.0.1` fails with `ModuleNotFoundError` in CI (add a minimal-install smoke test).

**Phase to address:**
Phase 101 (notification fan-out) — establish the extras pattern before any SDK is introduced. All subsequent integration phases inherit the pattern.

---

### Pitfall 6: Dashboard Auth Pitfalls — Default-Open Routes, Key in URL/Logs, Weak Comparison

**What goes wrong — three sub-variants:**

**6a. Default-open routes after adding team auth:**
New routes added for integration management (webhook config, HEC endpoint, Jira credentials) are registered after the `require_auth` middleware and accidentally bypass it, or are registered before the auth middleware mounts. The dashboard is then accessible without a token on the new routes.

**6b. API key or token in URL / access logs:**
An operator or documentation example passes the dashboard API key as a query parameter: `curl http://localhost:8000/api/scan/latest?token=abc123`. The token appears in FastAPI's uvicorn access log, any reverse proxy log, and browser history. Slack or Jira integration config UIs that display the configured integration URLs (for "test connection" features) risk exposing embedded webhook tokens in the Slack URL path.

**6c. Non-timing-safe comparison:**
A new auth path for integration callbacks (e.g., a Slack event subscription verification endpoint) uses `==` to compare the Slack signing secret against the computed HMAC. Python's `==` on strings short-circuits on first differing byte — exploitable as a timing oracle to brute-force the secret byte-by-byte under low-latency conditions.

**Why it happens:**
6a: FastAPI route registration order matters and new phases add routes incrementally. Without a test asserting every route is auth-protected, gaps slip in.
6b: Query-param tokens are documented as "convenient for testing" but copied into production configs.
6c: `hmac.compare_digest()` is not widely known; `==` is the default mental model.

**How to avoid:**
- **6a:** The existing `require_auth` Depends() pattern in `auth.py` is route-level, not middleware-level — each new router must explicitly include `dependencies=[Depends(require_auth)]`. Add a CI test that enumerates all registered routes and asserts each one is covered by `require_auth` (or is explicitly listed in a `PUBLIC_ROUTES` allowlist like `/`, `/health`).
- **6b:** Never accept the dashboard token as a query parameter. The existing `HTTPBearer` extraction reads `Authorization: Bearer <token>` from headers only — preserve this. For integration config display, show `[configured]` not the raw value. For outbound URLs that embed secrets (Slack webhook URLs), store and display them as `[configured]` and only use the value at delivery time.
- **6c:** All secret comparisons must use `hmac.compare_digest()`. The existing `auth.py` already does this for the bearer token — replicate the pattern for any new HMAC verification (Slack signing secret, webhook payload signature). Add the pattern to the project's SECURITY.md style guide.
- The existing `QUIRK_API_TOKEN` env-var-first pattern handles single-tenant API key storage correctly — extend it to `QUIRK_SLACK_TOKEN`, `QUIRK_HEC_TOKEN`, `QUIRK_JIRA_TOKEN` with the same precedence (env var wins over YAML).

**Warning signs:**
- A new `@router.get(...)` without `Depends(require_auth)` in its signature or router-level dependency.
- Any `?token=` or `?api_key=` query parameter in API documentation examples.
- A string comparison `credentials == configured_token` anywhere in the auth path (not `hmac.compare_digest`).
- `quirk doctor` printing the raw value of any integration token.

**Phase to address:**
Phase 104 (dashboard team auth). The route-coverage CI test should be added in Phase 101 when the first new routes are registered, not deferred to the auth phase.

---

### Pitfall 7: Delivery Failure Must Never Abort or Corrupt a Scan / Report Run

**What goes wrong:**
A Slack delivery fails with a network timeout (30 seconds) during a scheduled scan. Because the notification call is inside the scan pipeline's `_wrapped_phase()` path, the `BaseException` wrapper catches the timeout and marks the entire scan as `scan_error_category='exception'`. The scan result is never written to SQLite. The CBOM is not emitted. The scheduled_runs row shows `status='failed'`. An operator investigating the failure finds no findings, no CBOM, and a cryptic exception — the scan data is lost entirely because a notification side-effect failed.

Alternatively: the Jira client raises `jira.exceptions.JIRAError` during ticket creation (rate limit). This exception propagates up through `run_scan.py` and causes the PDF report export to be skipped.

**Why it happens:**
The existing `_wrapped_phase()` pattern correctly isolates scanner phases from each other, but notifications and integrations are typically bolted on as "post-scan hooks" or wired directly into the scan pipeline without their own isolation boundary. Any unhandled exception in an integration call that executes inside the scan pipeline corrupts the scan outcome.

**How to avoid:**
- **Strict isolation:** All outbound integration delivery (Slack, HEC, Jira, email) must execute in a **separate, isolated try/except block** that is entirely outside the scanner `_wrapped_phase()` call chain. Delivery is a side-effect, not a scan phase.
- The correct architecture: scanner phases write results to SQLite and emit CBOM as normal; a post-scan integration step reads from the completed scan record and delivers notifications. If delivery fails, the scan record is unaffected — the delivery failure is recorded in the `integration_deliveries` table (or equivalent), and the operator is informed via `quirk doctor` status.
- Delivery timeouts must be short (default 5s, configurable) and must not block the scan completion path.
- An integration delivery failure must produce a `scan_error_category='integration_delivery_failed'` advisory finding (not `'exception'`) so it is excluded from trend regression counts (following the existing `missing_extra` exclusion in `trends.py`).
- The `scheduled_runs` record must be written with `status='complete'` before any integration delivery is attempted. Delivery status is separate metadata.

**Warning signs:**
- Any integration API call inside a `with _wrapped_phase(...)` context.
- Integration delivery code that does not have its own `try/except Exception` with `safe_str(exc)` logging.
- A test that fails the scheduled scan when the mock Slack endpoint returns 500.
- No timeout set on integration HTTP calls (default `httpx` / `requests` timeout is infinite or very long).

**Phase to address:**
Phase 101 (notification fan-out). The delivery isolation architecture must be established before any integration delivery code is written — retrofitting after the first integration ships is high-risk.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|---|---|---|---|
| Top-level `import slack_sdk` in integration module | Simple, familiar | Breaks minimal install silently — caught post-ship (pypdf precedent) | Never — use `find_spec` guard |
| Per-finding Slack message (not drift summary) | Richer context per alert | Notification storm; Slack rate-limit ban; alert fatigue | Never for real-time; OK for async digest |
| Jira tickets without `(scan_id, finding_hash)` idempotency key | Simpler first pass | Duplicate tickets on every retry or re-run | Never — add idempotency from day one |
| Hardcoded HTTP timeout of `None` on integration calls | No timeout boilerplate | Scan completion hangs on dead endpoint | Never — always set explicit timeout <= 10s |
| Config-time-only SSRF validation | Single validation point | DNS rebinding attack window between config load and delivery | Never — validate at delivery time too |
| `str(exc)` in integration error log | Full error context | Leaks auth tokens, URLs with embedded secrets | Never — always `safe_str(exc)` |
| API token in YAML config file only (no env var path) | Simple for development | Token in source control / shared configs | Acceptable only if env-var alternative is documented as preferred |
| `==` for token comparison in webhook verification | Familiar Python | Timing oracle for HMAC brute-force | Never in auth paths — always `hmac.compare_digest()` |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|---|---|---|
| Slack incoming webhook | URL contains the token as a path segment — logged raw | Store URL as credential (env var, never log raw); display `[configured]` in UI |
| Slack incoming webhook | Send one message per finding | Send drift summary (N new, M resolved) with dashboard link |
| Slack API rate limit | Linear retry on 429 | Exponential backoff + jitter; honor `Retry-After` header |
| Splunk HEC | One POST per event | Batch events array in a single HEC POST |
| Splunk HEC | `Authorization: Splunk <token>` header in exception text | Extend `safe_str` patterns to cover `Splunk\s+\S+` shape |
| Jira REST API | Create ticket without dedup key | Track `(scan_id, finding_hash)` in `integration_deliveries`; skip if already delivered |
| Jira REST API | Include full `service_detail` / raw CBOM in description | Use `to_integration_payload()` whitelist — severity, category, remediation, scan-ID only |
| SMTP (email notification) | `smtplib.SMTP(host)` without explicit SSL context | Use `smtplib.SMTP_SSL` or `SMTP` + `starttls()` with verified SSL context; never disable cert verification |
| SMTP credentials | Password in exception text from `SMTPAuthenticationError` | Wrap all smtplib calls in `safe_str(exc)`; `SMTPAuthenticationError` embeds server response which may echo credentials |
| Webhook (generic) | No HTTPS enforcement | Validate scheme with `_ALLOWED_SCHEMES = {"https"}` — plain HTTP rejected outright |
| Webhook (generic) | URL accepted at config time only | Re-validate with `validate_external_url()` immediately before each delivery call |
| Webhook DNS rebinding | Domain passes allowlist at config load, re-resolves to internal IP at delivery time | Re-resolve and re-validate at delivery time; optionally pin the resolved IP at config time |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---|---|---|
| Outbound fetch to user-configured URL without `validate_external_url()` | SSRF to cloud metadata (credential theft), internal service probe | Re-use `quirk.util.url_allowlist.validate_external_url()` at delivery time; never allow `allow_internal=True` for integration URLs |
| Embedding full CBOM or cert chain in Jira/Slack payload | Sensitive cryptographic inventory leaves operator's control | `to_integration_payload()` whitelist — no PEM, no raw JSON blobs |
| Bot token / HEC token / SMTP password in scan_error column | Credential persistence in SQLite (SQLite file may be shared/backed up) | `safe_str(exc)` on all integration exceptions before any write; extend `_SENSITIVE_PATTERNS` for new token shapes |
| Integration delivery inside `_wrapped_phase()` scan pipeline | Delivery failure kills scan; no findings, no CBOM | Strict isolation: delivery runs post-scan, reads from completed SQLite record |
| New dashboard route without `Depends(require_auth)` | Auth bypass for integration management endpoints | Route-coverage CI test enumerated against `PUBLIC_ROUTES` allowlist |
| API key in URL query param | Token in access logs, browser history, reverse proxy logs | `Authorization: Bearer` header only; no query-param token acceptance |
| Non-`compare_digest` comparison in webhook signature verification | Timing oracle enables HMAC brute-force of signing secret | `hmac.compare_digest()` — already in `auth.py`, replicate for all new verification paths |

---

## "Looks Done But Isn't" Checklist

- [ ] **Outbound SSRF guard:** `validate_external_url()` called at delivery time (not only at config-load time). DNS rebinding window closed.
- [ ] **Slack webhook URL:** Stored and logged as `[configured]`, not raw. URL contains the token in its path — treat as credential.
- [ ] **safe_str coverage:** `_SENSITIVE_PATTERNS` extended to cover Splunk `Authorization: Splunk <token>`, Slack `xoxb-`/`xoxp-` prefixes, SMTP auth error text.
- [ ] **Minimal install smoke test:** `pip install quirk-scanner && quirk scan --targets 127.0.0.1` passes without `ModuleNotFoundError` when integration extras are absent.
- [ ] **`REGISTRY` updated:** Each new integration extra (`notifications`, `siem`, `ticketing`) has an `OptionalExtra` entry with correct `enabled_attrs`.
- [ ] **Delivery isolation test:** A mock that returns 500 from the Slack/HEC/Jira endpoint does NOT cause the scan SQLite record to be absent or the CBOM to be missing.
- [ ] **`integration_deliveries` idempotency:** Re-running a scheduled scan with the same findings does not create duplicate Jira tickets.
- [ ] **Route-coverage CI test:** All new FastAPI routes are either in `PUBLIC_ROUTES` or have `Depends(require_auth)` — automated assertion, not a manual check.
- [ ] **Rate-limit test:** Mock Slack endpoint returning `429 Retry-After: 2` triggers backoff, not an immediate retry storm.
- [ ] **`to_integration_payload()` field whitelist:** All integration serializers call this — no `**finding.__dict__` or raw CBOM attachment paths.

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---|---|---|
| SSRF via outbound URL (Pitfall 1) | Phase 101 (notification fan-out) | Unit test: `validate_external_url("http://169.254.169.254")` called at delivery time; test with a URL that passes config-time but resolves to RFC1918 after config load |
| Secret leakage in logs/SQLite (Pitfall 2) | Phase 101 — extend `safe_str` before first SDK integration | AST gate (existing) must cover integration module paths; `safe_str` pattern test for Splunk/Slack token shapes |
| Sensitive finding data exfiltration (Pitfall 3) | Phase 101 — define `to_integration_payload()` | Review that no integration module accesses `finding.tls_capabilities_json` or CBOM builder output directly |
| Notification storm / no throttling (Pitfall 4) | Phase 101 | Integration test: 50-finding scan triggers exactly 1 Slack message (summary), not 50; Jira path creates at most N tickets with idempotency guard |
| Optional-extra import trap (Pitfall 5) | Phase 101 | CI smoke test: minimal install path does not import `slack_sdk`/`jira`/`splunk_sdk`; `REGISTRY` entry present |
| Dashboard auth gaps (Pitfall 6) | Phase 101 (route-coverage test) + Phase 104 (auth) | Automated route enumeration test; no `?token=` in API docs; `hmac.compare_digest` used in all new auth paths |
| Delivery failure corrupts scan (Pitfall 7) | Phase 101 | Test: mock delivery endpoint returns 500; scan SQLite record and CBOM are present and complete; `integration_deliveries` row shows `failed` |

---

## Sources

- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Webhook Vulnerabilities in Automation Pipelines](https://infosecwriteups.com/webhook-vulnerabilities-hidden-vulnerabilities-in-automation-pipelines-724d09ec6130)
- [Slack Security Best Practices](https://api.slack.com/authentication/best-practices)
- [Designing for Webhook Consumer Failures](https://gethook.to/blog/webhook-consumer-graceful-degradation)
- [Splunk HEC Token Security](https://w9.com.tr/en/article/what-is-the-hec-code)
- [FastAPI HTTP Basic Auth / compare_digest](https://fastapi.tiangolo.com/advanced/security/http-basic-auth/)
- [Atlassian Rate Limiting Guide](https://community.developer.atlassian.com/t/rate-limiting-guide-for-jira-and-confluence/43360)
- [Python smtplib TLS stripping vulnerability](https://python-security.readthedocs.io/vuln/smtplib-tls-stripping.html)
- [SSRF DNS Rebinding Attack](https://aydinnyunus.github.io/2026/03/14/ssrf-dns-rebinding-vulnerability/)
- Project: `quirk/util/url_allowlist.py` (validate_external_url, existing SSRF guard)
- Project: `quirk/util/safe_exc.py` (safe_str, existing credential scrubbing)
- Project: `quirk/util/optional_extra.py` (REGISTRY, find_spec probe pattern)
- Project: `quirk/dashboard/api/middleware/auth.py` (hmac.compare_digest, bearer pattern)
- Project memory: `feedback_optional_extra_import_trap.md` (pypdf post-ship minimal-install breakage, v4.10)

---
*Pitfalls research for: QU.I.R.K. v5.3 Adoption & Integration Surface — outbound notifications, SIEM export, ticketing, dashboard auth*
*Researched: 2026-05-24*
