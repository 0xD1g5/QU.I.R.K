# Phase 4: Chaos Lab Expansion - Research

**Researched:** 2026-03-30
**Domain:** Docker Compose multi-profile lab services — JWT microservices, Docker Registry v2, Gitea, LocalStack KMS, HashiCorp Vault, OpenSSH weak config, OpenLDAP over TLS
**Confidence:** HIGH (all decisions are locked in CONTEXT.md; research validates implementation details and documents pitfalls)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 4 separate JWT containers — RS256, HS256-weak, RSA1024, alg:none. One per algorithm type, own port, own behavior.
- **D-02:** Each JWT service exposes `/.well-known/jwks.json` and `/token`. Scanner hits JWKS discovery path.
- **D-03:** Language/framework is Claude's discretion (Python/FastAPI preferred).
- **D-04:** Registry images use custom Dockerfiles with deliberately old crypto library versions — not old base images pulled from Hub.
- **D-05:** 3 images: `image-old-libssl` (ubuntu:18.04, OpenSSL 1.0.x), `image-old-pycrypto` (python-cryptography<3.0 + pyOpenSSL<22), `image-mixed` (old libssl + old pycrypto + Go binary with embedded crypto).
- **D-06:** Images pushed to Docker Registry v2 on startup via seed script or init container.
- **D-07:** Gitea repos seeded via init script using Gitea API on startup. No pre-baked volume.
- **D-08:** 4 categories of crypto anti-patterns: hardcoded keys/secrets, weak algorithm usage, weak random/custom crypto, deprecated protocol usage.
- **D-09:** `storage` profile is independent of existing `cloud` profile. `cloud` profile unchanged.
- **D-10:** Storage profile: LocalStack with `SERVICES=kms` only, HashiCorp Vault, postgres with pgcrypto.
- **D-11:** Vault in dev mode (`vault server -dev`) + sidecar writes transit engine keys and KV secrets on startup.
- **D-12:** Custom Dockerfile for ssh-weak extending ubuntu:20.04 or lscr.io/linuxserver/openssh-server with full sshd_config replacement enabling: weak KEX (diffie-hellman-group1-sha1, diffie-hellman-group14-sha1), weak hostkey (ssh-dss), weak MAC (hmac-md5, hmac-sha1).
- **D-13:** ssh-weak uses `ssh-weak` profile — separate from base `ssh-alt`.
- **D-14:** New `ldaps` profile uses `osixia/openldap` — independent of existing `openldap` in `identity` profile. LDAP_TLS=true, certs from `./certs`, LDAPS on port 636.
- **D-15:** Existing `identity` profile's `openldap` on port 13890 is unchanged.

### Claude's Discretion
- JWT microservice language/framework (Python/FastAPI vs Node.js/jsonwebtoken)
- Port assignments for new services (must not conflict with existing: 443, 2222, 5555, 5556, 8000, 8443-8444, 9443, 10443, 11443, 12443, 13443, 13890, 14443, 15001, 15443, 15449, 15432, 15672, 16379, 16443, 17443, 18000, 18082, 19000, 21000-21002, 24443, 24566)
- Gitea version and init approach (API-only preferred)
- LocalStack KMS seed data (symmetric AES-256, RSA-2048, RSA-1024, ECC P-256)
- Vault transit engine key types (aes256-gcm96, rsa-2048, rsa-1024, ecdsa-p256)
- Postgres pgcrypto seed data
- Exact Dockerfile base images for ssh-weak
- LDAPS certificate (reuse `./certs/modern.crt`/`modern.key` or generate dedicated cert)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LAB-01 | jwt profile — 4 JWT API services (RS256, HS256-weak, RSA1024, alg:none) + JWKS server | JWT microservice patterns; JWKS JSON schema; Python/FastAPI or Node.js jsonwebtoken for key generation |
| LAB-02 | registry profile — Docker Registry v2 + test images with embedded crypto vulnerabilities | Docker Registry v2 API; Syft CRYPTO_LIB_ALLOWLIST shows which package names trigger findings; image push via curl or init container |
| LAB-03 | source profile — Gitea + pre-seeded repos with crypto anti-patterns | Gitea API init pattern; semgrep `p/cryptography` ruleset identifies which code patterns must appear |
| LAB-04 | storage profile — LocalStack KMS, HashiCorp Vault, postgres-encrypted | LocalStack `SERVICES=kms` env var; Vault dev mode + sidecar; pgcrypto extension in postgres |
| LAB-05 | ssh-weak service — OpenSSH with deliberately weak KEX/hostkey/MAC config | sshd_config directives; ubuntu:20.04 base; ssh-audit validates findings |
| LAB-06 | ldaps service — OpenLDAP over TLS (LDAPS on port 636) | osixia/openldap TLS env vars; existing certs in `./certs`; sslyze validates |
</phase_requirements>

