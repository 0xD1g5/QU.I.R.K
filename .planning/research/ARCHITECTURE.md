# Architecture Research — v5.3 Adoption & Integration Surface

**Domain:** Outbound integration layer on an existing Python CLI + FastAPI crypto-scanner
**Researched:** 2026-05-24
**Confidence:** HIGH (based on direct codebase inspection; no training-data inference)

---

## System Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│  EXISTING — unchanged                                                     │
│  ┌────────────────────┐     ┌────────────────────────────────────────┐   │
│  │  quirk/cli/        │     │  quirk/dashboard/api/                  │   │
│  │  scheduler_cmd.py  │     │  routes/{scan,trends,schedules,...}.py │   │
│  │  _dispatch_schedule│     │  middleware/auth.py  (require_auth)    │   │
│  └─────────┬──────────┘     └────────────────────────────────────────┘   │
│            │ db.commit()                                                  │
│            │ ← SEAM (post-commit, line 162)                              │
│            ↓                                                              │
├────────────┴──────────────────────────────────────────────────────────────┤
│  NEW — v5.3                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  quirk/notifications/                                              │  │
│  │  __init__.py          NotificationChannel ABC                      │  │
│  │  drift_helper.py      _compute_post_run_trend() wrapper            │  │
│  │  slack_channel.py     SlackChannel(webhook_url_env)                │  │
│  │  email_channel.py     EmailChannel(smtp_cfg)                       │  │
│  │  webhook_channel.py   WebhookChannel(url_env, method, headers_env) │  │
│  │  siem_channel.py      SIEMChannel(...)    ← phase 2                │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  quirk/integrations/                                               │  │
│  │  ticketing_channel.py TicketingChannel(jira_cfg / sn_cfg)          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  quirk/config.py additions                                         │  │
│  │  NotificationCfg / SlackNotifCfg / EmailNotifCfg / WebhookNotifCfg│  │
│  │  SIEMCfg / TicketingCfg                                            │  │
│  │  AppConfig.notifications field                                     │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  quirk/dashboard/api/routes/notifications.py (optional)            │  │
│  │  GET  /api/notifications/status  (auth required)                   │  │
│  │  POST /api/notifications/test    (auth + csrf)                     │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Drift-Event Emission Seam (Concrete Location)

### Where drift events currently live

The `TrendReport` dataclass in `quirk/intelligence/trends.py` is the canonical
drift-event data structure. `compute_trend_report(current_ts, previous_ts, db)` is
a pure function (no `datetime.now()` inside; D-12 in that module) that returns:

- `score_delta` — int delta between sessions, or None on first scan
- `new_high / new_medium / new_low` — net-new findings by severity bucket
- `resolved_high / resolved_medium / resolved_low`
- `scan_errors_new_count / scan_errors_resolved_count`
- `new_findings_sample / resolved_findings_sample` — top-5 `SampleFindingItem` arrays

The regression threshold the dashboard uses is `score_delta <= -5 OR new_high > 0`
(sourced from `RegressionAlertChip.tsx`, Phase 64). This threshold exists only in
the frontend — there is currently no backend code that evaluates it.

### Where the seam must go

The scheduler dispatch loop at `quirk/cli/scheduler_cmd.py:_dispatch_schedule()`
(lines 109-163) is the only place a scheduled scan completes and a compare-now-vs-before
action is meaningful. The exact insertion point:

```
_dispatch_schedule():
  152-158: proc.communicate() → returncode check
  159:     run.completed_at = _utcnow_naive()
  161:     schedule.last_run_at = now
  162:     db.commit()     ← THE SEAM — notification hook goes here
  163:     return run
```

After `db.commit()` at line 162, a `TrendReport` can be computed immediately by calling
`compute_trend_report(current_ts, previous_ts, db)` and passed to a notification
dispatcher. No existing logic changes — the notification call is purely additive.

```python
# Proposed addition in _dispatch_schedule(), after db.commit():
channels = _load_channels(config_path)
if channels and run.status == "completed":
    report = _compute_post_run_trend(db, schedule)
    for ch in channels:
        try:
            ch.send_drift_event(report, schedule)
        except Exception:
            logger.exception("notification channel %s failed silently", type(ch).__name__)
```

`_compute_post_run_trend` is a thin wrapper in `quirk/notifications/drift_helper.py`
that calls `_list_session_timestamps`-equivalent logic then `compute_trend_report`.
This avoids importing dashboard route internals into the scheduler.

---

## 2. Shared Abstraction: NotificationChannel

### Verdict: shared ABC, pluggable backends, fan-out in a loop

