# Azure Connector Setup

QU.I.R.K.'s Azure connector (`enable_azure`) discovers cryptographic material across Key Vault
keys and Application Gateway TLS policies. Storage Account / Blob encryption posture (`keySource`
— CMK vs. platform-managed) is switched on separately with `enable_blob`. Key Vault certificates
are not scanned.

> **Known limitation:** Key Vault key scanning currently emits no endpoints against a real
> vault. The connector reads `key_type` from each listed key, and the Azure SDK's `KeyProperties`
> objects that listing returns do not carry that attribute, so every key raises an error that is
> logged (verbose runs only) as `KeyVault key scan error for key in <vault_url>`. This is tracked
> as a product bug; App Gateway and Blob scanning are unaffected.

## RBAC Role Assignment

Assign the following built-in roles to the QU.I.R.K. service principal at the subscription
(or resource group) scope:

| Role | Scope | Purpose |
|------|-------|---------|
| `Reader` | Subscription | Enumerate resources including App Gateways and storage accounts |
| `Key Vault Reader` | Subscription or per-vault | Read Key Vault key metadata (QUIRK lists keys only, not certificates) |

> **Note:** `Key Vault Reader` grants the `Microsoft.KeyVault/vaults/*/read` data action, and
> Microsoft documents that it only works for key vaults that use the "Azure role-based access
> control" permission model (not legacy access policies). If you encounter permission errors
> listing keys, add `Key Vault Crypto Service Encryption User` to the specific vault; it grants
> the `Microsoft.KeyVault/vaults/keys/read` data action.

For App Gateway TLS policy scanning, the service principal needs
`Microsoft.Network/applicationGateways/read` — this is included in the `Reader` role.

## Prerequisites

- Azure subscription with access to the target resources
- Azure SDK installed: `azure-identity`, `azure-keyvault-keys`, `azure-keyvault-certificates`
  and `azure-mgmt-network` (used for App Gateway TLS policy scanning) are core dependencies of
  `quirk-scanner`, so a normal install already includes them.
- For Blob storage encryption scanning, `azure-mgmt-storage` is also required. It ships in the
  `cloud` extra, which `[all]` includes:

  ```bash
  pip install 'quirk-scanner[cloud]'
  ```

  If `azure-mgmt-storage` is not installed, the Blob scan finds no containers and logs
  `azure-mgmt-storage not installed — Azure Blob scanning unavailable` (verbose runs only). The
  phase is still recorded as having run, not as skipped.

## Service Principal Credentials

Create a service principal and set these environment variables before running a scan:

```bash
export AZURE_CLIENT_ID="00000000-0000-0000-0000-000000000000"
export AZURE_TENANT_ID="00000000-0000-0000-0000-000000000000"
export AZURE_CLIENT_SECRET="your-client-secret"
```

QU.I.R.K. uses `DefaultAzureCredential()` which resolves via the standard Azure credential chain:

1. **Environment variables** (above) — for service principals in CI/CD or scan hosts
2. **Managed identity** — for Azure VM or App Service execution
3. **Azure CLI** (`az login`) — for local development

## config.yaml Snippet

```yaml
connectors:
  enable_azure: true
  enable_blob: true   # optional — adds Storage Account / Blob encryption posture
  azure_subscription_id: "00000000-0000-0000-0000-000000000000"  # needed for App Gateway and Blob
  azure_keyvault_urls:
    - "https://myvault.vault.azure.net"
    - "https://anothervault.vault.azure.net"
```

`azure_subscription_id` is required for App Gateway and Blob scanning. `azure_keyvault_urls` is
a list of Key Vault base URLs to scan. Omit the list (or leave it empty) to skip Key Vault
scanning and scan only App Gateways. The Azure phase is skipped when both are empty.

## What Gets Scanned

| Service | Resource Type | Data Collected |
|---------|---------------|----------------|
| Key Vault | Keys | Key type (RSA, EC, oct/AES) and key size where the SDK exposes them (see the known limitation above) |
| Key Vault | Key metadata | Key ID, name, vault URL |
| App Gateway | TLS policies | Minimum TLS version, cipher suites, named policy |
| Storage Account / Blob (needs `enable_blob`) | Encryption posture | `encryption.keySource` per storage account; one CryptoEndpoint per container with parent account setting. `Microsoft.Keyvault` → BLOB/cmk (no finding), `Microsoft.Storage` → BLOB/platform-managed (MEDIUM), absent/null → BLOB/unknown (MEDIUM). Feeds the `data_at_rest` subscore. |

**Key types recognised:** `RSA`, `RSA-HSM` → RSA; `EC`, `EC-HSM` → ECDSA; `oct`, `oct-HSM` → AES.

## Graceful Degradation

The core Azure packages are always installed with `quirk-scanner`, so this only happens if they
were removed from the environment. If `azure-identity` or the Key Vault packages are missing, the
Azure phase is skipped before the connector is called, so nothing is printed, even in verbose
runs. The phase is recorded in the scan's phase-coverage records as skipped with reason
`missing-extra`. (The Blob phase, when `enable_blob` is on, does log
`azure SDK not installed — Azure Blob scanning skipped` in verbose runs.)

If only `azure-mgmt-network` is absent, the Key Vault scan still runs and App Gateway scanning
logs (verbose runs only):

```
azure-mgmt-network not installed — App Gateway scanning unavailable
```

All other scanners (TLS, SSH, AWS) continue to run normally.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `DefaultAzureCredential failed to retrieve a token` in the verbose log (after `KeyVault scan error for <vault_url>:` or `App Gateway scan error:`) | Credentials not found or invalid | Verify `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` are set and correct |
| `KeyVault scan error for <vault_url>` in the verbose log with a 403 (Forbidden) error | Missing `Key Vault Reader` role | Assign `Key Vault Reader` to the service principal on the vault or subscription |
| App Gateway results empty | `azure_subscription_id` missing, or the principal lacks the `Reader` role | Add `azure_subscription_id` to `config.yaml` and assign `Reader` |
| `KeyVault scan error for <vault_url>` in the verbose log | Vault URL typo, or the principal cannot reach that vault | Verify URLs in `azure_keyvault_urls` |