---

## Summary

Phase 4 adds six Docker Compose profiles to `quantum-chaos-enterprise-lab/docker-compose.yml`. Each profile is a self-contained set of services that produces known, reproducible cryptographic findings validated by the Phase 3 scanners. The patterns are established in the existing lab: profile-tagged services, nginx TLS wrappers, sidecar init containers with `restart: "no"` and `depends_on: condition: service_healthy`.

The most technically involved profiles are `source` (Gitea API seeding) and `storage` (Vault dev mode sidecar). The `jwt` profile requires generating real RSA and HMAC key material inside containers, which is straightforward with Python's `cryptography` library or Node.js `jsonwebtoken`. The `registry` profile requires careful Dockerfile pinning to versions that Syft's `CRYPTO_LIB_ALLOWLIST` will flag — the allowlist is definitive (read directly from `quirk/scanner/container_scanner.py`).

The `ssh-weak` and `ldaps` profiles are the lowest complexity: both are single-service additions with well-understood Docker images and straightforward config injection.

**Primary recommendation:** Use Python/FastAPI for JWT microservices (consistent with the QU.I.R.K. codebase). Use `osixia/openldap:1.5.0` (same version as the existing identity profile) for LDAPS. Use `hashicorp/vault:1.15` for Vault dev mode.

---

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| docker-compose.yml profiles | Compose v2.x profile feature | Profile-tagged service isolation | Already established pattern in this lab |
| Python/FastAPI | Python 3.12-slim + fastapi + uvicorn | JWT microservice framework | Consistent with QU.I.R.K. codebase (Python-native) |
| python-jose / PyJWT | PyJWT>=2.12.0 (already in pyproject.toml) | JWT signing with RSA/HMAC keys | Already installed in QU.I.R.K. dependencies |
| registry:2 | Docker Hub `registry:2` | Docker Registry v2 | Official minimal registry image |
| ubuntu:18.04 | Official | image-old-libssl base | Carries OpenSSL 1.0.2 in apt repos |
| gitea/gitea:latest | Gitea Docker image | Source code host | Lightweight, fast startup, REST API |
| localstack/localstack:latest | Current | KMS simulation | Already used in `cloud` profile |
| hashicorp/vault:1.15 | Vault 1.15 | Transit engine + KV | Dev mode: no unseal step |
| postgres:16 | Official | pgcrypto target | Already used in `identity` and `phaseA` profiles |
| osixia/openldap:1.5.0 | Same as identity profile | LDAPS target | Same image as existing `openldap` service |

### Supporting
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| lscr.io/linuxserver/openssh-server | latest | ssh-weak base option | If ubuntu:20.04 has OpenSSH config conflicts |
| ubuntu:20.04 | Official | ssh-weak base (recommended) | Full control over sshd_config; simpler |
| nginx:stable | Already in lab | TLS wrapping | If any new service needs TLS proxy layer |
| alpine | Already in lab | Lightweight init containers / seed scripts | sidecar init container pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python/FastAPI JWT services | Node.js + jsonwebtoken | Node.js has slightly simpler JWT key config but breaks language consistency |
| ubuntu:18.04 for old libssl | debian:stretch | Debian stretch also has OpenSSL 1.0.x; ubuntu:18.04 is more familiar |
| Vault dev mode sidecar | Vault with file storage | Dev mode is single-step, no init/unseal complexity; fine for lab purposes |
| Gitea API seeding on startup | Pre-baked volume | API seeding is the decided approach (D-07); reproducible without volume management |

**Installation:** No new host dependencies. All services are Docker images pulled at compose up time.

---

## Architecture Patterns

### Recommended Project Structure
```
quantum-chaos-enterprise-lab/
├── docker-compose.yml          # All new services appended here with profile tags
├── jwt/
│   ├── Dockerfile              # Shared base for all 4 JWT services (or 4 separate dirs)
│   ├── rs256/main.py           # RS256 service
│   ├── hs256/main.py           # HS256-weak service
│   ├── rsa1024/main.py         # RSA-1024 service
│   └── algnone/main.py         # alg:none service
├── registry/
│   ├── seed.sh                 # Pushes test images into registry on startup
│   ├── image-old-libssl/Dockerfile
│   ├── image-old-pycrypto/Dockerfile
│   └── image-mixed/Dockerfile
├── source/
│   └── seed.sh                 # Creates Gitea org + repos + pushes crypto anti-pattern files
├── storage/
│   └── vault-seed.sh           # Vault sidecar script: enables transit, creates keys
├── ssh/
│   └── sshd_config             # Weak config mounted into ssh-weak container
└── expected_results_v3.md      # Update with new profile expected findings
```

