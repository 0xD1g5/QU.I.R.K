"""quirk.notify.config — Notification configuration loader (Phase 101 NOTIFY-06).

Resolves the QUIRK config YAML (via QUIRK_CONFIG_PATH env var or an explicit
path arg), reads the [notifications] sub-block, and returns a NotifyCfg.

CRITICAL CONSTRAINT (Pitfall 1):
  The scheduler's --config is a SQLite .db path, NOT a YAML file.  This loader
  MUST resolve the YAML config via QUIRK_CONFIG_PATH (or an explicit path),
  never via the scheduler DB-path argument plumbed from _dispatch_schedule.  If a
  binary/non-YAML file is encountered the function silently returns None so
  notification failure never aborts a running scan.

NOTIFY-06: Secrets are stored as env-var NAMES (e.g. smtp_password_env="SMTP_PASS"),
  never as literal values.  The caller resolves os.environ[name] at delivery time.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml


# ---------------------------------------------------------------------------
# Dataclasses — env-var-NAME fields only, no literal-secret fields
# ---------------------------------------------------------------------------


@dataclass
class SlackNotifyCfg:
    """Slack incoming-webhook configuration (NOTIFY-03).

    slack_webhook_env — NAME of the env var holding the webhook URL.
    """

    slack_webhook_env: str              # name of env var holding the webhook URL
    dashboard_base_url: Optional[str] = None


@dataclass
class EmailNotifyCfg:
    """SMTP email notification configuration (NOTIFY-04).

    smtp_password_env — NAME of the env var holding the SMTP password.
    """

    smtp_host: str
    smtp_port: int = 587
    smtp_from: str = ""
    recipients: List[str] = field(default_factory=list)
    smtp_user: Optional[str] = None
    smtp_password_env: Optional[str] = None   # env-var NAME, not the password
    use_ssl: bool = False
    timeout_seconds: int = 10


@dataclass
class WebhookNotifyCfg:
    """Generic outbound webhook configuration (NOTIFY-05).

    url_env      — NAME of the env var holding the target webhook URL.
    hmac_key_env — NAME of the env var holding the HMAC signing key (optional).
    """

    url_env: str
    hmac_key_env: Optional[str] = None   # env-var NAME, not the key material
    timeout_seconds: int = 10


@dataclass
class NotifyCfg:
    """Top-level notification configuration object.

    trigger_score_floor — minimum score delta (negative) that triggers a
        notification.  Defaults to -5 (notify when score drops by >5 points).
    """

    trigger_score_floor: int = -5
    slack: Optional[SlackNotifyCfg] = None
    email: Optional[EmailNotifyCfg] = None
    webhook: Optional[WebhookNotifyCfg] = None


# ---------------------------------------------------------------------------
# Private helpers — mirrors config_from_dict nested raw.get() style
# ---------------------------------------------------------------------------


def _parse_slack(raw: dict) -> Optional[SlackNotifyCfg]:
    if not raw:
        return None
    webhook_env = raw.get("slack_webhook_env")
    if not webhook_env:
        return None
    return SlackNotifyCfg(
        slack_webhook_env=str(webhook_env),
        dashboard_base_url=raw.get("dashboard_base_url") or None,
    )


def _parse_email(raw: dict) -> Optional[EmailNotifyCfg]:
    if not raw:
        return None
    smtp_host = raw.get("smtp_host")
    if not smtp_host:
        return None
    recipients_raw = raw.get("recipients") or []
    if isinstance(recipients_raw, str):
        recipients_raw = [recipients_raw]
    return EmailNotifyCfg(
        smtp_host=str(smtp_host),
        smtp_port=int(raw.get("smtp_port", 587)),
        smtp_from=str(raw.get("smtp_from", "") or ""),
        recipients=list(recipients_raw),
        smtp_user=raw.get("smtp_user") or None,
        smtp_password_env=raw.get("smtp_password_env") or None,
        use_ssl=bool(raw.get("use_ssl", False)),
        timeout_seconds=int(raw.get("timeout_seconds", 10)),
    )


def _parse_webhook(raw: dict) -> Optional[WebhookNotifyCfg]:
    if not raw:
        return None
    url_env = raw.get("url_env")
    if not url_env:
        return None
    return WebhookNotifyCfg(
        url_env=str(url_env),
        hmac_key_env=raw.get("hmac_key_env") or None,
        timeout_seconds=int(raw.get("timeout_seconds", 10)),
    )


def _parse_notify_cfg(raw: dict) -> NotifyCfg:
    """Construct NotifyCfg from the raw [notifications] dict.

    Mirrors config_from_dict's nested raw.get() → dataclass construction style.
    Only present sub-blocks are populated; absent channels are None.
    """
    floor = int(raw.get("trigger_score_floor", -5))
    slack_raw = raw.get("slack") or {}
    email_raw = raw.get("email") or {}
    webhook_raw = raw.get("webhook") or {}
    return NotifyCfg(
        trigger_score_floor=floor,
        slack=_parse_slack(slack_raw),
        email=_parse_email(email_raw),
        webhook=_parse_webhook(webhook_raw),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_notifications_config(path: str | None = None) -> "NotifyCfg | None":
    """Load the [notifications] block from the QUIRK YAML config.

    Priority: explicit path > QUIRK_CONFIG_PATH env var > None (disabled).

    Returns None when:
    - No path is resolvable (notifications disabled — not an error).
    - The file does not exist.
    - The file is not valid YAML (e.g. a SQLite .db file — Pitfall 1).
    - The YAML has no [notifications] top-level key.

    Notification config failure MUST NEVER abort a running scan.
    """
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
        # Binary / malformed / non-YAML files (Pitfall 1) return None silently.
        return None
