# Azure Connector Setup

QU.I.R.K.'s Azure connector discovers cryptographic material across Key Vault keys and
certificates, and Application Gateway TLS policies.

## RBAC Role Assignment

Assign the following built-in roles to the QU.I.R.K. service principal at the subscription
(or resource group) scope:

| Role | Scope | Purpose |
|------|-------|---------|
| `Reader` | Subscription | Enumerate resources including App Gateways |
| `Key Vault Reader` | Subscription or per-vault | Read Key Vault key and certificate metadata |

> **Note:** `Key Vault Reader` is sufficient for most configurations. If you encounter
> permission errors reading key properties, add `Key Vault Crypto Service Encryption User`
> to the specific vault.

For App Gateway TLS policy scanning, the service principal needs
`Microsoft.Network/applicationGateways/read` — this is included in the `Reader` role.

## Prerequisites

- Azure subscription with access to the target resources
- Azure SDK installed:

  ```bash
  pip install azure-identity azure-keyvault-keys azure-keyvault-certificates
  ```

- For App Gateway TLS policy scanning (optional):

  ```bash
  pip install azure-mgmt-network
  ```

  If `azure-mgmt-network` is not installed, App Gateway scanning is skipped silently.

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
  azure_subscription_id: "00000000-0000-0000-0000-000000000000"  # required
  azure_keyvault_urls:
    - "https://myvault.vault.azure.net"
    - "https://anothervault.vault.azure.net"
```

`azure_subscription_id` is required for App Gateway scanning. `azure_keyvault_urls` is a list
of Key Vault base URLs to scan. Omit the list (or leave it empty) to skip Key Vault scanning
and scan only App Gateways.

## What Gets Scanned

| Service | Resource Type | Data Collected |
|---------|---------------|----------------|
| Key Vault | Keys | Key type (RSA, EC, oct/AES), key size, enabled/disabled state |
| Key Vault | Key metadata | Name, version, vault URL |
| App Gateway | TLS policies | Minimum TLS version, cipher suites, named policy |

**Key types recognised:** `RSA`, `RSA-HSM` → RSA; `EC`, `EC-HSM` → ECDSA; `oct`, `oct-HSM` → AES.

## Graceful Degradation

If the Azure SDK is not installed, the connector returns an empty result set and logs:

```
azure SDK not installed — Azure scanning unavailable
```

App Gateway scanning logs separately if `azure-mgmt-network` is absent:

```
azure-mgmt-network not installed — App Gateway scanning unavailable
```

All other scanners (TLS, SSH, AWS) continue to run normally.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `ClientAuthenticationError` | Credentials not found or invalid | Verify `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` are set and correct |
| `ForbiddenError` on Key Vault | Missing `Key Vault Reader` role | Assign `Key Vault Reader` to the service principal on the vault or subscription |
| App Gateway results empty | `azure-mgmt-network` not installed, or `azure_subscription_id` missing | Install `azure-mgmt-network` and add `azure_subscription_id` to `config.yaml` |
| `ResourceNotFoundError` for vault | Vault URL typo or vault in different subscription | Verify URLs in `azure_keyvault_urls` |
