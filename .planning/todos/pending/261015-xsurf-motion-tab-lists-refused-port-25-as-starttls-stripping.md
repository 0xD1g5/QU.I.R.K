---
type: todo
created: 2026-10-15
source: Phase 228 (Cross-Surface Score Parity) XSURF-08, RESEARCH Open Question 6
priority: low
area: quirk/dashboard/api/routes/scan.py (_derive_motion_findings)
status: pending
resolves_phase: null
owner: "999.137"
---

# The Data in Motion tab still lists a refused port 25 as "SMTP STARTTLS susceptible to stripping"

`_derive_motion_findings` (`quirk/dashboard/api/routes/scan.py:588`) builds a MEDIUM `SMTP STARTTLS susceptible to
stripping (port 25)` row for any `SMTP-STARTTLS` endpoint on port 25 (`:615`, `:624-626`). It never looks at
`tls_blocker_reason`, so it cannot tell a server that offers opportunistic STARTTLS from a port that refused the
connection. XSURF-08 removed unanswered email probe rows from the score (`_is_unanswered_email_probe`,
`quirk/intelligence/evidence.py:50-62`), so the Motion tab now claims a downgrade risk the score ignores.

Re-measured in-process at HEAD: a `SMTP-STARTTLS` port-25 row with `tls_blocker_reason="CONNECTION_REFUSED"` yields
`('MEDIUM', 'SMTP STARTTLS susceptible to stripping (port 25)')`, and a timed-out `SMTPS` row on 465 yields
`('LOW', 'SMTPS TLS endpoint')`. Neither describes a listening service.

- [ ] Skip unanswered probe rows in `_derive_motion_findings` (reuse `_is_unanswered_email_probe`).
- [ ] Add a test for refused and timed-out rows, plus an answered port-25 STARTTLS row that must still be listed.
- [ ] Check the Motion-tab counts in `docs/operators-guide.md` and the UAT cases that quote stm/pt totals.

## Feasibility & Effort

- **CONFIRMED** by the in-process probe above and by reading `scan.py:588-660` at HEAD.
- Effort **S**. Unknown: the Motion-tab counters (stm/pt) the UI shows may shift; RESEARCH measured stm=8, pt=6 for two
  hosts across seven email ports before the change. No spike needed.
