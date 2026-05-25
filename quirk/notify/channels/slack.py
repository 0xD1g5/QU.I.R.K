"""quirk.notify.channels.slack — Slack incoming-webhook delivery (Phase 101 NOTIFY-03).

Security controls:
  ISEC-01: validate_external_url() called at delivery time, before any connection.
  ISEC-04: slack_sdk is an optional extra ([notify]).  A missing slack_sdk is
           caught via find_spec() and logs an advisory WARNING — no ImportError.

Local-import shadow trap guard (MEMORY note):
  The `from slack_sdk.webhook import WebhookClient` import MUST live inside the
  dedicated send_slack() helper, AFTER the find_spec gate.  It must never appear
  at module top level or inside a branch of a larger function.
"""
from __future__ import annotations

import logging
import os
from importlib.util import find_spec

from quirk.util.url_allowlist import validate_external_url

logger = logging.getLogger(__name__)


def send_slack(cfg, summary) -> None:
    """Send a Slack notification via the incoming-webhook URL.

    Args:
        cfg: SlackNotifyCfg — env-var name for the webhook URL + optional
             dashboard_base_url.
        summary: DriftSummary — shared content model built by build_drift_summary().

    Raises:
        ValueError: When the webhook URL fails SSRF validation (ISEC-01).
        RuntimeError: When Slack's API returns a non-200 status code.
    """
    # ISEC-04: skip gracefully if slack_sdk is not installed
    if find_spec("slack_sdk") is None:
        logger.warning(
            "Slack notification skipped — slack_sdk not installed; "
            "run `pip install quirk[notify]` to enable"
        )
        return

    # Resolve the webhook URL from the named env var
    url = os.environ.get(cfg.slack_webhook_env, "")
    if not url:
        logger.warning(
            "Slack notification skipped — env var %r not set",
            cfg.slack_webhook_env,
        )
        return

    # ISEC-01: SSRF validation at delivery time, before any connection
    result = validate_external_url(url)
    if not result.ok:
        raise ValueError(
            f"SSRF blocked ({result.reason}) for Slack webhook URL"
        )

    # Lazy import — AFTER find_spec gate, inside this dedicated helper only.
    # This placement is the shadow-trap-safe pattern: no other branch of any
    # enclosing function references WebhookClient, so the name is never made
    # function-local for branches that run before this import.
    from slack_sdk.webhook import WebhookClient  # noqa: PLC0415

    client = WebhookClient(url)
    text = _format_slack_text(summary)
    response = client.send(text=text)

    if response.status_code != 200:
        raise RuntimeError(
            f"Slack webhook returned HTTP {response.status_code}: {response.body}"
        )


def _format_slack_text(summary) -> str:
    """Format a human-readable Slack message from a DriftSummary.

    The Slack channel receives a human-readable text message (unlike the webhook
    channel which sends to_integration_payload() machine-readable JSON).
    Host/port/protocol topology MAY appear here — Slack is an operator-controlled
    channel, not an integration endpoint.
    """
    score_str = (
        str(summary.current_score) if summary.current_score is not None else "N/A"
    )
    prev_str = (
        str(summary.previous_score) if summary.previous_score is not None else "N/A"
    )
    delta_str = (
        f"{summary.score_delta:+d}" if summary.score_delta is not None else "N/A"
    )

    lines = [
        f"*QUIRK Quantum-Readiness Alert* — Score Band: {summary.score_band}",
        f"Score: {score_str} (was {prev_str}, delta {delta_str})",
        f"New findings — HIGH: {summary.new_high}  MEDIUM: {summary.new_medium}"
        f"  LOW: {summary.new_low}",
    ]

    if summary.dashboard_url:
        lines.append(f"Dashboard: {summary.dashboard_url}")

    return "\n".join(lines)