### Pattern 1: Sidecar Init Container
**What:** A secondary container with `restart: "no"` and `depends_on: <primary>: condition: service_healthy` that runs a seed script once then exits.
**When to use:** Gitea seeding (source profile), Vault key creation (storage profile), Docker Registry image push (registry profile).
**Example:**
```yaml
# Source: established pattern from cloud profile + decisions D-06, D-07, D-11
gitea-seed:
  image: alpine
  profiles: ["source"]
  restart: "no"
  depends_on:
    gitea:
      condition: service_healthy
  volumes:
    - ./source/seed.sh:/seed.sh:ro
  command: ["/bin/sh", "/seed.sh"]
  environment:
    GITEA_URL: http://gitea:3000
    GITEA_ADMIN_USER: admin
    GITEA_ADMIN_PASSWORD: admin123
```

### Pattern 2: JWT JWKS Endpoint (Python/FastAPI)
**What:** FastAPI app that generates real key material on startup and serves it at `/.well-known/jwks.json` and `/token`.
**When to use:** All 4 JWT containers.
**Key insight:** The `alg:none` service must return a JWKS entry with `"alg": "none"` (or no `alg` field and `kty: "oct"` with zero key bits). The jwt_scanner falls back to `kty` if `alg` is absent — the `alg:none` entry should explicitly set `"alg": "none"` so the scanner classifies it correctly.

```python
# Source: jwt_scanner.py JWKS_PATHS[0] = "/.well-known/jwks.json"
# The scanner reads: kty, alg, n (RSA modulus), crv (EC curve), kid
# For alg:none: return {"keys": [{"kty": "oct", "alg": "none", "kid": "algnone-key-1"}]}
# For HS256-weak: 128-bit key (deliberately short), kty="oct", alg="HS256"
# For RS256: 2048-bit RSA key, kty="RSA", alg="RS256", n=<base64url modulus>
# For RSA1024: 1024-bit RSA key, kty="RSA", alg="RS256" (weak due to key size), n=<short modulus>
```

### Pattern 3: Docker Registry Seed via curl
**What:** A seed container uses `curl` to push pre-built Docker images to the local registry.
**When to use:** registry profile (D-06).
**Key approach:** Build images in a multi-stage Dockerfile step or push from a seed container that has Docker daemon access via `/var/run/docker.sock`. Simpler alternative: use `crane` (gcrane) or `skopeo` to copy images.

```yaml
# registry profile seed pattern
registry-seed:
  image: docker:dind  # has docker CLI
  profiles: ["registry"]
  restart: "no"
  depends_on:
    registry:
      condition: service_healthy
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
    - ./registry:/registry-build:ro
  command: ["/bin/sh", "/registry-build/seed.sh"]
```

### Pattern 4: Gitea API Seeding
**What:** Shell script calls the Gitea REST API to create admin user, organization, repos, then pushes files via git.
**When to use:** source profile (D-07).
**Key Gitea API endpoints:**
```
POST /api/v1/user/repos  — create repo under admin
POST /api/v1/orgs  — create org
POST /api/v1/api/v1/repos/{owner}/{repo}/contents/{filepath}  — create file via API
```
**Healthcheck:** Gitea exposes `GET /` returning 200 when ready. Seed container must wait for Gitea to be healthy before calling the API.

### Pattern 5: Vault Dev Mode Sidecar
**What:** `vault server -dev` starts pre-unsealed with root token. A sidecar container exports `VAULT_ADDR` and `VAULT_TOKEN` and calls the Vault CLI to enable transit engine and create keys.
**When to use:** storage profile (D-11).
**Key Vault CLI commands in seed script:**
```sh
vault secrets enable transit
vault write -f transit/keys/rsa-2048 type=rsa-2048
vault write -f transit/keys/rsa-1024 type=rsa-1024
vault write -f transit/keys/aes256 type=aes256-gcm96
vault write -f transit/keys/ecdsa-p256 type=ecdsa-p256
vault kv put secret/crypto-lab api_key="hardcoded-secret-12345"
```

### Pattern 6: sshd_config Injection
**What:** Mount a custom `sshd_config` file that explicitly overrides KexAlgorithms, HostKeyAlgorithms, and MACs with weak values.
**When to use:** ssh-weak profile (D-12, D-13).
**Critical sshd_config directives** (ssh-audit will flag all of these):
```
KexAlgorithms diffie-hellman-group1-sha1,diffie-hellman-group14-sha1
HostKeyAlgorithms ssh-dss
MACs hmac-md5,hmac-sha1
```
**Important:** On modern OpenSSH (>= 8.x), `diffie-hellman-group1-sha1` and `ssh-dss` are compiled out by default. ubuntu:20.04 ships OpenSSH 8.2, which may still have these but they are disabled at compile time. If they are unavailable at runtime, sshd will refuse to start. **Use ubuntu:18.04 for ssh-weak** (ships OpenSSH 7.6p1 which still supports these legacy algorithms), OR use the `RekeyLimit 0 0` + `--enable-legacy-groups` approach. The safest approach is ubuntu:18.04 for the ssh-weak service.

