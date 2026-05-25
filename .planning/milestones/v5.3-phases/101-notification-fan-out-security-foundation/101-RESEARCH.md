# Phase 101: Notification Fan-Out + Security Foundation — Research

**Researched:** 2026-05-24
**Domain:** Async notification dispatch, integration security primitives, SQLite schema extension, Python stdlib SMTP + HTTP, Slack SDK optional extra
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Global `[notifications]` config block lives in the existing YAML scan config loaded via `--config` (no separate notify.yaml)
- Secrets referenced by env-var NAME in config (e.g. `slack_webhook_env = "QUIRK_SLACK_WEBHOOK"`), resolved at dispatch time — never literal values, never persisted
- A channel is enabled by the presence of its config block (Slack / email / webhook each independently optional)
- Fan-out: when multiple channels are configured, dispatch delivers to all in one pass
- Default trigger: a new HIGH/CRITICAL finding OR a score regression beyond a configurable floor (default −5); never fires on MEDIUM-only
- Slack delivery: one summary message per scan (score band, delta, finding counts, dashboard link)
- Dashboard link comes from `dashboard_base_url`; if unset, link is omitted gracefully
- Shared `build_drift_summary()` content model feeds Slack/email/webhook formatters
- `integration_deliveries` schema: `scan_id, finding_hash, destination, status, attempted_at, error_summary`
- Failure handling: per-channel catch-all → log at WARNING via `safe_str`, record failed delivery row, continue; scan never aborted
- No retry/backoff in v5.3 — record + log only
- Dispatch logic in new `quirk/notify/dispatcher.py`, called from `_dispatch_schedule` after line 162 (post commit)
- SSRF: every user-configured outbound URL validated at DELIVERY time (not only config-load), rejecting loopback/internal/metadata
- Outbound whitelist: `to_integration_payload()` allowlist module — everything else redacted before any payload is built
- Secret scrubbing: reuse `safe_str` from `quirk/util/safe_exc.py`
- Optional-extra: lazy import; missing `[notify]` extra degrades with advisory WARNING and skips that channel
- `[notify]` extra: `slack-sdk` only; email uses stdlib `smtplib`, webhook uses stdlib `urllib`

### Claude's Discretion

- Whether `[notify]` joins `[all]` (consider CI-guard precedent — decide at plan time)
- Exact whitelist field set for `to_integration_payload()`

### Deferred Ideas (OUT OF SCOPE)

- Per-schedule notification routing — v5.3.x
- Delivery retry/backoff — out of scope for v5.3
- Splunk HEC endpoint — Phase 103

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOTIFY-01 | Scheduled scan computes drift (TrendReport) and dispatches notification when trigger fires | TrendReport + compute_trend_report() exist in quirk/intelligence/trends.py; caller supplies timestamps; dispatcher reads scanned_at sessions post-scan |
| NOTIFY-02 | Conservative trigger: new HIGH/CRITICAL OR score regression beyond −5; never on every scan, never on MEDIUM-only | TrendReport.new_high, new_medium, score_delta fields enable this check; guard is pure Python, no new deps |
| NOTIFY-03 | Slack via incoming-webhook URL (one summary message per scan) | slack_sdk.webhook.WebhookClient; lazy import behind [notify] extra |
| NOTIFY-04 | Email via stdlib SMTP to one or more recipients | smtplib.SMTP / SMTP_SSL — stdlib, no extra required |
| NOTIFY-05 | Generic outbound webhook (JSON POST) | urllib.request.urlopen — stdlib, no extra required |
| NOTIFY-06 | Global config block; secrets by env-var name, never stored | AppConfig extensible via new NotifyCfg dataclass; env-var resolution at dispatch time |
| NOTIFY-07 | Delivery failure isolated; each attempt recorded for observability | integration_deliveries table + per-channel try/except + safe_str logging |
| ISEC-01 | Every outbound URL validated against SSRF at delivery time | quirk/util/url_allowlist.py::validate_external_url() already exists with full IP-class guards; reuse verbatim |
| ISEC-02 | Integration secret shapes scrubbed from logs | quirk/util/safe_exc.py::safe_str() exists; extend _SENSITIVE_PATTERNS with Slack xoxb- and webhook URL shapes |
| ISEC-03 | Single whitelist defines safe finding/cert/drift fields for third-party payloads | New quirk/notify/payload.py::to_integration_payload(); downstream phases (103–105) reuse it |
| ISEC-04 | Every integration client is optional extra with lazy import + graceful skip | Established pattern: importlib.util.find_spec() gate; precedent in quirk/util/optional_extra.py |

</phase_requirements>

---

## Summary

Phase 101 wires the notification fan-out layer into the existing scheduler dispatch seam and simultaneously ships the seven integration-security primitives that all downstream integration phases (SIEM, Jira, ServiceNow) will inherit. The codebase already provides every foundational building block — `compute_trend_report()`, `validate_external_url()`, `safe_str()`, the `_ensure_columns` / `Base.metadata.create_all` migration patterns, and the optional-extra lazy-import convention — so Phase 101 is predominantly new module wiring, not invention.

The three delivery channels use exactly the libraries specified in CONTEXT.md: `slack_sdk.webhook.WebhookClient` (optional extra `[notify]`), stdlib `smtplib` (no extra), stdlib `urllib.request` (no extra). The SSRF validator (`quirk/util/url_allowlist.py`) is a drop-in reuse — it already handles loopback, RFC1918, link-local, and metadata IP blocking with an `allow_internal` bypass hatch and DNS-resolution fallthrough.

The key architectural complexity to plan around is the scheduler's `--config` overload: the scheduler accepts a raw SQLite `.db` path via `--config`, while the scan subprocess subprocess gets the YAML config via `--config`. The notifications block must be read from the YAML config, which the scheduler does not currently load. The resolution is for the dispatcher to read the notifications config from `QUIRK_CONFIG_PATH` env var (existing pattern in `quirk/config.py:507`) OR accept an explicit `notify_config_path` argument at construction time.

