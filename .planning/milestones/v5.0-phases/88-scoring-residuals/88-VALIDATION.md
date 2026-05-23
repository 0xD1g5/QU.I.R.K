---
phase: 88
slug: scoring-residuals
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-22
updated: 2026-05-22
---

# Phase 88 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (Python); vitest (dashboard, only if `src/dashboard` touched) |
| **Config file** | `pyproject.toml` ([tool.pytest]); `src/dashboard/` for vitest |
| **Quick run command** | `QUIRK_DB_PATH=./quirk.db python -m pytest -m 'not slow' -q` |
| **Full suite command** | `QUIRK_DB_PATH=./quirk.db python -m pytest tests/ -q` |
| **Estimated runtime** | ~21 seconds (full, not-slow) |

> **CAVEAT (carry-in from Phase 87):** the suite errors at *collection* with `Multiple QU.I.R.K. DBs found` unless `QUIRK_DB_PATH` is set — stray gitignored scan DBs exist in the working tree. **Always export `QUIRK_DB_PATH`** when running tests this phase. (Permanent conftest fix is logged for Phase 91.) Baseline: 39 pre-existing failures unrelated to this phase (CBOM compose-profile drift, stale version strings, dashboard themes) — Phase 88 must not increase that count.

---

## Sampling Rate

- **After every task commit:** Run quick command (`pytest -m 'not slow' -q` with `QUIRK_DB_PATH` set)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite green (no NEW failures vs the 39-failure pre-phase baseline)
- **Max feedback latency:** ~25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _to be filled by planner_ | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scoring_subscore_orthogonality.py` — parametrized six-subscore-family lock test (D-02 / EVIDENCE-TALLY-01)
- [ ] `tests/test_score_render_parity.py` — data-layer parity gate across CLI/dashboard/HTML-PDF anchored to the 0–100 contract (D-04 / RENDER-CLI/PDF-01)
- [ ] CBOM Pass-1 emission + no-crypto-marker tests for the 5 profiles (D-05/D-06 / SCORE-CBOM-01)
- [ ] subscore-decomposition render tests for HTML/PDF/CLI markdown (D-07 / SCORE-XPARENCY-01)

*Planner finalizes exact file list; existing infrastructure (pytest) covers the framework.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _none expected — all behaviors automatable at the data layer_ | | | |

*If none: all phase behaviors have automated verification (D-04 deliberately verifies at the data layer, not via rendered-PDF scraping).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 25s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
