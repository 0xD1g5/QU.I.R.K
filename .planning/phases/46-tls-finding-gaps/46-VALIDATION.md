---
phase: 46
slug: tls-finding-gaps
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `pytest tests/test_risk_engine.py tests/test_tls_scanner.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~30s quick · ~3 min full |

Live-fire chaos lab verification (manual gate):
- Bring up profile: `cd quantum-chaos-enterprise-lab && PROFILE_ARGS="--profile tls-cert-defects" ./lab.sh up`
- Run scanner: `quirk scan localhost:13444,localhost:13445,localhost:13446,localhost:13447`
- Inspect findings: open generated report and confirm 4 distinct findings (CRITICAL/HIGH/MEDIUM/HIGH)

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite + RESEARCH.md authored sentinel tests
- **Before `/gsd-verify-work`:** Full suite green + chaos lab live-fire pass
- **Max feedback latency:** 60s (quick) / 180s (full)

---

## Per-Task Verification Map

> Filled by planner. Each task must map to a requirement (TLS-FIND-01..07), an automated command, and a known test file. Manual-only behaviors live in the Manual section below.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _planner fills_ | _planner fills_ | _planner fills_ | TLS-FIND-NN | T-46-NN / — | _e.g. "no half-populated CryptoEndpoint reaches DB"_ | unit/integration | `pytest tests/test_x.py::test_y -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tls_scanner_chain_verified.py` — sentinel: sslyze success → `chain_verified` set; sslyze ERROR → fallback fires AND sets `chain_verified`; no `cert_not_after=None` half-populated rows
- [ ] `tests/test_risk_engine_cert_defects.py` — one finding per defect class (D-02), self-signed vs untrusted-CA mutually exclusive (D-04), expected severities CRITICAL/HIGH/MEDIUM/HIGH/HIGH
- [ ] `tests/conftest.py` — fixtures for cert variants (expired, self-signed, untrusted-CA, RSA-1024, EC-192) reusing chaos lab cert files where possible
- [ ] DB migration shim — if Phase 46 adds `chain_verified` column, ensure existing SQLite DBs get an `ALTER TABLE` upgrade path (Research open question)
- [ ] Update **existing** `tests/test_risk_engine.py` cases that assert old severities (TLS-FIND-01: HIGH→CRITICAL; TLS-FIND-02: MEDIUM→HIGH) — must land in same commit as engine fix

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chaos lab `tls-cert-defects` profile boots cleanly with all 4 nginx services | TLS-FIND-07 | Requires Docker daemon | `cd quantum-chaos-enterprise-lab && PROFILE_ARGS="--profile tls-cert-defects" ./lab.sh up` then `./lab.sh status` |
| End-to-end scan against live profile produces 4 distinct findings with correct severities | TLS-FIND-01..05 | Requires running lab | `quirk scan localhost:13444-13447 --output report.html` and inspect |
| `lab.sh down` cleanly tears down the new profile | CLAUDE.md chaos lab rule | Stateful Docker | `./lab.sh down` then `docker ps` shows no leftover tls-cert-* containers |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (chain_verified field, severity-fix tests, cert fixtures)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s (quick) / 180s (full)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