**Primary recommendation:** New package `quirk/notify/` with four modules: `config.py` (NotifyCfg dataclass + YAML parse), `payload.py` (to_integration_payload whitelist), `dispatcher.py` (build_drift_summary + fan-out), `channels/` (slack.py, email.py, webhook.py). The `integration_deliveries` table is added to `quirk/models.py` and bootstrapped in `init_db` via the established `Base.metadata.create_all` pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Drift trigger evaluation | Scheduler process | — | Runs post-scan inside `_dispatch_schedule`; has DB access and TrendReport |
| Drift content model (build_drift_summary) | Scheduler process | — | Pure function; mirrors v5.2 exec_content pattern |
| Secret resolution (env-var lookup) | Scheduler process | — | os.environ access at dispatch time, never persisted |
| Slack delivery | Scheduler process | — | Outbound HTTP; isolated in channel module |
| Email delivery | Scheduler process | — | Outbound SMTP; isolated in channel module |
| Webhook delivery | Scheduler process | — | Outbound HTTP; isolated in channel module |
| SSRF validation | Scheduler process (delivery time) | — | Per-channel, per-URL, at send — not at config-load |
| Delivery audit log (integration_deliveries) | SQLite / Storage | Scheduler process writes | Shared table for all integration phases downstream |
| Outbound field whitelist (to_integration_payload) | quirk/notify/payload.py | All integration phases import | Single canonical source; no per-channel reimplementation |
| Notification config parsing (NotifyCfg) | quirk/notify/config.py | Loaded at dispatch start | Read from YAML config, not from SQLite |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `slack_sdk` (PyPI: `slack-sdk`) | 3.42.0 (latest) | Slack incoming-webhook delivery | Official Slack SDK; `WebhookClient` is the canonical non-bot incoming-webhook client — no OAuth flow required [VERIFIED: pip registry] |
| `smtplib` (stdlib) | Python 3.11+ | Email delivery | No extra dep; supports SMTP_SSL and STARTTLS; multi-recipient via `sendmail` |
| `urllib.request` (stdlib) | Python 3.11+ | Generic outbound webhook | No dep; `urlopen` with `data=` triggers POST; timeout-controlled |
| `hmac` + `hashlib` (stdlib) | Python 3.11+ | HMAC-SHA256 webhook signing | Standard HMAC signing; digest in `X-QUIRK-Signature` header |
| `email.mime` (stdlib) | Python 3.11+ | Construct multipart email | `MIMEMultipart` + `MIMEText` for plain-text body |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `quirk.util.url_allowlist.validate_external_url` | in-repo | SSRF guard at delivery time | Call before every outbound HTTP connection (Slack, webhook, SMTP host validation) |
| `quirk.util.safe_exc.safe_str` | in-repo | Scrub credential shapes from log/error strings | Wrap all exception messages in delivery error paths |
| `quirk.intelligence.trends.compute_trend_report` | in-repo | Compute drift for trigger evaluation | Call after scan completes, supplying current + previous session timestamps |
| `importlib.util.find_spec` | stdlib | Lazy import gate for optional extras | Check `find_spec("slack_sdk")` before importing in channel module |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `slack_sdk.webhook.WebhookClient` | `urllib.request` + raw JSON POST | WebhookClient handles retries + signature verification; stdlib would require hand-rolling the Block Kit shape |
| stdlib `smtplib` | `aiosmtplib` | async SMTP has no benefit in synchronous scheduler context; adds a dep |
| stdlib `urllib` webhook | `httpx` or `requests` | Both are existing transitive deps but adding them to the notification code path increases coupling; urllib is sufficient for a single-endpoint POST |

**Installation:**

```bash
pip install "slack-sdk>=3.33.0"
```

(added to `pyproject.toml` under `[project.optional-dependencies]` as `notify = ["slack-sdk>=3.33.0"]`)

**Version verification:** `pip index versions slack_sdk` → current latest 3.42.0 [VERIFIED: pip registry]. The `slack-sdk` PyPI package is the same distribution as `slack_sdk` (the underscore/hyphen name aliases are the same package per PyPI normalization). [VERIFIED: pip registry]

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `slack_sdk` | PyPI | ~5 yrs (Slack official) | >1M/week | github.com/slackapi/python-slack-sdk | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** none

*slopcheck was available and ran successfully. slack_sdk rated [OK]. No postinstall script.*

---

## Architecture Patterns

### System Architecture Diagram

```
quirk scheduler (long-running process)
  └─ _check_and_dispatch_due()
       └─ _dispatch_schedule(schedule, db, config_path)
            ├─ [subprocess] python -m run_scan --config <yaml> …
            ├─ db.commit()  ← LINE 162 (existing)
            └─ dispatch_notifications(run, db, notify_cfg)  ← NEW (after L162)
                 ├─ load_notifications_config(QUIRK_CONFIG_PATH)
                 ├─ _find_previous_session_ts(db)
                 ├─ compute_trend_report(current_ts, previous_ts, db)
                 ├─ should_notify(report, cfg) → bool
                 │    └─ (new_high > 0 OR score_delta < -threshold)
                 └─ [if True] fan-out:
                      ├─ SlackChannel.send(drift_summary)
                      │    ├─ validate_external_url(url)  [SSRF gate]
                      │    ├─ to_integration_payload(report)  [whitelist]
                      │    └─ WebhookClient.send(...)
                      ├─ EmailChannel.send(drift_summary)
                      │    ├─ smtplib.SMTP / SMTP_SSL
                      │    └─ MIMEMultipart plaintext body
                      └─ WebhookChannel.send(drift_summary)
                           ├─ validate_external_url(url)  [SSRF gate]
                           ├─ to_integration_payload(report)  [whitelist]
                           ├─ HMAC-SHA256 sign (if key configured)
                           └─ urllib.request.urlopen(...)

integration_deliveries (SQLite)
  scan_id | finding_hash | destination | status | attempted_at | error_summary
```

### Recommended Project Structure

```
quirk/
└── notify/
    ├── __init__.py          # public surface: NotifyCfg, dispatch_notifications
    ├── config.py            # NotifyCfg dataclass, load_notifications_config()
    ├── payload.py           # to_integration_payload() whitelist; DriftSummary dataclass
    ├── dispatcher.py        # build_drift_summary(), should_notify(), fan-out loop
    └── channels/
        ├── __init__.py
        ├── slack.py         # SlackChannel — lazy-import slack_sdk
        ├── email.py         # EmailChannel — smtplib stdlib
        └── webhook.py       # WebhookChannel — urllib stdlib + HMAC signing

tests/
└── test_notify_dispatcher.py       # trigger logic, fan-out, failure isolation
└── test_notify_slack.py            # lazy-import, WebhookClient mock
└── test_notify_email.py            # smtplib.SMTP mock
└── test_notify_webhook.py          # urllib mock, HMAC verification
└── test_notify_ssrf.py             # validate_external_url reuse + delivery-time check
└── test_notify_payload_whitelist.py # to_integration_payload field coverage
└── test_install_all_excludes_slack_sdk.py  # CI guard if [notify] excluded from [all]
└── test_integration_deliveries_schema.py   # table creation + column names
```

