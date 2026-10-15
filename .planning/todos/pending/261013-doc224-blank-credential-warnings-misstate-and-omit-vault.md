---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS; ledger rows DCL-OPS-B-0002, DCL-OPS-GC3-0001 (docs/operators-guide.md, connector credential paragraph)
priority: low
area: src/dashboard/src/components/ConnectorsPanel.tsx (amber note text), quirk/dashboard/api/routes/jobs.py (_connectors_with_blank_credential_warnings)
status: pending
resolves_phase: null
owner: "999.137"
---

# Blank-credential warnings promise a skip that only Vault performs, and the server warning omits Vault

Two pre-launch warnings exist for a connector enabled with blank credentials, and they disagree with the scan:

1. The panel note (`ConnectorsPanel.tsx:650-652`) says the scan "will run and record a missing-credentials skip for
   this connector if it can't authenticate". The panel shows it for every connector with credential fields
   (`ConnectorsPanel.tsx:76-92`: vault, adcs, db, snmp, broker). In a real scan only the Vault phase records
   `missing-credentials` (`run_scan.py:3813-3820`, the only emitter). ADCS, DB, SNMP and broker run and report their
   own errors. Live probe `.planning/phases/224-doc-claim-ledger-verification/work/probes/gc3-ops-vault-precheck-probe.sh`:
   ADCS with no password -> `adcs_scanning` status `ran` plus a bind-failure warning, while Vault with no token ->
   `skipped / missing-credentials`.
2. The server's submit-time warnings (`jobs.py:553-557`) cover only `enable_adcs`, `enable_db` and `enable_snmp`. Vault,
   the one connector that actually skips without a credential, gets no server warning (in-process probe: four flags
   enabled, three warnings, none for `enable_vault`).

The operators-guide now describes this behaviour as it is. The product text should match it.

- [ ] Reword the panel note so it does not promise a `missing-credentials` skip for non-Vault connectors.
- [ ] Decide whether `_FLAG_TO_CREDENTIAL_FIELDS` should include `enable_vault: ("vault_token",)`.
- [ ] Add a test that asserts the warning set against the connectors that really skip.

## Feasibility & Effort

- **CONFIRMED** the note text at `src/dashboard/src/components/ConnectorsPanel.tsx:650-652` and its gate at `:562-564`
  (any connector whose `CONNECTOR_CREDENTIAL_FIELDS` entries are all blank).
- **CONFIRMED** the server map at `quirk/dashboard/api/routes/jobs.py:553-557` has no `enable_vault`, and `vault_token`
  is a registry credential (`quirk/config_redaction.py:55`), so adding it is a one-line map change.
- **CONFIRMED** sole emitter: `run_scan.py:3818` is the only `"missing-credentials"` string outside the allowed set at
  `quirk/models.py:285`.
- **LIKELY** effort **S**: one copy change, one map entry, a test in `tests/test_jobs_popen_env_injection.py` (which
  already exercises `credential_warnings`) plus a dashboard rebuild. No spike needed.
