---
phase: 6
slug: documentation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-31
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Shell/markdown linting + manual walkthrough |
| **Config file** | none — documentation phase, no automated test framework |
| **Quick run command** | `ls docs/*.md \| wc -l` |
| **Full suite command** | `find docs/ -name "*.md" -exec wc -l {} +` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Verify file exists at expected path with correct section headings
- **After every plan wave:** Confirm all required doc files present, run heading completeness check
- **Before `/gsd:verify-work`:** Full manual walkthrough per acceptance criteria
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 1 | DOC-01 | file check | `test -f docs/getting-started.md` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 1 | DOC-02 | file check | `test -f docs/installation.md` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | DOC-03 | file check | `test -f docs/connectors/aws.md` | ❌ W0 | ⬜ pending |
| 6-02-02 | 02 | 1 | DOC-03 | file check | `test -f docs/connectors/azure.md` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 2 | DOC-04 | grep check | `grep -q "Risk Score" docs/report-interpretation.md` | ❌ W0 | ⬜ pending |
| 6-03-02 | 03 | 2 | DOC-05 | grep check | `grep -q "CBOM" docs/cbom-guide.md` | ❌ W0 | ⬜ pending |
| 6-04-01 | 04 | 2 | DOC-06 | file check | `test -f docs/chaos-lab.md` | ❌ W0 | ⬜ pending |
| 6-05-01 | 05 | 3 | DOC-07 | file check | `test -f README.md && grep -q "quirk" README.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/` directory created at repo root
- [ ] `docs/connectors/` subdirectory created

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Getting Started completes scan in <10 min on clean macOS | DOC-01 | Requires a real machine + network | Follow guide on clean system, measure elapsed time |
| Installation guide works on Windows WSL | DOC-02 | Requires WSL environment | Follow guide in WSL2, confirm scan runs |
| IAM policy grants least-privilege AWS scan | DOC-03 | Requires AWS account | Apply policy, run scan, verify no permission errors |
| Score labels map to correct client explanations | DOC-04 | Subjective readability review | Read report-interpretation.md, cross-check against scoring.py thresholds |
| CBOM guide citable as compliance evidence | DOC-05 | Legal/compliance judgement | Review CBOM guide for ISO 27001/FedRAMP citation language |
| Chaos lab operator guide covers all 6 Phase 4 profiles | DOC-06 | Requires enumeration check | Confirm chaos-lab.md lists: cloud, containers, kubernetes, registry, source-code, storage |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
