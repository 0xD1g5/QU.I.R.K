# Phase 30: HashiCorp Vault Connector - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-26
**Phase:** 30-hashicorp-vault-connector
**Areas discussed:** Transit key severity, Chaos lab profile strategy, Vault TLS / connection config, Token auth always-fires, PKI intermediate CAs, Exportable transit keys

---

## Plans Exist Warning

Phase 30 already had 3 plans created without user context. User selected: **Continue and replan after**.

---

## Transit Key Severity

| Option | Description | Selected |
|--------|-------------|----------|
| Classification only — no severity | Transit keys appear in CBOM with alg+size only. RSA-2048 noted but not flagged. | ✓ |
| HIGH for RSA < 4096 | Match PKI behavior. RSA-2048 transit keys are quantum-vulnerable. | |
| MEDIUM for RSA < 4096 | Softer prompt to rotate. Doesn't affect dar_vault_weak_count without counter change. | |

**User's choice:** Classification only — no severity (Recommended)
**Notes:** Consistent with existing Plan 01 test contract (`test_dar_vault_weak_count_no_severity_no_increment` uses service_detail="transit/foo" with severity=None). Transit key rotation is straightforward; the quantum-safety signal comes from CBOM classification, not a severity flag.

---

## Chaos Lab Profile Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Separate `--profile vault` | New Docker Compose service, independent profile. | ✓ |
| Extend storage profile | Add Vault as sidecar to existing MinIO storage service. | |
| No chaos lab for Vault | Document manual `vault server -dev` steps instead. | |

**User's choice:** Separate `--profile vault` (Recommended)
**Notes:** This changes Plan 03's current artifact path from `quantum-chaos-enterprise-lab/storage/vault-seed.sh` to a new `quantum-chaos-enterprise-lab/vault/` directory. Matches pattern: one dedicated Docker profile per scanner phase.

---

## Vault TLS / Connection Config

| Option | Description | Selected |
|--------|-------------|----------|
| vault_tls_verify: bool = True config field | Add to ConnectorsCfg. Passed to hvac.Client(verify=...). | ✓ |
| Always verify TLS — no flag | Stricter, requires system trust store for self-signed certs. | |
| Always skip TLS verification | Insecure — MITM risk against Vault API. | |

**User's choice:** vault_tls_verify: bool = True config field (Recommended)
**Notes:** This adds a **5th** ConnectorsCfg field not in the existing Plan 01 interface spec. Plan 01 must be updated: add `vault_tls_verify: bool = True` after `vault_transit_mount`. Also update config_template.yaml and RED test assertions.

---

## Token Auth Always-Fires

| Option | Description | Selected |
|--------|-------------|----------|
| Always HIGH — unconditional | Token auth always fires regardless of other methods present. | ✓ |
| HIGH only if sole auth method | Suppress when AppRole/Kubernetes/OIDC also enabled. | |
| Downgrade to MEDIUM | Token auth is built-in, expected — treat as medium-priority note. | |

**User's choice:** Always HIGH — unconditional (Recommended)
**Notes:** Consistent with existing Plan 01 AUTH_RISK_MAP contract. Vault cannot disable token auth — it is always present. Remediation: avoid direct token auth usage.

---

## PKI Intermediate CAs

| Option | Description | Selected |
|--------|-------------|----------|
| Root CA only — one cert per PKI mount | Simpler. `read_ca_certificate` only. | |
| Root + intermediate CA | Call both `read_ca_certificate` and `read_ca_certificate_chain` per mount. | ✓ |
| Both, dedup by fingerprint | Complex — cert fingerprint comparison. | |

**User's choice:** Root + intermediate CA
**Notes:** Each cert (root + each intermediate) becomes a separate CryptoEndpoint. If `read_ca_certificate_chain` raises, error is swallowed silently — only root CA endpoint returned. Plan 02 must be updated to call both APIs.

---

## Exportable Transit Keys

| Option | Description | Selected |
|--------|-------------|----------|
| MEDIUM severity for exportable keys | `exportable=True` → MEDIUM. Signals key material can leave Vault. | ✓ |
| HIGH severity | Exportable keys are serious misuse of transit engine. | |
| No check — skip | Policy issue, not cryptographic weakness. Add in future phase. | |

**User's choice:** MEDIUM severity for exportable keys (Recommended)
**Notes:** MEDIUM does NOT increment `dar_vault_weak_count` (only HIGH does). The exportability check is additive — a key can be both classified for algorithm AND flagged for exportability. Plan 01's RED test contract needs `test_transit_key_exportable_medium_finding` added.

---

## Claude's Discretion

- Exact `service_detail` format for transit key endpoints (e.g., `"transit/my-key-name"`)
- Exact remediation text wording for auth method and exportable key findings
- Vault dev server Docker image version and init command
- Whether vault chaos lab seed is a shell script or Docker entrypoint sequence

## Deferred Ideas

- Vault Enterprise namespace support (`vault_namespace` config field) — open-source Vault only for v4.3
- Transit key version history enumeration (stale old key versions)
- PKI intermediate CA chain deduplication by cert fingerprint
- Vault audit log analysis for suspicious auth patterns
- Vault Enterprise / HCP Vault chaos lab scenarios
