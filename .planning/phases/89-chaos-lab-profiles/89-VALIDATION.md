---
phase: 89
slug: chaos-lab-profiles
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-22
---

# Phase 89 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x; chaos-lab tests are `slow`/Docker-gated |
| **Config file** | `pyproject.toml` ([tool.pytest]) |
| **Quick run command** | `QUIRK_DB_PATH=./quirk.db python -m pytest -m 'not slow' -q` |
| **Full suite command** | `QUIRK_DB_PATH=./quirk.db python -m pytest tests/ -q` |
| **Lab-integration command** | `cd quantum-chaos-enterprise-lab && PROFILE_ARGS="--profile <name>" ./lab.sh up` then scan + assert expected_results |
| **Estimated runtime** | ~21s (not-slow); lab bring-up minutes per profile (Docker) |

> **CAVEAT:** export `QUIRK_DB_PATH=./quirk.db` or the suite errors at collection (multi-DB). Baseline = 39 pre-existing failures; do not increase. Docker MUST be running for lab bring-up / profile verification tasks.

---

## Sampling Rate

- **After every task commit:** quick command (unit/config-level checks)
- **After a profile is added:** bring the profile up via `lab.sh` + run the scanner + assert the new `expected_results_v4.md` entry (Docker-gated)
- **gRPC task 1 (D-03):** empirically confirm sslyze negotiates ALPN-h2 BEFORE wiring the probe — a blocker gate, not a deferred check
- **Before `/gsd:verify-work`:** full suite green (no new failures vs 39 baseline) + each new profile's expected_results verified

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _to be filled by planner_ | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `expected_results_v4.md` oracle entries for each new profile (postgres-tls, redis-tls, kafka-tls, grpc-tls) — ports, services, expected findings
- [ ] profile bring-up + scanner-finding assertions per new profile (Docker-gated)
- [ ] LAB-03: expected-results/UAT note proving STARTTLS detection on the existing `email` profile
- [ ] LAB-06: UAT asserting Kerberos/SAML/DNSSEC evidence counters flow into the identity subscore (live identity profile)

*Planner finalizes; existing pytest + chaos-lab-test infra covers the framework.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live multi-profile lab bring-up on the operator's Docker host | LAB-01..05 | Requires Docker + minutes per profile; not CI-fast | `PROFILE_ARGS="--profile <name>" ./lab.sh up` then scan; compare to expected_results_v4.md |

*Profile-level scanner findings are automatable but Docker-gated (slow-marked).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency acceptable (unit fast; lab Docker-gated)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