Three backends ship in the anchor phase (Slack + email + webhook). SIEM and ticketing
follow on the same abstraction. Ad-hoc per-integration code would mean three separate
call sites in `_dispatch_schedule()` immediately, five after SIEM and ticketing, with
no central place to test the dispatch loop.

### Interface shape

```python
# quirk/notifications/__init__.py
from abc import ABC, abstractmethod
from quirk.intelligence.trends import TrendReport
from quirk.models import ScheduledScan

class NotificationChannel(ABC):
    @abstractmethod
    def send_drift_event(
        self,
        report: TrendReport,
        schedule: ScheduledScan,
    ) -> None:
        """Deliver a drift event. Must not raise — catch, log, return."""
        ...
```

Concrete backends:
- `quirk/notifications/slack_channel.py` — `SlackChannel` posts to a Slack incoming
  webhook URL. Zero new pip deps (stdlib `urllib.request`).
- `quirk/notifications/email_channel.py` — `EmailChannel` sends SMTP STARTTLS.
  Zero new pip deps (stdlib `smtplib` + `email`).
- `quirk/notifications/webhook_channel.py` — `WebhookChannel` posts JSON to any URL.
  Zero new pip deps (stdlib `urllib.request`).
- `quirk/notifications/siem_channel.py` — `SIEMChannel` for Splunk HEC / Elastic /
  syslog CEF. Splunk HEC is a plain POST (no new dep); Elastic needs `[siem]` extra.
- `quirk/integrations/ticketing_channel.py` — `TicketingChannel` for Jira/ServiceNow.
  Needs `[integrations]` extra with `jira>=3.5` or `pysnow>=0.7`.

SIEM export is findings-push (not drift-event-push), so `SIEMChannel` gets a second
method `send_findings_export(findings, scan_meta)`. Ticketing is per-finding, so
`TicketingChannel` gets `open_ticket_for_finding(finding, qramm_evidence)`. Both
remain on the same pluggable-backend architecture.

---

## 3. Integration Config — Location, Shape, and Secret Handling

### Established pattern to mirror

`BrokerCredential.pass_env` (Phase 57 / D-05) is the existing precedent: the YAML
holds the NAME of the env var, not the secret value. `SecurityCfg.api_token` and
`auth.py:_get_configured_token()` establish the env-var-wins-over-YAML priority.

Integration secrets (webhook URLs, SMTP passwords, API keys) are long-lived unlike
v5.1 ephemeral scanner credentials, but must not appear in `quirk.db` or scan JSON.
The pattern is identical: YAML holds `*_env` key names; secrets resolve from env vars
at dispatch time; never written to any ORM column or log.

### Proposed config additions to `quirk/config.py`

```python
@dataclass(frozen=True)
class SlackNotifCfg:
    webhook_url_env: str          # NAME of env var holding webhook URL
    on_regression: bool = True
    score_threshold: int = -5     # fire when score_delta <= this

@dataclass(frozen=True)
class EmailNotifCfg:
    smtp_host: str
    smtp_port: int = 587
    from_addr: str
    to_addrs: list                # non-secret, OK inline
    tls: bool = True
    username_env: str = ""        # NAME of env var; empty = no SMTP auth
    password_env: str = ""        # NAME of env var

@dataclass(frozen=True)
class WebhookNotifCfg:
    url_env: str                  # NAME of env var holding target URL
    method: str = "POST"
    headers_env: str = ""         # NAME of env var holding JSON headers dict

@dataclass
class NotificationCfg:
    slack: Optional[SlackNotifCfg] = None
    email: Optional[EmailNotifCfg] = None
    webhook: Optional[WebhookNotifCfg] = None
    siem: Optional[SIEMCfg] = None       # added in v5.3 phase 2
    ticketing: Optional[TicketingCfg] = None  # added in v5.3 phase 3
```

`AppConfig` gains `notifications: NotificationCfg = field(default_factory=NotificationCfg)`.
`config_from_dict()` parses the new `[notifications]` YAML block via the existing pattern
(pull raw dict, construct dataclass with `**kwargs`).

### YAML shape (non-secret values only)

```yaml
notifications:
  slack:
    webhook_url_env: QUIRK_SLACK_WEBHOOK_URL
    on_regression: true
    score_threshold: -5
  email:
    smtp_host: smtp.example.com
    smtp_port: 587
    from_addr: quirk-scanner@example.com
    to_addrs:
      - security-team@example.com
    tls: true
    username_env: QUIRK_SMTP_USER
    password_env: QUIRK_SMTP_PASS
  webhook:
    url_env: QUIRK_WEBHOOK_URL
    method: POST
```

### Secret resolution at call time

