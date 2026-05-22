# Stack Research — v5.0 Stabilization + Tech Debt Sweep (ADDITIONS ONLY)

**Domain:** Cryptographic inventory scanner — chaos lab expansion, dependency hygiene, CI hardening
**Researched:** 2026-05-22
**Confidence:** HIGH for lxml XXE API, Node 24 action versions, OQS-nginx, postgres-tls, redis-tls;
MEDIUM for Kafka TLS image selection (Bitnami legacy transition complicates); HIGH for gRPC lab,
SMTP/STARTTLS; LOW for identity lab new library needs (existing stack already covers them)

> This file covers ONLY stack changes for v5.0. The validated existing stack — sslyze, impacket,
> cyclonedx-python-lib, FastAPI, React + shadcn/ui, SQLite, dnspython, lxml>=6.0, defusedxml,
> nh3, beautifulsoup4, towncrier, Playwright, etc. — is documented in PROJECT.md Key Decisions
> and is NOT repeated here.

---

## 1. Dependency Hygiene (DEADLINE-DRIVEN — must land before Phase 87 closes)

### 1a. lxml Migration: Drop `defusedxml` from two call sites

**Current state (verified by code grep, 2026-05-22):**

- `quirk/scanner/saml_scanner.py` — primary path uses `lxml.etree` with
  `ET.XMLParser(resolve_entities=False, no_network=True)` already correctly in place (Phase 52
  DEBT-04). The `defusedxml` fallback triggers only when `lxml` is absent.
- `quirk/discovery/nmap_parser.py` — unconditionally `import defusedxml.ElementTree as ET`
  (installed per audit WR-06). This parses nmap XML output, which is locally generated but
  auditors flag it as an untrusted surface.
- `pyproject.toml` — `defusedxml>=0.7.1` is a core dep; `lxml>=6.0` is also a core dep.

**Migration target:** Remove the `defusedxml` core dep; replace both call sites with
`lxml.etree.XMLParser` using explicit XXE controls. `lxml` is already a mandatory core dep.

**The lxml XXE-hardening API surface (HIGH confidence — verified via lxml official docs and FAQ):**

```python
from lxml import etree

_SAFE_PARSER = etree.XMLParser(
    resolve_entities=False,   # PRIMARY: blocks XXE entity expansion (lxml 5.x+ default; explicit for defence-in-depth)
    no_network=True,          # Blocks external URI/network entity loading (SSRF mitigation)
    load_dtd=False,           # Do not load external DTDs at all
    dtd_validation=False,     # No DTD validation (prevents DTD-triggered network access)
    huge_tree=False,          # Keep security restrictions on tree size (default; explicit for audit trail)
)

def safe_fromstring(xml_bytes: bytes) -> etree._Element:
    return etree.fromstring(xml_bytes, parser=_SAFE_PARSER)

def safe_parse(xml_path: str) -> etree._ElementTree:
    return etree.parse(xml_path, parser=_SAFE_PARSER)
```

**Why these five flags together:**

| Flag | What it blocks | Why not just one |
|------|---------------|-----------------|
| `resolve_entities=False` | Entity expansion (classic XXE, billion-laughs) | The primary control; lxml 5.x default but must be explicit for audit reviewers |
| `no_network=True` | External URI lookups during parsing (SSRF via DTD/entity reference) | `resolve_entities=False` alone does not prevent network DNS lookups for referenced DTDs |
| `load_dtd=False` | DTD loading entirely (prevents parse-time fetch of DOCTYPE URI) | Overlaps with `no_network` but closes the local-filesystem DTD attack surface too |
| `dtd_validation=False` | On-the-fly DTD validation (which can trigger DTD fetch) | Without this, a SYSTEM DOCTYPE can still trigger fetch attempts |
| `huge_tree=False` | Deep/wide XML DoS attacks | Nmap output is bounded but defence-in-depth for external SAML metadata |

**lxml version:** `>=6.0` is already pinned in `pyproject.toml`. The current latest is **6.1.1**
(released 2026-05-18), which ships libxslt 1.1.43 on Linux (patched for libxslt CVE). Pin
`>=6.0` remains correct; upgrading to `>=6.1.1` for the libxslt fix is a separate consideration
but does not affect the XXE API surface — all five flags are stable since lxml 4.x.

**nmap_parser.py migration:** Replace `import defusedxml.ElementTree as ET` with:

```python
from lxml import etree as _lxml_etree

_NMAP_PARSER = _lxml_etree.XMLParser(
    resolve_entities=False, no_network=True,
    load_dtd=False, dtd_validation=False,
)

# In parse_nmap_xml():
tree = _lxml_etree.parse(xml_path, parser=_NMAP_PARSER)
root = tree.getroot()
```

`lxml._ElementTree` is a drop-in for `xml.etree.ElementTree` at the `findall` / `get` / `text`
API level used in nmap_parser.py — no caller changes required.

**saml_scanner.py migration:** The `lxml`-available path is already correct. Remove the
`defusedxml` fallback branch (lines 17–23). If `lxml` is unavailable, raise `ImportError`
immediately — do not silently downgrade to an unvetted stdlib parser that lacks these controls.
Rationale: `lxml>=6.0` is a mandatory core dep; its absence means a broken install, not a
graceful degrade.

**Removal from pyproject.toml:**

```toml
# Remove from [project.dependencies]:
# "defusedxml>=0.7.1",   <-- DELETE this line
```

`defusedxml` has not had a substantive release since 2021 (latest 0.7.1, 2021-03-08). Its
`defusedxml.lxml` submodule was never more than a thin re-export of lxml with the same
`resolve_entities=False` flag. QUIRK is better served by owning the explicit flag surface
directly in a `_SAFE_PARSER` module-level constant.

**What NOT to use from defusedxml going forward:**

| Avoid | Why |
|-------|-----|
| `defusedxml.lxml` | Thin wrapper around the same lxml flags QUIRK now sets directly; no longer needed |
| `defusedxml.ElementTree` (stdlib) | Stdlib ET does not support `no_network` or `load_dtd` controls; defusedxml patches only entity expansion |
| `defusedxml.expatbuilder` | C-extension path; no network control; no XPath support (needed for SAML NS queries) |

---

### 1b. Node.js 20 → 24 in GitHub Actions

**Deadline:** June 16, 2026 (GitHub begins forcing Node 24 on runners — effective enforcement
of the June 2026 deprecation). June 2, 2026 was a soft-warning date cited in issue trackers;
June 16, 2026 is when runners flip the default per the official GitHub Changelog announcement
(2025-09-19).

**Current state (verified by reading all workflow files, 2026-05-22):**

| Workflow file | Action | Current pin | Action version |
|---|---|---|---|
| `dashboard-quality.yml` | `actions/setup-node` | `node-version: '20'` | `@v4` |
| `release-container.yml` | No setup-node step (Docker build only) | N/A — no Node.js step | `actions/checkout@v4` only |
| `release.yml` | No setup-node step | N/A | `actions/setup-python@v5` |
| `python-staleness.yml` | No setup-node step | N/A | `actions/setup-python@v5` |

**The only file requiring a Node version change is `dashboard-quality.yml`.**

The `release-container.yml` workflow does use `actions/checkout@v4`. The `@v4` tag of
`actions/checkout` internally runs on Node 20 — this will also need to bump to `@v4` of
checkout which ships with Node 20 embedded. However, GitHub's runner-level Node migration
handles this transparently via `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` — the `@v4` checkout
action will continue to work. The **explicit action that requires a version file change** is
`actions/setup-node`.

**Required changes:**

```yaml
# dashboard-quality.yml — CHANGE:
- name: Setup Node
  uses: actions/setup-node@v4     # <-- keep @v4 OR upgrade to @v6; see below
  with:
    node-version: '24'            # <-- change from '20' to '24'
    cache: 'npm'
    cache-dependency-path: src/dashboard/package-lock.json
```

**Action version: v4 vs v6:**

`actions/setup-node@v4` supports `node-version: '24'` and will install Node 24 — the action
itself runs on Node 20 internally but that is the *action runtime*, not the *installed Node
version*. This is sufficient to unblock CI.

`actions/setup-node@v6` bumps the action's own internal runtime to Node 24 (requires runner
`>= v2.327.1`). v6 is the forward-compatible choice if there is a runner upgrade guarantee.

**Recommendation: bump `node-version: '24'` and stay on `actions/setup-node@v4` for v5.0.**
The hard deadline is about the *project's Node version*, not the action's internal runtime. If
the dashboard build and a11y tests pass on Node 24, this closes the deadline item. Bumping to
`@v6` is an optional follow-up; it does not affect the June 16, 2026 deadline.

