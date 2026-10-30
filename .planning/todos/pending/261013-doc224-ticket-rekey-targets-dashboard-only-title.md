---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS (fork B4); ledger rows DCL-OPS-B-0403..B-0409 (docs/operators-guide.md §14.1 one-time ticket re-key)
priority: low
area: quirk/ticketing/base.py (compute_fingerprint docstring), quirk/compliance/__init__.py (FINGERPRINT_TITLE_ALIASES), tests/test_ticketing_fingerprint_stability.py
status: pending
resolves_phase: null
owner: "999.135"
---

# Phase 178's ticket re-key fixed a title the ticket path never sees, and re-keyed five it does

`quirk ticket create` fingerprints the dicts in the scan's `findings-*.json` (`quirk/cli/ticket_cmd.py:31`, `:118`,
`:188` -> `quirk/ticketing/base.py:157` `fp = self.compute_fingerprint(finding)`). Those come from
`quirk/engine/findings_evaluator.py`, whose certificate-expiry title is the constant
`"TLS certificate expiring within 30 days"` (`findings_evaluator.py:615`; same in v5.18.0). The day-counting title
`"Certificate expiring in {N} day(s)"` exists only in the dashboard's derived findings
(`quirk/dashboard/api/routes/scan.py:217`), which never reach ticketing.

So the `FINGERPRINT_TITLE_ALIASES["Certificate expiring in "]` entry (`quirk/compliance/__init__.py:211`) never
changes a ticket fingerprint, while the five container-image prefixes inherited from `TITLE_PREFIX_ALIASES`
(`End-of-life `, `Severely outdated Python cryptography package (`, `Outdated Python cryptography package (`,
`Outdated pyOpenSSL package (`, `Outdated libgcrypt (`) DID re-key against v5.18.0's raw-title formula.
Probe `.planning/phases/224-doc-claim-ledger-verification/work/probes/gc2-ops-b4-ticket-rekey-probe.py` compares
the v5.18.0 formula with the current one: the CLI cert-expiry titles are `same`, the five container titles `CHANGED`.

The `compute_fingerprint` docstring (`base.py:91-104`, "only the 'Certificate expiring in {N} day(s)' family") and
`test_cert_expiry_fingerprint_stable_across_day_boundary` (which feeds the dashboard title) describe and test the
wrong family. The operators-guide §14.1 now states what actually happened.

- [ ] Correct the `compute_fingerprint` docstring and the `FINGERPRINT_TITLE_ALIASES` comment.
- [ ] Decide whether the dashboard's cert-expiry alias belongs in the fingerprint table at all (it does feed
      `remediation_persist` / storyline fingerprints via `TicketingChannel.compute_fingerprint`, routes/storyline.py:109).
- [ ] Add a test pinning that the five container-image families normalize, using real `findings_evaluator` titles.

## Feasibility & Effort

- **CONFIRMED** by the probe above and by reading `quirk/engine/findings_evaluator.py:163,200,216,234,251,615`,
  `quirk/compliance/__init__.py:112-133,185-211` and `git show v5.18.0:quirk/ticketing/base.py` (raw-title formula).
- **LIKELY** effort **S** (comments + one test). **UNKNOWN**: whether the storyline/remediation path relies on the cert
  alias; check before removing it. No spike needed.