### Anti-Patterns to Avoid
- **Do not add services without profile tags:** Any service without a profile tag starts with every `docker compose up`. All new Phase 4 services MUST have `profiles: ["<name>"]`.
- **Do not duplicate existing cloud profile LocalStack:** D-09 locks this — the storage profile's LocalStack uses `SERVICES=kms` only, on a different internal port than the cloud profile's LocalStack.
- **Do not pre-bake Gitea volumes:** D-07 locks API seeding. Pre-baked volumes break reproducibility when repo content changes.
- **Do not use `alg:none` JWT service without explicit JWKS entry:** The scanner reads JWKS. If the service does not return a valid JWKS JSON body, the scanner returns nothing for that service. The alg:none service must serve a JWKS endpoint.
- **Do not rely on osixia/openldap auto-TLS:** The osixia image generates self-signed certs if none are provided. For LDAPS validation with sslyze, mount known certs from `./certs` so sslyze has a predictable TLS target.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT RS256 key generation | Python RSA key math from scratch | `from cryptography.hazmat.primitives.asymmetric import rsa` | Already in QU.I.R.K. venv; handles padding, exponent, modulus encoding |
| JWKS JSON serialization | Manual base64url encoding of RSA modulus | `from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat` + `jwcrypto` or `python-jose` | Correct base64url (no padding) is non-trivial; PyJWT/python-jose already installed |
| Docker image pushing | Manual registry HTTP API calls | `docker push localhost:<port>/image-name` via docker CLI in seed container | Docker Registry v2 API auth negotiation is complex; use Docker CLI |
| Vault initialization | Custom Vault API calls | `vault` CLI in sidecar | Vault CLI handles token auth header automatically |
| Gitea org/repo creation | Manual HTTP calls | `curl -H "Authorization: token ..."` Gitea REST API | Gitea's API is straightforward but token auth is required; don't use httpx from QU.I.R.K. |

**Key insight:** All the crypto primitives needed for JWT key generation are already in the QU.I.R.K. virtualenv (`cryptography`, `PyJWT`, `python-jose`). The FastAPI JWT microservice images can be built on `python:3.12-slim` with a minimal requirements.txt.

---

## Runtime State Inventory

> This is a greenfield Docker Compose expansion phase — no rename or migration. Runtime state inventory is minimal.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — new profiles create fresh containers on each `up` | None — seed scripts run on each startup |
| Live service config | Existing `cloud` profile LocalStack state (if running) | None — D-09 uses separate LocalStack instance for storage profile |
| OS-registered state | None | None |
| Secrets/env vars | `VAULT_DEV_ROOT_TOKEN_ID` used in Vault dev mode | Set in docker-compose.yml environment block; value is "root" for lab use only |
| Build artifacts | JWT microservice Docker images built locally via `build:` directive | Images built at `docker compose --profile jwt build`; no registry push needed |

---

## Common Pitfalls

### Pitfall 1: OpenSSH Legacy Algorithm Availability
**What goes wrong:** The `ssh-weak` container fails to start because sshd refuses the sshd_config directives `diffie-hellman-group1-sha1`, `ssh-dss`, or `hmac-md5` on modern OpenSSH.
**Why it happens:** OpenSSH >= 8.x removes support for SHA1-based KEX and DSS host keys at compile time on modern Ubuntu/Debian images.
**How to avoid:** Use `ubuntu:18.04` as the base for the ssh-weak Dockerfile. ubuntu:18.04 ships OpenSSH 7.6p1 which still supports these legacy algorithms. Add the `AllowUsers` directive and test with `sshd -T` to verify config is accepted.
**Warning signs:** Container exits immediately with `no hostkeys available` or `Bad configuration option` in logs.

### Pitfall 2: Docker Registry Push Requires Image Already Tagged
**What goes wrong:** The seed script tries to push an image that hasn't been built or hasn't been tagged with the registry's address.
**Why it happens:** Docker images must be tagged as `localhost:<port>/image-name:tag` before `docker push`. If the seed container doesn't have a built image, push fails silently.
**How to avoid:** Use `build:` stanzas in docker-compose.yml for each registry test image. The seed script then tags and pushes already-built images. Alternatively, use the seed container to `docker build` then `docker push` using the socket mount.
**Warning signs:** Seed container exits 0 but registry catalog is empty (`curl localhost:<port>/v2/_catalog`).

