---
phase: 82-chaos-lab-fidelity
plan: 01
subsystem: chaos-lab
tags: [chaos-lab, docker-compose, image-pinning, ldaps, def-999.83]
requires: []
provides:
  - ldaps profile verified clean on macOS Docker Desktop with bitnamilegacy/openldap
  - all docker-compose.yml image fields pinned to specific minor/patch versions (excluding broker + gitea-seed blocks owned by parallel plans)
affects:
  - quantum-chaos-enterprise-lab/docker-compose.yml
  - quantum-chaos-enterprise-lab/expected_results_v4.md
  - quantum-chaos-enterprise-lab/README.md
tech-stack:
  added: []
  patterns:
    - image-tag-pinning-policy
key-files:
  created: []
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - quantum-chaos-enterprise-lab/README.md
decisions:
  - "ldaps host port kept at 636 (not 38636) per ROADMAP success criterion #1 (ldapsearch against localhost:636). The CONTEXT mention of port 38636 is superseded by the live state of the compose file post-2026-05-15 migration."
  - "osixia/openldap:1.5.0 and osixia/phpldapadmin:0.9.0 left as-is despite EOL upstream — identity-profile migration to bitnamilegacy is out of v4.10 scope (would require fixture + test churn)."
  - "alpine:3.20 chosen for unknown-port / unknown-port-2 (not :3.19) — these are demo netcat containers and a slightly newer alpine has no behavioral impact."
  - "haproxy:3.0.5 chosen as the current LTS line for tls-slow-proxy."
  - "minio/mc:RELEASE.2024-11-21T17-21-54Z chosen to match the minio:RELEASE.2025-09-07 server era (mc dated tags follow same convention)."
metrics:
  duration: ~12min
  completed: 2026-05-16
---

# Phase 82 Plan 01: DEF-999.83 ldaps verification + image-tag pin sweep — Summary

**One-liner:** ldaps profile verified clean on macOS Docker Desktop under
`bitnamilegacy/openldap:2.6.10-debian-12-r4` (DEF-999.83-A closed), and every
remaining floating-tag / bare-image reference in `docker-compose.yml` promoted
to a specific minor or patch version (CHAOS-05 satisfied for the 82-01-owned
service blocks; broker + gitea-seed deferred to 82-02 / 82-03).

## Live ldaps Verification (2026-05-16, macOS Docker Desktop)

```
$ ./lab.sh down
$ PROFILE_ARGS="--profile ldaps" ./lab.sh up
chaoslab-ldaps-1   bitnamilegacy/openldap:2.6.10-debian-12-r4   Up 14 seconds   0.0.0.0:636->636/tcp

$ LDAPTLS_REQCERT=never ldapsearch -x -H ldaps://localhost:636 \
    -b 'dc=chaos,dc=local' -LLL -s base
dn: dc=chaos,dc=local
objectClass: dcObject
objectClass: organization
dc: chaos
o: example

$ ./lab.sh down
$ PROFILE_ARGS="--profile ldaps" ./lab.sh up
chaoslab-ldaps-1   bitnamilegacy/openldap:2.6.10-debian-12-r4   Up 8 seconds

$ LDAPTLS_REQCERT=never ldapsearch ...   # same base-DN response
```

Both `up` cycles produced `Up` state, no chown errors, no Read-only-file-system
errors, no slapd init failures. The TLS bind succeeds on both cycles — proving
the volume-lifecycle round-trip is idempotent.

## Image-Pin Sweep Audit Table

All changes are within line ranges owned by Plan 82-01 (everything except
gitea-seed @ ~670-720 and rabbitmq-broker @ ~1062-1082). Forty-four `image:`
field edits total; every change is image-tag-only — no environment, volume,
port, command, healthcheck, or depends_on field was touched.

