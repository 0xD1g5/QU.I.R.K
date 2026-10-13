---
type: todo
created: 2026-10-13
source: Phase 224 front-door verification (FD-OVW); ledger row DCL-OVERVIEW-0193 (docs/quirk-overview.md Data at Rest and Data in Motion)
priority: high
area: quirk/intelligence/evidence.py (motion_email_* counters), quirk/scanner/email_scanner.py, quirk/engine/profiles.py
status: pending
resolves_phase: null
---

# Closed mail ports lower the Data in Motion subscore on every default scan

The default `standard` profile (and `deep`) turns email scanning on unless the YAML sets `enable_email`
(`quirk/engine/profiles.py:137-143`, `:109-115`). The email phase probes all seven `EMAIL_PORTS`
(`quirk/scanner/email_scanner.py:81-89`) on every host that has a TLS candidate (`run_scan.py:3893`
`email_hosts = list(dict.fromkeys(h for h, _ in tls_targets))`). A refused connection still yields a row:
`tls_blocker_reason = "CONNECTION_REFUSED"` (`email_scanner.py:449`, `:462`), no `scan_error`, empty `tls_version`.

`build_evidence_summary` keys the motion counters on an empty `tls_version` alone:
`*-STARTTLS` rows tick `motion_email_starttls_missing_count` (`quirk/intelligence/evidence.py:479-484`) and
`SMTPS/IMAPS/POP3S` rows tick `motion_email_plaintext_count` (`:497-502`). So a host with no mail server at all is
scored as if it served mail in plaintext.

Reproduced (`work/probes/fd-ovw-e2e-scans.txt`, run1, isolated HOME): one Python TLS server on 127.0.0.1:18443, every
mail port closed (`nc -z` on 25/110/143/465/587/993/995 all fail). Log: `Starting email TLS scans: 7 tasks (1 hosts x 7
ports)`, `Email scans complete: 0/7 successful`. Evidence: `motion_email_starttls_missing_count 4`,
`motion_email_plaintext_count 3`; Data in Motion assessed at 14/25 with the driver "Email plaintext or missing
STARTTLS". Without these rows Data in Motion would be unassessed and excluded from the rescale.

Related but distinct: `261013-doc224-smtp-without-starttls-is-a-scan-error-not-an-assessment.md` (a server that is
reached but offers no STARTTLS) and `email-scanner-host-derivation-is-invisible-to-operators.md` (which hosts are
probed).

- [ ] Exclude rows whose `tls_blocker_reason` is `CONNECTION_REFUSED` (and probably `TIMEOUT` with no banner) from
      the motion counters and from the protocol counts that `_motion_assessed` reads (`quirk/intelligence/scoring.py:363`); count them as "port closed", not as a posture.
- [ ] Add a scoring test that feeds the scanner's real CONNECTION_REFUSED row shape and asserts Data in Motion stays
      unassessed.
- [ ] Then drop the known-issue sentence from docs/quirk-overview.md and re-check docs/report-interpretation.md's
      Data in Motion section.

## Feasibility & Effort

- **CONFIRMED** by the e2e run above and by reading `quirk/intelligence/evidence.py:479-502`,
  `quirk/scanner/email_scanner.py:446-462` and `quirk/engine/profiles.py:137-143`.
- Effort **S**: a guard in two counter branches plus the `_motion_assessed` input, one test, and golden-fixture
  regeneration if any fixture carries closed-port email rows. Unknown: whether any report text counts these rows
  separately (grep `STARTTLS` in `quirk/reports/`). No spike needed.