### Pitfall 3: Gitea Startup Race Condition
**What goes wrong:** The Gitea seed container starts API calls before Gitea's HTTP server is ready, resulting in connection refused errors and the seed container exiting with error.
**Why it happens:** `condition: service_healthy` requires a healthcheck defined on the Gitea service. Gitea's official Docker image may not include a healthcheck by default.
**How to avoid:** Add an explicit `healthcheck` to the Gitea service:
```yaml
healthcheck:
  test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/"]
  interval: 10s
  timeout: 5s
  retries: 10
  start_period: 30s
```
Also add a `while ! curl -s http://gitea:3000/ > /dev/null; do sleep 2; done` loop at the start of the seed script as defense in depth.
**Warning signs:** Seed container exits with `connection refused` or `curl: (7)`.

### Pitfall 4: Vault Sidecar Token Not Yet Available
**What goes wrong:** Vault sidecar tries to run `vault secrets enable transit` before Vault dev mode has written its root token.
**Why it happens:** `vault server -dev` starts but there is a brief window before it accepts API calls.
**How to avoid:** Add a healthcheck to the Vault service on port 8200 (`GET /v1/sys/health` returns 200 when initialized). Configure the sidecar with `depends_on: vault: condition: service_healthy`. Add a `sleep 3` in the sidecar script as additional buffer.
**Warning signs:** Vault sidecar exits with `connection refused` or `permission denied` on vault CLI calls.

### Pitfall 5: Syft CRYPTO_LIB_ALLOWLIST — Exact Package Name Match
**What goes wrong:** Registry test images are built with old crypto libraries but Syft doesn't detect them because the package names don't match the allowlist in `container_scanner.py`.
**Why it happens:** The allowlist is `frozenset` and uses `name.lower()` comparison. The exact package names that are matched:
`openssl`, `libssl`, `libssl3`, `libssl1.1`, `libcrypto`, `libcrypto3`, `botan`, `libgcrypt`, `libgcrypt20`, `nss`, `libnss3`, `mbedtls`, `libmbedtls`, `wolfssl`, `gnutls`, `libgnutls`, `cryptography`, `pyopenssl`, `pycryptodome`, `pycryptodomex`, `bcrypt`, `nacl`, `pynacl`.
**How to avoid:** Install exactly these package names in the test Dockerfiles. For `image-old-libssl`: `apt-get install libssl1.1` (ubuntu:18.04 has 1.0.x as `libssl1.0.0`). For `image-old-pycrypto`: `pip install cryptography==2.9.2 pyOpenSSL==19.1.0` — these names are `cryptography` and `pyopenssl` respectively (both in the allowlist).
**Warning signs:** `docker run syft localhost:<port>/image-old-libssl -o json | jq '.artifacts[].name'` shows no crypto lib names matching the allowlist.

### Pitfall 6: LDAPS osixia/openldap Certificate Configuration
**What goes wrong:** The LDAPS service starts but sslyze cannot connect because the container uses self-generated certs (not the known lab certs).
**Why it happens:** `osixia/openldap` with `LDAP_TLS=true` and no explicit cert configuration generates its own CA and self-signed cert inside the container on first startup.
**How to avoid:** Mount the existing lab certs (`modern.crt`, `modern.key`, `ca.crt`) and set the environment variables:
```yaml
environment:
  LDAP_TLS: "true"
  LDAP_TLS_CRT_FILENAME: modern.crt
  LDAP_TLS_KEY_FILENAME: modern.key
  LDAP_TLS_CA_CRT_FILENAME: ca.crt
volumes:
  - ./certs:/container/service/slapd/assets/certs:ro
```
The osixia image reads TLS cert files from `/container/service/slapd/assets/certs/`.
**Warning signs:** `sslyze --targets localhost:636` fails with certificate error.

