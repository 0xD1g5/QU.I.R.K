---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-REPORTINT-0198 and DCL-REPORTINT-0201 (docs/report-interpretation.md section 22)
priority: low
area: run_scan.py (scan phase recorder), quirk/models.py SCAN_PHASE_SKIP_REASONS
status: pending
resolves_phase: null
---

# `missing-credentials` is only ever recorded for the Vault token

`quirk/models.py` lists five scan-phase skip reasons, one of them `missing-credentials`, and the Scan Coverage
section and operators guide describe it as "enabled with targets, but the credential it needs is not set". In
`run_scan.py` exactly one call site records it: the Vault token gate (`run_scan.py:3813-3818`). The database
connectors deliberately have no such gate (`run_scan.py:3409`, "Phase 192 review CR-01: NO missing-credentials
pre-gate here"), and no other connector has one. A dashboard scan with, say, the broker or email scanner enabled and a
blank credential therefore does not show `missing-credentials` in Scan Coverage; it shows a `ran` phase (with error
rows) or `failed`. The documentation now says "today only the Vault token is checked this way".

- [ ] Decide whether other credentialed connectors (broker credentials, email, cloud connectors that do not accept ambient
      credentials) should get a pre-launch gate that records `missing-credentials`, or whether the reason is intentionally
      Vault-only and the surrounding copy (Effective config panel, operators guide section 3.1.2 and 3.1.4) should say so.
- [ ] If gates are added, mirror `credential_is_set()` (`quirk/config_redaction.py:121`) as the Vault gate does, so the
      Effective config panel and the scan agree.

## Feasibility & Effort

**LIKELY** (single emission site confirmed by grep; which connectors lack an ambient-credential fallback was not
audited). Effort **M** if gates are added per connector, **S** if only the copy changes. Unknowns: per-connector
credential fallbacks (`broker_credentials` pass_env handling at `run_scan.py:435-458` looks relevant).
**Spike**: audit each `_wrapped_phase` connector for "works without a configured credential", about an hour.
