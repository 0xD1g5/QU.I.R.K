---
type: todo
created: 2026-10-15
source: Phase 228 (Cross-Surface Score Parity) XSURF-08, RESEARCH Open Question 6
priority: low
area: quirk/cbom/builder.py (build_cbom protocol pass), quirk/intelligence/evidence.py (_is_unanswered_email_probe)
status: pending
resolves_phase: null
owner: "999.132"
---

# CBOM emits a `protocol:tls:` component for every refused or timed-out email probe row

Phase 228 XSURF-08 stopped scoring an email probe row that never answered: `_is_unanswered_email_probe`
(`quirk/intelligence/evidence.py:50-62`) treats a `CONNECTION_REFUSED` or `TIMEOUT` blocker with no negotiated
`tls_version` like a CLOSED port. The CBOM did not follow. `build_cbom`'s protocol pass has explicit branches for SSH,
JWT, CONTAINER, SOURCE and so on, a skip list at `quirk/cbom/builder.py:1024-1033`, and falls through to the TLS default
for everything else (`:1040-1066`). The email labels (SMTP-STARTTLS, SMTPS, IMAP-STARTTLS, IMAPS, POP3-STARTTLS, POP3S)
are in neither, so each refused row becomes `protocol:tls:{host}:{port}` with no cipher suite and no version.

Re-measured in-process at HEAD: one refused SMTP-STARTTLS row (port 25) and one timed-out SMTPS row (port 465) give
`build_cbom` components `['protocol:tls:h1:25', 'protocol:tls:h1:465']` (2 rows, 2 components). A CBOM consumer reads
those as TLS services that exist, which is the opposite of what the scanner observed.

- [ ] Skip unanswered email probe rows in the protocol pass (reuse `_is_unanswered_email_probe`, do not copy it).
- [ ] Regenerate the CBOM golden fixtures (`REGEN_CBOM_FIXTURES=1 ... -m slow`) if any contain refused email rows.
- [ ] Add a test: a refused email row yields no `protocol:tls:` component; an answered one still does.

## Feasibility & Effort

- **CONFIRMED** by the in-process probe above and by reading `builder.py:1024-1066` and `evidence.py:50-62` at HEAD.
- Effort **S**. Unknown: whether a downstream report section counts CBOM protocol components (check
  `quirk/reports` for `protocol:tls` readers before changing). No spike needed.
