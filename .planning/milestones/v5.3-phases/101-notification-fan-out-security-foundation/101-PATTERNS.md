# Phase 101: Notification Fan-Out + Security Foundation - Pattern Map

**Mapped:** 2026-05-24
**Files analyzed:** 17 (10 new source modules + 7 new test files)
**Analogs found:** 17 / 17

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/notify/__init__.py` | package marker | — | `quirk/util/__init__.py` | role-match |
| `quirk/notify/config.py` | config/dataclass | request-response | `quirk/config.py` (AppConfig, config_from_dict) | role-match |
| `quirk/notify/payload.py` | utility/transform | transform | `quirk/reports/content_model.py` (ExecContent, build_exec_content) | exact |
| `quirk/notify/dispatcher.py` | service/orchestrator | event-driven | `quirk/cli/scheduler_cmd.py` (_dispatch_schedule) | role-match |
| `quirk/notify/channels/__init__.py` | package marker | — | `quirk/util/__init__.py` | role-match |
| `quirk/notify/channels/slack.py` | service/sender | request-response | `quirk/util/optional_extra.py` (lazy-import pattern) | exact |
| `quirk/notify/channels/email.py` | service/sender | request-response | `quirk/cli/scheduler_cmd.py` (subprocess + timeout pattern) | partial |
| `quirk/notify/channels/webhook.py` | service/sender | request-response | `quirk/util/url_allowlist.py` (validate_external_url reuse) | partial |
| `quirk/models.py` (extend) | model | CRUD | `quirk/models.py` (ScheduledRun — new SQLAlchemy model shape) | exact |
| `quirk/db.py` (extend) | utility/migration | CRUD | `quirk/db.py` (_ensure_scheduled_tables pattern, init_db chain) | exact |
| `quirk/util/safe_exc.py` (extend) | utility | transform | `quirk/util/safe_exc.py` (_SENSITIVE_PATTERNS extension) | exact |
| `quirk/cli/scheduler_cmd.py` (extend) | service | event-driven | `quirk/cli/scheduler_cmd.py` (after db.commit() at L162) | exact |
| `pyproject.toml` (extend) | config | — | `pyproject.toml` ([all] + docx precedent, lines 84–98) | exact |
| `tests/test_notify_dispatcher.py` | test | event-driven | `tests/test_scheduler_cmd.py` (tmp_path + monkeypatch pattern) | exact |
| `tests/test_notify_slack.py` | test | request-response | `tests/test_scheduler_cmd.py` (FakePopen monkeypatch → mock WebhookClient) | role-match |
| `tests/test_notify_email.py` | test | request-response | `tests/test_scheduler_cmd.py` (monkeypatch stdlib call) | role-match |
| `tests/test_notify_webhook.py` | test | request-response | `tests/test_scheduler_cmd.py` (monkeypatch urllib.request.urlopen) | role-match |
| `tests/test_notify_ssrf.py` | test | request-response | `tests/test_scheduler_cmd.py` (parametrize + assert pattern) | role-match |
| `tests/test_notify_payload_whitelist.py` | test | transform | `tests/test_install_all_excludes_impacket.py` (assertion structure) | partial |
| `tests/test_integration_deliveries_schema.py` | test | CRUD | `tests/test_scheduler_cmd.py` (init_db + sa_inspect pattern) | role-match |
| `tests/test_install_all_includes_notify.py` | test | — | `tests/test_install_all_excludes_impacket.py` (pip dry-run CI guard) | exact |

---

## Pattern Assignments

### `quirk/notify/config.py` (config/dataclass, request-response)

**Analog:** `quirk/config.py` (lines 1–10, 374–494, 491–514)

**Imports pattern** (model from `quirk/config.py` lines 1–8):
```python
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml
```

**Dataclass shape** (model from `quirk/config.py` lines 10–60):
```python
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
    smtp_password_env: Optional[str] = None
    use_ssl: bool = False
    timeout_seconds: int = 10

@dataclass
class WebhookNotifyCfg:
    url_env: str
    hmac_key_env: Optional[str] = None
    timeout_seconds: int = 10

@dataclass
class NotifyCfg:
    trigger_score_floor: int = -5
    slack: Optional[SlackNotifyCfg] = None
    email: Optional[EmailNotifyCfg] = None
    webhook: Optional[WebhookNotifyCfg] = None