### Pitfall 7: Port Conflict with Existing Lab Services
**What goes wrong:** A new Phase 4 service fails to bind its port because another lab service already uses it.
**Why it happens:** The existing lab occupies: 443, 2222, 5555, 5556, 8000, 8443-8444, 9443, 10443, 11443, 12443, 13443, 13890, 14443, 15001, 15432, 15443, 15449, 15672, 16379, 16443, 17443, 18000, 18082, 19000, 21000-21002, 24443, 24566.
**How to avoid:** Use ports in the 20000-23999 range (currently unused) for new JWT services. Recommended safe port assignments:
- JWT RS256: 20001
- JWT HS256-weak: 20002
- JWT RSA1024: 20003
- JWT alg:none: 20004
- Docker Registry: 20005
- Gitea: 20006
- LocalStack KMS (storage): 20007 (different from cloud profile's internal 4566)
- LocalStack KMS TLS wrapper: 20008
- Vault: 20009
- Postgres-pgcrypto: 20010
- SSH-weak: 20022 (2022 is ambiguous; this is clearly lab-only)
- LDAPS: 636 (standard LDAPS port — must use this for sslyze validation)
**Warning signs:** `docker compose up` fails with `bind: address already in use`.

### Pitfall 8: Gitea Admin User Init Mode
**What goes wrong:** Gitea API calls return 403 or 404 because Gitea has not completed initial setup.
**Why it happens:** Gitea's first startup requires setting an admin user. If launched without `GITEA__security__INSTALL_LOCK=true`, it stays in install mode and the API is unavailable.
**How to avoid:** Set these environment variables on the Gitea service:
```yaml
environment:
  GITEA__security__INSTALL_LOCK: "true"
  GITEA__database__DB_TYPE: sqlite3
  GITEA__database__PATH: /data/gitea.db
  GITEA__server__ROOT_URL: "http://gitea:3000/"
  GITEA__admin__DISABLE_REGULAR_ORG_CREATION: "false"
```
Create the admin user via `gitea admin user create` CLI on container startup (use an entrypoint wrapper) OR set via environment before the seed container hits the API.
**Warning signs:** Seed container returns `{"message":"Forbidden"}` on POST to `/api/v1/user/repos`.

---

## Code Examples

### JWT alg:none JWKS Response (Python)
```python
# Source: jwt_scanner.py — scanner checks kty, alg, n, crv fields
# The alg:none service MUST return a JWKS with these fields to be detected:
JWKS_ALGNONE = {
    "keys": [
        {
            "kty": "oct",
            "alg": "none",
            "kid": "algnone-key-1",
            "k": ""   # empty key material
        }
    ]
}
# JWT issued by this service has header: {"alg": "none"} — no signature
```

### JWT RS256 JWKS Key Generation (Python)
```python
# Source: PyJWT docs + python-cryptography (already in pyproject.toml)
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import base64, struct

def generate_rs256_jwks():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = private_key.public_key().public_numbers()
    def b64url(n):
        length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(length, 'big')).rstrip(b'=').decode()
    return {"keys": [{"kty": "RSA", "alg": "RS256", "kid": "rs256-key-1",
                      "n": b64url(pub.n), "e": b64url(pub.e), "use": "sig"}]}
```

### RSA-1024 JWKS (weak key size — scanner flags this)
```python
# Same as RS256 but key_size=1024
# jwt_scanner._rsa_key_bits_from_n() will compute 1024 bits from modulus
# The scanner produces: cert_pubkey_size=1024 (flags as weak RSA)
private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
```

### LocalStack KMS Seed (shell)
```bash
# Source: aws_connector.py KMS_KEY_SPEC_MAP — these key specs must exist
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
ENDPOINT=http://localstack-kms:4566

aws --endpoint-url=$ENDPOINT kms create-key --key-spec SYMMETRIC_DEFAULT --key-usage ENCRYPT_DECRYPT
aws --endpoint-url=$ENDPOINT kms create-key --key-spec RSA_2048 --key-usage SIGN_VERIFY
aws --endpoint-url=$ENDPOINT kms create-key --key-spec RSA_1024 --key-usage SIGN_VERIFY  # weak
aws --endpoint-url=$ENDPOINT kms create-key --key-spec ECC_NIST_P256 --key-usage SIGN_VERIFY
```

### Gitea API Seed (shell)
```bash
# Source: Gitea REST API v1 — standard pattern
GITEA_URL="http://gitea:3000"
ADMIN_USER="admin"
ADMIN_PASS="admin123"

# Create repo
curl -s -X POST "${GITEA_URL}/api/v1/user/repos" \
  -H "Content-Type: application/json" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -d '{"name": "crypto-antipatterns", "private": false, "auto_init": true}'

# Push a file via API (base64-encoded content)
CONTENT=$(echo 'import hashlib; h = hashlib.md5(b"data").hexdigest()' | base64)
curl -s -X POST "${GITEA_URL}/api/v1/repos/${ADMIN_USER}/crypto-antipatterns/contents/auth.py" \
  -H "Content-Type: application/json" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -d "{\"message\": \"seed\", \"content\": \"${CONTENT}\"}"
```

### Vault Dev Mode Sidecar (shell)
```bash
#!/bin/sh
# Source: HashiCorp Vault CLI docs — dev mode standard init
export VAULT_ADDR="http://vault:8200"
export VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN_ID:-root}"

until vault status 2>/dev/null; do sleep 2; done

vault secrets enable transit
vault write -f transit/keys/rsa-2048 type=rsa-2048
vault write -f transit/keys/rsa-1024 type=rsa-1024
vault write -f transit/keys/aes256 type=aes256-gcm96
vault write -f transit/keys/ecdsa-p256 type=ecdsa-p256
vault kv put secret/crypto-lab api_key="hardcoded-secret-12345"
```

### postgres pgcrypto Seed (SQL)
```sql
-- Source: PostgreSQL pgcrypto docs
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE encrypted_demo (
    id SERIAL PRIMARY KEY,
    data_sym TEXT,    -- pgp_sym_encrypt example
    data_hash TEXT    -- crypt() + gen_salt() example
);
INSERT INTO encrypted_demo (data_sym, data_hash)
VALUES (
    pgp_sym_encrypt('sensitive-value', 'weakpassword'),
    crypt('password123', gen_salt('md5'))  -- weak: MD5 salt
);
```

### sshd_config for ssh-weak
```
# /etc/ssh/sshd_config for ssh-weak container (ubuntu:18.04 / OpenSSH 7.6p1)
Port 22
Protocol 2
HostKey /etc/ssh/ssh_host_dsa_key
HostKey /etc/ssh/ssh_host_rsa_key

KexAlgorithms diffie-hellman-group1-sha1,diffie-hellman-group14-sha1,diffie-hellman-group-exchange-sha1
HostKeyAlgorithms ssh-dss,ssh-rsa
MACs hmac-md5,hmac-sha1,umac-64@openssh.com

PasswordAuthentication yes
PermitRootLogin yes
```

### Docker Compose LDAPS Service
```yaml
# Source: osixia/openldap documentation + existing identity profile pattern
ldaps:
  image: osixia/openldap:1.5.0
  profiles: ["ldaps"]
  environment:
    LDAP_ORGANISATION: "ChaosLab"
    LDAP_DOMAIN: "chaos.local"
    LDAP_ADMIN_PASSWORD: "admin"
    LDAP_TLS: "true"
    LDAP_TLS_CRT_FILENAME: "modern.crt"
    LDAP_TLS_KEY_FILENAME: "modern.key"
    LDAP_TLS_CA_CRT_FILENAME: "ca.crt"
    LDAP_TLS_VERIFY_CLIENT: "never"
  volumes:
    - ./certs:/container/service/slapd/assets/certs:ro
  ports:
    - "636:636"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| All services in one docker-compose.yml without profiles | Profile-tagged services (Compose v2.x) | Compose v2 (2021) | Services only start when explicitly requested |
| `SERVICES=s3,sts,iam,kms` monolith LocalStack | Per-purpose LocalStack instances with `SERVICES=kms` | LocalStack v2+ | Faster startup; avoids port conflicts between profiles |
| Vault with manual init/unseal steps | Vault dev mode (`vault server -dev`) | Always available | Zero-step: starts pre-unsealed, no manual init in lab context |
| osixia/openldap with auto-generated TLS certs | Mount known certs, disable auto-generation | Always supported | sslyze can validate predictable cert material |

**Deprecated/outdated:**
- `SERVICES` env var in LocalStack: LocalStack v3+ uses service auto-activation. Specifying `SERVICES=kms` still works for pinning, but v3+ ignores unknown services gracefully.
- `osixia/openldap:latest` tag: Use pinned `1.5.0` (same as identity profile) for reproducibility.

---

## Open Questions

1. **RSA-1024 key generation on modern OpenSSL**
   - What we know: Python's `cryptography` library wraps OpenSSL. Modern OpenSSL (3.x) may refuse to generate RSA-1024 keys due to FIPS restrictions.
   - What's unclear: Whether `python:3.12-slim` (OpenSSL 3.x) will allow `rsa.generate_private_key(key_size=1024)`.
   - Recommendation: Test during Wave 0. If blocked, pre-generate the RSA-1024 key at build time and include it as a static file in the Dockerfile. This is deterministic and avoids runtime failures.

2. **Gitea admin user bootstrap**
   - What we know: Gitea requires an admin user. Setting `GITEA__security__INSTALL_LOCK=true` bypasses the install wizard.
   - What's unclear: Whether the Gitea Docker image supports creating the admin user via environment variable (some versions do; current does not).
   - Recommendation: Use `gitea admin user create` via a `command` override or by adding the command to the container's startup via the seed script connecting via docker exec. Alternatively, bootstrap via the Gitea REST API's initial setup endpoint if available.

3. **Docker Registry image build context in compose**
   - What we know: `build:` stanzas in docker-compose.yml build images locally. The registry seed container needs Docker daemon access.
   - What's unclear: Whether the seed container approach (socket mount) works cleanly on macOS Docker Desktop (socket path varies).
   - Recommendation: Use `docker buildx build --load` in the seed script rather than `docker build`, which has more consistent behavior on Docker Desktop for macOS.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | All profiles | Yes | 29.2.1 | None (required) |
| Docker Compose | All profiles | Yes | v5.0.2 | None (required) |
| syft | LAB-02 validation | Yes | Available (`/opt/homebrew/bin/syft`) | None for validation |
| semgrep | LAB-03 validation | No | Not found | Install with `pip install semgrep` before validation |
| sslyze | LAB-06 validation | No | Not found | Install with `pip install sslyze` before validation |
| ssh-audit | LAB-05 validation | Not checked | — | Install with `pip install ssh-audit` or `brew install ssh-audit` |

**Missing dependencies with no fallback:**
- semgrep: Required to validate LAB-03 (source profile). Must be installed before running validation.
- sslyze: Required to validate LAB-06 (ldaps profile). Must be installed before running validation.

**Missing dependencies with fallback:**
- None among the Docker-based services. All Docker images are pulled at compose up time.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml (no separate pytest.ini) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map

Phase 4 is an infrastructure phase — all deliverables are Docker Compose profiles and Dockerfiles. The acceptance criteria are integration tests that require running Docker containers, not unit tests. The existing pytest suite does not cover live Docker services.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAB-01 | `docker compose --profile jwt up` starts 4 JWT services; scanner finds >= 2 weak-alg findings | integration/smoke | `docker compose --profile jwt up -d && sleep 5 && python -c "from quirk.scanner.jwt_scanner import scan_jwt_targets; r=scan_jwt_targets(['http://localhost:20001','http://localhost:20002','http://localhost:20003','http://localhost:20004']); print(len(r)); assert len(r) >= 2"` | N/A — manual smoke |
| LAB-02 | Registry starts; container scanner detects embedded crypto library issues | integration/smoke | `docker compose --profile registry up -d && syft localhost:20005/image-old-pycrypto -o json \| jq '.artifacts[].name'` | N/A — manual smoke |
| LAB-03 | Gitea starts; semgrep returns >= 1 algorithm finding per seeded anti-pattern | integration/smoke | `docker compose --profile source up -d && semgrep --json --config p/cryptography <cloned-repo-path>` | N/A — manual smoke |
| LAB-04 | LocalStack KMS and Vault respond to scan queries | integration/smoke | `docker compose --profile storage up -d && aws --endpoint-url=http://localhost:20007 kms list-keys` | N/A — manual smoke |
| LAB-05 | ssh-weak starts; ssh-audit returns weak KEX/hostkey/MAC findings | integration/smoke | `docker compose --profile ssh-weak up -d && ssh-audit localhost:20022` | N/A — manual smoke |
| LAB-06 | ldaps starts on 636; sslyze returns TLS findings | integration/smoke | `docker compose --profile ldaps up -d && sslyze --targets localhost:636` | N/A — manual smoke |

**Note:** All LAB requirements are integration tests, not unit tests. The existing test suite (pytest) covers scanner unit logic. Lab validation is performed by the smoke test commands above at phase gate.

### Wave 0 Gaps
- No new pytest test files are needed for this phase — Phase 4 delivers Docker infrastructure, not Python code.
- The validation commands above should be documented in `expected_results_v3.md` (updated as part of this phase).

---

## Sources

### Primary (HIGH confidence)
- `quirk/scanner/jwt_scanner.py` — JWKS_PATHS, key parsing logic, scanner contract (read directly)
- `quirk/scanner/container_scanner.py` — CRYPTO_LIB_ALLOWLIST (read directly)
- `quirk/scanner/source_scanner.py` — semgrep `p/cryptography` config used (read directly)
- `quirk/scanner/aws_connector.py` — KMS_KEY_SPEC_MAP; which key specs must exist in LocalStack KMS (read directly)
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing port assignments and profile patterns (read directly)
- `quantum-chaos-enterprise-lab/lab.sh` — PROFILE_ARGS pattern for profile selection (read directly)
- `.planning/phases/04-chaos-lab-expansion/04-CONTEXT.md` — All locked decisions (read directly)

### Secondary (MEDIUM confidence)
- osixia/openldap Docker image environment variables — standard TLS config (`LDAP_TLS_CRT_FILENAME`, etc.) is well-documented in the image README; confirmed consistent with `identity` profile behavior in the existing docker-compose.yml
- HashiCorp Vault dev mode behavior — `vault server -dev` pattern is well-established; confirmed from Vault documentation patterns (training data, HIGH confidence for stable feature)
- Gitea INSTALL_LOCK and API seeding — confirmed by Gitea Docker documentation patterns (MEDIUM confidence; specific env var names may differ in latest Gitea version)

### Tertiary (LOW confidence)
- OpenSSH 7.6p1 legacy algorithm support on ubuntu:18.04 — training data claim; should be verified by `sshd -T` output during Wave 0 build

---

## Project Constraints (from CLAUDE.md)

No `CLAUDE.md` was found in the project root. No project-specific override directives apply.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all images are either already in use (localstack, osixia/openldap, postgres) or are standard Docker Hub official images
- Architecture: HIGH — patterns read directly from existing docker-compose.yml and scanner source code
- Pitfalls: HIGH for Docker/Compose mechanics; MEDIUM for OpenSSH legacy algorithm availability (requires runtime verification)
- Port assignments: HIGH — read directly from existing docker-compose.yml

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (Docker image versions are stable; Gitea API may change in major versions)