### Pattern 1: Trigger Evaluation from TrendReport

**What:** After `db.commit()` at line 162, query the two most recent `scanned_at` sessions and call `compute_trend_report`. The trigger fires when `new_high > 0` (CRITICAL maps to "high" bucket in `_SEVERITY_BUCKET`) or `score_delta < -threshold` (default −5).

**When to use:** Every completed scheduled run — check trigger before fan-out.

**Example:**

```python
# Source: quirk/intelligence/trends.py — compute_trend_report() signature
from quirk.intelligence.trends import compute_trend_report, TrendReport
from sqlalchemy import func
from quirk.models import CryptoEndpoint

def _find_two_sessions(db):
    """Return (current_ts, previous_ts) from CryptoEndpoint.scanned_at — mirrors trends route."""
    ts_usec = func.strftime("%Y-%m-%d %H:%M:%f", CryptoEndpoint.scanned_at).label("ts_usec")
    rows = (
        db.query(ts_usec)
        .filter(CryptoEndpoint.scanned_at.isnot(None))
        .group_by("ts_usec")
        .order_by(ts_usec.desc())
        .limit(2)
        .all()
    )
    sessions = [datetime.fromisoformat(r.ts_usec) for r in rows]
    current = sessions[0] if sessions else None
    previous = sessions[1] if len(sessions) > 1 else None
    return current, previous

def should_notify(report: TrendReport, threshold: int = 5) -> bool:
    """Trigger: new HIGH/CRITICAL OR score regression beyond threshold."""
    if report.new_high > 0:
        return True
    if report.score_delta is not None and report.score_delta < -threshold:
        return True
    return False
```

### Pattern 2: SSRF Validation at Delivery Time (ISEC-01 Reuse)

**What:** `validate_external_url()` from `quirk/util/url_allowlist.py` is already fully implemented with loopback, RFC1918, link-local, and metadata-IP blocking. Call it at send time (not config-load time) for every outbound URL.

**When to use:** Before every `WebhookClient.send()` and `urlopen()` call. SMTP host validation is a special case — use for the SMTP server hostname too.

**Example:**

```python
# Source: quirk/util/url_allowlist.py::validate_external_url
from quirk.util.url_allowlist import validate_external_url, RC_METADATA_SERVICE_IP

def _ssrf_check(url: str, destination: str) -> None:
    """Raise ValueError if url fails SSRF check. Always blocks metadata IPs."""
    result = validate_external_url(url)  # allow_internal=False (default)
    if not result.ok:
        raise ValueError(
            f"SSRF blocked ({result.reason}) for destination={destination!r}"
        )
```

### Pattern 3: Secret Scrubbing (ISEC-02) — Extend safe_str

**What:** `safe_str()` in `quirk/util/safe_exc.py` already strips Vault tokens, connection strings, Authorization headers, and long base64 tokens. Need to add Slack webhook URL shapes (`hooks.slack.com`) and xoxb- token shapes.

**When to use:** Every `except` clause in delivery code that passes exc through to a log or the `integration_deliveries.error_summary` column.

**New patterns to add to `_SENSITIVE_PATTERNS`:**

```python
# Source: quirk/util/safe_exc.py — extend _SENSITIVE_PATTERNS tuple
re.compile(r"xox[bpoa]-[0-9A-Za-z\-]{10,}"),          # Slack tokens
re.compile(r"hooks\.slack\.com/services/[A-Za-z0-9/]+"),  # Slack webhook URLs
re.compile(r"smtp[s]?://[^:@\s]+:[^@\s]+@"),            # SMTP connection string
```

### Pattern 4: Lazy Import Gate (ISEC-04) — Follow optional_extra.py Convention

**What:** Use `importlib.util.find_spec("slack_sdk")` before importing `slack_sdk.webhook` at call time. Return an advisory WARNING and skip the channel if the spec is None. Follow the exact shape of existing optional extra guards.

**Example:**

```python
# Source: quirk/util/optional_extra.py pattern
from importlib.util import find_spec
import logging

logger = logging.getLogger(__name__)

def send_slack(url: str, summary: dict) -> None:
    if find_spec("slack_sdk") is None:
        logger.warning(
            "Slack notification skipped — run `pip install quirk[notify]` to enable"
        )
        return
    from slack_sdk.webhook import WebhookClient  # lazy import
    client = WebhookClient(url)
    response = client.send(text=summary["text"], blocks=summary.get("blocks"))
    if response.status_code != 200:
        raise RuntimeError(f"Slack webhook returned {response.status_code}: {response.body}")
```

### Pattern 5: integration_deliveries Table Migration

**What:** New table added to `quirk/models.py` as a SQLAlchemy model, then created via `Base.metadata.create_all(engine, checkfirst=True)` in a new `_ensure_integration_deliveries_table(engine)` function called from `init_db`. This is the same pattern as `_ensure_scheduled_tables` (line 330 in db.py), not the additive-column `_ensure_columns` pattern (which is for adding columns to existing tables).

**Schema:**

```python
class IntegrationDelivery(Base):
    __tablename__ = "integration_deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(String(64), nullable=False, index=True)  # ISO ts matching ScheduledRun.scan_id
    finding_hash = Column(String(64), nullable=True)          # SHA256 dedup key (future use by 103-105)
    destination = Column(String(64), nullable=False)          # "slack" | "email" | "webhook"
    status = Column(String(16), nullable=False)               # "ok" | "failed"
    attempted_at = Column(DateTime, nullable=False)
    error_summary = Column(Text, nullable=True)               # safe_str(exc) — never raw exception
```

### Pattern 6: Outbound Payload Whitelist (ISEC-03)

**What:** `to_integration_payload(report: TrendReport)` returns a dict of only safe, non-sensitive fields. Downstream phases (103 SIEM, 104 Jira, 105 ServiceNow) MUST call this before building any outbound payload. Fields NOT in the allowlist are never included.

**Safe TrendReport fields for third-party consumption:**