```

**Config loading pattern** (model from `quirk/config.py` lines 491–514 — QUIRK_CONFIG_PATH env var pattern):
```python
def load_notifications_config(path: str | None = None) -> "NotifyCfg | None":
    """Priority: explicit path > QUIRK_CONFIG_PATH env var > None (disabled)."""
    effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")
    if not effective_path or not os.path.isfile(effective_path):
        return None
    try:
        with open(effective_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        notify_raw = (raw or {}).get("notifications")
        if not notify_raw:
            return None
        return _parse_notify_cfg(notify_raw)
    except Exception:
        return None  # notification config failure must never abort scan
```

**Critical note:** `quirk/config.py:507` shows the exact `QUIRK_CONFIG_PATH` env-var pattern. The scheduler's `--config` is a DB path (not YAML) — never pass `config_path` from `_dispatch_schedule` to `load_config()`. Always use the env var.

---

### `quirk/notify/payload.py` (utility/transform, transform)

**Analog:** `quirk/reports/content_model.py` (lines 1–80)

**Imports pattern** (from `quirk/reports/content_model.py` lines 18–23):
```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from quirk.intelligence.trends import TrendReport
```

**DriftSummary dataclass** (mirrors ExecContent at `quirk/reports/content_model.py` lines 55–80 — one structured object consumed by all formatters):
```python
@dataclass
class DriftSummary:
    """Shared content model consumed by all channel formatters.
    Mirrors v5.2 ExecContent: built once, formatters receive this instance
    and format its fields — they do not re-derive content from raw inputs.
    """
    current_score: Optional[int]
    previous_score: Optional[int]
    score_delta: Optional[int]
    score_band: str          # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "GOOD"
    new_high: int
    new_medium: int
    new_low: int
    scan_id: str             # ISO timestamp from current_session_ts
    dashboard_url: Optional[str]
```

**Whitelist function** (new pattern, no direct analog — defined by ISEC-03):
```python
def to_integration_payload(report: TrendReport) -> dict:
    """Whitelist: only drift-level aggregate fields — no host/cert/key material.
    Downstream phases (103 SIEM, 104 Jira, 105 ServiceNow) MUST call this
    before building any outbound payload.
    """
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
        "current_session_ts": report.current_session_ts.isoformat() if report.current_session_ts else None,
        "previous_session_ts": report.previous_session_ts.isoformat() if report.previous_session_ts else None,
        # EXCLUDED: new_findings_sample[].host/port/protocol — infra topology
    }
```

---

### `quirk/notify/dispatcher.py` (service/orchestrator, event-driven)

**Analog:** `quirk/cli/scheduler_cmd.py` (lines 109–163) and `quirk/dashboard/api/routes/trends.py` (lines 41–60)

**Imports pattern** (model from `quirk/cli/scheduler_cmd.py` lines 1–20):
```python
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.intelligence.trends import compute_trend_report, TrendReport
from quirk.models import CryptoEndpoint, ScheduledRun, ScheduledScan
from quirk.util.safe_exc import safe_str
from quirk.notify.config import load_notifications_config, NotifyCfg
from quirk.notify.payload import build_drift_summary, to_integration_payload

logger = logging.getLogger(__name__)
```

**Session timestamp query** (copy from `quirk/dashboard/api/routes/trends.py` lines 41–60):
```python
def _find_two_sessions(db: Session):
    """Return (current_ts, previous_ts) — mirrors _list_session_timestamps in trends.py."""
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
```

**Trigger evaluation** (new, no direct analog):
```python
def should_notify(report: TrendReport, threshold: int = 5) -> bool:
    """Trigger: new HIGH/CRITICAL OR score regression beyond threshold.
    Must handle score_delta is None as False (first scan, no previous session).
    """
    if report.new_high > 0:
        return True
    if report.score_delta is not None and report.score_delta < -threshold:
        return True
    return False
