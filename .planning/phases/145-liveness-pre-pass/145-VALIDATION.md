---
phase: 145
slug: liveness-pre-pass
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-10
---

# Phase 145 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing repo standard) |
| **Config file** | `pyproject.toml` — `addopts = "-m 'not slow'"` (default run excludes `@slow`) |
| **Quick run command** | `pytest tests/test_nmap_provider.py tests/test_nmap_parser.py -x` |
| **Full suite command** | `pytest` (repo default; excludes `@slow` unless `-m slow` explicitly added) |
| **Estimated runtime** | ~30 seconds (quick), full suite per repo baseline |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_nmap_provider.py tests/test_nmap_parser.py -x`
- **After every plan wave:** Run `pytest` (full suite, `not slow` default)
- **Before `/gsd:verify-work`:** Full suite must be green, plus D-06's human-UAT non-root pass signed off separately (cannot be gated by automated suite per D-06)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 145-01-TBD | 01 | 1 | DISC-03 | — | Pre-pass filters batch hosts before `run_nmap_discovery()` call | unit (fake callable) | `pytest tests/test_nmap_provider.py::test_liveness_pass_filters_batch -x` | ❌ W0 | ⬜ pending |
| 145-01-TBD | 01 | 1 | DISC-03 | — | Liveness-skipped hosts produce `CryptoEndpoint(scan_error_category="liveness_skip")` rows, not silently dropped | unit | `pytest tests/test_nmap_provider.py::test_liveness_skip_appends_liveness_skip_category -x` | ❌ W0 | ⬜ pending |
| 145-01-TBD | 01 | 1 | DISC-03 | T-145-01 | `os.geteuid()`-based check produces the D-01 advisory row (logger + CryptoEndpoint) when non-root | unit (monkeypatch `os.geteuid`) | `pytest tests/test_nmap_provider.py::test_fallback_advisory_emitted_when_non_root -x` | ❌ W0 | ⬜ pending |
| 145-01-TBD | 01 | 1 | DISC-03 | — | `parse_nmap_host_status()` correctly extracts up/down state incl. down hosts | unit (fixture XML, up+down hosts) | `pytest tests/test_nmap_parser.py::test_parse_host_status_up_and_down -x` | ❌ W0 (new file) | ⬜ pending |
| 145-01-TBD | 01 | 1 | DISC-03 | T-145-02 | Port-list string for `-PS<ports>` passes through `_SAFE_NMAP_ARG_RE` allowlist validation before subprocess invocation | unit | `pytest tests/test_nmap_provider.py::test_liveness_port_spec_validated -x` | ❌ W0 | ⬜ pending |
| 145-01-TBD | 01 | 1 | DISC-03 | T-145-03 | `parse_nmap_host_status()` uses `quirk.util.xml_safe.make_safe_parser()` (WR-06 XXE chokepoint), not a bypassing parser | unit / invariant | `pytest tests/test_xml_safe.py::test_nmap_parser_blocks_xxe_lxml -x` | ✅ exists | ⬜ pending |
| 145-01-TBD | 01 | 1 | DISC-03 (D-06) | — | Real non-root nmap invocation triggers fallback detection end-to-end | manual-only | N/A — human-UAT chaos-lab walkthrough | manual gate, not automatable per D-06 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs are placeholders (145-01-TBD) pending planner-assigned task IDs; update this table once PLAN.md files exist.*

---

## Wave 0 Requirements

- [ ] `tests/test_nmap_parser.py` — does not exist today; create to cover `parse_nmap_host_status()` (verify during planning whether any existing file directly exercises `parse_nmap_xml()`, and decide whether to add to it or keep this as a new dedicated file)
- [ ] Fixture XML files or inline XML strings for up/down host test cases (mirror the "fake callable" style already used in `test_nmap_provider.py` — no live nmap binary required in CI)
- [ ] `os.geteuid` monkeypatch pattern for the privilege-check unit test (stdlib `unittest.mock.patch` of `os.geteuid`, standard and low-risk)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Non-root SYN→connect silent fallback detection | DISC-03 (D-06) | nmap's XML output is byte-identical whether privileged or not (verified live this session) — no automatable signal exists to distinguish the fallback from nmap's own output; only a real non-root process run against a real host proves the `os.geteuid()` pre-check actually fires the advisory in practice | Run QUIRK as a non-root user against a chaos-lab target; confirm the D-01 advisory (logger message + CryptoEndpoint advisory row) appears in the scan artifact/report. Gate as documented human-UAT checkpoint per D-06 (mirrors UAT-118-01 pattern). |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
