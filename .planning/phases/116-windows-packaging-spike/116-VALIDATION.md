---
phase: 116
slug: windows-packaging-spike
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-27
---

# Phase 116 — Validation Strategy

> Per-phase validation contract. This is a SPIKE — the deliverable is an
> assessment doc + a non-blocking CI job, so "validation" is content/structure
> assertions on the doc and YAML-validity of the CI job, not unit tests of
> production code (no production code ships).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | shell/grep assertions + YAML lint (no pytest target — spike) |
| **Config file** | n/a |
| **Quick run command** | `grep` content checks on docs/windows-packaging-spike.md + `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/python-ci.yml'))"` |
| **Full suite command** | `python -m pytest tests/ -q` (regression — confirms the spike added no breakage) |
| **Estimated runtime** | <30s for assertions; CI job runs async on windows-latest |

---

## Sampling Rate

- **After every task commit:** Run the doc grep + YAML-validity check
- **Before completion:** Full pytest suite green (no regression from CI-yaml/doc changes)
- **Max feedback latency:** <30s local; CI job result observed on the PR/push

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| (planner) | — | — | WINPKG-01 | yaml-valid | `python -c "import yaml; yaml.safe_load(open('.github/workflows/python-ci.yml'))"` | ⬜ |
| (planner) | — | — | WINPKG-01 | doc-content | `grep -q "go\|no-go\|defer" docs/windows-packaging-spike.md && grep -qi "scheduled task" docs/windows-packaging-spike.md` | ⬜ |
| (planner) | — | — | WINPKG-01 | scope-guard | `! ls *.spec *.nsi dist/ 2>/dev/null` (no artifact committed) | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red*

---

## Wave 0 Requirements

- [ ] No new test infrastructure needed — assertions are grep/YAML-lint on the deliverables.

*Existing infrastructure covers regression; spike deliverables are doc + CI YAML.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| windows-latest spike build result | WINPKG-01 | Needs the GitHub Actions windows-latest runner | Observe the `windows-packaging-spike` job on the PR/push; confirm build log + artifact captured and reflected in the assessment doc |
| Go/no-go judgement quality | WINPKG-01 | Human assessment of evidence | Read docs/windows-packaging-spike.md; confirm the recommendation follows from the CI evidence |

---

## Validation Sign-Off

- [ ] All tasks have an automated assertion or are manual-only (CI-runner-gated)
- [ ] Doc content assertions cover the 5 required topics + go/no-go line
- [ ] Scope guard assertion: no frozen EXE / installer / NSIS committed
- [ ] Full pytest suite green (no regression)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
