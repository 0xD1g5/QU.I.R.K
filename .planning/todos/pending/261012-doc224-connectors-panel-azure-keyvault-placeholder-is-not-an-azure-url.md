---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger row DCL-CONNFIELDS (Azure Key Vault URLs)
priority: low
area: src/dashboard/src/components/ConnectorsPanel.tsx
status: pending
resolves_phase: null
owner: "999.126"
---

# The Connectors panel's "Azure Key Vault URLs" placeholder is not an Azure Key Vault URL

`src/dashboard/src/components/ConnectorsPanel.tsx` (the `azure_keyvault_urls` entry in `CONNECTOR_DETAIL_FIELDS`)
sets `placeholder: "https://vault.example.com/v1/kv"`. That is the shape of a HashiCorp Vault KV path, not an Azure
Key Vault base URL. `quirk/scanner/azure_connector.py` documents the expected form as
`https://myvault.vault.azure.net`, and `docs/connector-field-reference.md` now uses that form. An operator who copies
the placeholder shape gets a vault URL that `KeyClient` cannot resolve; the error is swallowed and logged only in
verbose runs (`KeyVault scan error for <vault_url>`).

- [ ] Change the placeholder to `https://myvault.vault.azure.net`.
- [ ] Rebuild the dashboard (`cd src/dashboard && npm run build`, statics are committed) and update any vitest that
      pins the old placeholder (`grep -rn "vault.example.com" src/dashboard/src`).

## Feasibility & Effort

**CONFIRMED** (placeholder read at the cited entry on 2026-10-12). Effort **S**: a one-string change plus a committed
statics rebuild. **No spike needed.**