```

**Fan-out core pattern** (model from `quirk/cli/scheduler_cmd.py` per-channel isolation shape):
```python
def dispatch_notifications(run: ScheduledRun, schedule: ScheduledScan, db: Session) -> None:
    notify_cfg = load_notifications_config()
    if notify_cfg is None:
        return
    current_ts, previous_ts = _find_two_sessions(db)
    if current_ts is None:
        return
    report = compute_trend_report(current_ts, previous_ts, db)
    if not should_notify(report, threshold=abs(notify_cfg.trigger_score_floor)):
        return
    scan_id = current_ts.isoformat()
    # Bonus fix: populate ScheduledRun.scan_id if not set
    if run.scan_id is None:
        run.scan_id = scan_id
        db.commit()
    summary = build_drift_summary(report, dashboard_base_url=..., scan_id=scan_id)
    for channel_fn, channel_cfg in _enabled_channels(notify_cfg, summary):
        _deliver(channel_fn, channel_cfg, summary, scan_id, db)
```

**Delivery isolation** (each channel wrapped — model from `quirk/cli/scheduler_cmd.py` try/except pattern):
```python
def _deliver(channel_fn, channel_cfg, summary, scan_id, db):
    """Per-channel delivery with failure isolation (NOTIFY-07)."""
    from quirk.models import IntegrationDelivery
    from datetime import datetime as _dt
    row = IntegrationDelivery(
        scan_id=scan_id,
        destination=channel_cfg.destination_label,
        status="ok",
        attempted_at=_dt.utcnow(),
    )
    try:
        channel_fn(channel_cfg, summary)
    except Exception as exc:
        row.status = "failed"
        row.error_summary = safe_str(exc)  # ISEC-02: safe_str always
        logger.warning("Delivery failed (%s): %s", channel_cfg.destination_label, safe_str(exc))
    db.add(row)
    db.commit()
```

---

### `quirk/notify/channels/slack.py` (service/sender, request-response)

**Analog:** `quirk/util/optional_extra.py` (lines 37–168) — lazy-import via `find_spec`

**Lazy-import pattern** (copy from `quirk/util/optional_extra.py` lines 37–43, 159–167):
```python
from __future__ import annotations

import logging
import os
from importlib.util import find_spec

from quirk.util.url_allowlist import validate_external_url
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)

def send_slack(cfg, summary) -> None:
    """Send Slack notification. Skips with advisory WARNING if slack_sdk absent (ISEC-04)."""
    if find_spec("slack_sdk") is None:
        logger.warning(
            "Slack notification skipped — run `pip install quirk[notify]` to enable"
        )
        return
    url = os.environ.get(cfg.slack_webhook_env, "")
    if not url:
        logger.warning("Slack notification skipped — env var %r not set", cfg.slack_webhook_env)
        return
    # ISEC-01: SSRF check at delivery time, not config-load time
    result = validate_external_url(url)
    if not result.ok:
        raise ValueError(f"SSRF blocked ({result.reason}) for Slack webhook")
    from slack_sdk.webhook import WebhookClient  # lazy import — AFTER find_spec gate
    client = WebhookClient(url)
    response = client.send(text=summary["text"], blocks=summary.get("blocks"))
    if response.status_code != 200:
        raise RuntimeError(f"Slack webhook returned {response.status_code}: {response.body}")
```

**Critical:** The `from slack_sdk.webhook import WebhookClient` MUST live inside the dedicated `send_slack` helper function, NOT inside a branch of `dispatch_notifications`. This avoids the local-import shadow trap (see `tests/test_run_scan_init_db_scope.py` AST gate pattern).

---

### `quirk/notify/channels/email.py` (service/sender, request-response)

**Analog:** `quirk/cli/scheduler_cmd.py` (timeout pattern, lines 152–163) for the blocking-call + timeout discipline

**Core pattern** (stdlib smtplib — no analog in codebase; follow RESEARCH Pattern 8):
```python
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from quirk.util.url_allowlist import validate_external_url
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)

def send_email(cfg, subject: str, body: str) -> None:
    """Deliver email via stdlib smtplib. Timeout mandatory (NOTIFY-07 / Pitfall 3)."""
    # ISEC-01: validate SMTP host as URL to block metadata IPs
    smtp_url = f"https://{cfg.smtp_host}:{cfg.smtp_port}"
    result = validate_external_url(smtp_url)
    if not result.ok:
        raise ValueError(f"SSRF blocked ({result.reason}) for SMTP host")
    password = os.environ.get(cfg.smtp_password_env or "", "")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.smtp_from
    msg["To"] = ", ".join(cfg.recipients)
    msg.attach(MIMEText(body, "plain"))
    context = ssl.create_default_context()
    if cfg.use_ssl:
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port,
                               context=context, timeout=cfg.timeout_seconds) as smtp:
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

