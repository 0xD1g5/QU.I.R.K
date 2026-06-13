"""quirk.notify.channels.email — Email delivery via stdlib smtplib (Phase 101 NOTIFY-04).

Security controls:
  ISEC-01: validate_external_url() called on the SMTP host (as https://host:port)
           at delivery time, before any connection is made.
  Pitfall 3: timeout is ALWAYS passed to both SMTP and SMTP_SSL constructors so a
           hung SMTP server can never stall the scheduler loop indefinitely.

  SSRF-05 / D-03 — DNS-rebinding compensating control (NOT IP-pinned):
    smtplib re-resolves the SMTP host at connect time, leaving a TOCTOU window
    between the ISEC-01 validation and the actual connection. Unlike the
    rest_fuzzer requests/raw-socket paths (which pin the validated IP via
    PinnedIPAdapter / server_hostname), full smtplib IP-pinning is explicitly
    OUT OF SCOPE for Phase 123 per decision D-03. The residual risk is accepted
    as a *documented compensating control* because: (1) the SMTP host is
    operator-configured, not attacker-controlled; (2) notification delivery is
    opt-in; (3) connections are TLS-verified (SMTP_SSL / STARTTLS), so a TCP
    misdirection to a rebind target fails certificate hostname verification.
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from quirk.util.url_allowlist import validate_external_url

logger = logging.getLogger(__name__)


def send_email(cfg, subject: str, body: str) -> None:
    """Deliver an email alert via stdlib smtplib.

    Args:
        cfg: EmailNotifyCfg — SMTP connection settings with env-var name for
             the password (secret resolved at delivery time, never persisted).
        subject: Email subject line.
        body: Plain-text email body.

    Raises:
        ValueError: When the SMTP host fails SSRF validation (ISEC-01).
    """
    # ISEC-01: validate the SMTP host as a URL to block metadata IPs and
    # loopback/RFC1918 addresses before connecting.
    smtp_url = f"https://{cfg.smtp_host}:{cfg.smtp_port}"
    result = validate_external_url(smtp_url)
    if not result.ok:
        raise ValueError(
            f"SSRF blocked ({result.reason}) for SMTP host {cfg.smtp_host!r}"
        )

    # Resolve the SMTP password from the env-var name at delivery time.
    password = os.environ.get(cfg.smtp_password_env or "", "")

    # Build the MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.smtp_from
    msg["To"] = ", ".join(cfg.recipients)
    msg.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()

    if cfg.use_ssl:
        # SSL from the start (port 465 pattern)
        with smtplib.SMTP_SSL(
            cfg.smtp_host,
            cfg.smtp_port,
            context=context,
            timeout=cfg.timeout_seconds,
        ) as smtp:
            if cfg.smtp_user:
                smtp.login(cfg.smtp_user, password)
            smtp.sendmail(cfg.smtp_from, cfg.recipients, msg.as_string())
    else:
        # Plaintext upgrade to TLS via STARTTLS (port 587 pattern)
        with smtplib.SMTP(
            cfg.smtp_host,
            cfg.smtp_port,
            timeout=cfg.timeout_seconds,
        ) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            if cfg.smtp_user:
                smtp.login(cfg.smtp_user, password)
            smtp.sendmail(cfg.smtp_from, cfg.recipients, msg.as_string())
