---
phase: 101-notification-fan-out-security-foundation
fixed_at: 2026-05-24T21:25:00Z
review_path: .planning/phases/101-notification-fan-out-security-foundation/101-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 101: Code Review Fix Report

**Fixed at:** 2026-05-24T21:25:00Z
**Source review:** .planning/phases/101-notification-fan-out-security-foundation/101-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, CR-02, WR-01, WR-02; IN-01 excluded per instructions)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: SSRF Bypass via HTTP Redirect in webhook.py

**Files modified:** `quirk/notify/channels/webhook.py`, `tests/test_notify_webhook.py`
**Commit:** 3fbc18b (test updates in d6971be)
**Applied fix:** Added `_NoRedirectHandler(urllib.request.HTTPRedirectHandler)` class whose
`redirect_request` method raises `urllib.error.HTTPError` instead of following any 3xx redirect.
Changed `urllib.request.urlopen(req, ...)` to `urllib.request.build_opener(_NoRedirectHandler).open(req, ...)`.
Updated the 5 pre-existing tests that patched `urllib.request.urlopen` to instead patch
`urllib.request.build_opener` (via a `_FakeOpener` / `_make_fake_build_opener` helper).
Added new regression test `test_redirect_blocked_by_no_redirect_handler` that directly
exercises `_NoRedirectHandler.redirect_request` and asserts it raises `HTTPError(302)` with
"Redirect blocked" in the reason.

### CR-02: TypeError Crash in Email Body When score_delta Is None

**Files modified:** `quirk/notify/dispatcher.py`, `tests/test_notify_dispatcher.py`
**Commit:** a4c85f6
**Applied fix:** In `_channel_send_email`, introduced `delta_str` using the same guard as
`slack.py`: `f"{summary.score_delta:+d}" if summary.score_delta is not None else "N/A"`.
Replaced the bare `{summary.score_delta:+d}` f-string in the body with `{delta_str}`.
Added regression test `test_email_score_delta_none_does_not_crash` covering the first-scan
scenario (new_high=3, score_delta=None): asserts delivery row status is "ok" (not "failed"),
transport was reached, and the body contains "N/A".

### WR-01: db.commit() Outside Per-Channel Try/Except in dispatcher.py

**Files modified:** `quirk/notify/dispatcher.py`
**Commit:** 1e6fa41
**Applied fix:** Replaced the pattern of `db.add(row_X)` / `db.commit()` after each channel
block with a collect-then-commit approach: an `audit_rows` list accumulates one
`IntegrationDelivery` per enabled channel, then a single `for row in audit_rows: db.add(row)`
followed by one `db.commit()` (wrapped in its own try/except logging the failure) at the end.
This means a transient DB failure on one channel's row write no longer propagates through
`dispatch_notifications` and silently abandons subsequent channels' delivery attempts and
audit rows.

### WR-02: Path Traversal via schedule.name in scheduler_cmd.py

**Files modified:** `quirk/cli/scheduler_cmd.py`
**Commit:** d6971be
**Applied fix:** Added `import re` to the module imports. At the output directory construction
site (just before `output_dir = ...`), added `_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")`
and `safe_name = schedule.name if _SAFE_NAME_RE.match(schedule.name) else "unnamed"`.
Changed `Path("output/scheduled") / schedule.name / ...` to use `safe_name` instead.
A schedule name like `../../../etc/cron.d` now falls back to `"unnamed"` rather than
escaping the `output/scheduled/` tree.

## Skipped Issues

None.

---

**Verification:** `python -m compileall quirk/notify quirk/cli/scheduler_cmd.py` clean.
Full notify test suite: 108 passed, 1 deselected (pre-existing deselection unrelated to fixes).

_Fixed: 2026-05-24T21:25:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
