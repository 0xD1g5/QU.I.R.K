---
phase: 41
slug: ci-stability-scanner-robustness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-29
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python 3.11+) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (Wave 0 creates if missing — see RESEARCH §"No `[tool.pytest.ini_options]` exists") |
| **Quick run command** | `pytest -m 'not slow' -x` |
| **Full suite command** | `pytest -m 'not slow'` |
| **Estimated runtime** | <60s on developer machine (D-16 budget) |

---

## Sampling Rate

- **After every task commit:** Run `pytest -m 'not slow' -x` (filter to changed module via `pytest tests/test_<area>.py` when wave is scoped)
- **After every plan wave:** Run `pytest -m 'not slow'` (full default suite)
- **Before `/gsd-verify-work`:** Full suite must be green AND `pytest -m slow` must pass at least once
- **Max feedback latency:** 60s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner — one row per task) | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Derived from RESEARCH §"Validation Architecture" and §"Open Questions":

- [ ] `pyproject.toml` — add `[tool.pytest.ini_options]` with `addopts = "-m 'not slow'"` and register `slow` + `live_infra` markers (RESEARCH found this is currently absent)
- [ ] `tests/skip_registry.py` (or `tests/conftest.py` registry hook) — central allowed-skip registry with `{file:line, category, reason}` entries (D-02)
- [ ] `tests/test_skip_registry.py` — meta-test that fails on unregistered `pytest.skip` / `importorskip` / `@skipif` (D-03; analog: `tests/test_hygiene.py` per PATTERNS.md)
- [ ] `tests/test_scan_robustness.py` — stubs for ROBUST-01..04 acceptance criteria (analogs: `test_broker_db_schema.py` + `test_email_scanner.py` per PATTERNS.md)
- [ ] `tests/test_timeouts_config.py` — stubs for TimeoutsCfg / RetryCfg loading + deprecation-alias warnings (D-06, D-07)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stderr advisory format on missing `[motion]` extra | ROBUST-01 / D-12 | Stderr capture in pytest is brittle across `capsys`/`capfd`; one canonical UAT line is more durable than a fragile assertion | UAT-41-01: `pip uninstall -y quirk[motion]` (or use a venv without it), run `quirk scan --target localhost --enable-broker`, confirm stderr contains `[advisory] scanner=broker_scanner extra=motion not installed` and exit code is 0 |
| Overall scan upper-bound formula documentation | ROBUST-02 / D-10 | Documentation correctness is read-verified, not asserted | UAT-41-02: confirm `docs/configuration.md` contains the formula `sum(per_scanner_timeout × max_targets_for_phase) + 10s safety_margin` and lists every scanner's timeout slot |
| `lab.sh` profile-tagged service sweep | D-18 + RESEARCH "lab.sh reset arm" | Requires running compose lab; not appropriate for unit-test wave | UAT-41-03: `./lab.sh up && ./lab.sh down`, then `docker ps -a` shows zero quirk-lab profile-tagged containers; same for `./lab.sh reset` if reset arm is in scope |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
