---
type: todo
created: 2026-10-16
source: Phase 229 verification, fifth pass (229-VERIFICATION, evidence-field dimension)
priority: medium
area: quirk/scanner/dnssec_scanner.py; quirk/scanner/email_scanner.py; run_scan.py (broker evidence attach)
status: pending
resolves_phase: null
owner: "999.138"
---

# Closure evidence shape residue: a DNSSEC timeout reads as an unsigned zone, email/broker evidence sits on one row, and database findings never close

**Owner:** 999.138 (closure evidence)

Two PRE-EXISTING, non-blocking items the Phase 229 verifier found while probing the evidence-field
dimension. Neither closes an unfixed finding today.

## (a) DNSSEC swallows a DNSKEY timeout

`_query_rrset` swallows every exception and returns None, so a DNSKEY query timeout becomes a
`DNSSEC` row with the `unsigned-zone` result, carrying `dnssec_scan_json` and no `scan_error`
(`dnssec_scanner.py:151-164, 300-320`). It misleads any surface that reads the row. It is not a
closure path today: the report deriver emits no DNSSEC findings, so no DNSSEC fingerprint rows
exist. It becomes a false-closure trap the day DNSSEC findings are added to the deriver.

## (b) Email and broker evidence lives on one row

`email_scan_json` is attached per host to the lowest-port row, and `broker_scan_json` to the first
broker row of the whole scan (`run_scan.py:4041`). A finding on any other email port, or on any
other broker host:port, can therefore never have a live row carrying its family's evidence and can
never close. This is an under-claim only (Phase 32/33 layout). The email half was narrowed, not
fixed, by 229-12 (a blocked mail port now refuses closure).

## (c) Database findings can never close (added 2026-10-16, Phase 229 final verification)

The `database` family's evidence field is `tls_version`, but `quirk/scanner/db_connector.py` never sets
it on POSTGRESQL/MYSQL rows, so whenever DB rows exist the family reads `unhealthy` and no database
finding can ever close. Pre-existing (predates Phase 229), an under-claim only; `docs/operators-guide.md`
§16 makes no database-closure claim. Fix shape: point the family at the field the DB connector actually
writes, or have the connector write `tls_version`, with a closure test on real connector rows.

## Feasibility & Effort

- (a) CONFIRMED, effort S: the swallow site is at the cited lines. Fix is to return a sentinel from
  `_query_rrset` on exception and set `scan_error`/a failure row; needs a DNSSEC scanner test.
  No spike needed.
- (b) LIKELY, effort M: evidence would have to be written per row (or `endpoint_has_family_evidence`
  taught to read the host-level summary for that port). Unknown: how many report/CBOM consumers
  read the per-host attach point. Spike: grep consumers of `email_scan_json`/`broker_scan_json`
  before choosing.