```python
# In SlackChannel.send_drift_event():
webhook_url = os.environ.get(self._cfg.webhook_url_env, "")
if not webhook_url:
    logger.warning("%s not set; skipping Slack notification", self._cfg.webhook_url_env)
    return
```

Same discipline as `CredentialContext.from_cli()` in v5.1: validated at injection
boundary, never persisted, never logged. The process holds the resolved secret only
for the duration of the HTTP call.

---

## 4. FastAPI Auth — Current Attachment Points and v5.3 Work

### Current state (Phase 58 / v4.8) — verified by inspection

`require_auth` in `quirk/dashboard/api/middleware/auth.py` is a `Depends()` bearer-token
dependency. It is attached at **router level** via `dependencies=[Depends(require_auth)]`.

Current attachment map (all routers verified against source):

| Router file | Auth deps | CSRF? |
|---|---|---|
| `scan.py` — line 81 | `require_auth` | No |
| `trends.py` — line 38 | `require_auth` | No |
| `schedules.py` — line 33 | `require_auth` | Yes |
| `jobs.py` read_router — line 38 | `require_auth` | No |
| `jobs.py` write_router — line 39 | `require_auth` | Yes |
| `pdf.py` — line 23 | `require_auth` | Yes |
| `qramm.py` — line 50 | `require_auth` | Yes |
| `health.py` | (unprotected — health check is public) | No |
| SPA catch-all `app.py` | (unprotected — serves static assets) | No |

The pattern: read routes get `require_auth` only; write routes get `require_auth` +
`require_csrf`. All new v5.3 routes follow this same split.

### v5.3 dashboard auth work

No new FastAPI auth mechanism is needed for single-tenant team sharing. The Phase 58
`QUIRK_API_TOKEN` bearer-token pattern already implements this. The v5.3 "dashboard
team auth" feature is UX polish:

1. `quirk auth generate-token` CLI command — prints a cryptographically random token
   and the `export QUIRK_API_TOKEN=...` one-liner so operators do not hand-craft tokens.
2. `GET /api/auth/status` endpoint — returns `{"auth_enabled": bool}` unprotected,
   allowing the React SPA to show a login prompt rather than silently returning 401s.
3. React login form — a token-input component that stores to
   `localStorage.quirk_api_token` and sends `Authorization: Bearer <token>` on API
   calls. Shown when auth is enabled and no stored token, replacing the current silent
   401 behavior.

### New notifications router

```python
# quirk/dashboard/api/routes/notifications.py
read_router = APIRouter(dependencies=[Depends(require_auth)])
write_router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
```

Endpoints:
- `GET /api/notifications/status` (read_router) — returns which channels are configured
  (by checking env var presence, NOT returning values)
- `POST /api/notifications/test` (write_router) — sends a test notification to all
  configured channels; returns per-channel success/failure

---

## 5. Data Flow

### Notification fan-out (anchor path)

```
ScheduledScan (cron due)
    ↓
scheduler_cmd._check_and_dispatch_due()
    ↓
_dispatch_schedule(schedule, db, config_path)
    ↓  subprocess: run_scan.py writes CryptoEndpoints to SQLite
    ↓  proc.communicate() → returncode
    ↓  run.status = "completed" | "failed"
    ↓  db.commit()   ← SEAM (line 162)
    ↓
drift_helper._compute_post_run_trend(db, schedule)
    → resolves current/previous session timestamps from CryptoEndpoint.scanned_at
    → calls compute_trend_report(current_ts, previous_ts, db) → TrendReport
    ↓
_evaluate_regression(report, cfg.notifications)
    → score_delta <= threshold OR new_high > 0
    ↓  (if triggered, or always-notify mode)
channels = _load_channels_from_config(cfg.notifications)
    → each channel reads its secret from env var at this moment
    ↓
for channel in channels:
    channel.send_drift_event(report, schedule)
        SlackChannel   → POST to Slack webhook URL (resolved from QUIRK_SLACK_WEBHOOK_URL)
        EmailChannel   → SMTP STARTTLS to configured recipients
        WebhookChannel → POST JSON payload to operator URL
        ← any Exception: caught, logged at WARNING, not re-raised
```

### SIEM export (findings-push, distinct from drift events)

Runs either after each scheduled scan completes (same `_dispatch_schedule` seam, but
calls `send_findings_export`) or on demand via `quirk export --siem`. Serializes
`CryptoEndpoint` findings to the target format (Splunk HEC JSON events, Elastic bulk
API, or syslog/CEF lines). This is a separate method path from `send_drift_event`
but uses the same channel lifecycle.

### Ticketing (per-finding, distinct from drift events)

