---
phase: 152
slug: discovery-empirical-closure
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-13
---

# Phase 152 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`pyproject.toml` `[tool.pytest.ini_options]`, existing) |
| **Config file** | `pyproject.toml` (`addopts = "-m 'not slow'"`) |
| **Quick run command** | `pytest tests/test_interactive_mode.py tests/test_interactive_validate_routes.py -x -q` |
| **Full suite command** | `pytest -q -m ""` (matches `linux-full-suite` CI job) |
| **Estimated runtime** | full suite per existing baseline; DISC-09/10 are manual live-fire, not pytest |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_interactive_validate_routes.py tests/test_interactive_mode.py -x -q`
- **After every plan wave:** `pytest -q -m ""` (full suite)
- **Before `/gsd:verify-work`:** Full suite green; DISC-09/DISC-10 gated by the written finding
  document + at least 3 live verification runs (CONTEXT.md), not by pytest
- **Max feedback latency:** 30 seconds (pytest); DISC-09/DISC-10 live-fire runs are manual/slow
  and out of the automated sampling loop by design

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 152-01-01 | 152-01 | 1 | DISC-09 | T-152-01, T-152-02 | `segmented-network` profile exists, `./lab.sh profiles` lists it, gateway/live-tls topology + 2-host smoke test show RST/open split | automated + manual live-fire | `./lab.sh profiles \| grep -c segmented-network`; `docker compose --profile segmented-network config` | ✅ | ✅ verify block added |
| 152-01-02 | 152-01 | 1 | DISC-09 | T-152-02 | Full dead-range sweep shows 100% RST/unreachable; both live services report open; exactly 4 `segnet-*` services | manual live-fire + automated grep | `grep -c "^  segnet-" quantum-chaos-enterprise-lab/docker-compose.yml` | ✅ | ✅ verify block added |
| 152-01-03 | 152-01 | 1 | DISC-09 | — | chaos-lab.md/README.md/oracle file all document the profile per CLAUDE.md Chaos Lab Maintenance | automated (doc grep) | `grep -c "### 3.24 segmented-network Profile" docs/chaos-lab.md`; `grep -c "segmented-network" quantum-chaos-enterprise-lab/README.md`; `test -f .../expected_results_segmented_network.md` | ✅ | ✅ verify block added |
| 152-02-01 | 152-02 | 1 | DISC-11 | T-152-03 | `enable_nmap` prompt defaults to `True`, locked by a regression test | unit (TDD) | `pytest tests/test_interactive_validate_routes.py -x -q`; `pytest tests/test_interactive_validate_routes.py tests/test_interactive_mode.py -x -q`; `python -m compileall quirk/interactive.py` | ✅ | ✅ verify block added |
| 152-03-01 | 152-03 | 2 | DISC-10 | — | `compare_discovery.py` exists, compiles, diff logic scoped to `segnet-live` before diffing | automated (compile+grep) + manual live-fire run | `python -m py_compile .../compare_discovery.py`; `grep -n "segnet-live\|10.70.0" .../compare_discovery.py` | ✅ | ✅ verify block added |
| 152-03-02 | 152-03 | 2 | DISC-10 | — | Written finding on whether the Phase 144 artifact reproduces, grounded in 3 live-fire runs | manual live-fire, doc-producing | `test -f 152-DISC09-FINDING.md && grep -Ec "VERDICT: (DOES NOT REPRODUCE\|REPRODUCES)" 152-DISC09-FINDING.md` | ✅ | ✅ verify block added |
| 152-03-03 | 152-03 | 2 | DISC-10 | T-152-04 | Ledger (STATE.md, v5.11-MILESTONE-AUDIT.md) closed out; conditional mitigation applied or explicitly absent | automated (grep + compileall) + conditional pytest | `! grep -q "OPEN (needs real hardware)" .../v5.11-MILESTONE-AUDIT.md`; `grep -c "152-DISC09-FINDING" .planning/STATE.md`; `python -m compileall quirk/discovery/nmap_provider.py` | ✅ | ✅ verify block added |
| 152-04-01 | 152-04 | 3 | DISC-09, DISC-10, DISC-11 | — | docs/UAT-SERIES.md carries a Series 152 entry covering all three requirements | automated (doc grep) | `grep -c "## Series 152" docs/UAT-SERIES.md`; `grep -Ec "DISC-09\|DISC-10\|DISC-11" docs/UAT-SERIES.md` | ✅ | ✅ verify block added |
| 152-04-02 | 152-04 | 3 | DISC-09, DISC-10, DISC-11 | — | Obsidian phase note + Chaos-Lab.md vault re-sync exist and are current | automated (obsidian CLI search) | `obsidian vault="Digs" search query="path:20_Dev-Work/QUIRK/Phases/Phase-152"`; `obsidian vault="Digs" search query="path:20_Dev-Work/QUIRK/Guides/Chaos-Lab segmented-network"` | ✅ | ✅ verify block added |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Note: "✅ verify block added" means the `<verify><automated>` block now exists in the corresponding
PLAN.md task and is ready to run at execution time — it does not assert the command has already
been run against a live environment. DISC-09/DISC-10 automated checks intentionally cover only the
static/artifact-level assertions; the live Docker-topology runs themselves remain manual live-fire
per the Manual-Only Verifications table below, consistent with RESEARCH.md's Validation Architecture
section (chaos-lab infra is not part of the pytest-driven sampling loop).*

---

## Wave 0 Requirements

- [x] New unit test in `tests/test_interactive_validate_routes.py` asserting `default=True` at
  the `enable_nmap` prompt call site (static-source-check style, matching existing pattern) —
  scaffolded as Task 1's RED test in Plan 152-02 (`tdd="true"`, `<behavior>` block specifies the
  RED test explicitly before the flip)
- [x] `quantum-chaos-enterprise-lab/expected_results_segmented_network.md` — new oracle file,
  scaffolded as Plan 152-01 Task 3 with an explicit `<verify>` file-existence check
- [x] `.planning/phases/152-discovery-empirical-closure/152-DISC09-FINDING.md` — new, dedicated
  finding document per CONTEXT.md's locked decision, scaffolded as Plan 152-03 Task 2 with an
  explicit `<verify>` file-existence + verdict-string check

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Segmented-network lab profile produces real RST/ICMP-unreachable on the dead subnet | DISC-09 | Requires live Docker Compose up + a prober container inside the network (macOS Docker Desktop cannot route host traffic into custom bridges) | `docker compose --profile segmented-network up -d`; exec into the prober container; run direct nmap probes against dead-subnet hosts; confirm RST/ICMP-unreachable, not silence |
| Chunked discovery + partial-result tolerance run against the profile, compared to a direct nmap run of the same segment, at least 3 times | DISC-10 | Requires live Docker Compose infra and produces a qualitative written finding, not a pass/fail assertion | Run the scan via the prober container 3+ times; diff chunked-discovery output against a direct nmap run each time; write `152-DISC09-FINDING.md` with the result |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — every one of the 8 tasks across
  the 4 plans now carries a `<verify><automated>` block; DISC-09/DISC-10's irreducibly manual
  live-fire steps are explicitly carved out in the Manual-Only Verifications table above, not
  faked as automated
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — all 8 tasks have one
- [x] Wave 0 covers all MISSING references — see Wave 0 Requirements above, all three now scaffolded
  with explicit verify checks in their owning plans
- [x] No watch-mode flags
- [x] Feedback latency < 30s (pytest path) — confirmed for 152-02-01 and the pytest-based portions
  of 152-03-03
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (plan-checker blocker resolved — verify/done added to all tasks across
152-01, 152-02, 152-03, 152-04; Per-Task Verification Map filled in with real task IDs)