---

### `quirk/notify/channels/webhook.py` (service/sender, request-response)

**Analog:** `quirk/util/url_allowlist.py` (validate_external_url reuse pattern, lines 95–161)

**Core pattern** (stdlib urllib + HMAC — no direct analog; follow RESEARCH Pattern 9):
```python
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.request

from quirk.util.url_allowlist import validate_external_url
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)

def send_webhook(cfg, payload: dict) -> None:
    url = os.environ.get(cfg.url_env, "")
    if not url:
        raise ValueError(f"Webhook URL env var {cfg.url_env!r} not set")
    # ISEC-01: SSRF check at delivery time
    result = validate_external_url(url)
    if not result.ok:
        raise ValueError(f"SSRF blocked ({result.reason}) for webhook")
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if cfg.hmac_key_env:
        key = os.environ.get(cfg.hmac_key_env, "").encode("utf-8")
        if key:
            sig = hmac.new(key, body, hashlib.sha256).hexdigest()
            req.add_header("X-QUIRK-Signature", f"sha256={sig}")
    with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
        if resp.status not in (200, 201, 202, 204):
            raise RuntimeError(f"Webhook returned HTTP {resp.status}")
```

---

### `quirk/models.py` — IntegrationDelivery model (model, CRUD)

**Analog:** `quirk/models.py` — `ScheduledRun` (lines 183–199) — same table-creation pattern

**New model** (copy column shape from ScheduledRun at lines 183–199):
```python
class IntegrationDelivery(Base):
    """Phase 101 NOTIFY-07 / ISEC-03: delivery audit log for all integration phases.

    Shared by Phases 103 (SIEM), 104 (Jira), 105 (ServiceNow).
    error_summary is always safe_str(exc) — never a raw exception.
    """
    __tablename__ = "integration_deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(String(64), nullable=False, index=True)  # ISO ts from current_session_ts
    finding_hash = Column(String(64), nullable=True)          # SHA256 dedup key (future phases)
    destination = Column(String(64), nullable=False)          # "slack" | "email" | "webhook"
    status = Column(String(16), nullable=False)               # "ok" | "failed"
    attempted_at = Column(DateTime, nullable=False)
    error_summary = Column(Text, nullable=True)               # safe_str(exc) — never raw exc
```

---

### `quirk/db.py` — `_ensure_integration_deliveries_table` + `init_db` extension (utility/migration, CRUD)

**Analog:** `quirk/db.py` — `_ensure_scheduled_tables` (lines 330–337) and `init_db` chain (lines 358–392)

**New helper** (copy from `_ensure_scheduled_tables` at lines 330–337):
```python
def _ensure_integration_deliveries_table(engine) -> None:
    """Phase 101 NOTIFY-07: create integration_deliveries table if absent (idempotent).

    IntegrationDelivery is registered on Base.metadata via import of quirk.models.
    Uses Base.metadata.create_all with checkfirst=True — same pattern as
    _ensure_scheduled_tables. New table only — not new columns — so create_all is correct.
    """
    Base.metadata.create_all(engine, checkfirst=True)
```

**init_db extension** (add after line 391, after `_ensure_scan_checkpoints_table`):
```python
    _ensure_integration_deliveries_table(engine)  # Phase 101 — NOTIFY-07
```

---

### `quirk/util/safe_exc.py` — extend `_SENSITIVE_PATTERNS` (utility, transform)

**Analog:** `quirk/util/safe_exc.py` — `_SENSITIVE_PATTERNS` tuple (lines 21–40)

**New patterns to append** (add after line 40, before the closing parenthesis):
```python
    # Phase 101 ISEC-02: Slack token and webhook URL shapes
    re.compile(r"xox[bpoa]-[0-9A-Za-z\-]{10,}"),          # Slack bot/user tokens
    re.compile(r"hooks\.slack\.com/services/[A-Za-z0-9/]+"),  # Slack incoming webhook URLs
    # Phase 101 ISEC-02: SMTP connection string with credentials
    re.compile(r"smtp[s]?://[^:@\s]+:[^@\s]+@"),           # SMTP conn string with password
```