**Compatibility check for the dashboard:** The dashboard uses React 19 + Vite + Vitest + shadcn/ui.
Node 24 (V8 v13, based on Chrome 126) is backward-compatible with this stack — no breaking
changes in the dashboard's `package.json` toolchain are expected. Verify by running `npm ci &&
npm run build && npm run lint` locally against Node 24 before merging Phase 87.

**What NOT to change in CI for v5.0:**

- Do NOT add `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` as a workaround — this is a runner
  opt-in, not a project fix. Fix the `node-version` pin instead.
- Do NOT touch `release.yml` or `python-staleness.yml` — they have no Node.js steps.
- Do NOT create a separate `ci.yml` for this — the change is one line in `dashboard-quality.yml`.

---

## 2. Chaos Lab New Profiles — Docker Images

**Context:** The chaos lab uses Docker Compose with named profiles. Existing profiles (confirmed
from docker-compose.yml, 2026-05-22): core (no profile), phaseA, cloud, identity, pki, jwt,
registry, source, vault, ssh-weak, ldaps, smime, adcs, dnssec, saml, kerberos, database,
storage-s3, email, broker, tls-cert-defects.

New profiles for v5.0: `postgres-tls`, `redis-tls`, `oqs-nginx`, `smtp-starttls`, `grpc`,
`kafka-tls`. The existing `database` profile has a plaintext postgres on port 25432 and a MySQL
on port 23306 — the new `postgres-tls` profile is a distinct service on a separate port (e.g.
25433) that enables SSL.

---

### 2a. postgres-tls Profile

**Image:** `postgres:16.6` (same pin as existing `database` profile for consistency)

**Why not a different image:** Official Postgres image supports SSL natively — no custom image
needed. TLS is enabled via postgres command flags and mounted certificates.

**Docker Compose pattern:**

```yaml
postgres-tls:
  image: postgres:16.6
  profiles: ["postgres-tls"]
  ports:
    - "25433:5432"          # distinct from database profile's 25432
  environment:
    POSTGRES_PASSWORD: testpass
    POSTGRES_DB: quirktest
  command: >
    postgres
      -c ssl=on
      -c ssl_cert_file=/etc/ssl/server.crt
      -c ssl_key_file=/etc/ssl/server.key
      -c ssl_ca_file=/etc/ssl/ca.crt
  volumes:
    - ./certs/postgres:/etc/ssl:ro
```

**Certificate generation:** A self-signed CA + server cert (via openssl in an `entrypoint.sh`
or a one-time `make certs` target in lab.sh). Key permission requirement: Postgres refuses TLS
if the key file is world-readable (`chmod 600 server.key`, `chown 999:999` for the postgres
user inside the container).

**TLS negotiation modes to expose for scanner validation:**

- `sslmode=require` — QUIRK scanner verifies TLS is present (existing scanner path in `database` scanner)
- `sslmode=verify-ca` — verify cert against CA (scanner should check cert validity)
- `sslmode=disable` explicitly on a separate service — plaintext-only comparison target

The scanner (`quirk/scanner/database_scanner.py`) already probes `pg_has_role` to detect TLS.
The `postgres-tls` profile gives the scanner a *real TLS endpoint* to confirm the positive path.

**Expected scanner output:** `protocol: "PostgreSQL"`, `tls_enabled: true`, cipher suite from
SSLinfo, `ssl_version` from server connection params.

---

### 2b. redis-tls Profile

**Image:** `bitnami/redis` from `bitnamilegacy` (same as existing lab pattern) OR official
`redis:7.4.1-alpine` with custom `redis.conf`.

**Recommended approach:** Use the official `redis:7.4.1-alpine` image (already in the lab at
`phaseA` and `broker` profiles) with a mounted `redis.conf` that enables TLS. This avoids the
Bitnami legacy dependency and keeps image consistency.

**Docker Compose pattern:**

```yaml
redis-tls:
  image: redis:7.4.1-alpine
  profiles: ["redis-tls"]
  ports:
    - "16380:6380"          # TLS port (conventional 6380; mapped from host 16380)
  command: >
    redis-server
      --tls-port 6380
      --port 0
      --tls-cert-file /tls/server.crt
      --tls-key-file /tls/server.key
      --tls-ca-cert-file /tls/ca.crt
      --tls-auth-clients no
  volumes:
    - ./certs/redis:/tls:ro
