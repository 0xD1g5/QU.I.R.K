---
phase: 101-notification-fan-out-security-foundation
reviewed: 2026-05-24T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - quirk/notify/dispatcher.py
  - quirk/notify/config.py
  - quirk/notify/payload.py
  - quirk/notify/channels/slack.py
  - quirk/notify/channels/email.py
  - quirk/notify/channels/webhook.py
  - quirk/cli/scheduler_cmd.py
  - quirk/db.py
  - quirk/models.py
  - quirk/util/safe_exc.py
  - pyproject.toml
findings:
  critical: 2
  warning: 2
  info: 1
  total: 5
status: issues_found
---

# Phase 101: Code Review Report

**Reviewed:** 2026-05-24T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the Phase 101 ANCHOR integration-security foundation: dispatcher fan-out
orchestrator, notification config loader, payload whitelisting, all three channel
senders (Slack, email, webhook), the scheduler hook integration, DB/model additions,
safe_exc, and pyproject.toml.

The overall architecture is sound — QUIRK_CONFIG_PATH isolation is correctly implemented,
safe_str is consistently used for error_summary, the per-channel failure isolation pattern
is correctly structured, and the HMAC signing and env-var-name indirection for secrets are
correctly implemented.

Two blockers require fixes before ship: a redirect-following SSRF bypass in the webhook
channel that defeats the validate_external_url gate, and a TypeError crash in the email
body formatter when score_delta is None on the first-scan-with-new-HIGH-findings scenario.
Two warnings cover a DB commit ordering issue that silently aborts downstream audit rows on
commit failure, and a pre-existing path traversal in the scheduler output directory
construction.

## Critical Issues

### CR-01: SSRF Bypass via HTTP Redirect in webhook.py

**File:** `quirk/notify/channels/webhook.py:70`

**Issue:** `urllib.request.urlopen(req, timeout=cfg.timeout_seconds)` uses the default
urllib opener which installs `HTTPRedirectHandler`. This follows HTTP 301/302/307 redirects
automatically, *after* the `validate_external_url()` check at line 47 has already passed.
An attacker who controls the webhook endpoint (or a compromised CDN in front of it) can
return `HTTP 302 Location: http://169.254.169.254/latest/meta-data/iam/security-credentials/`
and urllib will follow the redirect to the cloud metadata service, bypassing SSRF protection
entirely and potentially exfiltrating instance credentials.

Attack chain:
1. Operator configures `WEBHOOK_URL=https://trusted-external-host.example.com/hook`
2. `validate_external_url("https://trusted-external-host.example.com/hook")` → `ok=True`
3. `urlopen(POST to trusted-external-host...)` → server responds `302 → http://169.254.169.254/...`
4. `HTTPRedirectHandler` follows redirect → AWS/GCP metadata service returns IAM credentials
5. Response body is available to the caller; scan audit row records `status=ok`

**Fix:** Build a no-redirect opener before calling `urlopen`:

```python
import urllib.error
import urllib.request

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block all HTTP redirects to prevent post-validation SSRF bypass."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirect blocked (SSRF guard)", headers, fp)

def send_webhook(cfg, payload: dict) -> None:
    url = os.environ.get(cfg.url_env, "")
    if not url:
        raise ValueError(f"Webhook URL env var {cfg.url_env!r} not set")

    result = validate_external_url(url)
    if not result.ok:
        raise ValueError(f"SSRF blocked ({result.reason}) for webhook URL")

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    if cfg.hmac_key_env:
        key = os.environ.get(cfg.hmac_key_env, "").encode("utf-8")
        if key:
            sig = hmac.new(key, body, hashlib.sha256).hexdigest()
            req.add_header("X-QUIRK-Signature", f"sha256={sig}")

    # Use no-redirect opener so a post-validation redirect cannot bypass SSRF check
    opener = urllib.request.build_opener(_NoRedirectHandler)
    with opener.open(req, timeout=cfg.timeout_seconds) as resp:
        if resp.status not in (200, 201, 202, 204):
            raise RuntimeError(f"Webhook returned HTTP {resp.status}")
```

Note: The Slack channel uses `slack_sdk.WebhookClient` which may also follow redirects;
verify that `slack_sdk >= 3.33.0` does not follow redirects or apply the same guard there.

---

### CR-02: TypeError Crash in Email Body When score_delta Is None on First HIGH Finding

**File:** `quirk/notify/dispatcher.py:55`

**Issue:** The email body f-string uses `{summary.score_delta:+d}` without a None guard.
`DriftSummary.score_delta` is `Optional[int]` (payload.py line 46). `should_notify()`
can return `True` via the `report.new_high > 0` branch (dispatcher.py line 120) even
when `score_delta is None` — specifically on the very first scan if it discovers HIGH
findings. In this scenario `_channel_send_email` is called with `summary.score_delta = None`,
and `f"{None:+d}"` raises `TypeError: unsupported format string passed to NoneType.__format__`.

Verified:
```python
>>> score_delta = None
>>> f"{score_delta:+d}"
TypeError: unsupported format string passed to NoneType.__format__
```

The TypeError is caught by the per-channel except in dispatcher.py, so it does not corrupt
the scan record, but the email notification is silently suppressed (audit row shows `status=failed`)
precisely on the most important alert — the first scan that finds HIGH-severity findings.

The Slack formatter at `slack.py:91` correctly guards against this:
`f"{summary.score_delta:+d}" if summary.score_delta is not None else "N/A"`.
The email body builder is the only site that is unguarded.

**Fix:** Apply the same guard used in `_format_slack_text`:

