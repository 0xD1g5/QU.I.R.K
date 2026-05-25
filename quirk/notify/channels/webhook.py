"""quirk.notify.channels.webhook — Generic outbound webhook delivery (Phase 101 NOTIFY-05).

Security controls:
  ISEC-01: validate_external_url() called at delivery time before any urlopen.
           _NoRedirectHandler additionally blocks post-validation redirect bypass
           (SSRF guard: any 3xx redirect is refused rather than followed).
  ISEC-03: caller MUST pass to_integration_payload(report) output — the webhook
           body contains only whitelisted aggregate fields, no topology detail.
  HMAC:    Optional X-QUIRK-Signature: sha256=<hexdigest> header when a signing
           key is configured via hmac_key_env.
  Pitfall 3: timeout ALWAYS passed to urlopen so a hung endpoint cannot stall
           the scheduler loop.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.request

from quirk.util.url_allowlist import validate_external_url

logger = logging.getLogger(__name__)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block all HTTP redirects to prevent post-validation SSRF bypass.

    urllib.request.urlopen follows 3xx redirects by default via HTTPRedirectHandler.
    An attacker-controlled endpoint returning 302 → http://169.254.169.254/... would
    bypass the validate_external_url() pre-connection check.  This handler refuses
    any redirect by raising HTTPError, keeping the connection to the validated URL.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code, "Redirect blocked (SSRF guard)", headers, fp
        )


def send_webhook(cfg, payload: dict) -> None:
    """POST a JSON payload to the configured webhook URL.

    Args:
        cfg: WebhookNotifyCfg — env-var names for the URL and optional HMAC key.
        payload: The dict to POST.  MUST be the output of to_integration_payload()
                 (whitelisted aggregates only — no host/port/protocol topology).

    Raises:
        ValueError: When the URL env var is not set or the URL fails SSRF
                    validation (ISEC-01).
        RuntimeError: When the endpoint returns a non-2xx HTTP status code.
    """
    # Resolve the webhook URL from the named env var
    url = os.environ.get(cfg.url_env, "")
    if not url:
        raise ValueError(
            f"Webhook URL env var {cfg.url_env!r} not set"
        )

    # ISEC-01: SSRF validation at delivery time, before any urlopen call
    result = validate_external_url(url)
    if not result.ok:
        raise ValueError(
            f"SSRF blocked ({result.reason}) for webhook URL"
        )

    # JSON-encode the payload (caller provides whitelisted aggregates only)
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    # Optional HMAC-SHA256 signing
    if cfg.hmac_key_env:
        key = os.environ.get(cfg.hmac_key_env, "").encode("utf-8")
        if key:
            sig = hmac.new(key, body, hashlib.sha256).hexdigest()
            req.add_header("X-QUIRK-Signature", f"sha256={sig}")

    # Use no-redirect opener so a post-validation redirect cannot bypass SSRF check
    opener = urllib.request.build_opener(_NoRedirectHandler)
    with opener.open(req, timeout=cfg.timeout_seconds) as resp:
        if resp.status not in (200, 201, 202, 204):
            raise RuntimeError(
                f"Webhook returned HTTP {resp.status}"
            )