Invoked with individual finding dicts enriched with QRAMM evidence from
`evidence_bridge.py`. The seam is either post-scheduled-scan (auto-ticket new
HIGH/CRITICAL findings) or an explicit `quirk ticket create --finding <id>`. Dedup
key: `(finding_category, host, port)` — prevents duplicate tickets on repeated scans.

---

## 6. Component Boundaries

| Component | Responsibility | Communicates With |
|---|---|---|
| `quirk/notifications/__init__.py` | `NotificationChannel` ABC | No imports from scanner or dashboard |
| `quirk/notifications/drift_helper.py` | Wraps `compute_trend_report` for scheduler use | `quirk.intelligence.trends`, `quirk.models` |
| `quirk/notifications/slack_channel.py` | HTTP POST to Slack webhook; formats payload | ABC, stdlib `urllib.request` |
| `quirk/notifications/email_channel.py` | SMTP send; MIME formatting | ABC, stdlib `smtplib` + `email` |
| `quirk/notifications/webhook_channel.py` | Generic HTTP POST/GET; JSON payload | ABC, stdlib `urllib.request` |
| `quirk/notifications/siem_channel.py` | Findings serialization + SIEM transport | ABC; `elasticsearch` optional |
| `quirk/integrations/ticketing_channel.py` | Per-finding ticket creation; dedup logic | `jira` or `pysnow` optional |
| `quirk/config.py` additions | `NotificationCfg` dataclasses; `pass_env` secret indirection | Extends existing `AppConfig` |
| `quirk/cli/scheduler_cmd.py` additions | Fan-out call in `_dispatch_schedule` after commit | `quirk.notifications` module |
| `quirk/dashboard/api/routes/notifications.py` | View/test notification config | `require_auth`, `require_csrf` |

---

## 7. Packaging — Optional Extras

Notification backends ship with zero new hard deps where possible:

| Backend | New pip dep | Extra name |
|---|---|---|
| Slack webhook | None (stdlib `urllib.request`) | No new extra |
| Email SMTP | None (stdlib `smtplib`) | No new extra |
| Webhook (generic) | None (stdlib `urllib.request`) | No new extra |
| SIEM — Splunk HEC | None (plain HTTP POST) | No new extra |
| SIEM — Elastic | `elasticsearch>=8.0` | `[siem]` new extra |
| Ticketing — Jira | `jira>=3.5` | `[integrations]` new extra |
| Ticketing — ServiceNow | `pysnow>=0.7` | `[integrations]` new extra |

The `[notifications]` group (Slack/email/webhook/Splunk HEC) ships with zero new hard
deps. `[siem]` and `[integrations]` follow the lazy-import guard pattern: unconditional
top-level import blocked; lazy import inside the channel constructor with a graceful
advisory if the extra is missing. Add entries to `REGISTRY` in `optional_extra.py`
with appropriate `enabled_attrs` mapped to the presence of `NotificationCfg.*` fields.

---

## 8. Recommended Build Order

Ordering constraints:
1. `NotificationChannel` ABC and `NotificationCfg` config schema must exist before
   any backend is implemented.
2. `drift_helper.py` and the scheduler seam must exist before any backend can be
   wired end-to-end.
3. Slack/email/webhook (the anchor) must ship before SIEM or ticketing — they
   validate the abstraction on the simplest backends first and with zero new pip deps.
4. Dashboard auth UX is independent of the notification path — can run in parallel.

**Phase 101 — Foundation + Notification Fan-Out (ANCHOR)**
- `NotificationCfg` family in `config.py` (all channels, `pass_env` shape)
- `quirk/notifications/` package: ABC + `drift_helper.py`
- Slack + email + webhook backends (stdlib only, zero new deps)
- `_dispatch_schedule()` seam wired with fan-out loop and regression gate
- `QUIRK_SLACK_WEBHOOK_URL` / `QUIRK_SMTP_*` / `QUIRK_WEBHOOK_URL` env-var contract
- REGISTRY entries for notification channels in `optional_extra.py`
- Tests: `send_drift_event` called after scan completes; secret resolution from env;
  no-op on missing env var; failed channel does not abort scheduler loop

**Phase 102 — Dashboard Auth UX + CLI Token Generator**
- `quirk auth generate-token` CLI command
- `GET /api/auth/status` unprotected endpoint
- React login form for when auth is enabled
- `notifications.py` route (GET status + POST test)

**Phase 103 — SIEM Export**
- `quirk/notifications/siem_channel.py` (Splunk HEC first; Elastic if capacity allows)
- `quirk export --siem` CLI command (on-demand in addition to scheduled-scan trigger)
- `SIEMCfg` dataclass; `[siem]` optional extra
- Findings-to-SIEM-event serialization from `CryptoEndpoint` model