```python
def _channel_send_email(cfg, summary) -> None:
    from quirk.notify.channels.email import send_email
    delta_str = f"{summary.score_delta:+d}" if summary.score_delta is not None else "N/A"
    subject = f"QUIRK Alert: {summary.new_high} new HIGH finding(s) — score {summary.current_score}"
    body = (
        f"QUIRK Quantum-Readiness Alert\n"
        f"Score: {summary.current_score} (was {summary.previous_score}, "
        f"delta {delta_str})\n"
        f"New findings — HIGH: {summary.new_high}  MEDIUM: {summary.new_medium}  "
        f"LOW: {summary.new_low}\n"
    )
    if summary.dashboard_url:
        body += f"\nDashboard: {summary.dashboard_url}\n"
    send_email(cfg, subject=subject, body=body)
```

---

## Warnings

### WR-01: db.commit() for IntegrationDelivery Rows Is Outside Per-Channel Try/Except

**File:** `quirk/notify/dispatcher.py:210-211,232-233,252-253`

**Issue:** The pattern for each channel is:

```python
row_X = IntegrationDelivery(...)
try:
    _channel_send_X(...)
except Exception as exc:
    row_X.status = "failed"
    row_X.error_summary = safe_str(exc)
    logger.warning(...)
db.add(row_X)    # ← outside try/except
db.commit()      # ← outside try/except
```

`db.add()` and `db.commit()` are outside the per-channel try/except block. If `db.commit()`
raises (e.g., a transient SQLite lock, connection reset, or schema constraint violation),
the exception propagates out of `dispatch_notifications`. The outer try/except in
`scheduler_cmd.py:168-176` catches it and logs it — so the scan record is safe — but all
*subsequent* channel audit rows are skipped entirely. A DB failure during the Slack commit
silently abandons the email and webhook audit rows (and their delivery attempts).

Additionally, if a channel delivery raises and the session enters a partial error state,
the subsequent `db.commit()` for the *next* channel's row may encounter a dirty session
depending on SQLAlchemy's internal state tracking.

**Fix:** Wrap both `db.add()` and `db.commit()` inside a per-channel nested try/except, or
use `db.add()` for all three rows first and commit once at the end (also reduces round-trips):

```python
# Option A: commit all rows in one shot after all channels
rows = []
if notify_cfg.slack is not None:
    row_slack = IntegrationDelivery(scan_id=scan_id, destination="slack", status="ok", ...)
    try:
        _channel_send_slack(notify_cfg.slack, summary)
    except Exception as exc:
        row_slack.status = "failed"
        row_slack.error_summary = safe_str(exc)
        logger.warning("Delivery failed (slack): %s", safe_str(exc))
    rows.append(row_slack)

# ... repeat for email, webhook ...

for row in rows:
    db.add(row)
try:
    db.commit()
except Exception as exc:
    logger.warning("Audit row commit failed: %s", safe_str(exc))
```

---

### WR-02: schedule.name Used Unvalidated in Output Directory Path (Path Traversal)

**File:** `quirk/cli/scheduler_cmd.py:129`

**Issue:** The output directory is constructed as:

```python
output_dir = (
    Path("output/scheduled") / schedule.name / now.strftime("%Y%m%d-%H%M%S")
)
output_dir.mkdir(parents=True, exist_ok=True)
```

`schedule.name` is a `String(255)` column read from the database without sanitization.
If a schedule name contains path-traversal sequences (`../../../etc/cron.d`), `Path` will
resolve them and `mkdir(parents=True)` will create directories outside the intended
`output/scheduled/` tree:

```python
>>> from pathlib import Path
>>> (Path("output/scheduled") / "../../../etc" / "20240101-120000")
PosixPath('output/scheduled/../../../etc/20240101-120000')
```

While this requires DB write access (which implies prior compromise), the `--config` DB path
is operator-supplied, and the scheduler runs as the application user in potentially privileged
environments. This is pre-existing Phase 63 code but is included in the review scope file.

**Fix:** Sanitize `schedule.name` before use in the path, or resolve and check that the result
stays within the expected prefix:

```python
import re
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")

safe_name = schedule.name if _SAFE_NAME_RE.match(schedule.name) else "unnamed"
output_dir = Path("output/scheduled") / safe_name / now.strftime("%Y%m%d-%H%M%S")
# Optionally: assert output_dir.resolve().is_relative_to(Path("output/scheduled").resolve())
```

---

## Info

### IN-01: SMTP SSRF Validation Silently Degrades for Bare IPv6 smtp_host Values

**File:** `quirk/notify/channels/email.py:37`

**Issue:** The SSRF check constructs a URL as `f"https://{cfg.smtp_host}:{cfg.smtp_port}"`.
When `smtp_host` is a bare IPv6 address without brackets (e.g., `::1` instead of `[::1]`),
`urlparse` produces `hostname=None` from the malformed URL `https://::1:587`. The validator
then falls through to the DNS path with an empty string host, which resolves to `0.0.0.0`
via `socket.gethostbyname("")`, which is classified as private and correctly blocked — but
the block is accidental, not intentional. The error message would name the wrong reason code,
and the behavior could change across OS or Python versions.

The `smtplib.SMTP` constructor accepts bare IPv6 natively, so an operator-supplied
`smtp_host = "::1"` would be blocked (via the accidental 0.0.0.0 path), but the SSRF
check's intent and the actual network connection target are misaligned.

**Fix:** Normalize the SMTP host before constructing the validation URL:

```python
def _smtp_ssrf_url(smtp_host: str, smtp_port: int) -> str:
    """Build a validatable URL from smtp_host, bracketing IPv6 literals."""
    import ipaddress
    try:
        ip = ipaddress.ip_address(smtp_host)
        if isinstance(ip, ipaddress.IPv6Address):
            return f"https://[{smtp_host}]:{smtp_port}"
    except ValueError:
        pass
    return f"https://{smtp_host}:{smtp_port}"
```

---

_Reviewed: 2026-05-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
