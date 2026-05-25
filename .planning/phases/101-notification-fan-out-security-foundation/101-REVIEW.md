---
phase: 101-notification-fan-out-security-foundation
reviewed: 2026-05-24T00:00:00Z
depth: standard
iteration: 2
files_reviewed: 4
files_reviewed_list:
  - quirk/notify/channels/webhook.py
  - quirk/notify/dispatcher.py
  - quirk/cli/scheduler_cmd.py
  - quirk/notify/channels/email.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 101: Code Review Report (Iteration 2 — Post-Fix Verification)

**Reviewed:** 2026-05-24T00:00:00Z
**Depth:** standard
**Iteration:** 2 (--auto fix/re-review loop)
**Files Reviewed:** 4
**Status:** clean

## Summary

This is the iteration-2 re-review verifying the four fixes applied after the iteration-1 findings
(CR-01 SSRF redirect bypass, CR-02 score_delta=None TypeError, WR-01 audit-commit isolation,
WR-02 path traversal). All four fixes are confirmed correct and complete. No new Critical or
Warning issues were introduced. Two Info-level observations remain; neither is blocking.

---

### CR-01 — webhook.py SSRF redirect bypass (FIXED, CONFIRMED)

`_NoRedirectHandler` overrides `redirect_request()` and raises `urllib.error.HTTPError`
unconditionally. `urllib.request.HTTPRedirectHandler` routes every 3xx status code (301, 302, 303,
307, 308) through `redirect_request()` before following the redirect, so raising there blocks all
redirect variants without needing to enumerate individual codes.

The opener is constructed with `urllib.request.build_opener(_NoRedirectHandler)` which replaces
the default `HTTPRedirectHandler` with the blocking variant, and the actual request is issued via
`opener.open(req, timeout=cfg.timeout_seconds)` — not via the default `urlopen`. There is no
fallback path to the redirect-following opener. Fix is correct and complete.

---

### CR-02 — dispatcher.py score_delta=None email TypeError (FIXED, CONFIRMED)

`_channel_send_email` now guards `score_delta` before formatting (dispatcher.py lines 52-54):

```python
delta_str = (
    f"{summary.score_delta:+d}" if summary.score_delta is not None else "N/A"
)
```

No other `{...:+d}` or `{...:d}` format specifiers appear on Optional fields in the email
subject or body. `current_score` and `previous_score` appear in the body with bare interpolation
only (no format spec), which renders safely as `"None"` string rather than raising TypeError.
Fix is correct and complete.

---

### WR-01 — dispatcher.py audit-commit isolation (FIXED, CONFIRMED)

All three per-channel audit rows are collected into an `audit_rows` list after their respective
delivery attempts. Delivery failures are caught per-channel and set `row.status = "failed"` /
`row.error_summary = safe_str(exc)` without touching the DB. After all channels have been
attempted, the rows are bulk-added with `db.add(row)` and committed once in a single
`try/except`-wrapped `db.commit()` (dispatcher.py lines 264-269). A commit failure logs a warning
but cannot skip any channel's delivery — deliveries have already completed at that point.

The scan record commit (line 169) precedes the entire fan-out block. The bonus `run.scan_id`
assignment (lines 179-181) only fires when `run.scan_id is None` and commits only the already-
persisted run row, not audit rows. NOTIFY-07 scan-record isolation is intact. Fix is correct and
complete.

---

### WR-02 — scheduler_cmd.py path traversal via schedule.name (FIXED, CONFIRMED)

The allowlist regex `r"^[a-zA-Z0-9_\-]{1,128}$"` (line 133) accepts only alphanumerics,
underscores, and hyphens up to 128 characters. Names failing the check are replaced with the
literal string `"unnamed"` — no truncation, no partial substitution, no character-by-character
transform that could smuggle a traversal sequence through. Valid names pass unchanged, so no
valid name can collide with another valid name through the sanitization step. Fix is correct and
complete. One edge case for multiple invalid-named schedules is noted below as IN-01.

---

## Info

### IN-01: Multiple invalid-named schedules share an output directory within the same second

**File:** `quirk/cli/scheduler_cmd.py:134-137`

**Issue:** When more than one `ScheduledScan` has a name that fails the `_SAFE_NAME_RE`
allowlist, all of them map to the directory component `"unnamed"`. The timestamp suffix uses
`%Y%m%d-%H%M%S` (one-second precision). If two such schedules are dispatched in the same
calendar second — possible if the due-schedules loop has many back-logged entries — both call
`mkdir("output/scheduled/unnamed/<same-timestamp>", exist_ok=True)` and write scan output into
the same directory. The `--output` argument for both subprocesses is identical, so artifacts
co-mingle silently. This is not a security issue (no path escapes `output/scheduled/`), but
post-hoc audit of outputs becomes ambiguous.

**Fix:** Append the schedule's integer primary key to the fallback to guarantee uniqueness:
```python
safe_name = (
    schedule.name
    if _SAFE_NAME_RE.match(schedule.name)
    else f"unnamed-{schedule.id}"
)
```

---

### IN-02: Email subject renders current_score as literal `None` string when score is absent

**File:** `quirk/notify/dispatcher.py:55`

**Issue:** The email subject is:
```python
subject = f"QUIRK Alert: {summary.new_high} new HIGH finding(s) — score {summary.current_score}"
```
`DriftSummary.current_score` is `Optional[int]`. On a first-ever scan, `current_score` can be
`None`, producing `"QUIRK Alert: 1 new HIGH finding(s) — score None"` — visually broken for
recipients. The Slack formatter in `slack.py:_format_slack_text` already applies the correct
guard (`str(summary.current_score) if summary.current_score is not None else "N/A"`); the email
formatter should be consistent.

This is not a crash — bare interpolation of `None` does not raise — but the rendered string is
user-visible and looks like a bug.

**Fix:** Mirror the Slack formatter's guard in `_channel_send_email`:
```python
score_str = str(summary.current_score) if summary.current_score is not None else "N/A"
prev_str  = str(summary.previous_score) if summary.previous_score is not None else "N/A"
subject = f"QUIRK Alert: {summary.new_high} new HIGH finding(s) — score {score_str}"
body = (
    f"QUIRK Quantum-Readiness Alert\n"
    f"Score: {score_str} (was {prev_str}, delta {delta_str})\n"
    f"New findings — HIGH: {summary.new_high}  MEDIUM: {summary.new_medium}  "
    f"LOW: {summary.new_low}\n"
)
```

---

_Reviewed: 2026-05-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2 — all CR/WR findings from iteration 1 confirmed resolved; status: clean_
