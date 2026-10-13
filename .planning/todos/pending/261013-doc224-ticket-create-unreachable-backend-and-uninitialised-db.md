---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS fork G; ledger row DCL-OPS-C-0033 (docs/operators-guide.md §21 Command Reference)
priority: low
area: quirk/cli/ticket_cmd.py (channel construction, audit DB path)
status: pending
resolves_phase: null
---

# `quirk ticket create` crashes on an unreachable backend and on a database without the audit table

Probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc3-ops-G-ticket-delivery-failure-exit.sh`):

1. Jira URL pointing at a closed `127.0.0.1` port -> exit 1 with an uncaught `requests.exceptions.ConnectionError`
   traceback at `/rest/api/2/serverInfo`. Channel construction catches only `(ValueError, ImportError)`
   (`quirk/cli/ticket_cmd.py:158`, `:175`); the `JIRA(...)` constructor contacts the server (`quirk/ticketing/jira.py:78`).
2. A stub Jira that rejects every request, with `QUIRK_DB_PATH` pointing at a file that does not exist yet -> exit 2,
   "audit-row persistence failed, no audit records were saved: PendingRollbackError". `ticket_cmd.py` never calls
   `init_db`, and its default DB is `quirk.db` in the working directory (`quirk/cli/ticket_cmd.py:144`), not the
   canonical `./quirk-output/quirk.db`.

With an initialised DB the same stub gives exit 0 and two `failed` rows in `integration_deliveries`, which is the
intended per-finding behaviour.

- [ ] Catch connection errors at channel construction and print an `ERROR:` line with a non-zero exit, no traceback.
- [ ] Call `init_db(db_path)` before dispatch, and consider the canonical DB path as the default.

## Feasibility & Effort

- **CONFIRMED** by the probe and by reading `quirk/cli/ticket_cmd.py:144-180` and `quirk/ticketing/jira.py:78-82`.
- **LIKELY** effort **S**: widen two except clauses (or wrap construction in `except Exception` with `safe_str`) and add
  one `init_db` call; tests can monkeypatch `JIRA` to raise. No spike needed.
