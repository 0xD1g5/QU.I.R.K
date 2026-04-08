---
phase: 4
slug: chaos-lab-expansion
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-30
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Docker Compose smoke tests (no new pytest files needed) |
| **Config file** | `quantum-chaos-enterprise-lab/docker-compose.yml` |
| **Quick run command** | `docker compose --profile <name> up -d && sleep 5` (per profile) |
| **Full suite command** | Run each profile smoke test in sequence (see Per-Task map) |
| **Estimated runtime** | ~60–120 seconds per profile (image pull + service startup) |

---

## Sampling Rate

- **After every task commit:** Verify the new Dockerfile/service builds with `docker compose build <service>`
- **After every plan wave:** Run the profile smoke test command for completed profiles
- **Before `/gsd:verify-work`:** All 6 profile smoke tests must pass
- **Max feedback latency:** 120 seconds per profile

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| JWT services | 01 | 1 | LAB-01 | smoke | `docker compose --profile jwt up -d && sleep 5 && curl -s http://localhost:20001/.well-known/jwks.json` | ❌ W0 | ⬜ pending |
| Registry + images | 01 | 1 | LAB-02 | smoke | `docker compose --profile registry up -d && curl -s http://localhost:20005/v2/_catalog` | ❌ W0 | ⬜ pending |
| Gitea + seed | 02 | 1 | LAB-03 | smoke | `docker compose --profile source up -d && sleep 10 && curl -s http://localhost:20006/api/v1/repos/search` | ❌ W0 | ⬜ pending |
| Storage profile | 02 | 1 | LAB-04 | smoke | `docker compose --profile storage up -d && sleep 5 && aws --endpoint-url=http://localhost:20007 kms list-keys` | ❌ W0 | ⬜ pending |
| ssh-weak service | 03 | 1 | LAB-05 | smoke | `docker compose --profile ssh-weak up -d && sleep 5 && ssh-audit localhost:20022` | ❌ W0 | ⬜ pending |
| LDAPS service | 03 | 1 | LAB-06 | smoke | `docker compose --profile ldaps up -d && sleep 5 && sslyze --targets localhost:636` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- No new pytest test files are needed — Phase 4 delivers Docker infrastructure, not Python code.
- Validation is performed via Docker Compose smoke commands above.
- `expected_results_v3.md` must be updated with expected scanner findings per profile.

*All validation is smoke-test only for this phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| JWT scanner finds ≥ 2 weak-alg findings | LAB-01 | Requires running QU.I.R.K. scanner against live JWT services | `docker compose --profile jwt up -d && quirk scan --targets http://localhost:20001,http://localhost:20002,http://localhost:20003,http://localhost:20004` |
| Container scanner detects old crypto libs in registry images | LAB-02 | Requires syft + running Docker Registry | `docker compose --profile registry up -d && quirk scan --container localhost:20005/image-old-pycrypto` |
| Source scanner returns ≥ 1 finding per anti-pattern category | LAB-03 | Requires cloning Gitea repos then running semgrep | Clone repo from Gitea at localhost:20006, run `semgrep --config p/cryptography .` |
| AWS connector + storage targets respond to scan queries | LAB-04 | Requires live LocalStack KMS + Vault + postgres | `quirk scan --cloud aws --endpoint http://localhost:20007` |
| SSH scanner returns weak KEX/hostkey/MAC findings | LAB-05 | Requires ssh-audit against live weak SSH service | `ssh-audit localhost:20022` — expect group1-sha1, ssh-dss, hmac-md5 |
| sslyze returns TLS findings against LDAPS | LAB-06 | Requires running OpenLDAP with TLS on port 636 | `sslyze --targets localhost:636` — expect cert chain + cipher findings |

---

## Validation Sign-Off

- [x] All 6 lab profiles start cleanly with `docker compose --profile <name> up -d`
- [x] All 6 profile smoke tests return expected findings
- [x] `expected_results_v3.md` updated with new profile findings
- [x] No port conflicts with existing lab ports
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
