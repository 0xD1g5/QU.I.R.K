---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONN-AZURE-*
priority: high
area: quirk/scanner/azure_connector.py
status: pending
resolves_phase: null
owner: "999.126"
---

# Azure Key Vault key scanning emits zero endpoints against the real SDK

`_scan_keyvault_keys` (`quirk/scanner/azure_connector.py`) iterates `KeyClient.list_properties_of_keys()` and reads
`key.key_type`, `key.n`, `key.crv` and `key.key_size` from each item. The SDK yields `KeyProperties` objects, which
carry only `id`, `name`, `version`, `vault_url`, `enabled`, `created_on`, `updated_on`, `expires_on`, `not_before`,
`recoverable_days`, `recovery_level`, `tags`, `managed`, `exportable`, `release_policy`, `hsm_platform`,
`attestation`. There is no `key_type`, so every key raises `AttributeError`, which the per-key `except Exception`
logs (verbose runs only) and swallows. Reproduced 2026-10-12 by feeding a real
`azure.keyvault.keys._models.KeyProperties(key_id="https://v.vault.azure.net/keys/k/abc123")` through
`_scan_keyvault_keys` with a mocked `KeyClient`: `KeyVault key scan error for key in https://v.vault.azure.net:
'KeyProperties' object has no attribute 'key_type'`, 0 endpoints.

`tests/test_azure_keyvault.py` builds `MagicMock` keys with a `key_type` attribute, so it cannot see this.
`docs/connectors/azure.md` carries a Known-limitation note until it is fixed. Separately, `CertificateClient` is
imported but never used, so Key Vault certificates are not scanned although the old doc claimed they were.

- [ ] Fetch each key with `KeyClient.get_key(name)` (which returns a `KeyVaultKey` with `key_type`, `key.n`, `key.crv`)
      or drop key-type/size detail and record only what `KeyProperties` provides.
- [ ] Rewrite `tests/test_azure_keyvault.py` fixtures to use real `KeyProperties` / `KeyVaultKey` objects.
- [ ] Decide whether certificate scanning is wanted (`CertificateClient.list_properties_of_certificates`).
- [ ] Then remove the Known-limitation note from `docs/connectors/azure.md` and re-verify its rows.

## Feasibility & Effort

**CONFIRMED** (reproduction above; attribute list from `dir(KeyProperties)` in the project venv). Effort **M**: one
extra SDK call per key, new fixtures, and a decision on certificates. Unknown: a vault with thousands of keys makes
`get_key` per key slow; consider batching. **No spike needed** beyond a live vault check, which needs credentials.

## Phase 235 note (2026-10-30)

v5.28.0 ships the **disclosure**, not the fix: the README (`README.md:107`, `:156`) and the CHANGELOG state that Key Vault key scanning
has a known defect and currently records no keys (D-02). The defect and the fix list above stay open with owner **999.126**.
