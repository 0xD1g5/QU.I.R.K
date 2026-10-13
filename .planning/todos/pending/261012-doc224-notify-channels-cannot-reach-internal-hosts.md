---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-B-* (configuration.md Notifications, Security controls)
priority: low
area: quirk/notify/channels/email.py, webhook.py, slack.py (validate_external_url without allow_internal), quirk/notify/config.py
status: pending
resolves_phase: null
---

# Notification channels have no `allow_internal` opt-in, so an internal SMTP relay or webhook is refused

Jira and ServiceNow (`ticketing.*.allow_internal`) and SIEM (loopback/RFC1918 allowed by design) have a way to reach
internal hosts. The notification channels do not: `email.send_email`, `webhook.send_webhook` and `slack.send_slack` call
`validate_external_url(url)` with the default `allow_internal=False`, and `EmailNotifyCfg` / `WebhookNotifyCfg` have no
field to change that. Checked live:

```
validate_external_url('https://10.0.0.5:587').ok        -> False (internal_ip)
validate_external_url('https://127.0.0.1:587').ok       -> False (loopback)
validate_external_url('https://example.com/x').ok       -> True
```

The most common enterprise setup, an on-prem SMTP relay (`smtp.corp.com` resolving to 10.x) or an internal webhook receiver,
therefore fails every delivery with `ValueError: SSRF blocked (internal_ip) ...` recorded as a `failed` audit row.
`docs/configuration.md` now states that no override exists.

- [ ] Add an `allow_internal: false` key to the `email:` and `webhook:` notification blocks (and pass it through), keeping
      cloud-metadata addresses blocked, as the ticketing blocks do.
- [ ] Tests mirroring `tests/test_notify_ssrf.py` for the opt-in; document the key in the Notifications section.

## Feasibility & Effort

**CONFIRMED** by the three calls above and by reading the three channel modules. Effort **S** (two config fields, three call
sites, tests). Unknown: whether the omission is a deliberate hardening choice for hosted consoles; if so, gate the new key behind
the same operator-only config the other `allow_internal` flags use.
