# Phase 30 — HashiCorp Vault Connector Expected Results

**Lab:** HashiCorp Vault dev server (Docker Compose profile `vault`)
**Phase:** 30 — HashiCorp Vault Connector
**Requirements:** VAULT-01, VAULT-02, VAULT-03

## Lab Setup

Boot the dedicated vault chaos profile:

```sh
cd quantum-chaos-enterprise-lab
docker compose --profile vault up -d
# vault-30 listens on http://localhost:28200
# Root token: root (dev mode only — never use in production)
```

The `vault-30-seed` init container creates these scenarios:

| Resource                              | Type            | Expected Finding             | Severity |
|---------------------------------------|-----------------|------------------------------|----------|
| transit/rsa-2048-classification       | RSA-2048 (D-01) | Classification only          | (none)   |
| transit/rsa-2048-exportable           | RSA-2048 +exportable (D-02) | Exportable transit  | MEDIUM   |
| PKI/pki                               | RSA-2048 root CA (D-03)     | RSA<4096 weak       | HIGH     |
| auth/token                            | dev-mode root token (D-05)  | Token auth always-fires | HIGH |
| auth/userpass                         | userpass (D-06)             | Userpass MEDIUM     | MEDIUM   |

## Scanner Configuration

Add to your `config.yaml` (or use `lab.yaml`):

```yaml
connectors:
  enable_vault: true
  vault_addr: "http://localhost:28200"
  vault_token: "root"
  vault_transit_mount: "transit"
  vault_tls_verify: true   # http URL — verification not exercised
```

## Expected Scan Output

5 `protocol="VAULT"` CryptoEndpoint rows are produced:

| host                                                  | service_detail                  | severity | cert_pubkey_alg | cert_pubkey_size |
|-------------------------------------------------------|----------------------------------|----------|-----------------|------------------|
| `http://localhost:28200/transit/keys/rsa-2048-classification` | `transit/rsa-2048-classification` | (none)   | `RSA`           | 2048             |
| `http://localhost:28200/transit/keys/rsa-2048-exportable`     | `transit/rsa-2048-exportable`     | MEDIUM   | `RSA`           | 2048             |
| `http://localhost:28200/pki/pki`                              | `PKI/pki`                         | HIGH     | `RSA`           | 2048             |
| `http://localhost:28200/auth/token`                           | `auth/token`                      | HIGH     | `token`         | (none)           |
| `http://localhost:28200/auth/userpass`                        | `auth/userpass`                   | MEDIUM   | `userpass`      | (none)           |

## Expected Evidence/Scoring Impact

Evidence summary additions:
- `dar_vault_weak_count`: 2  (PKI/pki HIGH + auth/token HIGH; D-11 — MEDIUM rows do NOT count)
- `dar_vault_weak_ratio`: 2 / total_endpoints

Scoring impact:
- `data_at_rest` subscore drops by `_ratio(2, total_endpoints) * 8.0` points (D-12 weight)

CBOM impact:
- `RSA-2048` registered as algorithm component via Pass 1 (D-14 — transit keys NOT skipped)
- No X.509 CertificateProperties components emitted for VAULT (Pass 2 skip — D-15)
- No TLS protocol component emitted for VAULT (Pass 3 skip — D-15)

## Tear-Down

```sh
docker compose --profile vault down -v
```
