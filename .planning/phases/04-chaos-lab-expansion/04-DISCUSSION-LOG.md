# Phase 4: Chaos Lab Expansion - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 04-chaos-lab-expansion
**Areas discussed:** JWT service design, Registry vulnerable images, Gitea source seeding, Storage + ssh-weak + ldaps

---

## JWT Service Design

| Option | Description | Selected |
|--------|-------------|----------|
| 4 separate microservices | One container per algorithm (RS256, HS256-weak, RSA1024, alg:none) — each with own port | ✓ |
| Single service, 4 endpoints | One Python/FastAPI container with /rs256, /hs256-weak, /rsa1024, /alg-none routes | |
| You decide | No strong preference on service topology | |

**User's choice:** 4 separate microservices

| Option | Description | Selected |
|--------|-------------|----------|
| JWKS endpoint + token issuer | /.well-known/jwks.json + /token endpoint that issues signed JWTs | ✓ |
| JWKS endpoint only | Only /.well-known/jwks.json | |
| Token issuer + static JWKS | Issues real JWTs, JWKS is a static file | |

**User's choice:** JWKS endpoint + token issuer

| Option | Description | Selected |
|--------|-------------|----------|
| Python + FastAPI | Consistent with QU.I.R.K. codebase | |
| Node.js + jsonwebtoken | Canonical JWT library in Node land | |
| You decide | Language doesn't matter much — pick easiest | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## Registry Vulnerable Images

| Option | Description | Selected |
|--------|-------------|----------|
| Custom Dockerfiles with old crypto libs | ubuntu:18.04 base, install old libssl / python-cryptography<3.0 | ✓ |
| Use existing old base images | centos:7, ubuntu:16.04 — ship old OpenSSL by default | |
| Images with crypto code patterns | Python/Go files using weak algorithms in application code | |

**User's choice:** Custom Dockerfiles with old crypto libs

| Option | Description | Selected |
|--------|-------------|----------|
| 3 images: old-libssl, old-python-crypto, mixed | Covers Syft's main detection surfaces | ✓ |
| 2 images: clean and vulnerable | Minimal, before/after comparison | |
| 4 images, one per scanner surface | Comprehensive: libssl, Python, Go, Java (Bouncy Castle) | |

**User's choice:** 3 images (old-libssl, old-python-crypto, mixed)

---

## Gitea Source Seeding

| Option | Description | Selected |
|--------|-------------|----------|
| Init script on container startup | Shell script creates org + repos via Gitea API, pushes files | ✓ |
| Pre-baked Docker volume | Custom Gitea image with repos already initialized | |
| External git init sidecar | Separate init-gitea container (restart: no) | |

**User's choice:** Init script on container startup

Anti-patterns to seed (all four selected):
- ✓ Hardcoded keys/secrets
- ✓ Weak algorithm usage (MD5/SHA1, DES/3DES/RC4, ECB mode)
- ✓ Weak random / custom crypto
- ✓ Deprecated protocol usage

---

## Storage + ssh-weak + ldaps

| Option | Description | Selected |
|--------|-------------|----------|
| New storage profile, extend LocalStack | New `storage` profile with KMS-only LocalStack + Vault + postgres | ✓ |
| Extend existing cloud profile | Add KMS, Vault, postgres to cloud profile | |
| Separate LocalStack for KMS only | New localstack-kms alongside existing localstack | |

**User's choice:** New storage profile, extend LocalStack

| Option | Description | Selected |
|--------|-------------|----------|
| Dev mode + pre-seeded secrets | vault server -dev + sidecar writes transit keys + KV secrets on startup | ✓ |
| Dev mode only, no seeding | Just vault server -dev | |
| Production init mode | Full vault operator init + unseal via init sidecar | |

**User's choice:** Dev mode + pre-seeded secrets

| Option | Description | Selected |
|--------|-------------|----------|
| Custom Dockerfile + sshd_config | Extends base image, injects sshd_config with weak KEX/hostkey/MAC | ✓ |
| Env-var-based config injection | linuxserver DOCKER_MODS mechanism | |
| Use an old OpenSSH Docker image | OpenSSH 5.x/6.x — most authentic but fragile | |

**User's choice:** Custom Dockerfile + sshd_config (weak KEX: diffie-hellman-group1-sha1, diffie-hellman-group14-sha1; weak hostkey: ssh-dss; weak MAC: hmac-md5, hmac-sha1)

| Option | Description | Selected |
|--------|-------------|----------|
| New ldaps profile, new OpenLDAP service | Independent osixia/openldap with LDAP_TLS=true, port 636 | ✓ |
| Extend identity profile | Add TLS config to existing openldap service | |
| nginx TLS wrapper over plain LDAP | Stream-mode TLS proxy on 636 — matches localstack-tls pattern | |

**User's choice:** New ldaps profile, new OpenLDAP service

---

## Claude's Discretion

- JWT microservice language/framework
- Port assignments for new services
- Gitea version and init method
- LocalStack KMS seed key specs
- Vault transit engine key types
- Postgres pgcrypto seed data
- ssh-weak Dockerfile base image
- LDAPS certificate selection

## Deferred Ideas

None — discussion stayed within phase scope.