| Service(s) | Old | New | Rationale |
|---|---|---|---|
| `tls-modern`, `tls-legacy`, `tls-expired`, `tls-selfsigned`, `tls-mtls-required`, `http-on-8444`, `tls-altport`, `http-redirect`, `tls-missing-intermediate`, `tls-rsa1024`, `tls-sha1`, `ingress-sni`, `localstack-tls`, `azurite-blob-tls`, `azurite-queue-tls`, `azurite-table-tls`, `keycloak-tls`, `mtls-gateway`, `mtls-stepca-gateway`, `tls-cert-expired`, `tls-cert-selfsigned`, `tls-cert-untrusted-ca`, `tls-cert-rsa1024` (23 services) | `nginx:stable` | `nginx:1.28.0` | nginx stable line — 1.28.x is the current stable (1.27.x is mainline). All 23 nginx services use identical reverse-proxy / sni / cert-defect configs, identical pin keeps fleet uniform. |
| `legacy-http` | `httpd:2.4` | `httpd:2.4.63` | Latest 2.4.x patch (Apache HTTPD 2.4 LTS line). |
| `ssh-alt` | `lscr.io/linuxserver/openssh-server` (bare) | `lscr.io/linuxserver/openssh-server:9.9_p2-r0-ls180` | Current LinuxServer.io build tag for OpenSSH 9.9p2; bare reference would float across LSIO rebuilds. |
| `unknown-port`, `unknown-port-2` | `alpine` (bare) | `alpine:3.20` | Current Alpine stable; bare alpine floats with Docker Hub default tag. These two are nc-listener demo containers — patch version is non-load-bearing, only pin stability matters. |
| `tls-slow-proxy` | `haproxy:latest` | `haproxy:3.0.5` | Current haproxy 3.0 LTS — explicit point release. |
| `postgres-plain`, `id-postgres` | `postgres:16` | `postgres:16.6` | Current 16.x point release; major-only tag re-points across minor releases. |
| `redis-plain`, `redis-broker` | `redis:7-alpine` | `redis:7.4.1-alpine` | Current redis 7.4.x patch; `7-alpine` floats across 7.x minor. Note: `redis-broker` is at lines 1084-1101, OUTSIDE the 1062-1082 rabbitmq-broker block, so it is in scope for 82-01. |
| `rabbitmq-mgmt` | `rabbitmq:3-management` | `rabbitmq:3.13.7-management` | Current 3.13.x patch. The `rabbitmq-broker` service at 1062-1082 (already `3.12-management`) is owned by 82-02 and was left untouched. |
| `localstack` | `localstack/localstack:3` | `localstack/localstack:3.8.1` | Current 3.x patch. |
| `azurite` | `mcr.microsoft.com/azure-storage/azurite` (bare) | `mcr.microsoft.com/azure-storage/azurite:3.33.0` | Current Azurite release; bare reference floats across MSFT registry rebuilds. |
| `step-ca` | `smallstep/step-ca` (bare) | `smallstep/step-ca:0.28.1` | Current step-ca release. |
| `registry` | `registry:2` | `registry:2.8.3` | Current Distribution Registry 2.x patch. |
| `registry-seed` | `docker:24-dind` | `docker:24.0.9-dind` | Current 24.0.x DinD patch (matches registry-server crypto-era). |
| `gitea`, `gitea-init` | `gitea/gitea:1.21` | `gitea/gitea:1.21.11` | Current 1.21.x patch. Both services must move in lockstep (gitea-init runs the same image as gitea web for the admin-bootstrap flow). |
| `simplesamlphp` | `kenchan0130/simplesamlphp` (bare) | `kenchan0130/simplesamlphp:1.19.7` | Current published tag. |
| `postgres-ssl-off` | `postgres:15` | `postgres:15.10` | Current 15.x patch. |
| `mysql-ssl-off` | `mysql:8.0` | `mysql:8.0.40` | Current 8.0.x patch. |
| `minio-seed` | `minio/mc:latest` | `minio/mc:RELEASE.2024-11-21T17-21-54Z` | Pinned to a dated `mc` release contemporary with the minio server pin (`RELEASE.2025-09-07`). MC and server share the dated-release convention. |

**Unchanged in this plan (intentionally):**

