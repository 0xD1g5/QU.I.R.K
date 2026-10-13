---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger part 224-13, docs/configuration.md Notifications / Jira)
priority: low
area: quirk/notify/dispatcher.py, quirk/notify/channels/slack.py, quirk/cli/ticket_cmd.py
status: pending
resolves_phase: null
---

# A skipped Slack delivery is audited as `ok`; two install hints name the wrong package

The Slack audit row is created with `status="ok"` before the send (`quirk/notify/dispatcher.py:244`).
`send_slack` returns silently when `slack_sdk` is missing or the webhook env var is unset
(`quirk/notify/channels/slack.py:37-50`), so the row stays `ok` (fork probe: `[('slack', 'ok', None)]`
with no slack_sdk).

Both install hints name `quirk` instead of the distribution `quirk-scanner`:
`slack.py:40` ("pip install quirk[notify]") and `quirk/cli/ticket_cmd.py:97` ("pip install quirk[tickets]").

- [ ] Have send_slack signal a skip and record `skipped`/`failed`.
- [ ] Fix both hints to `quirk-scanner[...]`.

## Feasibility & Effort

- **Feasibility: CONFIRMED** (probe; lines above).
- **Effort: S.**
- **Unknowns:** whether `skipped` needs a schema/UI value in the audit views.
- **Spike:** no.
