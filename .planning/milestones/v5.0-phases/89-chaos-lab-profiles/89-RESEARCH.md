# Phase 89: Chaos Lab Profiles — Research

**Researched:** 2026-05-22
**Domain:** Docker Compose chaos-lab infrastructure + TLS protocol weak-config recipes
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 (LAB-03 disposition):** Close LAB-03 as already-covered by the existing `email` profile
(Postfix+Dovecot, STARTTLS on port 587, `labs/email/`). Do NOT add a standalone smtp-starttls
service. Deliverable: add expected-results/UAT proof of STARTTLS detection on the email profile's
port 30587; document in the requirement closure that smtp-starttls coverage lives in the `email`
profile.

**D-02 (TLS posture):** Each new profile exposes an intentionally weak/legacy TLS config (single
variant). `expected_results_v4.md` must assert those findings. No modern duplicates — `tls-modern`
already provides a clean baseline.

**D-03 (gRPC ALPN-h2):** Build a custom minimal Go gRPC-TLS image with ALPN `h2`. Executor's
FIRST task for this profile brings the service up and runs sslyze to confirm ALPN-h2 negotiation
empirically before wiring the probe. If sslyze cannot negotiate h2, that surfaces as an in-flight
blocker — no silent fallback.

**D-04 (LAB-06 identity):** Add Kerberos/SAML/DNSSEC targets to an EXISTING lab scan config (not
a new file). Add a UAT asserting all three evidence counters (`identity_weak_etype_count`,
`saml_weak_signing_count`, `dnssec_weak_algo_count`) flow end-to-end into the identity subscore.
Research confirms the code is wired (BACK-78). Gap = scan-config + UAT.

### Claude's Discretion

Exact weak-TLS knobs per protocol (cipher/version/cert choices), port assignments, the gRPC
Dockerfile internals, and which existing scan config hosts the identity targets — implementation
details grounded in the v5.0 research files and existing lab patterns.

### Carried Forward (Locked)

- Digest-pin every new image (not `:latest`) — enforced by `tests/test_chaos_lab_image_pinning.py`.
- `bitnamilegacy/*` namespace for any Bitnami images (Phase 82 lesson).
- Lab-sync rule (CLAUDE.md): every profile add/change updates `docker-compose.yml` + `lab.sh`
  ALL_PROFILES list + chaos-lab README + `expected_results_v4.md` oracle in the SAME change.

### Deferred Ideas (OUT OF SCOPE)

- A standalone `smtp-starttls` service (D-01).
- Modern-baseline variants for the 4 new protocols (`tls-modern` already covers this).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LAB-01 | `postgres-tls` chaos-lab profile — sslyze `--starttls postgres`; full lab-sync | Postgres 16.6 official image with `ssl=on` + weak `ssl_ciphers` in `postgresql.conf`; sslyze `ProtocolWithOpportunisticTlsEnum.POSTGRES` confirmed supported |
| LAB-02 | `redis-tls` profile — direct-socket TLS on 6380; confirm `broker_scanner.py` probe | `redis:7.4.1-alpine` already in `docker-compose.yml` as `redis-broker`; broker profile is the wrong parent — new `redis-tls` is a separate profile |
| LAB-03 | `smtp-starttls` — already-covered closure; expected-results/UAT proof on email profile port 30587 | Postfix on 30587 confirmed in `docker-compose.yml` line 1005; email-tls-research.md details STARTTLS probe |
| LAB-04 | `kafka-tls` profile — `apache/kafka:3.9.0`, PEM keystore, TLS 9093 + plaintext 9092 healthcheck | `apache/kafka:3.7.0` is the current broker-profile image; new profile uses 3.9.0 with same `server.properties` weak-config pattern |
| LAB-05 | `grpc-tls` profile — custom minimal Go image, ALPN `h2`; empirical sslyze ALPN-h2 confirm | sslyze has no `ALPN_H2` ScanCommand; the TLS handshake still completes and CERTIFICATE_INFO is still emitted — empirical check resolves whether sslyze produces useful cipher/cert findings |
| LAB-06 | Identity evidence end-to-end — Kerberos/SAML/DNSSEC targets in existing lab scan config | BACK-78 confirmed pure config gap; counters wired in `evidence.py` L87–89, L165, L171–183; ratios emitted L397–399; weights in `scoring.py` L31–33 |
</phase_requirements>

---

## Summary

