---
phase: 147
slug: backlog-drain-lifecycle-ledger-tail
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-10
updated: 2026-08-11
---

# Phase 147 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing project standard) |
| **Config file** | `pytest.ini` / `pyproject.toml` addopts (existing — deselects `@slow` by default per project memory) |
| **Quick run command** | `pytest tests/test_run_scan_otics_ssh_gate.py -x` (DRAIN-01); new BACnet-vendor test file (DRAIN-02) |
| **Full suite command** | `python -m pytest` |
| **Estimated runtime** | ~120 seconds (existing suite size) |

---

## Sampling Rate

- **After every task commit:** Run targeted `pytest` for the touched module (DRAIN-01/02 only; DRAIN-03/04 are doc-only, no automated command)
- **After every plan wave:** Run `python -m pytest` full suite (catches any regression from DRAIN-01's `run_scan.py` restructure — this file is heavily depended-upon)
- **Before `/gsd:verify-work`:** Full suite must be green, plus `python -m compileall` per CLAUDE.md
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 147-01-* | 01 | 1 | DRAIN-01 | — | Resume path with ssh-checkpointed-complete still fingerprints OT-only hosts | unit | `pytest tests/test_run_scan_otics_ssh_gate.py -x` (extended with Group C) | ✅ exists | ✅ green |
| 147-02-* | 02 | 1 | DRAIN-02 | — | BACnet vendor ID 5 resolves to "Johnson Controls" and correlates to the existing CVE entry | unit | `pytest tests/test_bacnet_vendor_resolution.py -x` | ✅ exists | ✅ green |
| 147-03-* | 03 | 1 | DRAIN-03 | T-WR-02 / T-CD-03 | Ledger has zero undecided/stale rows; WR-02 fixed, CD-03 accept-risk documented | manual (doc review) | N/A — markdown correctness, not code | N/A | ✅ green |
| 147-04-* | 04 | 1 | DRAIN-04 | — | STATE.md Deferred Items ledger re-triaged, Authenticode item folded in | manual (doc review) | N/A — markdown correctness, not code | N/A | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Post-execution result (2026-08-11, v5.11 milestone-audit closeout):**
`pytest -q tests/test_run_scan_otics_ssh_gate.py tests/test_bacnet_vendor_resolution.py` →
**27 passed**. Both manual doc-review rows were independently confirmed by `147-VERIFICATION.md`
(status `passed`, 4/4 must-haves, criteria 3 and 4) against the live ledger files, including
`git cat-file -e` confirmation of all eight cited commit SHAs.

---

## Wave 0 Requirements

- [x] `tests/test_run_scan_otics_ssh_gate.py` — extended with Group C (resume-path OT-supplemental coverage), covers DRAIN-01
- [x] New test file `tests/test_bacnet_vendor_resolution.py` — no existing test covered BACnet vendor-ID→name resolution, covers DRAIN-02
- Framework install: none — pytest already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Audit ledger rows flipped to `[x] closed` with correct commit citations | DRAIN-03 | Markdown ledger correctness is not code-verifiable; requires human/agent cross-read against `git log -S` citations | Read `.planning/audit-2026-05-27/AUDIT-TASKS.md` after the plan's edits; confirm each of the 12 named rows has either `[x] closed` + commit SHA, or an explicit fresh fix-or-accept-risk call (WR-02, CD-03) |
| WR-02 CORS fix actually closes the origin/port mismatch | DRAIN-03 | Behavioral fix in `quirk/config.py::get_cors_origins` / `quirk/dashboard/api/app.py`; correctness verified by reading the diff against the documented mismatch, not a new automated CORS test (out of phase scope per drain-phase framing) | Read the diff; confirm default origins now include port; optionally curl-test if a local server is easy to stand up |
| STATE.md Deferred Items table re-triaged with accurate current status per row | DRAIN-04 | Ledger status of items like "Windows Authenticode production cert" is an external-state fact only the user can confirm | Read updated STATE.md table; confirm each row is either resolved with evidence, or re-confirmed blocked with a stated reason; Authenticode item explicitly flagged as awaiting user confirmation |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — DRAIN-03/04 are doc-only by design and are covered by the Manual-Only Verifications table below, both confirmed in `147-VERIFICATION.md`
- [x] Wave 0 covers all MISSING references — both test files now exist and are green
- [x] No watch-mode flags
- [x] Feedback latency < 120s — measured 6.7s for the combined targeted run
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-11 (retroactive closeout — this file was written pre-execution and
never updated when the phase completed; the v5.11 milestone audit flagged it as the milestone's
only `nyquist_compliant: false` phase. Closed by re-running both automated commands live and
cross-checking the two manual rows against `147-VERIFICATION.md`. No code changes were required.)