```python
# Source: quirk/intelligence/trends.py::TrendReport dataclass
def to_integration_payload(report: TrendReport) -> dict:
    """Whitelist: only drift-level aggregate fields — no host/cert/key material."""
    return {
        "current_score": report.current_score,
        "previous_score": report.previous_score,
        "score_delta": report.score_delta,
        "new_high": report.new_high,
        "new_medium": report.new_medium,
        "new_low": report.new_low,
        "resolved_high": report.resolved_high,
        "resolved_medium": report.resolved_medium,
        "resolved_low": report.resolved_low,
        "scan_errors_new_count": report.scan_errors_new_count,
        # new_findings_sample / resolved_findings_sample: EXCLUDED
        # host/port/protocol are infrastructure topology details — not for third-party
        # current_session_ts / previous_session_ts: included as ISO strings (non-sensitive)
        "current_session_ts": report.current_session_ts.isoformat() if report.current_session_ts else None,
        "previous_session_ts": report.previous_session_ts.isoformat() if report.previous_session_ts else None,
    }
```

**Fields explicitly excluded:** `new_findings_sample[].host`, `.port`, `.protocol`, `.severity` — these expose internal infrastructure topology to third-party services. They should remain in the Slack/email human-readable body (formatted text), but NOT in JSON payloads sent to webhook/SIEM/ticketing endpoints.

### Pattern 7: Notification Config Threading into Scheduler

**Critical architectural note:** The scheduler's `--config` is overloaded to accept a raw SQLite `.db` path (see `_resolve_db_path` in `scheduler_cmd.py:44` and the SQLite magic-byte carve-out in `schedule_cmd.py:50-56`). The YAML scan config is passed to the scan subprocess via `--config` (see `cmd` construction at lines 135-147), but the scheduler process itself does NOT load the YAML config.

The notification dispatcher needs the YAML config to read the `[notifications]` block. Resolution strategy: load the YAML config at dispatch time using `QUIRK_CONFIG_PATH` (an existing env var — see `config.py:507`) OR add a separate `--notify-config` argument to the scheduler. **Recommended:** use `QUIRK_CONFIG_PATH` env var (consistent with existing pattern, no signature change to `_dispatch_schedule`).

```python
# quirk/notify/config.py
import os
from quirk.config import load_config

def load_notifications_config(path: str | None = None) -> "NotifyCfg | None":
    """Load [notifications] block from YAML config.

    Priority: explicit path > QUIRK_CONFIG_PATH env var > None (notifications disabled).
    Returns None when no config path is resolvable — silent, not an error.
    """
    effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")
    if not effective_path or not os.path.isfile(effective_path):
        return None
    try:
        import yaml
        with open(effective_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        notify_raw = (raw or {}).get("notifications")
        if not notify_raw:
            return None
        return _parse_notify_cfg(notify_raw)
    except Exception:
        return None  # silently skip — notification config failure must never abort scan
```

### Pattern 8: SMTP Delivery Pattern (stdlib)

```python
# stdlib smtplib — no extra dep
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(cfg, subject: str, body: str) -> None:
    password = os.environ.get(cfg.smtp_password_env, "")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.smtp_from
    msg["To"] = ", ".join(cfg.recipients)
    msg.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()
    # SMTP_SSL for port 465; STARTTLS for port 587
    if cfg.use_ssl:
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=context,
                               timeout=cfg.timeout_seconds) as smtp:
            if cfg.smtp_user:
                smtp.login(cfg.smtp_user, password)
            smtp.sendmail(cfg.smtp_from, cfg.recipients, msg.as_string())
    else:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port,
                          timeout=cfg.timeout_seconds) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            if cfg.smtp_user:
                smtp.login(cfg.smtp_user, password)
            smtp.sendmail(cfg.smtp_from, cfg.recipients, msg.as_string())
```

### Pattern 9: Generic Webhook with HMAC Signing (stdlib)

```python
# stdlib urllib + hmac — no extra dep
import hmac
import hashlib
import json
import urllib.request

def send_webhook(url: str, payload: dict, hmac_key_env: str | None = None,
                 timeout: int = 10) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if hmac_key_env:
        key = os.environ.get(hmac_key_env, "").encode("utf-8")
        if key:
            sig = hmac.new(key, body, hashlib.sha256).hexdigest()
            req.add_header("X-QUIRK-Signature", f"sha256={sig}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status not in (200, 201, 202, 204):
            raise RuntimeError(f"Webhook returned HTTP {resp.status}")
```

### Anti-Patterns to Avoid

- **Top-level `import slack_sdk`:** Triggers `ImportError` on minimal install. Always use `find_spec("slack_sdk")` gate before any import path that reaches `slack_sdk`.
- **Logging raw exception text without `safe_str`:** Slack webhook URLs, SMTP passwords, and HMAC keys will appear in log output. Every `except` clause in delivery code must pass through `safe_str(exc)`.
- **Evaluating SSRF only at config-load:** Config is loaded once; the URL could be environment-injected or templated. Validate at the moment of connection — inside each channel's send method.
- **Local-import shadow trap:** If `from slack_sdk.webhook import WebhookClient` is placed inside a branch of a function that also has `WebhookClient` referenced elsewhere in the same function scope, Python makes the name function-local for the entire function. Avoid this by keeping the lazy import in a dedicated helper function (see Pattern 4 above).
- **Reading `scanned_at` sessions before the scan subprocess completes:** The notification dispatch must occur after `proc.communicate()` returns and `db.commit()` is called (line 162). Starting earlier will see no new session endpoints.
- **Alert storm on first scan:** When `previous_ts is None`, `TrendReport.score_delta` is `None` and all delta counts are 0 — `should_notify` will return `False` correctly. Verify this edge case in tests.
- **Blocking the scheduler loop with SMTP timeouts:** All delivery channels must use explicit timeouts (smtp timeout, urlopen timeout). Default is blocking-forever, which would prevent the scheduler from dispatching other schedules.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSRF IP validation | Custom ipaddress checks | `quirk.util.url_allowlist.validate_external_url` | Already handles loopback, RFC1918, link-local, and metadata IP (169.254.169.254 and fd00:ec2::254) with DNS resolution + allow_internal bypass |
| Credential scrubbing in logs | Regex on log strings | `quirk.util.safe_exc.safe_str(exc)` | Established pattern already covering Vault tokens, Authorization headers, long base64, query-param keys |
| Drift computation | Recompute finding deltas | `quirk.intelligence.trends.compute_trend_report()` | Pure function already handles severity bucketing, null-session, scan_error exclusion, and sample capping |
| Session timestamp discovery | Custom query | `_list_session_timestamps()` pattern from `quirk/dashboard/api/routes/trends.py:41` | Already uses millisecond-precision strftime grouping to handle CR-05 (two scans per second) |
| SQLite schema migration | Raw `CREATE TABLE` | `Base.metadata.create_all(engine, checkfirst=True)` + `_ensure_scheduled_tables` pattern | Idempotent, consistent with all other new-table additions in `init_db` |
| Optional extra detection | `try: import slack_sdk` | `importlib.util.find_spec("slack_sdk")` | `try/import` triggers the import side effects; `find_spec` is probe-only (established in `optional_extra.py`) |
| HMAC signing | Roll custom MAC | `hmac.new(key, body, hashlib.sha256).hexdigest()` (stdlib) | Standard; avoids accidental timing-unsafe compare in consumer |

