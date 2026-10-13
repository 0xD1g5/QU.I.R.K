# HashiCorp Vault Connector Setup

QU.I.R.K.'s Vault connector (`enable_vault`) inspects a HashiCorp Vault server's cryptographic
posture: transit engine keys, PKI mount certificates, and the enabled auth methods.

## Minimum Vault Policy

Create a read-only policy for the token QU.I.R.K. will use. The paths match the API calls the
connector makes through `hvac`: list and read the secrets engine and auth method inventories, and
list and read transit keys. Replace `transit` with your `vault_transit_mount` if it differs.

```hcl
path "sys/mounts" {
  capabilities = ["read"]
}

path "sys/auth" {
  capabilities = ["read"]
}

path "transit/keys" {
  capabilities = ["list"]
}

path "transit/keys/*" {
  capabilities = ["read"]
}
```

Vault policies are deny by default, so no other path is reachable with this policy. The PKI
certificate reads the connector makes (`<mount>/ca/pem` and `<mount>/ca_chain`) are
unauthenticated Vault endpoints and need no policy path.

Create the policy and a token that carries it:

```bash
vault policy write quirk-readonly quirk-readonly.hcl
vault token create -policy=quirk-readonly
```

## Prerequisites

- A reachable Vault server and a token that carries the policy above
- The `hvac` package; it ships in the `cloud` extra, which `[all]` includes:

  ```bash
  pip install 'quirk-scanner[cloud]'
  ```

## Credential Setup

The connector needs an explicit token and a server address:

- Token: `vault_token` in `config.yaml`, or the `VAULT_TOKEN` environment variable. Prefer the
  environment variable so the token never lands in a file. With neither set the Vault phase is
  skipped as `missing-credentials`.
- Address: `vault_addr` in `config.yaml`, or the `VAULT_ADDR` environment variable. With neither
  set the Vault phase is skipped.

```bash
export VAULT_TOKEN="<token created above>"
export VAULT_ADDR="https://vault.example.com:8200"
```

## config.yaml Snippet

```yaml
connectors:
  enable_vault: true
  vault_addr: "https://vault.example.com:8200"   # required (or VAULT_ADDR)
  vault_transit_mount: "transit"                 # optional — defaults to "transit"
  vault_tls_verify: true                         # optional — defaults to true
```

`vault_tls_verify` is passed to `hvac` as its `verify` setting; set it to `false` only for a
development server without a trusted certificate. Per-request timeout is
`scan.timeouts.vault_seconds` (default `10`).

## What Gets Scanned

| Area | Resource Type | Data Collected |
|------|---------------|----------------|
| Transit | Keys under `vault_transit_mount` | Key type mapped to algorithm and size (`aes128-gcm96`, `aes256-gcm96`, `chacha20-poly1305`, `ed25519`, `ecdsa-p256/p384/p521`, `rsa-2048/3072/4096`, `hmac`, and the `ml-dsa-*` and `slh-dsa-*` post-quantum types); an exportable key is MEDIUM |
| PKI | Every mount of type `pki` | The root CA certificate and each certificate in the CA chain as separate records; an RSA key below 4096 bits or a SHA-1 signature is HIGH |
| Auth | Enabled auth methods | `token` and `ldap` are HIGH, `userpass` is MEDIUM; other methods (for example `approle`, `kubernetes`, `oidc`) produce no finding |

Token auth is always reported HIGH: Vault cannot disable it.

## Graceful Degradation

If `hvac` is not installed, the Vault phase is skipped before the connector is called and is
recorded as skipped (`missing-extra`). Verbose runs log `hvac not installed -- Vault scanning
skipped`, and every run prints a `[QRK-INSTALL-001]` line to stderr. If the token is rejected or Vault is sealed, the connector
returns a single endpoint whose scan error begins `vault-auth-failed:`. A failing sub-scanner
(transit, PKI or auth) does not suppress the others. All other scanners continue to run normally.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `vault-auth-failed: token rejected or Vault sealed` scan error | Bad token, expired token, or sealed Vault | Create a fresh token with the policy above; unseal Vault |
| Vault phase skipped as `missing-credentials` | Neither `vault_token` nor `VAULT_TOKEN` is set | Export `VAULT_TOKEN` |
| Vault phase skipped as `no-eligible-targets` | Neither `vault_addr` nor `VAULT_ADDR` is set | Set `vault_addr` |
| No transit results | `vault_transit_mount` does not match the mount path, or the token lacks `list` on `<mount>/keys` | Set `vault_transit_mount` and extend the policy |
| TLS verification errors | The Vault certificate is self-signed or not trusted | Install a trusted certificate on Vault; for a development server only, set `vault_tls_verify: false` |
