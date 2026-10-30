---
type: todo
created: 2026-10-15
source: Phase 228 (Cross-Surface Score Parity) XSURF-08, RESEARCH Open Question 6
priority: medium
area: run_scan.py (broker_email stage resume branch)
status: pending
resolves_phase: null
owner: "999.136"
---

# The resume path's email filter keeps one of six email protocol labels

When the `broker_email` stage was completed in a prior run, `run_scan.py` rebuilds `email_endpoints` from the resumed
rows with `protocol in ("SMTP", "SMTPS", "EMAIL")` (`run_scan.py:3873`). The email scanner emits six labels:
`SMTP-STARTTLS`, `SMTPS`, `IMAP-STARTTLS`, `IMAPS`, `POP3-STARTTLS`, `POP3S` (`quirk/scanner/email_scanner.py:82-90`
and the label table around it). Only `SMTPS` matches the filter, so the other five labels drop out of `email_endpoints`
on a resumed scan. `"SMTP"` and `"EMAIL"` are not labels the scanner emits.

Read the neighbouring lines first: `_broker_email_protocols` (`run_scan.py:3870-3871`) has the same stale vocabulary, and
the kafka and redis filters at `:3874,3876` compare against `"KAFKA"` and `"REDIS"`, and the rabbit filter keeps
`"AMQP"` but not `AMQP-PLAIN`; the
broker scanner no longer emits the bare names (it writes `KAFKA-TLS` / `KAFKA-PLAIN` at `broker_scanner.py:236,501`, `AMQP-PLAIN` at
`:624`). Verify before fixing which downstream
consumers use these lists, since XSURF-08's unanswered-row exclusion runs on the persisted endpoints either way.

- [ ] Replace the literal tuple with the scanner's label set (import it; do not hand-copy).
- [ ] Check the broker filters at `:3874-3876` for the same drift and fix them in the same change.
- [ ] Add a resume test: a persisted SMTP-STARTTLS/IMAPS/POP3S row survives the resume branch into `email_endpoints`.

## Feasibility & Effort

- **CONFIRMED** for the email filter by reading `run_scan.py:3873` and `email_scanner.py:82-90` at HEAD (filter not
  executed end to end).
- **UNKNOWN** how many downstream consumers read `email_endpoints` after a resume. Effort **S** for the filter, **M** if
  the broker filters need the same repair. Spike: a short one resuming a fixture DB.
