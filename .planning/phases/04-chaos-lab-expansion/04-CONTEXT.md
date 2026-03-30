# Phase 4: Chaos Lab Expansion - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Add six Docker Compose profiles to the existing `quantum-chaos-enterprise-lab/` chaos lab — `jwt`, `registry`, `source`, `storage`, `ssh-weak`, and `ldaps` — each producing known, reproducible findings that validate the corresponding Phase 3 scanner. No scanner code changes (Phase 3 complete). No UI (Phase 5). No documentation (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### JWT Profile (LAB-01)
- **D-01:** 4 separate microservice containers — one per algorithm type: RS256, HS256-weak, RSA1024, alg:none. Each container gets its own port and distinct JWT behavior. Not a single multi-endpoint service.
- **D-02:** Each JWT service exposes two endpoints: `/.well-known/jwks.json` (JWKS discovery with key material) and `/token` (issues a signed JWT). The scanner hits JWKS discovery and can optionally fetch a live token.
- **D-03:** Language/framework for JWT microservices is Claude's discretion. (Python/FastAPI preferred for consistency with QU.I.R.K. codebase, but Node.js/jsonwebtoken is acceptable if simpler for key config.)

### Registry Profile (LAB-02)
- **D-04:** Build custom Dockerfiles with deliberately old crypto library versions — not old base images pulled from Docker Hub. This ensures controlled, documented expected findings.
- **D-05:** 3 test images:
  - `image-old-libssl` — based on ubuntu:18.04 or similar, installs OpenSSL 1.0.x
  - `image-old-pycrypto` — installs `python-cryptography<3.0` and `pyOpenSSL<22`
  - `image-mixed` — combines old libssl + old python-cryptography + a Go binary with embedded crypto
- **D-06:** Images are pushed to the Docker Registry v2 container on profile startup via a seed script or init container.

### Source Profile (LAB-03)
- **D-07:** Gitea repos are pre-seeded via an init script that runs on container startup — creates org + repos via the Gitea API, then pushes pre-written files with crypto anti-patterns. No pre-baked volume required.
- **D-08:** Four categories of crypto anti-patterns to seed:
  - Hardcoded keys/secrets (RSA private keys in source files, hardcoded AES keys, API secrets)
  - Weak algorithm usage (MD5/SHA1 for integrity, DES/3DES/RC4 for encryption, ECB mode)
  - Weak random / custom crypto (random.random() for security, custom XOR-based encryption, home-rolled PRNG)
  - Deprecated protocol usage (explicit SSL/TLS 1.0 version pinning in code, MD2/MD4 references, RC4 in config)

### Storage Profile (LAB-04)
- **D-09:** New `storage` profile — independent of the existing `cloud` profile. The `cloud` profile (LocalStack with S3/STS/IAM) is left untouched for backwards compatibility.
- **D-10:** Storage profile includes: LocalStack with `SERVICES=kms` (KMS-only, not duplicating S3/STS/IAM from cloud), HashiCorp Vault, and postgres with pgcrypto extension.
- **D-11:** HashiCorp Vault in dev mode (`vault server -dev`) with `VAULT_DEV_ROOT_TOKEN_ID` set, plus a sidecar that writes transit engine keys and KV secrets on startup. Scanner can hit the Vault API immediately without manual init/unseal.

### ssh-weak Service (LAB-05)
- **D-12:** Custom Dockerfile extending a suitable base image (ubuntu:20.04 or lscr.io/linuxserver/openssh-server), injecting a custom `sshd_config` that explicitly enables: weak KEX (`diffie-hellman-group1-sha1`, `diffie-hellman-group14-sha1`), weak hostkey (`ssh-dss`), weak MAC (`hmac-md5`, `hmac-sha1`). ssh-audit will flag all of these as critical/warning findings.
- **D-13:** ssh-weak service uses the `ssh-weak` profile — separate from the base `ssh-alt` service which remains vanilla.

### LDAPS Service (LAB-06)
- **D-14:** New `ldaps` profile with its own `osixia/openldap` container — independent of the existing `openldap` service in the `identity` profile. Configured with `LDAP_TLS=true`, certs mounted from the existing `./certs` directory, binds LDAPS on port 636 (exposed as a host port).
- **D-15:** The existing `identity` profile's `openldap` service (plain LDAP on port 13890) is unchanged.