**Phase 104 — Ticketing Integration**
- `quirk/integrations/ticketing_channel.py` (Jira first; ServiceNow if capacity)
- `TicketingCfg` dataclass; `[integrations]` optional extra
- Per-finding dedup key `(category, host, port)` to prevent duplicate tickets
- QRAMM `evidence_bridge.py` evidence threaded into ticket body
- `quirk ticket create / list / sync` CLI subcommands

---

## 9. Anti-Patterns to Avoid

### Anti-Pattern 1: Unconditional top-level import of notification backend deps

**What people do:** `import slack_sdk` at the top of `slack_channel.py`.
**Why it's wrong:** Breaks `quirk serve` and `run_scan.py` on minimal installs with no
advisory. The `pypdf` bug (v4.10 post-ship) documented in MEMORY.md is this exact
failure class — unconditional import of a dep declared only in extras silently breaks
CLI on minimal install, invisible in dev envs that always have `[all]`.
**Do this instead:** Lazy import inside the channel's `send_*` method, guarded with
`try/except ImportError` that emits `logging.warning` and returns.

### Anti-Pattern 2: Storing secrets in SQLite or scan JSON output

**What people do:** Persist `NotificationCfg` (with resolved webhook URL) to
`scheduled_scans` table for scheduler reload without config.
**Why it's wrong:** The database and scan JSON blobs are output artifacts shared with
clients. Secrets in SQLite are credential leakage (Phase 59 / LEAK-01 lesson).
**Do this instead:** YAML holds `pass_env` names only. Secrets are resolved from env
vars at dispatch time and held only for the HTTP call lifetime.

### Anti-Pattern 3: Raising exceptions in `send_drift_event`

**What people do:** Let `SlackChannel.send_drift_event()` propagate network errors.
**Why it's wrong:** Kills the scheduler's `_dispatch_schedule()` context, which would
abort the `ScheduledRun` status commit or corrupt the run record.
**Do this instead:** All channel implementations catch all exceptions internally,
log at WARNING via `logging.exception(...)`, and return silently. Test invariant:
a misconfigured Slack URL must not prevent `run.status = "completed"` from being
committed.

### Anti-Pattern 4: Re-deriving TrendReport inside the notification channel

**What people do:** Call `compute_trend_report` again inside `SlackChannel` to format
the message.
**Why it's wrong:** Doubles the DB query; risks session window shift between two calls.
**Do this instead:** Compute once in `drift_helper._compute_post_run_trend()` after
the scheduler commits; pass the `TrendReport` object down to all channels. The API
trends route continues to call `compute_trend_report` independently on its own request
cycle.

### Anti-Pattern 5: Per-integration auth in the `require_auth` middleware

**What people do:** Add Jira / Slack credentials to `SecurityCfg` so they share the
auth middleware loading path.
**Why it's wrong:** Auth middleware is for dashboard API protection. Mixing integration
secrets into it couples unrelated concerns and makes `_get_configured_token()` read
multiple credential types.
**Do this instead:** Integration secrets live in `NotificationCfg.*.pass_env` fields
and are resolved by the channel implementations. They never touch the auth middleware.

---

## Sources

All findings are HIGH confidence — sourced from direct codebase inspection (2026-05-24):

- `quirk/cli/scheduler_cmd.py` — `_dispatch_schedule()` lines 109-163; concrete seam location
- `quirk/intelligence/trends.py` — `TrendReport` dataclass + `compute_trend_report()` signature
- `quirk/dashboard/api/middleware/auth.py` — `require_auth` Depends() + `_get_configured_token()` priority
- `quirk/dashboard/api/routes/schedules.py` — router-level auth + CSRF attachment example
- `quirk/dashboard/api/routes/trends.py` — router-level auth-only attachment; `require_auth` line 38
- `quirk/dashboard/api/routes/jobs.py` — read/write router split (auth-only vs auth+CSRF)
- `quirk/dashboard/api/app.py` — full router registration map; health and SPA unprotected
- `quirk/config.py` — `AppConfig`, `SecurityCfg`, `BrokerCredential.pass_env` (secret pattern)
- `quirk/util/optional_extra.py` — `REGISTRY`, lazy-import guard pattern
- `quirk/auth/credentials.py` — ephemeral credential zeroization discipline (v5.1)
- `src/dashboard/src/components/RegressionAlertChip.tsx` — regression threshold definition

---

*Architecture research for: QU.I.R.K. v5.3 Adoption & Integration Surface*
*Researched: 2026-05-24*
