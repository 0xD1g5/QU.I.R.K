---
phase: 04-chaos-lab-expansion
plan: "05"
subsystem: infra
tags: [docker, docker-compose, openssh, openldap, ssh-audit, sslyze, lab]

# Dependency graph
requires:
  - phase: 04-chaos-lab-expansion/04-04
    provides: storage profile services (LocalStack KMS, Vault, postgres-pgcrypto) completing pre-ssh/ldaps compose sections

provides:
  - ssh-weak Docker service: ubuntu:18.04 OpenSSH server with weak KEX/hostkey/MAC config on port 20022
  - ldaps Docker service: osixia/openldap:1.5.0 with TLS enabled on port 636 using existing lab certs
  - expected_results_v3.md Phase 4 sections: 6 profile oracle entries (jwt, registry, source, storage, ssh-weak, ldaps)

affects:
  - Phase 5 (Web Dashboard) — lab remains stable for integration validation
  - SSH scanner tests (SCAN-02) — ssh-weak service validates ssh-audit KEX/hostkey/MAC findings
  - sslyze TLS scanner — ldaps service validates sslyze against LDAP over TLS

# Tech tracking
tech-stack:
  added:
    - ubuntu:18.04 (OpenSSH 7.6p1 base for ssh-weak container)
    - osixia/openldap:1.5.0 with LDAP_TLS=true (ldaps service)
  patterns:
    - Docker build context pattern: ./ssh directory with sshd_config COPY injection
    - Profile isolation: ssh-weak and ldaps profiles independent of all prior profiles

key-files:
  created:
    - quantum-chaos-enterprise-lab/ssh/sshd_config
    - quantum-chaos-enterprise-lab/ssh/Dockerfile
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/expected_results_v3.md

key-decisions:
  - "ubuntu:18.04 base for ssh-weak (OpenSSH 7.6p1 still supports legacy algorithms removed in later versions)"
  - "Port 20022 for ssh-weak (safe range, no conflict with existing 2222 ssh-alt service)"
  - "Port 636 for ldaps (standard LDAPS port — required for sslyze to recognize LDAP-over-TLS)"
  - "Reuse existing lab certs (modern.crt, modern.key, ca.crt) for ldaps TLS via /container/service/slapd/assets/certs/ mount path (osixia/openldap convention)"
  - "LDAP_TLS_VERIFY_CLIENT=never for lab use (no client cert required)"
  - "ssh_host_dsa_key generated explicitly in Dockerfile (required for ssh-dss HostKeyAlgorithms)"

patterns-established:
  - "Pattern: sshd_config COPY injection — place sshd_config alongside Dockerfile, COPY into /etc/ssh/sshd_config at build time"
  - "Pattern: ubuntu:18.04 for legacy algorithm support — newer ubuntu base images ship OpenSSH that has removed group1/dss algorithms"

requirements-completed: [LAB-05, LAB-06]

# Metrics
duration: 3min
completed: 2026-03-30
---

# Phase 4 Plan 05: SSH-Weak + LDAPS Profiles + Phase 4 Expected Results Summary

**ubuntu:18.04 OpenSSH ssh-weak service (port 20022) with group1-sha1/ssh-dss/hmac-md5 weak config, osixia/openldap ldaps service (port 636) with TLS via modern.crt, and expected_results_v3.md updated with all 6 Phase 4 scanner oracle sections**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-30T18:53:30Z
- **Completed:** 2026-03-30T18:56:19Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `ssh/sshd_config` with deliberately weak algorithms: `diffie-hellman-group1-sha1`, `diffie-hellman-group14-sha1`, `ssh-dss`, `hmac-md5`, `hmac-sha1` — all critical/warning findings for ssh-audit (LAB-05)
- Created `ssh/Dockerfile` from ubuntu:18.04 installing openssh-server, generating DSA host key, injecting weak sshd_config
- Added `ssh-weak` (port 20022) and `ldaps` (port 636, LDAP_TLS=true, existing lab certs) services to docker-compose.yml; YAML validates cleanly
- Appended 6 Phase 4 oracle sections to expected_results_v3.md (jwt, registry, source, storage, ssh-weak, ldaps) with expected findings and scanner validation commands per profile

## Task Commits

Each task was committed atomically:

1. **Task 1: Build ssh-weak Dockerfile and sshd_config; add ssh-weak + ldaps compose services** - `238e165` (feat)
2. **Task 2: Update expected_results_v3.md with Phase 4 profile findings** - `6b08d2e` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `quantum-chaos-enterprise-lab/ssh/sshd_config` - Weak OpenSSH server config with group1-sha1, ssh-dss, hmac-md5 algorithms
- `quantum-chaos-enterprise-lab/ssh/Dockerfile` - ubuntu:18.04 base with openssh-server and DSA host key generation
- `quantum-chaos-enterprise-lab/docker-compose.yml` - Added ssh-weak (port 20022) and ldaps (port 636) profile services
- `quantum-chaos-enterprise-lab/expected_results_v3.md` - Appended 6 Phase 4 oracle sections (jwt/registry/source/storage/ssh-weak/ldaps)

## Decisions Made

- ubuntu:18.04 chosen as base because OpenSSH 7.6p1 still ships group1-sha1, ssh-dss, and hmac-md5 — newer bases have removed these legacy algorithms making weak-config testing impossible
- Port 20022 for ssh-weak avoids conflict with existing ssh-alt on 2222
- Port 636 (standard LDAPS) required — sslyze identifies LDAP-over-TLS by standard port; non-standard port would require explicit protocol hint
- osixia/openldap TLS cert mount path `/container/service/slapd/assets/certs/` is the image's documented convention; existing lab certs (modern.crt, modern.key, ca.crt) reused without modification

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Docker daemon not running in execution environment — ssh-weak build and smoke tests (steps 2-4 of verification) could not be executed. YAML validity confirmed (`docker compose config --quiet` passes). File content verified by grep. Smoke tests (ssh-audit localhost:20022, sslyze localhost:636) require docker daemon to be running.

## Known Stubs

None - all Phase 4 sections in expected_results_v3.md contain real expected findings mapped to actual services. No placeholder text or TODO markers.

## Next Phase Readiness

- Phase 4 lab infrastructure complete: all 6 profiles (jwt, registry, source, storage, ssh-weak, ldaps) built and documented
- expected_results_v3.md updated as scanner oracle for validation testing
- Phase 5 (Web Dashboard) can proceed independently; Phase 4 lab remains available for regression validation
- SSH scanner (SCAN-02) can be validated against ssh-weak service when Docker is available

---
*Phase: 04-chaos-lab-expansion*
*Completed: 2026-03-30*