**Key insight:** Every SSRF, scrubbing, drift, and migration concern is already solved in the codebase. Phase 101 wires them together; it does not invent them.

---

## Runtime State Inventory

> Omitted — this is a greenfield phase adding new modules and a new table. No renaming, refactoring, or data migration involved.

---

## Common Pitfalls

### Pitfall 1: Scheduler `--config` is a DB path, not a YAML path

**What goes wrong:** Passing `config_path` (which is a `.db` file path or `QUIRK_DB_PATH`) to `load_config()` — `yaml.safe_load` on a binary SQLite file will raise or produce garbage, causing a silent notification skip (or a noisy crash if not caught).

**Why it happens:** `_dispatch_schedule` receives `config_path` which `_resolve_db_path` resolved to the `.db` file. The YAML scan config is passed to the subprocess but the scheduler process never loads it.

**How to avoid:** Load the notifications config from `QUIRK_CONFIG_PATH` env var (separate from the DB path). In `load_notifications_config`, check `os.path.isfile(path)` and silently return `None` if the file doesn't parse as YAML. Document that operators must set `QUIRK_CONFIG_PATH` alongside `QUIRK_DB_PATH`.

**Warning signs:** Notification config fields are always None/empty; test `QUIRK_CONFIG_PATH` env-var override explicitly.

### Pitfall 2: Local-import shadow trap in dispatch function

**What goes wrong:** Defining `from slack_sdk.webhook import WebhookClient` inside a branch of `dispatch_notifications()` makes `WebhookClient` function-local for the entire function (Python compile-time scoping). Any reference to `WebhookClient` outside that branch raises `UnboundLocalError`.

**Why it happens:** Python scoping is determined at compile time, not runtime. Any assignment (including `import X`) inside a function makes X function-local everywhere in that function.

**How to avoid:** Keep lazy imports inside dedicated single-purpose functions (e.g., `_send_slack_channel`) rather than inside branches of larger dispatch functions.

**Warning signs:** `UnboundLocalError: local variable 'WebhookClient' referenced before assignment` — the existing `tests/test_run_scan_init_db_scope.py` AST gate pattern should be extended to cover new delivery modules.

### Pitfall 3: Blocking SMTP call stalls scheduler loop

**What goes wrong:** `smtplib.SMTP` without a timeout argument blocks indefinitely if the SMTP server is unreachable. The scheduler loop makes one DB session per 60-second iteration; a blocked SMTP call prevents all other schedules from dispatching.

**Why it happens:** `smtplib.SMTP(host, port)` timeout defaults to `None` (blocking).

**How to avoid:** Always pass `timeout=cfg.timeout_seconds` (default 10) to `SMTP()` and `SMTP_SSL()`. Wrap in a `try/except` with `safe_str` error capture.

**Warning signs:** Scheduler loop takes longer than 60s between iterations; delivery rows stuck in "pending".

### Pitfall 4: Alert storm on first scan (no previous session)

**What goes wrong:** On the very first scheduled scan, `previous_ts` is `None`, so `TrendReport.score_delta` is `None` and `new_high` is 0. `should_notify()` correctly returns `False` in this case. If the trigger logic is inverted or uses `score_delta is not None and score_delta < -5`, a `None` check failure can cause either an alert storm or a silent skip.

**Why it happens:** `compute_trend_report` with `previous_ts=None` returns the early-exit single-session response (lines 206–221 in `trends.py`) where all delta fields are 0 and `score_delta` is `None`.

**How to avoid:** `should_notify` must explicitly handle `score_delta is None` as `False` for the score-regression branch. Covered by test: `test_notify_dispatcher.py::test_no_notify_on_first_scan`.

### Pitfall 5: Finding hash dedup collision with SHA256 truncation

**What goes wrong:** Using a truncated hash (e.g., SHA256[:16]) for `finding_hash` in `integration_deliveries` risks collision on large finding sets, silently deduping distinct findings as identical.

**Why it happens:** Premature optimization to reduce column width.

**How to avoid:** Use full `hashlib.sha256(f"{host}:{port}:{protocol}:{category}".encode()).hexdigest()` — 64 hex chars, zero collision risk for realistic finding counts. `VARCHAR(64)` is already safe per `_SAFE_COL_TYPE_RE` in `db.py`.

### Pitfall 6: `[notify]` inclusion in `[all]` — follow the CI-guard discipline

**What goes wrong:** If `[notify]` (which contains `slack-sdk`) is added to `[all]` without adding a CI guard test (`test_install_all_excludes_*`), future contributors can add problematic transitive deps without detection.

**Why it happens:** `[all]` meta-extra is manually maintained; no automatic guard.

**How to avoid:** If `[notify]` joins `[all]`, add `tests/test_install_all_excludes_slack_sdk.py` that does a pip dry-run resolve and asserts `slack-sdk` IS present (or asserts any known incompatible transitives are absent). If `[notify]` is EXCLUDED from `[all]` (like `[identity]`, `[api]`), add a guard that asserts `slack-sdk` is NOT present in the `[all]` resolve. Decision to make at plan time.

**Recommendation (plan-time):** Include `[notify]` in `[all]`. `slack-sdk>=3.33` has no known cryptography downgrade chain (unlike `impacket`) and is officially maintained by Slack. This is analogous to `[docx]` which was added to `[all]` in Phase 100. Add a CI inclusion test, not an exclusion test.

---

## Code Examples