```

`--port 0` disables the plaintext port so the scanner only sees the TLS port (intentional — the
existing `broker` profile's `redis:7.4.1-alpine` on port 6380 plaintext is the contrast target).

**Why `bitnamilegacy` is NOT recommended here:** Bitnami legacy images (`bitnamilegacy/*`) are
frozen — no security updates since August 2025. The official Redis image supports TLS natively
since Redis 6.0; the mount + config approach is the production-grade pattern.

**Bitnami alternative if env-var config is preferred (MEDIUM confidence — some labs prefer it):**

```yaml
  image: bitnamilegacy/redis:7.4.0-debian-12-r4
  environment:
    REDIS_TLS_ENABLED: "yes"
    REDIS_TLS_PORT_NUMBER: "6380"
    REDIS_TLS_CERT_FILE: /tls/server.crt
    REDIS_TLS_KEY_FILE: /tls/server.key
    REDIS_TLS_CA_FILE: /tls/ca.crt
    REDIS_TLS_AUTH_ENABLED: "no"
```

Stick with the official image approach — it is already in the lab, more auditable, and the
Redis native `redis-server` TLS flags are stable since 7.x.

**Expected scanner output:** The existing `broker` scanner probes Redis on port 6380. The
`redis-tls` profile exposes port 16380 on host; the chaos lab test target should be
`localhost:16380` with TLS expected. Finding: `REDIS-TLS` cipher + protocol.

---

### 2c. OQS-nginx PQC Hybrid Profile (BACK-81 — strategic centerpiece)

**Image:** `openquantumsafe/nginx` — the official Open Quantum Safe project nginx image on
Docker Hub. Latest tag: `latest` (last pushed approximately 4 days prior to 2026-05-22, size
30.3 MB). Built from `oqs-demos/nginx/Dockerfile` using `openquantumsafe/oqs-ossl3` base with
`oqs-provider` compiled in.

**oqs-provider version:** 0.11.0 (released 2024-12-24). This is the provider compiled into the
current `openquantumsafe/nginx:latest` image.

**Port:** 4433 (default for the OQS-nginx image, configurable via nginx.conf).

**The hybrid group to use: `X25519MLKEM768`**

This is the correct choice because:
1. It is explicitly listed in the oqs-provider 0.11.0 supported group table.
2. It is the only hybrid algorithm currently supported by default in major web browsers
   (Chrome 124+, Firefox 132+).
3. It combines classical X25519 (ECDH) with NIST-standardized ML-KEM-768 (FIPS 203) — this is
   the NIST-blessed hybrid the QUIRK scanner should recognize as "SAFE" in its quantum-readiness
   model.
4. `SecP256r1MLKEM768` is the secondary option (P-256 + ML-KEM-768) — include it in
   DEFAULT_GROUPS as a fallback but not as the primary.

**Docker Compose pattern:**

```yaml
oqs-nginx:
  image: openquantumsafe/nginx
  profiles: ["oqs-nginx"]
  ports:
    - "14433:4433"          # host 14433 → container 4433
  environment:
    DEFAULT_GROUPS: "X25519MLKEM768:SecP256r1MLKEM768:x25519:prime256v1"
  # nginx.conf is baked into the image; DEFAULT_GROUPS env var sets the ssl_ecdh_curve
  # directive at container start time via the image's entrypoint script.
```

**Why this DEFAULT_GROUPS ordering:**
- `X25519MLKEM768` first — preferred hybrid, browser-compatible, NIST PQC SAFE.
- `SecP256r1MLKEM768` second — fallback hybrid for P-256-preferring clients.
- `x25519` third — classical fallback for non-PQC clients (sslyze probe compatibility).
- `prime256v1` last — P-256 classical fallback.

**Scanner integration:** The TLS scanner (sslyze) negotiates TLS with the OQS-nginx endpoint.
sslyze's cipher suite enumeration reports the negotiated group — for OQS hybrid groups, sslyze
will report the group name as a string (e.g., `X25519MLKEM768`). The QUIRK quantum-safety
classifier already has an entry for ML-KEM in the NIST PQC classification table. The
`oqs-nginx` profile's finding should be:
- `cipher_suite: "TLS_AES_256_GCM_SHA384"` (TLS 1.3, the OQS image uses TLS 1.3 only)
- `key_exchange_group: "X25519MLKEM768"` — QUIRK classifies this as SAFE (post-quantum hybrid)
- Quantum readiness score contribution: above "good classical TLS" — this is the scoring-ceiling
  anchor for the PQC side of the model.

**Certificate for the OQS endpoint:** The image ships with a self-signed RSA-2048 cert by
default (classical auth; hybrid only applies to key exchange). The scanner will detect a
classical auth cert + PQC key exchange — this is the expected real-world deployment pattern
during the PQC transition period.

**IMPORTANT — sslyze and OQS groups:** sslyze uses the system OpenSSL for TLS handshakes. The
standard OpenSSL 3.x (without the OQS provider) does NOT support `X25519MLKEM768` as a client
group. This means sslyze will negotiate the classical fallback (`x25519` or `prime256v1`) when
probing the OQS-nginx endpoint — unless the QUIRK scanner uses an OQS-enabled OpenSSL or sends
a dedicated `ClientHello` with the hybrid group advertised.

**Mitigation:** The `oqs-nginx` profile's primary scanner value is not cipher-suite detection
via sslyze (classical TLS probes only see the classical fallback), but rather:
1. Verifying the endpoint accepts TLS at all (TLS-present finding).
2. Using a dedicated `openssl s_client -curves X25519MLKEM768` subprocess call (requires the
   OQS provider to be installed on the scan host — out of scope for the default scanner path).
3. Alternatively: use `openquantumsafe/curl` as a test client container in the chaos lab to
   confirm the endpoint works, and have the scanner detect it via a custom probe.

**Recommended v5.0 scope for oqs-nginx:** Ship the profile + confirm the endpoint is TLS-live
via sslyze (classical cipher observed). Document the PQC handshake as a future scanner
enhancement requiring an OQS-enabled sslyze build. The scoring-ceiling contribution is that
this target scores above classical TLS because QUIRK's CBOM classification recognizes the OQS
cert's `PublicKeyAlgorithm` (currently RSA — classical) but the *chaos-lab oracle* declares
this target as "PQC-hybrid demo endpoint" and the test confirms the scanner correctly parses
its TLS cert + finds it live.

**NOT recommended for v5.0:** Shipping a custom sslyze build with OQS provider linked — this
is a heavy engineering effort (custom liboqs + OpenSSL 3.x provider compilation) and belongs in
a dedicated v5.1 PQC scanner enhancement phase.

---

### 2d. SMTP/STARTTLS Profile

**Image:** `docker-mailserver/docker-mailserver:14.0` (Docker Mailserver — actively maintained,
well-documented TLS config, supports STARTTLS on port 25 + SMTPS on port 465)

Alternative simpler image: `rnwood/smtp4dev:3.6.1` (dev-only lightweight SMTP server with TLS
support and web UI for inspecting sent emails).

**Recommendation: `rnwood/smtp4dev:3.6.1`** for the chaos lab context. It is lighter (~100 MB),
requires no complex config, exposes SMTP with STARTTLS on port 25 and SMTPS on 465, and is
purpose-built for testing. docker-mailserver is production-grade but requires more config files.

**Docker Compose pattern:**

```yaml
smtp-starttls:
  image: rnwood/smtp4dev:3.6.1
  profiles: ["smtp-starttls"]
  ports:
    - "12025:25"            # SMTP + STARTTLS
    - "14650:465"           # SMTPS (implicit TLS)
    - "15143:143"           # IMAP (for completeness)
  environment:
    ServerOptions__TlsMode: StartTls     # STARTTLS on port 25
    ServerOptions__TlsCertificate: /tls/server.pfx
  volumes:
    - ./certs/smtp:/tls:ro
```

**For a minimal Postfix-based STARTTLS target** (more realistic for scanner validation):

```yaml
smtp-starttls:
  image: juanluisbaptiste/postfix:latest
  profiles: ["smtp-starttls"]
  ports:
    - "12025:25"
  environment:
    SMTP_SERVER: localhost
    SERVER_HOSTNAME: chaos.quirk.lab
  # Postfix STARTTLS config added via mounted main.cf
```

**Note on existing `email` profile:** The existing `email` profile (Phase 32) already includes
a Postfix+Dovecot setup. The new `smtp-starttls` profile is specifically for demonstrating
*STARTTLS stripping detection* — exposing an SMTP endpoint where STARTTLS is advertised but
the scanner should verify that an upgrade is correctly enforced (or detect when it is not).

**BACK-82 scope:** The key scanner finding for this profile is `STARTTLS-ADVERTISED` vs
`STARTTLS-ENFORCED` — the scanner already detects STARTTLS stripping (Phase 32). The chaos lab
needs a target where STARTTLS is offered but not enforced so the scanner's positive detection
can be validated end-to-end.

---

### 2e. gRPC TLS Profile

**Image:** No pre-built public gRPC+TLS chaos lab image exists. The correct approach is a
minimal custom Dockerfile in `quantum-chaos-enterprise-lab/grpc/`.

**Recommended implementation:** A Go-based gRPC server (minimal, no business logic) with TLS
enabled via a mounted certificate, compiled into a Docker image.

**Alternative without a custom image:** Use `envoyproxy/envoy:v1.31.0` as a TLS-terminating
front-end in front of a plaintext gRPC service. This is common in production but adds
complexity to the lab.

**Simplest approach for a chaos lab:** Build a minimal Go gRPC server from the official gRPC
Go SDK. The Dockerfile is ~15 lines:

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /app
RUN go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
# ... compile a minimal echo service with TLS
FROM alpine:3.20
COPY --from=builder /app/server /server
COPY certs/ /tls/
ENTRYPOINT ["/server", "--tls", "--cert=/tls/server.crt", "--key=/tls/server.key"]
```

**Port:** 50051 (gRPC convention); expose on host port 15051.

**Scanner integration:** gRPC uses HTTP/2 over TLS. sslyze's TLS prober treats it the same as
any TLS endpoint — it negotiates TLS on port 15051 and extracts cipher suite + cert. The gRPC
profile's scanner value is verifying that the TLS scanner correctly classifies an HTTP/2 TLS
endpoint (gRPC characteristic) and emits a `GRPC-TLS` finding.

**What NOT to do:** Do not use Envoy for the chaos lab unless the team is already familiar with
Envoy config. The complexity-to-value ratio is high for a single chaos lab profile. A minimal
Go server is 50 lines of code and produces a portable ~15 MB Docker image.

---

### 2f. Kafka TLS Profile

**Current state:** The existing `broker` profile uses `apache/kafka:3.7.0` (NOT the deprecated
Bitnami image) in KRaft mode on port 9092 (plaintext). This is confirmed from docker-compose.yml
line 1045.

**Bitnami situation:** Bitnami/kafka images moved to `bitnamilegacy` in August 2025 and no
longer receive updates. The existing lab already uses `apache/kafka:3.7.0` — this is the correct
image to continue using for the new `kafka-tls` profile.

**Image:** `apache/kafka:3.9.0` (upgrade from 3.7.0 for the new TLS profile; latest stable as
of May 2026). Using a slightly newer pin for the TLS profile vs the existing broker profile is
intentional — it lets the scanner be tested against two Kafka versions.

**TLS listener configuration for apache/kafka in KRaft mode:**

```yaml
kafka-tls:
  image: apache/kafka:3.9.0
  profiles: ["kafka-tls"]
  ports:
    - "19093:9093"          # SSL listener; host 19093 → container 9093
  environment:
    KAFKA_NODE_ID: 1
    KAFKA_PROCESS_ROLES: broker,controller
    KAFKA_LISTENERS: "CONTROLLER://0.0.0.0:9091,PLAINTEXT://0.0.0.0:9092,SSL://0.0.0.0:9093"
    KAFKA_ADVERTISED_LISTENERS: "PLAINTEXT://localhost:9092,SSL://localhost:19093"
    KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,SSL:SSL"
    KAFKA_CONTROLLER_QUORUM_VOTERS: "1@localhost:9091"
    KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
    KAFKA_SSL_KEYSTORE_TYPE: PEM
    KAFKA_SSL_KEYSTORE_LOCATION: /tls/server.crt
    KAFKA_SSL_KEYSTORE_KEY_LOCATION: /tls/server.key
    KAFKA_SSL_TRUSTSTORE_TYPE: PEM
    KAFKA_SSL_TRUSTSTORE_CERTIFICATES: /tls/ca.crt
    KAFKA_SSL_CLIENT_AUTH: none        # one-way TLS (server cert only)
  volumes:
    - ./certs/kafka:/tls:ro
```

**Apache/kafka PEM support:** `apache/kafka` (KIP-651) supports PEM-format keystores via
`KAFKA_SSL_KEYSTORE_TYPE: PEM` — avoids Java keystore (JKS) ceremony that plagued older Kafka
TLS setups. This is confirmed in the Kafka 3.7+ feature set.

**Port assignment:** Port 19093 on host is intentionally distinct from the existing `broker`
profile's potential port usage and the `redis-tls` port on 16380.

**Expected scanner output:** `KAFKA-TLS` finding; cipher suite from TLS handshake on port 19093;
no `KAFKA-PLAIN` finding for this profile (no plaintext listener exposed on host).

---

## 3. Identity Lab Gap — No New Libraries Required (BACK-78)

**Question asked:** What tooling/libraries extract observable crypto evidence from Kerberos KDC,
SAML SP, and DNSSEC zones?

**Answer for v5.0:** No new libraries are required. The existing stack already covers all three:

| Identity surface | Existing library | What it extracts |
|---|---|---|
| Kerberos KDC etype | `impacket>=0.13.0` (in `[identity]`) | AS-REQ unauthenticated probe; etype values from KRB-ERROR padata; already implemented in `quirk/scanner/kerberos_scanner.py` |
| SAML SP | `lxml>=6.0` (core) | IdP metadata XML; signing/encryption cert extraction; already implemented in `quirk/scanner/saml_scanner.py` |
| DNSSEC zone | `dnspython[dnssec]>=2.8.0` (core, current latest 2.9.0) | DNSKEY/DS/NSEC records; RFC 8624 algorithm classification; already implemented in `quirk/scanner/dnssec_scanner.py` |

**BACK-78 is an evidence-key wiring issue, not a library gap.** The scanners run and extract
crypto evidence, but the evidence counters (`identity_weak_etype_count`, `saml_weak_signing_count`,
`dnssec_weak_algo_count`) may not be wiring correctly to the 6-pillar scoring model for the
**chaos lab profiles** specifically. The fix is in `quirk/intelligence/evidence.py` wiring, not
a new dependency.

**No new packages needed for identity lab gap.**

---

## 4. Scoring Residuals — No New Libraries

EVIDENCE-TALLY-01, RENDER-CLI-01, RENDER-PDF-01, and BACK-63 score transparency are all
internal logic bugs in `quirk/intelligence/` and the report renderers. No new packages needed.

---

## Summary: New Stack Additions for v5.0

| Item | Change type | What changes | Version |
|---|---|---|---|
| `defusedxml` | **REMOVE** from core deps | Drop from `pyproject.toml [project.dependencies]` | n/a (removed) |
| `lxml` XXE API | Config pattern (no version change) | Add `_SAFE_PARSER` module-level constant; 5-flag XMLParser | `>=6.0` (existing) |
| Node.js version in CI | CI config change (no package change) | `node-version: '20'` → `'24'` in `dashboard-quality.yml` | 24.x |
| `actions/setup-node` | Stay at `@v4` (no upgrade required for deadline) | Only `node-version` value changes | `@v4` (existing) |
| `postgres:16.6` | Chaos lab new profile use (image already in lab) | New `postgres-tls` Docker Compose profile | `16.6` (existing pin) |
| `redis:7.4.1-alpine` | Chaos lab new profile use (image already in lab) | New `redis-tls` Docker Compose profile | `7.4.1-alpine` (existing pin) |
| `openquantumsafe/nginx` | **NEW Docker image** — OQS-nginx chaos lab profile | `oqs-nginx` profile, port 14433 | `latest` (pinned to digest recommended) |
| `rnwood/smtp4dev:3.6.1` | **NEW Docker image** — SMTP/STARTTLS chaos lab profile | `smtp-starttls` profile, ports 12025/14650 | `3.6.1` |
| Custom gRPC image | **NEW custom Dockerfile** — minimal Go gRPC+TLS server | `grpc` profile, port 15051 | Go 1.22-alpine + alpine:3.20 |
| `apache/kafka:3.9.0` | **NEW Docker image** (upgrade from 3.7.0 in existing broker) | `kafka-tls` profile, port 19093 | `3.9.0` |

**Total new Python packages: 0.** `defusedxml` is removed; nothing is added.

**Total new Docker images: 3** (`openquantumsafe/nginx`, `rnwood/smtp4dev`, `apache/kafka:3.9.0`).

**1 new custom Dockerfile** for the gRPC chaos lab service.

---

## What NOT to Add for v5.0

| Avoid | Why | What to do instead |
|---|---|---|
| OQS-enabled sslyze build | Requires compiling liboqs + OpenSSL3 provider; heavy engineering; wrong shape for a stabilization milestone | Ship oqs-nginx profile; note PQC handshake detection as a v5.1 enhancement |
| `pysaml2` or `signxml` | SAML parsing is already implemented via lxml; adding these would duplicate functionality | No action needed; lxml + SAML_NS dict is the correct approach |
| `krb5` / `pykrb5` / `minikerberos` | Kerberos etype scanning already uses impacket AS-REQ probe | No action needed for BACK-78 |
| `bitnamilegacy/redis` | Frozen since Aug 2025; no security updates | Use official `redis:7.4.1-alpine` with TLS flags |
| `bitnami/kafka` (new) | No longer free on Docker Hub (moved to commercial Bitnami Secure Images) | Use `apache/kafka:3.9.0` |
| `docker-mailserver/docker-mailserver` | Heavy (500+ MB); requires complex config files | Use `rnwood/smtp4dev:3.6.1` for chaos lab simplicity |
| `strimzi-kafka-operator` | Kubernetes operator; chaos lab uses Docker Compose | `apache/kafka` directly |
| `actions/setup-node@v6` | Not required for the June 16, 2026 deadline; `@v4` with `node-version: 24` is sufficient | Defer to v5.1 if runner version guarantees aren't confirmed |
| Any new Python scanner library | v5.0 is stabilization — no new scanner capability surface | All three identity scanners work with existing deps |

---

## Version Compatibility Notes

| Constraint | Risk | Mitigation |
|---|---|---|
| `lxml>=6.0` + removal of `defusedxml` | nmap_parser.py callers get lxml's `_Element` instead of stdlib `ElementTree._Element` — API-compatible at `findall`/`get`/`text` level | Confirm no caller uses `ET.Element` type annotations directly; add type check in CI |
| Node 24 + React 19 + Vite 5.x | Node 24 EOL for Node 20 may surface minor CJS/ESM resolution differences | Run `npm ci && npm run build` on Node 24 in pre-merge CI before finalizing Phase 87 |
| `apache/kafka:3.9.0` KRaft + PEM TLS | KIP-651 PEM support is confirmed for 3.7+; 3.9.0 follows same env var pattern | Test TLS listener startup with a health check in docker-compose before declaring profile live |
| `openquantumsafe/nginx` + sslyze probe | sslyze negotiates classical fallback (x25519); the PQC handshake is not directly observable from the scanner | Document in oracle; scanner sees TLS-live + classical cipher; PQC group detection is future work |

---

## Sources

- `lxml` official FAQ (lxml.de/FAQ.html) — XXE default behavior in 5.x+, XMLParser flags (HIGH confidence)
- `lxml` official parsing docs (lxml.de/6.0/parsing.html) — all XMLParser keyword arguments verified (HIGH confidence)
- PyPI lxml — latest version 6.1.1 released 2026-05-18 (HIGH confidence)
- GitHub blog changelog (2025-09-19) — Node 20 deprecation announcement, June 16, 2026 effective date (HIGH confidence)
- `github.com/actions/setup-node` releases — v6 requires runner v2.327.1; v4 supports `node-version: 24` (HIGH confidence)
- `hub.docker.com/r/openquantumsafe/nginx` — latest tag, 30.3 MB, port 4433, quantum-safe TLS 1.3 (HIGH confidence)
- `github.com/open-quantum-safe/oqs-provider` — version 0.11.0 (2024-12-24); X25519MLKEM768, SecP256r1MLKEM768 in supported group list (HIGH confidence)
- `oqs-demos/nginx/USAGE.md` — DEFAULT_GROUPS env var, Kyber family defaults (HIGH confidence)
- OQS interop test server (test.openquantumsafe.org) — X25519MLKEM768 browser compatibility confirmation (HIGH confidence)
- `hub.docker.com/r/bitnami/redis` — REDIS_TLS_ENABLED env var pattern; official redis TLS flags (MEDIUM — bitnami legacy note)
- docker-compose.yml (QUIRK repo, 2026-05-22) — confirmed existing profiles, apache/kafka:3.7.0 in broker profile (HIGH confidence — source of truth)
- pyproject.toml (QUIRK repo, 2026-05-22) — defusedxml>=0.7.1, lxml>=6.0, dnspython[dnssec]>=2.8.0 (HIGH confidence — source of truth)
- quirk/scanner/saml_scanner.py (QUIRK repo, 2026-05-22) — existing lxml XXE pattern confirmed; defusedxml fallback confirmed (HIGH confidence — source of truth)
- quirk/discovery/nmap_parser.py (QUIRK repo, 2026-05-22) — defusedxml.ElementTree unconditional import confirmed (HIGH confidence — source of truth)
- `github.com/bitnami/containers` README — Bitnami legacy transition August 2025; KRaft mode env vars (MEDIUM confidence)
- Apache Kafka KIP-651 — PEM keystore support in 3.7+; SSL env vars (MEDIUM confidence — per community documentation)

---

*Stack research for: QU.I.R.K. v5.0 Stabilization + Tech Debt Sweep*
*Researched: 2026-05-22*