---

### `quirk/cli/scheduler_cmd.py` — dispatch hook after line 162 (service, event-driven)

**Analog:** `quirk/cli/scheduler_cmd.py` — `_dispatch_schedule` (lines 109–163); insert after `db.commit()` at line 162

**Hook pattern** (deferred import to avoid circular imports — model from `quirk/util/optional_extra.py` local-import pattern):
```python
    # Phase 101 NOTIFY-01: dispatch notifications for this completed run.
    # Full try/except: notification failure must never propagate or corrupt scan record.
    try:
        from quirk.notify.dispatcher import dispatch_notifications
        dispatch_notifications(run=run, schedule=schedule, db=db)
    except Exception as exc:  # noqa: BLE001
        import logging
        from quirk.util.safe_exc import safe_str
        logging.getLogger(__name__).warning(
            "Notification dispatch error (scan record unaffected): %s", safe_str(exc)
        )
    return run
```

---

### `pyproject.toml` — `[notify]` extra + `[all]` inclusion (config)

**Analog:** `pyproject.toml` — `docx` extra + `[all]` inclusion (lines 84–98)

**New extra** (insert after the `docx` block at line 86, before `dev`):
```toml
notify = [
    "slack-sdk>=3.33.0",  # Phase 101 NOTIFY-03 — Slack incoming-webhook delivery
    # email: stdlib smtplib — no extra required
    # webhook: stdlib urllib — no extra required
]
```

**`[all]` extension** (add after line 98, alongside docx):
```toml
    "quirk-scanner[notify]",  # Phase 101 NOTIFY-03 — slack-sdk; no cryptography downgrade chain
```

**CI guard test** (`tests/test_install_all_includes_notify.py`) — copy structure from `tests/test_install_all_excludes_impacket.py` (lines 1–119) but assert `slack-sdk` IS present in the resolved set (inclusion guard, not exclusion).

---

## Test File Patterns

### `tests/test_notify_dispatcher.py` (test, event-driven)

**Analog:** `tests/test_scheduler_cmd.py` (lines 1–80)

**Setup pattern** (copy from `test_scheduler_cmd.py` lines 36–80):
```python
from __future__ import annotations

import pytest
from quirk.db import init_db, get_session
from quirk.models import ScheduledScan, ScheduledRun, IntegrationDelivery
from quirk.cli.scheduler_cmd import _utcnow_naive

def _make_db(tmp_path):
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    return db_path
```

**Trigger test shape:**
```python
def test_trigger_high_fires(tmp_path, monkeypatch):
    """NOTIFY-02: should_notify returns True when new_high > 0."""
    from quirk.notify.dispatcher import should_notify
    from quirk.intelligence.trends import TrendReport
    report = TrendReport(
        current_session_ts=None, previous_session_ts=None,
        current_score=70, previous_score=80, score_delta=-10,
        new_high=1, new_medium=0, new_low=0,
        resolved_high=0, resolved_medium=0, resolved_low=0,
        scan_errors_new_count=0, scan_errors_resolved_count=0,
    )
    assert should_notify(report) is True

def test_no_notify_on_first_scan(tmp_path):
    """NOTIFY-02: no notification when previous session is None (first scan)."""
    from quirk.notify.dispatcher import should_notify
    from quirk.intelligence.trends import TrendReport
    report = TrendReport(
        current_session_ts=None, previous_session_ts=None,
        current_score=70, previous_score=None, score_delta=None,
        new_high=0, new_medium=0, new_low=0,
        resolved_high=0, resolved_medium=0, resolved_low=0,
        scan_errors_new_count=0, scan_errors_resolved_count=0,
    )
    assert should_notify(report) is False  # score_delta is None must not trigger
```

### `tests/test_notify_slack.py` (test, request-response)

**Analog:** `tests/test_scheduler_cmd.py` (monkeypatch pattern)

**Lazy-import skip test:**
```python
def test_graceful_skip_missing_extra(monkeypatch, caplog):
    """ISEC-04: missing slack_sdk logs WARNING and returns without ImportError."""
    import importlib.util
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    import logging
    with caplog.at_level(logging.WARNING):
        from quirk.notify.channels.slack import send_slack
        send_slack(cfg=..., summary=...)
    assert "pip install quirk[notify]" in caplog.text
```

