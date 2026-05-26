---
phase: 112
slug: distributed-chaos-lab-stabilization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-25
---

# Phase 112 — Validation Strategy

> Final v5.4 phase. The live multi-container E2E (LAB-01/02) is human-UAT; the automated floor is a
> compose-config validation + a YAML-parsing topology test + the existing Phase 110 unit regression.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (PyYAML for the topology parse test) |
| **Quick run command** | `pytest tests/ -k "distributed_topology or datetime_utcnow" -q` |
| **Compose validation** | `docker compose -f quantum-chaos-enterprise-lab/docker-compose.distributed.yml config -q` (CI/operator) |
| **Full suite command** | `pytest tests/ -q && python -m compileall quirk run_scan.py` |
| **Estimated runtime** | ~30 seconds (topology test) |

---

## Sampling Rate

- **After every task commit:** quick pytest command
- **After lab/compose changes:** `docker compose -f ...distributed.yml config -q` (where Docker available)
- **Before `/gsd:verify-work`:** full suite green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Requirement | Correct Behavior | Test Type | Automated Command | Status |
|-------------|------------------|-----------|-------------------|--------|
| LAB-01 | distributed compose has 2 networks, sensor-per-segment + 1 console; e2e script references enroll→push→merge in order | YAML/script parse test | `pytest -k distributed_topology` | ⬜ pending |
| LAB-02 | each segment's target reachable at the SAME hostname alias; both sensors scan it → identical recorded host:port; (live collision = human-UAT) | topology test + unit MERGE-03 (Phase 110) | `pytest -k "distributed_topology or two_segment"` | ⬜ pending |
| LAB-03 | lab.sh has a `distributed` command; README + expected_results_distributed.md exist and describe the profile; no ALL_PROFILES drift | static/grep test | `pytest -k lab_sh_distributed` ; `grep` gates | ⬜ pending |
| STAB-01 | operators-guide.md has a distributed workflow section + Windows sensor install; 999.59 settings gap closed | doc grep | `grep -q "Distributed Sensor" docs/operators-guide.md` | ⬜ pending |
| STAB-03 | no `datetime.utcnow()` in quirk/; deps pinned/placed; UAT-SERIES covers 106–112 | grep gate + doc grep | `! grep -rn "datetime.utcnow()" quirk/` ; `grep -q "Series 112" docs/UAT-SERIES.md` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] PyYAML available for the topology-parse test (confirm; it's a transitive dep)
- [ ] No new pip dependencies in the package (lab containers install `.[all]`)
- [ ] Reuse existing nginx TLS service definitions for the per-segment crypto targets

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live distributed E2E: `lab.sh distributed up` → enroll → scan → push → merge → one CBOM + one score | LAB-01 | Requires running a multi-container Docker stack | Operator runs `lab.sh distributed` + `scripts/distributed-e2e.sh`; confirm one merged CBOM + score + coverage_warning |
| Same-host:port → two components under real Docker networking | LAB-02 | Requires live two-network deployment | After the live merge, inspect the CBOM for two `crypto.internal:443` components (one per sensor_id) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