### Complete _dispatch_schedule hook (integration seam)

```python
# Source: quirk/cli/scheduler_cmd.py — add after line 162 (db.commit())
# The notification call is isolated: any exception must not propagate to the caller.

    # ... (existing code, line 162):
    db.commit()
    # Phase 101 NOTIFY-01: dispatch notifications for this completed run.
    # Import is deferred to avoid circular imports in the scheduler module.
    try:
        from quirk.notify.dispatcher import dispatch_notifications
        dispatch_notifications(run=run, schedule=schedule, db=db)
    except Exception as exc:  # noqa: BLE001 — notification failure must never crash scheduler
        import logging
        from quirk.util.safe_exc import safe_str
        logging.getLogger(__name__).warning(
            "Notification dispatch error (scan record unaffected): %s", safe_str(exc)
        )
    return run
```

### NotifyCfg dataclass shape

```python
# Source: new quirk/notify/config.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class SlackNotifyCfg:
    slack_webhook_env: str           # name of env var holding the webhook URL
    dashboard_base_url: Optional[str] = None

@dataclass
class EmailNotifyCfg:
    smtp_host: str
    smtp_port: int = 587
    smtp_from: str = ""
    recipients: List[str] = field(default_factory=list)
    smtp_user: Optional[str] = None
    smtp_password_env: Optional[str] = None  # env var name, not the password
    use_ssl: bool = False            # True → SMTP_SSL (port 465); False → STARTTLS (port 587)
    timeout_seconds: int = 10

@dataclass
class WebhookNotifyCfg:
    url_env: str                     # env var name holding the webhook URL
    hmac_key_env: Optional[str] = None  # env var name holding HMAC signing key
    timeout_seconds: int = 10

@dataclass
class NotifyCfg:
    trigger_score_floor: int = -5    # score_delta < this → notify
    slack: Optional[SlackNotifyCfg] = None
    email: Optional[EmailNotifyCfg] = None
    webhook: Optional[WebhookNotifyCfg] = None
```

### YAML config block shape

```yaml
# Additions to config.yaml (loaded via QUIRK_CONFIG_PATH)
notifications:
  trigger_score_floor: -5            # score regression beyond this fires notification

  slack:
    slack_webhook_env: "QUIRK_SLACK_WEBHOOK"   # env var name, not the URL itself
    dashboard_base_url: "https://quirk.example.com"

  email:
    smtp_host: "smtp.example.com"
    smtp_port: 587
    smtp_from: "quirk@example.com"
    recipients:
      - "security@example.com"
    smtp_user: "quirk@example.com"
    smtp_password_env: "QUIRK_SMTP_PASSWORD"   # env var name
    timeout_seconds: 10

  webhook:
    url_env: "QUIRK_WEBHOOK_URL"     # env var name
    hmac_key_env: "QUIRK_WEBHOOK_HMAC_KEY"  # optional; omit to skip signing
    timeout_seconds: 10
```

### build_drift_summary content model

```python
# Source: new quirk/notify/payload.py — mirrors v5.2 exec_content pattern
from dataclasses import dataclass
from typing import Optional
from quirk.intelligence.trends import TrendReport

@dataclass
class DriftSummary:
    """Shared content model consumed by all channel formatters."""
    current_score: Optional[int]
    previous_score: Optional[int]
    score_delta: Optional[int]
    score_band: str          # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "GOOD"
    new_high: int
    new_medium: int
    new_low: int
    scan_id: str             # ISO timestamp identifying the scan session
    dashboard_url: Optional[str]

def build_drift_summary(report: TrendReport, dashboard_base_url: Optional[str] = None,
                        scan_id: str = "") -> DriftSummary:
    band = _score_to_band(report.current_score)
    dash_url = f"{dashboard_base_url.rstrip('/')}/?scan_id={scan_id}" if dashboard_base_url else None
    return DriftSummary(
        current_score=report.current_score,
        previous_score=report.previous_score,
        score_delta=report.score_delta,
        score_band=band,
        new_high=report.new_high,
        new_medium=report.new_medium,
        new_low=report.new_low,
        scan_id=scan_id,
        dashboard_url=dash_url,
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TrendReport computed in dashboard routes only | TrendReport exists as pure function (`compute_trend_report`) usable anywhere | Phase 63/64 (D-12) | Can call from scheduler without hitting the API layer |
| SSRF validation was scanner-side only | `validate_external_url` reusable util in `quirk/util/` | Phase 57 | Drop-in reuse for delivery-time SSRF — no reinvention |
| optional extras loaded eagerly | `find_spec` lazy-import gate, `REGISTRY` in `optional_extra.py` | Phase 45 | Established convention; `[notify]` follows the same gate |
| Schema migrations were per-feature helpers | Generic `_ensure_columns` + `_ADDITIVE_MIGRATIONS` registry | Phase 77/85 | New-table additions still use `Base.metadata.create_all` with `checkfirst=True` |

**Deprecated/outdated:**

- `T-63-10` startup recovery: `run_scan.scan_id` column in `ScheduledRun` is currently `None` until... nowhere sets it (column exists, never populated by the scanner subprocess). The notification dispatcher should use `run.scan_output_path` (the output directory path, which functions as a run identifier) and the `current_session_ts` (the `scanned_at` timestamp from the freshest CryptoEndpoint row) as the `scan_id` for `integration_deliveries`. Do NOT rely on `ScheduledRun.scan_id` — it is `None` in production.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `[notify]` including `slack-sdk` is safe to add to `[all]` — no cryptography downgrade chain | Pitfall 6, Standard Stack | If slack-sdk has a problematic transitive dep, minimal-install users are affected; mitigated by CI guard test |
| A2 | `QUIRK_CONFIG_PATH` env var is the right mechanism to thread the YAML config path into the scheduler notification dispatch | Pattern 7 | If operators don't set `QUIRK_CONFIG_PATH`, notifications silently disabled; doc update required |
| A3 | `ScheduledRun.scan_id` is always `None` in production (never set by the scan subprocess) | State of the Art | If some code path sets `scan_id`, the notification `scan_id` derivation strategy is already consistent |
| A4 | `SampleFindingItem.host/port/protocol` fields are infrastructure topology and should be excluded from the `to_integration_payload()` whitelist | Pattern 6 (ISEC-03) | If customers expect host-level detail in webhook payloads, they'll need a separate config opt-in; an overly broad whitelist is a security regression, so err toward exclusion |

---

## Open Questions

1. **`[notify]` in `[all]`?**
   - What we know: `slack-sdk` is the only `[notify]` dep; no known cryptography downgrade chain; precedent is `[docx]` which joined `[all]` in Phase 100
   - What's unclear: Whether any downstream Slack SDK transitive dep (aiohttp, httpx) causes a version pin conflict with QUIRK's existing `httpx>=0.28.0` core dep
   - Recommendation: Include `[notify]` in `[all]` AND add a pip dry-run CI guard asserting no version conflicts; check `pip index versions slack-sdk` for transitive chain during plan execution

2. **SMTP SSRF guard for the server hostname**
   - What we know: `validate_external_url` works on HTTP/HTTPS URLs; SMTP uses `host:port` not a URL
   - What's unclear: Whether a crafted SMTP hostname pointing to `169.254.169.254` would be blocked
   - Recommendation: In the email channel, construct `smtp://{host}:{port}` and call `validate_external_url` on that before connecting; the URL scheme guard will block `file://` etc., and IP validation will block metadata IPs

