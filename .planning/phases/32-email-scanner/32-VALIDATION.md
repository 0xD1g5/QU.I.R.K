---
phase: 32
slug: email-scanner
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/scanners/test_email_scanner.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~30 seconds (quick) / ~2 minutes (full) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (email scanner tests only)
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD by planner | — | — | — | — | — | — | — | — | ⬜ pending |

*Planner fills this table per task. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/scanners/test_email_scanner.py` — stubs for EMAIL-00..12
- [ ] `tests/scanners/conftest.py` — shared fixtures (mocked sslyze handshake, recorded SSLSocket cipher tuples)
- [ ] `tests/fixtures/email/` — recorded handshake fixtures for the 7 port modes
- [ ] `labs/email/` — Postfix+Dovecot weak-TLS lab + `expected_results.md`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Lab container produces ≥1 HIGH weak-cipher + ≥1 MEDIUM starttls-downgrade-risk finding | EMAIL-11 / Success #5 | Requires `docker compose --profile email up` and a real scan against the lab | 1) `docker compose --profile email up -d` 2) `quirk scan --target localhost --ports 25,465,587,993,143,995,110` 3) Inspect findings for the two expected categories |
| Port 25 cloud-egress block does not crash scan | Success #3 | Network-layer behavior depends on host egress policy | Run scan against an unreachable port-25 host (or simulate with iptables drop); confirm graceful `CONNECTION_REFUSED` log + scan completes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
