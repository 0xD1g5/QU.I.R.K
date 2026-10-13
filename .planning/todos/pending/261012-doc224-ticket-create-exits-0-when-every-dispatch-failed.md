---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-B-* (configuration.md Jira / ServiceNow CLI usage; SIEM export)
priority: medium
area: quirk/cli/ticket_cmd.py, quirk/ticketing/base.py (dispatch_finding), quirk/cli/export_cmd.py
status: pending
resolves_phase: null
---

# `quirk ticket create` exits 0 when every ticket failed; `quirk export --siem` exits 2 after delivering events

Two exit-code mismatches found while verifying the Jira, ServiceNow and SIEM sections of `docs/configuration.md`:

1. `TicketingChannel.dispatch_finding()` catches every delivery exception, writes an `integration_deliveries` row with
   `status="failed"` and returns normally. `ticket_cmd.py` then prints `Ticket run complete: N finding(s) processed.`
   and falls off the end of `main`, so the process exits **0** even if all N tickets failed (wrong credentials, Jira down,
   SSRF block at send time). A cron job or CI step gating on the exit code reads that as success. The doc previously
   promised `0 = all findings dispatched`; it now says per-finding failures do not change the exit code.
2. `quirk export --siem` sends the CEF events first and writes the audit row afterwards. If `QUIRK_DB_PATH` is unset
   the command opens `./quirk.db`; when that file is not an initialised QUIRK database the audit insert fails
   (`no such table: integration_deliveries`), the exception is reported as `SIEM export failed` and the command exits **2**
   although the events arrived at the collector (observed against a local UDP stub listener). Retrying duplicates the events.

- [ ] Ticketing: count failed rows and exit 3 (some failed) / 2 (all failed), mirroring `export --siem`'s 0/2/3 scheme.
- [ ] SIEM export: initialise the DB (or skip the audit write with a clear warning) instead of failing after the send.
- [ ] Update the Exit codes paragraphs in `docs/configuration.md` and regenerate `docs/quirk-master-guide.md`.

## Feasibility & Effort

**CONFIRMED**: item 1 by reading `ticket_cmd.py` plus `tests/test_ticket_cmd.py` (no test asserts a non-zero exit for a failed
dispatch); item 2 by running `export --siem` against a fresh empty `QUIRK_DB_PATH` with a loopback UDP listener. Effort **S** each.
Unknown: whether scripts already rely on the exit-0 behaviour (search `docs/` and `deploy` files for `ticket create` before
changing it).