### `tests/test_integration_deliveries_schema.py` (test, CRUD)

**Analog:** `tests/test_scheduler_cmd.py` (init_db + query pattern, lines 37–41)

**Schema verification:**
```python
from sqlalchemy import inspect as sa_inspect
from quirk.db import init_db, get_engine

def test_integration_deliveries_table_created(tmp_path):
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    engine = get_engine(db_path)
    inspector = sa_inspect(engine)
    tables = inspector.get_table_names()
    assert "integration_deliveries" in tables
    cols = {c["name"] for c in inspector.get_columns("integration_deliveries")}
    assert cols >= {"id", "scan_id", "finding_hash", "destination",
                    "status", "attempted_at", "error_summary"}
```

---

## Shared Patterns

### SSRF Validation (ISEC-01)
**Source:** `quirk/util/url_allowlist.py` lines 95–161
**Apply to:** `quirk/notify/channels/slack.py`, `quirk/notify/channels/webhook.py`, `quirk/notify/channels/email.py` (SMTP host)
```python
from quirk.util.url_allowlist import validate_external_url

result = validate_external_url(url)  # allow_internal=False (default)
if not result.ok:
    raise ValueError(f"SSRF blocked ({result.reason}) for destination={destination!r}")
```
**Call at delivery time, not config-load time.** For SMTP: construct `https://{host}:{port}` and validate before connecting.

### Secret Scrubbing (ISEC-02)
**Source:** `quirk/util/safe_exc.py` lines 43–60
**Apply to:** All `except` clauses in delivery code; all `error_summary` writes to `integration_deliveries`
```python
from quirk.util.safe_exc import safe_str

except Exception as exc:
    row.error_summary = safe_str(exc)   # never str(exc) directly
    logger.warning("...: %s", safe_str(exc))
```

### Lazy-Import Gate (ISEC-04)
**Source:** `quirk/util/optional_extra.py` lines 159–167 (`find_spec` pattern)
**Apply to:** `quirk/notify/channels/slack.py` only (`slack_sdk`); email and webhook use stdlib
```python
from importlib.util import find_spec

if find_spec("slack_sdk") is None:
    logger.warning("Slack notification skipped — run `pip install quirk[notify]` to enable")
    return
# THEN import inside the dedicated helper function (not inside a branch of a larger function)
from slack_sdk.webhook import WebhookClient
```

### SQLAlchemy Model + init_db Pattern
**Source:** `quirk/models.py` lines 183–199 (ScheduledRun shape); `quirk/db.py` lines 330–337 + 388–391 (init_db chain)
**Apply to:** `IntegrationDelivery` model in `quirk/models.py`; `_ensure_integration_deliveries_table` + `init_db` extension in `quirk/db.py`

### Session Timestamp Discovery
**Source:** `quirk/dashboard/api/routes/trends.py` lines 41–60 (`_list_session_timestamps`)
**Apply to:** `quirk/notify/dispatcher.py` — `_find_two_sessions()` must use the same millisecond-precision `func.strftime("%Y-%m-%d %H:%M:%f")` grouping pattern to handle CR-05 (two scans per second).

### YAML Config Block Pattern
**Source:** `quirk/config.py` lines 374–494 (`config_from_dict` — nested raw.get + dataclass construction)
**Apply to:** `quirk/notify/config.py` — `_parse_notify_cfg(raw)` inner function that maps YAML keys to dataclass fields

---

## No Analog Found

All files have a close analog. The following use patterns from RESEARCH.md because the codebase has no existing SMTP or webhook sender:

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `quirk/notify/channels/email.py` (core smtp logic) | service | request-response | No existing smtplib usage in codebase; use RESEARCH Pattern 8 verbatim |
| `quirk/notify/channels/webhook.py` (HMAC signing) | service | request-response | No existing urllib+HMAC pattern in codebase; use RESEARCH Pattern 9 verbatim |

---

## Metadata

**Analog search scope:** `quirk/`, `quirk/util/`, `quirk/cli/`, `quirk/reports/`, `quirk/models.py`, `quirk/db.py`, `quirk/config.py`, `quirk/intelligence/trends.py`, `quirk/dashboard/api/routes/trends.py`, `tests/`
**Files scanned:** 15 source files read directly
**Pattern extraction date:** 2026-05-24