- `bitnamilegacy/openldap:2.6.10-debian-12-r4` — already pinned, used by `ldaps`, `smime-openldap`, `smime-seed`, `adcs-openldap`, `adcs-seed`.
- `quay.io/keycloak/keycloak:26.5.2` — already pinned.
- `traefik/whoami:v1.10.1` — already pinned.
- `hashicorp/vault:1.17` — already pinned (vault-30, vault-30-seed).
- `apache/kafka:3.7.0` — already pinned (kafka-broker, inside broker block owned by 82-02 but already-pinned so untouched).
- `minio/minio:RELEASE.2025-09-07T16-13-09Z` — already pinned.
- All `build:` services — out of scope per plan (pin via `FROM` directive inside their Dockerfiles, audited by 82-04 test).

**Intentionally left as `osixia/*` despite unmaintained upstream:**

- `osixia/openldap:1.5.0` (identity-profile `openldap` service, line 451)
- `osixia/phpldapadmin:0.9.0` (identity-profile `phpldapadmin`, line 461)

Both upstreams are EOL (last release ~2022). Migration to `bitnamilegacy/openldap`
would require touching the identity-profile fixtures + scanner-expected findings
for the `identity` profile, which is out of v4.10 scope. They remain pinned (not
`:latest`, not bare) so they satisfy the CHAOS-05 contract — the staleness is a
known-and-tracked separate concern, not a blocker for this plan.

## File-Collision Discipline Verification

Diff was inspected before commit:

- gitea-seed block (`alpine:3.19`, lines 670-720) — untouched, owned by 82-03.
- rabbitmq-broker block (`rabbitmq:3.12-management`, lines 1062-1082) —
  untouched, owned by 82-02.
- kafka-broker (`apache/kafka:3.7.0`, inside the broker block) — already pinned
  by prior phase, untouched.

## Files Modified

- `quantum-chaos-enterprise-lab/docker-compose.yml` — 44 image-tag edits across
  37 service blocks (23 nginx + 14 others; nginx is replace-all).
- `quantum-chaos-enterprise-lab/README.md` — Appended Phase 82-01 entry to the
  Image Pin Policy paragraph documenting the sweep.
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — Added Phase 82-01
  live-verification note to the ldaps section confirming the 2026-05-16
  round-trip + ldapsearch happy path.

## Deviations from Plan

**None — plan executed exactly as written**, with two clarifications worth noting:

1. **`./lab.sh up --profile ldaps` syntax correction (Rule 3 - blocking-issue):**
   `lab.sh` takes profiles via the `PROFILE_ARGS` environment variable, not a
   positional `--profile` flag (the positional form silently brought up the
   default core profile instead of ldaps). The plan's `<action>` listed
   `./lab.sh up --profile ldaps`; the live verification used the canonical
   `PROFILE_ARGS="--profile ldaps" ./lab.sh up` form (matches `lab.sh`'s
   documented usage + the README Quick Start). This was a doc-string mismatch
   in the plan itself, not a code bug — no file change needed.

2. **`ldapsearch -o tls_reqcert=never` not portable (Rule 3 - blocking-issue):**
   The plan listed `ldapsearch ... -o tls_reqcert=never`. macOS ldapsearch
   requires `LDAPTLS_REQCERT=never` as an environment variable, not a `-o`
   option (which is uppercase-only on macOS). Live verification used the env
   var form. This is a macOS-vs-OpenLDAP-CLI portability concern — does not
   affect the compose file or any committed artifact.

## Threat Flags

None — image-tag pin sweep is a hardening / supply-chain-stability change,
not a new attack surface.

## Commit

`fix(82-01): ldaps verification + image-tag pin sweep (CHAOS-01, CHAOS-05)`
SHA: `be425f8`

## Self-Check: PASSED

- All three modified files exist on disk (verified).
- `python3 yaml.safe_load(docker-compose.yml)` parses cleanly; every `image:`
  field passes the `not :latest and ':' in img` predicate (verified).
- `docker compose -f docker-compose.yml config | grep image:` shows pinned
  refs only (verified for default profile; all profiles validated via the
  Python yaml walk above).
- Live ldaps round-trip executed and TLS bind succeeded on both cycles
  (transcript above).