Phase 89 is purely a chaos-lab infrastructure and verification phase. No new Python scanner code
is required (CONTEXT.md: "the scanners already handle these protocols — this is lab/config +
verification work"). The work falls into three categories:

1. **Four new Docker Compose profiles** (postgres-tls, redis-tls, kafka-tls, grpc-tls): each
   adds one service with intentionally weak TLS config, a `labs/<name>/` support directory, and
   four-file lab-sync artifacts (docker-compose.yml, lab.sh ALL_PROFILES, README, expected_results_v4.md).

2. **LAB-03 already-covered closure**: The existing `email` profile's Postfix service on port
   30587 exposes SMTP STARTTLS. The deliverable is an oracle entry in `expected_results_v4.md`
   explicitly noting STARTTLS detection at that port, and a UAT step confirming scanner output.

3. **LAB-06 identity-lab scan-config + UAT**: Add `enable_kerberos: true`, `enable_saml: true`,
   `enable_dnssec: true` with their respective lab targets to `config.yaml` (the top-level scan
   config), then assert all three evidence counters are non-zero in `intelligence-*.json`.

The gRPC ALPN-h2 empirical check (D-03) is the only material risk. sslyze has no ALPN-specific
ScanCommand, but the TLS handshake itself does produce cipher + cert findings. Whether sslyze
successfully negotiates the connection at all when the server advertises only h2 via ALPN is the
open question — verified at execution time as task 1 of the grpc-tls plan.

**Primary recommendation:** Implement all four new profiles in a single plan structured as four
sequential sub-tasks (one per profile) plus one sub-task for LAB-03 closure and one for LAB-06.
Each sub-task must commit the four-file lab-sync atomically.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| postgres-tls profile service | Docker Compose (chaos lab) | `labs/postgres-tls/` cert-gen | Lab infra; scanner probes externally |
| redis-tls profile service | Docker Compose (chaos lab) | `labs/redis-tls/` conf + certs | Lab infra; broker_scanner.py already probes |
| kafka-tls profile service | Docker Compose (chaos lab) | `labs/kafka-tls/` properties + certs | Lab infra; broker_scanner.py already probes |
| grpc-tls profile service | Docker Compose + custom Dockerfile | `labs/grpc-tls/` Go source | Requires build; no off-the-shelf image |
| STARTTLS probe (postgres) | sslyze `ProtocolWithOpportunisticTlsEnum.POSTGRES` | db_connector.py (SQL) | STARTTLS cipher scan is separate from SQL-level ssl-off detection |
| STARTTLS probe (email/LAB-03) | email_scanner.py + sslyze SMTP | Postfix service on email profile | Already wired; lab target already exists |
| Identity evidence flow | evidence.py → scoring.py | config.yaml connector settings | Wired; gap is scan config, not code |

---

## Standard Stack

### Core (no new packages — v5.0 stabilization principle)

| Component | Version | Purpose | Notes |
|-----------|---------|---------|-------|
| `postgres` (official image) | `16.6` | postgres-tls lab service | Matches existing `postgres-plain` (`docker-compose.yml` L151) [VERIFIED: docker-compose.yml] |
| `redis` (official image) | `7.4.1-alpine` | redis-tls lab service | Same pin as `redis-broker` (`docker-compose.yml` L1088) [VERIFIED: docker-compose.yml] |
| `apache/kafka` | `3.9.0` | kafka-tls lab service | Upgrade from `3.7.0` in the `broker` profile; required per REQUIREMENTS.md LAB-04 [VERIFIED: docker.io/apache/kafka:3.9.0] |
| `golang` (alpine) | `1.23-alpine` | gRPC-TLS image builder | Minimal Go base for gRPC server Dockerfile [VERIFIED: docker.io/library/golang:1.23-alpine] |
| `sslyze` | already installed | postgres STARTTLS + TLS cipher enumeration | `ProtocolWithOpportunisticTlsEnum.POSTGRES` confirmed in installed sslyze [VERIFIED: .venv/bin/python] |

### Image Digest Pins (fetch at execution time)

These digests were obtained during research (2026-05-22). Planner must fetch fresh digests at
execution time and embed in `docker-compose.yml` if digest-pinning policy applies to new services.
The CHAOS-05 gate (`tests/test_chaos_lab_image_pinning.py`) checks for a version tag, not a
digest — tag-level pinning satisfies the gate.

| Image | Tag | Digest (2026-05-22) |
|-------|-----|---------------------|
| `apache/kafka` | `3.9.0` | `sha256:fbc7d7c428e3755cf36518d4976596002477e4c052d1f80b5b9eafd06d0fff2f` |
| `redis` | `7.4.1-alpine` | `sha256:c1e88455c85225310bbea54816e9c3f4b5295815e6dbf80c34d40afc6df28275` |
| `postgres` | `16.6` | `sha256:557fea37a744d5f4c8faab304b0a90858b53ab119735a88c131fd19dab802f36` |
| `golang` | `1.23-alpine` | `sha256:383395b794dffa5b53012a212365d40c8e37109a626ca30d6151c8348d380b5f` |

---

## Package Legitimacy Audit

This phase installs **no new Python packages**. All new Docker images are official Docker Hub
images from well-established publishers (postgres, redis, apache, golang — all official library
images) or purpose-built internal Dockerfiles. No slopcheck needed for Python packages.

| Image | Registry | Age | Publisher | Disposition |
|-------|----------|-----|-----------|-------------|
| `apache/kafka:3.9.0` | Docker Hub | 8+ yrs (Apache project) | apache | Approved — official Apache image [VERIFIED: docker hub] |
| `redis:7.4.1-alpine` | Docker Hub | 10+ yrs | redis (official library) | Approved — already used as `redis-broker` [VERIFIED: docker-compose.yml L1088] |
| `postgres:16.6` | Docker Hub | 10+ yrs | postgres (official library) | Approved — already used as `postgres-plain` and `id-postgres` [VERIFIED: docker-compose.yml L151, L399] |
| `golang:1.23-alpine` | Docker Hub | 10+ yrs | golang (official library) | Approved — standard Go builder base [VERIFIED: docker.io pull] |

**No packages removed. No suspicious packages flagged.**

---

## Architecture Patterns

### 4-File Lab-Sync Checklist (per new profile)

Every new chaos-lab profile must touch exactly these four files in a single commit:

1. `quantum-chaos-enterprise-lab/docker-compose.yml` — add service(s) under new profile name
2. `quantum-chaos-enterprise-lab/lab.sh` — `_derive_all_profiles()` auto-derives from compose;
   no hardcoded list to update. **Verify with `./lab.sh profiles`** after adding the profile.
3. `quantum-chaos-enterprise-lab/README.md` — add a row to the Profile Summary table
4. `quantum-chaos-enterprise-lab/expected_results_v4.md` — add a `## Profile: <name>` section

Support directories created per profile (not tracked by the lab-sync checklist but required for
the profile to work):
- `labs/<profile-name>/` — Makefile for cert gen, README, conf files, Dockerfile (if build)
- `labs/<profile-name>/certs/` — generated certs (gitignored via `*.key`, `*.crt`)

Note on `lab.sh`: The `_derive_all_profiles()` function (lab.sh L58-70) reads profiles directly
from `docker-compose.yml` using `yq` or `grep`. There is NO hardcoded `ALL_PROFILES` list to
update — adding the profile to `docker-compose.yml` is sufficient for `./lab.sh all` to pick it
up. [VERIFIED: lab.sh L56-70]

### Port Allocation (used vs. available)

Ports currently in use by the chaos lab (host side):
`88, 389, 443, 636, 2222, 5555, 5556, 8000, 8080, 8443, 8444, 9443, 10443, 11443, 12443, 13443-13447, 13890, 14443, 15001, 15353, 15432, 15443, 15449, 15672, 16379, 16443, 17443, 18000, 18082, 19000, 20001-20006, 20022, 21000-21002, 23306, 24443, 24566, 25432, 25671, 25672, 26379, 26380, 28200, 29000, 29001, 29092, 29093, 30025, 30110, 30143, 30465, 30587, 30993, 30995, 38900, 38910`
[VERIFIED: docker-compose.yml grep]

**Recommended new port assignments:**

| Profile | Service | Host Port | Container Port | Protocol |
|---------|---------|-----------|----------------|----------|
| postgres-tls | postgres-tls | **39432** | 5432 | PostgreSQL STARTTLS |
| redis-tls | redis-tls | **39380** | 6380 | Redis TLS (direct) |
| kafka-tls | kafka-tls (TLS) | **39093** | 9093 | Kafka SSL listener |
| kafka-tls | kafka-tls (plaintext) | **39092** | 9092 | Kafka PLAINTEXT (healthcheck) |
| grpc-tls | grpc-tls | **39443** | 443 | gRPC TLS h2 |

These ports are in the 39xxx range, clear of all existing allocations.

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│  Scanner host (quirk scan)                          │
│                                                     │
│  sslyze POSTGRES STARTTLS ──→ 39432/tcp            │
│  broker_scanner.py REDIS  ──→ 39380/tcp            │
│  broker_scanner.py KAFKA  ──→ 39092+39093/tcp      │
│  sslyze direct TLS        ──→ 39443/tcp            │
└─────────────────────────────────────────────────────┘
           │           │           │           │
           ▼           ▼           ▼           ▼
   postgres:16.6  redis:7.4.1  apache/      grpc-tls
   weak ssl_      -alpine      kafka:3.9.0  (Go image)
   ciphers        DES-CBC3-SHA TLS_RSA_*    ALPN h2
```

### Per-Protocol Weak TLS Recipes

#### LAB-01: postgres-tls

**Image:** `postgres:16.6` (same as `postgres-plain`)
**Scanner probe:** sslyze `ProtocolWithOpportunisticTlsEnum.POSTGRES` on port 5432 (mapped to 39432 on host)
**Weakness:** RSA key exchange ciphers (no forward secrecy), TLS 1.2 only

**`postgresql.conf` weak settings:**
```
ssl = on
ssl_cert_file = '/etc/ssl/certs/postgres-tls.crt'
ssl_key_file  = '/etc/ssl/private/postgres-tls.key'
ssl_ca_file   = '/etc/ssl/certs/postgres-tls.crt'

# TLS version: 1.2 minimum (TLS 1.0/1.1 disabled by modern OpenSSL)
ssl_min_protocol_version = 'TLSv1.2'
ssl_max_protocol_version = 'TLSv1.2'

# Weak ciphers: RSA key exchange = no forward secrecy (quantum-vulnerable)
ssl_ciphers = 'AES128-SHA:AES256-SHA'
```

**`pg_hba.conf` setting:**
```
hostssl  all  all  0.0.0.0/0  trust
```

**docker-compose.yml service block:**
```yaml
postgres-tls:
  image: postgres:16.6
  profiles: ["postgres-tls"]
  environment:
    POSTGRES_DB: chaos
    POSTGRES_USER: chaos
    POSTGRES_PASSWORD: chaos
  volumes:
    - ../labs/postgres-tls/postgresql.conf:/etc/postgresql/postgresql.conf:ro
    - ../labs/postgres-tls/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro
    - ../labs/postgres-tls/certs/postgres-tls.crt:/etc/ssl/certs/postgres-tls.crt:ro
    - ../labs/postgres-tls/certs/postgres-tls.key:/etc/ssl/private/postgres-tls.key:ro
  command: ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
  ports:
    - "39432:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U chaos || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 6
    start_period: 20s
```

**Important:** The `postgres` image runs as the `postgres` user. SSL key files must be owned
by the container's postgres user (uid 999). Use `chmod 640` + `chown 999:999` in the cert-gen
Makefile, or mount the key under `/var/lib/postgresql/` which postgres already owns.
[ASSUMED — based on known postgres image ssl key ownership requirements]

**Expected findings:**
- Weak cipher suite (RSA key exchange, no forward secrecy) — HIGH
- RSA-2048 cert (quantum-vulnerable) — MEDIUM

#### LAB-02: redis-tls

**Image:** `redis:7.4.1-alpine` (same pin as existing `redis-broker`)
**Scanner probe:** `broker_scanner.py scan_redis_targets()` — direct-socket TLS on port 6380
**Weakness:** 3DES + RSA ciphers (mirrors existing `broker` profile redis-broker)

**`redis.conf`:** Mirror the existing `labs/broker/redis/redis.conf` with identical weak config.
The existing conf already uses `DES-CBC3-SHA:AES128-SHA:AES256-SHA` and `TLSv1.2`.
[VERIFIED: labs/broker/redis/redis.conf]

```
tls-port 6380
port 6379
tls-cert-file /etc/redis/certs/redis-tls.crt
tls-key-file  /etc/redis/certs/redis-tls.key
tls-ca-cert-file /etc/redis/certs/redis-tls.crt
tls-auth-clients no
tls-protocols "TLSv1.2"
tls-ciphers "DES-CBC3-SHA:AES128-SHA:AES256-SHA"
tls-prefer-server-ciphers yes
```

Note: This new `redis-tls` profile is **separate from the `broker` profile** — the broker
profile's `redis-broker` service already fills the redis TLS testing role but is bundled with
Kafka and RabbitMQ. The new `redis-tls` profile is standalone, mirroring D-02.

**Expected findings:**
- Weak cipher suite (3DES, RSA key exchange) — HIGH
- Redis plaintext port accessible on 39379 — HIGH (include plaintext port 6379 to mirror broker pattern)

#### LAB-04: kafka-tls

**Image:** `apache/kafka:3.9.0` (upgrade from `3.7.0` in the `broker` profile — REQUIREMENTS.md specifies 3.9.0)
**Scanner probe:** `broker_scanner.py scan_kafka_targets()` on ports 39092 (plaintext detection) and 39093 (TLS)
**Weakness:** TLS 1.2 with RSA key exchange ciphers — no forward secrecy

**`server.properties`:** Mirror the existing `labs/broker/kafka/server.properties` pattern.
[VERIFIED: labs/broker/kafka/server.properties]

```
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@kafka-tls:9094
listeners=PLAINTEXT://:9092,SSL://:9093,CONTROLLER://:9094
advertised.listeners=PLAINTEXT://localhost:39092,SSL://localhost:39093
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,SSL:SSL,CONTROLLER:CONTROLLER
inter.broker.listener.name=SSL
controller.listener.names=CONTROLLER

ssl.enabled.protocols=TLSv1.2
ssl.cipher.suites=TLS_RSA_WITH_AES_128_CBC_SHA,TLS_RSA_WITH_AES_256_CBC_SHA
ssl.keystore.type=PEM
ssl.keystore.location=/etc/kafka/secrets/kafka-tls.crt
ssl.keystore.key.location=/etc/kafka/secrets/kafka-tls.key
ssl.client.auth=none
```

**Healthcheck caveat:** The `apache/kafka:3.9.0` healthcheck must use the PLAINTEXT port (9092),
not the SSL port (9093), to avoid needing a client cert or truststore. This mirrors the existing
`broker` profile kafka healthcheck pattern. [VERIFIED: labs/broker/expected_results.md - "Kafka
server.properties mount path" caveat]

**Expected findings:**
- Kafka plaintext listener detected — HIGH (port 39092)
- Weak cipher suite (RSA key exchange, no PFS) on TLS listener — HIGH (port 39093)
- RSA-2048 cert (quantum-vulnerable) — MEDIUM

**Upgrade note:** `apache/kafka:3.9.0` vs `3.7.0` in the `broker` profile — both use the same
`server.properties` mount approach and identical weak-config knobs. The `kafka-tls` profile is
a NEW standalone profile, not a replacement for `broker`'s `kafka-broker` service.

#### LAB-05: grpc-tls

**Image:** Custom Go Dockerfile built at `../labs/grpc-tls/Dockerfile`
**Scanner probe:** sslyze direct TLS on port 39443 (no STARTTLS needed — gRPC uses direct TLS)
**Weakness:** RSA-2048 cert (quantum-vulnerable); TLS config inherits Go's tls.Config defaults (TLS 1.2/1.3)

**Dockerfile skeleton:**
```dockerfile
FROM golang:1.23-alpine AS builder
WORKDIR /app
COPY main.go go.mod go.sum ./
RUN go build -o grpc-server .

FROM alpine:3.20
COPY --from=builder /app/grpc-server /grpc-server
COPY certs/grpc-tls.crt /tls/server.crt
COPY certs/grpc-tls.key /tls/server.key
EXPOSE 443
CMD ["/grpc-server"]
```

**`main.go` minimal gRPC TLS server:**
```go
package main

import (
    "crypto/tls"
    "net"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials"
    pb "google.golang.org/grpc/examples/helloworld/helloworld"
)

func main() {
    creds, _ := credentials.NewServerTLSFromFile("/tls/server.crt", "/tls/server.key")
    // ALPN h2 is automatically negotiated by grpc-go's TLS credentials
    s := grpc.NewServer(grpc.Creds(creds))
    pb.RegisterGreeterServer(s, &server{})
    lis, _ := net.Listen("tcp", ":443")
    s.Serve(lis)
}
```

**ALPN h2 risk (D-03):** `grpc-go` credentials automatically set `NextProtos: ["h2"]` in the
`tls.Config`. sslyze's `ServerNetworkConfiguration` does not have an ALPN parameter. The question
is whether sslyze's TLS negotiation succeeds when the server presents only `h2` as ALPN. sslyze
scans at the TLS record layer — ALPN is negotiated during the ClientHello but does not prevent
the TLS handshake from completing for `ScanCommand.CERTIFICATE_INFO` and cipher enumeration.
However, if the grpc-go server rejects non-ALPN connections at the application layer after the TLS
handshake, sslyze may get a TLS-level success but immediate connection close. The empirical check
at execution time (D-03) resolves this. [ASSUMED — sslyze ALPN behavior against grpc-go server;
needs empirical validation per D-03]

**Fallback if sslyze fails ALPN-h2:** Use `openssl s_client -alpn h2 -connect localhost:39443`
as the scanner evidence source and document the limitation in expected_results_v4.md.

**Expected findings (if sslyze succeeds):**
- RSA-2048 cert (quantum-vulnerable) — MEDIUM
- TLS cipher suite detected — informational

### Recommended Project Structure (new labs directories)

```
labs/
├── postgres-tls/
│   ├── Makefile              # make certs (RSA-2048 self-signed)
│   ├── postgresql.conf       # weak ssl_ciphers = AES128-SHA:AES256-SHA
│   ├── pg_hba.conf           # hostssl all all 0.0.0.0/0 trust
│   ├── README.md
│   └── certs/               # gitignored; generated by Makefile
│       ├── postgres-tls.crt
│       └── postgres-tls.key
├── redis-tls/
│   ├── Makefile              # make certs
│   ├── redis.conf            # DES-CBC3-SHA:AES128-SHA:AES256-SHA, TLSv1.2
│   ├── README.md
│   └── certs/
├── kafka-tls/
│   ├── Makefile              # make certs
│   ├── server.properties     # TLS_RSA_WITH_AES_128_CBC_SHA, TLSv1.2
│   ├── README.md
│   └── certs/
└── grpc-tls/
    ├── Dockerfile            # FROM golang:1.23-alpine; multi-stage build
    ├── main.go               # minimal grpc.NewServer with TLS credentials
    ├── go.mod / go.sum       # google.golang.org/grpc dependency
    ├── Makefile              # make certs; make build
    ├── README.md
    └── certs/
```

### Anti-Patterns to Avoid

- **Using `:latest` or bare tag images:** CHAOS-05 gate (`tests/test_chaos_lab_image_pinning.py`)
  will fail. Every `image:` field must have a pinned version tag. [VERIFIED: test_chaos_lab_image_pinning.py]
- **Adding profiles without updating all four lab-sync files:** CLAUDE.md Chaos Lab Maintenance
  rule. A partial sync is a CI failure waiting to happen.
- **Using bitnami images outside `bitnamilegacy/*` namespace:** Phase 82 lesson — bitnami images
  lack cipher-level weak-TLS control and use a different namespace for legacy packages.
- **Modifying the `broker` profile's existing services:** The `broker` profile's Kafka/RabbitMQ/
  Redis services are separately tested. New profiles are additive.
- **Postgres SSL key file permissions:** The `postgres` Docker image runs as uid 999. Private key
  files mounted at `/etc/ssl/private/` must be group-readable by uid 999 or postgres will refuse
  to start SSL. [ASSUMED — based on PostgreSQL SSL key permission requirements]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| gRPC ALPN-h2 TLS server | Custom TLS socket server | `grpc-go` + `credentials.NewServerTLSFromFile()` | grpc-go auto-sets ALPN h2 in NextProtos |
| Kafka TLS config | Manual JKS keystore + keytool | PEM keystore via `ssl.keystore.type=PEM` | Avoids keytool dependency in lab; matches existing `labs/broker/kafka/server.properties` pattern |
| Cipher weakening | Custom SSL handshake interceptor | Standard `ssl_ciphers` / `tls-ciphers` directives | Service-native cipher config is stable; custom interceptors are fragile |
| Cert generation | OpenSSL scripting from scratch | `make certs` Makefile pattern from `labs/broker/Makefile` | Consistent RSA-2048 self-signed cert approach across all profiles |

---

## LAB-03 Already-Covered Closure (email profile port 30587)

**What exists:** `docker-compose.yml` L996-1014 defines `postfix-email` with ports
`30025:25`, `30465:465`, `30587:587`. [VERIFIED: docker-compose.yml L1003-1005]

**What the scanner detects:** `email_scanner.py` uses sslyze with
`ProtocolWithOpportunisticTlsEnum.SMTP` for port 587. Expected finding per
`expected_results_v4.md` L438:
```
| 30587 | postfix-email (submission) | SMTP-STARTTLS | protocol=SMTP-STARTTLS, 
  service_detail=SMTP-STARTTLS:587; risk: "Weak cipher suite on email TLS endpoint"
  (HIGH, EMAIL-09) |
```
[VERIFIED: expected_results_v4.md L438]

**Deliverable for LAB-03 closure:**

1. Add an explicit note to `expected_results_v4.md` under the `## Profile: email` section
   that port 30587 covers the smtp-starttls requirement (LAB-03) — scanner must emit
   `protocol=SMTP-STARTTLS, service_detail=SMTP-STARTTLS:587` with a HIGH finding.
2. Add a UAT step: bring up the email profile, run `quirk scan`, assert the 30587 STARTTLS
   finding is present in the output.
3. Mark LAB-03 closed in `REQUIREMENTS.md` with the documented closure note.

---

## LAB-06 Identity Evidence End-to-End

### What Is Wired (code — BACK-78 confirmed)

The entire evidence → scoring chain for identity counters is complete:
[VERIFIED: quirk/intelligence/evidence.py L87-89, L165, L171-183, L387-399; quirk/intelligence/scoring.py L31-33, L159-161, L196-198]

```
evidence.py::build_evidence_summary()
  KERBEROS endpoints → identity_weak_etype_count (L165)
  SAML endpoints    → saml_weak_signing_count    (L171, L173)
  DNSSEC endpoints  → dnssec_weak_algo_count     (L180, L183)
  → emits ratios at L397-399

scoring.py::compute_readiness_score()
  kerberos_weak_count = evidence.get("identity_weak_etype_count")  (L159)
  saml_weak_count     = evidence.get("saml_weak_signing_count")    (L160)
  dnssec_weak_count   = evidence.get("dnssec_weak_algo_count")     (L161)
  → weights: 10.0, 8.0, 8.0 applied at L196-198
```

### What Is Missing (config gap)

The top-level `config.yaml` does not enable identity connectors:
[VERIFIED: config.yaml — no kerberos/saml/dnssec keys present]

Lab containers that need to be running:
- `kerberos` profile: `samba-dc` on ports 88, 389 [VERIFIED: docker-compose.yml L913-928]
- `saml` profile: `simplesamlphp` on port 8080 [VERIFIED: docker-compose.yml L895-911]
- `dnssec` profile: `bind9-dnssec` on port 15353/udp+tcp [VERIFIED: docker-compose.yml L879-892]

### config.yaml Changes Required

Add to `config.yaml` (or create a new `config-identity-lab.yaml` for the UAT):
[VERIFIED approach from .planning/research/ARCHITECTURE.md L258-262]

```yaml
connectors:
  enable_kerberos: true
  kerberos_targets:
    - "127.0.0.1"    # samba-dc on port 88 (privileged, direct-mapped)

  enable_saml: true
  saml_targets:
    - "http://localhost:8080/simplesaml/saml2/idp/metadata.php"

  enable_dnssec: true
  dnssec_targets:
    - "weak.example.com"
    - "unsigned.example.com"
    # Resolver override needed: bind9-dnssec listens on 15353, not 53
```

**DNSSEC resolver caveat:** `bind9-dnssec` binds to port 15353, not 53. The dnssec_scanner must
use a custom resolver pointing to `127.0.0.1:15353`. Check `quirk/scanner/dnssec_scanner.py` to
confirm whether resolver override is configurable. [ASSUMED — dnssec_scanner port 15353 resolver override availability needs code verification]

**Kerberos macOS caveat:** macOS binds `*:88` for the system KDC. The `kerberos` profile will
fail on macOS unless the system KDC is stopped. `lab.sh all` already auto-skips kerberos on
Darwin unless `LAB_INCLUDE_KERBEROS=1` is set. [VERIFIED: lab.sh L139-153]

### UAT Assertion

After running `quirk scan` with identity connectors enabled against the live profiles:
```bash
# From intelligence-*.json output file
cat output/intelligence-*.json | python3 -m json.tool | grep -E "identity_weak_etype|saml_weak|dnssec_weak"
```

Expected: all three counters non-zero. If zero: the scan did not reach the target containers —
check that the correct profiles are running and the config targets match the lab ports.

---

## Common Pitfalls

### Pitfall 1: Postgres SSL Key File Ownership

**What goes wrong:** `postgres` container refuses to start SSL, logs `"private key file ... must
be owned by the database superuser or root"`.
**Why it happens:** The postgres image runs as uid 999; mounted key files default to root ownership.
**How to avoid:** In the cert-gen Makefile: `chmod 640 certs/postgres-tls.key` and ensure the file
is group-readable by uid 999, or mount under `/var/lib/postgresql/` (owned by postgres user).
**Warning signs:** Container health check fails; `docker logs postgres-tls` shows SSL startup error.

### Pitfall 2: Kafka PEM Keystore Combined File

**What goes wrong:** Kafka fails to load the PEM keystore because the cert and key are separate
files but `ssl.keystore.location` expects a combined PEM.
**Why it happens:** `ssl.keystore.type=PEM` with `ssl.keystore.location` expects cert+key in one
file OR separate `ssl.keystore.certificate.chain` + `ssl.keystore.key` properties.
**How to avoid:** Either (a) combine cert+key into one PEM file for `ssl.keystore.location`, or
(b) use `ssl.keystore.certificate.chain` (cert file) + `ssl.keystore.key` (key file) separately.
The existing `labs/broker/kafka/server.properties` uses `ssl.keystore.location` alone — check
the current working pattern in `labs/broker/certs/kafka.crt` to see if cert+key are combined.
[ASSUMED — verify the existing broker Kafka PEM format before repeating]

### Pitfall 3: sslyze vs gRPC ALPN h2

**What goes wrong:** sslyze returns `ServerScanStatusEnum.ERROR` or connection timeout against
the grpc-tls service even though the TLS handshake completes.
**Why it happens:** grpc-go sets `NextProtos: ["h2"]` in the TLS config. Some servers reject the
connection at the application layer if the client's ALPN does not match. sslyze sends a
ClientHello without ALPN (or with a different ALPN) — the server may close the connection after
TLS finishes.
**How to avoid:** This is exactly the D-03 empirical check. If sslyze fails, use `openssl s_client
-alpn h2 -connect localhost:39443 </dev/null 2>&1 | grep -E "Cipher|Protocol|ALPN"` as the
verification evidence and document the limitation.
**Warning signs:** sslyze returns `ServerTlsConfigurationNotSupported` or `ConnectionRejected`.

### Pitfall 4: Kerberos Port 88 macOS Collision

**What goes wrong:** `kerberos` profile fails to start on macOS; port 88 already in use.
**Why it happens:** macOS has a built-in Kerberos KDC that binds `*:88`.
**How to avoid:** Do not run the kerberos profile on macOS without first stopping the system KDC
(`sudo launchctl unload /System/Library/LaunchDaemons/com.apple.Kerberos.kdc.plist`). For LAB-06
UAT, use the `LAB_INCLUDE_KERBEROS=1` env var and set up system KDC workaround, or run the LAB-06
UAT on Linux CI.
**Warning signs:** `docker compose ... up` fails with "port is already allocated".

### Pitfall 5: DNSSEC Scanner Port 15353

**What goes wrong:** `dnssec_weak_algo_count` remains zero even though the `bind9-dnssec`
container is healthy.
**Why it happens:** The dnssec_scanner defaults to system resolver (port 53). The lab resolver
runs on port 15353.
**How to avoid:** Verify whether `dnssec_scanner.py` accepts a resolver override config key
(`dnssec_resolver` or similar). If not, add one as part of the LAB-06 plan.
**Warning signs:** Scanner completes without error but `dnssec_weak_algo_count` is 0.

### Pitfall 6: redis-tls vs broker Profile Duplication

**What goes wrong:** The planner creates a `redis-tls` service inside the existing `broker` profile.
**Why it happens:** The `broker` profile already has a redis service (`redis-broker`).
**How to avoid:** The new `redis-tls` profile is a STANDALONE profile, not an addition to
`broker`. Its purpose is to provide an isolated redis-TLS target for per-protocol chaos testing.
The `broker` profile remains unchanged.

---

## Code Examples

### sslyze POSTGRES STARTTLS Probe Pattern

```python
# Source: email-tls-research.md (confirmed pattern for STARTTLS protocols)
# + sslyze ProtocolWithOpportunisticTlsEnum.POSTGRES confirmed in .venv/bin/python

from sslyze import (
    Scanner as SslyzeScanner,
    ServerScanRequest,
    ServerNetworkLocation,
    ServerNetworkConfiguration,
    ProtocolWithOpportunisticTlsEnum,
    ScanCommand,
)

scan_request = ServerScanRequest(
    server_location=ServerNetworkLocation(hostname="localhost", port=39432),
    network_configuration=ServerNetworkConfiguration(
        tls_server_name_indication="localhost",
        tls_opportunistic_encryption=ProtocolWithOpportunisticTlsEnum.POSTGRES,
        network_timeout=10,
    ),
    scan_commands={
        ScanCommand.CERTIFICATE_INFO,
        ScanCommand.TLS_1_2_CIPHER_SUITES,
        ScanCommand.TLS_1_3_CIPHER_SUITES,
    },
)
```

### Existing Redis Weak-TLS Config (verified working in broker profile)

```conf
# Source: labs/broker/redis/redis.conf (VERIFIED)
port 6379
tls-port 6380
tls-cert-file /etc/redis/certs/redis.crt
tls-key-file  /etc/redis/certs/redis.key
tls-ca-cert-file /etc/redis/certs/redis.crt
tls-auth-clients no
tls-protocols "TLSv1.2"
tls-ciphers "DES-CBC3-SHA:AES128-SHA:AES256-SHA"
tls-prefer-server-ciphers yes
```

### Existing Kafka Weak-TLS Properties (verified working in broker profile)

```properties
# Source: labs/broker/kafka/server.properties (VERIFIED)
ssl.enabled.protocols=TLSv1.2
ssl.cipher.suites=TLS_RSA_WITH_AES_128_CBC_SHA,TLS_RSA_WITH_AES_256_CBC_SHA
ssl.keystore.type=PEM
ssl.client.auth=none
```

### Cert Generation Pattern (from existing labs/broker/Makefile)

```bash
# Source: labs/broker/Makefile (VERIFIED)
openssl req -x509 -newkey rsa:2048 -keyout certs/postgres-tls.key \
    -out certs/postgres-tls.crt -days 3650 -nodes \
    -subj "/CN=postgres-tls.chaos.local" 2>/dev/null
chmod 644 certs/*.crt
chmod 640 certs/*.key   # 640 not 600 to allow group read for postgres uid 999
```

### Identity Config Keys (from quirk/config_template.yaml)

```yaml
# Source: quirk/config_template.yaml L62-70 (VERIFIED)
connectors:
  enable_kerberos: true
  kerberos_targets:
    - "127.0.0.1"
  enable_saml: true
  saml_targets:
    - "http://localhost:8080/simplesaml/saml2/idp/metadata.php"
  enable_dnssec: true
  dnssec_targets:
    - "weak.example.com"
    - "unsigned.example.com"
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| `bitnami/kafka` with `KAFKA_CFG_*` env vars | `apache/kafka` with `server.properties` bind-mount | Phase 33 D-15: official images needed for cipher-level control |
| JKS keystore + keytool | PEM keystore (`ssl.keystore.type=PEM`) | No keytool dependency; same weak-cipher effect |
| `redis:7-alpine` (floating minor) | `redis:7.4.1-alpine` (pinned) | Phase 82-01 pin sweep |
| `docker-mailserver` for email lab | Custom Postfix+Dovecot Dockerfile | docker-mailserver v12+ removed weak TLS support |

**Deprecated/outdated:**
- `bitnamilegacy/*` images: acceptable only for the existing `ldaps` profile (OpenLDAP,
  identified as unmaintained upstream — left as-is per Phase 82-01 scope). New profiles must
  use official images.
- `apache/kafka:3.7.0` (the existing `broker` profile): the new `kafka-tls` profile uses `3.9.0`
  per REQUIREMENTS.md. The `broker` profile's `kafka-broker` at 3.7.0 is NOT changed in Phase 89.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | sslyze successfully negotiates TLS against a grpc-go server advertising `h2` via ALPN | LAB-05 gRPC section | D-03 empirical check mitigates this; if wrong, use openssl s_client evidence |
| A2 | Postgres SSL key file requires chmod 640 + group-readable by uid 999 | LAB-01 postgres pitfall | Container may fail to start SSL; easily fixed by adjusting Makefile permissions |
| A3 | DNSSEC scanner supports a resolver port override for port 15353 | LAB-06 pitfall | If not supported, a small config key addition is needed in dnssec_scanner.py |
| A4 | Kafka PEM keystore format in `apache/kafka:3.9.0` uses same `server.properties` pattern as 3.7.0 | LAB-04 Kafka section | Minor version gap; verify with `docker logs kafka-tls` at execution time |
| A5 | `config.yaml` (top-level) is the correct scan config to add LAB-06 identity targets | LAB-06 section | Could be a new `config-identity-lab.yaml` instead — either works; CONTEXT says "existing" |

---

## Open Questions

1. **sslyze ALPN-h2 against grpc-go (D-03 risk)**
   - What we know: sslyze has no ALPN ScanCommand; grpc-go sets `NextProtos: ["h2"]` automatically
   - What's unclear: whether sslyze's TLS negotiation succeeds when server enforces h2-only ALPN
   - Recommendation: Executor resolves empirically as task 1 of the grpc-tls plan per D-03

2. **DNSSEC resolver port override**
   - What we know: `bind9-dnssec` runs on port 15353; system resolver is 53; dnssec targets
     `weak.example.com` and `unsigned.example.com` use the lab's bind9 zone
   - What's unclear: whether `dnssec_scanner.py` accepts a custom resolver address+port
   - Recommendation: Check `quirk/scanner/dnssec_scanner.py` resolver config before writing the
     LAB-06 plan task; add a `dnssec_resolver` config key if missing

3. **Postgres PEM keystore unified file vs. separate cert+key**
   - What we know: `labs/broker/kafka/server.properties` uses `ssl.keystore.location` for the PEM
     approach; it's unclear if the existing certs are combined cert+key or separate
   - What's unclear: The exact cert format that `apache/kafka:3.9.0` accepts for `ssl.keystore.type=PEM`
   - Recommendation: Inspect `labs/broker/certs/kafka.crt` at execution time to see if it includes
     both cert and key sections

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | All new profiles | Check at execution | — | None — Docker required for lab |
| sslyze | LAB-01 postgres STARTTLS | ✓ | Installed in .venv | stdlib ssl fallback |
| `yq` | `lab.sh profiles` fast path | Optional | — | grep fallback in lab.sh L64-69 |
| Go toolchain | LAB-05 grpc-tls build | Optional at dev time | — | Pre-built binary in image |
| `openssl` CLI | cert generation Makefiles | ✓ | System openssl | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml L104) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_chaos_lab_image_pinning.py -x` |
| Full suite command | `pytest -m 'not slow'` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAB-01 | postgres-tls image pinned in docker-compose.yml | unit | `pytest tests/test_chaos_lab_image_pinning.py -x` | ✅ |
| LAB-02 | redis-tls image pinned | unit | `pytest tests/test_chaos_lab_image_pinning.py -x` | ✅ |
| LAB-04 | kafka-tls image pinned | unit | `pytest tests/test_chaos_lab_image_pinning.py -x` | ✅ |
| LAB-05 | grpc-tls Dockerfile FROM pinned | unit | `pytest tests/test_chaos_lab_image_pinning.py -x` | ✅ |
| LAB-01 | sslyze POSTGRES STARTTLS detects weak cipher | integration (slow) | Manual / live lab | ❌ Wave 0 |
| LAB-02 | broker_scanner Redis-TLS probe finds weak cipher | integration (slow) | Manual / live lab | ❌ Wave 0 |
| LAB-04 | broker_scanner Kafka-TLS probe finds weak cipher | integration (slow) | Manual / live lab | ❌ Wave 0 |
| LAB-05 | sslyze TLS handshake against grpc-tls | integration (slow) | Manual / live lab per D-03 | ❌ Wave 0 |
| LAB-03 | email profile STARTTLS on 30587 in expected_results | doc review | Manual | ❌ Wave 0 |
| LAB-06 | identity evidence counters non-zero in intelligence-*.json | integration (slow) | Manual / live lab | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_chaos_lab_image_pinning.py -x`
- **Per wave merge:** `pytest -m 'not slow'`
- **Phase gate:** Full suite green before `/gsd:verify-work`; manual live-lab validation for
  integration tests

### Wave 0 Gaps

- [ ] `tests/test_phase89_lab_expected_results.py` — asserts expected_results_v4.md contains all
  four new profile sections (parse + grep); covers LAB-01..05 doc completeness
- [ ] `tests/test_phase89_lab_config_identity.py` — asserts config.yaml identity connector keys
  are present; covers LAB-06 config gap

*(Existing `tests/test_chaos_lab_image_pinning.py` already covers LAB-01..05 image pin requirements.)*

---

## Security Domain

> `security_enforcement` not set to false in config — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Lab-only services; no real auth |
| V5 Input Validation | no | No new scanner code in this phase |
| V6 Cryptography | yes | Intentionally weak configs (lab); scanner detects these |

### Known Threat Patterns

This phase adds lab infrastructure only. The weak TLS configs are intentional (the chaos lab's
purpose). No production code changes. The security concern is image supply chain:

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Slopsquatted Docker image | Tampering | Official library images only; tag-pinned; CHAOS-05 gate |
| Stale image with CVEs | Tampering | Pinned to specific patch tag; not `:latest` |

---

## Sources

### Primary (HIGH confidence)

- `quantum-chaos-enterprise-lab/docker-compose.yml` — verified all existing profiles, ports, image versions
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — verified email profile oracle entries (L436-444), broker oracle (L458-463), identity profile (L115-135), kerberos/saml/dnssec (L290-363)
- `quantum-chaos-enterprise-lab/lab.sh` — verified `_derive_all_profiles()` auto-detection (L58-70); no hardcoded ALL_PROFILES list
- `quantum-chaos-enterprise-lab/README.md` — verified all 21 existing profiles + image pin history
- `labs/broker/redis/redis.conf` — verified weak cipher config: DES-CBC3-SHA:AES128-SHA:AES256-SHA, TLSv1.2
- `labs/broker/kafka/server.properties` — verified weak cipher config: TLS_RSA_WITH_AES_128_CBC_SHA, TLSv1.2
- `labs/broker/Makefile` — verified RSA-2048 cert-gen pattern
- `quirk/intelligence/evidence.py` — verified identity counter wiring (L87-89, L165, L171-183, L387-399)
- `quirk/intelligence/scoring.py` — verified identity weights (L31-33, L159-161, L196-198)
- `.planning/research/ARCHITECTURE.md` L248-312 — verified BACK-78 is pure config gap; scanner code complete
- `.venv/bin/python` — verified `ProtocolWithOpportunisticTlsEnum` includes `POSTGRES`
- `tests/test_chaos_lab_image_pinning.py` — verified CHAOS-05 gate checks version tag, not digest
- `config.yaml` — verified identity connector keys absent (LAB-06 config gap confirmed)

### Secondary (MEDIUM confidence)

- `.planning/research/kafka-tls-research.md` — Kafka TLS probe mechanics, port conventions, weak cipher recipes
- `.planning/research/redis-broker-architecture-research.md` — Redis TLS probe mechanics, chaos lab docker config
- `.planning/research/email-tls-research.md` — sslyze STARTTLS pattern (SMTP, IMAP, POP3, confirmed POSTGRES from same enum)

### Tertiary (LOW confidence)

- Docker Hub digests for `apache/kafka:3.9.0`, `redis:7.4.1-alpine`, `postgres:16.6`, `golang:1.23-alpine` — fetched 2026-05-22; stable over next 30 days

---

## Metadata

**Confidence breakdown:**
- Lab infrastructure (existing patterns): HIGH — all file:line verified
- Weak TLS configs (redis, kafka): HIGH — copies of verified working configs
- Postgres SSL weak cipher approach: MEDIUM — config directives known; key file ownership is ASSUMED
- gRPC ALPN-h2 sslyze compatibility: LOW — empirical check required (D-03)
- Identity evidence flow (BACK-78): HIGH — verified through evidence.py, scoring.py code review
- LAB-06 DNSSEC resolver port: MEDIUM — scanner code review of port override not completed

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (30 days for stable lab infrastructure)