3. **`ScheduledRun.scan_id` field — who should populate it?**
   - What we know: Column exists in `ScheduledRun` model but is always `None` (no code sets it)
   - What's unclear: Whether Phase 101 should populate `scan_id` from the `current_session_ts` ISO timestamp (making it consistent with the dashboard's scan_id convention)
   - Recommendation: Yes — the notification dispatcher has access to `current_session_ts`; it should also write `run.scan_id = current_ts.isoformat()` and commit. This closes a latent gap and makes `ScheduledRun` rows consistently queryable by `scan_id`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | smtplib SSL context API | Check | — | Python 3.10+ also works for all stdlib patterns used |
| `slack_sdk` (PyPI) | Slack channel | Not in project venv (no `[notify]` extra yet) | 3.42.0 on PyPI | lazy-import skip with advisory |
| SMTP server | Email delivery | Operator-provided | — | None (operator configures or omits the email block) |
| Network egress to Slack API | Slack delivery | Operator-controlled | — | None (SSRF guard will block if misconfigured) |

**Missing dependencies with no fallback:** None — all delivery channels are individually optional; a missing channel skips gracefully with an advisory log line.

**Missing dependencies with fallback:** `slack_sdk` — not installed in project venv; installed at operator time via `pip install quirk[notify]`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing; see `pyproject.toml` `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/test_notify_dispatcher.py tests/test_notify_payload_whitelist.py tests/test_notify_ssrf.py -x` |
| Full suite command | `pytest tests/ -x -m "not slow and not live_infra"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOTIFY-01 | Drift computed from current + previous session timestamps after scan | unit | `pytest tests/test_notify_dispatcher.py::test_dispatch_computes_trend -x` | ❌ Wave 0 |
| NOTIFY-02 | Trigger fires on new HIGH; does not fire on MEDIUM-only or first scan | unit | `pytest tests/test_notify_dispatcher.py::test_trigger_high_fires tests/test_notify_dispatcher.py::test_no_trigger_medium_only tests/test_notify_dispatcher.py::test_no_notify_on_first_scan -x` | ❌ Wave 0 |
| NOTIFY-03 | Slack channel sends via WebhookClient; skips gracefully when slack_sdk absent | unit | `pytest tests/test_notify_slack.py -x` | ❌ Wave 0 |
| NOTIFY-04 | Email channel sends via smtplib; SMTP mocked; multi-recipient | unit | `pytest tests/test_notify_email.py -x` | ❌ Wave 0 |
| NOTIFY-05 | Webhook channel POSTs JSON; HMAC header present when key configured | unit | `pytest tests/test_notify_webhook.py -x` | ❌ Wave 0 |
| NOTIFY-06 | Secrets never appear in integration_deliveries.error_summary; env-var resolved at dispatch | unit | `pytest tests/test_notify_dispatcher.py::test_secret_not_in_delivery_row -x` | ❌ Wave 0 |
| NOTIFY-07 | Delivery failure logs WARNING + records failed row; scan record unaffected | unit | `pytest tests/test_notify_dispatcher.py::test_delivery_failure_isolated -x` | ❌ Wave 0 |
| ISEC-01 | SSRF blocked at delivery time for loopback, RFC1918, metadata IP (169.254.169.254) | unit | `pytest tests/test_notify_ssrf.py -x` | ❌ Wave 0 |
| ISEC-02 | safe_str strips Slack xoxb- tokens and webhook URLs from error_summary | unit | `pytest tests/test_notify_dispatcher.py::test_safe_str_scrubs_secrets -x` | ❌ Wave 0 |
| ISEC-03 | to_integration_payload excludes host/port/protocol sample fields | unit | `pytest tests/test_notify_payload_whitelist.py -x` | ❌ Wave 0 |
| ISEC-04 | Missing slack_sdk → WARNING logged, Slack channel skipped, no ImportError | unit | `pytest tests/test_notify_slack.py::test_graceful_skip_missing_extra -x` | ❌ Wave 0 |
| (schema) | integration_deliveries table created by init_db; columns match spec | unit | `pytest tests/test_integration_deliveries_schema.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_notify_dispatcher.py tests/test_notify_payload_whitelist.py tests/test_notify_ssrf.py -x`
- **Per wave merge:** `pytest tests/ -x -m "not slow and not live_infra"`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

All test files listed above are new — none exist yet. Wave 0 must create:

- [ ] `tests/test_notify_dispatcher.py` — trigger logic, fan-out, failure isolation, secret scrubbing
- [ ] `tests/test_notify_slack.py` — WebhookClient mock, lazy-import skip
- [ ] `tests/test_notify_email.py` — smtplib.SMTP mock, SMTP_SSL mock, multi-recipient
- [ ] `tests/test_notify_webhook.py` — urlopen mock, HMAC signature header
- [ ] `tests/test_notify_ssrf.py` — delivery-time SSRF check for all three channel types
- [ ] `tests/test_notify_payload_whitelist.py` — field inclusion/exclusion coverage
- [ ] `tests/test_integration_deliveries_schema.py` — init_db creates table; SA inspect confirms columns
- [ ] `quirk/notify/__init__.py` — package marker
- [ ] (optional, if `[notify]` joins `[all]`) `tests/test_install_all_includes_notify.py` — pip dry-run CI guard

Existing test infrastructure: `conftest.py` provides `_isolate_quirk_db` fixture (monkeypatches `QUIRK_DB_PATH`). Use `tmp_path` for DB isolation consistent with `test_scheduler_cmd.py`.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a (delivery auth is per-channel, not user-facing) |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a (notification dispatch is internal to scheduler process) |
| V5 Input Validation | yes | `validate_external_url` for outbound URLs; `_parse_notify_cfg` must validate field types from YAML |
| V6 Cryptography | yes | HMAC-SHA256 (stdlib `hmac` + `hashlib`) for webhook signing; `ssl.create_default_context()` for SMTP TLS |
| V7 Error Handling / Logging | yes | `safe_str(exc)` in all delivery error paths; error_summary column bounded by TEXT but safe_str-scrubbed |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via user-configured webhook/Slack URL | Elevation of Privilege | `validate_external_url` at delivery time; always-block metadata IPs |
| Secret leakage into logs (SMTP password, Slack webhook URL, HMAC key) | Information Disclosure | `safe_str(exc)` wraps all exception paths; new `_SENSITIVE_PATTERNS` for xoxb- and hooks.slack.com shapes |
| Exfiltration of internal infra topology (host/port/protocol) via webhook payloads | Information Disclosure | `to_integration_payload()` whitelist excludes sample finding fields; shared by all integration phases |
| Import chain expansion breaking minimal install | Tampering | `find_spec("slack_sdk")` gate + `[notify]` optional extra; never top-level import |
| notification failure corrupting scan record | Tampering / Denial of Service | Full try/except wrapping the notification dispatch call in `_dispatch_schedule`; scan record written before dispatch |
| Alert storm on new HIGH findings at every re-scan | Denial of Service (ops) | `finding_hash` in `integration_deliveries` provides dedup key for downstream phases; Phase 101 does not implement dedup — it writes the hash for future use |

---

## Sources

### Primary (HIGH confidence)

- `quirk/cli/scheduler_cmd.py` — `_dispatch_schedule` seam at lines 109–163; verified `db.commit()` at line 162
- `quirk/intelligence/trends.py` — `TrendReport` dataclass + `compute_trend_report()` API; severity bucketing; `_SEVERITY_BUCKET` mapping CRITICAL/HIGH → "high"
- `quirk/util/url_allowlist.py` — `validate_external_url()` full implementation; reason-code constants; DNS resolution fallthrough behavior
- `quirk/util/safe_exc.py` — `safe_str()` + `_SENSITIVE_PATTERNS` tuple; existing coverage
- `quirk/util/optional_extra.py` — `find_spec` lazy-import pattern + `REGISTRY` shape
- `quirk/db.py` — `init_db` orchestration; `_ensure_columns`; `_ADDITIVE_MIGRATIONS`; `Base.metadata.create_all` pattern for new tables
- `quirk/models.py` — `ScheduledRun.scan_id` column (nullable, always None); `ScheduledRun.scan_output_path`
- `quirk/config.py` — `AppConfig` + `config_from_dict`; YAML loader is `yaml.safe_load`; `QUIRK_CONFIG_PATH` env var at line 507
- `pyproject.toml` — `[all]` extras list; precedent for excluded extras (`identity`, `api`); `docx` inclusion in `[all]`
- `quirk/dashboard/api/routes/trends.py` — `_list_session_timestamps()` millisecond-precision strftime pattern for session discovery

### Secondary (MEDIUM confidence)

- `pip index versions slack_sdk` → current latest 3.42.0 [VERIFIED: pip registry]
- `slopcheck install slack_sdk` → [OK] (ran successfully)
- Python stdlib docs for `smtplib`, `urllib.request`, `hmac`, `email.mime` [ASSUMED from training; stdlib APIs are stable]

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — verified via pip registry + slopcheck; stdlib requires no verification
- Architecture: HIGH — all integration points read directly from source files with line references
- Pitfalls: HIGH — derived from existing code patterns (scheduler_cmd, optional_extra, safe_exc) and confirmed anti-patterns in project MEMORY.md
- Validation architecture: HIGH — follows existing pytest patterns; test file names and assertions derived from actual requirement behaviors

**Research date:** 2026-05-24
**Valid until:** 2026-08-24 (90 days; stack is stable; only `slack_sdk` version floor could drift)

---

## RESEARCH COMPLETE

**Phase:** 101 — Notification Fan-Out + Security Foundation
**Confidence:** HIGH

### Key Findings

- The dispatch seam is confirmed at `quirk/cli/scheduler_cmd.py:162` (after `db.commit()`); the notification hook goes immediately after, wrapped in a full try/except so scan records are never corrupted by delivery failures.
- `quirk/util/url_allowlist.py::validate_external_url()` is a drop-in SSRF guard — already handles loopback, RFC1918, link-local, and both cloud metadata IPs (169.254.169.254 + fd00:ec2::254). Call it in every channel's send method, not at config-load time.
- `TrendReport` fields are safe except `new_findings_sample[].host/port/protocol` — these expose infra topology and must be excluded from `to_integration_payload()`. Include only score and count aggregates.
- The scheduler's `--config` is a DB path, NOT a YAML path — the notifications config must be read separately via `QUIRK_CONFIG_PATH` env var (existing pattern in `config.py:507`).
- `ScheduledRun.scan_id` is always `None` in production; Phase 101 should populate it from `current_session_ts.isoformat()` as a bonus fix.
- `slack_sdk` latest is 3.42.0; slopcheck rated it [OK]; `[notify]` joining `[all]` is recommended with a CI guard test.

### File Created

`.planning/phases/101-notification-fan-out-security-foundation/101-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Verified via pip registry + slopcheck |
| Architecture | HIGH | All seam locations read from source; exact line numbers confirmed |
| Pitfalls | HIGH | Derived from existing project feedback (local-import shadow, optional-extra import trap) and code structure |
| Validation Architecture | HIGH | Follows existing pytest + conftest patterns; all test names derived from specific behaviors |

### Open Questions

- Does `slack_sdk>=3.33.0` introduce a transitive `httpx` or `aiohttp` version conflict with QUIRK's `httpx>=0.28.0` core dep? (Verify with `pip install -e ".[all,notify]" --dry-run` during plan execution.)
- Should `ScheduledRun.scan_id` be populated by the dispatcher as a bonus fix? (Recommended: yes.)

### Ready for Planning

Research complete. Planner can now create PLAN.md files.
