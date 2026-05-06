---
phase: 50-enterprise-documentation
plan: 01
subsystem: tests
tags: [docs, phase-50, gate-test, tdd-red, wave-1]
requires: []
provides:
  - tests/test_phase50_docs_presence.py (RED gate, uncommitted, awaits 50-02 atomic landing)
affects:
  - docs/architecture.md (gated — created by 50-02)
  - docs/operators-guide.md (gated — created by 50-03)
tech-stack:
  added: []
  patterns:
    - "File-presence + lowercased substring assertion gate (analog of tests/test_pqc_terminology_gate.py)"
key-files:
  created:
    - tests/test_phase50_docs_presence.py
  modified: []
decisions:
  - "Test file deliberately left uncommitted per W6 fix; Plan 50-02 will commit it atomically alongside docs/architecture.md to avoid an interim RED on QUIRK-v4 CI."
metrics:
  duration: ~3 min
  completed: 2026-05-05
status: complete
---

# Phase 50 Plan 01: Phase 50 Docs Presence Gate (RED) Summary

**One-liner:** Authored the Phase 50 docs presence pytest gate (`tests/test_phase50_docs_presence.py`) using the Phase 48 PQC-terminology-gate analog — file-presence + lowercased substring checks for the two not-yet-existent docs; left uncommitted for atomic landing in Plan 50-02 (W6 fix).

## What Shipped

A single new test file at `tests/test_phase50_docs_presence.py` containing:

- Module docstring citing `tests/test_pqc_terminology_gate.py` as the pattern source.
- Module constants:
  - `_REPO_ROOT` resolved from `__file__`.
  - `_REQUIRED_DOCS = ["docs/architecture.md", "docs/operators-guide.md"]`.
  - `_REQUIRED_SECTIONS` dict mapping each doc to its required substring tuple (verbatim below).
- Helper `_read(rel) -> str` returning lowercased file contents.
- Two test functions:
  - `test_required_docs_resolve()` — asserts both docs exist on disk; FAILS with `Required Phase 50 doc missing: docs/architecture.md` in current state.
  - `test_required_sections_present()` — accumulates `(rel, needle)` pairs for any required substring missing from the lowercased file contents.

### Final Substring Set (verbatim from the file)

`docs/architecture.md`:
- `"data flow"`
- `"trust boundar"`
- ` ```mermaid `
- `"credential"` (covers connector credential-storage matrix — scope addition #1)

`docs/operators-guide.md`:
- `"troubleshoot"`
- `"compliance map maintenance"`
- `"quirk compliance status"`
- `"staleness_threshold_days"`
- `"tests/test_compliance_freshness.py"`
- `"https://www.pcisecuritystandards.org"` (PCI source URL)
- `"https://www.ecfr.gov"` (HIPAA canonical regulation text via ECFR)
- `"hhs.gov"` (HIPAA publisher)
- `"https://csrc.nist.gov"` (NIST source URL)
- `"quirk init"` (covers scope addition #2)

## Verification

- `python -m compileall tests/test_phase50_docs_presence.py` → clean (PEP 8 / syntax OK).
- `python -m pytest tests/test_phase50_docs_presence.py -x` → **FAILS** at `test_required_docs_resolve` with assertion message `Required Phase 50 doc missing: docs/architecture.md`.
- This is the **expected RED state** per Wave 1 design — proves the gate is wired before the docs land.

## Deliberate RED → GREEN Path

| Plan | Lands | Test transition |
| ---- | ----- | --------------- |
| 50-01 (this plan) | Test file authored, **uncommitted** | RED — by design |
| 50-02 | `docs/architecture.md` + this test (atomic single commit, W6 fix) | architecture half GREEN; operators-guide half still RED |
| 50-03 | `docs/operators-guide.md` | All assertions GREEN |

After 50-03 ships, any future PR that removes a required section, source URL, or compliance citation breaks CI.

## Pattern Source

Module docstring opens:

> "Pattern modelled on tests/test_pqc_terminology_gate.py — read source file from disk, substring-check the contents."

Same `_REPO_ROOT` resolution, same `_read(rel)` helper shape, same lowercased substring assertion style as the Phase 48 PQC terminology gate.

## Deviations from Plan

None — plan executed exactly as written. The test file is intentionally uncommitted per the W6 fix encoded in Task 2; Plan 50-02 owns the atomic commit.

## Self-Check: PASSED

- `tests/test_phase50_docs_presence.py` exists on disk (verified via `ls`).
- Pytest fails with the expected assertion message (verified above).
- No commit recorded for the test file in this plan (verified via `git status` showing it as untracked, `git log` empty for this path).
- Only this SUMMARY.md will be committed by this plan.