### Claude's Discretion
- JWT microservice language/framework (Python/FastAPI vs Node.js/jsonwebtoken)
- Port assignments for new services (must not conflict with existing lab ports: 443, 2222, 8000, 8443-8444, 9443, 10443, 11443, 13890, 15449, 16443-19000, 24566)
- Gitea version and whether to use Gitea's built-in admin setup or API-only init
- LocalStack KMS seed data (key specs to pre-create: symmetric AES-256, RSA-2048, RSA-1024, ECC P-256)
- Vault transit engine key types to pre-create (aes256-gcm96, rsa-2048, rsa-1024, ecdsa-p256)
- Postgres pgcrypto seed data (tables with pgp_sym_encrypt, crypt/gen_salt examples)
- Exact Dockerfile base images for ssh-weak (ubuntu:20.04 is a safe default)
- LDAPS certificate — reuse `./certs/modern.crt` / `modern.key` or generate a dedicated cert

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing chaos lab
- `quantum-chaos-enterprise-lab/docker-compose.yml` — Full existing compose file; all new services must extend this file with new profiles. Note existing port assignments to avoid conflicts.
- `quantum-chaos-enterprise-lab/README.md` — Lab usage guide; new profiles should follow the same usage pattern
- `quantum-chaos-enterprise-lab/CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` — Build and operations reference for the lab

### Phase 3 scanner code (new profiles must validate these)
- `quirk/scanner/jwt_scanner.py` — JWT scanner implementation; the `jwt` lab profile must produce findings this scanner can discover via JWKS at `/.well-known/jwks.json`
- `quirk/scanner/container_scanner.py` — Container scanner (Syft subprocess); the `registry` lab profile must have images that Syft detects old crypto libs in
- `quirk/scanner/source_scanner.py` — Source code scanner (semgrep); the `source` lab profile's Gitea repos must contain patterns that `semgrep --config p/cryptography` flags
- `quirk/scanner/aws_scanner.py` — AWS scanner; the `storage` profile's LocalStack KMS must be reachable and contain key specs the scanner returns
- `run_scan.py` — Full orchestration; shows how scanner targets are configured (JWT base URLs, container image refs, source repo paths, cloud config)

### Requirements
- `.planning/REQUIREMENTS.md` §LAB — LAB-01 through LAB-06 acceptance criteria for each profile
- `.planning/ROADMAP.md` §Phase 4 — Success criteria (6 items, one per profile)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quantum-chaos-enterprise-lab/certs/` — Existing self-signed certs (modern.crt/key, expired.crt/key, etc.) — reusable for LDAPS and any new TLS-wrapped services
- `quantum-chaos-enterprise-lab/scripts/` — Existing cert generation scripts (`gen-certs.sh`, `gen_phaseA_certs.sh`) — pattern for generating new certs if needed
- `quantum-chaos-enterprise-lab/lab.sh` — Lab control script; any new profiles should work with existing start/stop commands

### Established Patterns
- Profile isolation: each profile is self-contained — services tagged with a profile only start when `--profile <name>` is passed
- LocalStack pattern: LocalStack service (internal) + nginx TLS wrapper (external) — the `storage` profile's LocalStack KMS can follow the same localstack/localstack-tls pattern from the `cloud` profile
- Init/seed pattern: Not yet established for Gitea or Vault — new `source` and `storage` profiles will set the precedent. Consider a sidecar container with `restart: "no"` and `depends_on` with `condition: service_healthy`
- Cert reuse: `./certs` mounted as read-only volume — established in identity/pki profiles; LDAPS service should follow this

### Integration Points
- `quantum-chaos-enterprise-lab/docker-compose.yml` — All new services added here with new profile tags
- `quantum-chaos-enterprise-lab/expected_results_v3.md` — Expected scanner findings document; update with expected findings per new profile
- `run_scan.py` config: `quirk/config.py` `ConnectorsCfg` — JWT base URLs, container image refs, and cloud endpoints are configured here; lab profiles must be reachable at the configured addresses

</code_context>

<specifics>
## Specific Ideas

- JWT services: 4 separate containers on distinct ports. The alg:none service is the most critical for scanner validation — it must produce a JWT with no signature verification and expose it via JWKS.
- Registry images: 3 images pushed to the local Docker Registry v2. The `image-mixed` image (old libssl + old python-cryptography + Go binary) is the richest target for Syft.
- Gitea source seeding: init script creates at minimum 2-3 repos with files spread across multiple languages (Python, Go, Java where feasible) so semgrep hits multiple rule categories.
- Storage profile: LocalStack KMS-only instance (not duplicating the S3/STS/IAM from cloud profile) + Vault dev mode + postgres. These are all independent services in the same `storage` profile.
- ssh-weak: custom Dockerfile is the right call — the linuxserver/openssh-server image environment vars cannot reliably override `KexAlgorithms`, `HostKeyAlgorithms`, and `MACs` in sshd_config without a full config replacement.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-chaos-lab-expansion*
*Context gathered: 2026-03-30*
